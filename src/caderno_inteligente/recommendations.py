"""Recomendação operacional por SKU.

Desde a Etapa 15.3, com o plano de suprimento (`supply_plan.build_supply_plans`), a ação e a quantidade saem da projeção
diária datada. Sem plano (entradas sintéticas da validação), vale a conta de "próximo mês" anterior.
"""
from __future__ import annotations

import math
from datetime import date
from typing import Any, Iterable

from .supply_plan import ACTION_LABELS, decide

CAPACITY_CODES = {"CAPACITY_SHORTFALL", "CAPACITY_CONFLICT"}  # CONFLICT: entradas antigas/sintéticas; SHORTFALL: Etapa 15.4
PLAN_ASSUMPTIONS = [
    "Projeção diária a partir da data de planejamento: carteira na data prometida, previsão do mês além da carteira rateada pelos dias e OPs na conclusão prevista.",
    "Estoque de segurança em unidades = demanda diária de referência × dias de segurança.",
    "Ordem planejada: chega na primeira data possível (planejamento + lead time) em que o estoque fica abaixo da segurança e cobre as semanas-alvo seguintes, descontadas as OPs que já chegam nesse período; quantidade arredondada ao lote mínimo.",
    "A quantidade sugerida soma só as ordens com liberação dentro da janela de decisão; as demais aparecem como ordens planejadas.",
    "Capacidade: as ordens planejadas são encaixadas na capacidade livre da linha (Etapa 15.4); a quantidade sugerida não é cortada, e o que não cabe aparece como sem programação.",
]
PLAN_LIMITATIONS = [
    "A base não vincula pedidos a OPs; a carteira tem prioridade sobre a demanda prevista na leitura de atrasos.",
    "A recomendação não cria, antecipa nem reduz ordem de produção: tudo exige validação humana comercial e operacional.",
    "A demanda prevista é rateada por dia dentro do mês; a data exata da falta é estimativa.",
]


def _ptbr(value: str | None) -> str:
    if not value:
        return "—"
    day = date.fromisoformat(value)
    return f"{day.day:02d}/{day.month:02d}"


