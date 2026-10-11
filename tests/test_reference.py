"""Upload (U.0): data de planejamento derivada de Capacidade_Semanal e regras de coerência, com fixtures derivadas da base."""
from __future__ import annotations

import json
from datetime import date, timedelta

import pandas as pd
import pytest
from fastapi.testclient import TestClient

import backend.main as main
from caderno_inteligente.forecast_engine_config import load_engine_config
from caderno_inteligente.ingestion import load_workbook
from caderno_inteligente.official_forecast import build_official_forecasts
from caderno_inteligente.reference import (
    ReferenceDateError,
    derive_reference_date,
    reference_info,
    resolve_supply_settings,
    series_last_months,
    validate_coherence,
)
from caderno_inteligente.supply_plan import _orders_by_sku, daily_demand, load_supply_settings
from caderno_inteligente.transformations import normalise_dataset

BASE_REFERENCE = date(2026, 9, 14)
OCTOBER_REFERENCE = date(2026, 10, 12)
PREVIOUS = {"reference_date": "2026-09-14", "sales_last_month": "2026-08"}
SNAPSHOTS = {"Estoque_Atual", "Carteira_Pedidos", "Ordens_Producao", "Capacidade_Semanal"}


@pytest.fixture(scope="module")
def base() -> dict[str, pd.DataFrame]:
    return normalise_dataset(load_workbook(main.SOURCE))


