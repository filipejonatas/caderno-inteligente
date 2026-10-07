from __future__ import annotations

import math
from copy import deepcopy
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from caderno_inteligente import rolling_backtest as rb
from caderno_inteligente.forecast_candidates import CANDIDATES
from caderno_inteligente.forecast_engine_config import load_engine_config
from caderno_inteligente.forecasting import _monthly_series, build_demand_forecasts
from caderno_inteligente.ingestion import load_workbook
from caderno_inteligente.transformations import normalise_dataset
from caderno_inteligente.validation_center import _naive_last

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "source" / "Base de Dados - Caderno Inteligente.xlsm"
CONFIG = load_engine_config()
PATTERN = [10 + month for month in range(12)]  # 10..21


def _series(values, start: str = "2024-01") -> pd.Series:
    return pd.Series([float(value) for value in values], index=pd.period_range(start, periods=len(values), freq="M"))


def _sales(sku: str, values) -> pd.DataFrame:
    return pd.DataFrame({"Mês": pd.date_range("2024-01-01", periods=len(values), freq="MS"), "SKU": sku, "Quantidade faturada": [float(v) for v in values]})


def _noisy_seasonal(seed: int = 5, sd: float = 1.0) -> pd.Series:
    noise = np.random.default_rng(seed).normal(0, sd, 24)
    return _series([value + extra for value, extra in zip(PATTERN * 2, noise)])


def _config(**changes):
    config = deepcopy(CONFIG)
    config.update(changes)
    return config


@pytest.fixture(scope="module")
def sales():
    return normalise_dataset(load_workbook(SOURCE))["Vendas_24m"]


# --- Origens rolantes ----------------------------------------------------------------------------------------------

def test_origins_for_24_months_are_15_18_21():
    assert rb.rolling_origins(24, 3, 3, 3, 6) == [15, 18, 21]


def test_origins_drop_windows_with_too_short_a_train():
    assert rb.rolling_origins(12, 3, 3, 3, 6) == [6, 9]
    assert rb.rolling_origins(9, 3, 3, 3, 6) == [6]
    assert rb.rolling_origins(8, 3, 3, 3, 6) == []


def test_origins_respect_the_number_of_windows_and_the_step():
    assert rb.rolling_origins(24, 3, 3, 2, 6) == [18, 21]
    assert rb.rolling_origins(24, 3, 1, 3, 6) == [19, 20, 21]


def test_origins_reject_nonpositive_parameters():
    with pytest.raises(ValueError):
        rb.rolling_origins(24, 0, 3, 3, 6)


def test_naive_last_matches_the_validation_center_baseline():
    history = _series([4, 7, 9])
    targets = pd.period_range(history.index[-1] + 1, periods=3, freq="M")
    assert rb.naive_last(history, targets) == _naive_last(history, targets) == [9.0, 9.0, 9.0]
    assert rb.naive_last(_series([]), targets) is None


# --- Backtest rolante ----------------------------------------------------------------------------------------------

def test_constant_series_picks_the_simplest_model_with_zero_error():
    result = rb.rolling_backtest(_series([10] * 24), CONFIG)

    assert result["status"] == "ok"
    assert result["windows"] == 3 and result["window_train_lengths"] == [15, 18, 21]
    assert result["selected_model"] == "moving_average_3"  # todos empatam em 0: vence o mais simples
    assert result["backtest_wape"] == 0.0 and result["backtest_bias"] == 0.0
    assert result["baseline_wape"] == 0.0
    assert result["beats_baseline"] is False  # só supera com WAPE estritamente menor
    assert result["windows_beating_baseline"] == 0 and result["windows_compared"] == 3
    assert [row["model"] for row in result["candidates"]] == list(CANDIDATES) and all(row["eligible"] for row in result["candidates"])


def test_exactly_seasonal_series_selects_seasonal_naive():
    result = rb.rolling_backtest(_series(PATTERN * 2), CONFIG)

    assert result["selected_model"] == "seasonal_naive_12"
    assert result["backtest_wape"] == 0.0
    moving = next(row for row in result["candidates"] if row["model"] == "moving_average_3")
    assert moving["wape"] > 0
    assert sum(row["selected"] for row in result["candidates"]) == 1


