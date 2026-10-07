from __future__ import annotations

import json
from copy import deepcopy

import pytest

from caderno_inteligente.forecast_candidates import CANDIDATES
from caderno_inteligente.forecast_engine_config import DEFAULTS, load_engine_config


def _write(tmp_path, **changes):
    values = deepcopy(DEFAULTS)
    values.update(changes)
    path = tmp_path / "forecast_engine.json"
    path.write_text(json.dumps(values), encoding="utf-8")
    return path


def test_versioned_config_loads_with_the_plan_defaults():
    config = load_engine_config()

    assert config["engine"] == "v1"
    assert config["candidates"] == list(CANDIDATES)
    assert config["rolling"] == {"windows": 3, "step_months": 3, "horizon_months": 3, "minimum_train_months": 6, "minimum_windows": 1}
    assert config["nested"] == {"outer_windows": 2}
    assert config["sensitivity"] == {"outer_windows": [1, 2, 3], "minimum_windows": [1, 2]}
    assert config["parsimony_margin"] == 0.05
    assert config["promotion"] == {"min_relative_wape_gain": 0.05, "max_bias_worsening_pp": 2.0}


def test_partial_file_falls_back_to_defaults_per_section(tmp_path):
    path = tmp_path / "forecast_engine.json"
    path.write_text(json.dumps({"rolling": {"windows": 2}}), encoding="utf-8")

    config = load_engine_config(path)

    assert config["rolling"]["windows"] == 2
    assert config["rolling"]["step_months"] == 3
    assert config["candidates"] == list(CANDIDATES)


@pytest.mark.parametrize(
    "changes, message",
    [
        ({"engine": "rolling"}, "Motor de previsão inválido"),
        ({"candidates": ["moving_average_3", "seasonal_naive_12", "arima"]}, "desconhecidos"),
        ({"candidates": ["moving_average_3", "moving_average_3", "seasonal_naive_12"]}, "repetir"),
        ({"candidates": ["ses", "holt_damped"]}, "modelos atuais"),
        ({"candidates": "ses"}, "lista"),
        ({"rolling": {"windows": 0}}, "inteiro"),
        ({"rolling": {"windows": 2.5}}, "inteiro"),
        ({"rolling": {"minimum_train_months": 5}}, "histórico mínimo"),
        ({"rolling": {"windows": 3, "extra": 1}}, "desconhecidos em rolling"),
        ({"rolling": {"minimum_windows": 0}}, "inteiro"),
        ({"rolling": {"windows": 2, "minimum_windows": 3}}, "minimum_windows"),
        ({"nested": {"outer_windows": 0}}, "inteiro"),
        ({"nested": {"outer_windows": 2, "extra": 1}}, "desconhecidos em nested"),
        ({"sensitivity": {"outer_windows": []}}, "lista não vazia"),
        ({"sensitivity": {"outer_windows": "2"}}, "lista não vazia"),
        ({"sensitivity": {"outer_windows": [1, 1]}}, "repetir"),
        ({"sensitivity": {"minimum_windows": [0]}}, "inteiro"),
        ({"sensitivity": {"minimum_windows": [4]}}, "rolling.windows"),
        ({"sensitivity": {"extra": [1]}}, "desconhecidos em sensitivity"),
        ({"parsimony_margin": 1}, "parsimony_margin"),
        ({"parsimony_margin": True}, "inválido"),
        ({"promotion": {"min_relative_wape_gain": -0.1}}, "promoção"),
        ({"promotion": {"max_bias_worsening_pp": -1}}, "promoção"),
        ({"promotion": {"surprise": 1}}, "desconhecidos em promotion"),
        ({"unknown_key": 1}, "campos desconhecidos"),
    ],
)
def test_invalid_config_is_rejected(tmp_path, changes, message):
    path = tmp_path / "forecast_engine.json"
    path.write_text(json.dumps(changes), encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        load_engine_config(path)


def test_defaults_are_not_mutated_by_loading(tmp_path):
    before = deepcopy(DEFAULTS)
    load_engine_config(_write(tmp_path, parsimony_margin=0.1))
    assert DEFAULTS == before


def test_sensitivity_grid_is_sorted_on_load(tmp_path):
    path = tmp_path / "forecast_engine.json"
    path.write_text(json.dumps({"sensitivity": {"outer_windows": [3, 1, 2]}}), encoding="utf-8")
    assert load_engine_config(path)["sensitivity"]["outer_windows"] == [1, 2, 3]
