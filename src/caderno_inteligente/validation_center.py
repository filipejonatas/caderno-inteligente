"""Week 4 validation evidence. Read-only: never changes weights, thresholds, models or the ranking."""
from __future__ import annotations

import json
import math
from datetime import date, datetime
from pathlib import Path
from statistics import median
from typing import Any, Iterable

import pandas as pd

from caderno_inteligente.forecasting import MODEL_LABELS, _MODELS, _monthly_series, _wape, build_demand_forecasts
from caderno_inteligente.recommendations import build_operational_recommendation
from caderno_inteligente.rules import evaluate_rules

HOLDOUT_MONTHS = 3
BASELINE_MODEL = "naive_last"
BASELINE_LABEL = "Ingênuo do último mês (baseline)"


def load_validation_config(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _safe(value: Any) -> Any:
    """Return JSON-safe values; absent stays null, never zero."""
    if isinstance(value, dict):
        return {key: _safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_safe(item) for item in value]
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return None if pd.isna(value) else value.date().isoformat() if isinstance(value, datetime) else value.isoformat()
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float) and math.isnan(value):
        return None
    if value is pd.NaT:
        return None
    return value


def _naive_last(history: pd.Series, targets: pd.PeriodIndex) -> list[float] | None:
    if history.empty:
        return None
    return [max(0.0, float(history.iloc[-1]))] * len(targets)


# ---------------------------------------------------------------- forecast

def _aggregate(rows: list[dict], key: str) -> dict[str, Any]:
    evaluated = [row for row in rows if row["errors"].get(key) is not None]
    defined = [row["wapes"][key] for row in evaluated if row["wapes"].get(key) is not None]
    actual = sum(row["holdout_actual_total"] for row in evaluated if row["holdout_actual_total"] > 0)
    errors = sum(row["errors"][key] for row in evaluated if row["holdout_actual_total"] > 0)
    return {
        "evaluated_skus": len(evaluated),
        "wape_defined_skus": len(defined),
        "median_wape": None if not defined else round(float(median(defined)), 4),
        "weighted_wape": None if actual <= 0 else round(errors / actual, 4),
    }


