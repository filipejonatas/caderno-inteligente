from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from caderno_inteligente.persistence import SqlitePersistence, build_persistence
from caderno_inteligente.postgres_persistence import PostgresPersistence


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def execute(self, query, params=None):
        self.connection.statements.append((" ".join(query.split()), params))
        if self.connection.fail_on == len(self.connection.statements):
            raise RuntimeError("simulated database failure")
        return self

    def fetchone(self):
        return self.connection.one_results.pop(0)

    def fetchall(self):
        result = self.connection.all_results.pop(0)
        return result


class FakeConnection:
    def __init__(self, *, one_results=None, all_results=None, fail_on=None):
        self.one_results = list(one_results or [])
        self.all_results = list(all_results or [])
        self.fail_on = fail_on
        self.statements = []
        self.committed = False
        self.rolled_back = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.committed = exc_type is None
        self.rolled_back = exc_type is not None
        return False

    def cursor(self):
        return FakeCursor(self)


class TestPostgresPersistence(PostgresPersistence):
    __test__ = False

    def __init__(self, connection):
        super().__init__("postgresql://user:secret@example.test:6543/postgres")
        self.connection = connection

    def _connect(self):
        return self.connection


def test_factory_uses_sqlite_without_database_url(tmp_path):
    persistence = build_persistence(
        database_url=None,
        cases_db=tmp_path / "cases.db",
        feedback_db=tmp_path / "feedback.db",
        runs_db=tmp_path / "runs.db",
    )

    assert isinstance(persistence, SqlitePersistence)
    assert persistence.kind == "sqlite"
    assert persistence.health()


def test_factory_uses_postgres_without_exposing_secret(tmp_path):
    persistence = build_persistence(
        database_url="postgresql://user:very-secret@example.test:6543/postgres",
        cases_db=tmp_path / "cases.db",
        feedback_db=tmp_path / "feedback.db",
        runs_db=tmp_path / "runs.db",
    )

    assert isinstance(persistence, PostgresPersistence)
    assert persistence.kind == "postgres"
    assert "very-secret" not in repr(persistence)


def test_postgres_connection_is_configured_for_transaction_pooler(monkeypatch):
    captured = {}

    def connect(url, **kwargs):
        captured.update(url=url, **kwargs)
        return object()

    monkeypatch.setitem(sys.modules, "psycopg", SimpleNamespace(connect=connect))
    monkeypatch.setitem(sys.modules, "psycopg.rows", SimpleNamespace(dict_row="dict-row"))
    persistence = PostgresPersistence("postgresql://user:secret@example.test:6543/postgres?sslmode=require")

    persistence._connect()

    assert captured["prepare_threshold"] is None
    assert captured["autocommit"] is False
    assert captured["row_factory"] == "dict-row"


def test_postgres_case_and_initial_history_share_a_transaction():
    connection = FakeConnection(one_results=[{"id": 7}])
    persistence = TestPostgresPersistence(connection)

    case_id = persistence.create_case(sku="CI-0001", owner="PCP")

    assert case_id == 7
    assert len(connection.statements) == 2
    assert connection.statements[0][0].startswith("insert into cases")
    assert connection.statements[1][0].startswith("insert into case_history")
    assert connection.committed
    assert not connection.rolled_back


def test_postgres_case_update_rolls_back_if_history_fails():
    connection = FakeConnection(fail_on=2)
    persistence = TestPostgresPersistence(connection)

    with pytest.raises(RuntimeError, match="simulated database failure"):
        persistence.update_case(
            7,
            status="em_investigacao",
            owner="PCP",
            due_date="2026-10-01",
            action="validar",
            note="teste",
        )

    assert connection.rolled_back
    assert not connection.committed


def test_postgres_feedback_preserves_api_tuple_contract():
    created_at = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)
    connection = FakeConnection(
        all_results=[[
            {
                "sku": "CI-0001",
                "action": "aceita",
                "note": "ok",
                "user_name": "PCP",
                "partner_data_effect": "confirmou",
                "analysis_minutes": 8,
                "created_at": created_at,
            }
        ]]
    )
    persistence = TestPostgresPersistence(connection)

    assert persistence.list_feedback() == [
        ("CI-0001", "aceita", "ok", "PCP", "confirmou", 8, created_at.isoformat())
    ]


def test_postgres_summary_keeps_existing_response_keys():
    connection = FakeConnection(one_results=[{"total": 4, "influenced": 2}])
    persistence = TestPostgresPersistence(connection)

    assert persistence.feedback_summary() == {
        "decision_count": 4,
        "partner_data_influenced_decision_count": 2,
    }


def test_supabase_migration_enables_rls_and_creates_all_tables():
    sql = Path("supabase/migrations/001_initial.sql").read_text(encoding="utf-8").lower()

    for table in ("runs", "cases", "case_history", "feedback"):
        assert f"create table if not exists public.{table}" in sql
        assert f"alter table public.{table} enable row level security" in sql
