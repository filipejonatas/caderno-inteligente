"""Estimativa de faturamento: previsão em unidades multiplicada pelo preço vigente.

Camada aditiva: lê a previsão de demanda já calculada e nunca a altera. Todo valor aqui é estimativa;
sem preço ou sem previsão, o resultado é nulo (nunca zero).
"""
from __future__ import annotations

import math
from typing import Any

import pandas as pd

from .forecasting import _MODELS, _backtest, _monthly_series

PRICE_COLUMN = "Preço unitário (R$)"
VALUE_COLUMN = "Valor faturado (R$)"
FORMULA = "Faturamento estimado = previsão em unidades × preço unitário vigente"
OBSERVED_WINDOW = 12
REVENUE_MONTHS = 3  # os campos e as telas "3 meses" continuam com 3 meses quando a previsão oficial tem horizonte maior
CONFIDENCE_LEVELS = ("alta", "média", "baixa")
PRICE_TOLERANCE = 0.005

LIMITATIONS = [
    "Estimativa, não faturamento realizado: resulta da previsão em unidades multiplicada pelo preço vigente.",
    "O preço é mantido constante: não considera reajuste, desconto, campanha (ex.: Black Friday) nem mix de canal.",
    "Receita bruta, sem impostos, devoluções ou bonificações.",
    "A previsão é global por SKU; não existe faturamento previsto por parceiro, canal ou região.",
    "A confiança de cada valor é a da previsão em unidades que o originou.",
]

FIELD_NATURE = {
    "unit_price": {"nature": "observado na fonte", "origin": "Precos_Produtos.Preço unitário (R$); na falta, último preço de Vendas_24m"},
    "forecast_units": {"nature": "previsto", "origin": "os 3 primeiros meses da previsão oficial de demanda por SKU (motor configurado em config/forecast_engine.json)"},
    "revenue_values": {"nature": "estimado", "origin": "calculado: previsão em unidades × preço unitário vigente"},
    "revenue_total_3m": {"nature": "estimado", "origin": "soma dos 3 meses estimados; SKUs sem preço ou sem previsão ficam fora e são listados"},
    "revenue_total_6m": {"nature": "estimado", "origin": "soma dos 6 meses da previsão oficial × preço; nulo quando o horizonte oficial é menor que 6 meses"},
    "observed_revenue": {"nature": "observado", "origin": "Vendas_24m.Valor faturado (R$), todos os canais"},
    "commercial_reference": {"nature": "previsto na fonte", "origin": "Forecast_Comercial (unidades) × mesmo preço vigente, em todos os meses em comum com a previsão oficial"},
    "backtest_wape": {"nature": "calculado", "origin": "erro absoluto em R$ ÷ faturamento real no teste da previsão oficial (motor v2: origens rolantes com meses de pico; v1: últimos 3 meses)"},
}


def _number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _valid_price(value: Any) -> float | None:
    number = _number(value)
    return number if number is not None and number > 0 else None


def _round(value: float | None, digits: int = 2) -> float | None:
    return None if value is None else round(value, digits)


def _text(value: Any) -> str | None:
    if value is None or (isinstance(value, float) and math.isnan(value)) or pd.isna(value):
        return None
    return str(value)


def _table_price(prices: pd.DataFrame | None, sku: str) -> float | None:
    if prices is None or prices.empty or PRICE_COLUMN not in prices:
        return None
    rows = prices[prices["SKU"] == sku]
    if rows.empty:
        return None
    if "Vigência fictícia" in rows:
        rows = rows.sort_values("Vigência fictícia", na_position="first")
    return _valid_price(rows[PRICE_COLUMN].iloc[-1])


def _last_sales_price(sales: pd.DataFrame, sku: str) -> float | None:
    if PRICE_COLUMN not in sales:
        return None
    rows = sales.loc[sales["SKU"] == sku, ["Mês", PRICE_COLUMN]].dropna().sort_values("Mês")
    for value in reversed(rows[PRICE_COLUMN].tolist()):
        price = _valid_price(value)
        if price is not None:
            return price
    return None


def _resolve_price(sku: str, prices: pd.DataFrame | None, sales: pd.DataFrame) -> tuple[float | None, str | None, bool]:
    table, last = _table_price(prices, sku), _last_sales_price(sales, sku)
    conflict = table is not None and last is not None and abs(table - last) > PRICE_TOLERANCE
    if table is not None:
        return table, "Precos_Produtos", conflict
    if last is not None:
        return last, "Vendas_24m (último preço faturado)", False
    return None, None, False


def _iso(period: pd.Period) -> str:
    return period.to_timestamp().date().isoformat()


