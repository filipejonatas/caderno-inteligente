"""Produção planejada por mês de liberação (gráfico da Fila operacional).

Camada derivada e somente leitura: soma as ordens planejadas do plano de suprimento (Etapa 15.3) por mês de
liberação, separando as urgentes (liberação dentro da janela de decisão, o "sugerido agora") das demais. Não
recalcula a projeção nem muda ação, quantidade, score ou ranking.

Mês completo: um mês de liberação só é exibido quando `último dia do mês + maior lead time ≤ fim do horizonte`.
Depois disso, ordens que atenderiam necessidades além do horizonte não foram planejadas e o mês pareceria menor
do que é. SKU sem previsão não tem plano: fica fora da soma e é listado, nunca entra como zero.
"""
from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd

LIMITATIONS = [
    "Plano sugerido, não ordem liberada: cada ordem exige revisão humana antes de virar OP.",
    "Soma por mês de liberação (início da produção), não por mês de conclusão.",
    "As OPs já abertas não entram na soma; a capacidade de cada linha está em Capacidade.",
    "Meses de liberação cujo horizonte da previsão não cobre o lead time ficam de fora, para não parecerem menores do que são.",
]

FIELD_NATURE = {
    "urgent": {"nature": "estimado", "origin": "ordens planejadas com liberação dentro da janela de decisão"},
    "later": {"nature": "estimado", "origin": "ordens planejadas com liberação depois da janela de decisão"},
}


def _month_end(month: str) -> date:
    return pd.Period(month, freq="M").end_time.date()


def _months_between(start: date, end: date) -> list[str]:
    return [str(period) for period in pd.period_range(start, end, freq="M")]


def _aggregate(plans: list[dict[str, Any]], months: list[str]) -> dict[str, Any]:
    urgent = {month: 0.0 for month in months}
    later = {month: 0.0 for month in months}
    for plan in plans:
        for order in plan["planned_orders"]:
            month = order["release_date"][:7]
            if month not in urgent:
                continue
            (urgent if order["urgent"] else later)[month] += float(order["quantity"])
    return {
        "months": [{"month": month, "urgent": urgent[month], "later": later[month]} for month in months],
        "urgent_total": float(sum(plan["suggested_quantity"] for plan in plans)),
        "horizon_total": float(sum(plan["planned_quantity_horizon"] for plan in plans)),
    }


def build_production_plan(plans: dict[str, dict[str, Any]], indicators: pd.DataFrame, forecasts: pd.DataFrame) -> dict[str, Any]:
    """Agrega o plano de suprimento por mês de liberação, no total e por família."""
    families = {str(row["SKU"]): str(row["family"]) for row in indicators[["SKU", "family"]].to_dict("records")}
    status = {str(row["sku"]): str(row["status"]) for row in forecasts[["sku", "status"]].to_dict("records")}
    excluded = [{"sku": sku, "reason": "sem_previsao"} for sku in plans if status.get(sku) != "ok"]
    included = [plan for sku, plan in plans.items() if status.get(sku) == "ok"]
    if not included:
        return {"reference_date": None, "horizon_end": None, "urgent_window_end": None, "max_lead_time_days": None,
                "total": {"months": [], "urgent_total": 0.0, "horizon_total": 0.0}, "families": [],
                "excluded_skus": excluded, "omitted_months": [], "field_nature": FIELD_NATURE,
                "limitations": LIMITATIONS, "requires_human_review": True}

    reference = min(date.fromisoformat(plan["reference_date"]) for plan in included)
    horizon_end = min(date.fromisoformat(plan["horizon_end"]) for plan in included)
    max_lead = max(int(plan["lead_time_days"]) for plan in included)
    # Liberação ≤ necessidade ≤ fim do horizonte: os meses possíveis vão da data de planejamento ao fim do horizonte.
    candidates = _months_between(reference, horizon_end)
    complete = [month for month in candidates if (_month_end(month) - horizon_end).days + max_lead <= 0]
    omitted = [month for month in candidates if month not in complete]

    by_family: dict[str, list[dict[str, Any]]] = {}
    for plan in included:
        by_family.setdefault(families.get(str(plan["sku"]), "Sem família"), []).append(plan)
    return {
        "reference_date": reference.isoformat(),
        "horizon_end": horizon_end.isoformat(),
        "urgent_window_end": min(plan["decision_window_end"] for plan in included),
        "max_lead_time_days": max_lead,
        "total": _aggregate(included, complete),
        "families": [{"family": family, **_aggregate(group, complete)} for family, group in sorted(by_family.items())],
        "excluded_skus": excluded,
        "omitted_months": omitted,
        "field_nature": FIELD_NATURE,
        "limitations": LIMITATIONS,
        "requires_human_review": True,
    }
