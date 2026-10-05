import sqlite3

from caderno_inteligente.run_comparison import SCHEMA_VERSION, build_comparison_payload, compare_runs
from caderno_inteligente.runs import create_run, get_run, list_runs


def _item(sku, priority, score, confidence="média", signals=(), evidence=None):
    return {
        "sku": sku, "product": f"Produto {sku}", "family": "F", "priority": priority, "attention_score": score,
        "confidence": confidence, "confidence_reason": f"motivo {confidence}",
        "reasons": [{"code": code, "description": code, "severity": "alta"} for code in signals],
        "evidence": [{"code": code, "values_used": (evidence or {}).get(code, {}), "data_origin": []} for code in signals],
    }


def _forecast_summary(sku, next_month, action, quantity):
    return {"sku": sku, "forecast": {"status": "ok", "model": "moving_average_3", "forecast_next_month": next_month, "forecast_total_3m": next_month * 3,
                                     "backtest_wape": 0.1, "forecast_confidence": "alta", "trend": "estável"},
            "operational_recommendation": {"action": action, "suggested_quantity": quantity, "capacity_status": "family_context_available", "confidence": "alta"}}


def _partners(coverage):
    return {"reference_month": "2026-08", "partners": [{"code": "KA-01", "name": "Parceiro", "coverage": coverage, "observed_skus": int(coverage * 10),
                                                       "total_catalog_skus": 10, "latest_sell_out_month": "2026-08", "action_counts": {}}]}


def _run(run_id, ranking, weights, comparison=None, source_hash="h1", created_at=None, thresholds=None):
    return {"id": run_id, "created_at": created_at or f"2026-10-0{run_id}T00:00:00+00:00", "source_hash": source_hash, "weights": weights,
            "thresholds": thresholds or {"excess_coverage_days": 90}, "quality": {}, "ranking": ranking, "comparison": comparison}


WEIGHTS = {"A": 10, "B": 5, "C": 2}


def test_score_change_is_decomposed_into_signals_and_weights():
    base = _run(1, [_item("X", 1, 15, signals=("A", "B")), _item("Y", 2, 5, signals=("B",))], WEIGHTS)
    target = _run(2, [_item("Y", 1, 12, signals=("B", "C")), _item("X", 2, 10, signals=("A",))], {**WEIGHTS, "B": 10, "C": 2})
    result = compare_runs(base, target)
    changed = {item["sku"]: item for item in result["ranking"]["changed"]}

    y = changed["Y"]
    assert y["position_delta"] == 1 and y["score_delta"] == 7
    assert y["signals_added"] == ["C"]
    assert {(e["code"], e["change"], e["delta"]) for e in y["score_breakdown"]} == {("C", "adicionado", 2), ("B", "peso alterado", 5)}
    assert y["score_delta_explained"] is True

    x = changed["X"]
    assert x["signals_removed"] == ["B"] and x["score_delta"] == -5 and x["score_delta_explained"]
    assert any("Sinal removido B" in line for line in x["explanation"])
    assert result["context"]["weights_changes"] == [{"key": "B", "base": 5, "target": 10}]
    assert result["ranking"]["summary"]["unexplained"] == 0


def test_entries_exits_confidence_and_evidence_changes():
    base = _run(1, [_item("X", 1, 10, signals=("A",), evidence={"A": {"coverage_days": 5}}), _item("OUT", 2, 2, signals=("C",))], WEIGHTS)
    target = _run(2, [_item("X", 1, 10, confidence="baixa", signals=("A",), evidence={"A": {"coverage_days": 3}}), _item("NEW", 2, 5, signals=("B",))], WEIGHTS)
    result = compare_runs(base, target)
    assert [item["sku"] for item in result["ranking"]["entered"]] == ["NEW"]
    assert [item["sku"] for item in result["ranking"]["exited"]] == ["OUT"]
    x = result["ranking"]["changed"][0]
    assert x["confidence_changed"] and any("Confiança mudou de média para baixa: motivo baixa" in line for line in x["explanation"])
    assert x["evidence_changes"] == [{"code": "A", "field": "coverage_days", "base": 5, "target": 3}]


def test_position_change_without_score_change_is_explained_by_other_skus():
    base = _run(1, [_item("X", 1, 5, signals=("B",))], WEIGHTS)
    target = _run(2, [_item("NEW", 1, 10, signals=("A",)), _item("X", 2, 5, signals=("B",))], WEIGHTS)
    x = compare_runs(base, target)["ranking"]["changed"][0]
    assert x["position_delta"] == -1 and x["score_delta"] == 0
    assert any("outros SKUs" in line for line in x["explanation"])


def test_unexplained_score_difference_is_flagged_not_hidden():
    base = _run(1, [_item("X", 1, 10, signals=("A",))], WEIGHTS)
    target = _run(2, [_item("X", 1, 12, signals=("A",))], WEIGHTS)
    result = compare_runs(base, target)
    assert result["ranking"]["changed"][0]["score_delta_explained"] is False
    assert result["ranking"]["summary"]["unexplained"] == 1


