from __future__ import annotations

import logging
import math
import os
import sys
from pathlib import Path
from threading import Lock
from time import perf_counter

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from caderno_inteligente.cases import STATUSES  # noqa: E402
from caderno_inteligente.feedback import (  # noqa: E402
    ACTIONS,
    PARTNER_DATA_EFFECTS,
)
from caderno_inteligente.forecasting import build_demand_forecasts  # noqa: E402
from caderno_inteligente.indicators import build_sku_indicators  # noqa: E402
from caderno_inteligente.ingestion import load_workbook  # noqa: E402
from caderno_inteligente.prioritization import load_weights, prioritize  # noqa: E402
from caderno_inteligente.persistence import build_persistence  # noqa: E402
from caderno_inteligente.recommendations import build_operational_recommendation  # noqa: E402
from caderno_inteligente.rules import evaluate_rules, load_rule_thresholds  # noqa: E402
from caderno_inteligente.transformations import normalise_dataset  # noqa: E402
from caderno_inteligente.validation import validate_dataset  # noqa: E402

SOURCE = ROOT / "data/source/Base de Dados - Caderno Inteligente.xlsm"
FEEDBACK_DB = ROOT / "runtime/feedback.db"
CASES_DB = ROOT / "runtime/cases.db"
RUNS_DB = ROOT / "runtime/runs.db"
WEIGHTS_FILE = ROOT / "config/prioritization_weights.json"
THRESHOLDS_FILE = ROOT / "config/rule_thresholds.json"

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("caderno_inteligente.api")


def _persistence():
    """Select PostgreSQL in production and retain SQLite for local development."""
    return build_persistence(
        database_url=os.getenv("DATABASE_URL"),
        cases_db=CASES_DB,
        feedback_db=FEEDBACK_DB,
        runs_db=RUNS_DB,
    )


def _allowed_origins() -> list[str]:
    value = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    return [origin.strip() for origin in value.split(",") if origin.strip()]


