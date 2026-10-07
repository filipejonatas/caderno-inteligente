from __future__ import annotations

import pandas as pd
import pytest

from caderno_inteligente import rolling_backtest as rb
from caderno_inteligente.forecast_engine_config import load_engine_config

CONFIG = load_engine_config()
INTERVALS = CONFIG["intervals"]
PATTERN = [10 + month for month in range(12)]  # 10..21


def _series(values) -> pd.Series:
    return pd.Series([float(value) for value in values], index=pd.period_range("2024-01", periods=len(values), freq="M"))


def _sales(sku: str, values) -> pd.DataFrame:
    return pd.DataFrame({"Mês": pd.date_range("2024-01-01", periods=len(values), freq="MS"), "SKU": sku, "Quantidade faturada": [float(v) for v in values]})


# Erros relativos (real − previsto) ÷ previsto: 0,25 · 0 · −0,1667 | 0,25 · 0 · −0,2 | 0 · 0 · 0
WINDOWS = [
    ([10.0, 10.0, 10.0], [8.0, 10.0, 12.0]),
    ([20.0, 20.0, 20.0], [16.0, 20.0, 25.0]),
    ([10.0, 10.0, 10.0], [10.0, 10.0, 10.0]),
]


# --- Quantis e faixa, à mão -----------------------------------------------------------------------------------------

def test_quantile_interpolates_linearly_between_neighbours():
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert rb._quantile(values, 0.0) == 1.0 and rb._quantile(values, 1.0) == 5.0
    assert rb._quantile(values, 0.5) == pytest.approx(3.0)
    assert rb._quantile(values, 0.1) == pytest.approx(1.4)
    assert rb._quantile(values, 0.9) == pytest.approx(4.6)
    assert rb._quantile([7.0], 0.9) == 7.0


def test_error_quantiles_by_hand():
    quantiles = rb.error_quantiles(WINDOWS, INTERVALS)

    # Ordenados: −0,2; −0,1667; 0; 0; 0; 0; 0; 0,25; 0,25. P10 na posição 0,8; P90 na 7,2.
    assert quantiles["residuals"] == 9
    assert quantiles["lower"] == pytest.approx(-0.2 + 0.8 * (0.2 - 1 / 6))
    assert quantiles["upper"] == pytest.approx(0.25)


def test_error_quantiles_need_the_minimum_number_of_residuals():
    five = [([10.0] * 5, [10.0] * 5)]
    six = [([10.0] * 6, [10.0] * 6)]

    assert rb.error_quantiles(five, INTERVALS) is None
    assert rb.error_quantiles(six, INTERVALS)["residuals"] == 6


def test_zero_forecasts_have_no_relative_error_and_are_not_counted_as_zero_error():
    windows = [([5.0, 5.0, 5.0, 5.0, 5.0, 5.0], [0.0, 0.0, 10.0, 10.0, 10.0, 10.0])]  # só 4 erros válidos
    assert rb.error_quantiles(windows, INTERVALS) is None
    assert rb.error_quantiles(windows, {**INTERVALS, "minimum_residuals": 4})["residuals"] == 4


def test_interval_applies_the_quantiles_to_each_forecast():
    quantiles = rb.error_quantiles(WINDOWS, INTERVALS)
    lower, upper = rb.apply_interval([100.0, 100.0, 100.0], quantiles)

    assert lower == pytest.approx([100 * (1 + quantiles["lower"])] * 3) and lower[0] == pytest.approx(82.667, abs=1e-3)
    assert upper == pytest.approx([125.0] * 3)


def test_interval_is_never_negative_and_always_contains_the_point_forecast():
    assert rb.apply_interval([100.0], {"lower": -1.5, "upper": 0.2}) == ([0.0], [120.0])
    # Erros todos positivos (previsão sempre abaixo do real): a faixa se estende até a previsão pontual, não a deixa de fora.
    lower, upper = rb.apply_interval([100.0], {"lower": 0.1, "upper": 0.1})
    assert lower == [100.0] and upper == [pytest.approx(110.0)]
    assert rb.apply_interval([0.0], {"lower": -0.2, "upper": 0.3}) == ([0.0], [0.0])


# --- Dentro do backtest e das previsões ------------------------------------------------------------------------------

def test_backtest_exposes_the_quantiles_of_the_selected_model():
    result = rb.rolling_backtest(_series(PATTERN * 2), CONFIG)

    assert result["selected_model"] == "seasonal_naive_12"
    assert result["residual_count"] == 9 and result["error_quantiles"]["residuals"] == 9
    assert result["error_quantiles"]["lower"] == 0 and result["error_quantiles"]["upper"] == 0  # sazonal exato: erro zero


