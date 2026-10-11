"""Upload pela API real (backend.main): ligação do router, cache do pipeline e hash da base ativa (critérios 10 e 11)."""
import hashlib
import secrets
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import backend.main as main
from caderno_inteligente.dataset_store import Database, DatasetStore
from caderno_inteligente.ingestion import load_workbook

EXAMPLE = Path(__file__).resolve().parents[1] / "docs/exemplos/atualizacao-2026-10.xlsx"
EMAIL = "pcp@exemplo.com"


@pytest.fixture
def client(tmp_path, monkeypatch):
    for name in ("RUNS_DB", "CASES_DB", "FEEDBACK_DB", "DATASET_DB", "BENCHMARK_DB"):
        monkeypatch.setattr(main, name, tmp_path / f"{name.lower()}.db")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("DATA_SOURCE", "banco")
    monkeypatch.setenv("AUTH_SECRET", secrets.token_urlsafe(48))
    monkeypatch.setattr(main, "_pipeline_cache", None)
    monkeypatch.setattr(main, "_version_seen", None)
    password = secrets.token_urlsafe(18)  # gerada no teste e nunca registrada
    main.user_store().create_user(EMAIL, "Ana PCP", password)
    main.dataset_store().import_dataset(load_workbook(main.SOURCE))
    client = TestClient(main.app)
    token = client.post("/api/auth/login", json={"email": EMAIL, "password": password}).json()["token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client


def _apply_example(client) -> dict:
    content = EXAMPLE.read_bytes()
    headers = {"Content-Type": "application/octet-stream", "X-Filename": EXAMPLE.name}
    preview = client.post("/api/dataset/preview", content=content, headers=headers)
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["can_apply"] and body["reference"]["after"] == "2026-10-12"
    assert body["engine"]["after"]["forecast_first_month"] == "2026-10"
    applied = client.post("/api/dataset/apply", content=content, headers={
        **headers, "X-Confirm-Sha256": hashlib.sha256(content).hexdigest(), "X-Expected-Version": str(body["expected_version"])})
    assert applied.status_code == 200, applied.text
    return applied.json()


def test_dataset_status_in_database_mode_starts_from_the_original(client):
    body = client.get("/api/dataset").json()
    assert (body["data_source"], body["reference_date"], body["matches_original"], body["upload_enabled"]) == ("banco", "2026-09-14", True, True)
    assert main.active_source_hash() == hashlib.sha256(main.SOURCE.read_bytes()).hexdigest()


def test_apply_refreshes_the_pipeline_on_the_same_instance(client):
    """Critério 10, mesma instância: on_change invalida o cache e a próxima consulta já vê a base nova."""
    before = client.get("/api/priorities").json()
    assert client.get("/api/data-quality").json()["reference"]["reference_date"] == "2026-09-14"
    _apply_example(client)
    assert client.get("/api/data-quality").json()["reference"]["reference_date"] == "2026-10-12"
    after = client.get("/api/priorities").json()
    assert after != before
    summary = main.engine_summary()  # None: a base ativa, do cache já recalculado
    assert (summary["reference_date"], summary["forecast_first_month"]) == ("2026-10-12", "2026-10")
    assert summary["top5"] == [{"sku": item["sku"], "product": item["product"], "urgency_label": item["urgency_label"]} for item in after[:5]]


def test_write_by_another_instance_is_seen_after_the_version_check(client, monkeypatch):
    """Critério 10, outra instância: gravando por outro DatasetStore, a consulta seguinte à checagem de versão reflete."""
    assert client.get("/api/data-quality").json()["reference"]["reference_date"] == "2026-09-14"
    other = DatasetStore(Database(sqlite_path=main.DATASET_DB))
    dataset = load_workbook(main.SOURCE)
    dataset["Produtos"].loc[dataset["Produtos"]["SKU"] == "CI-0004", "Produto"] = "Planner Semanal Outra Instância"
    other.apply_version(dataset, action="upload", user_email="outra@exemplo.com")
    monkeypatch.setattr(main, "_version_seen", None)  # o mesmo efeito de esperar VERSION_CHECK_SECONDS
    products = {item["sku"]: item["product"] for item in client.get("/api/priorities").json()}
    assert products["CI-0004"] == "Planner Semanal Outra Instância"


def test_active_hash_reaches_validation_and_runs_and_restore_brings_cases_back(client):
    """Critério 11: base nova → casos da base anterior fora da contagem; execução grava o hash ativo; original → volta a valer."""
    original = client.get("/api/validation/summary").json()["frozen_cases"]
    assert original["source_matches_frozen"] is True and original.get("previous_base", 0) == 0

    applied = _apply_example(client)
    summary = client.get("/api/validation/summary").json()["frozen_cases"]
    assert summary["source_matches_frozen"] is False and summary["previous_base"] == 20
    assert summary["failed"] == 0
    run_id = client.post("/api/runs").json()["id"]
    assert client.get(f"/api/runs/{run_id}").json()["source_hash"] == applied["content_sha256"]

    restored = client.post("/api/dataset/restore-original", headers={"X-Expected-Version": str(applied["version"])})
    assert restored.status_code == 200, restored.text
    again = client.get("/api/validation/summary").json()["frozen_cases"]
    assert again["source_matches_frozen"] is True and again.get("previous_base", 0) == 0
    assert (again["passed"], again["failed"]) == (original["passed"], original["failed"])
    assert client.get("/api/dataset").json()["matches_original"] is True