def test_legacy_snapshots_only_compare_ranking_and_explain_why():
    base = _run(1, [_item("X", 1, 10, signals=("A",))], WEIGHTS)
    payload = build_comparison_payload([_forecast_summary("X", 100, "produzir", 200)], _partners(0.5), {"recent_months": 3})
    target = _run(2, [_item("X", 1, 10, signals=("A",))], WEIGHTS, comparison=payload)
    result = compare_runs(base, target)
    assert result["comparable"] is True and result["ranking"]["available"]
    for section in ("forecasts", "b2b_coverage"):
        assert result[section]["available"] is False
        assert "Execução #1" in result[section]["reason"]
    assert result["context"]["commercial_thresholds"]["available"] is False


def test_incompatible_ranking_is_refused():
    result = compare_runs(_run(1, [{"sku": "X"}], WEIGHTS), _run(2, [_item("X", 1, 10, signals=("A",))], WEIGHTS))
    assert result["ranking"] == {"available": False, "reason": "Execução #1 não preserva os campos do ranking necessários: priority, attention_score, confidence, reasons."}
    assert result["comparable"] is False


def test_incompatible_schema_version_is_refused():
    payload = build_comparison_payload([_forecast_summary("X", 100, "produzir", 200)], _partners(0.5), {})
    future = {**payload, "schema_version": SCHEMA_VERSION + 1}
    result = compare_runs(_run(1, [], WEIGHTS, comparison=future), _run(2, [], WEIGHTS, comparison=payload))
    assert result["forecasts"]["available"] is False and "incompatível" in result["forecasts"]["reason"]


def test_forecast_recommendation_and_partner_coverage_changes():
    base = _run(1, [], WEIGHTS, comparison=build_comparison_payload(
        [_forecast_summary("X", 100, "produzir", 200), _forecast_summary("Y", 50, "sem_acao_necessaria", 0)], _partners(0.5), {"recent_months": 3}))
    target = _run(2, [], WEIGHTS, source_hash="h2", comparison=build_comparison_payload(
        [_forecast_summary("X", 120, "produzir", 300), _forecast_summary("Y", 50, "sem_acao_necessaria", 0)], _partners(0.7), {"recent_months": 4}))
    result = compare_runs(base, target)
    assert result["context"]["source_changed"] is True
    assert result["context"]["commercial_thresholds"]["changes"] == [{"key": "recent_months", "base": 3, "target": 4}]
    forecasts = result["forecasts"]
    assert forecasts["summary"]["changed_skus"] == 1 and forecasts["summary"]["quantity_changes"] == 1
    fields = {change["field"]: change for change in forecasts["items"][0]["changes"]}
    assert fields["forecast.forecast_next_month"]["delta"] == 20
    assert fields["recommendation.suggested_quantity"]["delta"] == 100
    partner = result["b2b_coverage"]["items"][0]
    assert partner["partner"] == "KA-01" and {c["field"] for c in partner["changes"]} == {"partner.coverage", "partner.observed_skus"}


def test_unavailable_partner_analysis_is_recorded_with_reason():
    payload = build_comparison_payload([], None, None, "Análise comercial indisponível no registro: erro")
    result = compare_runs(_run(1, [], WEIGHTS, comparison=payload), _run(2, [], WEIGHTS, comparison=payload))
    assert result["b2b_coverage"]["available"] is False
    assert "Motivo: Análise comercial indisponível" in result["b2b_coverage"]["reason"]


def test_reverse_order_is_noted():
    result = compare_runs(_run(2, [], WEIGHTS), _run(1, [], WEIGHTS))
    assert any("anterior à base" in note for note in result["notes"])


def test_sqlite_migrates_legacy_runs_table_additively(tmp_path):
    db = tmp_path / "runs.db"
    with sqlite3.connect(db) as connection:
        connection.execute("CREATE TABLE runs (id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, source_hash TEXT NOT NULL, weights TEXT NOT NULL, thresholds TEXT NOT NULL, quality TEXT NOT NULL, ranking TEXT NOT NULL)")
        connection.execute("INSERT INTO runs(created_at, source_hash, weights, thresholds, quality, ranking) VALUES ('2026-10-01', 'h', '{}', '{}', '{}', '[]')")
    source = tmp_path / "source.xlsm"
    source.write_bytes(b"base")
    new_id = create_run(db, source, {}, {}, {}, [], {"schema_version": 1})
    listed = {run["id"]: run for run in list_runs(db)}
    assert listed[1]["comparison_schema_version"] is None
    assert listed[new_id]["comparison_schema_version"] == 1
    assert get_run(db, 1)["comparison"] is None
    assert get_run(db, new_id)["comparison"] == {"schema_version": 1}
