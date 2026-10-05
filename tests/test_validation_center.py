import copy
from pathlib import Path

import pandas as pd

from caderno_inteligente.validation_center import (
    _check,
    evaluate_forecasts,
    evaluate_frozen_cases,
    load_validation_config,
    process_comparison,
    safe_behavior_checks,
    summarize_analysis_time,
)

CONFIG = Path(__file__).resolve().parents[1] / "config/validation_center.json"


def _sales(values, sku="SKU-1"):
    return pd.DataFrame({"Mês": pd.date_range("2025-01-01", periods=len(values), freq="MS"), "SKU": sku, "Quantidade faturada": values})


def _forecast(sku="SKU-1", model="moving_average_3", status="ok"):
    return pd.DataFrame([{"sku": sku, "model": model, "status": status, "reference_month": "2026-08-01"}])


def test_baseline_is_explicit_and_does_not_change_selection():
    sales = _sales([100.0] * 12 + [100, 100, 100, 100, 100, 100])
    result = evaluate_forecasts(sales, _forecast())
    roles = {row["model"]: row["role"] for row in result["models"]}
    assert roles["naive_last"] == "baseline"
    assert result["items"][0]["selected_model"] == "moving_average_3"
    # Tie with the baseline is reported as not beating it, never hidden as a win.
    assert result["items"][0]["outcome"] == "nao_superou"
    assert result["did_not_beat_baseline_skus"] == 1


def test_zero_demand_holdout_is_not_comparable_and_excluded_from_weighted_wape():
    sales = _sales([50.0] * 9 + [0.0, 0.0, 0.0])
    result = evaluate_forecasts(sales, _forecast())
    assert result["items"][0]["selected_wape"] is None
    assert result["items"][0]["outcome"] == "nao_comparavel"
    assert result["zero_demand_holdout_skus"] == 1
    selected = next(row for row in result["models"] if row["model"] == "selected")
    assert selected["weighted_wape"] is None and selected["median_wape"] is None


def test_insufficient_forecasts_are_counted_not_scored():
    result = evaluate_forecasts(_sales([10.0] * 4), _forecast(status="insufficient_data", model=None))
    assert result["eligible_skus"] == 0
    assert result["insufficient_skus"] == 1
    assert result["insufficient_sku_list"] == ["SKU-1"]


def test_analysis_time_does_not_claim_gain_with_small_sample():
    rows = [("A", "aceita", "", "", "nao_utilizado", 30, "2026-10-01"), ("B", "aceita", "", "", "nao_utilizado", None, "2026-10-01")]
    result = summarize_analysis_time(rows, minimum_sample=20)
    assert result["records_with_minutes"] == 1
    assert result["total_minutes"] == 30
    assert result["comparison_allowed"] is False
    assert "Nenhum ganho" in result["note"]
    sufficient = summarize_analysis_time([rows[0]] * 20, minimum_sample=20)
    assert sufficient["comparison_allowed"] is True


def test_absent_minutes_are_null_not_zero():
    result = summarize_analysis_time([], minimum_sample=20)
    assert result["total_minutes"] is None and result["average_minutes_per_decision"] is None


def test_process_comparison_separates_informed_recalculated_and_target():
    config = load_validation_config(CONFIG)
    evaluation = {"models": [{"model": "selected", "weighted_wape": 0.07}]}
    rows = {row["id"]: row for row in process_comparison(config, evaluation, summarize_analysis_time([], 20))}
    assert rows["analysis_time"]["informed"] == {"value": 22, "unit": "horas/semana", "nature": "informado", "source": rows["analysis_time"]["informed"]["source"]}
    assert rows["analysis_time"]["target"]["value"] == 8 and rows["analysis_time"]["target"]["nature"] == "meta"
    assert rows["forecast_error"]["recalculated"]["value"] == 0.07
    assert rows["forecast_error"]["recalculated"]["comparable"] is False
    for key in ("on_time_orders", "plan_adherence"):
        assert rows[key]["recalculated"]["value"] is None
        assert rows[key]["recalculated"]["nature"] == "recalculado"


def test_check_operators():
    assert _check("signals", {"includes": ["A"], "excludes": ["B"]}, ["A"])["passed"]
    assert not _check("signals", {"includes": ["A"], "excludes": ["B"]}, ["A", "B"])["passed"]
    assert _check("q", {"is_null": True}, None)["passed"]
    assert not _check("q", {"equals": 0}, None)["passed"]
    assert not _check("q", {"positive": True}, None)["passed"]
    assert _check("p", {"max": 5}, 1)["passed"] and not _check("p", {"max": 5}, None)["passed"]
    assert _check("c", {"not": "alta"}, "média")["passed"]
    assert not _check("m", {"empty": True}, None)["passed"]


def _empty_context():
    return {
        "indicators": pd.DataFrame(columns=["SKU"]), "issues": pd.DataFrame(columns=["sku", "code"]),
        "ranking": pd.DataFrame(columns=["sku", "priority"]), "forecasts": pd.DataFrame(columns=["sku"]),
        "partner_items": [], "thresholds": {"excess_coverage_days": 90, "capacity_occupation_threshold": 0.9},
    }


def test_synthetic_cases_run_through_existing_rules_and_recommendation():
    config = load_validation_config(CONFIG)
    synthetic = {**config, "cases": [case for case in config["cases"] if case["origin"] == "synthetic"]}
    result = evaluate_frozen_cases(synthetic, **_empty_context(), source_sha256=config["frozen_source_sha256"])
    assert result["total"] == 2 and result["passed"] == 2
    first = result["items"][0]
    assert {"RUP_LEAD_TIME", "RUP_SAFETY_STOCK", "ORDER_WITHOUT_PRODUCTION"} <= set(first["obtained"]["signals"])
    assert first["obtained"]["suggested_quantity"] == 500.0


def test_failed_and_missing_cases_are_reported_not_hidden():
    config = load_validation_config(CONFIG)
    broken = copy.deepcopy(config)
    synthetic = next(case for case in broken["cases"] if case["id"] == "VC-01")
    synthetic["expected"]["action"] = "sem_acao_necessaria"
    base_case = next(case for case in broken["cases"] if case["id"] == "VC-02")
    broken["cases"] = [synthetic, base_case]
    result = evaluate_frozen_cases(broken, **_empty_context(), source_sha256="outro-hash")
    assert [item["result"] for item in result["items"]] == ["falhou", "nao_encontrado"]
    assert result["failed"] == 1 and result["not_found"] == 1
    assert result["source_matches_frozen"] is False and result["source_note"]
    failed_check = next(check for check in result["items"][0]["checks"] if check["field"] == "action")
    assert failed_check == {"field": "action", "expected": "sem_acao_necessaria", "obtained": "produzir", "passed": False}


def test_safe_behavior_guard_rails_pass_and_detect_violation():
    forecasts = pd.DataFrame([{"sku": "X", "status": "ok", "forecast_next_month": 1.0}])
    checks = {item["id"]: item for item in safe_behavior_checks(forecasts, [{"requires_human_review": True}], [])}
    assert all(item["status"] == "aprovado" for item in checks.values())
    violated = {item["id"]: item for item in safe_behavior_checks(forecasts, [{"requires_human_review": False}], [{"estimated_stock": None, "coverage_days": 10}])}
    assert violated["human_review"]["status"] == "reprovado"
    assert violated["no_false_precision"]["status"] == "reprovado"
