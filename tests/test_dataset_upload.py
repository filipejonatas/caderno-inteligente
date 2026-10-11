"""Prévia do upload da planilha (U1A, serviço): validação com endereço, mescla, coerência com a referência e avisos."""
from pathlib import Path

import pytest

from caderno_inteligente.dataset_store import Database, DatasetStore, sku_rows
from caderno_inteligente.dataset_upload import prepare_upload
from caderno_inteligente.ingestion import load_workbook, read_workbook_bytes
from caderno_inteligente.upload_safety import UploadRejected, load_upload_settings
from caderno_inteligente.workbook_writer import write_workbook

SOURCE = Path("data/source/Base de Dados - Caderno Inteligente.xlsm")
EXAMPLE = Path("docs/exemplos/atualizacao-2026-10.xlsx")
ORIGINAL_STATE = {"version": 1, "reference_date": "2026-09-14", "sales_last_month": "2026-08"}
AFTER_EXAMPLE_STATE = {"version": 2, "reference_date": "2026-10-12", "sales_last_month": "2026-09"}


@pytest.fixture(scope="module")
def base():
    return load_workbook(SOURCE)


@pytest.fixture(scope="module")
def settings():
    return load_upload_settings()


def _run(content, current, settings, *, state=ORIGINAL_STATE, edited=(), engine=None, filename="envio.xlsx", inactive=None, supply=None):
    return prepare_upload(content, filename, current=current, state=state, settings=settings,
                          engine=engine or (lambda dataset: {"queue_size": len(dataset["Produtos"])}),
                          current_engine={"queue_size": 0}, edited_skus=set(edited), inactive_skus=inactive, supply_settings=supply)


def _codes(items):
    return {item["code"] for item in items}


def test_sales_ahead_of_the_reference_are_blocked_with_the_exact_message(base, settings):
    """Critério 2: vendas até out/26 com a capacidade de 14/09 → não aplica, com a mensagem do contrato."""
    sales = base["Vendas_24m"]
    sent = sales[sales["Mês"].isin(["2025-09", "2025-10"])].copy()
    sent["Mês"] = sent["Mês"].map({"2025-09": "2026-09", "2025-10": "2026-10"})
    preview, merged = _run(write_workbook({"Vendas_24m": sent}, title="teste"), base, settings)
    assert preview["can_apply"] is False and merged is None
    messages = [item["message"] for item in preview["errors"]]
    assert ("Vendas vão até out/26, mas a data de planejamento é 14/09/2026; envie Capacidade_Semanal, Estoque_Atual, "
            "Carteira_Pedidos e Ordens_Producao atualizadas") in messages
    assert sum(message.startswith("Vendas vão até out/26") for message in messages) == 1
    assert "REFERENCE_NOT_ADVANCED" not in _codes(preview["errors"])
    assert preview["engine"]["after"] is None and preview["engine"]["error"]
    assert preview["requires_human_review"] is True and preview["limitations"]


def test_example_package_can_be_applied_and_advances_the_reference(base, settings):
    """Critério 3 (serviço): o pacote de exemplo passa, com referência 12/10/2026, e o motor roda no conjunto mesclado."""
    preview, merged = _run(EXAMPLE.read_bytes(), base, settings, filename="atualizacao-2026-10.xlsx")
    assert preview["can_apply"] is True and preview["errors"] == []
    assert preview["reference"] == {"before": "2026-09-14", "after": "2026-10-12", "advanced": True,
                                    "sales_last_month_before": "2026-08", "sales_last_month_after": "2026-09"}
    assert {"EXAMPLE_FILE", "PRODUCT_STOCK_DIVERGENCE"} <= _codes(preview["warnings"])
    assert preview["file"]["example"] is True and preview["file"]["has_macro"] is False
    assert preview["engine"] == {"before": {"queue_size": 0}, "after": {"queue_size": 50}, "error": None}
    assert preview["ignored_sheets"] == ["LEIA_ME"] and preview["expected_version"] == 1
    sheets = {report["sheet"]: report for report in preview["sheets"]}
    assert sheets["Vendas_24m"]["status"] == "mesclada" and sheets["Vendas_24m"]["header_row"] == 3
    assert sheets["Produtos"]["status"] == "mantida" and sheets["Produtos"]["header_row"] is None
    assert merged is not None and set(merged) == set(base)


