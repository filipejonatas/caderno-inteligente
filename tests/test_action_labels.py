import json
import re
import sqlite3
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import backend.main as main
from caderno_inteligente.action_labels import (
    CHALLENGE_PDF_CODES, DEFAULT_SETTINGS, DEFINITIONS, LABELS, PRECEDENCE, label_channel_row, label_commercial_row, label_operational,
    label_partner, load_action_settings, recompra_signal,
)
from caderno_inteligente.feedback import init_feedback_db, list_feedback, list_feedback_records, save_feedback

ROOT = Path(__file__).resolve().parents[1]
S = dict(DEFAULT_SETTINGS)
REF = date(2026, 8, 31)


def _op(action, priority=None, status="ok", alerts=(), capacity="family_context_available"):
    return label_operational(action, priority, status, None if alerts is None else list(alerts), capacity, REF, S)


def _alert(decision, in_horizon=True, event_id="bf"):
    return {"event_id": event_id, "event": "Black Friday", "decision_date": decision, "in_horizon": in_horizon}


def _row(action="monitorar_estoque", **extra):
    base = {"partner": "KA", "sku": "A", "action": action, "data_quality": "sufficient", "coverage_days": 60, "average_monthly_sell_out": 50, "estimated_stock": 100,
            "reference_month": "2026-08", "signals": [], "periods": [{"month": f"2026-{m:02d}", "sell_in_quantity": 10} for m in range(1, 6)]}
    return {**base, **extra}


# --- configuração e vocabulário ----------------------------------------------

def test_shipped_settings_load_and_invalid_values_are_rejected(tmp_path):
    assert load_action_settings(ROOT / "config/challenge_actions.json") == DEFAULT_SETTINGS
    for bad in ({"x": 1}, {"priority_top_n": 0}, {"priority_top_n": 2.5}, {"recompra_min_sell_in_months": 1}, {"event_decision_window_days": -1}, {"partner_min_opportunities": True}):
        path = tmp_path / "bad.json"
        path.write_text(json.dumps(bad), encoding="utf-8")
        with pytest.raises(ValueError):
            load_action_settings(path)


def test_every_label_is_defined_and_the_nine_pdf_actions_exist():
    assert set(CHALLENGE_PDF_CODES) <= set(LABELS) and len(CHALLENGE_PDF_CODES) == 9
    assert set(DEFINITIONS) == set(LABELS) and all(PRECEDENCE.values())
    assert {LABELS[c] for c in CHALLENGE_PDF_CODES} == {"Produzir", "Repor", "Priorizar produção", "Priorizar parceiro", "Ampliar mix", "Recomendar recompra", "Monitorar", "Investigar", "Sem ação necessária"}


# --- SKU (operacional) -------------------------------------------------------

def test_operational_mapping_and_priority_rule():
    assert _op("investigar_dados", status="insufficient_data")["code"] == "investigar"
    assert _op("monitorar_excesso")["code"] == "monitorar" and _op("sem_acao_necessaria")["code"] == "sem_acao_necessaria"
    assert _op("produzir", priority=25, alerts=[])["code"] == "produzir"
    top = _op("produzir", priority=10, alerts=[])
    assert top["code"] == "priorizar_producao" and "priority_top_10" in top["signals_used"] and top["evidence"][0]["value"] == 10
    assert _op("produzir", priority=11, alerts=[])["code"] == "produzir"
    assert _op("produzir", priority=None, alerts=[])["code"] == "produzir"  # fora do ranking nunca vira prioridade


def test_event_decision_window_and_horizon_drive_priorizar_producao():
    inside = _op("produzir", priority=30, alerts=[_alert("2026-09-30")])
    assert inside["code"] == "priorizar_producao" and "event_decision:bf" in inside["signals_used"]
    assert _op("produzir", priority=30, alerts=[_alert("2026-10-01")])["code"] == "produzir"          # 31 dias: fora da janela
    assert _op("produzir", priority=30, alerts=[_alert("2026-09-10", in_horizon=False)])["code"] == "produzir"
    assert _op("produzir", priority=30, alerts=[{"event_id": "x", "event": "X", "decision_date": None, "in_horizon": True}])["code"] == "produzir"


def test_unavailable_event_analysis_is_declared_and_does_not_invent_urgency():
    result = _op("produzir", priority=30, alerts=None)
    assert result["code"] == "produzir" and any("indisponível" in text for text in result["limitations"])