def evaluate_forecasts(sales: pd.DataFrame, forecasts: pd.DataFrame) -> dict[str, Any]:
    """Recompute the holdout of every candidate and an explicit baseline, without changing the selection."""
    by_sku = {str(row["sku"]): row for row in forecasts.to_dict("records")}
    models = {**_MODELS, BASELINE_MODEL: _naive_last}
    rows: list[dict] = []
    insufficient: list[str] = []
    for sku, forecast in sorted(by_sku.items()):
        if forecast.get("status") != "ok":
            insufficient.append(sku)
            continue
        series = _monthly_series(sales, sku)
        train, actual = series.iloc[:-HOLDOUT_MONTHS], series.iloc[-HOLDOUT_MONTHS:]
        wapes: dict[str, float | None] = {}
        errors: dict[str, float | None] = {}
        for model, function in models.items():
            predictions = function(train, actual.index)
            if predictions is None:
                wapes[model] = errors[model] = None
                continue
            errors[model] = float(sum(abs(float(a) - p) for a, p in zip(actual, predictions)))
            error = _wape(actual, predictions)
            wapes[model] = None if error is None else round(float(error), 4)
        selected = str(forecast["model"])
        selected_wape, baseline_wape = wapes.get(selected), wapes.get(BASELINE_MODEL)
        if selected_wape is None or baseline_wape is None:
            outcome = "nao_comparavel"
        elif selected_wape < baseline_wape:
            outcome = "superou"
        else:
            outcome = "nao_superou"
        rows.append({
            "sku": sku,
            "selected_model": selected,
            "selected_model_label": MODEL_LABELS.get(selected, selected),
            "selected_wape": selected_wape,
            "baseline_wape": baseline_wape,
            "candidate_wapes": {model: wapes[model] for model in _MODELS},
            "outcome": outcome,
            "holdout_actual_total": round(float(actual.sum()), 1),
            "wapes": wapes,
            "errors": {**errors, "selected": errors.get(selected)},
        })
    for row in rows:
        row["wapes"]["selected"] = row["selected_wape"]

    winners: dict[str, int] = {}
    for row in rows:
        winners[row["selected_model"]] = winners.get(row["selected_model"], 0) + 1
    model_rows = [
        {"model": model, "label": MODEL_LABELS[model], "role": "candidato", "selected_skus": winners.get(model, 0), **_aggregate(rows, model)}
        for model in _MODELS
    ]
    model_rows.append({"model": "selected", "label": "Modelo selecionado por SKU", "role": "selecionado", "selected_skus": len(rows), **_aggregate(rows, "selected")})
    model_rows.append({"model": BASELINE_MODEL, "label": BASELINE_LABEL, "role": "baseline", "selected_skus": 0, **_aggregate(rows, BASELINE_MODEL)})
    outcomes = {key: sum(row["outcome"] == key for row in rows) for key in ("superou", "nao_superou", "nao_comparavel")}
    return {
        "holdout_months": HOLDOUT_MONTHS,
        "total_skus": len(by_sku),
        "eligible_skus": len(rows),
        "insufficient_skus": len(insufficient),
        "insufficient_sku_list": insufficient,
        "zero_demand_holdout_skus": sum(row["holdout_actual_total"] <= 0 for row in rows),
        "baseline": {"model": BASELINE_MODEL, "label": BASELINE_LABEL, "description": "Repete o último mês observado antes do holdout. Serve apenas como referência; não participa da seleção."},
        "models": model_rows,
        "beat_baseline_skus": outcomes["superou"],
        "did_not_beat_baseline_skus": outcomes["nao_superou"],
        "not_comparable_skus": outcomes["nao_comparavel"],
        "items": [{key: value for key, value in row.items() if key not in ("wapes", "errors")} for row in rows],
        "limitations": [
            "O mesmo holdout escolhe o modelo e mede o erro; o WAPE do modelo selecionado tende a ser otimista.",
            "WAPE é calculado sobre faturamento mensal por SKU e não é diretamente comparável ao MAPE informado pela empresa.",
            "Com três meses de holdout por SKU, a amostra temporal é pequena; os resultados não garantem precisão futura.",
        ],
    }


# ------------------------------------------------------------ analysis time

def summarize_analysis_time(feedback_rows: Iterable[tuple], minimum_sample: int) -> dict[str, Any]:
    """Consolidate registered minutes without claiming a gain before the sample is sufficient."""
    rows = list(feedback_rows)
    minutes = [int(row[5]) for row in rows if row[5] is not None]
    sufficient = len(minutes) >= minimum_sample
    return {
        "feedback_count": len(rows),
        "records_with_minutes": len(minutes),
        "total_minutes": sum(minutes) if minutes else None,
        "average_minutes_per_decision": None if not minutes else round(sum(minutes) / len(minutes), 1),
        "median_minutes_per_decision": None if not minutes else float(median(minutes)),
        "minimum_sample": minimum_sample,
        "sample_status": "suficiente" if sufficient else "insuficiente",
        "comparison_allowed": sufficient,
        "note": (
            "Amostra atinge o mínimo definido, mas os minutos medem decisões registradas, não a jornada semanal completa do PCP."
            if sufficient else
            f"Somente {len(minutes)} registro(s) com tempo de análise; mínimo de {minimum_sample} para comparar com a linha de base. Nenhum ganho é afirmado."
        ),
    }


