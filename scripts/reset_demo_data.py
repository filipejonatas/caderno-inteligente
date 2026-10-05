"""Remove demonstration records (decisions, cases, case history and runs). The XLSM source is never touched.

Default is a dry run that only counts rows. Deleting requires --confirm and writes a JSON backup first.

    python scripts/reset_demo_data.py                 # SQLite local: conta registros
    python scripts/reset_demo_data.py --confirm       # SQLite local: backup + limpeza
    python scripts/reset_demo_data.py --postgres      # usa DATABASE_URL do ambiente (nunca impressa)
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "runtime"
SQLITE_TABLES = {"feedback": RUNTIME / "feedback.db", "cases": RUNTIME / "cases.db", "case_history": RUNTIME / "cases.db", "runs": RUNTIME / "runs.db"}
ORDER = ("case_history", "cases", "feedback", "runs")


def _json_default(value):
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def sqlite_rows(tables: dict[str, Path], selected: list[str]) -> dict[str, list[dict]]:
    result = {}
    for table in selected:
        path = tables[table]
        if not path.exists():
            result[table] = []
            continue
        with sqlite3.connect(path) as connection:
            connection.row_factory = sqlite3.Row
            exists = connection.execute("select 1 from sqlite_master where type='table' and name=?", (table,)).fetchone()
            result[table] = [dict(row) for row in connection.execute(f"select * from {table}")] if exists else []
    return result


def sqlite_delete(tables: dict[str, Path], selected: list[str]) -> None:
    for table in [name for name in ORDER if name in selected]:
        path = tables[table]
        if not path.exists():
            continue
        with sqlite3.connect(path) as connection:
            if connection.execute("select 1 from sqlite_master where type='table' and name=?", (table,)).fetchone():
                connection.execute(f"delete from {table}")


def postgres_connect():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL não está definida no ambiente; nada foi alterado.")
    import psycopg
    from psycopg.rows import dict_row

    return psycopg.connect(url, autocommit=False, prepare_threshold=None, row_factory=dict_row)


def postgres_rows(selected: list[str]) -> dict[str, list[dict]]:
    with postgres_connect() as connection, connection.cursor() as cursor:
        result = {}
        for table in selected:
            cursor.execute(f"select * from public.{table}")
            result[table] = cursor.fetchall()
        return result


def postgres_delete(selected: list[str]) -> None:
    tables = ", ".join(f"public.{name}" for name in ORDER if name in selected)
    with postgres_connect() as connection, connection.cursor() as cursor:
        cursor.execute(f"truncate table {tables} restart identity")


def main(argv: list[str] | None = None, *, sqlite_tables: dict[str, Path] | None = None, backup_dir: Path | None = None) -> int:
    parser = argparse.ArgumentParser(description="Limpa registros de demonstração sem alterar a planilha de origem.")
    parser.add_argument("--confirm", action="store_true", help="apaga de fato; sem esta opção apenas conta os registros")
    parser.add_argument("--postgres", action="store_true", help="usa o PostgreSQL/Supabase indicado por DATABASE_URL")
    parser.add_argument("--tables", default=",".join(ORDER), help="tabelas separadas por vírgula (padrão: todas)")
    parser.add_argument("--no-backup", action="store_true", help="não grava o backup JSON antes de apagar")
    args = parser.parse_args(argv)

    selected = [name.strip() for name in args.tables.split(",") if name.strip()]
    unknown = sorted(set(selected) - set(ORDER))
    if unknown or not selected:
        parser.error(f"tabelas inválidas: {', '.join(unknown) or '(nenhuma)'}; use {', '.join(ORDER)}")
    if "cases" in selected and "case_history" not in selected:
        parser.error("cases exige case_history, para não deixar histórico órfão")

    tables = sqlite_tables or SQLITE_TABLES
    target = "PostgreSQL (DATABASE_URL)" if args.postgres else "SQLite local"
    rows = postgres_rows(selected) if args.postgres else sqlite_rows(tables, selected)
    print(f"Destino: {target}")
    for table in selected:
        print(f"  {table}: {len(rows[table])} registro(s)")
    if not args.confirm:
        print("Simulação: nada foi apagado. Use --confirm para limpar.")
        return 0

    if not args.no_backup:
        folder = backup_dir or (RUNTIME / "backups")
        folder.mkdir(parents=True, exist_ok=True)
        backup = folder / f"demo-reset-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
        backup.write_text(json.dumps({"target": target, "tables": rows}, ensure_ascii=False, default=_json_default, indent=2), encoding="utf-8")
        print(f"Backup gravado em {backup}")
    postgres_delete(selected) if args.postgres else sqlite_delete(tables, selected)
    print("Registros de demonstração removidos. A planilha de origem não foi alterada.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
