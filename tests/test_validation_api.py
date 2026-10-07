import hashlib
from pathlib import Path

from fastapi.testclient import TestClient

import backend.main as main
from backend.main import app

ROOT = Path(__file__).resolve().parents[1]
GUARDED_FILES = [
    ROOT / "config/prioritization_weights.json",
    ROOT / "config/rule_thresholds.json",
    ROOT / "config/commercial_thresholds.json",
    ROOT / "data/source/Base de Dados - Caderno Inteligente.xlsm",
]


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_validation_summary_contract():
    response = TestClient(app).get("/api/validation/summary")
    assert response.status_code == 200
    body = response.json()
    assert {"process_comparison", "analysis_time", "forecast_evaluation", "frozen_cases", "safe_behavior",
            "known_failures", "known_limitations", "adjustments", "requires_human_review", "source"} <= set(body)
    assert body["requires_human_review"] is True
    natures = {(row["informed"]["nature"], row["recalculated"]["nature"]) for row in body["process_comparison"]}
    assert natures == {("informado", "recalculado")}
    cases = body["frozen_cases"]
    assert len(cases["items"]) == 30
    assert cases["passed"] + cases["failed"] + cases["not_found"] + cases["pending"] == 30
    for item in cases["items"]:
        assert item["result"] in {"passou", "falhou", "nao_encontrado", "pendente"}
        assert item["limitation"] and item["adjustment"]
    # Só a Etapa 15 muda modelo ou pesos, e sempre com a evidência da subetapa no histórico.
    for entry in body["adjustments"]:
        assert entry["changed_weights_or_models"] is False or "docs/historico.md — Etapa 15." in entry["evidence"]


def test_forecast_evaluation_reports_sample_and_matches_existing_backtest():
    client = TestClient(app)
    evaluation = client.get("/api/validation/summary").json()["forecast_evaluation"]
    forecasts = {item["sku"]: item["forecast"] for item in client.get("/api/forecasts").json()}
    assert evaluation["eligible_skus"] + evaluation["insufficient_skus"] == evaluation["total_skus"] == len(forecasts)
    assert evaluation["beat_baseline_skus"] + evaluation["did_not_beat_baseline_skus"] + evaluation["not_comparable_skus"] == evaluation["eligible_skus"]
    for item in evaluation["items"]:
        assert item["selected_model"] == forecasts[item["sku"]]["model"]
        assert item["selected_wape"] == forecasts[item["sku"]]["backtest_wape"]
    roles = [row["role"] for row in evaluation["models"]]
    assert roles.count("baseline") == 1 and roles.count("selecionado") == 1


def test_known_failures_expose_models_that_did_not_beat_baseline():
    body = TestClient(app).get("/api/validation/summary").json()
    if body["forecast_evaluation"]["did_not_beat_baseline_skus"]:
        assert any(item["area"] == "previsão" for item in body["known_failures"])


def test_validation_summary_preserves_ranking_forecasts_and_files():
    client = TestClient(app)
    before = {path: _digest(path) for path in GUARDED_FILES}
    priorities = client.get("/api/priorities").json()
    forecasts = client.get("/api/forecasts").json()
    overview = client.get("/api/overview").json()
    assert client.get("/api/validation/summary").status_code == 200
    assert client.get("/api/priorities").json() == priorities
    assert client.get("/api/forecasts").json() == forecasts
    assert client.get("/api/overview").json() == overview
    assert {path: _digest(path) for path in GUARDED_FILES} == before


def test_validation_summary_survives_unavailable_persistence():
    class Broken:
        kind = "broken"

        def list_feedback(self):
            raise RuntimeError("database offline")

    from fastapi import FastAPI
    from backend.validation import create_validation_router

    isolated = FastAPI()
    isolated.include_router(create_validation_router(
        pipeline=main.pipeline, persistence=lambda: Broken(), recommendations=main._all_operational_recommendations,
        sku_detail=main.detail, source=main.SOURCE, config_file=ROOT / "config/validation_center.json",
        thresholds_file=main.THRESHOLDS_FILE, commercial_thresholds_file=ROOT / "config/commercial_thresholds.json",
    ))
    body = TestClient(isolated).get("/api/validation/summary").json()
    assert body["analysis_time"]["records_with_minutes"] == 0
    assert "indisponível" in body["analysis_time"]["note"]
    assert any(item["area"] == "tempo de análise" for item in body["known_failures"])


def test_safe_behavior_includes_missing_sku_and_api_error_coverage():
    checks = {item["id"]: item for item in TestClient(app).get("/api/validation/summary").json()["safe_behavior"]}
    assert checks["missing_sku"]["status"] == "aprovado"
    assert checks["api_error"]["status"] == "coberto_por_teste"
    assert {"missing_sell_out", "zero_holdout", "insufficient_forecast", "aggregated_capacity", "human_review", "no_false_precision"} <= set(checks)
