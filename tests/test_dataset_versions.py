import sqlite3
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import pytest

from caderno_inteligente.dataset_merge import merge_upload
from caderno_inteligente.dataset_store import (
    MAX_VERSIONS,
    Database,
    DatasetStore,
    DatasetStoreError,
    DatasetVersionConflict,
    DatasetVersionNotFound,
    MIGRATION_005_MISSING,
    content_sha256,
    decode_snapshot,
    encode_snapshot,
    sku_rows,
)
from caderno_inteligente.ingestion import load_workbook
from caderno_inteligente.upload_safety import load_upload_settings

SOURCE = Path("data/source/Base de Dados - Caderno Inteligente.xlsm")
USER = "pcp@exemplo.com"


@pytest.fixture(scope="module")
def workbook():
    return load_workbook(SOURCE)


@pytest.fixture
def store(tmp_path, workbook):
    result = DatasetStore(Database(sqlite_path=tmp_path / "dataset.db"))
    result.import_dataset(workbook)
    return result


def with_september(workbook):
    sales = workbook["Vendas_24m"]
    sent = sales[sales["Mês"] == "2025-09"].copy()
    sent["Mês"] = "2026-09"
    merged, _, issues = merge_upload(workbook, {"Vendas_24m": sent})
    assert issues == []
    return merged


def test_import_round_trip_keeps_the_content_hash(store, workbook):
    assert content_sha256(workbook) == content_sha256(store.load_dataset())
    assert len(content_sha256(workbook)) == 64


def test_snapshot_encoding_round_trip(workbook):
    blob = encode_snapshot(workbook, {"CI-0002", "CI-0001"})
    assert blob == encode_snapshot(workbook, {"CI-0001", "CI-0002"})  # determinístico
    frames, inactive = decode_snapshot(blob)
    assert inactive == {"CI-0001", "CI-0002"}
    assert content_sha256(frames) == content_sha256(workbook)


def test_apply_version_writes_the_base_records_the_version_and_restores_it(store, workbook):
    assert store.state() == {"version": 1, "active_version_id": None, "active": None}
    merged = with_september(workbook)
    result = store.apply_version(merged, action="upload", user_email=USER, filename="atualizacao.xlsx", file_sha256="ab" * 32,
                                 size_bytes=1234, reference_date="2026-10-12", sales_last_month="2026-09",
                                 summary={"sheets": 1}, expected_version=1)
    assert (result["version"], result["pruned"]) == (2, 0)
    loaded = store.load_dataset()
    assert loaded["Vendas_24m"]["Mês"].nunique() == 25
    assert result["content_sha256"] == content_sha256(loaded) == content_sha256(merged)

    state = store.state()
    assert state["version"] == 2 and state["active_version_id"] == result["version_id"]
    active = state["active"]
    assert (active["action"], active["user_email"], active["filename"], active["size_bytes"], active["reference_date"],
            active["sales_last_month"], active["summary"]) == ("upload", USER, "atualizacao.xlsx", 1234, "2026-10-12", "2026-09", {"sheets": 1})
    assert "snapshot" not in active and set(active) == set(store.list_versions()[0])

    snapshot, inactive, row = store.version_snapshot(result["version_id"])
    assert content_sha256(snapshot) == result["content_sha256"] and inactive == set() and row["id"] == result["version_id"]

    original = store.apply_version(workbook, action="original", user_email=USER, inactive_skus=set())
    assert original["content_sha256"] == content_sha256(workbook)
    back = store.apply_version(snapshot, action="restore", user_email=USER, restored_from=row["id"], inactive_skus=inactive)
    assert back["content_sha256"] == result["content_sha256"]
    assert [item["action"] for item in store.list_versions()] == ["restore", "original", "upload"]
    assert store.list_versions()[0]["restored_from"] == row["id"]


def test_expected_version_mismatch_is_a_conflict_and_writes_nothing(store, workbook):
    with pytest.raises(DatasetVersionConflict, match="refaça a prévia"):
        store.apply_version(with_september(workbook), action="upload", user_email=USER, expected_version=7)
    assert store.version() == 1 and store.list_versions() == []
    assert store.load_dataset()["Vendas_24m"]["Mês"].nunique() == 24