def process_comparison(config: dict[str, Any], forecast_evaluation: dict[str, Any], analysis_time: dict[str, Any]) -> list[dict[str, Any]]:
    """Keep informed, recalculated and target values in separate fields."""
    selected = next(row for row in forecast_evaluation["models"] if row["model"] == "selected")
    recalculated = {
        "analysis_time": {
            "value": None,
            "unit": "horas/semana",
            "comparable": False,
            "reason": analysis_time["note"],
        },
        "forecast_error": {
            "value": selected["weighted_wape"],
            "unit": "WAPE ponderado (holdout de 3 meses)",
            "comparable": False,
            "reason": "Erro do modelo estatístico do protótipo sobre faturamento. A empresa informa MAPE do forecast comercial; a base só traz forecast comercial para meses futuros, então esse erro não pode ser recalculado.",
        },
        "on_time_orders": {
            "value": None,
            "unit": "percentual",
            "comparable": False,
            "reason": "A base não traz histórico de entregas realizadas; não é possível recalcular.",
        },
        "plan_adherence": {
            "value": None,
            "unit": "percentual",
            "comparable": False,
            "reason": "A base não traz produção realizada contra planejada; não é possível recalcular.",
        },
    }
    return [{
        "id": item["id"],
        "label": item["label"],
        "informed": {"value": item["value"], "unit": item["unit"], "nature": "informado", "source": item["source"]},
        "recalculated": {**recalculated[item["id"]], "nature": "recalculado"},
        "target": None if item.get("target") is None else {"value": item["target"], "unit": item["target_unit"], "nature": "meta"},
    } for item in config["company_baseline"]]


# ------------------------------------------------------------ frozen cases

def _check(field: str, spec: Any, obtained: Any) -> dict[str, Any]:
    if isinstance(spec, dict) and ("includes" in spec or "excludes" in spec):
        values = set(obtained or [])
        missing = [code for code in spec.get("includes", []) if code not in values]
        unexpected = [code for code in spec.get("excludes", []) if code in values]
        parts = []
        if spec.get("includes"):
            parts.append("inclui " + ", ".join(spec["includes"]))
        if spec.get("excludes"):
            parts.append("não inclui " + ", ".join(spec["excludes"]))
        return {"field": field, "expected": "; ".join(parts), "obtained": sorted(values), "passed": not missing and not unexpected}
    if isinstance(spec, dict) and "max" in spec:
        return {"field": field, "expected": f"≤ {spec['max']}", "obtained": obtained, "passed": obtained is not None and obtained <= spec["max"]}
    if isinstance(spec, dict) and "not" in spec:
        return {"field": field, "expected": f"diferente de {spec['not']}", "obtained": obtained, "passed": obtained is not None and obtained != spec["not"]}
    if isinstance(spec, dict) and "positive" in spec:
        return {"field": field, "expected": "> 0", "obtained": obtained, "passed": obtained is not None and obtained > 0}
    if isinstance(spec, dict) and "equals" in spec:
        return {"field": field, "expected": f"= {spec['equals']}", "obtained": obtained, "passed": obtained is not None and obtained == spec["equals"]}
    if isinstance(spec, dict) and "is_null" in spec:
        return {"field": field, "expected": "nulo (não disponível)", "obtained": obtained, "passed": obtained is None}
    if isinstance(spec, dict) and "empty" in spec:
        return {"field": field, "expected": "vazio", "obtained": obtained, "passed": obtained is not None and len(obtained) == 0}
    return {"field": field, "expected": spec, "obtained": obtained, "passed": obtained == spec}


def _indicator_frame(values: dict[str, Any]) -> pd.DataFrame:
    frame = pd.DataFrame([values])
    for column in ("first_promised_date", "first_production_completion"):
        frame[column] = pd.to_datetime(frame[column])
    return frame


def _operational_output(indicator: dict[str, Any], forecast: dict[str, Any], codes: list[str], priority: int | None) -> dict[str, Any]:
    recommendation = build_operational_recommendation(indicator, forecast, codes)
    return {
        "signals": sorted(codes),
        "ranked": priority is not None,
        "priority": priority,
        "forecast_status": forecast.get("status"),
        "action": recommendation["action"],
        "suggested_quantity": recommendation["suggested_quantity"],
        "capacity_status": recommendation["capacity_status"],
        "confidence": recommendation["confidence"],
        "requires_human_review": recommendation["requires_human_review"],
    }


_OPERATIONAL_INPUT = (
    "current_stock", "coverage_days_calculated", "lead_time_days", "safety_stock_days", "backlog_order_quantity",
    "production_order_quantity", "first_promised_date", "first_production_completion", "capacity_occupation_average", "has_sell_out",
)
_COMMERCIAL_INPUT = (
    "sell_out_months", "missing_months", "estimated_stock", "average_monthly_sell_out", "coverage_days", "age_months", "backlog_quantity",
)


