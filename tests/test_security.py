import io
import json
import logging
import sqlite3
from dataclasses import replace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.main as main
from backend.security import (
    MAX_BODY_BYTES,
    WRITE_DISABLED_MESSAGE,
    RedactingFilter,
    install_error_handling,
    load_settings,
    public_message,
    redact,
)
from scripts.reset_demo_data import main as reset_demo_data

SECRET_URL = "postgresql://postgres.ref:super-secret@aws-0.pooler.supabase.com:6543/postgres?sslmode=require"


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Isolated databases: no test writes to runtime/*.db."""
    monkeypatch.setattr(main, "RUNS_DB", tmp_path / "runs.db")
    monkeypatch.setattr(main, "CASES_DB", tmp_path / "cases.db")
    monkeypatch.setattr(main, "FEEDBACK_DB", tmp_path / "feedback.db")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    return TestClient(main.app)


def _settings(monkeypatch, **changes):
    monkeypatch.setattr(main, "SETTINGS", replace(main.SETTINGS, **changes))


# ----------------------------------------------------------------- settings

def test_defaults_preserve_local_behaviour(monkeypatch):
    for name in ("APP_ENV", "DEMO_MODE", "WRITE_ENABLED", "CORS_ORIGINS"):
        monkeypatch.delenv(name, raising=False)
    settings = load_settings()
    assert (settings.environment, settings.demo_mode, settings.write_enabled) == ("development", False, True)
    assert settings.cors_origins == ("http://localhost:5173", "http://127.0.0.1:5173")


def test_production_without_origins_allows_none_and_unknown_env_fails_closed(monkeypatch):
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    monkeypatch.setenv("APP_ENV", "production")
    assert load_settings().cors_origins == ()
    monkeypatch.setenv("APP_ENV", "staging-typo")
    assert load_settings().production is True


def test_cors_origins_are_validated(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://app.example.com/, *, https://a.example.com/path, ftp://x.example.com, https://u:p@b.example.com, https://ok.example.com:8443")
    settings = load_settings()
    assert settings.cors_origins == ("https://app.example.com", "https://ok.example.com:8443")
    assert len(settings.rejected_origins) == 4


@pytest.mark.parametrize("value, expected", [("true", True), ("SIM", True), ("0", False), ("off", False), ("talvez", False)])
def test_demo_flag_parsing(monkeypatch, value, expected):
    monkeypatch.setenv("DEMO_MODE", value)
    assert load_settings().demo_mode is expected


# -------------------------------------------------------------- redaction

def test_redact_removes_database_url_connection_strings_and_passwords(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", SECRET_URL)
    text = redact(f"falha: {SECRET_URL} | outra postgres://x:y@h/db | password=abc123")
    assert "super-secret" not in text and "x:y@h" not in text and "abc123" not in text
    assert "<DATABASE_URL redigida>" in text


def test_log_filter_redacts_messages_and_tracebacks(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", SECRET_URL)
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.addFilter(RedactingFilter())
    log = logging.getLogger("test.redaction")
    log.addHandler(handler)
    log.propagate = False
    try:
        raise RuntimeError(f"connection failed for {SECRET_URL}")
    except RuntimeError:
        log.error("db_error url=%s", SECRET_URL, exc_info=True)
    finally:
        log.removeHandler(handler)
    output = stream.getvalue()
    assert "super-secret" not in output and "pooler.supabase.com" not in output
    assert "RuntimeError" in output


def test_installed_root_handlers_redact(monkeypatch):
    assert any(isinstance(item, RedactingFilter) for handler in logging.getLogger().handlers for item in handler.filters)


# ------------------------------------------------------------- write access

def test_read_only_mode_blocks_every_write_and_keeps_reads(client, monkeypatch):
    _settings(monkeypatch, write_enabled=False)
    writes = [
        client.post("/api/feedback", json={"sku": "CI-0001", "action": "aceita"}),
        client.post("/api/cases", json={"sku": "CI-0001"}),
        client.put("/api/cases/1", json={"sku": "CI-0001"}),
        client.post("/api/runs"),
    ]
    for response in writes:
        assert response.status_code == 403
        assert response.json() == {"detail": WRITE_DISABLED_MESSAGE}
    assert client.get("/api/feedback").json() == [] and client.get("/api/cases").json() == [] and client.get("/api/runs").json() == []
    assert client.get("/api/overview").status_code == 200
    assert client.post("/api/scenarios", json={"weights": {"EXCESS_COVERAGE": 4}}).status_code == 200
    assert client.get("/api/system").json()["write_enabled"] is False


def test_system_reports_demo_mode_without_secrets(client, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", SECRET_URL)
    _settings(monkeypatch, demo_mode=True)
    body = client.get("/api/system").json()
    assert body["demo_mode"] is True and body["notice"]
    assert "super-secret" not in json.dumps(body) and "pooler" not in json.dumps(body)


# ------------------------------------------------------------ validation

def test_valid_writes_still_work(client):
    assert client.post("/api/feedback", json={"sku": "CI-0001", "action": "aceita", "note": "linha 1\nlinha 2", "analysis_minutes": 15}).status_code == 200
    case_id = client.post("/api/cases", json={"sku": "CI-0001", "owner": " PCP ", "due_date": "2026-10-10"}).json()["id"]
    assert client.get("/api/cases").json()[0]["owner"] == "PCP"
    assert client.put(f"/api/cases/{case_id}", json={"sku": "CI-0001", "status": "concluido"}).status_code == 200


@pytest.mark.parametrize("payload, fragment", [
    ({"sku": "NAO-EXISTE", "action": "aceita"}, "SKU não encontrado"),
    ({"sku": "CI-0001", "action": "aceita", "note": "x" * 2001}, "at most 2000"),
    ({"sku": "CI-0001", "action": "aceita", "user_name": "y" * 81}, "at most 80"),
    ({"sku": "CI-0001", "action": "aceita", "note": "abc\x00def"}, "caracteres de controle"),
    ({"sku": "CI-0001", "action": "aceita", "analysis_minutes": 1441}, "less than or equal to 1440"),
    ({"sku": "CI-0001", "action": "aceita", "analysis_minutes": -1}, "greater than or equal to 0"),
    ({"sku": "CI-0001", "action": "aceita", "admin": True}, "Extra inputs"),
    ({"sku": "CI-0001", "action": "apagar_tudo"}, "Ação de feedback inválida"),
])
def test_feedback_validation(client, payload, fragment):
    response = client.post("/api/feedback", json=payload)
    assert response.status_code == 422
    assert fragment in json.dumps(response.json(), ensure_ascii=False)
    assert client.get("/api/feedback").json() == []


@pytest.mark.parametrize("payload", [
    {"sku": "CI-0001", "due_date": "10/10/2026"},
    {"sku": "CI-0001", "due_date": "2026-02-30"},
    {"sku": "CI-0001", "owner": "z" * 81},
    {"sku": "CI-0001", "run_id": 0},
    {"sku": "CI-0001", "status": "apagado"},
])
def test_case_validation(client, payload):
    assert client.post("/api/cases", json=payload).status_code == 422
    assert client.get("/api/cases").json() == []


def test_updating_missing_case_returns_404_without_orphan_history(client):
    assert client.put("/api/cases/999", json={"sku": "CI-0001"}).status_code == 404
    assert client.get("/api/cases/999/history").json() == []


@pytest.mark.parametrize("payload", [
    {"weights": {"NAO_EXISTE": 1}}, {"weights": {"EXCESS_COVERAGE": 101}}, {"thresholds": {"excess_coverage_days": 0}},
    {"thresholds": {"desconhecido": 1}},
])
def test_scenario_validation(client, payload):
    assert client.post("/api/scenarios", json=payload).status_code == 422


def test_search_length_is_limited(client):
    assert client.get("/api/priorities", params={"search": "x" * 101}).status_code == 422


def test_oversized_body_is_rejected(client):
    response = client.post("/api/feedback", content=b"x" * (MAX_BODY_BYTES + 1), headers={"content-type": "application/json"})
    assert response.status_code == 413


# ---------------------------------------------------- CORS and headers

def test_cors_allows_only_configured_origins_and_methods(client):
    evil = client.options("/api/overview", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in evil.headers
    ok = client.options("/api/feedback", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type"})
    assert ok.headers["access-control-allow-origin"] == "http://localhost:5173"
    delete = client.options("/api/feedback", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "DELETE"})
    assert delete.status_code == 400
    assert "access-control-allow-credentials" not in ok.headers


def test_security_headers_and_request_id(client):
    response = client.get("/api/overview")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert len(response.headers["x-request-id"]) == 12


# ------------------------------------------------------- error disclosure

def _failing_app(settings):
    app = FastAPI()
    install_error_handling(app, lambda: settings)

    @app.get("/boom")
    def boom():
        raise RuntimeError(f"psycopg falhou em {SECRET_URL} /srv/app/backend/main.py")

    @app.get("/typed")
    def typed(limit: int):
        return {"limit": limit}

    return TestClient(app)


def test_production_errors_are_generic_and_traceable(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    client = _failing_app(load_settings())
    response = client.get("/boom")
    assert response.status_code == 500
    detail = response.json()["detail"]
    assert detail == f"Erro interno. Código de referência: {response.headers['x-request-id']}."
    invalid = client.get("/typed", params={"limit": "abc"}).json()["detail"][0]
    assert set(invalid) == {"type", "loc", "msg"}


def test_development_errors_show_cause_but_never_the_secret(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DATABASE_URL", SECRET_URL)
    detail = _failing_app(load_settings()).get("/boom").json()["detail"]
    assert "RuntimeError" in detail and "super-secret" not in detail and "pooler" not in detail


def test_public_message_hides_cause_in_production(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    assert public_message(load_settings(), "Configuração inválida", ValueError("C:/srv/config.json")) == "Configuração inválida"
    monkeypatch.setenv("APP_ENV", "development")
    assert "config.json" in public_message(load_settings(), "Configuração inválida", ValueError("C:/srv/config.json"))


# ------------------------------------------------------ demo data reset

def _seed(tmp_path):
    feedback, cases, runs = tmp_path / "feedback.db", tmp_path / "cases.db", tmp_path / "runs.db"
    for path, statements in {
        feedback: ["create table feedback (id integer primary key, sku text)", "insert into feedback(sku) values ('CI-0001')"],
        cases: ["create table cases (id integer primary key, sku text)", "create table case_history (id integer primary key, case_id integer)",
                "insert into cases(sku) values ('CI-0001')", "insert into case_history(case_id) values (1)"],
        runs: ["create table runs (id integer primary key, source_hash text)", "insert into runs(source_hash) values ('h')"],
    }.items():
        with sqlite3.connect(path) as connection:
            for statement in statements:
                connection.execute(statement)
    return {"feedback": feedback, "cases": cases, "case_history": cases, "runs": runs}


def _count(path, table):
    with sqlite3.connect(path) as connection:
        return connection.execute(f"select count(*) from {table}").fetchone()[0]


def test_reset_is_a_dry_run_by_default(tmp_path, capsys):
    tables = _seed(tmp_path)
    assert reset_demo_data([], sqlite_tables=tables, backup_dir=tmp_path / "backups") == 0
    assert "Simulação" in capsys.readouterr().out
    assert all(_count(path, table) == 1 for table, path in tables.items())
    assert not (tmp_path / "backups").exists()


def test_reset_with_confirm_backs_up_then_deletes(tmp_path):
    tables = _seed(tmp_path)
    reset_demo_data(["--confirm"], sqlite_tables=tables, backup_dir=tmp_path / "backups")
    assert all(_count(path, table) == 0 for table, path in tables.items())
    backup = json.loads(next((tmp_path / "backups").glob("demo-reset-*.json")).read_text(encoding="utf-8"))
    assert backup["tables"]["feedback"] == [{"id": 1, "sku": "CI-0001"}]


def test_reset_refuses_partial_case_deletion(tmp_path):
    with pytest.raises(SystemExit):
        reset_demo_data(["--tables", "cases", "--confirm"], sqlite_tables=_seed(tmp_path), backup_dir=tmp_path / "b")


def test_reset_postgres_requires_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(SystemExit, match="DATABASE_URL não está definida"):
        reset_demo_data(["--postgres"])
