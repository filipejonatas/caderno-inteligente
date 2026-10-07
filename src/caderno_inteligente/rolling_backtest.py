"""Backtest com origem rolante e avaliação aninhada dos candidatos de previsão (Etapa 14.2).

Seleção (`rolling_backtest`): cada candidato é treinado em janelas crescentes e medido nos meses seguintes; vale o WAPE
agrupado (Σ|erro| ÷ Σ real) de todas as janelas. Um candidato mais complexo só vence se reduzir esse WAPE em pelo menos
`parsimony_margin` (relativo) sobre o vencedor parcial mais simples. A baseline (repetir o último mês) é medida nas mesmas
janelas, mas nunca participa da seleção.

Avaliação aninhada (`nested_evaluation`): o WAPE do vencedor, medido nas mesmas janelas em que foi escolhido, é otimista.
Aqui cada procedimento (motor atual, motor rolante, baseline) escolhe o modelo só com dados anteriores a cada origem
externa e é medido nos meses seguintes. É esta medida que sustenta a decisão de promoção da Etapa 14.5.

Nada aqui altera `forecasting.py` nem é chamado pelo pipeline oficial.
"""
from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
from typing import Any, Callable

import pandas as pd

from .forecast_candidates import CANDIDATES, applicable_candidates, run_candidate
from .forecast_engine_config import load_engine_config
from .forecasting import _MODELS, _backtest, _confidence, _insufficient, _monthly_series, _trend

BASELINE_MODEL = "naive_last"
BASELINE_LABEL = "Ingênuo do último mês (baseline)"
FALLBACK_MODEL = "moving_average_3"  # o mesmo recuo do motor atual quando nada é avaliável
MINIMUM_HISTORY = 6
LIMITATION = "Previsão estatística baseada em faturamento mensal, escolhida por backtest rolante; não incorpora causalidade, campanhas futuras ou alocação por parceiro."


def naive_last(history: pd.Series, targets: pd.PeriodIndex) -> list[float] | None:
    """Baseline: repete o último mês observado. Mesma definição da Central de validação."""
    if history.empty:
        return None
    return [max(0.0, float(history.iloc[-1]))] * len(targets)


@lru_cache(maxsize=200_000)
def _run_cached(code: str, values: tuple[float, ...], start: int, horizon: int) -> tuple[float, ...] | None:
    history = pd.Series(values, index=pd.period_range(pd.Period(ordinal=start, freq="M"), periods=len(values), freq="M"))
    predicted = run_candidate(code, history, pd.period_range(history.index[-1] + 1, periods=horizon, freq="M"))
    return None if predicted is None else tuple(predicted)


def _run(code: str, history: pd.Series, targets: pd.PeriodIndex) -> list[float] | None:
    """`run_candidate` com memória: o mesmo treino reaparece em várias origens e células da grade de sensibilidade.

    O resultado é idêntico ao da chamada direta; a memória só vale para série mensal contínua seguida pelos meses-alvo.
    """
    index = history.index
    contiguous = (
        isinstance(index, pd.PeriodIndex) and index.freqstr == "M" and len(index) > 0
        and index[-1].ordinal - index[0].ordinal == len(index) - 1
        and len(targets) > 0 and targets[0] == index[-1] + 1 and targets[-1].ordinal - targets[0].ordinal == len(targets) - 1
    )
    if not contiguous:
        return run_candidate(code, history, targets)
    cached = _run_cached(code, tuple(float(value) for value in history.tolist()), index[0].ordinal, len(targets))
    return None if cached is None else list(cached)


def rolling_origins(n: int, horizon: int, step: int, windows: int, minimum_train: int) -> list[int]:
    """Tamanhos de treino (em ordem crescente) das janelas cujo teste termina em n, n − step, n − 2·step…

    Janelas com treino menor que `minimum_train` são descartadas; a lista pode vir vazia ou com menos de `windows` itens.
    """
    if min(horizon, step, windows, minimum_train) < 1:
        raise ValueError("horizon, step, windows e minimum_train precisam ser positivos")
    return sorted(origin for origin in (n - horizon - index * step for index in range(windows)) if origin >= minimum_train)


def _rounded(value: float | None) -> float | None:
    return None if value is None else round(float(value), 4)


def _pooled(windows: list[tuple[list[float], list[float]]]) -> tuple[float | None, float | None]:
    """WAPE e viés (Σ(previsto − real) ÷ Σ real) agrupados; `None` se a demanda real soma zero."""
    actual = sum(sum(real) for real, _ in windows)
    if actual <= 0:
        return None, None
    absolute = sum(abs(r - p) for real, predicted in windows for r, p in zip(real, predicted))
    signed = sum(p - r for real, predicted in windows for r, p in zip(real, predicted))
    return absolute / actual, signed / actual