def _evaluate_case(case: dict, indicators: pd.DataFrame, issues: pd.DataFrame, ranking: pd.DataFrame,
                   forecasts: pd.DataFrame, partner_items: list[dict], thresholds: dict) -> dict[str, Any]:
    result = {key: case.get(key) for key in ("id", "title", "kind", "origin", "origin_reason", "sku", "partner", "limitation")}
    obtained: dict[str, Any] | None = None
    case_input: dict[str, Any] = {}
    if case["kind"] == "commercial":
        item = next((row for row in partner_items if row["partner"] == case["partner"] and row["sku"] == case["sku"]), None)
        if item is not None:
            case_input = {key: item.get(key) for key in _COMMERCIAL_INPUT}
            obtained = {
                "action": item["action"],
                "signals": sorted(signal["code"] for signal in item["signals"]),
                "data_quality": item["data_quality"],
                "missing_months": item["missing_months"],
                "estimated_stock": item["estimated_stock"],
                "coverage_days": item["coverage_days"],
                "requires_human_review": item["requires_human_review"],
            }
    elif case["origin"] == "synthetic":
        indicator = case["input"]["indicator"]
        codes = list(evaluate_rules(_indicator_frame(indicator), thresholds)["code"])
        if "sales" in case["input"]:
            sales = pd.DataFrame(case["input"]["sales"]).assign(SKU=indicator["SKU"])
            sales["Mês"] = pd.to_datetime(sales["Mês"])
            forecast = build_demand_forecasts(sales).to_dict("records")[0]
        else:
            forecast = case["input"]["forecast"]
        case_input = {**{key: indicator.get(key) for key in _OPERATIONAL_INPUT}, "forecast_status": forecast.get("status"), "forecast_next_month": forecast.get("forecast_next_month")}
        obtained = _operational_output(indicator, forecast, codes, None)
    else:
        row = indicators[indicators.SKU == case["sku"]]
        if not row.empty:
            indicator = {key: _safe(value) for key, value in row.iloc[0].to_dict().items()}
            forecast_rows = forecasts[forecasts.sku == case["sku"]].to_dict("records")
            forecast = forecast_rows[0] if forecast_rows else {"status": "insufficient_data", "forecast_next_month": None}
            codes = list(issues.loc[issues.sku == case["sku"], "code"])
            ranked = ranking[ranking.sku == case["sku"]]
            priority = None if ranked.empty else int(ranked["priority"].iloc[0])
            case_input = {**{key: indicator.get(key) for key in _OPERATIONAL_INPUT}, "forecast_status": forecast.get("status"), "forecast_next_month": forecast.get("forecast_next_month")}
            obtained = _operational_output(indicator, forecast, codes, priority)

    if obtained is None:
        return {**result, "input": None, "expected": case["expected"], "obtained": None, "checks": [], "result": "nao_encontrado",
                "adjustment": "Nenhum ajuste realizado. O caso não foi encontrado na base atual e precisa ser revisado."}
    checks = [_check(field, spec, obtained.get(field)) for field, spec in case["expected"].items()]
    return {
        **result,
        "input": _safe(case_input),
        "expected": case["expected"],
        "obtained": _safe(obtained),
        "checks": _safe(checks),
        "result": "passou" if all(check["passed"] for check in checks) else "falhou",
        "adjustment": "Nenhum ajuste de pesos, limiares ou modelos foi feito a partir deste caso.",
    }


def evaluate_frozen_cases(config: dict[str, Any], *, indicators: pd.DataFrame, issues: pd.DataFrame, ranking: pd.DataFrame,
                          forecasts: pd.DataFrame, partner_items: list[dict], thresholds: dict, source_sha256: str) -> dict[str, Any]:
    items = [_evaluate_case(case, indicators, issues, ranking, forecasts, partner_items, thresholds) for case in config["cases"]]
    counts = {key: sum(item["result"] == key for item in items) for key in ("passou", "falhou", "nao_encontrado")}
    matches = source_sha256 == config["frozen_source_sha256"]
    return {
        "frozen_at": config["frozen_at"],
        "frozen_source_sha256": config["frozen_source_sha256"],
        "source_matches_frozen": matches,
        "source_note": None if matches else "A planilha mudou desde o congelamento; os casos baseados na base precisam ser revisados antes de servir como evidência.",
        "policy": config["policy"],
        "total": len(items),
        "passed": counts["passou"],
        "failed": counts["falhou"],
        "not_found": counts["nao_encontrado"],
        "synthetic": sum(item["origin"] == "synthetic" for item in items),
        "items": items,
    }