app = FastAPI(
    title="Caderno Inteligente API",
    description="API local e auditável para apoio à decisão do PCP.",
    version="0.2.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)


def _file_signature(path: Path) -> tuple[int, int]:
    stat = path.stat()
    return stat.st_mtime_ns, stat.st_size


def _pipeline_signature() -> tuple[tuple[int, int], ...]:
    return tuple(_file_signature(path) for path in (SOURCE, WEIGHTS_FILE, THRESHOLDS_FILE))


_pipeline_lock = Lock()
_pipeline_cache: tuple[tuple[tuple[int, int], ...], tuple] | None = None
_cache_hits = 0


def _build_pipeline():
    started = perf_counter()
    dataset = normalise_dataset(load_workbook(SOURCE))
    quality = validate_dataset(dataset)
    indicators = build_sku_indicators(dataset)
    issues = evaluate_rules(indicators, load_rule_thresholds())
    ranking = prioritize(issues, load_weights(), indicators)
    forecasts = build_demand_forecasts(dataset["Vendas_24m"])
    logger.info(
        "pipeline_built duration_ms=%.1f skus=%s issues=%s",
        (perf_counter() - started) * 1000,
        len(indicators),
        len(issues),
    )
    return dataset, quality, indicators, issues, ranking, forecasts


def pipeline():
    """Return cached data, invalidated when the source or configuration changes."""
    global _pipeline_cache, _cache_hits
    signature = _pipeline_signature()
    with _pipeline_lock:
        if _pipeline_cache and _pipeline_cache[0] == signature:
            _cache_hits += 1
            return _pipeline_cache[1]
        result = _build_pipeline()
        _pipeline_cache = (signature, result)
        return result


def data():
    _, quality, indicators, issues, ranking, _ = pipeline()
    return quality, indicators, issues, ranking


def _records(frame):
    """Convert a DataFrame to JSON-safe records, preserving absent values as null."""
    return frame.astype(object).where(frame.notna(), None).to_dict("records")


def _forecast_record(forecasts, sku: str):
    rows = forecasts[forecasts.sku == sku]
    if not rows.empty:
        return _records(rows)[0]
    return {
        "sku": sku,
        "status": "insufficient_data",
        "forecast_confidence": "baixa",
        "forecast_months": [],
        "forecast_values": [],
        "forecast_next_month": None,
        "forecast_total_3m": None,
        "limitation": "Não há histórico mensal disponível para este SKU.",
    }


def _recommendation_for(indicator, forecast, item_issues):
    return build_operational_recommendation(
        indicator,
        forecast,
        (item["code"] for item in item_issues),
    )


def _rupture_summary(issues):
    """Summarize rupture rules without counting the same SKU twice."""
    rupture_codes = ("RUP_LEAD_TIME", "RUP_SAFETY_STOCK")
    rupture_issues = issues[issues["code"].isin(rupture_codes)]
    return {
        "rupture_sku_count": int(rupture_issues["sku"].nunique()),
        "below_lead_time_count": int(
            rupture_issues.loc[rupture_issues["code"] == "RUP_LEAD_TIME", "sku"].nunique()
        ),
        "below_safety_stock_count": int(
            rupture_issues.loc[rupture_issues["code"] == "RUP_SAFETY_STOCK", "sku"].nunique()
        ),
        "rupture_signal_count": int(len(rupture_issues)),
    }


@app.get("/api/health")
def health():
    persistence = _persistence()
    try:
        database_status = "ok" if persistence.health() else "unavailable"
    except Exception:
        logger.warning("database_health_failed persistence=%s", persistence.kind)
        database_status = "unavailable"
    return {
        "status": "ok" if database_status == "ok" else "degraded",
        "source_available": SOURCE.exists(),
        "database": database_status,
        "persistence": persistence.kind,
        "cache": {"loaded": _pipeline_cache is not None, "hits": _cache_hits},
    }


@app.get("/api/overview")
def overview():
    _, indicators, issues, ranking = data()
    rupture = _rupture_summary(issues)
    decisions = _persistence().feedback_summary()
    return {
        "total_skus": len(indicators),
        "prioritized": len(ranking),
        # Compatibilidade temporária: risk_count agora possui a mesma semântica
        # corrigida de rupture_sku_count. rupture_signal_count preserva o total
        # anterior de ocorrências para consumidores que precisem dessa informação.
        "risk_count": rupture["rupture_sku_count"],
        **rupture,
        "order_without_production": int((issues.code == "ORDER_WITHOUT_PRODUCTION").sum()),
        "excess_count": int((issues.code == "EXCESS_COVERAGE").sum()),
        "low_confidence": int((ranking.confidence == "baixa").sum()),
        "risk_distribution": issues.code.value_counts().to_dict(),
        "confidence_distribution": ranking.confidence.value_counts().to_dict(),
        **decisions,
    }


@app.get("/api/priorities")
def priorities(family: str | None = None, confidence: str | None = None, search: str | None = None):
    *_, ranking = data()
    result = ranking
    if family:
        result = result[result.family == family]
    if confidence:
        result = result[result.confidence == confidence]
    if search:
        result = result[
            result.sku.str.contains(search, case=False, na=False)
            | result.product.str.contains(search, case=False, na=False)
        ]
    return _records(result)


@app.get("/api/forecasts")
def forecast_summaries():
    """Consolidate cached forecasts and recommendations without changing the official ranking."""
    _, _, indicators, issues, ranking, forecasts = pipeline()
    ranking_by_sku = {item["sku"]: item for item in _records(ranking)}
    forecast_by_sku = {item["sku"]: item for item in _records(forecasts)}
    issues_by_sku: dict[str, list[dict]] = {}
    for item in issues.to_dict("records"):
        issues_by_sku.setdefault(item["sku"], []).append(item)

    result = []
    for indicator in _records(indicators):
        sku = indicator["SKU"]
        ranked = ranking_by_sku.get(sku)
        forecast = forecast_by_sku.get(sku) or _forecast_record(forecasts, sku)
        recommendation = _recommendation_for(
            indicator,
            forecast,
            issues_by_sku.get(sku, []),
        )
        result.append(
            {
                "sku": sku,
                "product": indicator["Produto"],
                "family": indicator["family"],
                "priority": ranked["priority"] if ranked else None,
                "attention_score": ranked["attention_score"] if ranked else None,
                "confidence": ranked["confidence"] if ranked else forecast["forecast_confidence"],
                "confidence_reason": ranked["confidence_reason"] if ranked else (
                    "SKU fora do ranking oficial; a confiança exibida vem do backtest da previsão."
                ),
                "forecast": forecast,
                "operational_recommendation": {
                    key: recommendation[key]
                    for key in (
                        "action",
                        "action_label",
                        "suggested_quantity",
                        "minimum_lot",
                        "capacity_status",
                        "confidence",
                        "confidence_reason",
                        "requires_human_review",
                    )
                },
            }
        )

    return sorted(
        result,
        key=lambda item: (
            item["priority"] is None,
            item["priority"] if item["priority"] is not None else math.inf,
            item["sku"],
        ),
    )


@app.get("/api/priorities/{sku}")
def detail(sku: str):
    _, _, indicators, issues, ranking, forecasts = pipeline()
    row = indicators[indicators.SKU == sku]
    if row.empty:
        raise HTTPException(404, "SKU não encontrado")
    weights = load_weights()
    item_issues = issues[issues.sku == sku].to_dict("records")
    contributions = [
        {
            "code": item["code"],
            "weight": weights[item["code"]],
            "description": item["description"],
        }
        for item in item_issues
    ]
    indicator = _records(row)[0]
    forecast = _forecast_record(forecasts, sku)
    recommendation = _recommendation_for(indicator, forecast, item_issues)
    return {
        "indicator": indicator,
        "issues": item_issues,
        "priority": _records(ranking[ranking.sku == sku]),
        "score_contributions": contributions,
        "forecast": forecast,
        "operational_recommendation": recommendation,
        "limitation": "A base não vincula pedidos a OPs por semana; capacidade é contexto familiar, não promessa de viabilidade individual.",
    }


class Scenario(BaseModel):
    weights: dict[str, int] | None = None
    thresholds: dict[str, float] | None = None


@app.post("/api/scenarios")
def scenario(item: Scenario):
    dataset, _, indicators, _, _, _ = pipeline()
    thresholds = {**load_rule_thresholds(), **(item.thresholds or {})}
    weights = {**load_weights(), **(item.weights or {})}
    scenario_issues = evaluate_rules(indicators, thresholds)
    ranking = prioritize(scenario_issues, weights, indicators)
    return {
        "is_simulation": True,
        "warning": "Cenário hipotético: não altera pesos, limiares ou ranking oficial.",
        "weights": weights,
        "thresholds": thresholds,
        "ranking": _records(ranking),
        "source_sheets": len(dataset),
    }


def _partner_level(coverage: float) -> str:
    if coverage <= 0:
        return "Sem visibilidade"
    if coverage < 0.40:
        return "Essencial"
    if coverage < 0.80:
        return "Conectado"
    return "Estratégico"


def _partner_maturity(coverage: float, observed_skus: int, total_skus: int) -> dict:
    level = _partner_level(coverage)
    if level == "Sem visibilidade":
        next_level = "Essencial"
        required_skus = 1 if total_skus else 0
        requirement = "Receber sell-out de pelo menos 1 SKU."
    elif level == "Essencial":
        next_level = "Conectado"
        required_skus = max(0, math.ceil(total_skus * 0.40) - observed_skus)
        requirement = f"Observar sell-out de mais {required_skus} SKU(s) para atingir 40% de cobertura."
    elif level == "Conectado":
        next_level = "Estratégico"
        required_skus = max(0, math.ceil(total_skus * 0.80) - observed_skus)
        requirement = f"Observar sell-out de mais {required_skus} SKU(s) para atingir 80% de cobertura."
    else:
        next_level = None
        required_skus = 0
        requirement = "Manter cobertura igual ou superior a 80% e dados atualizados."
    return {
        "level": level,
        "next_level": next_level,
        "next_level_required_skus": required_skus,
        "next_level_requirement": requirement,
    }


@app.get("/api/b2b2c/visibility")
def b2b_visibility():
    dataset, *_ = pipeline()
    partners = dataset["Parceiros_Canais"]
    sell_out = dataset["Sell_Out"]
    total_skus = int(dataset["Produtos"]["SKU"].nunique())
    latest = sell_out["Mês"].max()
    rows = []
    for _, partner in partners[partners["Tipo"] != "Canal direto"].iterrows():
        subset = sell_out[sell_out["Cliente"] == partner["Código"]]
        observed = int(subset["SKU"].nunique())
        coverage = observed / total_skus if total_skus else 0
        rows.append(
            {
                "partner": partner["Código"],
                "name": partner["Nome fictício"],
                "observed_skus": observed,
                "total_skus": total_skus,
                "coverage": coverage,
                "latest_sell_out_month": None if subset.empty else subset["Mês"].max().date().isoformat(),
                "months_observed": int(subset["Mês"].nunique()),
                **_partner_maturity(coverage, observed, total_skus),
            }
        )
    return {
        "reference_month": latest.date().isoformat(),
        "partners": rows,
        "note": "Cobertura representa observação disponível; ausência não equivale a venda zero.",
        "classification_disclaimer": "O nível é uma classificação demonstrativa baseada em cobertura e atualidade. Não representa acordo comercial firmado.",
    }


@app.get("/api/capacity/{family}")
def capacity_timeline(family: str):
    dataset, *_ = pipeline()
    frame = dataset["Capacidade_Semanal"]
    result = frame[frame["Família"] == family].sort_values("Semana inicial")
    if result.empty:
        raise HTTPException(404, "Família não encontrada")
    return {
        "family": family,
        "limitation": "Capacidade é agregada por família; não há vínculo pedido–OP por semana.",
        "weeks": result[
            ["Semana inicial", "Linha", "Capacidade máxima", "Capacidade comprometida", "Capacidade disponível", "Ocupação"]
        ].to_dict("records"),
    }


@app.get("/api/data-quality")
def quality():
    return data()[0]


@app.post("/api/runs")
def create_snapshot():
    quality_report, _, _, ranking = data()
    run_id = _persistence().create_run(
        SOURCE, load_weights(), load_rule_thresholds(), quality_report, _records(ranking)
    )
    return {"id": run_id}


class Case(BaseModel):
    sku: str
    run_id: int | None = None
    status: str = "novo"
    owner: str = ""
    due_date: str = ""
    action: str = ""
    note: str = ""


@app.get("/api/cases")
def cases():
    return _persistence().list_cases()


@app.post("/api/cases")
def case_create(item: Case):
    try:
        return {"id": _persistence().create_case(**item.model_dump())}
    except ValueError as error:
        raise HTTPException(422, str(error)) from error


@app.put("/api/cases/{case_id}")
def case_update(case_id: int, item: Case):
    try:
        persistence = _persistence()
        persistence.update_case(case_id, **item.model_dump(exclude={"sku", "run_id"}))
        return {"status": "updated", "history": persistence.case_history(case_id)}
    except ValueError as error:
        raise HTTPException(422, str(error)) from error


@app.get("/api/cases/{case_id}/history")
def case_history(case_id: int):
    return _persistence().case_history(case_id)


@app.get("/api/runs")
def runs():
    return _persistence().list_runs()


@app.get("/api/runs/{run_id}")
def run_detail(run_id: int):
    result = _persistence().get_run(run_id)
    if not result:
        raise HTTPException(404, "Execução não encontrada")
    return result


@app.get("/api/config")
def config():
    return {
        "weights": load_weights(),
        "thresholds": load_rule_thresholds(),
        "actions": ACTIONS,
        "partner_data_effects": PARTNER_DATA_EFFECTS,
        "case_statuses": STATUSES,
    }


class Feedback(BaseModel):
    sku: str
    action: str
    note: str = ""
    user_name: str = ""
    partner_data_effect: str = "nao_utilizado"
    analysis_minutes: int | None = Field(default=None, ge=0)


@app.get("/api/feedback")
def feedback():
    return [
        {
            "sku": sku,
            "action": action,
            "note": note,
            "user_name": user_name,
            "partner_data_effect": partner_data_effect,
            "analysis_minutes": analysis_minutes,
            "created_at": created_at,
        }
        for sku, action, note, user_name, partner_data_effect, analysis_minutes, created_at
        in _persistence().list_feedback()
    ]


@app.post("/api/feedback")
def feedback_post(item: Feedback):
    try:
        _persistence().save_feedback(
            item.sku,
            item.action,
            item.note,
            item.user_name,
            item.partner_data_effect,
            item.analysis_minutes,
        )
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    return {"status": "created"}


# Additive commercial view: separate configuration; no change to pipeline/ranking.
from backend.partners import create_partner_router  # noqa: E402

app.include_router(create_partner_router(lambda: pipeline()[0], ROOT / "config/commercial_thresholds.json"))

# Additive Week 4 validation view: read-only, reuses the cached pipeline and existing recommendations.
from backend.validation import create_validation_router  # noqa: E402


def _all_operational_recommendations():
    return [item["operational_recommendation"] for item in forecast_summaries()]


app.include_router(create_validation_router(
    pipeline=pipeline,
    persistence=_persistence,
    recommendations=_all_operational_recommendations,
    sku_detail=detail,
    source=SOURCE,
    config_file=ROOT / "config/validation_center.json",
    thresholds_file=THRESHOLDS_FILE,
    commercial_thresholds_file=ROOT / "config/commercial_thresholds.json",
))