def _observed(sales: pd.DataFrame, skus: list[str], months: list[pd.Period]) -> dict[str, Any]:
    """Faturamento observado por mês; mês sem registro depois do primeiro faturamento do conjunto vale zero, antes dele é nulo."""
    labels = [_iso(month) for month in months]
    if VALUE_COLUMN not in sales or not skus or not months:
        return {"months": labels, "values": [None] * len(months)}
    subset = sales.loc[sales["SKU"].isin(skus), ["Mês", VALUE_COLUMN]].dropna(subset=["Mês"]).copy()
    if subset.empty:
        return {"months": labels, "values": [None] * len(months)}
    subset["period"] = pd.to_datetime(subset["Mês"]).dt.to_period("M")
    monthly = subset.groupby("period")[VALUE_COLUMN].sum(min_count=1)
    first = subset["period"].min()
    values: list[float | None] = []
    for month in months:
        if month < first:
            values.append(None)
            continue
        value = monthly.get(month)
        values.append(0.0 if value is None or pd.isna(value) else _round(float(value)))
    return {"months": labels, "values": values}


def _observed_window(sales: pd.DataFrame) -> list[pd.Period]:
    if sales.empty:
        return []
    last = pd.to_datetime(sales["Mês"]).dt.to_period("M").max()
    return list(pd.period_range(last - (OBSERVED_WINDOW - 1), last, freq="M"))


def _commercial_reference(item: dict, commercial: pd.DataFrame | None, months_all: list[str], units_all: list[float]) -> dict[str, Any] | None:
    if commercial is None or commercial.empty or item["unit_price"] is None:
        return None
    rows = commercial[commercial["SKU"] == item["sku"]]
    if rows.empty:
        return None
    by_month = {pd.Timestamp(row["Mês"]).date().isoformat(): row for _, row in rows.iterrows() if pd.notna(row["Mês"])}
    months, model_units, commercial_units = [], [], []
    for month, units in zip(months_all, units_all):
        row = by_month.get(month)
        value = None if row is None else _number(row["Previsão unidades"])
        if value is None:
            continue
        months.append(month)
        model_units.append(units)
        commercial_units.append(value)
    if not months:
        return None
    price = item["unit_price"]
    revenue_model, revenue_commercial = sum(model_units) * price, sum(commercial_units) * price
    origins = sorted({str(by_month[month]["Origem previsão"]) for month in months if _text(by_month[month].get("Origem previsão"))})
    return {
        "months": months,
        "commercial_units": [_round(value, 1) for value in commercial_units],
        "model_revenue": _round(revenue_model),
        "commercial_revenue": _round(revenue_commercial),
        "difference_ratio": None if revenue_commercial <= 0 else _round((revenue_model - revenue_commercial) / revenue_commercial, 4),
        "origins": origins,
        "note": "Comparação, não erro: o consenso comercial não substitui a previsão estatística.",
    }


def _item(row: dict | None, sku: str, product: str | None, family: str | None, prices, sales, commercial) -> tuple[dict, dict | None]:
    price, source, conflict = _resolve_price(sku, prices, sales)
    usable = bool(row) and row.get("status") == "ok" and bool(row.get("forecast_values"))
    months_all = list(row["forecast_months"]) if usable else []
    units_all = list(row["forecast_values"]) if usable else []
    item: dict[str, Any] = {
        "sku": sku, "product": product, "family": family or "Sem família",
        "status": "ok", "reason": None,
        "unit_price": price, "price_source": source, "price_conflict": conflict,
        "model_label": None if not row else row.get("model_label"),
        "forecast_confidence": "baixa" if not row else row.get("forecast_confidence", "baixa"),
        "forecast_months": months_all[:REVENUE_MONTHS],
        "forecast_units": units_all[:REVENUE_MONTHS],
        "revenue_values": [], "revenue_next_month": None, "revenue_total_3m": None, "revenue_total_6m": None,
        "commercial_reference": None, "calculation": None,
        "nature": "estimado",
    }
    if not usable:
        item["status"], item["reason"] = "sem_previsao", "Sem previsão de unidades; não há como estimar faturamento."
        return item, None
    if price is None:
        item["status"], item["reason"] = "sem_preco", "Sem preço unitário na tabela de preços nem nas vendas; faturamento não estimado."
        return item, None
    revenue = [_round(units * price) for units in item["forecast_units"]]
    item.update(
        revenue_values=revenue, revenue_next_month=revenue[0], revenue_total_3m=_round(sum(units * price for units in item["forecast_units"])),
        revenue_total_6m=_round(sum(units * price for units in units_all[:6])) if len(units_all) >= 6 else None,
        calculation={"formula": FORMULA, "terms": [{"month": month, "units": units, "unit_price": price, "revenue": value}
                                                   for month, units, value in zip(item["forecast_months"], item["forecast_units"], revenue)]},
    )
    if conflict:
        item["reason"] = "O preço da tabela difere do último preço faturado; foi usado o da tabela."
    item["commercial_reference"] = _commercial_reference(item, commercial, months_all, units_all)

    backtest = None
    if row.get("backtest_actual_units") is not None and row.get("backtest_abs_error_units") is not None:
        # Motor v2: o mesmo teste rolante que dá o erro e a confiança da previsão oficial, convertido em R$.
        return item, {"abs_error": float(row["backtest_abs_error_units"]) * price, "actual": float(row["backtest_actual_units"]) * price}
    series = _monthly_series(sales, sku)
    if row.get("model") in _MODELS and len(series) >= 6:
        _, predictions = _backtest(series, row["model"], 3)
        if predictions is not None:
            actual = series.iloc[-3:].tolist()
            backtest = {
                "abs_error": sum(abs(real - estimate) for real, estimate in zip(actual, predictions)) * price,
                "actual": sum(actual) * price,
            }
    return item, backtest


