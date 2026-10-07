import math

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from caderno_inteligente.forecasting import build_demand_forecasts
from caderno_inteligente.revenue import build_revenue_forecasts

PRICE = "Preço unitário (R$)"
VALUE = "Valor faturado (R$)"


def _sales(sku: str, units: list[int], price: float = 10.0, start: str = "2025-01-01", channel: str = "E-commerce") -> pd.DataFrame:
    months = pd.date_range(start, periods=len(units), freq="MS")
    return pd.DataFrame({
        "Mês": months, "SKU": sku, "Cliente/Canal": channel, "Quantidade faturada": units,
        PRICE: price, VALUE: [u * price for u in units],
    })


def _products(*rows: tuple[str, str]) -> pd.DataFrame:
    return pd.DataFrame({"SKU": [r[0] for r in rows], "Produto": [f"Produto {r[0]}" for r in rows], "Família": [r[1] for r in rows]})


def _prices(**by_sku: float) -> pd.DataFrame:
    return pd.DataFrame({"SKU": list(by_sku), PRICE: list(by_sku.values()), "Vigência fictícia": pd.Timestamp("2024-09-01")})


def _build(sales, products, prices=None, commercial=None):
    return build_revenue_forecasts(build_demand_forecasts(sales), products, sales, prices, commercial)


def test_revenue_is_forecast_units_times_price():
    sales = _sales("A", [100] * 12)
    result = _build(sales, _products(("A", "F1")), _prices(A=12.5))
    item = result["items"][0]
    assert item["status"] == "ok" and item["nature"] == "estimado" and item["unit_price"] == 12.5
    assert item["forecast_units"] == [100.0, 100.0, 100.0]
    assert item["revenue_values"] == [1250.0, 1250.0, 1250.0]
    assert item["revenue_next_month"] == 1250.0 and item["revenue_total_3m"] == 3750.0
    assert item["calculation"]["terms"][0] == {"month": "2026-01-01", "units": 100.0, "unit_price": 12.5, "revenue": 1250.0}


def test_price_table_wins_and_conflict_with_sales_is_flagged():
    result = _build(_sales("A", [100] * 12, price=10.0), _products(("A", "F1")), _prices(A=12.0))
    item = result["items"][0]
    assert item["unit_price"] == 12.0 and item["price_source"] == "Precos_Produtos"
    assert item["price_conflict"] is True and "tabela" in item["reason"]


def test_falls_back_to_last_sales_price_when_table_has_no_price():
    result = _build(_sales("A", [100] * 12, price=10.0), _products(("A", "F1")), _prices(B=5.0))
    item = result["items"][0]
    assert item["unit_price"] == 10.0 and item["price_source"].startswith("Vendas_24m")
    assert item["price_conflict"] is False


def test_sku_without_any_price_is_null_never_zero_and_listed_as_excluded():
    sales = _sales("A", [100] * 12).drop(columns=[PRICE])
    result = _build(sales, _products(("A", "F1")), None)
    item = result["items"][0]
    assert item["status"] == "sem_preco"
    assert item["revenue_values"] == [] and item["revenue_total_3m"] is None and item["revenue_next_month"] is None
    family = result["families"][0]
    assert family["revenue_total_3m"] is None and family["by_month"] == []
    assert family["skus_with_estimate"] == 0 and family["skus_excluded"][0]["sku"] == "A"


def test_zero_or_invalid_price_is_not_used():
    result = _build(_sales("A", [100] * 12, price=0.0), _products(("A", "F1")), _prices(A=0.0))
    assert result["items"][0]["status"] == "sem_preco"


def test_sku_without_forecast_has_no_estimate_even_with_price():
    sales = pd.concat([_sales("A", [100] * 12), _sales("B", [10, 10, 10])], ignore_index=True)
    result = _build(sales, _products(("A", "F1"), ("B", "F1")), _prices(A=10.0, B=10.0))
    by_sku = {item["sku"]: item for item in result["items"]}
    assert by_sku["B"]["status"] == "sem_previsao" and by_sku["B"]["revenue_total_3m"] is None
    total = result["total"]
    assert total["skus_total"] == 2 and total["skus_with_estimate"] == 1
    assert [row["sku"] for row in total["skus_excluded"]] == ["B"]
    assert total["revenue_total_3m"] == by_sku["A"]["revenue_total_3m"]


def test_aggregation_by_family_and_total():
    sales = pd.concat([_sales("A", [100] * 12), _sales("B", [50] * 12), _sales("C", [20] * 12)], ignore_index=True)
    result = _build(sales, _products(("A", "F1"), ("B", "F1"), ("C", "F2")), _prices(A=10.0, B=10.0, C=100.0))
    families = {group["label"]: group for group in result["families"]}
    assert families["F1"]["revenue_total_3m"] == 4500.0 and families["F2"]["revenue_total_3m"] == 6000.0
    assert result["total"]["revenue_total_3m"] == 10500.0
    assert [row["revenue"] for row in result["total"]["by_month"]] == [3500.0] * 3
    assert result["families"][0]["label"] == "F2"  # ordenadas pelo maior faturamento estimado


