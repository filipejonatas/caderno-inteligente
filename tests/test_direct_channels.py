import json
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from caderno_inteligente.direct_channels import DEFAULT_SETTINGS, build_channel_findings, build_direct_channels, load_direct_channel_settings

ROOT = Path(__file__).resolve().parents[1]
MONTHS = pd.period_range("2024-09", "2026-08", freq="M")


def _sales(rows):
    """rows: (canal, sku, função mês→unidades, preço). Mês com unidades None não gera linha."""
    out = []
    for channel, sku, units, price in rows:
        for period in MONTHS:
            value = units(period)
            if value is not None:
                out.append({"Mês": period.to_timestamp(), "SKU": sku, "Cliente/Canal": channel, "Quantidade faturada": value, "Preço unitário (R$)": price, "Valor faturado (R$)": value * price})
    return pd.DataFrame(out)


def _flat(value):
    return lambda period: value


def _data(sales, *, partners=None, orders=None, sell_out=None, sell_in=None, products=None):
    return {
        "Vendas_24m": sales,
        "Produtos": products if products is not None else pd.DataFrame({"SKU": ["A", "B", "C"], "Produto": ["Pa", "Pb", "Pc"], "Família": "F", "Status": ["Ativo", "Ativo", "Ativo"]}),
        "Parceiros_Canais": partners if partners is not None else pd.DataFrame({
            "Código": ["D1", "KA-1"], "Nome fictício": ["Direto 1", "KA"], "Tipo": ["Canal direto", "Parceiro varejista"], "Região": ["Nacional", "Sul"],
            "Cobertura de sell-out": ["Completo", "Parcial"], "SKUs com sell-out": [3, 3]}),
        "Carteira_Pedidos": orders if orders is not None else pd.DataFrame({"Pedido": [], "SKU": [], "Cliente/Canal": [], "Quantidade": [], "Data prometida": [], "Status": []}),
        "Sell_Out": sell_out if sell_out is not None else pd.DataFrame({"Mês": [], "Cliente": [], "SKU": [], "Quantidade vendida": []}),
        "Sell_In": sell_in if sell_in is not None else pd.DataFrame({"Mês": [], "Cliente": [], "SKU": [], "Quantidade enviada": []}),
    }


def _rows(result, channel="D1"):
    return {row["sku"]: row for row in result["rows"][channel]}


def _basic():
    # A: estável nos dois canais; B: parou de vender em D1 em 2026-04; C: nunca vendeu em D1 (só no KA).
    return _sales([
        ("D1", "A", _flat(100), 10.0),
        ("D1", "B", lambda p: 50 if p <= pd.Period("2026-04") else None, 20.0),
        ("KA-1", "A", _flat(40), 10.0), ("KA-1", "C", _flat(30), 5.0),
    ])


# --- resumo por canal --------------------------------------------------------

def test_only_direct_channels_are_analysed_and_totals_include_partners():
    result = build_direct_channels(_data(_basic()))
    assert [c["code"] for c in result["channels"]] == ["D1"] and list(result["rows"]) == ["D1"]
    channel = result["channels"][0]
    own = 100 * 10.0 * 24 + 50 * 20.0 * 20
    total = own + 40 * 10.0 * 24 + 30 * 5.0 * 24
    assert channel["revenue_24m"] == pytest.approx(own) and result["totals"]["total_revenue_24m"] == pytest.approx(total)
    assert channel["share_of_revenue"] == pytest.approx(own / total, abs=1e-4) and result["totals"]["direct_share_of_revenue"] == pytest.approx(own / total, abs=1e-4)
    assert channel["observed_skus"] == 2 and channel["catalog_skus"] == 3
    assert channel["monthly"]["months"][0] == "2024-09-01" and len(channel["monthly"]["revenue"]) == 24


def test_channel_trend_and_concentration_use_observed_billing():
    sales = _sales([("D1", "A", lambda p: 100 if p < pd.Period("2026-06") else 130, 10.0), ("D1", "B", _flat(100), 10.0)])
    channel = build_direct_channels(_data(sales))["channels"][0]
    assert channel["trend"] == "crescente" and channel["change_ratio"] == pytest.approx((230 - 200) / 200 * 1.0 * 1.0 * 1.0, abs=0.01)
    assert channel["revenue_recent"] == pytest.approx(3 * 230 * 10.0) and channel["concentration"]["top5_share"] == 1.0
    assert channel["concentration"]["skus_for_target_share"] == 2


# --- sinais por SKU ----------------------------------------------------------

def test_sku_never_sold_is_not_sold_with_null_values_never_zero():
    row = _rows(build_direct_channels(_data(_basic())))["C"]
    assert row["signals"] == ["NOT_SOLD"] and row["units_24m"] is None and row["revenue_24m"] is None and row["share_in_channel"] is None
    assert row["rank"] is None and row["trend"] == "indeterminada"
    assert row["suggestion"]["code"] == "avaliar_ampliacao_mix" and row["suggestion"]["requires_human_review"] is True


