from pathlib import Path

import pandas as pd
import pytest

from caderno_inteligente.dataset_merge import MONTH_COLUMN, POLICIES, POLICY_TEXT, merge_upload
from caderno_inteligente.dataset_store import SHEET_TABLES, encode_frame
from caderno_inteligente.ingestion import load_workbook

SOURCE = Path("data/source/Base de Dados - Caderno Inteligente.xlsm")


@pytest.fixture(scope="module")
def workbook():
    return load_workbook(SOURCE)


def september(workbook, sheet="Vendas_24m", source_month="2025-09", target="2026-09"):
    frame = workbook[sheet]
    rows = frame[frame[MONTH_COLUMN[sheet]] == source_month].copy()
    rows[MONTH_COLUMN[sheet]] = target
    return rows.reset_index(drop=True)


def report_of(reports, sheet):
    [report] = [report for report in reports if report["sheet"] == sheet]
    return report


def test_every_sheet_has_a_policy_and_the_text_is_the_single_rule():
    assert set(POLICIES) == set(SHEET_TABLES)
    assert {POLICIES[sheet] for sheet in MONTH_COLUMN} == {"serie_mensal"}
    assert "só os meses enviados" in POLICY_TEXT


def test_new_month_is_appended_and_history_stays_identical(workbook):
    """Critério 4: só Vendas_24m 2026-09 enviada → 25 meses e 2024-09 a 2026-08 iguais às originais."""
    merged, reports, issues = merge_upload(workbook, {"Vendas_24m": september(workbook)})
    assert issues == []
    sales = merged["Vendas_24m"]
    assert sales["Mês"].nunique() == 25 and sales["Mês"].iloc[-1] == "2026-09"
    original = workbook["Vendas_24m"]
    history = sales.iloc[: len(original)]
    assert encode_frame(history.reset_index(drop=True))[1] == encode_frame(original)[1]
    assert list(sales.dtypes.astype(str)) == list(original.dtypes.astype(str))
    report = report_of(reports, "Vendas_24m")
    assert (report["status"], report["months_added"], report["months_replaced"]) == ("mesclada", ["2026-09"], [])
    assert (report["rows_before"], report["rows_received"], report["rows_after"]) == (9600, 400, 10000)
    assert report["keys_added"] == 400 and report["keys_removed"] == 0 and len(report["keys_added_examples"]) == 5


def test_resent_month_is_replaced_without_duplicating_keys(workbook):
    """Critério 5: reenviar 2026-09 com valores diferentes substitui o mês."""
    first, _, _ = merge_upload(workbook, {"Vendas_24m": september(workbook)})
    resent = september(workbook)
    resent["Quantidade faturada"] = resent["Quantidade faturada"] + 7
    merged, reports, issues = merge_upload(first, {"Vendas_24m": resent})
    assert issues == []
    sales = merged["Vendas_24m"]
    assert len(sales) == 10000
    assert not sales.duplicated(["Mês", "SKU", "Cliente/Canal"]).any()
    new = sales[sales["Mês"] == "2026-09"].reset_index(drop=True)
    assert new["Quantidade faturada"].tolist() == resent["Quantidade faturada"].tolist()
    report = report_of(reports, "Vendas_24m")
    assert (report["months_added"], report["months_replaced"], report["keys_added"], report["keys_removed"]) == ([], ["2026-09"], 0, 0)


def test_month_sent_as_a_date_takes_the_format_of_the_base(workbook):
    sent = september(workbook)
    sent["Mês"] = pd.Timestamp("2026-09-01")
    merged, _, issues = merge_upload(workbook, {"Vendas_24m": sent})
    assert issues == []
    assert merged["Vendas_24m"]["Mês"].iloc[-1] == "2026-09"
    assert merged["Vendas_24m"]["Mês"].nunique() == 25


def test_datetime_month_column_receives_the_first_day_of_the_month():
    current = {"Sell_In": pd.DataFrame({"Mês": pd.to_datetime(["2026-07-01", "2026-08-01"]), "Cliente": ["P1", "P1"],
                                        "SKU": ["A", "A"], "Quantidade enviada": [10, 20]})}
    sent = pd.DataFrame({"Mês": ["2026-09", "2026-08"], "Cliente": ["P1", "P1"], "SKU": ["A", "A"], "Quantidade enviada": [30, 25]})
    merged, reports, _ = merge_upload(current, {"Sell_In": sent})
    frame = merged["Sell_In"]
    assert frame["Mês"].dtype == "datetime64[ns]"
    assert frame["Mês"].dt.strftime("%Y-%m-%d").tolist() == ["2026-07-01", "2026-08-01", "2026-09-01"]
    assert frame["Quantidade enviada"].tolist() == [10, 25, 30]
    assert report_of(reports, "Sell_In")["months_replaced"] == ["2026-08"]


def test_snapshot_replaces_and_missing_sheet_stays_the_same(workbook):
    stock = workbook["Estoque_Atual"].head(10).copy()
    stock["Estoque atual"] = 1
    merged, reports, issues = merge_upload(workbook, {"Estoque_Atual": stock})
    assert issues == []
    pd.testing.assert_frame_equal(merged["Estoque_Atual"], stock.reset_index(drop=True))
    report = report_of(reports, "Estoque_Atual")
    assert (report["status"], report["rows_after"], report["keys_removed"], report["keys_added"]) == ("substituida", 10, 40, 0)
    for sheet, frame in workbook.items():
        if sheet != "Estoque_Atual":
            assert merged[sheet] is frame
            assert report_of(reports, sheet)["status"] == "mantida" and report_of(reports, sheet)["rows_received"] is None


def test_columns_follow_the_base_extra_columns_are_ignored_and_missing_columns_block(workbook):
    stock = workbook["Estoque_Atual"].copy()
    reordered = stock[list(reversed(stock.columns))].assign(Observação="x")
    merged, _, issues = merge_upload(workbook, {"Estoque_Atual": reordered})
    assert list(merged["Estoque_Atual"].columns) == list(stock.columns)
    assert [(issue["code"], issue["severity"], issue["column"]) for issue in issues] == [("EXTRA_COLUMNS_IGNORED", "warning", "Observação")]

    merged, reports, issues = merge_upload(workbook, {"Estoque_Atual": stock.drop(columns=["Local"])})
    assert [(issue["code"], issue["severity"], issue["sheet"]) for issue in issues] == [("MISSING_COLUMNS", "error", "Estoque_Atual")]
    assert "Local" in issues[0]["message"] and issues[0]["examples"] == [] and issues[0]["more"] == 0
    assert merged["Estoque_Atual"] is workbook["Estoque_Atual"]
    assert report_of(reports, "Estoque_Atual")["status"] == "mantida"


def test_empty_sheet_is_an_error_except_open_orders_and_production_orders(workbook):
    empty_stock = workbook["Estoque_Atual"].iloc[0:0]
    _, _, issues = merge_upload(workbook, {"Estoque_Atual": empty_stock})
    assert [(issue["code"], issue["severity"]) for issue in issues] == [("EMPTY_SHEET", "error")]

    empty_orders = workbook["Carteira_Pedidos"].iloc[0:0]
    merged, reports, issues = merge_upload(workbook, {"Carteira_Pedidos": empty_orders})
    assert [(issue["code"], issue["severity"]) for issue in issues] == [("EMPTY_SHEET", "warning")]
    assert "nenhum pedido aberto" in issues[0]["message"]
    assert merged["Carteira_Pedidos"].empty and report_of(reports, "Carteira_Pedidos")["status"] == "substituida"