def test_history_keeps_the_last_twenty_and_never_the_active_one(store, workbook):
    ids = [store.apply_version(workbook, action="original", user_email=USER)["version_id"] for _ in range(MAX_VERSIONS)]
    result = store.apply_version(workbook, action="original", user_email=USER)
    assert result["pruned"] == 1
    versions = store.list_versions()
    assert len(versions) == MAX_VERSIONS and versions[0]["id"] == result["version_id"] and ids[0] not in {item["id"] for item in versions}
    with pytest.raises(DatasetVersionNotFound):
        store.version_snapshot(ids[0])
    small = store.apply_version(workbook, action="original", user_email=USER, keep=3)
    assert small["pruned"] == MAX_VERSIONS - 2
    assert [item["id"] for item in store.list_versions()][0] == store.state()["active_version_id"] == small["version_id"]


def test_inactive_sku_stays_inactive_and_vanishes_quietly_when_it_leaves_the_workbook(store, workbook):
    store.set_active("CI-0001", False, USER)
    store.set_active("CI-0002", False, USER)
    without_two = {sheet: frame[frame["SKU"] != "CI-0002"].reset_index(drop=True) if "SKU" in frame else frame
                   for sheet, frame in workbook.items()}
    result = store.apply_version(without_two, action="upload", user_email=USER)
    assert store.inactive_skus() == {"CI-0001"}
    loaded = store.load_dataset()
    assert "CI-0001" not in set(loaded["Produtos"]["SKU"]) and "CI-0001" not in set(loaded["Vendas_24m"]["SKU"])
    assert "CI-0001" in set(store.load_dataset(include_inactive=True)["Produtos"]["SKU"])
    assert result["content_sha256"] == content_sha256(loaded)

    snapshot, inactive, _ = store.version_snapshot(result["version_id"])
    assert inactive == {"CI-0001"} and "CI-0001" in set(snapshot["Produtos"]["SKU"])  # snapshot guarda o conjunto completo


def test_upload_overwrites_the_screen_registry(store, workbook):
    store.save_sku("CI-9001", sku_rows("CI-9001", {"produto": "Caderno Teste", "familia": "Clássico", "curva_abc": "B", "lead_time_dias": 12,
                                                   "lote_minimo": 200, "estoque_atual": 300, "estoque_seguranca_dias": 7,
                                                   "venda_media_dia": 10.0}), USER, create=True)
    assert store.edited_skus() == {"CI-9001"}
    store.apply_version(workbook, action="upload", user_email=USER)
    assert store.edited_skus() == set() and "CI-9001" not in set(store.load_dataset()["Produtos"]["SKU"])


def test_apply_version_rejects_incomplete_sets_and_unknown_actions(store, workbook):
    with pytest.raises(DatasetStoreError, match="Produtos"):
        store.apply_version({k: v for k, v in workbook.items() if k != "Produtos"}, action="upload", user_email=USER)
    with pytest.raises(DatasetStoreError, match="desconhecida"):
        store.apply_version(workbook, action="apagar", user_email=USER)
    assert store.version() == 1


def test_import_from_the_command_line_clears_the_active_version(store, workbook):
    store.apply_version(workbook, action="original", user_email=USER)
    store.import_dataset(workbook, replace=True)
    assert store.state()["active_version_id"] is None and len(store.list_versions()) == 1


def test_old_sqlite_database_gains_the_new_column_and_table_on_open(tmp_path, workbook):
    path = tmp_path / "antigo.db"
    with sqlite3.connect(path) as connection:
        connection.execute("create table dataset_version (id integer primary key check (id = 1), version integer not null default 0,"
                           " updated_at text not null default current_timestamp)")
        connection.execute("insert into dataset_version(id, version) values (1, 5)")
    store = DatasetStore(Database(sqlite_path=path))
    assert store.state() == {"version": 5, "active_version_id": None, "active": None}
    with sqlite3.connect(path) as connection:
        assert "active_version_id" in {row[1] for row in connection.execute("pragma table_info(dataset_version)")}
    store.import_dataset(workbook)
    assert store.apply_version(workbook, action="original", user_email=USER, expected_version=6)["version"] == 7
    DatasetStore(Database(sqlite_path=path))  # reabrir não repete a alteração
    assert [item["id"] for item in store.list_versions()] == [store.state()["active_version_id"]]


