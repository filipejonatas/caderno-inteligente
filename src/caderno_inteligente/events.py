"""Calendário de eventos como alerta e cenário explícito, sem alterar a previsão base.

Duas camadas separadas:
1. alerta: eventos que afetam a família do SKU e exigem decisão dentro do horizonte (ou antes dele, pelo lead time);
2. cenário: previsão base × fator sazonal medido no histórico da própria família. O fator nunca substitui a previsão.

Os modelos sazonais (sazonal ingênuo, combinação e mês do ano anterior ajustado pelo nível, o motor oficial v2) já repetem
o mesmo mês do ano anterior; para esses SKUs só há alerta, para não contar a sazonalidade duas vezes.
"""
from __future__ import annotations

import json
import math
import re
import unicodedata
from datetime import timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from .forecast_candidates import SEASONAL_CODES

DEFAULT_SETTINGS: dict[str, Any] = {
    "minimum_factor": 0.5,
    "maximum_factor": 3.0,
    "lookahead_buffer_days": 30,
    "baseline_radius_months": 6,
    "minimum_baseline_months": 3,
    "minimum_history_months": 12,
    "minimum_occurrences": 1,
    "neutral_band": 0.1,
    "no_history_markers": ["sem histórico"],
}
SCENARIO_MODEL = "moving_average_3"
MONTH_NAMES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]

FIELD_NATURE = {
    "events": {"nature": "observado na fonte", "origin": "Calendario_Eventos (nome, datas, famílias e impacto esperado)"},
    "decision_date": {"nature": "calculado", "origin": "início do evento − lead time do SKU (Produtos.Lead time (dias))"},
    "factor": {"nature": "estimado", "origin": "histórico de Vendas_24m da família: mês do evento ÷ média dos meses sem evento num raio de meses; limitado por config/event_factors.json"},
    "scenario_units": {"nature": "estimado", "origin": "previsão base em unidades × fator do mês; não substitui a previsão"},
    "scenario_revenue": {"nature": "estimado", "origin": "cenário em unidades × preço vigente (Etapa 10)"},
}

LIMITATIONS = [
    "Cenário indicativo: o fator vem do histórico da própria família (poucas ocorrências por evento) e não prevê campanhas futuras.",
    "O fator é medido em mês calendário; eventos de poucos dias dentro do mês recebem o fator do mês inteiro.",
    "O cenário só existe para SKUs cuja previsão é a média móvel; as previsões sazonais (incluindo o motor oficial v2) já incorporam o padrão do ano anterior.",
    "Evento sem histórico direto (ex.: lançamento) gera apenas alerta; nenhum fator é inventado.",
    "A previsão base, o ranking e a quantidade oficial sugerida não são alterados pelo cenário.",
]


def load_event_settings(path: str | Path | None = None) -> dict[str, Any]:
    values = {**DEFAULT_SETTINGS, "no_history_markers": list(DEFAULT_SETTINGS["no_history_markers"])}
    if path is not None:
        overrides = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(overrides, dict) or set(overrides) - set(values):
            raise ValueError("Configuração de eventos contém campos desconhecidos")
        values.update(overrides)
    return _validate_settings(values)


def _validate_settings(values: dict[str, Any]) -> dict[str, Any]:
    def number(key: str) -> float:
        value = values[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"Parâmetro de eventos inválido: {key}")
        return float(value)

    for key in ("minimum_factor", "maximum_factor", "neutral_band"):
        number(key)
    for key in ("lookahead_buffer_days", "baseline_radius_months", "minimum_baseline_months", "minimum_history_months", "minimum_occurrences"):
        if number(key) != int(number(key)):
            raise ValueError(f"Parâmetro precisa ser inteiro: {key}")
        values[key] = int(values[key])
    if not 0 < values["minimum_factor"] <= 1 <= values["maximum_factor"]:
        raise ValueError("Limites do fator devem satisfazer 0 < mínimo ≤ 1 ≤ máximo")
    if values["lookahead_buffer_days"] < 0 or not 0 <= values["neutral_band"] < 1:
        raise ValueError("Janela de antecedência ou faixa neutra inválida")
    if not 1 <= values["baseline_radius_months"] <= 12 or not 1 <= values["minimum_baseline_months"] <= 2 * values["baseline_radius_months"]:
        raise ValueError("Janela da linha de base inválida")
    if values["minimum_history_months"] < 1 or values["minimum_occurrences"] < 1:
        raise ValueError("Histórico e ocorrências mínimas devem ser positivos")
    markers = values["no_history_markers"]
    if not isinstance(markers, list) or not all(isinstance(item, str) and item.strip() for item in markers):
        raise ValueError("no_history_markers deve ser uma lista de textos")
    return values


