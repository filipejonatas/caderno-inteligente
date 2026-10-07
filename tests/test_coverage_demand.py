"""Etapa 15.2: cobertura pela demanda de referência e aviso de divergência do cadastro."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

import backend.main as main
from caderno_inteligente.indicators import build_sku_indicators, registered_demand_warning
from caderno_inteligente.ingestion import load_workbook
from caderno_inteligente.recommendations import build_operational_recommendation
from caderno_inteligente.rules import evaluate_rules
from caderno_inteligente.transformations import normalise_dataset

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/source/Base de Dados - Caderno Inteligente.xlsm"
SETTINGS = {"days_per_month": 30.0, "registered_demand_divergence": 0.2}


@pytest.fixture(scope="module")
def dataset():
    return normalise_dataset(load_workbook(SOURCE))


def _forecasts(values_by_sku: dict[str, list[float]]) -> pd.DataFrame:
    return pd.DataFrame([{"sku": sku, "status": "ok", "forecast_values": values} for sku, values in values_by_sku.items()])


def test_reference_demand_comes_from_the_next_three_forecast_months(dataset):
    indicators = build_sku_indicators(dataset, _forecasts({"CI-0014": [1500, 1200, 1800, 9999]}), SETTINGS).set_index("SKU")
    row = indicators.loc["CI-0014"]
    assert row["demand_source"] == "previsao_3m"
    assert row["reference_daily_demand"] == pytest.approx(1500 / 30)  # média dos 3 primeiros meses; o 4º não entra
    assert row["coverage_days_calculated"] == pytest.approx(row["current_stock"] / row["reference_daily_demand"])
    assert row["coverage_days_registered"] == pytest.approx(row["current_stock"] / row["average_sales_per_day"])


def test_without_forecast_uses_recent_sales_and_never_invents_zero(dataset):
    indicators = build_sku_indicators(dataset, _forecasts({"CI-0014": [0, 0, 0]}), SETTINGS).set_index("SKU")
    sales = dataset["Vendas_24m"]
    recent = sales[pd.to_datetime(sales["Mês"]).dt.to_period("M") >= pd.Period("2026-06", "M")]
    expected = recent.loc[recent["SKU"] == "CI-0014", "Quantidade faturada"].sum() / 3 / 30
    assert indicators.loc["CI-0014", "demand_source"] == "vendas_3m"
    assert indicators.loc["CI-0014", "reference_daily_demand"] == pytest.approx(expected)
    assert (indicators["reference_daily_demand"] > 0).all()


def _empty(**columns) -> pd.DataFrame:
    """Aba vazia com tipos definidos, como sairia da planilha sem registros."""
    return pd.DataFrame({"SKU": pd.Series(dtype=str), **{name: pd.Series(dtype=kind) for name, kind in columns.items()}})


def test_registered_field_is_the_last_fallback():
    data = {
        "Produtos": pd.DataFrame({"SKU": ["X"], "Produto": ["P"], "Família": ["F"], "Curva ABC": ["A"], "Status": ["Ativo"], "Lead time (dias)": [10],
                                  "Lote mínimo": [100], "Venda média/dia": [4.0]}),
        "Estoque_Atual": pd.DataFrame({"SKU": ["X"], "Estoque atual": [40], "Cobertura dias": [10], "Estoque segurança dias": [5]}),
        "Ordens_Producao": _empty(Quantidade=float, **{"Conclusão prevista": "datetime64[ns]"}),
        "Carteira_Pedidos": _empty(Quantidade=float, **{"Data prometida": "datetime64[ns]"}),
        "Sell_In": _empty(**{"Quantidade enviada": float}),
        "Sell_Out": _empty(Cliente=str, **{"Quantidade vendida": float}),
        "Forecast_Comercial": _empty(**{"Previsão unidades": float}),
        "Capacidade_Semanal": pd.DataFrame({"Família": ["F"], "Semana inicial": [pd.Timestamp("2026-09-14")], "Capacidade máxima": [10], "Capacidade comprometida": [5],
                                            "Capacidade disponível": [5], "Ocupação": [0.5]}),
    }
    row = build_sku_indicators(data, None, SETTINGS).iloc[0]
    assert row["demand_source"] == "cadastro" and row["coverage_days_calculated"] == pytest.approx(10.0)
    assert row["data_quality_warnings"] == []


def test_divergence_is_flagged_both_ways_and_listed_largest_first(dataset):
    indicators = build_sku_indicators(dataset, _forecasts({"CI-0001": [300, 300, 300], "CI-0002": [100, 100, 100], "CI-0003": [262, 262, 262]}), SETTINGS)
    rows = indicators.set_index("SKU")
    assert rows.loc["CI-0001", "data_quality_warnings"] == ["REGISTERED_DEMAND_DIVERGENCE"]  # 10/dia previsto × 5 cadastrado
    assert rows.loc["CI-0002", "data_quality_warnings"] == ["REGISTERED_DEMAND_DIVERGENCE"]  # 3,3/dia previsto × 6,7 cadastrado
    assert rows.loc["CI-0003", "data_quality_warnings"] == []  # 8,7/dia previsto × 8,4 cadastrado
    warning = registered_demand_warning(indicators[indicators["SKU"].isin(["CI-0001", "CI-0002", "CI-0003"])], 0.2)
    assert warning["code"] == "REGISTERED_DEMAND_DIVERGENCE" and warning["count"] == 2
    assert [item["sku"] for item in warning["items"]] == ["CI-0001", "CI-0002"]


def test_rules_report_the_demand_used_and_its_source(dataset):
    indicators = build_sku_indicators(dataset, _forecasts({"CI-0002": [300, 300, 300]}), SETTINGS)
    issues = evaluate_rules(indicators[indicators["SKU"] == "CI-0002"])
    rupture = issues[issues["code"] == "RUP_SAFETY_STOCK"].iloc[0]
    assert rupture["values_used"]["daily_demand"] == pytest.approx(10.0) and rupture["values_used"]["demand_source"] == "previsao_3m"
    assert any("demanda de referência" in origin for origin in rupture["data_origin"])


def test_safety_stock_uses_the_reference_demand_with_registered_fallback():
    forecast = {"status": "ok", "forecast_next_month": 0.0, "forecast_confidence": "alta"}
    base = {"current_stock": 0, "production_order_quantity": 0, "backlog_order_quantity": 0, "minimum_lot": 1, "safety_stock_days": 10, "has_sell_out": True}
    with_reference = build_operational_recommendation({**base, "average_sales_per_day": 2, "reference_daily_demand": 5}, forecast, [])
    without_reference = build_operational_recommendation({**base, "average_sales_per_day": 2}, forecast, [])
    assert with_reference["safety_stock_quantity"] == 50 and without_reference["safety_stock_quantity"] == 20


def test_api_exposes_the_warning_and_the_new_coverage():
    client = TestClient(main.app)
    warnings = [item for item in client.get("/api/data-quality").json()["warnings"] if item.get("code") == "REGISTERED_DEMAND_DIVERGENCE"]
    assert len(warnings) == 1 and {"CI-0014", "CI-0004"} <= {item["sku"] for item in warnings[0]["items"]}
    indicator = client.get("/api/priorities/CI-0014").json()["indicator"]
    assert indicator["demand_source"] == "previsao_3m" and indicator["coverage_days_calculated"] < 55 <= indicator["coverage_days_registered"] + 0.1
    assert indicator["data_quality_warnings"] == ["REGISTERED_DEMAND_DIVERGENCE"]
