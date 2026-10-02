from __future__ import annotations

import hashlib
from datetime import date, datetime
from pathlib import Path
from typing import Any

from caderno_inteligente.cases import STATUSES
from caderno_inteligente.feedback import ACTIONS, PARTNER_DATA_EFFECTS


def _iso(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


class PostgresPersistence:
    """Persistência PostgreSQL compatível com o Transaction Pooler do Supabase."""

    kind = "postgres"

    def __init__(self, database_url: str):
        if not database_url:
            raise ValueError("DATABASE_URL não pode ser vazia")
        self._database_url = database_url

    def __repr__(self) -> str:
        return "PostgresPersistence(database_url=<redacted>)"

    def _connect(self):
        import psycopg
        from psycopg.rows import dict_row

        return psycopg.connect(
            self._database_url,
            autocommit=False,
            prepare_threshold=None,
            row_factory=dict_row,
        )

    def health(self) -> bool:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("select 1")
                return cursor.fetchone() is not None

    def create_case(self, **values: Any) -> int:
        status = values.get("status", "novo")
        if status not in STATUSES:
            raise ValueError("Status inválido")
        params = (values["sku"], values.get("run_id"), status, values.get("owner", ""), values.get("due_date", ""), values.get("action", ""), values.get("note", ""))
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "insert into cases(sku, run_id, status, owner, due_date, action, note) values (%s, %s, %s, %s, %s, %s, %s) returning id",
                    params,
                )
                case_id = int(cursor.fetchone()["id"])
                cursor.execute(
                    "insert into case_history(case_id, status, owner, due_date, action, note) values (%s, %s, %s, %s, %s, %s)",
                    (case_id, *params[2:]),
                )
                return case_id

    def list_cases(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("select id, sku, run_id, status, owner, due_date, action, note, created_at, updated_at from cases order by updated_at desc")
                return [{key: _iso(value) for key, value in row.items()} for row in cursor.fetchall()]

    def update_case(self, case_id: int, **values: Any) -> None:
        status = values.get("status")
        if status not in STATUSES:
            raise ValueError("Status inválido")
        params = (status, values.get("owner", ""), values.get("due_date", ""), values.get("action", ""), values.get("note", ""))
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("update cases set status=%s, owner=%s, due_date=%s, action=%s, note=%s, updated_at=now() where id=%s", (*params, case_id))
                cursor.execute("insert into case_history(case_id, status, owner, due_date, action, note) values (%s, %s, %s, %s, %s, %s)", (case_id, *params))

    def case_history(self, case_id: int) -> list[dict[str, Any]]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("select status, owner, due_date, action, note, changed_at from case_history where case_id=%s order by id desc", (case_id,))
                return [{key: _iso(value) for key, value in row.items()} for row in cursor.fetchall()]

    def save_feedback(self, sku: str, action: str, note: str, user_name: str, partner_data_effect: str = "nao_utilizado", analysis_minutes: int | None = None) -> None:
        if action not in ACTIONS:
            raise ValueError("Ação de feedback inválida")
        if partner_data_effect not in PARTNER_DATA_EFFECTS:
            raise ValueError("Efeito do dado do parceiro inválido")
        if analysis_minutes is not None and (isinstance(analysis_minutes, bool) or not isinstance(analysis_minutes, int) or analysis_minutes < 0):
            raise ValueError("Tempo de análise deve ser um número inteiro não negativo")
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "insert into feedback(sku, action, note, user_name, partner_data_effect, analysis_minutes) values (%s, %s, %s, %s, %s, %s)",
                    (sku, action, note, user_name, partner_data_effect, analysis_minutes),
                )

    def list_feedback(self) -> list[tuple]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("select sku, action, note, user_name, partner_data_effect, analysis_minutes, created_at from feedback order by id desc")
                return [(row["sku"], row["action"], row["note"], row["user_name"], row["partner_data_effect"], row["analysis_minutes"], _iso(row["created_at"])) for row in cursor.fetchall()]

    def feedback_summary(self) -> dict[str, int]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("select count(*) as total, count(*) filter (where partner_data_effect in (%s, %s)) as influenced from feedback", ("aumentou_confianca", "alterou_decisao"))
                row = cursor.fetchone()
                return {"decision_count": int(row["total"]), "partner_data_influenced_decision_count": int(row["influenced"])}

    def create_run(self, source: str | Path, weights: dict, thresholds: dict, quality: dict, ranking: list[dict]) -> int:
        from psycopg.types.json import Jsonb

        source_hash = hashlib.sha256(Path(source).read_bytes()).hexdigest()
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "insert into runs(source_hash, weights, thresholds, quality, ranking) values (%s, %s, %s, %s, %s) returning id",
                    (source_hash, Jsonb(weights), Jsonb(thresholds), Jsonb(quality), Jsonb(ranking)),
                )
                return int(cursor.fetchone()["id"])

    def list_runs(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("select id, created_at, source_hash, jsonb_array_length(ranking) as prioritized_skus from runs order by id desc")
                return [{key: _iso(value) for key, value in row.items()} for row in cursor.fetchall()]

    def get_run(self, run_id: int) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("select id, created_at, source_hash, weights, thresholds, quality, ranking from runs where id=%s", (run_id,))
                row = cursor.fetchone()
                return None if row is None else {key: _iso(value) for key, value in row.items()}
