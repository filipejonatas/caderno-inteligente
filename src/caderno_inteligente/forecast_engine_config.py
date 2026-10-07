"""Configuração do motor de previsão da Etapa 14, validada no carregamento (campos desconhecidos são rejeitados).

O motor `v1` (`forecasting.py`) é o único aceito por enquanto: o motor com backtest rolante só passa a existir se a
Etapa 14.5 aprovar a promoção, e uma chave que não faz nada seria um risco silencioso.
"""
from __future__ import annotations

import json
import math
from copy import deepcopy
from pathlib import Path
from typing import Any

import pandas as pd

from .forecast_candidates import CANDIDATES

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "config" / "forecast_engine.json"
ENGINES = ("v1",)
REQUIRED_CANDIDATES = ("moving_average_3", "seasonal_naive_12")  # os modelos atuais: sem eles não há comparação com o v1

DEFAULTS: dict[str, Any] = {
    "engine": "v1",
    "candidates": list(CANDIDATES),
    "rolling": {"windows": 3, "step_months": 3, "horizon_months": 3, "minimum_train_months": 6, "minimum_windows": 1},
    "nested": {"outer_windows": 2},
    "sensitivity": {"outer_windows": [1, 2, 3], "minimum_windows": [1, 2]},
    "intervals": {"lower_quantile": 0.1, "upper_quantile": 0.9, "minimum_residuals": 6},
    "parsimony_margin": 0.05,
    "promotion": {"min_relative_wape_gain": 0.05, "max_bias_worsening_pp": 2.0},
    # Etapa 15: protocolo da avaliação com meses de pico, gravado antes de o motor v2 existir (consumido na 15.1).
    "evaluation": {"first_origin": "2025-11", "last_origin": "2026-05", "horizon_months": 3, "peak_months": [11, 1, 2], "max_abs_peak_bias": 0.10},
}


def _number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"Parâmetro do motor de previsão inválido: {name}")
    return float(value)


def _integer(value: Any, name: str, minimum: int) -> int:
    number = _number(value, name)
    if number != int(number) or number < minimum:
        raise ValueError(f"Parâmetro do motor de previsão precisa ser inteiro ≥ {minimum}: {name}")
    return int(number)


def _section(values: dict[str, Any], key: str) -> dict[str, Any]:
    section = values[key]
    if not isinstance(section, dict) or set(section) - set(DEFAULTS[key]):
        raise ValueError(f"Configuração do motor de previsão contém campos desconhecidos em {key}")
    return {**DEFAULTS[key], **section}


def load_engine_config(path: str | Path | None = None) -> dict[str, Any]:
    values = deepcopy(DEFAULTS)
    source = DEFAULT_PATH if path is None else Path(path)
    if source.exists() or path is not None:
        overrides = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(overrides, dict) or set(overrides) - set(values):
            raise ValueError("Configuração do motor de previsão contém campos desconhecidos")
        values.update(overrides)
    return validate_engine_config(values)