def _group(label: str, members: list[tuple[dict, dict | None]], sales: pd.DataFrame, window: list[pd.Period]) -> dict[str, Any]:
    estimated = [item for item, _ in members if item["status"] == "ok"]
    excluded = [{"sku": item["sku"], "status": item["status"], "reason": item["reason"]} for item, _ in members if item["status"] != "ok"]
    by_month: dict[str, float] = {}
    for item in estimated:
        for month, value in zip(item["forecast_months"], item["revenue_values"]):
            by_month[month] = by_month.get(month, 0.0) + value
    total = _round(sum(item["revenue_total_3m"] for item in estimated)) if estimated else None
    with_6m = [item["revenue_total_6m"] for item in estimated if item["revenue_total_6m"] is not None]
    total_6m = _round(sum(with_6m)) if estimated and len(with_6m) == len(estimated) else None

    errors = [bt for _, bt in members if bt]
    actual = sum(bt["actual"] for bt in errors)
    wape = _round(sum(bt["abs_error"] for bt in errors) / actual, 4) if errors and actual > 0 else None

    observed = _observed(sales, [item["sku"] for item, _ in members], window)
    estimated_skus = [item["sku"] for item in estimated]
    last_three = _observed(sales, estimated_skus, window[-3:])["values"]
    observed_last_3m = None if not last_three or any(value is None for value in last_three) else _round(sum(last_three))
    change = None if total is None or not observed_last_3m else _round((total - observed_last_3m) / observed_last_3m, 4)

    compared = [item["commercial_reference"] for item in estimated if item["commercial_reference"]]
    reference = None
    if compared:
        model, commercial = sum(ref["model_revenue"] for ref in compared), sum(ref["commercial_revenue"] for ref in compared)
        reference = {
            "months": sorted({month for ref in compared for month in ref["months"]}),
            "skus_compared": len(compared),
            "model_revenue": _round(model), "commercial_revenue": _round(commercial),
            "difference_ratio": None if commercial <= 0 else _round((model - commercial) / commercial, 4),
        }
    return {
        "label": label,
        "skus_total": len(members), "skus_with_estimate": len(estimated), "skus_excluded": excluded,
        "by_month": [{"month": month, "revenue": _round(value)} for month, value in sorted(by_month.items())],
        "revenue_total_3m": total,
        "revenue_total_6m": total_6m,
        "confidence_distribution": {level: sum(1 for item in estimated if item["forecast_confidence"] == level) for level in CONFIDENCE_LEVELS},
        "backtest_wape": wape,
        "observed_revenue": observed,
        "observed_last_3m_same_skus": observed_last_3m,
        "change_vs_last_3m": change,
        "commercial_reference": reference,
    }


def build_revenue_forecasts(
    forecasts: pd.DataFrame,
    products: pd.DataFrame,
    sales: pd.DataFrame,
    prices: pd.DataFrame | None = None,
    commercial: pd.DataFrame | None = None,
) -> dict[str, Any]:
    rows = {row["sku"]: row for row in forecasts.astype(object).where(forecasts.notna(), None).to_dict("records")}
    catalog = products.set_index("SKU")
    skus = sorted({*catalog.index.astype(str), *rows})
    members: list[tuple[dict, dict | None]] = []
    for sku in skus:
        info = catalog.loc[sku] if sku in catalog.index else None
        product = None if info is None else _text(info.get("Produto"))
        family = None if info is None else _text(info.get("Família"))
        members.append(_item(rows.get(sku), sku, product, family, prices, sales, commercial))

    window = _observed_window(sales)
    items = [item for item, _ in members]
    for item in items:
        item["observed_revenue"] = _observed(sales, [item["sku"]], window)
    by_family: dict[str, list[tuple[dict, dict | None]]] = {}
    for member in members:
        by_family.setdefault(member[0]["family"], []).append(member)
    families = [_group(name, group, sales, window) for name, group in by_family.items()]
    families.sort(key=lambda group: (group["revenue_total_3m"] is None, -(group["revenue_total_3m"] or 0), group["label"]))

    references = [row["reference_month"] for row in rows.values() if row.get("reference_month")]
    return {
        "reference_month": max(references) if references else None,
        "nature": "estimado",
        "formula": FORMULA,
        "items": items,
        "families": families,
        "total": _group("Total da empresa", members, sales, window),
        "field_nature": FIELD_NATURE,
        "limitations": LIMITATIONS,
    }