def _number(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return default if math.isnan(number) else number


def build_operational_recommendation(
    indicator: dict[str, Any], forecast: dict[str, Any], issue_codes: Iterable[str], plan: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Derive a reviewable quantity without claiming production feasibility."""
    issues = set(issue_codes)
    if plan is not None and forecast.get("status") == "ok" and forecast.get("forecast_next_month") is not None:
        return _plan_recommendation(indicator, forecast, issues, plan)
    assumptions = [
        "A previsão do próximo mês e a carteira não são somadas; utiliza-se o maior valor para reduzir dupla contagem.",
        "Estoque de segurança em unidades usa a demanda diária de referência (previsão oficial dos 3 próximos meses) multiplicada pelos dias de segurança.",
        "Capacidade por família é somente contexto e não limita automaticamente a quantidade sugerida.",
    ]
    limitations = [
        "A base não vincula pedidos a ordens de produção por semana.",
        "A recomendação não cria nem libera ordem de produção.",
        "A quantidade precisa de validação humana comercial e operacional.",
    ]

    if forecast.get("status") != "ok" or forecast.get("forecast_next_month") is None:
        return {
            "action": "investigar_dados",
            "action_label": ACTION_LABELS["investigar_dados"],
            "horizon": "próximo mês",
            "suggested_quantity": None,
            "raw_quantity": None,
            "minimum_lot": _number(indicator.get("minimum_lot")),
            "forecast_next_month": None,
            "backlog_quantity": _number(indicator.get("backlog_order_quantity")),
            "safety_stock_quantity": None,
            "current_stock": _number(indicator.get("current_stock")),
            "open_production_quantity": _number(indicator.get("production_order_quantity")),
            "capacity_status": "not_evaluated",
            "confidence": "baixa",
            "confidence_reason": "Histórico insuficiente para produzir uma previsão quantitativa.",
            "rationale": ["Investigar e completar o histórico antes de sugerir produção."],
            "calculation": {},
            "assumptions": assumptions,
            "limitations": limitations,
            "requires_human_review": True,
        }

    next_month = _number(forecast.get("forecast_next_month"))
    backlog = _number(indicator.get("backlog_order_quantity"))
    current_stock = _number(indicator.get("current_stock"))
    open_production = _number(indicator.get("production_order_quantity"))
    daily_demand = _number(indicator.get("reference_daily_demand"), _number(indicator.get("average_sales_per_day")))
    safety_stock = daily_demand * _number(indicator.get("safety_stock_days"))
    demand_to_cover = max(next_month, backlog)
    raw = max(0.0, demand_to_cover + safety_stock - current_stock - open_production)
    minimum_lot = _number(indicator.get("minimum_lot"))
    suggested = math.ceil(raw / minimum_lot) * minimum_lot if minimum_lot > 0 and raw > 0 else math.ceil(raw)
    capacity_conflict = bool(CAPACITY_CODES & issues)

    if suggested > 0 and capacity_conflict:
        action = "produzir_validar_capacidade"
    elif suggested > 0:
        action = "produzir"
    elif "EXCESS_COVERAGE" in issues:
        action = "monitorar_excesso"
    else:
        action = "sem_acao_necessaria"

    confidence = str(forecast.get("forecast_confidence", "baixa"))
    reasons = [f"Confiança preditiva {confidence}, calculada pelo erro no holdout temporal."]
    if not bool(indicator.get("has_sell_out")):
        confidence = "baixa"
        reasons.append("Sell-out não observado; a confiança da recomendação foi reduzida.")
    if capacity_conflict:
        if confidence == "alta":
            confidence = "média"
        reasons.append("A família apresenta pressão de capacidade e exige validação operacional.")

    rationale = [
        f"Demanda a cobrir definida como o maior valor entre previsão ({next_month:.1f}) e carteira ({backlog:.1f}).",
        f"Necessidade bruta de {raw:.1f} unidade(s) antes do arredondamento por lote.",
    ]
    if minimum_lot > 0:
        rationale.append(f"Quantidade arredondada para múltiplo do lote mínimo de {minimum_lot:.1f}.")

    return {
        "action": action,
        "action_label": ACTION_LABELS[action],
        "horizon": "próximo mês",
        "suggested_quantity": float(suggested),
        "raw_quantity": round(raw, 1),
        "minimum_lot": minimum_lot,
        "forecast_next_month": next_month,
        "backlog_quantity": backlog,
        "safety_stock_quantity": round(safety_stock, 1),
        "current_stock": current_stock,
        "open_production_quantity": open_production,
        "capacity_status": "requires_review" if capacity_conflict else "family_context_available",
        "confidence": confidence,
        "confidence_reason": " ".join(reasons),
        "rationale": rationale,
        "calculation": {
            "demand_to_cover": round(demand_to_cover, 1),
            "forecast_next_month": next_month,
            "backlog_quantity": backlog,
            "safety_stock_quantity": round(safety_stock, 1),
            "current_stock": current_stock,
            "open_production_quantity": open_production,
            "raw_quantity": round(raw, 1),
        },
        "assumptions": assumptions,
        "limitations": limitations,
        "requires_human_review": True,
    }


def _confidence(indicator: dict[str, Any], forecast: dict[str, Any], issues: set[str]) -> tuple[str, list[str]]:
    confidence = str(forecast.get("forecast_confidence", "baixa"))
    reasons = [f"Confiança preditiva {confidence}, calculada pelo erro da previsão em testes com meses já vendidos."]
    if not bool(indicator.get("has_sell_out")):
        confidence = "baixa"
        reasons.append("Sell-out não observado; a confiança da recomendação foi reduzida.")
    if CAPACITY_CODES & issues:
        if confidence == "alta":
            confidence = "média"
        reasons.append("Há ordem planejada que não cabe na capacidade livre da linha; exige validação operacional.")
    return confidence, reasons


def _rationale(action: str, plan: dict[str, Any]) -> list[str]:
    planned, adjustments, late = plan["planned_orders"], plan["op_adjustments"], plan["affected_orders"]
    lines = []
    if action == "atraso_inevitavel":
        when = plan["first_shortfall_date"] or (late[0]["promised_date"] if late else None)
        lines.append(f"Falta projetada a partir de {_ptbr(when)}; uma reposição nova só chega em {_ptbr(plan['earliest_arrival'])} (lead time de {plan['lead_time_days']} dias).")
    if action == "antecipar_op":
        lines += [item["reason"] for item in adjustments if item["adjustment"] == "antecipar"]
    if late:
        listed = ", ".join(f"{item['order']} ({item['client']}, {item['quantity']:.0f} un., {_ptbr(item['promised_date'])})" for item in late[:3])
        lines.append(f"Pedidos que não saem na data prometida: {listed}{'…' if len(late) > 3 else ''}.")
    if action == "rever_op" or any(item["adjustment"] in ("reduzir", "cancelar") for item in adjustments):
        lines += [f"{item['order']}: {item['reason']}" for item in adjustments if item["adjustment"] in ("reduzir", "cancelar")]
    if planned:
        first = planned[0]
        lines.append(f"Ordem planejada de {first['quantity']:.0f} un. para chegar em {_ptbr(first['due_date'])}, liberando até {_ptbr(first['release_date'])}"
                     + (f"; mais {len(planned) - 1} ordem(ns) até {_ptbr(plan['horizon_end'])}." if len(planned) > 1 else "."))
    capacity = plan.get("capacity") or {}
    short = [order for order in capacity.get("orders", []) if order["status"] == "insuficiente"]
    if short:
        listed = ", ".join(f"{order['unscheduled']:.0f} un. para {_ptbr(order['due_date'])}" for order in short[:3])
        lines.append(f"Capacidade: a linha {capacity.get('family') or ''} não comporta {listed} até a data de necessidade; antecipar, terceirizar ou repriorizar.")
    if action == "monitorar_excesso":
        lines.append("Cobertura atual acima do limite de excesso, sem OP aberta a rever: acompanhar sem produzir agora.")
    if action == "sem_acao_necessaria":
        lines.append(f"Estoque projetado acima da segurança até {_ptbr(plan['horizon_end'])}, sem pedido atrasado nem OP a rever.")
    return lines


def _plan_recommendation(indicator: dict[str, Any], forecast: dict[str, Any], issues: set[str], plan: dict[str, Any]) -> dict[str, Any]:
    action, secondary = decide(plan, issues)
    if action == "produzir" and CAPACITY_CODES & issues:
        action = "produzir_validar_capacidade"
    label = ACTION_LABELS[action]
    urgent = [order for order in plan["planned_orders"] if order["urgent"]]
    if action in ("produzir", "produzir_validar_capacidade") and not urgent and plan["planned_orders"]:
        label = f"{label} (liberar a partir de {_ptbr(plan['planned_orders'][0]['release_date'])})"
    confidence, reasons = _confidence(indicator, forecast, issues)
    calculation = plan["calculation"]
    return {
        "action": action,
        "action_label": label,
        "secondary_actions": secondary,
        "horizon": f"projeção diária de {_ptbr(plan['reference_date'])} a {_ptbr(plan['horizon_end'])}",
        "suggested_quantity": plan["suggested_quantity"],
        "raw_quantity": calculation["raw_quantity"],
        "planned_quantity_horizon": plan["planned_quantity_horizon"],
        "minimum_lot": _number(indicator.get("minimum_lot")),
        "forecast_next_month": _number(forecast.get("forecast_next_month")),
        "backlog_quantity": _number(indicator.get("backlog_order_quantity")),
        "safety_stock_quantity": plan["safety_stock_quantity"],
        "current_stock": _number(indicator.get("current_stock")),
        "open_production_quantity": _number(indicator.get("production_order_quantity")),
        "capacity_status": "requires_review" if CAPACITY_CODES & issues else "family_context_available",
        "capacity": plan.get("capacity"),
        "confidence": confidence,
        "confidence_reason": " ".join(reasons),
        "rationale": _rationale(action, plan),
        "calculation": calculation,
        "reference_date": plan["reference_date"],
        "earliest_arrival": plan["earliest_arrival"],
        "decision_window_end": plan["decision_window_end"],
        "first_shortfall_date": plan["first_shortfall_date"],
        "planned_orders": plan["planned_orders"],
        "op_adjustments": plan["op_adjustments"],
        "affected_orders": plan["affected_orders"],
        "projection": plan["projection"],
        "assumptions": PLAN_ASSUMPTIONS,
        "limitations": PLAN_LIMITATIONS,
        "requires_human_review": True,
    }
