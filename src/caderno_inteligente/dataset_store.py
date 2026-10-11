"""Planilha no banco (fase 3): uma tabela por aba, cadastro de SKU com exclusão lógica e versão dos dados.

O banco devolve os mesmos DataFrames que `ingestion.load_workbook` lê da planilha (mesmas colunas, ordem e tipos),
então cálculos, ranking e previsão não mudam. PostgreSQL em produção (migração 004); SQLite local em `runtime/`.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import math
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import numpy as np
import pandas as pd

from .ingestion import OPTIONAL_SHEETS
from .schemas import SCHEMAS

SHEET_TABLES: dict[str, str] = {
    "Produtos": "sheet_produtos",
    "Vendas_24m": "sheet_vendas_24m",
    "Estoque_Atual": "sheet_estoque_atual",
    "Carteira_Pedidos": "sheet_carteira_pedidos",
    "Ordens_Producao": "sheet_ordens_producao",
    "Capacidade_Semanal": "sheet_capacidade_semanal",
    "Sell_In": "sheet_sell_in",
    "Sell_Out": "sheet_sell_out",
    "Forecast_Comercial": "sheet_forecast_comercial",
    "Calendario_Eventos": "sheet_calendario_eventos",
    "Parceiros_Canais": "sheet_parceiros_canais",
    "Lead_Times": "sheet_lead_times",
    "Precos_Produtos": "sheet_precos_produtos",
}
assert set(SHEET_TABLES) == {*SCHEMAS, *OPTIONAL_SHEETS}

# Abas que o cadastro de SKU mantém: as que o pipeline cruza um a um com Produtos.
SKU_SHEETS = ("Produtos", "Estoque_Atual", "Lead_Times")


class DatasetStoreError(RuntimeError):
    pass


class SkuConflict(DatasetStoreError):
    pass


class SkuNotFound(DatasetStoreError):
    pass


class DatasetVersionConflict(DatasetStoreError):
    pass


class DatasetVersionNotFound(DatasetStoreError):
    pass


# Versões da base (D7): as 20 últimas, cada uma com o snapshot gzip do conjunto completo.
MAX_VERSIONS = 20
VERSION_ACTIONS = ("upload", "restore", "original")
MIGRATION_005_MISSING = ("O banco PostgreSQL não tem a tabela dataset_versions ou a coluna dataset_version.active_version_id: "
                         "rode a migração 005 (supabase/migrations/005_dataset_uploads.sql).")
_VERSION_COLUMNS = ("id", "created_at", "user_email", "action", "filename", "file_sha256", "size_bytes", "content_sha256",
                    "reference_date", "sales_last_month", "restored_from", "summary")


# ----------------------------------------------------------- frame <-> rows

def normalise_sku(value: Any) -> str | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return str(value).strip().upper() or None


def _encode_value(value: Any, datetime_column: bool) -> Any:
    if value is None or value is pd.NaT:
        return None
    if isinstance(value, dict) and set(value) in ({"$datetime"}, {"$date"}):
        return value  # Já codificado (linha relida do banco).
    if isinstance(value, (pd.Timestamp, datetime)):
        iso = pd.Timestamp(value).isoformat()
        return iso if datetime_column else {"$datetime": iso}
    if isinstance(value, date):
        return {"$date": value.isoformat()}
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        return None if math.isnan(value) else float(value)
    if isinstance(value, str):
        return value
    raise DatasetStoreError(f"Tipo de valor não suportado no banco: {type(value).__name__}")


def _decode_value(value: Any) -> Any:
    if isinstance(value, dict):
        if "$datetime" in value:
            return pd.Timestamp(value["$datetime"]).to_pydatetime()
        if "$date" in value:
            return date.fromisoformat(value["$date"])
    return value


def encode_frame(frame: pd.DataFrame) -> tuple[list[list[str]], list[dict[str, Any]]]:
    """Colunas na ordem original com o dtype, e uma linha por registro (valor ausente vira null)."""
    columns = [[str(name), str(dtype)] for name, dtype in frame.dtypes.items()]
    datetime_columns = {name for name, dtype in columns if dtype.startswith("datetime64")}
    rows = [{name: _encode_value(value, name in datetime_columns) for name, value in record.items()}
            for record in frame.astype(object).to_dict("records")]
    return columns, rows


def decode_frame(columns: list[list[str]], rows: list[dict[str, Any]]) -> pd.DataFrame:
    names = [name for name, _ in columns]
    frame = pd.DataFrame([[_decode_value(row.get(name)) for name in names] for row in rows], columns=names)
    for name, dtype in columns:
        if dtype.startswith("datetime64"):
            frame[name] = pd.to_datetime(frame[name]).astype(dtype)
        elif dtype != "object":
            try:
                frame[name] = frame[name].astype(dtype)
            except (TypeError, ValueError):
                # Ex.: coluna inteira com valor ausente em um SKU cadastrado depois; mantém número com NaN.
                frame[name] = pd.to_numeric(frame[name], errors="coerce")
        elif frame[name].isna().all():
            frame[name] = frame[name].astype(object)
    return frame


def _without_skus(columns: list[list[str]], rows: list[dict[str, Any]], skus: set[str]) -> pd.DataFrame:
    """Mesmo filtro de `load_dataset`: linhas de SKU inativo saem; linha sem SKU fica."""
    return decode_frame(columns, [row for row in rows if normalise_sku(row.get("SKU")) not in skus] if skus else rows)


def content_sha256(dataset: dict[str, pd.DataFrame]) -> str:
    """Impressão digital do conteúdo (abas de SHEET_TABLES presentes): igual para a planilha e para a mesma base relida do banco."""
    payload = {sheet: encode_frame(dataset[sheet]) for sheet in SHEET_TABLES if sheet in dataset}
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def encode_snapshot(dataset: dict[str, pd.DataFrame], inactive_skus: set[str]) -> bytes:
    sheets = {}
    for sheet, frame in dataset.items():
        columns, rows = encode_frame(frame)
        sheets[sheet] = {"columns": columns, "rows": rows}
    payload = {"format": 1, "sheets": sheets, "inactive_skus": sorted(inactive_skus)}
    # mtime=0: o mesmo conjunto gera sempre os mesmos bytes.
    return gzip.compress(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), mtime=0)


def decode_snapshot(blob: bytes) -> tuple[dict[str, pd.DataFrame], set[str]]:
    payload = json.loads(gzip.decompress(bytes(blob)).decode("utf-8"))
    if payload.get("format") != 1:
        raise DatasetStoreError(f"Formato de snapshot desconhecido: {payload.get('format')!r}")
    sheets = payload["sheets"]
    frames = {name: decode_frame(sheets[name]["columns"], sheets[name]["rows"]) for name in SHEET_TABLES if name in sheets}
    return frames, set(payload.get("inactive_skus") or [])


# ------------------------------------------------------- cadastro de SKU

SKU_FIELDS = ("produto", "familia", "curva_abc", "lead_time_dias", "lote_minimo", "estoque_atual", "estoque_seguranca_dias", "venda_media_dia")


def _coverage_days(stock: float, daily_sales: float) -> int:
    """Mesma unidade da planilha (dias inteiros); sem venda cadastrada, a cobertura fica 0 e a previsão decide."""
    return int(round(stock / daily_sales)) if daily_sales > 0 else 0


def sku_rows(sku: str, fields: dict[str, Any], current: dict[str, dict[str, Any]] | None = None) -> dict[str, dict[str, Any]]:
    """Linhas de Produtos, Estoque_Atual e Lead_Times para o SKU; colunas não cadastradas pelo formulário são preservadas."""
    current = current or {}
    stock, daily = fields["estoque_atual"], fields["venda_media_dia"]
    coverage = _coverage_days(stock, daily)
    product = {
        **current.get("Produtos", {}),
        "SKU": sku, "Produto": fields["produto"], "Família": fields["familia"], "Curva ABC": fields["curva_abc"],
        "Lead time (dias)": fields["lead_time_dias"], "Lote mínimo": fields["lote_minimo"],
        "Estoque segurança (dias)": fields["estoque_seguranca_dias"], "Estoque atual": stock,
        "Cobertura (dias)": coverage, "Venda média/dia": daily,
    }
    product.setdefault("Status", "Ativo")
    product.setdefault("Descrição completa", fields["produto"])
    stock_row = {
        **current.get("Estoque_Atual", {}),
        "SKU": sku, "Estoque atual": stock, "Cobertura dias": coverage, "Estoque segurança dias": fields["estoque_seguranca_dias"],
        "Demanda média mensal": int(round(daily * 30)),
    }
    lead_time = {**current.get("Lead_Times", {}), "SKU": sku, "Família": fields["familia"], "Lead time dias": fields["lead_time_dias"], "Lote mínimo": fields["lote_minimo"]}
    return {"Produtos": product, "Estoque_Atual": stock_row, "Lead_Times": lead_time}


def apply_sku_rows(dataset: dict[str, pd.DataFrame], sku: str, rows: dict[str, dict[str, Any]] | None) -> dict[str, pd.DataFrame]:
    """Prévia em memória da alteração (None remove o SKU de todas as abas), para validar antes de gravar."""
    result = dict(dataset)
    for sheet, frame in dataset.items():
        if "SKU" not in frame:
            continue
        keep = frame[frame["SKU"].map(normalise_sku) != sku]
        if rows is None:
            result[sheet] = keep.reset_index(drop=True)
        elif sheet in rows:
            addition = pd.DataFrame([{column: rows[sheet].get(column) for column in frame.columns}], columns=frame.columns)
            result[sheet] = pd.concat([keep, addition.astype(frame.dtypes.to_dict(), errors="ignore")], ignore_index=True)
    return result


def registry_item(row: dict[str, Any], active: bool, updated_at: Any, updated_by: str | None) -> dict[str, Any]:
    return {
        "sku": normalise_sku(row.get("SKU")), "produto": row.get("Produto"), "familia": row.get("Família"), "curva_abc": row.get("Curva ABC"),
        "lead_time_dias": row.get("Lead time (dias)"), "lote_minimo": row.get("Lote mínimo"),
        "estoque_atual": row.get("Estoque atual"), "estoque_seguranca_dias": row.get("Estoque segurança (dias)"),
        "venda_media_dia": row.get("Venda média/dia"), "ativo": bool(active),
        "atualizado_em": updated_at.isoformat() if isinstance(updated_at, (datetime, date)) else updated_at, "atualizado_por": updated_by,
    }


# ------------------------------------------------------------- database

_SQLITE_SCHEMA = [
    "create table if not exists dataset_sheets (name text primary key, table_name text not null, columns text not null, imported_at text not null default current_timestamp)",
    "create table if not exists dataset_version (id integer primary key check (id = 1), version integer not null default 0, updated_at text not null default current_timestamp, active_version_id integer)",
    "insert or ignore into dataset_version(id, version) values (1, 0)",
    "create table if not exists sku_changes (id integer primary key autoincrement, sku text not null, action text not null, user_email text not null, before text, after text, changed_at text not null default current_timestamp)",
    "create table if not exists app_users (id integer primary key autoincrement, email text not null unique, name text not null default '', password_hash text not null, active integer not null default 1, created_at text not null default current_timestamp)",
    *(f"create table if not exists {table} (id integer primary key autoincrement, position integer not null, sku text, data text not null"
      + (", active integer not null default 1, updated_at text, updated_by text, unique (sku))" if sheet == "Produtos" else ")")
      for sheet, table in SHEET_TABLES.items()),
    "create table if not exists dataset_versions (id integer primary key autoincrement, created_at text not null default current_timestamp, user_email text not null,"
    " action text not null check (action in ('upload', 'restore', 'original')), filename text, file_sha256 text, size_bytes integer,"
    " content_sha256 text not null, reference_date text, sales_last_month text, restored_from integer, summary text not null default '{}', snapshot blob not null)",
]


class Database:
    """PostgreSQL (psycopg) ou SQLite com a mesma interface mínima: transação, placeholders e JSON."""

    def __init__(self, *, database_url: str | None = None, sqlite_path: Path | None = None):
        if bool(database_url) == bool(sqlite_path):
            raise ValueError("Informe DATABASE_URL ou o caminho do SQLite, não os dois")
        self._database_url = database_url
        self._sqlite_path = sqlite_path
        self.kind = "postgres" if database_url else "sqlite"
        if sqlite_path is not None:
            sqlite_path.parent.mkdir(parents=True, exist_ok=True)
            with self.transaction() as cursor:
                for statement in _SQLITE_SCHEMA:
                    cursor.execute(statement)
                # Bancos locais anteriores à migração 005 não têm a coluna da versão ativa.
                columns = {row["name"] for row in cursor.execute("pragma table_info(dataset_version)").fetchall()}
                if "active_version_id" not in columns:
                    cursor.execute("alter table dataset_version add column active_version_id integer")

    def __repr__(self) -> str:
        return f"Database(kind={self.kind!r})"

    @contextmanager
    def transaction(self) -> Iterator[Any]:
        if self._database_url:
            import psycopg
            from psycopg.rows import dict_row

            with psycopg.connect(self._database_url, autocommit=False, prepare_threshold=None, row_factory=dict_row) as connection:
                with connection.cursor() as cursor:
                    yield _Cursor(cursor, "%s")
            return
        connection = sqlite3.connect(self._sqlite_path)
        connection.row_factory = sqlite3.Row
        try:
            yield _Cursor(connection.cursor(), "?")
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    def json_in(self, value: Any) -> Any:
        if self.kind == "postgres":
            from psycopg.types.json import Jsonb

            return Jsonb(value)
        return json.dumps(value, ensure_ascii=False)

    @staticmethod
    def json_out(value: Any) -> Any:
        return json.loads(value) if isinstance(value, str) else value


class _Cursor:
    """Queries are written with `?`; PostgreSQL receives `%s`."""

    def __init__(self, cursor, placeholder: str):
        self._cursor = cursor
        self._placeholder = placeholder

    def execute(self, query: str, params: tuple | list = ()) -> "_Cursor":
        self._cursor.execute(query.replace("?", self._placeholder) if self._placeholder != "?" else query, tuple(params))
        return self

    def executemany(self, query: str, rows: list[tuple]) -> None:
        self._cursor.executemany(query.replace("?", self._placeholder) if self._placeholder != "?" else query, rows)

    def fetchone(self) -> dict[str, Any] | None:
        row = self._cursor.fetchone()
        return None if row is None else dict(row)

    def fetchall(self) -> list[dict[str, Any]]:
        return [dict(row) for row in self._cursor.fetchall()]


class DatasetStore:
    def __init__(self, database: Database):
        self.db = database
        self._versions_schema_ok = database.kind != "postgres"  # O SQLite cria a tabela e a coluna na abertura.

    def _require_versions_schema(self, cursor: _Cursor) -> None:
        """No PostgreSQL, confere (information_schema) se a migração 005 foi aplicada; sem ela, erro claro em vez de 500."""
        if self._versions_schema_ok:
            return
        row = cursor.execute(
            "select (select count(*) from information_schema.tables where table_schema = current_schema() and table_name = 'dataset_versions')"
            " + (select count(*) from information_schema.columns where table_schema = current_schema() and table_name = 'dataset_version'"
            " and column_name = 'active_version_id') as total").fetchone()
        if not row or int(row["total"]) < 2:
            raise DatasetStoreError(MIGRATION_005_MISSING)
        self._versions_schema_ok = True

    # -------------------------------------------------------------- leitura

    def version(self) -> int:
        with self.db.transaction() as cursor:
            row = cursor.execute("select version from dataset_version where id = 1").fetchone()
            return int(row["version"]) if row else 0

    def is_empty(self) -> bool:
        with self.db.transaction() as cursor:
            return cursor.execute("select count(*) as total from dataset_sheets").fetchone()["total"] == 0

    def load_dataset(self, *, include_inactive: bool = False) -> dict[str, pd.DataFrame]:
        """As abas como a planilha as entrega; SKUs inativos saem de todas as abas (o histórico de casos e decisões fica).

        `include_inactive=True` devolve também as linhas dos SKUs inativos (o conjunto completo, como no snapshot de versão).
        """
        where, params = ("", ()) if include_inactive else (" where sku is null or sku not in (select sku from sheet_produtos where active = ?)", (False,))
        with self.db.transaction() as cursor:
            sheets = cursor.execute("select name, table_name, columns from dataset_sheets").fetchall()
            if not sheets:
                raise DatasetStoreError("O banco ainda não tem a planilha importada. Rode scripts/import_workbook.py.")
            frames = {}
            for sheet in sheets:
                rows = cursor.execute(f"select data from {sheet['table_name']}{where} order by position, id", params).fetchall()
                frames[sheet["name"]] = decode_frame(self.db.json_out(sheet["columns"]), [self.db.json_out(row["data"]) for row in rows])
        missing = sorted(set(SCHEMAS) - set(frames))
        if missing:
            raise DatasetStoreError(f"Abas obrigatórias ausentes no banco: {', '.join(missing)}")
        return {name: frames[name] for name in SHEET_TABLES if name in frames}

    def inactive_skus(self) -> set[str]:
        with self.db.transaction() as cursor:
            return {row["sku"] for row in cursor.execute("select sku from sheet_produtos where active = ?", (False,)).fetchall()}

    def edited_skus(self) -> set[str]:
        """SKUs com cadastro feito pela tela; o upload sobrescreve essas linhas (D10)."""
        with self.db.transaction() as cursor:
            rows = cursor.execute("select sku from sheet_produtos where updated_by is not null and sku is not null").fetchall()
        return {row["sku"] for row in rows}

    # -------------------------------------------------------------- versões

    def state(self) -> dict[str, Any]:
        with self.db.transaction() as cursor:
            self._require_versions_schema(cursor)
            row = cursor.execute("select version, active_version_id from dataset_version where id = 1").fetchone()
            version, active_id = (int(row["version"]), row["active_version_id"]) if row else (0, None)
            found = None if active_id is None else cursor.execute(
                f"select {', '.join(_VERSION_COLUMNS)} from dataset_versions where id = ?", (active_id,)).fetchone()
        return {"version": version, "active_version_id": None if active_id is None else int(active_id),
                "active": None if found is None else self._version_row(found)}

    def list_versions(self) -> list[dict[str, Any]]:
        with self.db.transaction() as cursor:
            self._require_versions_schema(cursor)
            rows = cursor.execute(f"select {', '.join(_VERSION_COLUMNS)} from dataset_versions order by id desc").fetchall()
        return [self._version_row(row) for row in rows]

    def version_snapshot(self, version_id: int) -> tuple[dict[str, pd.DataFrame], set[str], dict[str, Any]]:
        with self.db.transaction() as cursor:
            self._require_versions_schema(cursor)
            row = cursor.execute(f"select {', '.join(_VERSION_COLUMNS)}, snapshot from dataset_versions where id = ?", (version_id,)).fetchone()
        if row is None:
            raise DatasetVersionNotFound(f"Versão {version_id} não encontrada (o histórico guarda só as {MAX_VERSIONS} últimas).")
        dataset, inactive = decode_snapshot(row.pop("snapshot"))
        return dataset, inactive, self._version_row(row)

    def _version_row(self, row: dict[str, Any]) -> dict[str, Any]:
        """VersionRow de C4: nunca inclui o snapshot."""
        item = {column: row.get(column) for column in _VERSION_COLUMNS}
        for column in ("created_at", "reference_date"):
            if isinstance(item[column], (datetime, date)):
                item[column] = item[column].isoformat()
        if isinstance(item["created_at"], str) and self.db.kind == "sqlite":
            # current_timestamp do SQLite é UTC sem fuso ("2026-10-11 12:00:00"); sai em ISO com +00:00, como no PostgreSQL.
            moment = datetime.fromisoformat(item["created_at"])
            item["created_at"] = (moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)).isoformat()
        for column in ("id", "size_bytes", "restored_from"):
            if item[column] is not None:
                item[column] = int(item[column])
        item["summary"] = {} if item["summary"] is None else self.db.json_out(item["summary"])
        return item

    def list_skus(self) -> list[dict[str, Any]]:
        with self.db.transaction() as cursor:
            rows = cursor.execute("select data, active, updated_at, updated_by from sheet_produtos order by sku").fetchall()
        return [registry_item(self.db.json_out(row["data"]), row["active"], row["updated_at"], row["updated_by"]) for row in rows]

    def sku_state(self, sku: str) -> tuple[bool, dict[str, dict[str, Any]]] | None:
        """(ativo, linha atual de cada aba do cadastro) ou None se o SKU não existe."""
        with self.db.transaction() as cursor:
            product = cursor.execute("select active from sheet_produtos where sku = ?", (sku,)).fetchone()
            if product is None:
                return None
            current = {}
            for sheet in SKU_SHEETS:
                row = cursor.execute(f"select data from {SHEET_TABLES[sheet]} where sku = ? order by position limit 1", (sku,)).fetchone()
                if row is not None:
                    current[sheet] = self.db.json_out(row["data"])
            return bool(product["active"]), current

    # -------------------------------------------------------------- escrita

    def import_dataset(self, dataset: dict[str, pd.DataFrame], *, replace: bool = False) -> int:
        self._check_sheets(dataset)
        with self.db.transaction() as cursor:
            self._require_versions_schema(cursor)
            existing = cursor.execute("select count(*) as total from dataset_sheets").fetchone()["total"]
            if existing and not replace:
                raise DatasetStoreError("O banco já tem dados importados. Use --replace para substituir (o cadastro feito pela tela será perdido).")
            self._write_sheets(cursor, dataset)
            # A importação pela linha de comando não gera versão: a base ativa deixa de corresponder a uma versão do histórico.
            cursor.execute("update dataset_version set active_version_id = null where id = 1")
            return self._bump(cursor)

    def apply_version(self, dataset: dict[str, pd.DataFrame], *, action: str, user_email: str, filename: str | None = None,
                      file_sha256: str | None = None, size_bytes: int | None = None, reference_date: Any = None,
                      sales_last_month: str | None = None, summary: dict[str, Any] | None = None, restored_from: int | None = None,
                      inactive_skus: set[str] | None = None, expected_version: int | None = None, keep: int = MAX_VERSIONS) -> dict[str, Any]:
        """Grava o conjunto como base ativa e como versão nova, numa transação só.

        `inactive_skus=None` mantém as exclusões lógicas atuais; SKU inativo que saiu de Produtos some sem erro.
        `keep` = quantas versões ficam (o chamador passa max_versions de config/dataset_upload.json; padrão MAX_VERSIONS).
        `expected_version` é conferido sob trava: `for update` no PostgreSQL e `begin immediate` no SQLite (fecha a corrida
        confere-e-grava entre duas aplicações simultâneas).
        """
        if action not in VERSION_ACTIONS:
            raise DatasetStoreError(f"Ação de versão desconhecida: {action}")
        if isinstance(keep, bool) or not isinstance(keep, int) or keep < 1:
            raise DatasetStoreError("keep precisa ser pelo menos 1")
        self._check_sheets(dataset)
        missing = sorted(set(SCHEMAS) - set(dataset))
        if missing:
            raise DatasetStoreError(f"Abas obrigatórias ausentes: {', '.join(missing)}")
        lock = " for update" if self.db.kind == "postgres" else ""
        with self.db.transaction() as cursor:
            if self.db.kind == "sqlite":
                cursor.execute("begin immediate")  # Trava de escrita antes de ler a versão; a outra aplicação espera e vê a nova.
            self._require_versions_schema(cursor)
            current = cursor.execute(f"select version from dataset_version where id = 1{lock}").fetchone()
            if expected_version is not None and int(expected_version) != (int(current["version"]) if current else 0):
                raise DatasetVersionConflict("Outra pessoa atualizou a base; refaça a prévia.")
            if inactive_skus is None:
                inactive_skus = {row["sku"] for row in cursor.execute("select sku from sheet_produtos where active = ?", (False,)).fetchall()}
            present = {normalise_sku(value) for value in dataset["Produtos"]["SKU"]} if "SKU" in dataset["Produtos"] else set()
            inactive = {sku for sku in map(normalise_sku, inactive_skus) if sku in present}
            self._write_sheets(cursor, dataset)
            for sku in sorted(inactive):
                cursor.execute("update sheet_produtos set active = ? where sku = ?", (False, sku))
            # Hash do conjunto como load_dataset() o devolve, isto é, sem as linhas dos SKUs inativos.
            digest = content_sha256({sheet: _without_skus(*encode_frame(frame), inactive) for sheet, frame in dataset.items()})
            row = cursor.execute(
                "insert into dataset_versions(user_email, action, filename, file_sha256, size_bytes, content_sha256, reference_date,"
                " sales_last_month, restored_from, summary, snapshot) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) returning id",
                (user_email, action, filename, file_sha256, size_bytes, digest,
                 reference_date.isoformat() if isinstance(reference_date, (date, datetime)) else reference_date,
                 sales_last_month, restored_from, self.db.json_in(summary or {}), encode_snapshot(dataset, inactive)),
            ).fetchone()
            version_id = int(row["id"])
            cursor.execute("update dataset_version set active_version_id = ? where id = 1", (version_id,))
            # Poda: ficam as `keep` mais recentes, contando a nova (que é a ativa e nunca sai).
            stale = cursor.execute("select id from dataset_versions where id <> ? order by id desc", (version_id,)).fetchall()[keep - 1:]
            for item in stale:
                cursor.execute("delete from dataset_versions where id = ?", (item["id"],))
            version = self._bump(cursor)
        return {"version": version, "version_id": version_id, "content_sha256": digest, "pruned": len(stale)}

    @staticmethod
    def _check_sheets(dataset: dict[str, pd.DataFrame]) -> None:
        unknown = sorted(set(dataset) - set(SHEET_TABLES))
        if unknown:
            raise DatasetStoreError(f"Abas sem tabela no banco: {', '.join(unknown)}")

    def _write_sheets(self, cursor: _Cursor, dataset: dict[str, pd.DataFrame]) -> None:
        """Regrava todas as abas (rotina de import_dataset e apply_version); o cadastro feito pela tela é substituído."""
        for table in SHEET_TABLES.values():
            cursor.execute(f"delete from {table}")
        cursor.execute("delete from dataset_sheets")
        for sheet, frame in dataset.items():
            columns, rows = encode_frame(frame)
            table = SHEET_TABLES[sheet]
            cursor.execute("insert into dataset_sheets(name, table_name, columns) values (?, ?, ?)", (sheet, table, self.db.json_in(columns)))
            cursor.executemany(f"insert into {table}(position, sku, data) values (?, ?, ?)",
                               [(position, normalise_sku(row.get("SKU")), self.db.json_in(row)) for position, row in enumerate(rows)])

    def save_sku(self, sku: str, rows: dict[str, dict[str, Any]], user_email: str, *, create: bool) -> int:
        with self.db.transaction() as cursor:
            existing = cursor.execute("select data, active from sheet_produtos where sku = ?", (sku,)).fetchone()
            if create and existing is not None:
                state = "ativo" if existing["active"] else "inativo (reative em vez de cadastrar de novo)"
                raise SkuConflict(f"SKU {sku} já existe e está {state}.")
            if not create and existing is None:
                raise SkuNotFound(f"SKU {sku} não encontrado no cadastro.")
            columns = {row["name"]: [name for name, _ in self.db.json_out(row["columns"])]
                       for row in cursor.execute("select name, columns from dataset_sheets").fetchall()}
            for sheet, values in rows.items():
                table = SHEET_TABLES[sheet]
                data = {column: _encode_value(values.get(column), False) for column in columns.get(sheet, values)}
                updated = cursor.execute(f"select id from {table} where sku = ? order by position limit 1", (sku,)).fetchone()
                if updated is not None:
                    cursor.execute(f"update {table} set data = ? where id = ?", (self.db.json_in(data), updated["id"]))
                else:
                    position = cursor.execute(f"select coalesce(max(position), -1) + 1 as next from {table}").fetchone()["next"]
                    cursor.execute(f"insert into {table}(position, sku, data) values (?, ?, ?)", (position, sku, self.db.json_in(data)))
            cursor.execute("update sheet_produtos set updated_at = current_timestamp, updated_by = ? where sku = ?", (user_email, sku))
            self._log(cursor, sku, "criado" if create else "editado", user_email, None if existing is None else self.db.json_out(existing["data"]), rows["Produtos"])
            return self._bump(cursor)

    def set_active(self, sku: str, active: bool, user_email: str) -> int:
        with self.db.transaction() as cursor:
            existing = cursor.execute("select active from sheet_produtos where sku = ?", (sku,)).fetchone()
            if existing is None:
                raise SkuNotFound(f"SKU {sku} não encontrado no cadastro.")
            if bool(existing["active"]) == active:
                raise SkuConflict(f"SKU {sku} já está {'ativo' if active else 'inativo'}.")
            cursor.execute("update sheet_produtos set active = ?, updated_at = current_timestamp, updated_by = ? where sku = ?", (active, user_email, sku))
            self._log(cursor, sku, "reativado" if active else "excluido", user_email, {"ativo": not active}, {"ativo": active})
            return self._bump(cursor)

    def _log(self, cursor: _Cursor, sku: str, action: str, user_email: str, before: Any, after: Any) -> None:
        cursor.execute("insert into sku_changes(sku, action, user_email, before, after) values (?, ?, ?, ?, ?)",
                       (sku, action, user_email, None if before is None else self.db.json_in(before), None if after is None else self.db.json_in(after)))

    @staticmethod
    def _bump(cursor: _Cursor) -> int:
        cursor.execute("update dataset_version set version = version + 1, updated_at = current_timestamp where id = 1")
        return int(cursor.execute("select version from dataset_version where id = 1").fetchone()["version"])