def _copy(dataset: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    return {sheet: frame.copy(deep=True) for sheet, frame in dataset.items()}


def _shift(dataset, sheet: str, columns: tuple[str, ...], days: int) -> None:
    frame = dataset[sheet]
    for column in columns:
        frame[column] = pd.to_datetime(frame[column]) + timedelta(days=days)


def _repeat_month(dataset, source: str, *targets: str) -> None:
    """Copia o mês `source` das três séries mensais para os meses `targets` (vendas novas fictícias)."""
    for sheet in ("Vendas_24m", "Sell_In", "Sell_Out"):
        frame = dataset[sheet]
        month = frame[frame["Mês"] == pd.Timestamp(source)]
        dataset[sheet] = pd.concat([frame, *(month.assign(**{"Mês": pd.Timestamp(target)}) for target in targets)], ignore_index=True)


def _october(base, *, shift_ops: bool = True) -> dict[str, pd.DataFrame]:
    """Setembro nas séries, capacidade e OPs deslocadas 4 semanas (referência 12/10/2026) e a carteira sem os pedidos já vencidos."""
    dataset = _copy(base)
    _repeat_month(dataset, "2026-08-01", "2026-09-01")
    _shift(dataset, "Capacidade_Semanal", ("Semana inicial",), 28)
    orders = dataset["Carteira_Pedidos"]
    dataset["Carteira_Pedidos"] = orders[pd.to_datetime(orders["Data prometida"]) >= pd.Timestamp(OCTOBER_REFERENCE)].reset_index(drop=True)
    if shift_ops:
        _shift(dataset, "Ordens_Producao", ("Início previsto", "Conclusão prevista"), 28)
    return dataset


def _codes(result) -> list[str]:
    return [issue["code"] for issue in result["errors"]]


# --- derivação -----------------------------------------------------------------------------------


def test_packaged_base_gives_14_september_from_the_capacity_calendar(base):
    assert derive_reference_date(base) == BASE_REFERENCE
    info = reference_info(base, load_supply_settings())
    assert info == {"reference_date": "2026-09-14", "reference_source": "auto", "sales_last_month": "2026-08",
                    "series_last_months": {"Vendas_24m": "2026-08", "Sell_In": "2026-08", "Sell_Out": "2026-08"}}


def test_capacity_shifted_four_weeks_gives_12_october(base):
    dataset = _copy(base)
    _shift(dataset, "Capacidade_Semanal", ("Semana inicial",), 28)
    assert derive_reference_date(dataset) == OCTOBER_REFERENCE


def test_explicit_date_in_config_still_wins_and_auto_is_resolved(base):
    settings = load_supply_settings()
    assert settings["reference_date"] == "auto"
    resolved = resolve_supply_settings(settings, base)
    assert resolved["reference_date"] == "2026-09-14" and resolved["reference_source"] == "auto" and settings["reference_date"] == "auto"
    explicit = resolve_supply_settings({**settings, "reference_date": "2026-09-21"}, base)
    assert explicit["reference_date"] == "2026-09-21" and explicit["reference_source"] == "config"
    assert reference_info(base, {**settings, "reference_date": "2026-09-21"})["reference_source"] == "config"


def test_config_accepts_auto_and_keeps_rejecting_a_date_that_is_not_monday(tmp_path):
    path = tmp_path / "supply_plan.json"
    path.write_text(json.dumps({**load_supply_settings(), "reference_date": "auto"}), encoding="utf-8")
    assert load_supply_settings(path)["reference_date"] == "auto"
    path.write_text(json.dumps({**load_supply_settings(), "reference_date": "2026-09-14"}), encoding="utf-8")
    assert load_supply_settings(path)["reference_date"] == "2026-09-14"
    path.write_text(json.dumps({**load_supply_settings(), "reference_date": "2026-09-15"}), encoding="utf-8")
    with pytest.raises(ValueError, match="segunda-feira"):
        load_supply_settings(path)


def test_missing_or_non_monday_first_week_is_an_error(base):
    tuesday = _copy(base)
    _shift(tuesday, "Capacidade_Semanal", ("Semana inicial",), 1)
    with pytest.raises(ReferenceDateError, match=r"^A primeira semana de Capacidade_Semanal \(15/09/2026\) precisa ser uma segunda-feira$"):
        derive_reference_date(tuesday)
    assert _codes(validate_coherence(tuesday, None)) == ["REFERENCE_NOT_MONDAY"]
    empty = _copy(base)
    empty["Capacidade_Semanal"] = empty["Capacidade_Semanal"].iloc[0:0]
    with pytest.raises(ReferenceDateError) as error:
        derive_reference_date(empty)
    assert error.value.code == "REFERENCE_MISSING"
    assert str(error.value) == "Capacidade_Semanal não tem semana válida; a data de planejamento sai da primeira semana"


def test_pipeline_refuses_a_first_week_that_is_not_monday(base, monkeypatch):
    tuesday = _copy(base)
    _shift(tuesday, "Capacidade_Semanal", ("Semana inicial",), 1)
    monkeypatch.setattr(main, "load_source", lambda: tuesday)
    with pytest.raises(ValueError, match="precisa ser uma segunda-feira"):
        main._build_pipeline()


# --- coerência -------------------------------------------------------------------------------------


def test_packaged_base_is_coherent_with_only_the_overdue_order_warning(base):
    result = validate_coherence(base, BASE_REFERENCE)
    assert result["errors"] == []
    assert [issue["code"] for issue in result["warnings"]] == ["OVERDUE_ORDER"]
    overdue = result["warnings"][0]
    assert overdue["count"] == 3 and overdue["more"] == 0 and overdue["sheet"] == "Carteira_Pedidos" and overdue["value"] == "13/09/2026"
    assert overdue["message"].endswith("pedido vencido: confirme se já foi entregue")
    assert {issue_key for issue_key in ("code", "severity", "sheet", "column", "message", "count", "examples", "more", "row", "cell", "value")} <= set(overdue)


def test_sales_ahead_of_the_capacity_reference_are_blocked_with_the_exact_message(base):
    """Critério 2 (P1): vendas até out/26 com a capacidade de 14/09."""
    dataset = _copy(base)
    _repeat_month(dataset, "2026-08-01", "2026-09-01", "2026-10-01")
    result = validate_coherence(dataset, derive_reference_date(dataset))
    sales = next(issue for issue in result["errors"] if issue["sheet"] == "Vendas_24m")
    assert sales["code"] == "SERIES_NOT_CLOSED"
    assert sales["message"] == ("Vendas vão até out/26, mas a data de planejamento é 14/09/2026; "
                                "envie Capacidade_Semanal, Estoque_Atual, Carteira_Pedidos e Ordens_Producao atualizadas")
    sell_in = next(issue for issue in result["errors"] if issue["sheet"] == "Sell_In")
    assert sell_in["message"].startswith("Sell_In vai até out/26, mas a data de planejamento é 14/09/2026")


def test_partial_month_in_the_series_is_blocked(base):
    dataset = _october(base)
    _repeat_month(dataset, "2026-08-01", "2026-10-01")
    errors = validate_coherence(dataset, OCTOBER_REFERENCE)["errors"]
    assert {issue["sheet"] for issue in errors} == {"Vendas_24m", "Sell_In", "Sell_Out"}
    assert errors[0]["message"] == "out/26 ainda não fechou: as abas mensais aceitam só meses anteriores ao da data de planejamento (12/10/2026)"


def test_sales_that_advance_without_a_new_reference_are_blocked(base):
    result = validate_coherence(base, BASE_REFERENCE, {"reference_date": "2026-09-14", "sales_last_month": "2026-07"})
    assert _codes(result) == ["REFERENCE_NOT_ADVANCED"]
    assert result["errors"][0]["message"].startswith("As vendas avançaram de jul/26 para ago/26, mas a data de planejamento não avançou "
                                                     "junto com as vendas (continua 14/09/2026); envie")


def test_sales_beyond_the_reference_with_a_previous_base_report_the_cause_once(base):
    """Critério 2 com a base anterior: a mensagem exata aparece uma vez, sem REFERENCE_NOT_ADVANCED repetindo o texto."""
    dataset = _copy(base)
    _repeat_month(dataset, "2026-08-01", "2026-09-01", "2026-10-01")
    result = validate_coherence(dataset, derive_reference_date(dataset), PREVIOUS, sent_sheets={"Vendas_24m"})
    messages = [issue["message"] for issue in result["errors"]]
    exact = ("Vendas vão até out/26, mas a data de planejamento é 14/09/2026; "
             "envie Capacidade_Semanal, Estoque_Atual, Carteira_Pedidos e Ordens_Producao atualizadas")
    assert messages.count(exact) == 1 and "REFERENCE_NOT_ADVANCED" not in _codes(result)


def test_reference_fixed_in_config_blocks_sales_beyond_it_with_its_own_message(base):
    """Data fixa em config/supply_plan.json: enviar as fotografias não muda a referência, então a mensagem pede para trocá-la."""
    dataset = _october(base)
    result = validate_coherence(dataset, BASE_REFERENCE, PREVIOUS, sent_sheets=SNAPSHOTS | {"Vendas_24m"}, reference_source="config")
    sales = next(issue for issue in result["errors"] if issue["sheet"] == "Vendas_24m")
    assert sales["code"] == "REFERENCE_FIXED_IN_CONFIG"
    assert sales["message"] == ("Vendas vão até set/26, mas a data de planejamento está fixa em 14/09/2026 em config/supply_plan.json; "
                                "troque reference_date para \"auto\" (ou para a nova segunda-feira) antes de aplicar")
    assert "REFERENCE_NOT_ADVANCED" not in _codes(result) and "SNAPSHOTS_REQUIRED" not in _codes(result)
    assert "REFERENCE_FROM_CONFIG" in [issue["code"] for issue in result["warnings"]]


def test_coherent_october_package_has_no_error_and_demand_from_the_reference(base):
    dataset = _october(base)
    reference = derive_reference_date(dataset)
    assert reference == OCTOBER_REFERENCE
    assert validate_coherence(dataset, reference, PREVIOUS, sent_sheets=SNAPSHOTS | {"Vendas_24m", "Sell_In", "Sell_Out"})["errors"] == []
    forecasts = build_official_forecasts(dataset["Vendas_24m"], load_engine_config(main.ENGINE_CONFIG_FILE))
    ok = forecasts[forecasts["status"] == "ok"]
    assert not ok.empty and all(str(months[0])[:7] == "2026-10" for months in ok["forecast_months"])
    orders = _orders_by_sku(dataset["Carteira_Pedidos"])
    active = set(dataset["Produtos"].loc[dataset["Produtos"]["Status"] == "Ativo", "SKU"].astype(str))
    checked = 0
    for row in ok.to_dict("records"):
        if row["sku"] not in active:
            continue
        _, extra = daily_demand(row, orders.get(row["sku"], []), reference, date(2026, 10, 31))
        assert min(extra) == reference and sum(extra.values()) > 0, row["sku"]
        checked += 1
    assert checked > 0


def test_reference_that_advances_requires_the_four_snapshots(base):
    dataset = _october(base)
    result = validate_coherence(dataset, OCTOBER_REFERENCE, PREVIOUS, sent_sheets={"Vendas_24m", "Estoque_Atual", "Carteira_Pedidos", "Capacidade_Semanal"})
    assert _codes(result) == ["SNAPSHOTS_REQUIRED"]
    assert result["errors"][0]["message"] == "A data de planejamento avançou de 14/09/2026 para 12/10/2026; envie também: Ordens_Producao"
    # Fora do upload (sent_sheets=None) a regra não se aplica.
    assert validate_coherence(dataset, OCTOBER_REFERENCE, PREVIOUS)["errors"] == []


def test_open_production_order_finishing_before_the_reference_is_blocked(base):
    dataset = _october(base, shift_ops=False)
    errors = validate_coherence(dataset, OCTOBER_REFERENCE)["errors"]
    assert _codes({"errors": errors}) == ["OPEN_OP_BEFORE_REFERENCE"]
    issue = errors[0]
    ops = dataset["Ordens_Producao"]
    late = ops[pd.to_datetime(ops["Conclusão prevista"]) < pd.Timestamp(OCTOBER_REFERENCE)].sort_values(["Conclusão prevista", "Ordem"])
    first = late.iloc[0]
    assert issue["count"] == len(late) and issue["more"] == max(0, len(late) - 5) and issue["examples"][0]["key"] == first["Ordem"]
    finish = pd.Timestamp(first["Conclusão prevista"])
    assert issue["message"] == (f"{first['Ordem']} ({first['Status']}) tem conclusão prevista em {finish:%d/%m/%Y}, antes da data de planejamento; "
                                "marque como Concluída ou atualize a data")
    # OP concluída não conta.
    dataset["Ordens_Producao"]["Status"] = "Concluída"
    assert validate_coherence(dataset, OCTOBER_REFERENCE)["errors"] == []


def test_gap_and_stock_divergence_are_warnings(base):
    dataset = _copy(base)
    _shift(dataset, "Capacidade_Semanal", ("Semana inicial",), 56)
    _shift(dataset, "Carteira_Pedidos", ("Data prometida",), 56)
    _shift(dataset, "Ordens_Producao", ("Início previsto", "Conclusão prevista"), 56)
    dataset["Produtos"].loc[dataset["Produtos"]["SKU"].isin(["CI-0001", "CI-0002"]), "Estoque atual"] += 1
    result = validate_coherence(dataset, derive_reference_date(dataset))
    assert result["errors"] == []
    warnings = {issue["code"]: issue for issue in result["warnings"]}
    assert warnings["REFERENCE_GAP"]["message"] == "Há meses sem vendas entre ago/26 e a data de planejamento (09/11/2026)"
    divergence = warnings["PRODUCT_STOCK_DIVERGENCE"]
    assert divergence["message"] == "Produtos.Estoque atual difere de Estoque_Atual em 2 SKUs; o cálculo usa Estoque_Atual"
    assert [example["key"] for example in divergence["examples"]] == ["CI-0001", "CI-0002"]


def test_series_last_months_handles_missing_sheet(base):
    dataset = _copy(base)
    del dataset["Sell_Out"]
    assert series_last_months(dataset) == {"Vendas_24m": "2026-08", "Sell_In": "2026-08", "Sell_Out": None}


# --- pipeline e API na base real --------------------------------------------------------------------


def test_api_exposes_one_reference_for_quality_events_and_plans():
    client = TestClient(main.app)
    reference = client.get("/api/data-quality").json()["reference"]
    assert reference == {"reference_date": "2026-09-14", "reference_source": "auto", "sales_last_month": "2026-08",
                         "series_last_months": {"Vendas_24m": "2026-08", "Sell_In": "2026-08", "Sell_Out": "2026-08"}}
    assert client.get("/api/events").json()["reference_date"] == "2026-09-14"
    assert {plan["reference_date"] for plan in main.supply_plans().values()} == {"2026-09-14"}
    assert main.allocation()["reference_date"] == "2026-09-14"
