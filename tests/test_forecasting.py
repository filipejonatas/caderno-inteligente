from __future__ import annotations

import pandas as pd

from caderno_inteligente.forecasting import _backtest, build_demand_forecasts


def _sales(sku: str, values: list[float], start: str = "2024-01-01") -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Mês": pd.date_range(start, periods=len(values), freq="MS"),
            "SKU": sku,
            "Quantidade faturada": values,
        }
    )


def test_seasonal_series_selects_seasonal_naive_and_forecasts_three_months():
    seasonal = list(range(10, 22)) * 2
    result = build_demand_forecasts(_sales("SKU-S", seasonal)).iloc[0]

    assert result["model"] == "seasonal_naive_12"
    assert result["backtest_wape"] == 0
    assert result["forecast_confidence"] == "alta"
    assert len(result["forecast_months"]) == 3
    assert len(result["forecast_values"]) == 3


def test_smooth_recent_series_selects_moving_average():
    result = build_demand_forecasts(_sales("SKU-M", list(range(1, 25)))).iloc[0]

    assert result["model"] == "moving_average_3"
    assert result["forecast_next_month"] >= 0
    assert all(value >= 0 for value in result["forecast_values"])


def test_trend_classification_covers_growing_stable_and_declining():
    sales = pd.concat(
        [
            _sales("GROW", [10, 10, 10, 20, 20, 20]),
            _sales("STABLE", [10, 10, 10, 10, 10, 10]),
            _sales("FALL", [20, 20, 20, 10, 10, 10]),
        ],
        ignore_index=True,
    )
    trends = build_demand_forecasts(sales).set_index("sku")["trend"].to_dict()

    assert trends == {"FALL": "decrescente", "GROW": "crescente", "STABLE": "estável"}


def test_insufficient_history_does_not_return_a_zero_forecast():
    result = build_demand_forecasts(_sales("SHORT", [1, 2, 3, 4, 5])).iloc[0]

    assert result["status"] == "insufficient_data"
    assert result["forecast_next_month"] is None
    assert result["forecast_values"] == []
    assert result["forecast_confidence"] == "baixa"


def test_backtest_predictions_do_not_read_holdout_values():
    index = pd.period_range("2024-01", periods=9, freq="M")
    first = pd.Series([10, 20, 30, 40, 50, 60, 1, 1, 1], index=index, dtype=float)
    second = pd.Series([10, 20, 30, 40, 50, 60, 999, 999, 999], index=index, dtype=float)

    _, first_predictions = _backtest(first, "moving_average_3")
    _, second_predictions = _backtest(second, "moving_average_3")

    assert first_predictions == second_predictions


def test_zero_holdout_has_low_confidence_and_null_wape():
    result = build_demand_forecasts(_sales("ZERO", [10] * 9 + [0, 0, 0])).iloc[0]

    assert result["backtest_wape"] is None
    assert result["forecast_confidence"] == "baixa"