def test_observed_revenue_is_observed_and_compared_with_last_three_months():
    result = _build(_sales("A", [100] * 12), _products(("A", "F1")), _prices(A=10.0))
    total = result["total"]
    assert total["observed_revenue"]["values"] == [1000.0] * 12
    assert total["observed_last_3m_same_skus"] == 3000.0 and total["change_vs_last_3m"] == 0.0


def test_backtest_wape_in_revenue_is_computed_and_null_when_unavailable():
    units = [100, 100, 100, 100, 100, 100, 100, 100, 100, 110, 110, 110]
    result = _build(_sales("A", units), _products(("A", "F1")), _prices(A=10.0))
    wape = result["total"]["backtest_wape"]
    assert wape is not None and 0 < wape < 0.2
    sparse = _build(_sales("A", [100, 100]), _products(("A", "F1")), _prices(A=10.0))
    assert sparse["total"]["backtest_wape"] is None


def test_commercial_reference_compares_only_overlapping_months_and_does_not_replace():
    sales = _sales("A", [100] * 12)
    commercial = pd.DataFrame({
        "SKU": ["A", "A"], "Mês": pd.to_datetime(["2026-02-01", "2026-03-01"]),
        "Previsão unidades": [80, 90], "Origem previsão": ["Consenso S&OP", "Comercial"],
    })
    result = _build(sales, _products(("A", "F1")), _prices(A=10.0), commercial)
    item = result["items"][0]
    reference = item["commercial_reference"]
    assert reference["months"] == ["2026-02-01", "2026-03-01"]
    assert reference["model_revenue"] == 2000.0 and reference["commercial_revenue"] == 1700.0
    assert reference["difference_ratio"] == round((2000 - 1700) / 1700, 4)
    assert reference["origins"] == ["Comercial", "Consenso S&OP"]
    assert item["revenue_total_3m"] == 3000.0  # a previsão estatística segue sendo a estimativa
    assert _build(sales, _products(("A", "F1")), _prices(A=10.0), None)["items"][0]["commercial_reference"] is None


def test_revenue_layer_does_not_change_the_unit_forecast():
    sales = _sales("A", [100, 120, 90, 130, 110, 100, 95, 140, 100, 105, 99, 101])
    before = build_demand_forecasts(sales).copy(deep=True)
    _build(sales, _products(("A", "F1")), _prices(A=10.0))
    pd.testing.assert_frame_equal(before, build_demand_forecasts(sales))


# --- API sobre a base real -------------------------------------------------

@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_api_revenue_forecast_contract_and_labels(client):
    response = client.get("/api/revenue-forecast")
    assert response.status_code == 200
    body = response.json()
    assert body["nature"] == "estimado" and "×" in body["formula"] and body["limitations"]
    assert len(body["items"]) == client.get("/api/overview").json()["total_skus"]
    for item in body["items"]:
        assert item["nature"] == "estimado"
        if item["status"] == "ok":
            assert item["unit_price"] > 0 and item["price_source"]
            assert len(item["revenue_values"]) == 3 and item["revenue_total_3m"] is not None
            assert math.isclose(item["revenue_total_3m"], sum(item["revenue_values"]), abs_tol=0.05)
        else:
            assert item["revenue_total_3m"] is None and item["reason"]


def test_api_revenue_matches_units_times_price_and_family_sum_equals_total(client):
    body = client.get("/api/revenue-forecast").json()
    forecasts = {item["sku"]: item["forecast"] for item in client.get("/api/forecasts").json()}
    for item in body["items"]:
        if item["status"] != "ok":
            continue
        assert item["forecast_units"] == forecasts[item["sku"]]["forecast_values"][:3]
        assert math.isclose(item["revenue_total_6m"], sum(forecasts[item["sku"]]["forecast_values"][:6]) * item["unit_price"], abs_tol=0.05)
        for units, revenue in zip(item["forecast_units"], item["revenue_values"]):
            assert math.isclose(units * item["unit_price"], revenue, abs_tol=0.01)
    assert math.isclose(sum(group["revenue_total_3m"] for group in body["families"]), body["total"]["revenue_total_3m"], abs_tol=1)


def test_api_sku_detail_carries_revenue_and_keeps_operational_fields(client):
    detail = client.get("/api/priorities/CI-0014").json()
    revenue = detail["revenue_forecast"]
    assert revenue["sku"] == "CI-0014" and revenue["nature"] == "estimado"
    listed = next(item for item in client.get("/api/revenue-forecast").json()["items"] if item["sku"] == "CI-0014")
    assert revenue == listed
    assert detail["forecast"] == next(item["forecast"] for item in client.get("/api/forecasts").json() if item["sku"] == "CI-0014")


def test_api_forecasts_and_priorities_have_no_revenue_fields(client):
    for item in client.get("/api/forecasts").json():
        assert not any("revenue" in key for key in item) and not any("revenue" in key for key in item["forecast"])
    for item in client.get("/api/priorities").json():
        assert not any("revenue" in key for key in item)