def test_discontinuing_product_without_sales_is_not_a_mix_candidate():
    products = pd.DataFrame({"SKU": ["A", "B", "C"], "Produto": "P", "Família": "F", "Status": ["Ativo", "Ativo", "Descontinuando"]})
    row = _rows(build_direct_channels(_data(_basic(), products=products)))["C"]
    assert row["suggestion"]["code"] == "monitorar_saida_de_linha"


def test_sku_that_stopped_selling_is_a_reactivation_candidate():
    row = _rows(build_direct_channels(_data(_basic())))["B"]
    assert "STOPPED" in row["signals"] and row["last_month"] == "2026-04-01" and row["months_sold"] == 20
    assert row["suggestion"]["code"] == "avaliar_reativacao" and "2026-04-01" in row["suggestion"]["reason"]


def test_growing_and_declining_follow_the_neutral_band():
    sales = _sales([
        ("D1", "A", lambda p: 100 if p < pd.Period("2026-06") else 120, 10.0),
        ("D1", "B", lambda p: 100 if p < pd.Period("2026-06") else 80, 10.0),
        ("D1", "C", lambda p: 100 if p < pd.Period("2026-06") else 105, 10.0),
    ])
    rows = _rows(build_direct_channels(_data(sales)))
    assert rows["A"]["trend"] == "crescente" and rows["A"]["suggestion"]["code"] == "acompanhar_crescimento"
    assert rows["B"]["trend"] == "decrescente" and rows["B"]["suggestion"]["code"] == "investigar_queda"
    assert rows["C"]["trend"] == "estável" and rows["C"]["suggestion"]["code"] == "sem_acao_necessaria"


def test_rows_are_ordered_by_revenue_rank_with_unsold_skus_last():
    sales = _sales([("D1", "B", _flat(100), 10.0), ("D1", "A", _flat(10), 10.0)])
    order = [row["sku"] for row in build_direct_channels(_data(sales))["rows"]["D1"]]
    assert order == ["B", "A", "C"]


def test_ranking_and_cumulative_share_close_at_one_and_yoy_compares_same_months():
    sales = _sales([("D1", "A", _flat(100), 10.0), ("D1", "B", _flat(50), 10.0), ("D1", "C", _flat(25), 10.0)])
    rows = _rows(build_direct_channels(_data(sales)))
    assert [rows[s]["rank"] for s in "ABC"] == [1, 2, 3]
    assert rows["C"]["cumulative_share"] == pytest.approx(1.0, abs=1e-3) and rows["A"]["share_in_channel"] == pytest.approx(100 / 175, abs=1e-3)
    assert rows["A"]["yoy_ratio"] == 0.0


def test_open_backlog_is_scoped_to_the_channel_and_ignores_closed_orders():
    orders = pd.DataFrame({
        "Pedido": ["P1", "P2", "P3", "P4"], "SKU": ["A", "A", "A", "B"], "Cliente/Canal": ["D1", "D1", "D1", "KA-1"],
        "Quantidade": [100, 40, 7, 999], "Data prometida": pd.Timestamp("2026-09-20"), "Status": ["Confirmado", "Cancelado", "Entregue", "Confirmado"]})
    result = build_direct_channels(_data(_basic(), orders=orders))
    row = _rows(result)["A"]
    assert row["backlog_open_quantity"] == 100.0 and row["backlog_open_orders"] == 1 and "OPEN_BACKLOG" in row["signals"]
    assert _rows(result)["B"]["backlog_open_orders"] == 0
    assert result["channels"][0]["backlog"] == {"open_orders": 1, "open_quantity": 100.0, "skus": 1}


def test_partner_comparison_is_context_not_mixed_into_direct_values():
    row = _rows(build_direct_channels(_data(_basic())))["A"]
    assert row["partners_units_recent"] == 120.0 and row["units_recent"] == 300.0
    assert row["direct_share_of_sku_recent"] == pytest.approx(300 / 420, abs=1e-3)


def test_no_stock_by_channel_is_declared_absent():
    result = build_direct_channels(_data(_basic()))
    assert result["field_nature"]["stock"]["nature"] == "ausente"
    assert not any("stock" in key for key in result["channels"][0]) and not any("stock" in key for key in result["rows"]["D1"][0])


# --- achados de qualidade ----------------------------------------------------

def test_declared_complete_coverage_without_sell_out_rows_is_flagged():
    findings = {f["code"]: f for f in build_channel_findings(_data(_basic()))}
    finding = findings["DIRECT_COVERAGE_NOT_IN_SELL_OUT"]
    assert finding["affects"] == ["D1"] and finding["evidence"][0]["sell_out_rows"] == 0 and finding["evidence"][0]["billing_observed_skus"] == 2
    assert "Vendas_24m" in finding["treatment"]
    with_rows = pd.DataFrame({"Mês": [pd.Timestamp("2026-08-01")], "Cliente": ["D1"], "SKU": ["A"], "Quantidade vendida": [5]})
    assert "DIRECT_COVERAGE_NOT_IN_SELL_OUT" not in {f["code"] for f in build_channel_findings(_data(_basic(), sell_out=with_rows))}