def test_pooled_wape_and_bias_are_computed_over_all_windows_by_hand():
    series = _series(range(1, 25))  # 1..24
    result = rb.rolling_backtest(series, CONFIG)
    # Baseline = último mês do treino. Treinos de 15, 18, 21 → previsões 15, 18, 21 para testes (16,17,18), (19,20,21), (22,23,24).
    absolute = (1 + 2 + 3) * 3
    actual = (16 + 17 + 18) + (19 + 20 + 21) + (22 + 23 + 24)
    assert result["baseline_wape"] == round(absolute / actual, 4)
    assert result["baseline_bias"] == round(-absolute / actual, 4)


def test_parsimony_margin_changes_the_winner_when_gain_is_small():
    series = _noisy_seasonal()
    default = rb.rolling_backtest(series, CONFIG)
    strict = rb.rolling_backtest(series, _config(parsimony_margin=0.99))
    lenient = rb.rolling_backtest(series, _config(parsimony_margin=0.0))

    assert default["selected_model"] != "moving_average_3"  # sazonalidade forte: o ganho passa de 5%
    assert strict["selected_model"] == "moving_average_3"  # exigir 99% de ganho trava no mais simples
    best = min((row["wape"], row["model"]) for row in lenient["candidates"] if row["eligible"])
    selected = next(row for row in lenient["candidates"] if row["selected"])
    assert selected["wape"] <= next(row["wape"] for row in lenient["candidates"] if row["model"] == "moving_average_3")
    assert selected["wape"] >= best[0]


def test_baseline_never_competes_for_selection():
    result = rb.rolling_backtest(_noisy_seasonal(seed=9, sd=4), CONFIG)

    assert rb.BASELINE_MODEL not in [row["model"] for row in result["candidates"]]
    assert result["selected_model"] in CANDIDATES


def test_no_future_leaks_into_earlier_windows():
    series = _noisy_seasonal(seed=3, sd=2)
    changed = series.copy()
    changed.iloc[-3:] = [500.0, 1.0, 900.0]  # só o teste da última janela muda
    first, second = rb.rolling_backtest(series, CONFIG), rb.rolling_backtest(changed, CONFIG)

    for code in CANDIDATES:
        before = next(row for row in first["candidates"] if row["model"] == code)["window_wapes"]
        after = next(row for row in second["candidates"] if row["model"] == code)["window_wapes"]
        assert before[:2] == after[:2], code  # janelas de treino 15 e 18: não enxergam os 3 últimos meses
        assert before[2] != after[2], code


def test_short_series_drops_candidates_before_it_drops_the_last_window():
    result = rb.rolling_backtest(_series([10 + (m % 5) for m in range(14)]), CONFIG)
    reasons = {row["model"]: row["reason"] for row in result["candidates"]}
    eligible = [row["model"] for row in result["candidates"] if row["eligible"]]

    assert result["window_train_lengths"] == [11]  # a janela de treino 8 não comporta o Holt (9 meses)
    assert eligible == ["moving_average_3", "ses", "holt_damped"]
    for code in ("seasonal_naive_12", "combo_ma_sn"):
        assert "janelas de teste exigidas" in reasons[code]
    assert "exige 15" in reasons["seasonal_level"]


def test_with_18_months_every_candidate_competes_on_the_one_window_that_fits_all_of_them():
    result = rb.rolling_backtest(_noisy_seasonal().iloc[:18], CONFIG)  # janelas possíveis: 9, 12, 15

    assert result["window_train_lengths"] == [15]
    assert all(row["eligible"] for row in result["candidates"])


def test_requiring_two_windows_sacrifices_the_seasonal_level_at_18_months():
    result = rb.rolling_backtest(_noisy_seasonal().iloc[:18], _config(rolling={**CONFIG["rolling"], "minimum_windows": 2}))

    assert result["window_train_lengths"] == [12, 15]
    assert [row["model"] for row in result["candidates"] if not row["eligible"]] == ["seasonal_level"]


def test_series_shorter_than_nine_months_has_no_rolling_backtest():
    result = rb.rolling_backtest(_series(range(1, 9)), CONFIG)

    assert result["status"] == "insufficient_history"
    assert result["windows"] == 0 and result["selected_model"] is None and result["candidates"] == []