def test_incremental_month_keeps_history_and_resent_month_is_replaced(base, settings):
    """Critérios 4 e 5: 25 meses com o histórico idêntico; reenviar setembro substitui o mês sem duplicar."""
    _, merged = _run(EXAMPLE.read_bytes(), base, settings)
    sales = merged["Vendas_24m"]
    assert sales["Mês"].nunique() == 25 and len(sales) == len(base["Vendas_24m"]) + 400
    history = sales[sales["Mês"] != "2026-09"].reset_index(drop=True)
    assert history.equals(base["Vendas_24m"])

    package = read_workbook_bytes(EXAMPLE.read_bytes())["sheets"]
    package["Vendas_24m"]["Quantidade faturada"] += 7
    resent = write_workbook(package, title="reenvio")
    preview, again = _run(resent, merged, settings, state=AFTER_EXAMPLE_STATE)
    assert preview["can_apply"] is True, preview["errors"]
    report = next(item for item in preview["sheets"] if item["sheet"] == "Vendas_24m")
    assert (report["months_added"], report["months_replaced"]) == ([], ["2026-09"])
    sales_again = again["Vendas_24m"]
    assert len(sales_again) == len(sales) and sales_again["Mês"].nunique() == 25
    new = sales_again[sales_again["Mês"] == "2026-09"]["Quantidade faturada"].sum()
    old = sales[sales["Mês"] == "2026-09"]["Quantidade faturada"].sum()
    assert new == old + 7 * 400


def test_invalid_cell_is_reported_with_its_address(base, settings):
    """Critério 7: texto em coluna numérica vira erro com linha e célula do arquivo enviado, sem exceção."""
    stock = base["Estoque_Atual"].copy()
    stock["Estoque atual"] = stock["Estoque atual"].astype(object)
    stock.loc[6, "Estoque atual"] = "abc"
    preview, merged = _run(write_workbook({"Estoque_Atual": stock}, title="teste"), base, settings)
    assert preview["can_apply"] is False and merged is None
    [error] = [item for item in preview["errors"] if item["code"] == "INVALID_NUMBER"]
    column = list(stock.columns).index("Estoque atual")
    assert error["sheet"] == "Estoque_Atual" and error["row"] == 10 and error["cell"] == f"{'ABCDEFGHIJ'[column]}10"
    assert error["value"] == "abc" and error["count"] == 1 and error["more"] == 0


def test_registry_override_lists_only_the_edited_skus_that_change(tmp_path, base, settings):
    """D10: SKU cadastrado pela tela cuja linha muda no envio gera aviso; o que não muda fica fora."""
    store = DatasetStore(Database(sqlite_path=tmp_path / "dataset.db"))
    store.import_dataset(base)
    fields = {"produto": "Caderno editado", "familia": "Clássico", "curva_abc": "B", "lead_time_dias": 12, "lote_minimo": 200,
              "estoque_atual": 300, "estoque_seguranca_dias": 7, "venda_media_dia": 10.0}
    store.save_sku("CI-0001", sku_rows("CI-0001", fields, store.sku_state("CI-0001")[1]), "pcp@exemplo.com", create=False)
    assert store.edited_skus() == {"CI-0001"}
    current = store.load_dataset(include_inactive=True)
    stock = current["Estoque_Atual"].copy()
    stock.loc[stock["SKU"] == "CI-0001", "Estoque atual"] = 999
    preview, _ = _run(write_workbook({"Estoque_Atual": stock}, title="teste"), current, settings, edited=store.edited_skus())
    assert preview["registry_overrides"] == {"count": 1, "skus": ["CI-0001"]}
    [warning] = [item for item in preview["warnings"] if item["code"] == "REGISTRY_OVERRIDE"]
    assert warning["examples"][0]["key"] == "CI-0001"
    unchanged, _ = _run(write_workbook({"Estoque_Atual": current["Estoque_Atual"]}, title="teste"), current, settings, edited={"CI-0001"})
    assert unchanged["registry_overrides"] == {"count": 0, "skus": []}