def test_capacity_pressure_keeps_the_label_but_adds_the_warning_and_review_flag():
    result = _op("produzir_validar_capacidade", priority=2, alerts=[], capacity="requires_review")
    assert result["code"] == "priorizar_producao" and result["requires_human_review"] is True
    assert any("capacidade" in text.lower() for text in result["limitations"])
    assert result["origin_action"] == "produzir_validar_capacidade"


def test_insufficient_forecast_beats_everything_even_with_a_producing_action():
    assert _op("produzir", priority=1, status="insufficient_data", alerts=[_alert("2026-09-01")])["code"] == "investigar"


# --- parceiro–SKU (comercial) ------------------------------------------------

def test_dirty_or_divergent_data_is_investigar_and_never_an_opportunity():
    for action in ("solicitar_atualizacao", "dados_insuficientes", "investigar_divergencia"):
        result = label_commercial_row(_row(action, coverage_days=5, signals=[{"code": "REPOSITION_OPPORTUNITY"}]), S)
        assert result["code"] == "investigar" and result["origin_action"] == action and result["evidence"]
    assert label_commercial_row(_row("avaliar_reposicao", signals=[{"code": "REPOSITION_OPPORTUNITY"}], coverage_days=20), S)["code"] == "repor"


def test_recompra_needs_a_gap_longer_than_the_pairs_own_rhythm_and_positive_sell_out():
    assert label_commercial_row(_row(), S)["code"] == "recomendar_recompra"
    result = label_commercial_row(_row(), S)
    assert result["signals_used"] == ["RECOMPRA_GAP"] and {item["label"] for item in result["evidence"]} >= {"Último sell-in", "Meses sem sell-in"}
    assert recompra_signal(_row(), S)["last_sell_in_month"] == "2026-05" and recompra_signal(_row(), S)["months_without_sell_in"] == 3
    assert label_commercial_row(_row(periods=[{"month": f"2026-{m:02d}", "sell_in_quantity": 10} for m in range(1, 9)]), S)["code"] == "monitorar"   # enviado até agosto
    assert label_commercial_row(_row(average_monthly_sell_out=None), S)["code"] == "monitorar"
    assert label_commercial_row(_row(average_monthly_sell_out=0), S)["code"] == "monitorar"
    assert label_commercial_row(_row(periods=[{"month": "2026-01", "sell_in_quantity": 10}, {"month": "2026-02", "sell_in_quantity": 10}]), S)["code"] == "monitorar"  # pouca história
    quarterly = [{"month": m, "sell_in_quantity": 10} for m in ("2025-09", "2025-12", "2026-03")]
    assert label_commercial_row(_row(periods=quarterly), S)["code"] == "monitorar"  # ritmo trimestral: 5 meses < 2 × 3 = 6
    assert label_commercial_row(_row("avaliar_reposicao", signals=[{"code": "REPOSITION_OPPORTUNITY"}]), S)["code"] == "repor"  # reposição vence recompra


# --- parceiro ---------------------------------------------------------------

def _partner_rows(*skus):
    return [{**_row("avaliar_reposicao", sku=sku, signals=[{"code": "REPOSITION_OPPORTUNITY"}]), "challenge_action": {"code": "repor"}} for sku in skus]


def test_priorizar_parceiro_requires_several_reposicoes_with_a_top_priority_sku():
    summary = {"code": "KA", "name": "Parceiro"}
    ok = label_partner(summary, _partner_rows("A", "B"), {"A": 4, "B": 30}, S)
    assert ok["code"] == "priorizar_parceiro" and ok["evidence"][0]["value"] == 2 and ok["evidence"][1]["value"] == 4
    assert label_partner(summary, _partner_rows("A"), {"A": 1}, S) is None                    # só uma reposição
    assert label_partner(summary, _partner_rows("A", "B"), {"A": 15, "B": 30}, S) is None    # nenhuma no topo
    assert label_partner(summary, _partner_rows("A", "B"), {"A": None, "B": 30}, S) is None  # fora do ranking não conta
    rows = _partner_rows("A", "B") + [{**_row(sku="C"), "challenge_action": {"code": "investigar"}}]
    assert label_partner(summary, rows[:1] + rows[2:], {"A": 1, "C": 2}, S) is None           # dado ruim não conta como oportunidade


# --- canais diretos ----------------------------------------------------------

