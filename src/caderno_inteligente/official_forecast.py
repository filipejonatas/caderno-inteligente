"""Previsão oficial de demanda: despacha para o motor configurado (Etapa 15.1).

- `v1`: `forecasting.build_demand_forecasts`, sem nenhuma alteração (escolhe entre média móvel de 3 meses e sazonal
  ingênuo de 12 meses no holdout dos últimos 3 meses; horizonte de 3 meses).
- `v2`: não há seleção por SKU. Vale a primeira previsão possível da cadeia `official.model_chain` (padrão: mês do ano
  anterior ajustado pelo nível → sazonal ingênuo → média móvel), com horizonte de `official.horizon_months` (6) meses.
  O erro e a confiança vêm de origens rolantes fixadas no protocolo (`evaluation`), que incluem meses de pico; a mesma
  cadeia é refeita em cada origem só com os dados anteriores a ela.

Os campos de 3 meses (`forecast_next_month`, `forecast_total_3m`) mantêm o significado nos dois motores.
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from .forecast_candidates import CANDIDATE_LABELS, CANDIDATES, run_candidate, seasonal_level
from .forecast_engine_config import load_engine_config
from .forecasting import _confidence, _insufficient, _monthly_series, _trend, build_demand_forecasts

MINIMUM_HISTORY_MONTHS = 6  # o mesmo mínimo do motor v1

V2_LIMITATION = (
    "Previsão estatística sobre o faturamento mensal: mesmo mês do ano anterior ajustado pelo nível recente. "
    "Repete a sazonalidade observada; não incorpora campanhas novas, lançamentos nem alocação por parceiro."
)
ENGINE_LABELS = {
    "v1": "Motor v1: escolhe entre média móvel de 3 meses e sazonal ingênuo no teste dos últimos 3 meses",
    "v2": "Motor v2: mês do ano anterior ajustado pelo nível, com erro medido em origens rolantes que incluem meses de pico",
}


def run_model(code: str, history: pd.Series, targets: pd.PeriodIndex, config: dict[str, Any]) -> list[float] | None:
    """Previsão de um modelo da cadeia; `seasonal_level` usa o limite de razão da configuração."""
    if len(history) < CANDIDATES[code].min_history:
        return None
    if code == "seasonal_level":
        low, high = config["seasonal_level"]["ratio_bounds"]
        return seasonal_level(history, targets, (low, high))
    return run_candidate(code, history, targets)


def chain_forecast(history: pd.Series, targets: pd.PeriodIndex, config: dict[str, Any]) -> tuple[str | None, list[float] | None]:
    """Primeiro modelo da cadeia que consegue prever todos os meses-alvo, com a previsão (nunca negativa)."""
    for code in config["official"]["model_chain"]:
        predicted = run_model(code, history, targets, config)
        if predicted is not None:
            return code, [max(0.0, float(value)) for value in predicted]
    return None, None


def evaluation_origins(series: pd.Series, config: dict[str, Any]) -> list[pd.Period]:
    """Origens do protocolo presentes na série e com todos os meses de teste observados."""
    if series.empty:
        return []
    evaluation = config["evaluation"]
    horizon = evaluation["horizon_months"]
    candidates = pd.period_range(evaluation["first_origin"], evaluation["last_origin"], freq="M")
    first, last = series.index.min(), series.index.max()
    return [origin for origin in candidates if first <= origin and origin + horizon <= last]


def chain_windows(series: pd.Series, config: dict[str, Any], origins: list[pd.Period] | None = None) -> list[dict[str, Any]]:
    """Refaz a cadeia em cada origem só com dados anteriores a ela; uma janela por origem com real, previsto e modelo."""
    horizon = config["evaluation"]["horizon_months"]
    windows = []
    for origin in evaluation_origins(series, config) if origins is None else origins:
        train = series[series.index <= origin]
        if len(train) < MINIMUM_HISTORY_MONTHS:
            continue
        targets = pd.period_range(origin + 1, periods=horizon, freq="M")
        code, predicted = chain_forecast(train, targets, config)
        if predicted is None:
            continue
        windows.append({"origin": str(origin), "model": code, "months": [period.month for period in targets],
                        "actual": [float(value) for value in series.reindex(targets).tolist()], "predicted": predicted})
    return windows


def window_errors(windows: list[dict[str, Any]], peak_months: list[int] | None = None) -> dict[str, float]:
    """Σ|erro|, Σ(previsto − real) e Σ real das janelas, no total e separados em meses de pico e normais."""
    peaks = set(peak_months or [])
    totals = {f"{part}_{kind}": 0.0 for part in ("all", "peak", "normal") for kind in ("abs", "signed", "actual")}
    for window in windows:
        for month, real, predicted in zip(window["months"], window["actual"], window["predicted"]):
            for part in ("all", "peak" if month in peaks else "normal"):
                totals[f"{part}_abs"] += abs(predicted - real)
                totals[f"{part}_signed"] += predicted - real
                totals[f"{part}_actual"] += real
    return totals


def ratio(numerator: float, denominator: float) -> float | None:
    return None if denominator <= 0 else numerator / denominator


def _v2_record(sku: str, series: pd.Series, config: dict[str, Any]) -> dict[str, Any]:
    if len(series) < MINIMUM_HISTORY_MONTHS:
        return {**_insufficient(sku, series), "engine": "v2"}
    horizon = config["official"]["horizon_months"]
    future = pd.period_range(series.index.max() + 1, periods=horizon, freq="M")
    model, predicted = chain_forecast(series, future, config)
    if predicted is None:
        return {**_insufficient(sku, series), "engine": "v2"}

    windows = chain_windows(series, config)
    errors = window_errors(windows, config["evaluation"]["peak_months"])
    wape = ratio(errors["all_abs"], errors["all_actual"])
    values = [round(value, 1) for value in predicted]
    trend, change = _trend(series)
    return {
        "sku": sku,
        "reference_month": series.index.max().to_timestamp().date().isoformat(),
        "history_months": int(len(series)),
        "model": model,
        "model_label": CANDIDATE_LABELS[model],
        "forecast_months": [period.to_timestamp().date().isoformat() for period in future],
        "forecast_values": values,
        "forecast_next_month": values[0],
        "forecast_total_3m": round(sum(values[:3]), 1),
        "forecast_total_6m": round(sum(values[:6]), 1) if horizon >= 6 else None,
        "trend": trend,
        "trend_change_ratio": None if change is None else round(change, 4),
        "backtest_wape": None if wape is None else round(wape, 4),
        "backtest_bias": None if wape is None else round(errors["all_signed"] / errors["all_actual"], 4),
        "backtest_peak_wape": None if (value := ratio(errors["peak_abs"], errors["peak_actual"])) is None else round(value, 4),
        "backtest_windows": len(windows),
        "backtest_origins": [window["origin"] for window in windows],
        "backtest_abs_error_units": round(errors["all_abs"], 1),
        "backtest_actual_units": round(errors["all_actual"], 1),
        "forecast_confidence": _confidence(wape),
        "status": "ok",
        "limitation": V2_LIMITATION,
        "engine": "v2",
        "horizon_months": horizon,
    }


def build_official_forecasts(sales: pd.DataFrame, config: dict[str, Any] | None = None,
                             series_map: dict[str, pd.Series] | None = None) -> pd.DataFrame:
    """Previsão oficial por SKU segundo `config["engine"]`."""
    config = load_engine_config() if config is None else config
    if config["engine"] == "v1":
        return build_demand_forecasts(sales)
    skus = sorted(sales["SKU"].dropna().astype(str).unique())
    records = [_v2_record(sku, series_map[sku] if series_map and sku in series_map else _monthly_series(sales, sku), config) for sku in skus]
    return pd.DataFrame(records)
