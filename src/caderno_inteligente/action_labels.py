"""Rótulos de ação do desafio como camada derivada dos sinais já calculados.

Não é um motor novo: lê a ação operacional, a ação comercial, os alertas de evento e os sinais dos canais diretos e
emite um segundo campo (`challenge_action`) com rótulo, sinais usados, evidências e limitações. Os campos `action`
existentes, o score, o ranking e as quantidades não são alterados. Dado insuficiente sempre vence: sem evidência, o
rótulo é "Investigar" com o motivo, nunca uma oportunidade inferida.
"""
from __future__ import annotations

import json
import math
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterable

DEFAULT_SETTINGS: dict[str, Any] = {
    "priority_top_n": 10,
    "event_decision_window_days": 30,
    "partner_min_opportunities": 2,
    "recompra_min_sell_in_months": 3,
    "recompra_min_months_without_sell_in": 2,
}

LABELS = {
    "produzir": "Produzir",
    "repor": "Repor",
    "priorizar_producao": "Priorizar produção",
    "priorizar_parceiro": "Priorizar parceiro",
    "ampliar_mix": "Ampliar mix",
    "recomendar_recompra": "Recomendar recompra",
    "reativar": "Reativar",
    "monitorar": "Monitorar",
    "investigar": "Investigar",
    "sem_acao_necessaria": "Sem ação necessária",
}
# As nove ações do PDF do desafio; "Reativar" vem das oportunidades de reativação do mesmo documento.
CHALLENGE_PDF_CODES = ("produzir", "repor", "priorizar_producao", "priorizar_parceiro", "ampliar_mix", "recomendar_recompra", "monitorar", "investigar", "sem_acao_necessaria")

DEFINITIONS = {
    "produzir": "Há ordem planejada no horizonte, segundo a projeção diária de estoque, carteira, previsão e OPs abertas.",
    "repor": "O estoque estimado do parceiro cobre poucos dias do giro observado; avaliar reposição comercial.",
    "priorizar_producao": "Produzir com urgência: o SKU está entre os primeiros da fila de atenção ou tem decisão de evento próxima.",
    "priorizar_parceiro": "O parceiro reúne várias oportunidades de reposição, incluindo SKU entre os primeiros da fila de atenção.",
    "ampliar_mix": "Produto ativo sem nenhum faturamento em um canal com visibilidade completa; avaliar incluí-lo no mix.",
    "recomendar_recompra": "O parceiro vende bem, mas parou de receber sell-in há mais tempo que o ritmo do próprio par; recomendar nova compra.",
    "reativar": "O SKU vendia no canal e ficou meses sem faturar; avaliar reativação.",
    "monitorar": "Sem urgência: acompanhar excesso de estoque, saída de linha ou crescimento.",
    "investigar": "Faltam dados ou há divergência; investigar antes de decidir. Nenhuma oportunidade é inferida.",
    "sem_acao_necessaria": "Nenhum sinal que justifique ação neste horizonte.",
}

PRECEDENCE = {
    "operational": ["investigar (dado insuficiente)", "priorizar produção (antecipar OP ou falta inevitável)", "priorizar produção ou produzir (ordem planejada)",
                    "investigar (rever OP)", "monitorar (excesso)", "sem ação necessária"],
    "commercial": ["investigar (dado antigo, insuficiente ou divergente)", "repor", "recomendar recompra", "monitorar"],
    "partner": ["priorizar parceiro (várias reposições com SKU de alta prioridade)"],
    "channel": ["ampliar mix", "reativar", "monitorar saída de linha", "investigar queda", "monitorar crescimento", "sem ação necessária"],
}

LIMITATIONS = {
    "operational": [
        "Não cria nem libera ordem de produção; a quantidade oficial não muda.",
        "Capacidade da família é só contexto e não comprova viabilidade individual.",
    ],
    "commercial": [
        "Estoque do parceiro é estimado, não é o estoque do CD.",
        "Ausência de registro não é venda zero; nenhum parceiro sem sell-out recebe oportunidade inferida.",
        "Sugestão demonstrativa; exige revisão humana.",
    ],
    "partner": [
        "Conta apenas pares parceiro–SKU com sell-out suficiente; ausência de dado não conta como oportunidade.",
        "A prioridade do SKU vem do ranking oficial e não é alterada.",
    ],
    "channel": [
        "A visibilidade vem do faturamento; os canais diretos não têm sell-in nem sell-out.",
        "Sem estoque por canal. Sugestão demonstrativa; exige revisão humana.",
    ],
}


