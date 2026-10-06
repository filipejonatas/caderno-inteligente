from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from caderno_inteligente import cases as sqlite_cases
from caderno_inteligente import feedback as sqlite_feedback
from caderno_inteligente import runs as sqlite_runs


class Persistence(Protocol):
    kind: str

    def health(self) -> bool: ...
    def create_case(self, **values: Any) -> int: ...
    def list_cases(self) -> list[dict[str, Any]]: ...
    def update_case(self, case_id: int, **values: Any) -> None: ...
    def case_history(self, case_id: int) -> list[dict[str, Any]]: ...
    def save_feedback(self, sku: str, action: str, note: str, user_name: str, partner_data_effect: str = "nao_utilizado", analysis_minutes: int | None = None, challenge_action: str | None = None) -> None: ...
    def list_feedback(self) -> list[tuple]: ...
    def list_feedback_records(self) -> list[dict[str, Any]]: ...
    def feedback_summary(self) -> dict[str, int]: ...
    def create_run(self, source: str | Path, weights: dict, thresholds: dict, quality: dict, ranking: list[dict], comparison: dict | None = None) -> int: ...
    def list_runs(self) -> list[dict[str, Any]]: ...
    def get_run(self, run_id: int) -> dict[str, Any] | None: ...


class SqlitePersistence:
    kind = "sqlite"

    def __init__(self, cases_db: Path, feedback_db: Path, runs_db: Path):
        self.cases_db = cases_db
        self.feedback_db = feedback_db
        self.runs_db = runs_db
        for path in (self.cases_db, self.feedback_db, self.runs_db):
            path.parent.mkdir(parents=True, exist_ok=True)

    def health(self) -> bool:
        return True

    def create_case(self, **values: Any) -> int:
        return sqlite_cases.create_case(self.cases_db, **values)

    def list_cases(self) -> list[dict[str, Any]]:
        return sqlite_cases.list_cases(self.cases_db)

    def update_case(self, case_id: int, **values: Any) -> None:
        sqlite_cases.update_case(self.cases_db, case_id, **values)

    def case_history(self, case_id: int) -> list[dict[str, Any]]:
        return sqlite_cases.history(self.cases_db, case_id)

    def save_feedback(self, sku: str, action: str, note: str, user_name: str, partner_data_effect: str = "nao_utilizado", analysis_minutes: int | None = None, challenge_action: str | None = None) -> None:
        sqlite_feedback.save_feedback(self.feedback_db, sku, action, note, user_name, partner_data_effect, analysis_minutes, challenge_action)

    def list_feedback(self) -> list[tuple]:
        return sqlite_feedback.list_feedback(self.feedback_db)

    def list_feedback_records(self) -> list[dict[str, Any]]:
        return sqlite_feedback.list_feedback_records(self.feedback_db)

    def feedback_summary(self) -> dict[str, int]:
        return sqlite_feedback.feedback_summary(self.feedback_db)

    def create_run(self, source: str | Path, weights: dict, thresholds: dict, quality: dict, ranking: list[dict], comparison: dict | None = None) -> int:
        return sqlite_runs.create_run(self.runs_db, source, weights, thresholds, quality, ranking, comparison)

    def list_runs(self) -> list[dict[str, Any]]:
        return sqlite_runs.list_runs(self.runs_db)

    def get_run(self, run_id: int) -> dict[str, Any] | None:
        return sqlite_runs.get_run(self.runs_db, run_id)


def build_persistence(*, database_url: str | None, cases_db: Path, feedback_db: Path, runs_db: Path) -> Persistence:
    if database_url:
        from caderno_inteligente.postgres_persistence import PostgresPersistence

        return PostgresPersistence(database_url)
    return SqlitePersistence(cases_db, feedback_db, runs_db)