def validate_engine_config(values: dict[str, Any]) -> dict[str, Any]:
    if values["engine"] not in ENGINES:
        raise ValueError(f"Motor de previsão inválido: {values['engine']!r}. Aceitos: {', '.join(ENGINES)}")

    candidates = values["candidates"]
    if not isinstance(candidates, list) or not all(isinstance(item, str) for item in candidates):
        raise ValueError("candidates deve ser uma lista de códigos de modelo")
    if len(set(candidates)) != len(candidates):
        raise ValueError("candidates não pode repetir modelos")
    unknown = [item for item in candidates if item not in CANDIDATES]
    if unknown:
        raise ValueError(f"Modelos desconhecidos em candidates: {', '.join(unknown)}")
    missing = [item for item in REQUIRED_CANDIDATES if item not in candidates]
    if missing:
        raise ValueError(f"candidates precisa manter os modelos atuais: {', '.join(missing)}")

    rolling = _section(values, "rolling")
    for key in ("windows", "step_months", "horizon_months", "minimum_train_months", "minimum_windows"):
        rolling[key] = _integer(rolling[key], f"rolling.{key}", 1)
    if rolling["minimum_train_months"] < 6:
        raise ValueError("rolling.minimum_train_months não pode ser menor que o histórico mínimo de 6 meses")
    if rolling["minimum_windows"] > rolling["windows"]:
        raise ValueError("rolling.minimum_windows não pode ser maior que rolling.windows")
    values["rolling"] = rolling

    nested = _section(values, "nested")
    nested["outer_windows"] = _integer(nested["outer_windows"], "nested.outer_windows", 1)
    values["nested"] = nested

    sensitivity = _section(values, "sensitivity")
    for key in ("outer_windows", "minimum_windows"):
        grid = sensitivity[key]
        if not isinstance(grid, list) or not grid:
            raise ValueError(f"sensitivity.{key} deve ser uma lista não vazia")
        grid = [_integer(item, f"sensitivity.{key}", 1) for item in grid]
        if len(set(grid)) != len(grid):
            raise ValueError(f"sensitivity.{key} não pode repetir valores")
        sensitivity[key] = sorted(grid)
    if max(sensitivity["minimum_windows"]) > rolling["windows"]:
        raise ValueError("sensitivity.minimum_windows não pode passar de rolling.windows")
    values["sensitivity"] = sensitivity

    intervals = _section(values, "intervals")
    lower = _number(intervals["lower_quantile"], "intervals.lower_quantile")
    upper = _number(intervals["upper_quantile"], "intervals.upper_quantile")
    if not 0 <= lower < 0.5 < upper <= 1:
        raise ValueError("intervals: use 0 ≤ lower_quantile < 0,5 < upper_quantile ≤ 1")
    values["intervals"] = {"lower_quantile": lower, "upper_quantile": upper, "minimum_residuals": _integer(intervals["minimum_residuals"], "intervals.minimum_residuals", 3)}

    margin = _number(values["parsimony_margin"], "parsimony_margin")
    if not 0 <= margin < 1:
        raise ValueError("parsimony_margin deve estar em [0, 1)")
    values["parsimony_margin"] = margin

    promotion = _section(values, "promotion")
    gain = _number(promotion["min_relative_wape_gain"], "promotion.min_relative_wape_gain")
    worsening = _number(promotion["max_bias_worsening_pp"], "promotion.max_bias_worsening_pp")
    if not 0 <= gain < 1 or worsening < 0:
        raise ValueError("Critérios de promoção inválidos")
    values["promotion"] = {"min_relative_wape_gain": gain, "max_bias_worsening_pp": worsening}

    evaluation = _section(values, "evaluation")
    origins = []
    for key in ("first_origin", "last_origin"):
        try:
            origins.append(pd.Period(str(evaluation[key]), freq="M"))
        except (ValueError, TypeError) as error:
            raise ValueError(f"evaluation.{key} deve ser um mês AAAA-MM") from error
    if origins[0] > origins[1]:
        raise ValueError("evaluation.first_origin não pode ser posterior a evaluation.last_origin")
    peaks = evaluation["peak_months"]
    if not isinstance(peaks, list) or not peaks:
        raise ValueError("evaluation.peak_months deve ser uma lista não vazia")
    peaks = [_integer(item, "evaluation.peak_months", 1) for item in peaks]
    if len(set(peaks)) != len(peaks) or max(peaks) > 12:
        raise ValueError("evaluation.peak_months deve ter meses distintos entre 1 e 12")
    peak_bias = _number(evaluation["max_abs_peak_bias"], "evaluation.max_abs_peak_bias")
    if not 0 < peak_bias < 1:
        raise ValueError("evaluation.max_abs_peak_bias deve estar em (0, 1)")
    values["evaluation"] = {
        "first_origin": str(origins[0]), "last_origin": str(origins[1]),
        "horizon_months": _integer(evaluation["horizon_months"], "evaluation.horizon_months", 1),
        "peak_months": peaks, "max_abs_peak_bias": peak_bias,
    }
    return values