def load_action_settings(path: str | Path | None = None) -> dict[str, Any]:
    values = dict(DEFAULT_SETTINGS)
    if path is not None:
        overrides = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(overrides, dict) or set(overrides) - set(values):
            raise ValueError("Configuração dos rótulos de ação contém campos desconhecidos")
        values.update(overrides)
    return _validate_settings(values)


def _validate_settings(values: dict[str, Any]) -> dict[str, Any]:
    if set(values) != set(DEFAULT_SETTINGS):
        raise ValueError("Parâmetro dos rótulos de ação desconhecido")
    for key, value in values.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value != int(value):
            raise ValueError(f"Parâmetro dos rótulos de ação deve ser inteiro: {key}")
        values[key] = int(value)
    if values["priority_top_n"] < 1 or values["partner_min_opportunities"] < 1 or values["recompra_min_sell_in_months"] < 2:
        raise ValueError("Limites mínimos dos rótulos de ação inválidos")
    if values["event_decision_window_days"] < 0 or values["recompra_min_months_without_sell_in"] < 1:
        raise ValueError("Janela dos rótulos de ação inválida")
    return values


def _result(code: str, source: str, origin_action: str | None, signals: list[str], evidence: list[dict[str, Any]], reason: str, extra_limitations: Iterable[str] = ()) -> dict[str, Any]:
    return {
        "code": code, "label": LABELS[code], "source": source, "origin_action": origin_action, "reason": reason,
        "signals_used": signals, "evidence": evidence, "limitations": [*LIMITATIONS[source], *extra_limitations],
        "requires_human_review": True,
    }


def _ev(label: str, value: Any, origin: str) -> dict[str, Any]:
    return {"label": label, "value": value, "origin": origin}


# --------------------------------------------------------------- SKU (operacional)

def label_operational(
    action: str, priority: int | None, forecast_status: str | None, event_alerts: list[dict] | None, capacity_status: str | None,
    reference_date: date | None, settings: dict[str, Any],
) -> dict[str, Any]:
    """Ação operacional do SKU → rótulo do desafio. `event_alerts` None significa análise de eventos indisponível."""
    if action == "investigar_dados" or forecast_status == "insufficient_data":
        return _result("investigar", "operational", action, ["INSUFFICIENT_FORECAST_HISTORY"], [_ev("Previsão", "histórico insuficiente", "forecasting")],
                       "Histórico insuficiente para prever; investigar e completar os dados antes de sugerir produção.")
    if action in ("atraso_inevitavel", "antecipar_op"):
        reason = ("Falta antes que qualquer reposição nova chegue: garantir a OP, priorizar os pedidos e renegociar prazos com os clientes afetados."
                  if action == "atraso_inevitavel" else "Uma OP ainda não iniciada pode chegar antes da falta: antecipar o início.")
        evidence = [] if priority is None else [_ev("Posição na fila de atenção", priority, "ranking oficial")]
        return _result("priorizar_producao", "operational", action, ["PROJECTED_SHORTFALL" if action == "atraso_inevitavel" else "OP_ANTICIPATION"], evidence, reason,
                       ["A data da falta vem da projeção diária: carteira na data prometida, previsão rateada e OPs na conclusão prevista."])
    if action == "rever_op":
        return _result("investigar", "operational", action, ["OP_REVIEW"], [] if priority is None else [_ev("Posição na fila de atenção", priority, "ranking oficial")],
                       "Rever a OP: ela supera a necessidade projetada ou é de produto em descontinuação. Não produzir antes de confirmar.")
    if action in ("produzir", "produzir_validar_capacidade"):
        signals, evidence, reasons = [f"operational_action:{action}"], [], []
        extra = ["A capacidade da família está pressionada: validar antes de executar."] if action == "produzir_validar_capacidade" or capacity_status == "requires_review" else []
        if priority is not None:
            evidence.append(_ev("Posição na fila de atenção", priority, "ranking oficial"))
            if priority <= settings["priority_top_n"]:
                signals.append(f"priority_top_{settings['priority_top_n']}")
                reasons.append(f"posição {priority} na fila de atenção (limite {settings['priority_top_n']})")
        urgent_event = None
        if event_alerts and reference_date is not None:
            limit = reference_date + timedelta(days=settings["event_decision_window_days"])
            for alert in sorted(event_alerts, key=lambda item: item.get("decision_date") or "9999"):
                if alert.get("decision_date") and alert.get("in_horizon") and date.fromisoformat(alert["decision_date"]) <= limit:
                    urgent_event = alert
                    break
        if urgent_event:
            signals.append(f"event_decision:{urgent_event['event_id']}")
            evidence.append(_ev(f"Decisão de {urgent_event['event']}", urgent_event["decision_date"], "Calendario_Eventos − lead time"))
            reasons.append(f"decisão de {urgent_event['event']} até {urgent_event['decision_date']} (janela de {settings['event_decision_window_days']} dias)")
        if event_alerts is None:
            extra.append("A análise de eventos estava indisponível; o critério de evento não foi avaliado.")
        if reasons:
            return _result("priorizar_producao", "operational", action, signals, evidence, "Produzir com urgência: " + "; ".join(reasons) + ".", extra)
        return _result("produzir", "operational", action, signals, evidence, "Há necessidade líquida de produção no próximo mês, sem urgência de fila ou de evento.", extra)
    if action == "monitorar_excesso":
        return _result("monitorar", "operational", action, ["EXCESS_COVERAGE"], [], "Excesso de cobertura; acompanhar sem produzir.")
    return _result("sem_acao_necessaria", "operational", action, [], [], "Sem necessidade de produção neste horizonte; os riscos do SKU continuam.")