def _window_wape(real: list[float], predicted: list[float]) -> float | None:
    return _pooled([(real, predicted)])[0]


def _totals(windows: list[tuple[list[float], list[float]]]) -> tuple[float, float, float]:
    """Σ|erro|, Σ(previsto − real) e Σ real: o que se soma entre SKUs para o WAPE e o viés ponderados."""
    return (
        sum(abs(r - p) for real, predicted in windows for r, p in zip(real, predicted)),
        sum(p - r for real, predicted in windows for r, p in zip(real, predicted)),
        sum(sum(real) for real, _ in windows),
    )


def _select_windows(all_origins: list[int], pool: list[str], required: int) -> tuple[list[int], list[str], dict[str, str]]:
    """Maior conjunto de candidatos que ainda deixa `required` janelas; descarta primeiro o de maior histórico mínimo."""
    codes, dropped = list(pool), {}
    while True:
        origins = [origin for origin in all_origins if all(origin >= CANDIDATES[code].min_history for code in codes)]
        if len(origins) >= required or len(codes) <= 1:
            return origins, codes, dropped
        drop = max(codes, key=lambda code: (CANDIDATES[code].min_history, CANDIDATES[code].complexity))
        codes.remove(drop)
        dropped[drop] = f"histórico mínimo de {CANDIDATES[drop].min_history} meses não deixa as {required} janelas de teste exigidas"