def test_keep_comes_from_config_and_must_be_a_positive_integer(store, workbook):
    keep = load_upload_settings()["max_versions"]
    for _ in range(keep + 2):
        store.apply_version(workbook, action="original", user_email=USER, keep=keep)
    assert len(store.list_versions()) == keep
    for invalid in (0, True, "3"):
        with pytest.raises(DatasetStoreError, match="keep"):
            store.apply_version(workbook, action="original", user_email=USER, keep=invalid)


def test_sqlite_version_created_at_is_iso_with_utc_offset(store, workbook):
    store.apply_version(workbook, action="original", user_email=USER)
    [row] = store.list_versions()
    assert row["created_at"].endswith("+00:00")
    assert abs((datetime.fromisoformat(row["created_at"]) - datetime.now(timezone.utc)).total_seconds()) < 120
    assert store.state()["active"]["created_at"] == row["created_at"]


def test_concurrent_applies_with_the_same_expected_version_only_one_wins(tmp_path, workbook):
    """begin immediate: a segunda aplicação espera a primeira gravar e então vê a versão nova (conflito), sem gravar duas vezes."""
    path = tmp_path / "dataset.db"
    DatasetStore(Database(sqlite_path=path)).import_dataset(workbook)
    first, second = DatasetStore(Database(sqlite_path=path)), DatasetStore(Database(sqlite_path=path))
    locked = threading.Event()
    original_write = first._write_sheets

    def slow_write(cursor, dataset):
        locked.set()  # A primeira já leu a versão sob a trava; a segunda começa agora.
        time.sleep(0.5)
        original_write(cursor, dataset)

    first._write_sheets = slow_write
    outcomes = {}

    def run(name, target):
        try:
            outcomes[name] = target.apply_version(workbook, action="original", user_email=USER, expected_version=1)["version"]
        except Exception as error:  # noqa: BLE001 - o teste confere o tipo
            outcomes[name] = error

    worker = threading.Thread(target=run, args=("first", first))
    worker.start()
    assert locked.wait(5)
    run("second", second)
    worker.join(10)
    assert outcomes["first"] == 2
    assert isinstance(outcomes["second"], DatasetVersionConflict)
    assert len(second.list_versions()) == 1 and second.version() == 2


class _FakePostgres:
    """Database falso no modo postgres: responde à consulta do information_schema e registra as consultas."""

    kind = "postgres"

    def __init__(self, total):
        self.total = total
        self.queries = []

    @contextmanager
    def transaction(self):
        fake = self

        class Cursor:
            def execute(self, query, params=()):
                fake.queries.append(query)
                self.query = query
                return self

            def fetchone(self):
                if "information_schema" in self.query:
                    return {"total": fake.total}
                raise AssertionError(f"consulta inesperada sem a migração 005: {self.query}")

        yield Cursor()

    @staticmethod
    def json_out(value):
        return value


def test_postgres_without_migration_005_raises_a_clear_error(workbook):
    for total in (0, 1):
        store = DatasetStore(_FakePostgres(total))
        for call in (store.state, store.list_versions, lambda: store.version_snapshot(1), lambda: store.import_dataset(workbook, replace=True),
                     lambda: store.apply_version(workbook, action="upload", user_email=USER)):
            with pytest.raises(DatasetStoreError, match="rode a migração 005"):
                call()
    assert "information_schema.tables" in store.db.queries[0] and "active_version_id" in store.db.queries[0]
    assert "005" in MIGRATION_005_MISSING


def test_postgres_with_migration_005_checks_the_schema_only_once():
    fake = _FakePostgres(2)
    store = DatasetStore(fake)
    with fake.transaction() as cursor:
        store._require_versions_schema(cursor)
        store._require_versions_schema(cursor)
    assert len(fake.queries) == 1
