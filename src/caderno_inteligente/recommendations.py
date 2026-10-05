from __future__ import annotations

import math
from typing import Any, Iterable


ACTION_LABELS = {
    "investigar_dados": "Investigar dados",
    "produzir_validar_capacidade": "Produzir após validar capacidade",
    "produzir": "Produzir",
    "monitorar_excesso": "Monitorar excesso",
    "sem_acao_necessaria": "Sem ação necessária",
}


def _number(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return default if math.isnan(number) else number


def build_operational_recommendation(
    indicator: dict[str, Any], forecast: dict[str, Any], issue_codes: Iterable[str]
) -> dict[str, Any]:
    """Derive a reviewable quantity without claiming production feasibility."""
    issues = set(issue_codes)
    assumptions = [
        "A previsão do próximo mês e a carteira não são somadas; utiliza-se o maior valor para reduzir dupla contagem.",
        "Estoque de segurança em unidades usa venda média diária multiplicada pelos dias de segurança.",
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
    safety_stock = _number(indicator.get("average_sales_per_day")) * _number(indicator.get("safety_stock_days"))
    demand_to_cover = max(next_month, backlog)
    raw = max(0.0, demand_to_cover + safety_stock - current_stock - open_production)
    minimum_lot = _number(indicator.get("minimum_lot"))
    suggested = math.ceil(raw / minimum_lot) * minimum_lot if minimum_lot > 0 and raw > 0 else math.ceil(raw)
    capacity_conflict = "CAPACITY_CONFLICT" in issues

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
