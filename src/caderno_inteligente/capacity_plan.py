"""Capacidade semanal finita (Etapa 15.4): encaixa as ordens planejadas na capacidade livre de cada linha.

`Capacidade_Semanal.Capacidade disponível` já desconta os compromissos base e as OPs existentes (LEIA_ME), então só as
ordens planejadas da Etapa 15.3 consomem essa sobra. Premissas, declaradas na tela:

- capacidade em unidades homogêneas dentro da família (linha);
- a ordem consome capacidade na semana de início (= liberação), como a coluna "Ordens planejadas" da base;
- "compromissos base" é demanda não detalhada (não validado com a empresa);
- não há capacidade informada depois da última semana do calendário: ordem que começa depois fica "a confirmar".

Alocação: por data de necessidade, depois curva ABC e SKU. A ordem usa a semana de liberação; se faltar, antecipa
semana a semana até a data de planejamento (pré-produção). O que não couber fica sem programação (`insuficiente`).
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pandas as pd

STATUS_ORDER = {"ok": 0, "pre_producao": 1, "a_confirmar": 2, "insuficiente": 3}
STATUS_LABELS = {"ok": "Cabe na semana planejada", "pre_producao": "Cabe com pré-produção", "a_confirmar": "Capacidade a confirmar (fora do calendário)",
                 "insuficiente": "Não cabe até a data de necessidade"}
ASSUMPTIONS = [
    "Capacidade disponível da base já desconta compromissos base e OPs existentes; só as ordens planejadas consomem a sobra.",
    "Capacidade em unidades homogêneas dentro da família; a ordem consome capacidade na semana de início (liberação).",
    "Compromissos base são demanda não detalhada; a premissa não foi validada com a empresa.",
    "Não há capacidade informada depois da última semana do calendário: ordens que começariam depois ficam a confirmar.",
    "Antecipação de OP e redução de OP não liberam nem consomem capacidade nesta conta (conservador).",
]
FIELD_NATURE = {
    "available": {"nature": "observado na fonte", "origin": "Capacidade_Semanal.Capacidade disponível"},
    "allocated": {"nature": "calculado", "origin": "ordens planejadas da projeção (Etapa 15.3) encaixadas na semana de liberação ou antes"},
    "status": {"nature": "calculado", "origin": "alocação: ok, pré-produção, a confirmar ou insuficiente"},
}


def _week(day: date) -> date:
    return day - timedelta(days=day.weekday())


def _calendar(capacity: pd.DataFrame) -> dict[str, dict[str, Any]]:
    families: dict[str, dict[str, Any]] = {}
    for _, row in capacity.sort_values("Semana inicial").iterrows():
        family = str(row["Família"])
        start = pd.Timestamp(row["Semana inicial"]).date()
        entry = families.setdefault(family, {"line": str(row.get("Linha") or ""), "weeks": {}})
        entry["weeks"][_week(start)] = {"available": float(row["Capacidade disponível"]), "maximum": float(row["Capacidade máxima"]),
                                        "occupation": float(row["Ocupação"])}
    return families


def build_capacity_plan(plans: dict[str, dict[str, Any]], indicators: pd.DataFrame, capacity: pd.DataFrame,
                        orders: pd.DataFrame | None = None, reference_date: str | None = None, peak_months: list[int] | None = None) -> dict[str, Any]:
    """Aloca as ordens planejadas e devolve o resultado por SKU, por família e semana e o resumo por família."""
    calendar = _calendar(capacity)
    info = {str(row["SKU"]): row for row in indicators.to_dict("records")}
    reference = date.fromisoformat(reference_date) if reference_date else min((week for item in calendar.values() for week in item["weeks"]), default=date.today())
    reference_week = _week(reference)
    remaining = {family: {week: values["available"] for week, values in item["weeks"].items()} for family, item in calendar.items()}
    allocated = {family: {week: 0.0 for week in item["weeks"]} for family, item in calendar.items()}

    queue = []
    for sku, plan in plans.items():
        for index, order in enumerate(plan.get("planned_orders") or []):
            row = info.get(sku, {})
            queue.append((order["due_date"], str(row.get("abc_curve") or "Z"), sku, index, order, str(row.get("family") or "")))
    results: dict[str, list[dict[str, Any]]] = {sku: [] for sku in plans}
    for due, _, sku, index, order, family in sorted(queue, key=lambda item: item[:4]):
        weeks = remaining.get(family)
        release_week = max(_week(date.fromisoformat(order["release_date"])), reference_week)
        entry = {"index": index, "due_date": order["due_date"], "release_date": order["release_date"], "quantity": order["quantity"],
                 "family": family, "allocations": [], "unscheduled": 0.0}
        if not weeks or release_week > max(weeks):
            entry["status"] = "a_confirmar"
            results[sku].append(entry)
            continue
        need = float(order["quantity"])
        for week in sorted((week for week in weeks if reference_week <= week <= release_week), reverse=True):
            take = min(need, weeks[week])
            if take <= 0:
                continue
            weeks[week] -= take
            allocated[family][week] += take
            need -= take
            entry["allocations"].append({"week_start": week.isoformat(), "quantity": round(take, 1)})
            if need <= 0:
                break
        entry["unscheduled"] = round(need, 1)
        early = any(item["week_start"] < release_week.isoformat() for item in entry["allocations"])
        entry["status"] = "insuficiente" if need > 0 else "pre_producao" if early else "ok"
        results[sku].append(entry)

    skus = {}
    for sku, entries in results.items():
        plan = plans[sku]
        urgent = [entry for entry, order in zip(sorted(entries, key=lambda e: e["index"]), plan.get("planned_orders") or []) if order.get("urgent")]
        worst = max((entry["status"] for entry in entries), key=STATUS_ORDER.get, default="ok")
        worst_now = max((entry["status"] for entry in urgent), key=STATUS_ORDER.get, default="ok")
        skus[sku] = {
            "status": worst if entries else "sem_ordens",
            "status_now": worst_now if urgent else "sem_ordens",
            "status_label": STATUS_LABELS.get(worst, "Sem ordens planejadas"),
            "unscheduled_quantity": round(sum(entry["unscheduled"] for entry in entries), 1),
            "executable_quantity_now": round(sum(entry["quantity"] - entry["unscheduled"] for entry in urgent), 1),
            "orders": sorted(entries, key=lambda entry: entry["index"]),
            "family": str(info.get(sku, {}).get("family") or ""),
        }

    open_orders = orders if orders is not None else pd.DataFrame(columns=["SKU"])
    families = []
    peaks = set(peak_months or [])
    for family, item in calendar.items():
        members = [sku for sku, value in skus.items() if value["family"] == family]
        entries = [entry for sku in members for entry in skus[sku]["orders"]]
        short = [entry for entry in entries if entry["status"] == "insuficiente"]
        peak_entries = [entry for entry in entries if date.fromisoformat(entry["due_date"]).month in peaks]
        peak_status = max((entry["status"] for entry in peak_entries), key=STATUS_ORDER.get, default="ok") if peak_entries else None
        short_skus = sorted({sku for sku in members if skus[sku]["status"] == "insuficiente"})
        affected = open_orders[open_orders["SKU"].isin(short_skus)] if short_skus and not open_orders.empty else open_orders.iloc[0:0]
        weeks = sorted(item["weeks"])
        families.append({
            "family": family, "line": item["line"],
            "calendar_start": weeks[0].isoformat() if weeks else None, "calendar_end": (weeks[-1] + timedelta(days=6)).isoformat() if weeks else None,
            "available_until_calendar_end": round(sum(values["available"] for values in item["weeks"].values()), 1),
            "planned_in_calendar": round(sum(allocated[family].values()), 1),
            "planned_after_calendar": round(sum(entry["quantity"] for entry in entries if entry["status"] == "a_confirmar"), 1),
            "unscheduled_quantity": round(sum(entry["unscheduled"] for entry in short), 1),
            "first_shortfall_due": min((entry["due_date"] for entry in short), default=None),
            "status": max((entry["status"] for entry in entries), key=STATUS_ORDER.get, default="ok"),
            "peak_months": sorted(peaks), "peak_need_units": round(sum(entry["quantity"] for entry in peak_entries), 1), "peak_status": peak_status,
            "skus_short": short_skus,
            "affected_orders": [{"order": str(row["Pedido"]), "sku": str(row["SKU"]), "client": str(row["Cliente/Canal"]), "quantity": float(row["Quantidade"])}
                                for _, row in affected.iterrows()],
            "weeks": [{"week_start": week.isoformat(), "maximum": item["weeks"][week]["maximum"], "available": item["weeks"][week]["available"],
                       "allocated": round(allocated[family][week], 1), "remaining": round(remaining[family][week], 1),
                       "occupation_base": item["weeks"][week]["occupation"]} for week in weeks],
        })
    families.sort(key=lambda family: (-STATUS_ORDER[family["status"]], family["family"]))
    return {"reference_date": reference.isoformat(), "skus": skus, "families": families, "assumptions": ASSUMPTIONS,
            "field_nature": FIELD_NATURE, "status_labels": STATUS_LABELS}