def test_short_series_has_no_band_instead_of_an_invented_one():
    result = rb.rolling_backtest(_series([10 + (m % 5) for m in range(12)]), CONFIG)

    assert result["residual_count"] < INTERVALS["minimum_residuals"]
    assert result["error_quantiles"] is None
    assert rb.rolling_backtest(_series(range(1, 9)), CONFIG)["error_quantiles"] is None


def test_forecast_record_carries_the_band_around_the_point_forecast():
    [record] = rb.build_rolling_forecasts(_sales("S", PATTERN * 2), CONFIG)
    band = record["forecast_interval"]

    assert band["level"] == 0.8 and band["residuals"] == 9
    assert len(band["lower"]) == len(band["upper"]) == 3
    for low, point, high in zip(band["lower"], record["forecast_values"], band["upper"]):
        assert 0 <= low <= point <= high
    assert band["lower"] == band["upper"] == record["forecast_values"]  # sem dispersão nos erros: a faixa colapsa na previsão


def test_forecast_record_without_enough_errors_has_no_band():
    [record] = rb.build_rolling_forecasts(_sales("S", [10 + (m % 5) for m in range(12)]), CONFIG)
    assert record["forecast_interval"] is None and record["forecast_values"]


def test_forecast_record_with_undefined_wape_has_no_band():
    [record] = rb.build_rolling_forecasts(_sales("Z", [0] * 24), CONFIG)
    assert record["status"] == "wape_indefinido" and record["forecast_interval"] is None


def test_band_widens_with_noisier_history():
    calm = rb.build_rolling_forecasts(_sales("C", [100 + (m % 3) for m in range(24)]), CONFIG)[0]
    noisy = rb.build_rolling_forecasts(_sales("N", [100 + 30 * ((m * 7) % 5 - 2) for m in range(24)]), CONFIG)[0]

    def width(record):
        band = record["forecast_interval"]
        return (band["upper"][0] - band["lower"][0]) / record["forecast_values"][0]

    assert width(noisy) > width(calm)


# --- Calibração fora da amostra --------------------------------------------------------------------------------------

def test_calibration_counts_hits_out_of_sample():
    sales = pd.concat([_sales(sku, PATTERN * 2) for sku in ("A", "B", "C")])
    result = rb.interval_calibration(sales, CONFIG)

    assert result["nominal_level"] == 0.8
    # Origem de treino 18 tem só 1 janela interna (3 erros): sem faixa. Só a origem 21 entra: 3 SKUs × 3 meses.
    assert result["origin_train_lengths"] == [21] and result["skus_tested"] == 3 and result["tested_months"] == 9
    assert result["hits"] == 9 and result["coverage"] == 1.0
    assert result["median_relative_width"] == 0


def test_calibration_measures_against_what_really_happened():
    values = PATTERN * 2
    values[-3:] = [1000, 1000, 1000]  # o futuro real foge de qualquer faixa calculada só com o passado
    result = rb.interval_calibration(_sales("A", values), CONFIG)

    assert result["tested_months"] == 3 and result["hits"] == 0 and result["coverage"] == 0.0


def test_calibration_without_any_band_reports_no_coverage():
    result = rb.interval_calibration(_sales("A", range(1, 10)), CONFIG)

    assert result["tested_months"] == 0 and result["coverage"] is None
    assert result["median_relative_width"] is None and result["origin_train_lengths"] == []


def test_reusing_the_monthly_series_gives_exactly_the_same_results():
    sales = pd.concat([_sales("A", PATTERN * 2), _sales("B", range(1, 25))])
    shared = rb.series_by_sku(sales)

    assert list(shared) == ["A", "B"]
    assert rb.interval_calibration(sales, CONFIG, shared) == rb.interval_calibration(sales, CONFIG)
    assert rb.nested_evaluation_table(sales, CONFIG, shared) == rb.nested_evaluation_table(sales, CONFIG)
    assert rb.sensitivity_grid(sales, CONFIG, shared) == rb.sensitivity_grid(sales, CONFIG)
    assert rb.build_rolling_forecasts(sales, CONFIG, series_map=shared) == rb.build_rolling_forecasts(sales, CONFIG)


def test_calibration_does_not_change_the_config():
    from copy import deepcopy

    before = deepcopy(CONFIG)
    rb.interval_calibration(_sales("A", PATTERN * 2), CONFIG)
    assert CONFIG == before
