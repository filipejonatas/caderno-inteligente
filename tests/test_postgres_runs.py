from pathlib import Path

from tests.test_persistence import FakeConnection, TestPostgresPersistence


def _source(tmp_path):
    source = tmp_path / "source.xlsm"
    source.write_bytes(b"base")
    return source


def test_postgres_run_stores_comparison_when_migration_applied(tmp_path):
    connection = FakeConnection(one_results=[{"?column?": 1}, {"id": 3}])
    run_id = TestPostgresPersistence(connection).create_run(_source(tmp_path), {}, {}, {}, [], {"schema_version": 1})
    assert run_id == 3
    assert "information_schema.columns" in connection.statements[0][0]
    assert connection.statements[1][0].startswith("insert into runs(source_hash, weights, thresholds, quality, ranking, comparison)")


def test_postgres_run_falls_back_before_migration(tmp_path):
    connection = FakeConnection(one_results=[None, {"id": 4}])
    assert TestPostgresPersistence(connection).create_run(_source(tmp_path), {}, {}, {}, [], {"schema_version": 1}) == 4
    assert connection.statements[1][0].startswith("insert into runs(source_hash, weights, thresholds, quality, ranking) values")


def test_postgres_legacy_snapshot_without_comparison_skips_detection(tmp_path):
    connection = FakeConnection(one_results=[{"id": 5}])
    TestPostgresPersistence(connection).create_run(_source(tmp_path), {}, {}, {}, [])
    assert len(connection.statements) == 1


def test_postgres_get_run_returns_null_comparison_before_migration():
    connection = FakeConnection(one_results=[None, {"id": 1, "comparison": None}])
    assert TestPostgresPersistence(connection).get_run(1) == {"id": 1, "comparison": None}
    assert "null::jsonb as comparison" in connection.statements[1][0]


def test_postgres_list_runs_reports_schema_version():
    connection = FakeConnection(one_results=[{"?column?": 1}], all_results=[[{"id": 1, "comparison_schema_version": 1}]])
    assert TestPostgresPersistence(connection).list_runs() == [{"id": 1, "comparison_schema_version": 1}]
    assert "(comparison->>'schema_version')::int" in connection.statements[1][0]


def test_migration_002_is_additive():
    sql = Path("supabase/migrations/002_run_comparison.sql").read_text(encoding="utf-8").lower()
    assert "add column if not exists comparison jsonb" in sql
    assert "drop" not in sql and "not null" not in sql
