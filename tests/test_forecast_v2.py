"""Etapa 15.1: motor oficial v2, horizonte de 6 meses e avaliação com meses de pico."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pandas as pd
import pytest

from caderno_inteligente.forecast_engine_config import DEFAULTS, load_engine_config
from caderno_inteligente.forecasting import build_demand_forecasts
from caderno_inteligente.ingestion import load_workbook
from caderno_inteligente.official_forecast import (
    build_official_forecasts,
    chain_forecast,
    chain_windows,
    evaluation_origins,
    window_errors,
)
from caderno_inteligente.rolling_backtest import peak_evaluation
from caderno_inteligente.transformations import normalise_dataset
from caderno_inteligente.validation_center import _forecast_aggregate_output

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/source/Base de Dados - Caderno Inteligente.xlsm"
SNAPSHOT = ROOT / "docs/etapa-15/snapshot-previsao-v2.json"


def _config(**changes):
    config = deepcopy(DEFAULTS)
    config["engine"] = "v2"
    for key, value in changes.items():
        config[key] = {**config[key], **value} if isinstance(value, dict) else value
    return config


def _seasonal(months: int, start: str = "2024-01", peak: float = 2.5, growth: float = 0.0) -> pd.Series:
    """Série mensal com pico em janeiro (×`peak`) e crescimento anual opcional."""
    index = pd.period_range(start, periods=months, freq="M")
    values = [100.0 * (1 + growth) ** (position / 12) * (peak if period.month == 1 else 1.0) for position, period in enumerate(index)]
    return pd.Series(values, index=index)


def _sales(series: pd.Series, sku: str = "SKU-1") -> pd.DataFrame:
    return pd.DataFrame({"Mês": series.index.to_timestamp(), "SKU": sku, "Quantidade faturada": series.values})


@pytest.mark.parametrize(("months", "model"), [(24, "seasonal_level"), (13, "seasonal_naive_12"), (8, "moving_average_3")])
def test_chain_uses_the_first_model_the_history_supports(months, model):
    series = _seasonal(months)
    targets = pd.period_range(series.index.max() + 1, periods=6, freq="M")
    code, values = chain_forecast(series, targets, _config())
    assert code == model and len(values) == 6 and all(value >= 0 for value in values)


def test_short_history_is_insufficient_never_zero():
    record = build_official_forecasts(_sales(_seasonal(4)), _config()).to_dict("records")[0]
    assert record["status"] == "insufficient_data" and record["forecast_values"] == [] and record["engine"] == "v2"


def test_v2_record_has_six_months_and_keeps_the_three_month_fields():
    record = build_official_forecasts(_sales(_seasonal(30, growth=0.1)), _config()).to_dict("records")[0]
    assert record["model"] == "seasonal_level" and record["horizon_months"] == 6 and len(record["forecast_values"]) == 6
    assert record["forecast_next_month"] == record["forecast_values"][0]
    assert record["forecast_total_3m"] == pytest.approx(sum(record["forecast_values"][:3]), abs=0.11)
    assert record["forecast_total_6m"] == pytest.approx(sum(record["forecast_values"]), abs=0.11)


def test_ratio_bounds_come_from_the_configuration():
    series = _seasonal(24, peak=2.5)  # janeiro vale 2,5× o nível
    target = pd.period_range("2026-01", periods=1, freq="M")
    _, wide = chain_forecast(series, target, _config(seasonal_level={"ratio_bounds": [0.5, 3.0]}))
    _, narrow = chain_forecast(series, target, _config(seasonal_level={"ratio_bounds": [0.5, 2.0]}))
    assert wide[0] == pytest.approx(250.0, rel=0.01) and narrow[0] == pytest.approx(200.0, rel=0.01)


def test_v1_engine_is_dispatched_unchanged():
    sales = _sales(_seasonal(24))
    config = _config()
    config["engine"] = "v1"
    assert build_official_forecasts(sales, config).equals(build_demand_forecasts(sales))


def test_origins_need_full_test_window_and_windows_never_see_the_future():
    series = _seasonal(30)  # 2024-01 a 2026-06
    config = _config(evaluation={"first_origin": "2025-03", "last_origin": "2026-06"})
    origins = evaluation_origins(series, config)
    assert str(origins[0]) == "2025-03" and str(origins[-1]) == "2026-03"  # depois disso faltam meses de teste
    for window in chain_windows(series, config):
        assert len(window["actual"]) == len(window["predicted"]) == 3


def test_window_errors_split_peak_and_normal_months():
    windows = [{"months": [12, 1, 2], "actual": [100.0, 200.0, 100.0], "predicted": [90.0, 150.0, 100.0]}]
    errors = window_errors(windows, [1])
    assert errors["peak_abs"] == 50 and errors["peak_actual"] == 200 and errors["peak_signed"] == -50
    assert errors["normal_abs"] == 10 and errors["all_abs"] == 60 and errors["all_actual"] == 400


def test_peak_evaluation_rewards_the_seasonal_engine_on_a_seasonal_series():
    sales = pd.concat([_sales(_seasonal(30, growth=0.1), f"SKU-{number}") for number in range(3)])
    config = _config(evaluation={"first_origin": "2025-03", "last_origin": "2026-03", "peak_months": [1]})
    result = peak_evaluation(sales, config)
    procedures = result["procedures"]
    assert result["skus"] == 3 and result["peak_months"] == [1]
    assert procedures["v2"]["peak_wape"] < procedures["baseline"]["peak_wape"]
    assert procedures["v2"]["peak_wape"] < procedures["v2_ratio_2"]["peak_wape"]  # o teto 2,0 corta o pico de 2,5×
    assert set(result["criteria"]) >= {"wape_criterion_met", "peak_bias_criterion_met", "bias_criterion_met", "baseline_criterion_met", "all_met"}


def test_forecast_aggregate_reads_month_totals_and_family_months():
    forecasts = pd.DataFrame([
        {"sku": "A", "status": "ok", "forecast_months": ["2026-11-01", "2027-01-01"], "forecast_values": [10.0, 5.0]},
        {"sku": "B", "status": "ok", "forecast_months": ["2026-11-01", "2027-01-01"], "forecast_values": [20.0, 7.0]},
        {"sku": "C", "status": "insufficient_data", "forecast_months": [], "forecast_values": []},
    ])
    indicators = pd.DataFrame({"SKU": ["A", "B", "C"], "family": ["Escolar", "Refis", "Escolar"]})
    obtained = _forecast_aggregate_output(["total_units_2026_11", "family_units_escolar_2026_11_2027_01", "family_units_escolar_2027_01"], forecasts, indicators)
    assert obtained["total_units_2026_11"] == 30.0
    assert obtained["family_units_escolar_2027_01"] == 5.0
    assert obtained["family_units_escolar_2026_11_2027_01"] is None  # mês com ano diferente não é inventado


def test_official_v2_forecast_matches_the_15_1_snapshot():
    sales = normalise_dataset(load_workbook(SOURCE))["Vendas_24m"]
    current = json.loads(build_official_forecasts(sales, load_engine_config()).sort_values("sku").to_json(orient="records", force_ascii=False))
    assert current == json.loads(SNAPSHOT.read_text(encoding="utf-8"))["forecasts"]


def test_real_base_promotion_criteria_hold_and_november_is_no_longer_underforecast():
    sales = normalise_dataset(load_workbook(SOURCE))["Vendas_24m"]
    config = load_engine_config()
    assert config["engine"] == "v2"
    result = peak_evaluation(sales, config)
    assert result["origins"] == ["2025-11", "2025-12", "2026-01", "2026-02", "2026-03", "2026-04", "2026-05"]
    assert result["criteria"]["all_met"] is True
    forecasts = build_official_forecasts(sales, config)
    november = sum(values[2] for values in forecasts["forecast_values"])
    assert 0.95 * 34_259 <= november <= 1.20 * 34_259