def test_too_many_rows_missing_header_and_engine_failure_are_errors_not_exceptions(base, settings):
    small = {**settings, "max_rows_per_sheet": 10}
    preview, _ = _run(write_workbook({"Estoque_Atual": base["Estoque_Atual"]}, title="teste"), base, small)
    assert "TOO_MANY_ROWS" in _codes(preview["errors"])

    broken = base["Lead_Times"].rename(columns={"Lead time dias": "Prazo"})
    preview, _ = _run(write_workbook({"Lead_Times": broken}, title="teste"), base, settings)
    [error] = [item for item in preview["errors"] if item["code"] == "MISSING_COLUMNS"]
    assert error["sheet"] == "Lead_Times" and "Lead time dias" in error["message"] and error["row"] is None

    def failing(_dataset):
        raise RuntimeError("falha interna")

    preview, merged = _run(EXAMPLE.read_bytes(), base, settings, engine=failing)
    assert preview["can_apply"] is False and merged is None and "ENGINE_FAILED" in _codes(preview["errors"])
    assert "falha interna" not in preview["engine"]["error"]


def test_file_rejections_propagate_to_the_caller(base, settings):
    with pytest.raises(UploadRejected) as error:
        _run(b"SKU;Estoque\nCI-0001;10\n", base, settings, filename="dados.xlsx")
    assert (error.value.status, error.value.code) == (422, "NOT_XLSX")


def test_invalid_number_message_cites_the_first_address(base, settings):
    stock = base["Estoque_Atual"].copy()
    stock["Estoque atual"] = stock["Estoque atual"].astype(object)
    stock.loc[[0, 1, 2], "Estoque atual"] = ["muito", "pouco", "x"]
    preview, _ = _run(write_workbook({"Estoque_Atual": stock}, title="teste"), base, settings)
    error = next(item for item in preview["errors"] if item["code"] == "INVALID_NUMBER")
    assert error["message"] == f"Estoque_Atual!{error['cell']}: 'muito' não é número; e mais 2"


def test_removing_an_inactive_sku_from_produtos_warns(base, settings):
    products = base["Produtos"][base["Produtos"]["SKU"] != "CI-0050"]
    preview, _ = _run(write_workbook({"Produtos": products}, title="teste"), base, settings, inactive={"CI-0050"})
    removed = next(item for item in preview["warnings"] if item["code"] == "INACTIVE_SKU_REMOVED")
    assert removed["count"] == 1 and removed["examples"][0]["key"] == "CI-0050"
    kept, _ = _run(write_workbook({"Produtos": base["Produtos"]}, title="teste"), base, settings, inactive={"CI-0050"})
    assert "INACTIVE_SKU_REMOVED" not in _codes(kept["warnings"])


def test_reference_fixed_in_config_is_the_one_used_by_the_preview(base, settings):
    """Data fixa em config/supply_plan.json: a prévia usa a mesma referência do motor e bloqueia vendas que passam dela."""
    fixed = {"reference_date": "2026-09-14"}
    preview, merged = _run(EXAMPLE.read_bytes(), base, settings, supply=fixed, filename="atualizacao-2026-10.xlsx")
    assert merged is None and preview["reference"]["after"] == "2026-09-14" and preview["reference"]["advanced"] is False
    blocked = next(item for item in preview["errors"] if item["code"] == "REFERENCE_FIXED_IN_CONFIG")
    assert "config/supply_plan.json" in blocked["message"] and blocked["sheet"] == "Vendas_24m"
    assert "REFERENCE_FROM_CONFIG" in _codes(preview["warnings"])
