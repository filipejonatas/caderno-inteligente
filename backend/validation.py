"""Additive Week 4 validation route; reads the cached pipeline and never changes the official ranking."""
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from fastapi import APIRouter, HTTPException

from caderno_inteligente.action_labels import load_action_settings
from caderno_inteligente.partner_insights import build_partner_insights, load_commercial_thresholds
from caderno_inteligente.rules import load_rule_thresholds
from caderno_inteligente.validation_center import (
    evaluate_forecasts,
    evaluate_frozen_cases,
    load_validation_config,
    process_comparison,
    safe_behavior_checks,
    summarize_analysis_time,
)

_hash_cache: dict[tuple[str, int, int], str] = {}


def _sha256(path: Path) -> str:
    stat = path.stat()
    key = (str(path), stat.st_mtime_ns, stat.st_size)
    if key not in _hash_cache:
        _hash_cache.clear()
        _hash_cache[key] = hashlib.sha256(path.read_bytes()).hexdigest()
    return _hash_cache[key]


def create_validation_router(*, pipeline: Callable, persistence: Callable, recommendations: Callable, sku_detail: Callable,
                             source: Path, config_file: Path, thresholds_file: Path, commercial_thresholds_file: Path,
                             challenge_actions_file: Path | None = None,
                             describe_error: Callable[[str, Exception], str] | None = None) -> APIRouter:
    router = APIRouter(prefix="/api")
    describe = describe_error or (lambda message, error: f"{message}: {error}")

    @router.get("/validation/summary")
    def validation_summary():
        try:
            config = load_validation_config(config_file)
        except (OSError, ValueError) as error:
            raise HTTPException(422, describe("Configuração de validação inválida", error)) from error
        dataset, _, indicators, issues, ranking, forecasts = pipeline()
        partner_items = build_partner_insights(dataset, load_commercial_thresholds(commercial_thresholds_file))["items"]
        source_sha256 = _sha256(source)

        forecast_evaluation = evaluate_forecasts(dataset["Vendas_24m"], forecasts)
        try:
            analysis_time = summarize_analysis_time(persistence().list_feedback(), int(config["minimum_feedback_sample"]))
            feedback_available = True
        except Exception:
            analysis_time = summarize_analysis_time([], int(config["minimum_feedback_sample"]))
            analysis_time["note"] = "Persistência indisponível; o tempo de análise registrado não pôde ser consultado."
            feedback_available = False
        cases = evaluate_frozen_cases(
            config, indicators=indicators, issues=issues, ranking=ranking, forecasts=forecasts,
            partner_items=partner_items, thresholds=load_rule_thresholds(thresholds_file), source_sha256=source_sha256,
            challenge_settings=None if challenge_actions_file is None else load_action_settings(challenge_actions_file),
        )

        safe = safe_behavior_checks(forecasts, recommendations(), partner_items)
        try:
            sku_detail("__VALIDACAO_SKU_INEXISTENTE__")
            missing_sku_ok = False
        except HTTPException as error:
            missing_sku_ok = error.status_code == 404
        safe.append({"id": "missing_sku", "label": "SKU inexistente retorna 404 sem resultado inventado", "method": "executado",
                     "status": "aprovado" if missing_sku_ok else "reprovado",
                     "evidence": "O detalhe do SKU respondeu 404 para um código inexistente." if missing_sku_ok else "O detalhe não respondeu 404."})
        safe.append({"id": "api_error", "label": "Erro de API mostra mensagem e permite nova tentativa", "method": "teste automatizado",
                     "status": "coberto_por_teste",
                     "evidence": "Verificado em frontend/scripts/test-page-data.mjs (erro HTTP preserva detalhe e permite retry); não é executado nesta rota."})

        failures = [
            {"area": "previsão", "description": f"O modelo selecionado não superou a baseline em {forecast_evaluation['did_not_beat_baseline_skus']} de {forecast_evaluation['eligible_skus']} SKU(s) elegíveis."}
        ] if forecast_evaluation["did_not_beat_baseline_skus"] else []
        failures += [{"area": "casos", "description": f"{item['id']} — {item['title']}: resultado {item['result']}."}
                     for item in cases["items"] if item["result"] in ("falhou", "nao_encontrado")]  # pendente não é falha
        failures += [{"area": "comportamento seguro", "description": f"{item['label']}: reprovado."} for item in safe if item["status"] == "reprovado"]
        failures += [{"area": "cobertura dos casos", "description": f"{item['id']} — {item['title']} usa entrada sintética: {item['origin_reason']}"}
                     for item in cases["items"] if item["origin"] == "synthetic"]
        if not feedback_available:
            failures.append({"area": "tempo de análise", "description": "Persistência indisponível durante a consulta."})

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": {"sha256": source_sha256, "sales_reference_month": forecasts["reference_month"].dropna().max() if not forecasts.empty else None},
            "process_comparison": process_comparison(config, forecast_evaluation, analysis_time),
            "analysis_time": analysis_time,
            "forecast_evaluation": forecast_evaluation,
            "frozen_cases": cases,
            "safe_behavior": safe,
            "known_failures": failures,
            "known_limitations": [
                "Pedidos no prazo e aderência ao plano não são recalculáveis: a base não traz entregas realizadas nem produção realizada.",
                "Decisões não são atribuíveis a parceiros específicos: o feedback não registra o código do parceiro.",
                "Limiares de regras e sinais comerciais são demonstrativos e não foram aprovados pela empresa.",
                "Os casos congelados verificam coerência com a especificação; não medem ganho de negócio.",
            ],
            "adjustments": config["adjustments"],
            "requires_human_review": True,
        }

    return router