def _text(value: Any) -> str | None:
    return None if value is None or pd.isna(value) else str(value).strip()


def _slug(name: str) -> str:
    plain = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", plain.lower()).strip("-")


def _iso(value: pd.Timestamp) -> str:
    return value.date().isoformat()


def parse_events(calendar: pd.DataFrame, settings: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """Eventos válidos e linhas ignoradas (com o motivo); nada é descartado em silêncio."""
    events, ignored = [], []
    markers = [marker.lower() for marker in settings["no_history_markers"]]
    for _, row in calendar.iterrows():
        name = _text(row.get("Evento")) or "(sem nome)"
        start, end = pd.to_datetime(row.get("Início"), errors="coerce"), pd.to_datetime(row.get("Fim"), errors="coerce")
        if pd.isna(start) or pd.isna(end):
            ignored.append({"event": name, "reason": "Data de início ou fim ausente ou inválida."})
            continue
        if end < start:
            ignored.append({"event": name, "reason": "Fim anterior ao início."})
            continue
        families = [part.strip() for part in (_text(row.get("Famílias impactadas")) or "").split(";") if part.strip()]
        observation = _text(row.get("Observação"))
        events.append({
            "id": _slug(name), "name": name, "start": start.normalize(), "end": end.normalize(),
            "families": None if any(item.lower() == "todas" for item in families) else families,
            "impact": _text(row.get("Impacto esperado")), "observation": observation,
            "has_history": not any(marker in (observation or "").lower() for marker in markers),
        })
    events.sort(key=lambda event: (event["start"], event["name"]))
    return events, ignored


def _covers(event: dict[str, Any], family: str) -> bool:
    return event["families"] is None or family in event["families"]


def _event_periods(event: dict[str, Any]) -> list[pd.Period]:
    return list(pd.period_range(event["start"].to_period("M"), event["end"].to_period("M"), freq="M"))


def _family_series(sales: pd.DataFrame, products: pd.DataFrame) -> dict[str, pd.Series]:
    joined = sales[["Mês", "SKU", "Quantidade faturada"]].merge(products[["SKU", "Família"]], on="SKU", how="inner")
    joined["period"] = pd.to_datetime(joined["Mês"]).dt.to_period("M")
    result = {}
    for family, group in joined.groupby("Família"):
        monthly = group.groupby("period")["Quantidade faturada"].sum().astype(float).sort_index()
        result[str(family)] = monthly.reindex(pd.period_range(monthly.index.min(), monthly.index.max(), freq="M"), fill_value=0.0)
    return result


def _month_factors(series: pd.Series, family: str, events: list[dict[str, Any]], settings: dict[str, Any]) -> dict[int, dict[str, Any]]:
    """Fator por mês-do-ano: mês coberto por evento ÷ média dos meses sem evento num raio local (acompanha a tendência)."""
    if len(series) < settings["minimum_history_months"]:
        return {}
    impacting = [event for event in events if _covers(event, family)]
    event_months = {period.month for event in impacting for period in _event_periods(event)}
    measurable = {period.month for event in impacting if event["has_history"] for period in _event_periods(event)}
    radius = settings["baseline_radius_months"]
    result: dict[int, dict[str, Any]] = {}
    for month in sorted(measurable):
        occurrences = []
        for period, units in series.items():
            if period.month != month:
                continue
            window = [series[p] for p in pd.period_range(period - radius, period + radius, freq="M") if p != period and p in series.index and p.month not in event_months]
            if len(window) < settings["minimum_baseline_months"]:
                continue
            baseline = sum(window) / len(window)
            if baseline <= 0:
                continue
            occurrences.append({"month": str(period), "units": round(float(units), 1), "baseline": round(baseline, 1), "baseline_months": len(window), "lift": round(float(units) / baseline, 4)})
        if len(occurrences) < settings["minimum_occurrences"]:
            result[month] = {"factor_raw": None, "factor": None, "capped": False, "occurrences": occurrences}
            continue
        raw = sum(item["lift"] for item in occurrences) / len(occurrences)
        factor = min(settings["maximum_factor"], max(settings["minimum_factor"], raw))
        result[month] = {"factor_raw": round(raw, 4), "factor": round(factor, 4), "capped": factor != raw, "occurrences": occurrences}
    return result


def _evidence_status(raw: float | None, band: float) -> str:
    if raw is None:
        return "sem_evidencia"
    if raw >= 1 + band:
        return "aumento"
    if raw <= 1 - band:
        return "queda"
    return "sem_alteracao"


def _event_family_summary(event: dict[str, Any], family: str, factors: dict[int, dict[str, Any]], settings: dict[str, Any]) -> dict[str, Any]:
    base = {"family": family, "factor": None, "factor_raw": None, "capped": False, "occurrences": 0, "months_used": [], "evidence_status": "sem_evidencia", "note": None}
    if not event["has_history"]:
        return {**base, "evidence_status": "sem_historico_direto", "note": "Evento sem histórico direto: apenas alerta; nenhum fator é estimado."}
    if not factors:
        return {**base, "note": f"Histórico da família menor que {settings['minimum_history_months']} meses ou sem linha de base: apenas alerta."}
    used = [(period.month, factors[period.month]) for period in _event_periods(event) if factors.get(period.month, {}).get("factor_raw") is not None]
    if not used:
        return {**base, "note": "Sem ocorrência anterior mensurável deste período para a família: apenas alerta."}
    raw = sum(item["factor_raw"] for _, item in used) / len(used)
    factor = min(settings["maximum_factor"], max(settings["minimum_factor"], raw))
    status = _evidence_status(raw, settings["neutral_band"])
    note = {
        "aumento": None,
        "queda": "O histórico mostra queda neste período para a família.",
        "sem_alteracao": "O histórico não mostra variação relevante neste período para a família; o calendário indica impacto, a evidência não.",
    }[status]
    return {
        **base, "factor": round(factor, 4), "factor_raw": round(raw, 4), "capped": factor != raw,
        "occurrences": sum(len(item["occurrences"]) for _, item in used), "months_used": [MONTH_NAMES[month - 1] for month, _ in used],
        "evidence_status": status, "note": note,
    }


def _plain(value: Any) -> Any:
    """Converte escalares numpy em tipos nativos para a resposta JSON."""
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_plain(item) for item in value]
    return value.item() if hasattr(value, "item") and not isinstance(value, (str, bytes)) else value