@pytest.mark.parametrize("suggestion,expected", [
    ("avaliar_ampliacao_mix", "ampliar_mix"), ("avaliar_reativacao", "reativar"), ("investigar_queda", "investigar"),
    ("monitorar_saida_de_linha", "monitorar"), ("acompanhar_crescimento", "monitorar"), ("sem_acao_necessaria", "sem_acao_necessaria"),
])
def test_channel_suggestions_map_to_challenge_labels(suggestion, expected):
    row = {"signals": ["X"], "revenue_24m": 1.0, "trend": "estável", "last_month": "2026-08-01", "suggestion": {"code": suggestion, "reason": "Motivo."}}
    result = label_channel_row(row)
    assert result["code"] == expected and result["origin_action"] == suggestion and result["reason"] == "Motivo."
    assert any("estoque por canal" in text.lower() for text in result["limitations"])


# --- casos congelados --------------------------------------------------------

def test_every_label_has_at_least_one_frozen_case():
    cases = json.loads((ROOT / "config/validation_center.json").read_text(encoding="utf-8"))["cases"]
    covered = {case["expected"]["code"] for case in cases if case["kind"] == "challenge_action"}
    assert covered == set(LABELS)


# --- API sobre a base real ---------------------------------------------------

@pytest.fixture(scope="module")
def client(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("labels")
    patch = pytest.MonkeyPatch()
    patch.setattr(main, "RUNS_DB", tmp / "runs.db")
    patch.setattr(main, "CASES_DB", tmp / "cases.db")
    patch.setattr(main, "FEEDBACK_DB", tmp / "feedback.db")
    patch.delenv("DATABASE_URL", raising=False)
    yield TestClient(main.app)
    patch.undo()


def test_api_forecasts_carry_the_label_without_changing_existing_fields(client):
    items = client.get("/api/forecasts").json()
    for item in items:
        label = item["challenge_action"]
        assert label["requires_human_review"] is True and label["code"] in LABELS and label["evidence"] is not None
        action = item["operational_recommendation"]["action"]
        if action == "investigar_dados":
            assert label["code"] == "investigar"
        elif action in ("produzir", "produzir_validar_capacidade"):
            assert label["code"] in ("produzir", "priorizar_producao")
            if item["priority"] is not None and item["priority"] <= 10:
                assert label["code"] == "priorizar_producao"
        elif action == "monitorar_excesso":
            assert label["code"] == "monitorar"
    assert {"sku", "product", "family", "priority", "attention_score", "confidence", "forecast", "operational_recommendation"} <= set(items[0])
    assert any(item["challenge_action"]["code"] == "priorizar_producao" for item in items)


def test_api_sku_detail_label_matches_the_list(client):
    listed = next(item for item in client.get("/api/forecasts").json() if item["sku"] == "CI-0049")
    detail = client.get("/api/priorities/CI-0049").json()
    assert detail["challenge_action"] == listed["challenge_action"] and detail["challenge_action"]["code"] == "priorizar_producao"


def test_api_commercial_rows_partners_and_filters(client):
    body = client.get("/api/commercial-recommendations?limit=500").json()
    assert body["challenge_labels"]["repor"] == "Repor"
    for row in body["items"]:
        label = row["challenge_action"]
        if row["action"] == "avaliar_reposicao":
            assert label["code"] == "repor"
        if row["action"] in ("dados_insuficientes", "solicitar_atualizacao", "investigar_divergencia"):
            assert label["code"] == "investigar"
    repor = client.get("/api/commercial-recommendations?challenge_action=repor&limit=500").json()
    assert repor["total"] == sum(1 for row in body["items"] if row["challenge_action"]["code"] == "repor") > 0
    partners = client.get("/api/partners").json()["items"]
    labeled = [p for p in partners if p["challenge_action"]]
    assert labeled and all(p["challenge_action"]["code"] == "priorizar_parceiro" and p["challenge_action"]["evidence"][0]["value"] >= 2 for p in labeled)
    only = client.get("/api/partners?challenge_action=priorizar_parceiro").json()["items"]
    assert {p["code"] for p in only} == {p["code"] for p in labeled}
    assert client.get("/api/partners?challenge_action=repor").json()["total"] > 0
    assert client.get("/api/partners/KA-01/skus?challenge_action=repor").json()["total"] > 0
    assert client.get("/api/commercial-recommendations?challenge_action=xyz").status_code == 422
    assert client.get("/api/partners?challenge_action=xyz").status_code == 422


def test_api_commercial_fields_other_than_the_label_are_unchanged(client):
    row = client.get("/api/commercial-recommendations?limit=1").json()["items"][0]
    assert {"action", "action_label", "signals", "recommendation_reason", "requires_human_review", "periods"} <= set(row)


def test_api_direct_channel_rows_carry_labels_and_filter(client):
    detail = client.get("/api/direct-channels/E-commerce").json()
    assert detail["challenge_labels"]["ampliar_mix"] == "Ampliar mix" and all(row["challenge_action"]["code"] in LABELS for row in detail["items"])
    assert {row["challenge_action"]["code"] for row in detail["items"]} <= {"ampliar_mix", "reativar", "investigar", "monitorar", "sem_acao_necessaria"}
    filtered = client.get("/api/direct-channels/E-commerce?challenge_action=investigar").json()
    assert 0 < filtered["total"] < 50 and all(row["challenge_action"]["code"] == "investigar" for row in filtered["items"])
    assert client.get("/api/direct-channels/E-commerce?challenge_action=xyz").status_code == 422


def test_api_validation_summary_runs_the_frozen_label_cases(client):
    body = client.get("/api/validation/summary").json()["frozen_cases"]
    challenge = [item for item in body["items"] if item["kind"] == "challenge_action"]
    assert len(challenge) == 11 and all(item["result"] == "passou" for item in challenge)
    assert {item["obtained"]["code"] for item in challenge} == set(LABELS)


# --- registro da decisão -----------------------------------------------------

def test_feedback_records_the_label_and_old_decisions_stay_null(client):
    assert client.post("/api/feedback", json={"sku": "CI-0049", "action": "aceita", "note": "ok"}).status_code == 200
    assert client.post("/api/feedback", json={"sku": "CI-0049", "action": "aceita", "note": "com rótulo", "challenge_action": "priorizar_producao"}).status_code == 200
    rows = client.get("/api/feedback").json()
    assert rows[0]["challenge_action"] == "priorizar_producao" and rows[1]["challenge_action"] is None
    assert client.post("/api/feedback", json={"sku": "CI-0049", "action": "aceita", "challenge_action": "inventado"}).status_code == 422


def test_sqlite_feedback_migrates_an_old_database_without_losing_rows(tmp_path):
    path = tmp_path / "old.db"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE feedback (id INTEGER PRIMARY KEY, sku TEXT NOT NULL, action TEXT NOT NULL, note TEXT, user_name TEXT, created_at TEXT NOT NULL, partner_data_effect TEXT NOT NULL DEFAULT 'nao_utilizado', analysis_minutes INTEGER)")
        conn.execute("INSERT INTO feedback(sku, action, note, user_name, created_at) VALUES('CI-1','aceita','n','u','2026-01-01T00:00:00+00:00')")
    init_feedback_db(path)
    save_feedback(path, "CI-2", "alterada", "n2", "u2", challenge_action="repor")
    records = list_feedback_records(path)
    assert [r["challenge_action"] for r in records] == ["repor", None] and [r["sku"] for r in records] == ["CI-2", "CI-1"]
    assert len(list_feedback(path)) == 2 and len(list_feedback(path)[0]) == 7   # formato histórico da tupla preservado
    with pytest.raises(ValueError):
        save_feedback(path, "CI-3", "aceita", "", "", challenge_action="xyz")


def test_postgres_migration_is_additive_and_documented():
    sql = (ROOT / "supabase/migrations/003_challenge_action.sql").read_text(encoding="utf-8").lower()
    assert "add column if not exists challenge_action text" in sql and "drop" not in sql and "not null" not in sql


def test_frontend_names_and_definitions_match_the_backend_vocabulary():
    """O frontend repete os textos (Guia, filtros); um texto diferente do backend seria uma segunda fonte de verdade."""
    source = (ROOT / "frontend/src/pages/shared.ts").read_text(encoding="utf-8")

    def block(name: str) -> dict[str, str]:
        body = source[source.index(f"export const {name}"):]
        body = body[body.index("{\n") + 1: body.index("\n};")]
        return dict(re.findall(r"(\w+): '([^']*)'", body))  # os textos não usam apóstrofo

    assert block("CHALLENGE_NAMES") == LABELS
    assert block("CHALLENGE_DEFINITIONS") == DEFINITIONS
