from __future__ import annotations

from typing import Callable

import pandas as pd


MODEL_LABELS = {
    "moving_average_3": "Média móvel de 3 meses",
    "seasonal_naive_12": "Sazonal ingênuo de 12 meses",
}


def _monthly_series(sales: pd.DataFrame, sku: str) -> pd.Series:
    subset = sales.loc[sales["SKU"] == sku, ["Mês", "Quantidade faturada"]].copy()
    if subset.empty:
        return pd.Series(dtype="float64")
    subset["Mês"] = pd.to_datetime(subset["Mês"]).dt.to_period("M")
    monthly = subset.groupby("Mês")["Quantidade faturada"].sum().astype(float).sort_index()
    full_index = pd.period_range(monthly.index.min(), monthly.index.max(), freq="M")
    return monthly.reindex(full_index, fill_value=0.0)


def _moving_average(history: pd.Series, targets: pd.PeriodIndex) -> list[float] | None:
    values = [float(value) for value in history.tolist()]
    if len(values) < 3:
        return None
    predictions: list[float] = []
    for _ in targets:
        prediction = max(0.0, sum(values[-3:]) / 3)
        predictions.append(prediction)
        values.append(prediction)
    return predictions


def _seasonal_naive(history: pd.Series, targets: pd.PeriodIndex) -> list[float] | None:
    lookup = {period: float(value) for period, value in history.items()}
    predictions: list[float] = []
    for target in targets:
        source = target - 12
        if source not in lookup:
            return None
        predictions.append(max(0.0, lookup[source]))
    return predictions


_MODELS: dict[str, Callable[[pd.Series, pd.PeriodIndex], list[float] | None]] = {
    "moving_average_3": _moving_average,
    "seasonal_naive_12": _seasonal_naive,
}


def _wape(actual: pd.Series, predicted: list[float]) -> float | None:
    denominator = float(actual.sum())
    if denominator <= 0:
        return None
    return sum(abs(float(observed) - estimate) for observed, estimate in zip(actual, predicted)) / denominator


def _backtest(series: pd.Series, model: str, holdout: int = 3) -> tuple[float | None, list[float] | None]:
    train = series.iloc[:-holdout]
    actual = series.iloc[-holdout:]
    predictions = _MODELS[model](train, actual.index)
    if predictions is None:
        return None, None
    return _wape(actual, predictions), predictions


def _trend(series: pd.Series) -> tuple[str, float | None]:
    if len(series) < 6:
        return "indeterminada", None
    previous = float(series.iloc[-6:-3].mean())
    recent = float(series.iloc[-3:].mean())
    if previous == 0:
        return ("crescente", None) if recent > 0 else ("estável", 0.0)
    change = (recent - previous) / previous
    if change > 0.10:
        return "crescente", change
    if change < -0.10:
        return "decrescente", change
    return "estável", change


def _confidence(wape: float | None) -> str:
    if wape is None or wape > 0.40:
        return "baixa"
    if wape > 0.20:
        return "média"
    return "alta"


def _insufficient(sku: str, series: pd.Series) -> dict:
    reference = None if series.empty else series.index.max().to_timestamp().date().isoformat()
    return {
        "sku": sku,
        "reference_month": reference,
        "history_months": int(len(series)),
        "model": None,
        "model_label": "Não selecionado",
        "forecast_months": [],
        "forecast_values": [],
        "forecast_next_month": None,
        "forecast_total_3m": None,
        "trend": "indeterminada",
        "trend_change_ratio": None,
        "backtest_wape": None,
        "forecast_confidence": "baixa",
        "status": "insufficient_data",
        "limitation": "São necessários pelo menos 6 meses de histórico para estimar demanda.",
    }


def build_demand_forecasts(sales: pd.DataFrame, horizon: int = 3, holdout: int = 3) -> pd.DataFrame:
    """Select an explainable monthly forecast per SKU using a temporal holdout."""
    if horizon != 3:
        raise ValueError("O protótipo V1 usa horizonte fixo de 3 meses")
    if holdout != 3:
        raise ValueError("O protótipo V1 usa holdout fixo de 3 meses")

    records: list[dict] = []
    for sku in sorted(sales["SKU"].dropna().astype(str).unique()):
        series = _monthly_series(sales, sku)
        if len(series) < 6:
            records.append(_insufficient(sku, series))
            continue

        candidates: list[tuple[str, float | None]] = []
        for model in _MODELS:
            error, predictions = _backtest(series, model, holdout)
            if predictions is not None:
                candidates.append((model, error))

        valid = [(model, error) for model, error in candidates if error is not None]
        selected = min(valid, key=lambda item: (item[1], item[0]))[0] if valid else "moving_average_3"
        future_months = pd.period_range(series.index.max() + 1, periods=horizon, freq="M")
        future_values = _MODELS[selected](series, future_months)
        if future_values is None:
            selected = "moving_average_3"
            future_values = _moving_average(series, future_months)
        if future_values is None:
            records.append(_insufficient(sku, series))
            continue

        selected_error = next((error for model, error in candidates if model == selected), None)
        trend, change = _trend(series)
        values = [round(max(0.0, float(value)), 1) for value in future_values]
        records.append(
            {
                "sku": sku,
                "reference_month": series.index.max().to_timestamp().date().isoformat(),
                "history_months": int(len(series)),
                "model": selected,
                "model_label": MODEL_LABELS[selected],
                "forecast_months": [period.to_timestamp().date().isoformat() for period in future_months],
                "forecast_values": values,
                "forecast_next_month": values[0],
                "forecast_total_3m": round(sum(values), 1),
                "trend": trend,
                "trend_change_ratio": None if change is None else round(change, 4),
                "backtest_wape": None if selected_error is None else round(float(selected_error), 4),
                "forecast_confidence": _confidence(selected_error),
                "status": "ok",
                "limitation": "Previsão estatística baseada em faturamento mensal; não incorpora causalidade, campanhas futuras ou alocação por parceiro.",
            }
        )
    return pd.DataFrame(records)