def rolling_backtest(series: pd.Series, config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Seleciona o candidato de um SKU por backtest rolante. Só usa dados dentro de `series`."""
    config = load_engine_config() if config is None else config
    rolling = config["rolling"]
    horizon, minimum_windows = rolling["horizon_months"], rolling["minimum_windows"]
    n = len(series)
    all_origins = rolling_origins(n, horizon, rolling["step_months"], rolling["windows"], rolling["minimum_train_months"])
    base = {"history_months": n, "horizon_months": horizon, "windows": 0, "window_train_lengths": [], "candidates": [], "baseline_wape": None}
    if not all_origins:
        return {**base, "status": "insufficient_history", "selected_model": None, "selected_label": None, "backtest_wape": None, "backtest_bias": None,
                "beats_baseline": None, "windows_beating_baseline": None, "windows_compared": 0}

    enabled = list(config["candidates"])
    pool = applicable_candidates(n, enabled)
    reasons: dict[str, str] = {code: f"série com {n} meses; o modelo exige {CANDIDATES[code].min_history}" for code in enabled if code not in pool}
    origins, codes, dropped = _select_windows(all_origins, pool, min(minimum_windows, len(all_origins)))
    reasons.update(dropped)

    runs: dict[str, list[tuple[list[float], list[float]]]] = {code: [] for code in codes}
    baseline_runs: list[tuple[list[float], list[float]]] = []
    for origin in origins:
        train, test = series.iloc[:origin], series.iloc[origin : origin + horizon]
        real = [float(value) for value in test.tolist()]
        baseline_runs.append((real, naive_last(train, test.index)))
        for code in codes:
            predicted = _run(code, train, test.index) if code in runs else None
            if predicted is None:
                runs.pop(code, None)
                reasons[code] = "o modelo não gerou previsão em alguma janela"
            else:
                runs[code].append((real, predicted))
    eligible = [code for code in codes if code in runs]

    baseline_wape, baseline_bias = _pooled(baseline_runs)
    baseline_windows = [_window_wape(real, predicted) for real, predicted in baseline_runs]
    rows: dict[str, dict[str, Any]] = {}
    for code in eligible:
        wape, bias = _pooled(runs[code])
        window_wapes = [_window_wape(real, predicted) for real, predicted in runs[code]]
        compared = [(own, ref) for own, ref in zip(window_wapes, baseline_windows) if own is not None and ref is not None]
        rows[code] = {
            "wape": wape,
            "bias": bias,
            "window_wapes": [_rounded(value) for value in window_wapes],
            "windows_beating_baseline": sum(own < ref for own, ref in compared),
            "windows_compared": len(compared),
        }

    # Parcimônia: do mais simples ao mais complexo, o desafiante só assume se reduzir o WAPE em `margin` (relativo).
    margin = config["parsimony_margin"]
    selected: str | None = None
    for code in eligible:
        wape = rows[code]["wape"]
        if wape is None:
            continue
        if selected is None or wape < rows[selected]["wape"] * (1 - margin):
            selected = code
    status = "ok"
    if selected is None:
        status = "wape_indefinido"
        selected = FALLBACK_MODEL if FALLBACK_MODEL in eligible else eligible[0]

    table = []
    for code in sorted(enabled, key=lambda item: CANDIDATES[item].complexity):
        candidate = CANDIDATES[code]
        row = rows.get(code)
        table.append(
            {
                "model": code,
                "label": candidate.label,
                "complexity": candidate.complexity,
                "eligible": row is not None,
                "reason": None if row is not None else reasons.get(code, "não avaliado"),
                "wape": None if row is None else _rounded(row["wape"]),
                "bias": None if row is None else _rounded(row["bias"]),
                "window_wapes": [] if row is None else row["window_wapes"],
                "windows_beating_baseline": None if row is None else row["windows_beating_baseline"],
                "windows_compared": None if row is None else row["windows_compared"],
                "selected": code == selected,
            }
        )
    chosen = rows[selected]
    return {
        **base,
        "status": status,
        "windows": len(origins),
        "window_train_lengths": origins,
        "selected_model": selected,
        "selected_label": CANDIDATES[selected].label,
        "backtest_wape": _rounded(chosen["wape"]),
        "backtest_bias": _rounded(chosen["bias"]),
        "baseline_wape": _rounded(baseline_wape),
        "baseline_bias": _rounded(baseline_bias),
        "beats_baseline": None if chosen["wape"] is None or baseline_wape is None else chosen["wape"] < baseline_wape,
        "windows_beating_baseline": chosen["windows_beating_baseline"],
        "windows_compared": chosen["windows_compared"],
        "candidates": table,
    }


def build_rolling_forecasts(sales: pd.DataFrame, config: dict[str, Any] | None = None, horizon: int = 3) -> list[dict[str, Any]]:
    """Previsão do motor rolante por SKU (desafiante). Não substitui `build_demand_forecasts`."""
    config = load_engine_config() if config is None else config
    records: list[dict[str, Any]] = []
    for sku in sorted(sales["SKU"].dropna().astype(str).unique()):
        series = _monthly_series(sales, sku)
        if len(series) < MINIMUM_HISTORY:
            records.append(_insufficient(sku, series))
            continue
        backtest = rolling_backtest(series, config)
        if backtest["status"] == "insufficient_history":
            record = _insufficient(sku, series)
            record["limitation"] = "O backtest rolante precisa de pelo menos 9 meses de histórico; o motor atual continua valendo para este SKU."
            record["status"] = "insufficient_rolling_history"
            records.append({**record, **{key: backtest[key] for key in ("windows", "window_train_lengths", "candidates")}})
            continue

        selected = backtest["selected_model"]
        future = pd.period_range(series.index.max() + 1, periods=horizon, freq="M")
        values = _run(selected, series, future)
        if values is None:
            selected = FALLBACK_MODEL
            values = _run(selected, series, future)
        trend, change = _trend(series)
        values = [round(max(0.0, float(value)), 1) for value in values]
        records.append(
            {
                "sku": sku,
                "reference_month": series.index.max().to_timestamp().date().isoformat(),
                "history_months": int(len(series)),
                "model": selected,
                "model_label": CANDIDATES[selected].label,
                "forecast_months": [period.to_timestamp().date().isoformat() for period in future],
                "forecast_values": values,
                "forecast_next_month": values[0],
                "forecast_total_3m": round(sum(values), 1),
                "trend": trend,
                "trend_change_ratio": None if change is None else round(change, 4),
                "backtest_wape": backtest["backtest_wape"],
                "forecast_confidence": _confidence(backtest["backtest_wape"]),
                "status": backtest["status"],
                "limitation": LIMITATION,
                "backtest_bias": backtest["backtest_bias"],
                "backtest_windows": backtest["windows"],
                "baseline_wape": backtest["baseline_wape"],
                "beats_baseline": backtest["beats_baseline"],
                "windows_beating_baseline": backtest["windows_beating_baseline"],
                "windows_compared": backtest["windows_compared"],
                "candidates": backtest["candidates"],
            }
        )
    return records


# ------------------------------------------------------------------------------------------ avaliação aninhada

Procedure = Callable[[pd.Series], str]  # recebe só o treino e devolve o código do modelo escolhido


def v1_procedure(train: pd.Series) -> str:
    """Seleção do motor atual (`forecasting.py`): menor WAPE no holdout de 3 meses entre os dois modelos; empate pelo código."""
    if len(train) < MINIMUM_HISTORY:
        return FALLBACK_MODEL
    valid = []
    for model in _MODELS:
        error, predictions = _backtest(train, model, 3)
        if predictions is not None and error is not None:
            valid.append((error, model))
    return min(valid)[1] if valid else FALLBACK_MODEL


def rolling_procedure(config: dict[str, Any] | None = None) -> Procedure:
    config = load_engine_config() if config is None else config
    return lambda train: rolling_backtest(train, config)["selected_model"] or FALLBACK_MODEL


def baseline_procedure(train: pd.Series) -> str:
    return BASELINE_MODEL


def default_procedures(config: dict[str, Any] | None = None) -> dict[str, Procedure]:
    return {"v1": v1_procedure, "rolling": rolling_procedure(config), "baseline": baseline_procedure}


def _predict(code: str, train: pd.Series, targets: pd.PeriodIndex) -> list[float]:
    predicted = naive_last(train, targets) if code == BASELINE_MODEL else _run(code, train, targets)
    return predicted if predicted is not None else _run(FALLBACK_MODEL, train, targets)


def nested_evaluation(series: pd.Series, procedures: dict[str, Procedure] | None = None, config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Mede cada procedimento nas origens externas escolhendo o modelo só com dados anteriores a cada origem."""
    config = load_engine_config() if config is None else config
    procedures = default_procedures(config) if procedures is None else procedures
    rolling, nested = config["rolling"], config["nested"]
    origins = rolling_origins(len(series), rolling["horizon_months"], rolling["step_months"], nested["outer_windows"], rolling["minimum_train_months"])
    if not origins:
        return {"status": "insufficient_history", "outer_train_lengths": [], "procedures": {}}

    results: dict[str, dict[str, Any]] = {}
    for name, procedure in procedures.items():
        windows, models = [], []
        for origin in origins:
            train, test = series.iloc[:origin], series.iloc[origin : origin + rolling["horizon_months"]]
            code = procedure(train)  # só o treino é entregue ao procedimento
            windows.append(([float(value) for value in test.tolist()], _predict(code, train, test.index)))
            models.append(code)
        wape, bias = _pooled(windows)
        absolute, signed, actual = _totals(windows)
        results[name] = {"models": models, "wape": wape, "bias": bias, "abs_error": absolute, "signed_error": signed, "actual_total": actual}
    return {"status": "ok", "outer_train_lengths": origins, "procedures": results}


def nested_evaluation_table(sales: pd.DataFrame, config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Avaliação aninhada de todos os SKUs, agregada, com a conferência dos critérios de promoção (informativa)."""
    config = load_engine_config() if config is None else config
    procedures = default_procedures(config)
    rows: list[dict[str, Any]] = []
    for sku in sorted(sales["SKU"].dropna().astype(str).unique()):
        series = _monthly_series(sales, sku)
        if len(series) < MINIMUM_HISTORY:
            continue
        result = nested_evaluation(series, procedures, config)
        if result["status"] == "ok":
            rows.append({"sku": sku, "outer_train_lengths": result["outer_train_lengths"], "procedures": result["procedures"]})

    aggregate: dict[str, Any] = {}
    for name in procedures:
        absolute = sum(row["procedures"][name]["abs_error"] for row in rows)
        actual = sum(row["procedures"][name]["actual_total"] for row in rows)
        signed = sum(row["procedures"][name]["signed_error"] for row in rows)
        aggregate[name] = {
            "weighted_wape": None if actual <= 0 else absolute / actual,
            "weighted_bias": None if actual <= 0 else signed / actual,
            "skus_beating_baseline": sum(
                1
                for row in rows
                if row["procedures"][name]["wape"] is not None and row["procedures"]["baseline"]["wape"] is not None
                and row["procedures"][name]["wape"] < row["procedures"]["baseline"]["wape"]
            ),
        }

    comparison = {"rolling_better": 0, "equal": 0, "rolling_worse": 0}
    for row in rows:
        new, old = row["procedures"]["rolling"]["wape"], row["procedures"]["v1"]["wape"]
        if new is None or old is None:
            continue
        key = "equal" if abs(new - old) < 1e-12 else ("rolling_better" if new < old else "rolling_worse")
        comparison[key] += 1
    result = {"skus": len(rows), "aggregate": aggregate, "rolling_vs_v1": comparison, "rows": rows}
    result["criteria"] = promotion_criteria(result, config)
    return result


def promotion_criteria(evaluation: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Confere os três critérios de promoção fixados em config; não promove nada (a decisão é da Etapa 14.5)."""
    aggregate, promotion = evaluation["aggregate"], config["promotion"]
    new, old = aggregate["rolling"], aggregate["v1"]
    if new["weighted_wape"] is None or old["weighted_wape"] is None or old["weighted_wape"] <= 0:
        gain = None
    else:
        gain = 1 - new["weighted_wape"] / old["weighted_wape"]
    worsening = None
    if new["weighted_bias"] is not None and old["weighted_bias"] is not None:
        worsening = (abs(new["weighted_bias"]) - abs(old["weighted_bias"])) * 100
    wape_ok = gain is not None and gain >= promotion["min_relative_wape_gain"]
    bias_ok = worsening is not None and worsening <= promotion["max_bias_worsening_pp"]
    baseline_ok = new["skus_beating_baseline"] >= old["skus_beating_baseline"]
    return {
        "relative_wape_gain": gain,
        "min_relative_wape_gain": promotion["min_relative_wape_gain"],
        "wape_criterion_met": wape_ok,
        "bias_worsening_pp": worsening,
        "max_bias_worsening_pp": promotion["max_bias_worsening_pp"],
        "bias_criterion_met": bias_ok,
        "skus_beating_baseline_rolling": new["skus_beating_baseline"],
        "skus_beating_baseline_v1": old["skus_beating_baseline"],
        "baseline_criterion_met": baseline_ok,
        "all_met": bool(wape_ok and bias_ok and baseline_ok),
    }


# ------------------------------------------------------------------------------------------ grade de sensibilidade

def sensitivity_grid(sales: pd.DataFrame, config: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Refaz a avaliação aninhada para cada combinação (origens externas × mínimo de janelas) e confere os critérios.

    O veredito da promoção não deve depender de uma única célula: esta grade mostra o quanto ele muda quando as duas
    escolhas de desenho mudam. Informativa; não altera nada oficial.
    """
    config = load_engine_config() if config is None else config
    cells: list[dict[str, Any]] = []
    for outer in config["sensitivity"]["outer_windows"]:
        for minimum in config["sensitivity"]["minimum_windows"]:
            variant = deepcopy(config)
            variant["nested"]["outer_windows"] = outer
            variant["rolling"]["minimum_windows"] = minimum
            table = nested_evaluation_table(sales, variant)
            aggregate, criteria = table["aggregate"], table["criteria"]
            cells.append(
                {
                    "outer_windows": outer,
                    "minimum_windows": minimum,
                    "is_default": outer == config["nested"]["outer_windows"] and minimum == config["rolling"]["minimum_windows"],
                    "outer_train_lengths": table["rows"][0]["outer_train_lengths"] if table["rows"] else [],
                    "skus": table["skus"],
                    "v1_wape": aggregate["v1"]["weighted_wape"],
                    "rolling_wape": aggregate["rolling"]["weighted_wape"],
                    "baseline_wape": aggregate["baseline"]["weighted_wape"],
                    "v1_bias": aggregate["v1"]["weighted_bias"],
                    "rolling_bias": aggregate["rolling"]["weighted_bias"],
                    "rolling_better_skus": table["rolling_vs_v1"]["rolling_better"],
                    "equal_skus": table["rolling_vs_v1"]["equal"],
                    "rolling_worse_skus": table["rolling_vs_v1"]["rolling_worse"],
                    **{key: criteria[key] for key in (
                        "relative_wape_gain", "wape_criterion_met", "bias_worsening_pp", "bias_criterion_met",
                        "skus_beating_baseline_rolling", "skus_beating_baseline_v1", "baseline_criterion_met", "all_met",
                    )},
                }
            )
    return cells


def summarize_sensitivity(cells: list[dict[str, Any]]) -> dict[str, Any]:
    """Quantas combinações atendem aos critérios e em que faixa fica o ganho de WAPE."""
    gains = [cell["relative_wape_gain"] for cell in cells if cell["relative_wape_gain"] is not None]
    default = next((cell for cell in cells if cell["is_default"]), None)
    met = sum(bool(cell["all_met"]) for cell in cells)
    return {
        "cells": len(cells),
        "cells_all_met": met,
        "robust": bool(cells) and met == len(cells),
        "default_all_met": None if default is None else bool(default["all_met"]),
        "min_relative_wape_gain": min(gains) if gains else None,
        "max_relative_wape_gain": max(gains) if gains else None,
    }
