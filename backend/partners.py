"""Additive commercial routes, isolated from the official operational ranking."""
from pathlib import Path
from typing import Callable

from fastapi import APIRouter, HTTPException, Query

from caderno_inteligente.action_labels import LABELS as CHALLENGE_LABELS
from caderno_inteligente.partner_insights import ACTION_LABELS, build_partner_insights, load_commercial_thresholds


def create_partner_router(dataset_loader: Callable, thresholds_file: Path, describe_error: Callable[[str, Exception], str] | None = None,
                          enrich: Callable[[dict], dict] | None = None) -> APIRouter:
    router = APIRouter(prefix="/api")
    describe = describe_error or (lambda message, error: f"{message}: {error}")

    def insights():
        try:
            result = build_partner_insights(dataset_loader(), load_commercial_thresholds(thresholds_file))
            return enrich(result) if enrich is not None else result
        except (ValueError, KeyError) as error:
            raise HTTPException(422, describe("Análise comercial bloqueada por dados/configuração inválidos", error)) from error

    def select(result, partner=None, sku=None, region=None, channel=None, action=None, data_quality=None, challenge_action=None):
        if action is not None and action not in ACTION_LABELS:
            raise HTTPException(422, "Ação comercial inválida")
        if data_quality is not None and data_quality not in ("sufficient", "stale", "insufficient"):
            raise HTTPException(422, "Qualidade comercial inválida")
        if challenge_action is not None and challenge_action not in CHALLENGE_LABELS:
            raise HTTPException(422, "Rótulo de ação inválido")
        return [row for row in result["items"] if all(value is None or row[key] == value for key, value in {
            "partner": partner, "sku": sku, "region": region, "channel": channel, "action": action, "data_quality": data_quality,
        }.items()) and (challenge_action is None or row.get("challenge_action", {}).get("code") == challenge_action)]

    def envelope(result, rows, limit, offset):
        return {"reference_month": result["reference_month"], "total": len(rows), "limit": limit, "offset": offset,
                "items": rows[offset:offset + limit], "thresholds": result["thresholds"],
                "field_nature": result["field_nature"], "limitation": result["limitation"],
                **({"challenge_labels": CHALLENGE_LABELS} if enrich is not None else {})}

    @router.get("/partners")
    def partners(partner: str | None = None, sku: str | None = None, region: str | None = None,
                 channel: str | None = None, action: str | None = None, data_quality: str | None = None,
                 challenge_action: str | None = None,
                 limit: int = Query(200, ge=1, le=500), offset: int = Query(0, ge=0)):
        result = insights()
        if challenge_action is not None and challenge_action not in CHALLENGE_LABELS:
            raise HTTPException(422, "Rótulo de ação inválido")
        partner_level = challenge_action == "priorizar_parceiro"  # rótulo do próprio parceiro; os demais vêm das linhas parceiro–SKU
        matched = select(result, partner, sku, region, channel, action, data_quality, None if partner_level else challenge_action)
        codes = {row["partner"] for row in matched}
        filtered_by_rows = any(v is not None for v in (sku, action, data_quality)) or (challenge_action is not None and not partner_level)

        def keep(p):
            if partner_level and (p.get("challenge_action") or {}).get("code") != challenge_action:
                return False
            return (partner is None or p["code"] == partner) and (region is None or p["region"] == region) and (
                channel is None or p["channel"] == channel) and (not filtered_by_rows or p["code"] in codes)

        rows = [p for p in result["partners"] if keep(p)]
        return envelope(result, rows, limit, offset)

    @router.get("/partners/{codigo}")
    def partner_detail(codigo: str):
        result = insights()
        found = next((p for p in result["partners"] if p["code"] == codigo), None)
        if found is None:
            raise HTTPException(404, "Parceiro não encontrado")
        return {"partner": found, "reference_month": result["reference_month"], "thresholds": result["thresholds"],
                "field_nature": result["field_nature"], "limitation": result["limitation"],
                "decisions": {"attribution_available": False, "items": None,
                              "reason": "O feedback existente não registra o código do parceiro. Não é possível atribuir decisões a este parceiro pelo SKU ou pelo efeito genérico de dados de parceiros."}}

    @router.get("/partners/{codigo}/skus")
    def partner_skus(codigo: str, sku: str | None = None, region: str | None = None, channel: str | None = None,
                     action: str | None = None, data_quality: str | None = None, challenge_action: str | None = None,
                     limit: int = Query(200, ge=1, le=500), offset: int = Query(0, ge=0)):
        result = insights()
        if not any(p["code"] == codigo for p in result["partners"]):
            raise HTTPException(404, "Parceiro não encontrado")
        return envelope(result, select(result, codigo, sku, region, channel, action, data_quality, challenge_action), limit, offset)

    @router.get("/commercial-recommendations")
    def commercial_recommendations(partner: str | None = None, sku: str | None = None, region: str | None = None,
                                   channel: str | None = None, action: str | None = None, data_quality: str | None = None,
                                   challenge_action: str | None = None,
                                   limit: int = Query(200, ge=1, le=500), offset: int = Query(0, ge=0)):
        result = insights()
        return envelope(result, select(result, partner, sku, region, channel, action, data_quality, challenge_action), limit, offset)

    return router