def _seasonal_note(model: str | None) -> str | None:
    if model in SEASONAL_CODES:
        return "A previsão já incorpora a sazonalidade do ano anterior (modelo sazonal); não há cenário, para não contar duas vezes."
    return None


def build_event_analysis(
    forecasts: pd.DataFrame,
    products: pd.DataFrame,
    sales: pd.DataFrame,
    calendar: pd.DataFrame,
    settings: dict[str, Any] | None = None,
    prices: dict[str, float] | None = None,
) -> dict[str, Any]:
    settings = _validate_settings(dict(settings or DEFAULT_SETTINGS))
    events, ignored = parse_events(calendar, settings)
    rows = {row["sku"]: row for row in forecasts.astype(object).where(forecasts.notna(), None).to_dict("records")}
    ok_rows = [row for row in rows.values() if row.get("status") == "ok" and row.get("forecast_months")]

    sales_last = pd.to_datetime(sales["Mês"]).dt.to_period("M").max()
    references = [row["reference_month"] for row in rows.values() if row.get("reference_month")]
    reference_period = pd.Period(max(references)[:7], freq="M") if references else sales_last
    reference_date = reference_period.end_time.normalize()
    horizon_months = sorted({m for row in ok_rows for m in row["forecast_months"]})
    horizon_end = (pd.Period(horizon_months[-1][:7], freq="M") if horizon_months else reference_period + 3).end_time.normalize()
    buffer_days = settings["lookahead_buffer_days"]

    family_series = _family_series(sales, products)
    catalog = products.set_index("SKU")
    families = sorted({str(value) for value in products["Família"].dropna()})
    factors = {family: _month_factors(family_series[family], family, events, settings) if family in family_series else {} for family in families}

    def summary(event: dict[str, Any], family: str) -> dict[str, Any]:
        return _event_family_summary(event, family, factors[family], settings)

    def decision(event: dict[str, Any], lead: float | None) -> pd.Timestamp | None:
        return None if lead is None else event["start"] - timedelta(days=int(lead))

    def needs_attention(event: dict[str, Any], lead: float | None) -> bool:
        if event["end"] <= reference_date:
            return False
        overlaps_horizon = event["start"] <= horizon_end
        deadline = event["start"] - timedelta(days=int(lead or 0)) - timedelta(days=buffer_days)
        return bool(overlaps_horizon or deadline <= horizon_end)

    items, alerted_skus = [], {event["id"]: 0 for event in events}
    for sku in sorted({*catalog.index.astype(str), *rows}):
        info = catalog.loc[sku] if sku in catalog.index else None
        family = str(info["Família"]) if info is not None and pd.notna(info.get("Família")) else None
        lead_raw = None if info is None else pd.to_numeric(info.get("Lead time (dias)"), errors="coerce")
        lead = None if lead_raw is None or pd.isna(lead_raw) else float(lead_raw)
        row = rows.get(sku)
        model = None if not row else row.get("model")
        usable = bool(row) and row.get("status") == "ok" and bool(row.get("forecast_months"))
        forecast_periods = [pd.Period(m[:7], freq="M") for m in (row["forecast_months"] if usable else [])]

        alerts = []
        for event in events:
            if family is None or not _covers(event, family) or not needs_attention(event, lead):
                continue
            alerted_skus[event["id"]] += 1
            deadline = decision(event, lead)
            alerts.append({
                "event_id": event["id"], "event": event["name"], "start": _iso(event["start"]), "end": _iso(event["end"]),
                "impact": event["impact"], "observation": event["observation"],
                "days_to_start": int((event["start"] - reference_date).days),
                "decision_date": None if deadline is None else _iso(deadline),
                "in_horizon": bool(any(event["start"] <= period.end_time and event["end"] >= period.start_time for period in forecast_periods)),
                "evidence": summary(event, family),
            })

        scenario, scenario_note = None, _seasonal_note(model)
        if usable and model == SCENARIO_MODEL and family is not None:
            base_units, month_factors, labels = list(row["forecast_values"]), [], []
            for period in forecast_periods:
                covering = [event for event in events if _covers(event, family) and event["start"] <= period.end_time and event["end"] >= period.start_time]
                labels.append(", ".join(event["name"] for event in covering) or None)
                entry = factors[family].get(period.month) if covering else None
                month_factors.append(None if entry is None else entry["factor"])
            if any(factor is not None for factor in month_factors):
                units = [round(base * (1.0 if factor is None else factor), 1) for base, factor in zip(base_units, month_factors)]
                price = (prices or {}).get(sku)
                scenario = {
                    "months": list(row["forecast_months"]), "base_units": [round(float(value), 1) for value in base_units],
                    "factors": month_factors, "events": labels, "scenario_units": units,
                    "base_total_3m": round(sum(base_units), 1), "scenario_total_3m": round(sum(units), 1),
                    "incremental_units_3m": round(sum(units) - sum(base_units), 1),
                    "unit_price": price,
                    "scenario_revenue_total_3m": None if price is None else round(sum(units) * price, 2),
                    "base_revenue_total_3m": None if price is None else round(sum(base_units) * price, 2),
                    "next_month_affected": month_factors[0] is not None and month_factors[0] != 1.0,
                    "nature": "estimado",
                    "formula": "Cenário = previsão base × fator do mês (histórico da família); meses sem evento ou sem evidência ficam com fator 1",
                }
            else:
                scenario_note = "Nenhum mês do horizonte tem evento com evidência histórica para a família; só há alerta."
        elif not usable:
            scenario_note = "Sem previsão de unidades; não há como montar cenário."
        items.append({
            "sku": sku, "family": family, "model": model, "lead_time_days": lead,
            "scenario_applicable": usable and model == SCENARIO_MODEL, "scenario_note": scenario_note,
            "alerts": alerts, "scenario": scenario,
        })

    event_rows = []
    for event in events:
        impacted = families if event["families"] is None else [family for family in event["families"] if family in families]
        unknown = [] if event["families"] is None else [family for family in event["families"] if family not in families]
        deadline_lead = [item["lead_time_days"] for item in items if item["family"] in impacted and item["lead_time_days"] is not None]
        event_rows.append({
            "id": event["id"], "name": event["name"], "start": _iso(event["start"]), "end": _iso(event["end"]),
            "impact": event["impact"], "observation": event["observation"], "all_families": event["families"] is None,
            "families": [summary(event, family) for family in impacted], "unknown_families": unknown, "has_history": event["has_history"],
            "days_to_start": int((event["start"] - reference_date).days),
            "in_horizon": bool(event["start"] <= horizon_end and event["end"] > reference_date),
            "past": bool(event["end"] <= reference_date),
            "decision_date_earliest": None if not deadline_lead else _iso(event["start"] - timedelta(days=int(max(deadline_lead)))),
            "skus_alerted": alerted_skus[event["id"]],
        })
    return _plain({
        "reference_month": _iso(reference_period.start_time.normalize()), "reference_date": _iso(reference_date), "horizon_end": _iso(horizon_end),
        "settings": settings, "events": event_rows, "ignored_events": ignored, "items": items,
        "family_factors": [
            {"family": family, "month": month, "month_name": MONTH_NAMES[month - 1], **entry}
            for family, by_month in factors.items() for month, entry in sorted(by_month.items())
        ],
        "field_nature": FIELD_NATURE, "limitations": LIMITATIONS,
    })
