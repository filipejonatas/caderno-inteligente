from __future__ import annotations

from caderno_inteligente.recommendations import build_operational_recommendation


def _indicator(**overrides):
    values = {
        "minimum_lot": 50,
        "average_sales_per_day": 10,
        "safety_stock_days": 5,
        "backlog_order_quantity": 80,
        "current_stock": 30,
        "production_order_quantity": 20,
        "has_sell_out": True,
    }
    values.update(overrides)
    return values


def _forecast(**overrides):
    values = {"status": "ok", "forecast_next_month": 100, "forecast_confidence": "alta"}
    values.update(overrides)
    return values


def test_recommendation_uses_max_of_forecast_and_backlog_and_rounds_lot():
    result = build_operational_recommendation(_indicator(), _forecast(), [])

    assert result["calculation"]["demand_to_cover"] == 100
    assert result["raw_quantity"] == 100
    assert result["suggested_quantity"] == 100
    assert result["action"] == "produzir"


def test_backlog_is_not_added_to_forecast():
    result = build_operational_recommendation(
        _indicator(backlog_order_quantity=120), _forecast(forecast_next_month=100), []
    )

    assert result["calculation"]["demand_to_cover"] == 120
    assert result["raw_quantity"] == 120


def test_quantity_is_never_negative_and_excess_is_monitored():
    result = build_operational_recommendation(
        _indicator(current_stock=1000), _forecast(), ["EXCESS_COVERAGE"]
    )

    assert result["raw_quantity"] == 0
    assert result["suggested_quantity"] == 0
    assert result["action"] == "monitorar_excesso"


def test_minimum_lot_rounds_up():
    result = build_operational_recommendation(
        _indicator(minimum_lot=60, current_stock=35), _forecast(), []
    )

    assert result["raw_quantity"] == 95
    assert result["suggested_quantity"] == 120


def test_capacity_conflict_requires_review_and_limits_confidence():
    result = build_operational_recommendation(_indicator(), _forecast(), ["CAPACITY_CONFLICT"])

    assert result["action"] == "produzir_validar_capacidade"
    assert result["capacity_status"] == "requires_review"
    assert result["confidence"] == "média"
    assert result["requires_human_review"] is True


def test_missing_sellout_reduces_confidence():
    result = build_operational_recommendation(_indicator(has_sell_out=False), _forecast(), [])

    assert result["confidence"] == "baixa"
    assert "Sell-out não observado" in result["confidence_reason"]


def test_insufficient_forecast_investigates_without_misleading_quantity():
    result = build_operational_recommendation(
        _indicator(), {"status": "insufficient_data", "forecast_next_month": None}, []
    )

    assert result["action"] == "investigar_dados"
    assert result["suggested_quantity"] is None
    assert result["requires_human_review"] is True