def test_sell_in_that_differs_from_billing_is_flagged_but_matching_data_is_not():
    sales = _sales([("KA-1", "A", _flat(40), 10.0), ("D1", "A", _flat(10), 10.0)])
    months = list(MONTHS[-12:])
    differing = pd.DataFrame({"Mês": [m.to_timestamp() for m in months], "Cliente": "KA-1", "SKU": "A", "Quantidade enviada": 100})
    finding = next(f for f in build_channel_findings(_data(sales, sell_in=differing)) if f["code"] == "KA_SELL_IN_DIFFERS_FROM_BILLING")
    assert finding["evidence"]["overlapping_pairs"] == 12 and finding["evidence"]["equal_pairs"] == 0
    assert finding["evidence"]["median_sell_in_over_billing"] == 2.5 and finding["evidence"]["sell_in_months"] == 12 and finding["evidence"]["billing_months"] == 24
    matching = pd.DataFrame({"Mês": [m.to_timestamp() for m in months], "Cliente": "KA-1", "SKU": "A", "Quantidade enviada": 40})
    assert "KA_SELL_IN_DIFFERS_FROM_BILLING" not in {f["code"] for f in build_channel_findings(_data(sales, sell_in=matching))}


# --- configuração ------------------------------------------------------------

def test_shipped_settings_load_and_invalid_values_are_rejected(tmp_path):
    assert load_direct_channel_settings(ROOT / "config/direct_channel_thresholds.json") == DEFAULT_SETTINGS
    for bad in ({"x": 1}, {"trend_months": 0}, {"trend_months": 2.5}, {"trend_band": 1}, {"inactive_months": 13}, {"concentration_share": 0}):
        path = tmp_path / "bad.json"
        path.write_text(json.dumps(bad), encoding="utf-8")
        with pytest.raises(ValueError):
            load_direct_channel_settings(path)


# --- API sobre a base real ---------------------------------------------------

@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_api_direct_channels_summary_matches_billing_totals(client):
    body = client.get("/api/direct-channels").json()
    assert [c["code"] for c in body["channels"]] == ["E-commerce", "Marketplace", "Loja própria"] and "rows" not in body
    assert body["totals"]["direct_share_of_revenue"] == pytest.approx(0.6821, abs=1e-3)
    assert body["field_nature"]["stock"]["nature"] == "ausente" and body["limitations"]
    assert sum(c["revenue_24m"] for c in body["channels"]) == pytest.approx(body["totals"]["direct_revenue_24m"], abs=1)
    assert all(c["sell_out_rows"] == 0 and c["declared_coverage"] == "Completo" and c["observed_skus"] == 50 for c in body["channels"])
    assert {f["code"] for f in body["findings"]} == {"DIRECT_COVERAGE_NOT_IN_SELL_OUT", "KA_SELL_IN_DIFFERS_FROM_BILLING"}


def test_api_channel_detail_filters_and_validation(client):
    detail = client.get("/api/direct-channels/Loja%20pr%C3%B3pria").json()
    assert detail["channel"]["code"] == "Loja própria" and detail["total"] == 50 == len(detail["items"])
    assert all(item["suggestion"]["requires_human_review"] for item in detail["items"])
    declining = client.get("/api/direct-channels/E-commerce?signal=DECLINING").json()
    assert 0 < declining["total"] < 50 and all("DECLINING" in item["signals"] for item in declining["items"])
    one = client.get("/api/direct-channels/E-commerce?search=ci-0014").json()
    assert [item["sku"] for item in one["items"]] == ["CI-0014"]
    ranks = [item["rank"] for item in detail["items"]]
    assert ranks == sorted(ranks)
    assert client.get("/api/direct-channels/Inexistente").status_code == 404
    assert client.get("/api/direct-channels/E-commerce?signal=XYZ").status_code == 422
    assert client.get("/api/direct-channels/E-commerce?suggestion=XYZ").status_code == 422
    assert client.get("/api/direct-channels/KA-01").status_code == 404  # parceiro B2B não é canal direto


def test_api_channel_billing_plus_partners_equals_total_sales(client):
    body = client.get("/api/direct-channels").json()
    total = body["totals"]["total_revenue_24m"]
    assert body["totals"]["direct_revenue_24m"] < total
    assert sum(c["share_of_revenue"] for c in body["channels"]) == pytest.approx(body["totals"]["direct_share_of_revenue"], abs=2e-4)


def test_api_quality_findings_endpoint_leaves_data_quality_untouched(client):
    findings = client.get("/api/data-quality/channels").json()["findings"]
    assert len(findings) == 2 and all(f["treatment"] and f["evidence"] for f in findings)
    assert "findings" not in client.get("/api/data-quality").json()