# --------------------------------------------------------------- parceiro–SKU (comercial)

def _month(value: str | None) -> int | None:
    if not value:
        return None
    year, month = value[:7].split("-")
    return int(year) * 12 + int(month) - 1


def recompra_signal(row: dict[str, Any], settings: dict[str, Any]) -> dict[str, Any] | None:
    """Meses sem sell-in acima do ritmo do próprio par, com sell-out recente positivo. None se não houver base."""
    reference = _month(row.get("reference_month"))
    months = sorted({_month(period["month"]) for period in row.get("periods", []) if period.get("sell_in_quantity") is not None and period.get("month")} - {None})
    average = row.get("average_monthly_sell_out")
    if reference is None or len(months) < settings["recompra_min_sell_in_months"] or not average or average <= 0:
        return None
    gaps = sorted(later - earlier for earlier, later in zip(months, months[1:]))
    typical = gaps[len(gaps) // 2] if len(gaps) % 2 else (gaps[len(gaps) // 2 - 1] + gaps[len(gaps) // 2]) / 2
    since = reference - months[-1]
    if since >= max(settings["recompra_min_months_without_sell_in"], math.ceil(typical * 2)):
        return {"last_sell_in_month": f"{months[-1] // 12}-{months[-1] % 12 + 1:02d}", "typical_interval_months": typical, "months_without_sell_in": since, "average_monthly_sell_out": average}
    return None


def label_commercial_row(row: dict[str, Any], settings: dict[str, Any]) -> dict[str, Any]:
    action, quality = row["action"], row.get("data_quality")
    pair = f"{row['partner']} · {row['sku']}"
    if action in ("solicitar_atualizacao", "dados_insuficientes", "investigar_divergencia"):
        why = {"solicitar_atualizacao": "Dado antigo ou descontínuo; atualizar antes de qualquer oportunidade.",
               "dados_insuficientes": "Sem sell-out suficiente (amostra, estoque estimado ou natureza declarada); nenhuma oportunidade é inferida.",
               "investigar_divergencia": "Sell-in e sell-out divergem nos mesmos meses; conferir registros antes de decidir."}[action]
        signals = [signal["code"] for signal in row.get("signals", [])] or [action.upper()]
        evidence = [_ev("Qualidade do dado", quality, "partner_insights")]
        if action == "investigar_divergencia":
            evidence.append(_ev("Diferença sell-in − sell-out (un.)", row.get("comparable_difference"), "Sell_In e Sell_Out, meses comparáveis"))
        if action == "solicitar_atualizacao":
            evidence.append(_ev("Idade do último sell-out (meses)", row.get("age_months"), "Sell_Out"))
        return _result("investigar", "commercial", action, signals, evidence, why)
    evidence = [_ev("Giro médio de sell-out (un./mês)", row.get("average_monthly_sell_out"), "Sell_Out"), _ev("Estoque estimado no parceiro (un.)", row.get("estimated_stock"), "Sell_Out, estimado")]
    if action == "avaliar_reposicao":
        evidence.insert(0, _ev("Cobertura estimada (dias)", None if row.get("coverage_days") is None else round(row["coverage_days"], 1), "Sell_Out"))
        return _result("repor", "commercial", action, [signal["code"] for signal in row.get("signals", [])], evidence, f"Cobertura estimada baixa para o giro observado em {pair}; avaliar reposição.")
    recompra = recompra_signal(row, settings)
    if recompra:
        evidence = [_ev("Último sell-in", recompra["last_sell_in_month"], "Sell_In"), _ev("Intervalo típico entre envios (meses)", recompra["typical_interval_months"], "Sell_In do próprio par"),
                    _ev("Meses sem sell-in", recompra["months_without_sell_in"], "Sell_In"), *evidence]
        return _result("recomendar_recompra", "commercial", action, ["RECOMPRA_GAP"], evidence,
                       f"O par {pair} vende (giro positivo) mas está há {recompra['months_without_sell_in']} meses sem sell-in, acima do ritmo do próprio par.")
    return _result("monitorar", "commercial", action, [signal["code"] for signal in row.get("signals", [])], evidence, "Dados suficientes, sem exceção; acompanhar o estoque do parceiro sem afirmar excesso.")


def label_partner(summary: dict[str, Any], rows: list[dict[str, Any]], priority_by_sku: dict[str, int | None], settings: dict[str, Any]) -> dict[str, Any] | None:
    """`rows` são as linhas do parceiro já com `challenge_action`. Só rotula 'Priorizar parceiro'; os demais ficam sem rótulo no nível do parceiro."""
    opportunities = [row for row in rows if row["challenge_action"]["code"] == "repor"]
    top = [row for row in opportunities if (priority_by_sku.get(row["sku"]) or math.inf) <= settings["priority_top_n"]]
    if len(opportunities) < settings["partner_min_opportunities"] or not top:
        return None
    evidence = [_ev("Pares com oportunidade de reposição", len(opportunities), "partner_insights"),
                *[_ev(f"Posição de {row['sku']} na fila de atenção", priority_by_sku[row["sku"]], "ranking oficial") for row in sorted(top, key=lambda item: priority_by_sku[item["sku"]])]]
    return _result("priorizar_parceiro", "partner", "avaliar_reposicao", ["REPOSITION_OPPORTUNITY", f"priority_top_{settings['priority_top_n']}"], evidence,
                   f"{len(opportunities)} pares com oportunidade de reposição em {summary.get('name') or summary['code']}, incluindo SKU entre os {settings['priority_top_n']} primeiros da fila de atenção.")


# --------------------------------------------------------------- canais diretos

_CHANNEL_MAP = {
    "avaliar_ampliacao_mix": "ampliar_mix", "avaliar_reativacao": "reativar", "investigar_queda": "investigar",
    "monitorar_saida_de_linha": "monitorar", "acompanhar_crescimento": "monitorar", "sem_acao_necessaria": "sem_acao_necessaria",
}


def label_channel_row(row: dict[str, Any]) -> dict[str, Any]:
    suggestion = row["suggestion"]
    code = _CHANNEL_MAP[suggestion["code"]]
    evidence = [_ev("Faturamento nos 24 meses", row.get("revenue_24m"), "Vendas_24m"), _ev("Tendência recente", row.get("trend"), "Vendas_24m"), _ev("Último mês com faturamento", row.get("last_month"), "Vendas_24m")]
    return _result(code, "channel", suggestion["code"], list(row.get("signals", [])), evidence, suggestion["reason"])


def known_codes() -> tuple[str, ...]:
    return tuple(LABELS)
