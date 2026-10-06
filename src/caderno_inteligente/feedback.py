from __future__ import annotations
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .action_labels import LABELS as CHALLENGE_LABELS

ACTIONS = ("aceita", "alterada", "rejeitada", "investigar")
PARTNER_DATA_EFFECTS = ("nao_utilizado", "confirmou", "aumentou_confianca", "alterou_decisao")


def _columns(conn: sqlite3.Connection) -> set[str]:
    return {row[1] for row in conn.execute("PRAGMA table_info(feedback)")}

def init_feedback_db(path: str | Path) -> None:
    with sqlite3.connect(path) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS feedback ("
            "id INTEGER PRIMARY KEY, sku TEXT NOT NULL, action TEXT NOT NULL, "
            "note TEXT, user_name TEXT, created_at TEXT NOT NULL, "
            "partner_data_effect TEXT NOT NULL DEFAULT 'nao_utilizado', "
            "analysis_minutes INTEGER)"
        )
        columns = _columns(conn)
        if "partner_data_effect" not in columns:
            conn.execute(
                "ALTER TABLE feedback ADD COLUMN partner_data_effect "
                "TEXT NOT NULL DEFAULT 'nao_utilizado'"
            )
        if "analysis_minutes" not in columns:
            conn.execute("ALTER TABLE feedback ADD COLUMN analysis_minutes INTEGER")
        if "challenge_action" not in columns:
            conn.execute("ALTER TABLE feedback ADD COLUMN challenge_action TEXT")

def save_feedback(
    path: str | Path,
    sku: str,
    action: str,
    note: str,
    user_name: str,
    partner_data_effect: str = "nao_utilizado",
    analysis_minutes: int | None = None,
    challenge_action: str | None = None,
) -> None:
    if action not in ACTIONS:
        raise ValueError("Ação de feedback inválida")
    if partner_data_effect not in PARTNER_DATA_EFFECTS:
        raise ValueError("Efeito do dado do parceiro inválido")
    if analysis_minutes is not None and (
        isinstance(analysis_minutes, bool)
        or not isinstance(analysis_minutes, int)
        or analysis_minutes < 0
    ):
        raise ValueError("Tempo de análise deve ser um número inteiro não negativo")
    if challenge_action is not None and challenge_action not in CHALLENGE_LABELS:
        raise ValueError("Rótulo de ação do desafio inválido")
    init_feedback_db(path)
    with sqlite3.connect(path) as conn:
        conn.execute(
            "INSERT INTO feedback("
            "sku, action, note, user_name, created_at, partner_data_effect, analysis_minutes, challenge_action"
            ") VALUES(?,?,?,?,?,?,?,?)",
            (
                sku,
                action,
                note,
                user_name,
                datetime.now(timezone.utc).isoformat(),
                partner_data_effect,
                analysis_minutes,
                challenge_action,
            ),
        )

def list_feedback(path: str | Path):
    init_feedback_db(path)
    with sqlite3.connect(path) as conn:
        return conn.execute(
            "SELECT sku, action, note, user_name, partner_data_effect, "
            "analysis_minutes, created_at FROM feedback ORDER BY id DESC"
        ).fetchall()


def list_feedback_records(path: str | Path) -> list[dict]:
    """Mesmas linhas de list_feedback, com o rótulo do desafio registrado (nulo em decisões anteriores)."""
    init_feedback_db(path)
    with sqlite3.connect(path) as conn:
        rows = conn.execute(
            "SELECT sku, action, note, user_name, partner_data_effect, analysis_minutes, created_at, challenge_action "
            "FROM feedback ORDER BY id DESC"
        ).fetchall()
    keys = ("sku", "action", "note", "user_name", "partner_data_effect", "analysis_minutes", "created_at", "challenge_action")
    return [dict(zip(keys, row)) for row in rows]


def feedback_summary(path: str | Path) -> dict[str, int]:
    init_feedback_db(path)
    with sqlite3.connect(path) as conn:
        total = conn.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
        influenced = conn.execute(
            "SELECT COUNT(*) FROM feedback WHERE partner_data_effect IN (?, ?)",
            ("aumentou_confianca", "alterou_decisao"),
        ).fetchone()[0]
    return {
        "decision_count": int(total),
        "partner_data_influenced_decision_count": int(influenced),
    }
