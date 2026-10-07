"""Etapa 15.5: estoque acumulando no parceiro, excesso estável e ligação com a OP do SKU."""
from __future__ import annotations

import pandas as pd
import pytest
from fastapi.testclient import TestClient

import backend.main as main
from caderno_inteligente.action_labels import DEFAULT_SETTINGS, label_commercial_row
from caderno_inteligente.partner_insights import DEFAULT_THRESHOLDS, build_partner_insights
from caderno_inteligente.supply_plan import attach_partner_buildup

MONTHS = [f"2026-{month:02d}" for month in range(1, 9)]


def _data(sell_in, sell_out, start_stock, broken_month=None):
    """Um parceiro e um SKU; o estoque segue a conta estoque anterior + sell-in − sell-out (salvo `broken_month`)."""
    stock, rows_in, rows_out = start_stock, [], []
    for index, (month, received, sold) in enumerate(zip(MONTHS, sell_in, sell_out)):
        stock = stock + received - sold + (500 if month == broken_month else 0)
        rows_in.append({"Mês": month, "Cliente": "KA-T", "SKU": "X", "Quantidade enviada": received})
        rows_out.append({"Mês": month, "Cliente": "KA-T", "SKU": "X", "Quantidade vendida": sold, "Estoque estimado cliente": stock,
                         "Natureza do dado": "Observado pelo parceiro"})
    return {
        "Sell_In": pd.DataFrame(rows_in), "Sell_Out": pd.DataFrame(rows_out),
        "Parceiros_Canais": pd.DataFrame([{"Código": "KA-T", "Nome fictício": "Parceiro", "Tipo": "Parceiro varejista", "Região": "Sul", "Canal principal": "Lojas"}]),
        "Produtos": pd.DataFrame([{"SKU": "X", "Produto": "Produto X"}]),
        "Carteira_Pedidos": pd.DataFrame(columns=["Pedido", "SKU", "Cliente/Canal", "Quantidade", "Data prometida", "Status"]),
    }


def _row(data):
    return build_partner_insights(data, dict(DEFAULT_THRESHOLDS))["items"][0]


def test_partner_receiving_more_than_it_sells_is_stock_buildup_not_data_divergence():
    row = _row(_data([150] * 8, [70] * 8, 200))
    codes = {signal["code"] for signal in row["signals"]}
    assert "PARTNER_STOCK_BUILDUP" in codes and "SELLIN_SELLOUT_DIVERGENCE" not in codes
    assert row["action"] == "conter_reposicao" and row["stock_identity_consistent"] is True
    assert row["sell_through_window"] == pytest.approx(70 / 150) and row["stock_growth"] > 0.3
    label = label_commercial_row(row, DEFAULT_SETTINGS)
    assert label["code"] == "investigar" and "Não repor" in label["reason"]


def test_when_the_stock_account_does_not_close_the_gap_is_still_a_data_divergence():
    row = _row(_data([150] * 8, [70] * 8, 200, broken_month="2026-07"))
    codes = {signal["code"] for signal in row["signals"]}
    assert row["stock_identity_consistent"] is False
    assert "SELLIN_SELLOUT_DIVERGENCE" in codes and row["action"] == "investigar_divergencia"


def test_high_but_stable_stock_is_monitored_without_the_old_low_turnover_lock():
    row = _row(_data([100] * 8, [100] * 8, 600))  # 600 un. para 100/mês: 180 dias, giro acima dos antigos 30 un./mês
    codes = {signal["code"] for signal in row["signals"]}
    assert "PARTNER_EXCESS_RISK" in codes and "PARTNER_STOCK_BUILDUP" not in codes
    assert row["action"] == "monitorar_excesso_parceiro"
    assert label_commercial_row(row, DEFAULT_SETTINGS)["code"] == "monitorar"


def test_healthy_pair_keeps_its_reposition_signal():
    row = _row(_data([100] * 8, [100] * 8, 50))
    assert row["action"] == "avaliar_reposicao"
    assert "low_monthly_sell_out" not in DEFAULT_THRESHOLDS


def test_buildup_reaches_the_sku_and_the_op_to_review():
    plans = {"X": {"signals": [], "op_adjustments": [{"order": "OP-1", "adjustment": "reduzir", "reason": "Excesso projetado."}]}, "Y": {"signals": [], "op_adjustments": []}}
    attach_partner_buildup(plans, [_row(_data([150] * 8, [70] * 8, 200))])
    assert "PARTNER_STOCK_BUILDUP" in plans["X"]["signals"] and plans["X"]["partner_buildup"][0]["partner"] == "KA-T"
    assert "Estoque acumulando no parceiro: KA-T vendeu" in plans["X"]["op_adjustments"][0]["reason"]
    assert plans["Y"]["signals"] == [] and plans["Y"]["partner_buildup"] == []


# ------------------------------------------------------------------------------------------ base real


@pytest.fixture(scope="module")
def client():
    return TestClient(main.app)


def test_ka02_ci0009_is_the_buildup_case_and_ci0009_enters_the_queue(client):
    rows = client.get("/api/partners/KA-02/skus?limit=50").json()["items"]
    row = next(item for item in rows if item["sku"] == "CI-0009")
    assert row["action"] == "conter_reposicao" and row["challenge_action"]["code"] == "investigar"
    assert row["stock_identity_consistent"] is True and row["sell_through_window"] < 0.9
    detail = client.get("/api/priorities/CI-0009").json()
    assert {"PARTNER_STOCK_BUILDUP", "PROJECTED_EXCESS"} <= {item["code"] for item in detail["issues"]}
    assert detail["priority"] and detail["operational_recommendation"]["action"] == "rever_op"
    reduction = next(item for item in detail["operational_recommendation"]["op_adjustments"] if item["order"] == "OP-7808")
    assert "KA-02" in reduction["reason"]