def test_all_zero_demand_has_undefined_wape_and_falls_back_to_moving_average():
    result = rb.rolling_backtest(_series([0] * 24), CONFIG)

    assert result["status"] == "wape_indefinido"
    assert result["selected_model"] == "moving_average_3"
    assert result["backtest_wape"] is None and result["beats_baseline"] is None
    level = next(row for row in result["candidates"] if row["model"] == "seasonal_level")
    assert level["eligible"] is False and "não gerou previsão" in level["reason"]  # nível de um ano atrás = 0 → sem previsão


def test_rolling_backtest_does_not_mutate_its_input():
    series = _noisy_seasonal()
    before = series.copy()
    rb.rolling_backtest(series, CONFIG)
    pd.testing.assert_series_equal(series, before)


# --- Previsões do motor rolante ------------------------------------------------------------------------------------

def test_rolling_forecast_record_for_a_seasonal_sku():
    [record] = rb.build_rolling_forecasts(_sales("SKU-S", PATTERN * 2), CONFIG)

    assert record["model"] == "seasonal_naive_12"
    assert record["forecast_values"] == [10.0, 11.0, 12.0]
    assert record["backtest_wape"] == 0.0 and record["forecast_confidence"] == "alta"
    assert record["status"] == "ok" and record["backtest_windows"] == 3
    assert len(record["candidates"]) == 6 and sum(row["selected"] for row in record["candidates"]) == 1
    assert record["forecast_months"] == ["2026-01-01", "2026-02-01", "2026-03-01"]


def test_rolling_forecast_marks_short_and_insufficient_series_without_inventing_numbers():
    short = rb.build_rolling_forecasts(_sales("A", range(1, 9)), CONFIG)[0]
    tiny = rb.build_rolling_forecasts(_sales("B", [1, 2, 3, 4, 5]), CONFIG)[0]

    assert short["status"] == "insufficient_rolling_history" and short["model"] is None and short["forecast_values"] == []
    assert tiny["status"] == "insufficient_data" and tiny["forecast_next_month"] is None


def test_rolling_forecast_never_returns_negative_values():
    records = rb.build_rolling_forecasts(_sales("SKU-D", [200 - 8 * m for m in range(24)]), CONFIG)
    assert all(value >= 0 for value in records[0]["forecast_values"])


# --- Avaliação aninhada --------------------------------------------------------------------------------------------

def test_nested_baseline_numbers_by_hand_on_a_linear_series():
    result = rb.nested_evaluation(_series(range(1, 25)), config=CONFIG)

    assert result["outer_train_lengths"] == [18, 21]
    baseline = result["procedures"]["baseline"]
    assert baseline["models"] == ["naive_last", "naive_last"]
    assert baseline["abs_error"] == 12 and baseline["actual_total"] == 60 + 69
    assert baseline["wape"] == pytest.approx(12 / 129) and baseline["bias"] == pytest.approx(-12 / 129)
    assert baseline["signed_error"] == -12


def test_nested_constant_series_has_zero_error_everywhere():
    result = rb.nested_evaluation(_series([10] * 24), config=CONFIG)

    for outcome in result["procedures"].values():
        assert outcome["wape"] == 0.0 and outcome["bias"] == 0.0
    assert result["procedures"]["v1"]["models"] == ["moving_average_3"] * 2  # empate: pelo código, como o motor atual
    assert result["procedures"]["rolling"]["models"] == ["moving_average_3"] * 2


def test_procedures_only_receive_the_training_part():
    seen: list[int] = []

    def spy(train: pd.Series) -> str:
        seen.append(len(train))
        return "moving_average_3"

    rb.nested_evaluation(_series(range(1, 25)), {"spy": spy}, CONFIG)
    assert seen == [18, 21]


def test_a_procedure_that_returns_an_unusable_model_falls_back_to_moving_average():
    # seasonal_level exige 15 meses: com treino curto o resultado é None e o recuo é a média móvel.
    short = _series(range(1, 13))
    assert rb._predict("seasonal_level", short, pd.period_range(short.index[-1] + 1, periods=3, freq="M")) == rb._predict(
        "moving_average_3", short, pd.period_range(short.index[-1] + 1, periods=3, freq="M")
    )