# ------------------------------------------------------------ safe behavior

def _base_indicator() -> dict[str, Any]:
    return {"minimum_lot": 100, "average_sales_per_day": 10, "safety_stock_days": 10, "current_stock": 100,
            "production_order_quantity": 0, "backlog_order_quantity": 0, "has_sell_out": True}


def safe_behavior_checks(forecasts: pd.DataFrame, recommendations: list[dict], partner_items: list[dict]) -> list[dict[str, Any]]:
    """Execute the guard rails with controlled inputs; results are reported, never hidden."""
    checks: list[dict[str, Any]] = []

    def add(check_id: str, label: str, passed: bool, evidence: str, method: str = "executado") -> None:
        checks.append({"id": check_id, "label": label, "status": "aprovado" if passed else "reprovado", "method": method, "evidence": evidence})

    ok_forecast = {"status": "ok", "forecast_next_month": 400, "forecast_confidence": "alta"}
    without_sell_out = build_operational_recommendation({**_base_indicator(), "has_sell_out": False}, ok_forecast, [])
    add("missing_sell_out", "Ausência de sell-out reduz a confiança", without_sell_out["confidence"] == "baixa",
        f"Previsão com confiança alta e sem sell-out resultou em confiança {without_sell_out['confidence']}.")

    zero_holdout = _wape(pd.Series([0.0, 0.0, 0.0]), [10.0, 10.0, 10.0])
    add("zero_holdout", "Holdout com demanda zero não gera erro artificial", zero_holdout is None,
        "WAPE retornado como não calculado quando a demanda real do holdout soma zero." if zero_holdout is None else f"WAPE retornou {zero_holdout}.")

    short = pd.DataFrame({"Mês": pd.date_range("2026-05-01", periods=4, freq="MS"), "SKU": "SAFE-01", "Quantidade faturada": [10, 12, 11, 13]})
    short_forecast = build_demand_forecasts(short).to_dict("records")[0]
    short_recommendation = build_operational_recommendation(_base_indicator(), short_forecast, [])
    add("insufficient_forecast", "Forecast insuficiente não vira quantidade",
        short_forecast["status"] == "insufficient_data" and short_recommendation["suggested_quantity"] is None and short_recommendation["action"] == "investigar_dados",
        f"Status {short_forecast['status']}, ação {short_recommendation['action']}, quantidade {short_recommendation['suggested_quantity']}.")

    plain = build_operational_recommendation(_base_indicator(), ok_forecast, [])
    pressured = build_operational_recommendation(_base_indicator(), ok_forecast, ["CAPACITY_CONFLICT"])
    add("aggregated_capacity", "Capacidade agregada exige revisão e não é tratada como garantia",
        pressured["capacity_status"] == "requires_review" and pressured["action"] == "produzir_validar_capacidade" and pressured["confidence"] != "alta",
        f"Com pressão familiar: ação {pressured['action']}, confiança {pressured['confidence']} (sem pressão: {plain['confidence']}).")

    review = [item for item in recommendations if not item.get("requires_human_review")]
    add("human_review", "Toda recomendação operacional exige revisão humana", not review,
        f"{len(recommendations)} recomendação(ões) da base verificadas; {len(review)} sem revisão obrigatória.")

    insufficient = forecasts[forecasts.status != "ok"]
    zeros = int(insufficient["forecast_next_month"].notna().sum()) if not insufficient.empty else 0
    invented = [item for item in partner_items if item["estimated_stock"] is None and item["coverage_days"] is not None]
    add("no_false_precision", "Dado ausente não é convertido em zero ou cobertura inventada", zeros == 0 and not invented,
        f"{len(insufficient)} previsão(ões) insuficiente(s) com valor: {zeros}; {len(invented)} par(es) com cobertura sem estoque estimado.")
    return checks
