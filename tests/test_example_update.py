from pathlib import Path

import pandas as pd
import pytest

from caderno_inteligente.ingestion import load_workbook
from caderno_inteligente.workbook_writer import EXAMPLE_MARKER
from scripts.build_example_update import (DEFAULT_OUTPUT, NEW_REFERENCE, build_example, main, package_sha256,
                                          read_package)

SOURCE = Path("data/source/Base de Dados - Caderno Inteligente.xlsm")
SERIES = ("Vendas_24m", "Sell_In", "Sell_Out")


@pytest.fixture(scope="module")
def base():
    return load_workbook(SOURCE)


@pytest.fixture(scope="module")
def example(base):
    return build_example(base)


def test_build_is_deterministic(base, example):
    assert package_sha256(build_example(base)) == package_sha256(example)


def test_monthly_series_have_only_september(example):
    for sheet in SERIES:
        assert set(example[sheet]["Mês"]) == {"2026-09"}, sheet
    assert len(example["Vendas_24m"]) == 400 and len(example["Sell_In"]) == 50


def test_snapshots_are_coherent_with_the_new_reference(example):
    ref = pd.Timestamp(NEW_REFERENCE)
    orders = example["Ordens_Producao"]
    open_orders = orders[~orders["Status"].isin(["Concluída"])]
    assert (pd.to_datetime(open_orders["Conclusão prevista"], dayfirst=True) >= ref).all()
    assert (pd.to_datetime(example["Carteira_Pedidos"]["Data prometida"], dayfirst=True) >= ref).all()
    capacity = example["Capacidade_Semanal"]
    assert pd.to_datetime(capacity["Semana inicial"]).min() == ref and ref.dayofweek == 0
    assert capacity.groupby("Linha").size().eq(16).all()
    assert (example["Estoque_Atual"]["Estoque atual"] >= 0).all()
    assert set(example["Forecast_Comercial"]["Mês"]) == {"Nov/26", "Dez/26", "Jan/27"}


def test_committed_package_matches_the_rules_and_is_marked_fictitious(capsys):
    assert DEFAULT_OUTPUT.stat().st_size < 1_000_000
    assert main(["--check"]) == 0
    leia_me = pd.read_excel(DEFAULT_OUTPUT, sheet_name="LEIA_ME", header=None)
    text = " ".join(leia_me[0].dropna().astype(str))
    assert EXAMPLE_MARKER in text and "arquivo de exemplo fictício" in text  # a segunda frase é o marcador lido por ingestion
    assert "README" not in capsys.readouterr().err


def test_check_fails_when_the_file_diverges(tmp_path):
    assert main(["--saida", str(tmp_path / "x.xlsx")]) == 0
    assert main(["--saida", str(tmp_path / "x.xlsx"), "--check"]) == 0
    assert main(["--saida", str(tmp_path / "ausente.xlsx"), "--check"]) == 1
    sheets = read_package(tmp_path / "x.xlsx")
    sheets["Vendas_24m"].loc[0, "Quantidade faturada"] += 1
    assert package_sha256(sheets) != package_sha256(read_package(DEFAULT_OUTPUT))


def test_merge_with_the_example_has_no_coherence_errors(base, example):
    merge = pytest.importorskip("caderno_inteligente.dataset_merge")
    reference = pytest.importorskip("caderno_inteligente.reference")
    from caderno_inteligente.transformations import normalise_dataset
    merged, _reports, issues = merge.merge_upload(base, example)
    assert not [i for i in issues if i["severity"] == "error"]
    normalised = normalise_dataset(merged)
    result = reference.validate_coherence(normalised, NEW_REFERENCE, previous={"reference_date": "2026-09-14", "sales_last_month": "2026-08"},
                                          sent_sheets=set(example))
    assert result["errors"] == []
    assert {w["code"] for w in result["warnings"]} <= {"PRODUCT_STOCK_DIVERGENCE"}  # esperado e documentado no README do exemplo