def test_nested_table_aggregates_weighted_across_skus():
    sales = pd.concat([_sales("CONST", [10] * 24), _sales("LINEAR", range(1, 25))])
    table = rb.nested_evaluation_table(sales, CONFIG)

    assert table["skus"] == 2
    assert table["aggregate"]["baseline"]["weighted_wape"] == pytest.approx(12 / (60 + 129))
    assert table["aggregate"]["baseline"]["weighted_bias"] == pytest.approx(-12 / (60 + 129))
    assert set(table["rolling_vs_v1"]) == {"rolling_better", "equal", "rolling_worse"}
    assert sum(table["rolling_vs_v1"].values()) == 2
    assert "all_met" in table["criteria"]


# --- Critérios de promoção -----------------------------------------------------------------------------------------

def _aggregate(new_wape, old_wape, new_bias=0.0, old_bias=0.0, new_beat=10, old_beat=10):
    return {"aggregate": {
        "rolling": {"weighted_wape": new_wape, "weighted_bias": new_bias, "skus_beating_baseline": new_beat},
        "v1": {"weighted_wape": old_wape, "weighted_bias": old_bias, "skus_beating_baseline": old_beat},
    }}


def test_promotion_criteria_all_met():
    verdict = rb.promotion_criteria(_aggregate(0.0900, 0.1000), CONFIG)  # ganho relativo de 10%
    assert verdict["all_met"] is True and verdict["relative_wape_gain"] == pytest.approx(0.10)


def test_promotion_criteria_fail_on_small_gain():
    verdict = rb.promotion_criteria(_aggregate(0.0960, 0.1000), CONFIG)  # 4% < 5%
    assert verdict["wape_criterion_met"] is False and verdict["all_met"] is False


def test_promotion_criteria_gain_exactly_at_the_threshold_passes():
    assert rb.promotion_criteria(_aggregate(0.0950, 0.1000), CONFIG)["wape_criterion_met"] is True


def test_promotion_criteria_fail_when_bias_worsens_too_much():
    verdict = rb.promotion_criteria(_aggregate(0.09, 0.10, new_bias=-0.05, old_bias=-0.01), CONFIG)  # +4 p.p.
    assert verdict["bias_worsening_pp"] == pytest.approx(4.0)
    assert verdict["bias_criterion_met"] is False and verdict["all_met"] is False


def test_promotion_criteria_tolerate_a_bias_change_inside_the_limit():
    verdict = rb.promotion_criteria(_aggregate(0.09, 0.10, new_bias=-0.03, old_bias=-0.01), CONFIG)  # +2 p.p.
    assert verdict["bias_criterion_met"] is True


def test_promotion_criteria_fail_when_fewer_skus_beat_the_baseline():
    verdict = rb.promotion_criteria(_aggregate(0.09, 0.10, new_beat=9, old_beat=10), CONFIG)
    assert verdict["baseline_criterion_met"] is False and verdict["all_met"] is False


def test_promotion_criteria_undefined_wape_never_passes():
    verdict = rb.promotion_criteria(_aggregate(None, 0.10), CONFIG)
    assert verdict["relative_wape_gain"] is None and verdict["all_met"] is False
    assert rb.promotion_criteria(_aggregate(0.0, 0.0), CONFIG)["all_met"] is False


# --- Base real -----------------------------------------------------------------------------------------------------

def test_v1_procedure_reproduces_the_official_model_choice(sales):
    official = build_demand_forecasts(sales).set_index("sku")["model"]
    for sku in official.index:
        assert rb.v1_procedure(_monthly_series(sales, sku)) == official[sku], sku


def test_every_real_sku_gets_three_windows_and_six_eligible_candidates(sales):
    records = rb.build_rolling_forecasts(sales, CONFIG)

    assert len(records) == 50
    for record in records:
        assert record["status"] == "ok" and record["backtest_windows"] == 3, record["sku"]
        assert sum(row["eligible"] for row in record["candidates"]) == 6, record["sku"]
        assert sum(row["selected"] for row in record["candidates"]) == 1, record["sku"]
        assert len(record["forecast_values"]) == 3 and all(math.isfinite(v) and v >= 0 for v in record["forecast_values"]), record["sku"]


def test_nested_table_on_the_real_base_is_complete_and_leaves_official_numbers_alone(sales):
    before = build_demand_forecasts(sales).to_json()
    table = rb.nested_evaluation_table(sales, CONFIG)

    assert table["skus"] == 50 and all(row["outer_train_lengths"] == [18, 21] for row in table["rows"])
    for name in ("v1", "rolling", "baseline"):
        aggregate = table["aggregate"][name]
        assert aggregate["weighted_wape"] is not None and math.isfinite(aggregate["weighted_wape"])
        assert math.isfinite(aggregate["weighted_bias"])
    assert sum(table["rolling_vs_v1"].values()) == 50
    assert build_demand_forecasts(sales).to_json() == before


# --- Memória do cálculo e grade de sensibilidade (14.3) -------------------------------------------------------------

def test_cached_run_is_identical_to_the_direct_candidate_call():
    rng = np.random.default_rng(21)
    history = _series(np.abs(rng.normal(100, 30, 21)).round(1))
    targets = pd.period_range(history.index[-1] + 1, periods=3, freq="M")
    for code in CANDIDATES:
        direct = rb.run_candidate(code, history, targets)
        assert rb._run(code, history, targets) == direct, code
        assert rb._run(code, history, targets) == direct, code  # segunda chamada vem da memória


def test_cached_run_falls_back_to_the_direct_call_for_non_contiguous_history():
    gapped = _series(range(1, 19))
    gapped = gapped.drop(gapped.index[5])  # buraco no meio: a memória não deve ser usada
    targets = pd.period_range(gapped.index[-1] + 1, periods=3, freq="M")
    assert rb._run("moving_average_3", gapped, targets) == rb.run_candidate("moving_average_3", gapped, targets)


def test_sensitivity_grid_covers_every_combination_and_marks_the_default_once():
    sales = pd.concat([_sales("CONST", [10] * 24), _sales("SEAS", PATTERN * 2), _sales("LINEAR", range(1, 25))])
    cells = rb.sensitivity_grid(sales, CONFIG)

    assert [(cell["outer_windows"], cell["minimum_windows"]) for cell in cells] == [(1, 1), (1, 2), (2, 1), (2, 2), (3, 1), (3, 2)]
    assert [cell["is_default"] for cell in cells].count(True) == 1
    default = next(cell for cell in cells if cell["is_default"])
    assert (default["outer_windows"], default["minimum_windows"]) == (CONFIG["nested"]["outer_windows"], CONFIG["rolling"]["minimum_windows"])
    assert [cell["outer_train_lengths"] for cell in cells[::2]] == [[21], [18, 21], [15, 18, 21]]
    assert all(cell["skus"] == 3 for cell in cells)
    # A célula padrão é exatamente a avaliação aninhada padrão.
    table = rb.nested_evaluation_table(sales, CONFIG)
    assert default["rolling_wape"] == table["aggregate"]["rolling"]["weighted_wape"]
    assert default["relative_wape_gain"] == table["criteria"]["relative_wape_gain"]
    assert default["all_met"] == table["criteria"]["all_met"]
    assert default["rolling_better_skus"] + default["equal_skus"] + default["rolling_worse_skus"] == 3


def test_sensitivity_grid_does_not_change_the_config_it_receives():
    before = deepcopy(CONFIG)
    rb.sensitivity_grid(_sales("X", PATTERN * 2), CONFIG)
    assert CONFIG == before


def test_sensitivity_summary_counts_cells_and_reports_the_gain_range():
    cells = [
        {"is_default": True, "all_met": True, "relative_wape_gain": 0.2},
        {"is_default": False, "all_met": True, "relative_wape_gain": 0.1},
        {"is_default": False, "all_met": False, "relative_wape_gain": -0.3},
        {"is_default": False, "all_met": False, "relative_wape_gain": None},
    ]
    summary = rb.summarize_sensitivity(cells)

    assert summary == {"cells": 4, "cells_all_met": 2, "robust": False, "default_all_met": True,
                       "min_relative_wape_gain": -0.3, "max_relative_wape_gain": 0.2}
    assert rb.summarize_sensitivity(cells[:2])["robust"] is True
    empty = rb.summarize_sensitivity([])
    assert empty["robust"] is False and empty["default_all_met"] is None and empty["min_relative_wape_gain"] is None
