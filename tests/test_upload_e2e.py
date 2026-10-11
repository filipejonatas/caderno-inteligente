"""Ponta a ponta do upload (U3B): pacote de exemplo pela API real, base nova no motor inteiro e volta à original."""
import hashlib
import secrets
import time
from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

import backend.main as main
from caderno_inteligente.ingestion import load_workbook, read_workbook_bytes
from caderno_inteligente.supply_plan import _orders_by_sku, daily_demand
from caderno_inteligente.workbook_writer import write_workbook

EXAMPLE = Path(__file__).resolve().parents[1] / "docs/exemplos/atualizacao-2026-10.xlsx"
EMAIL = "pcp@exemplo.com"
REFERENCE = "2026-10-12"
OCTET = {"Content-Type": "application/octet-stream", "X-Filename": EXAMPLE.name}


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
    api = TestClient(main.app)
    token = api.post("/api/auth/login", json={"email": EMAIL, "password": password}).json()["token"]
    api.headers["Authorization"] = f"Bearer {token}"
    return api


def _top5(client) -> list[str]:
    return [row["sku"] for row in client.get("/api/priorities").json()[:5]]


@pytest.fixture
def uploaded(client):
    """Estado antes do upload, prévia e aplicação do pacote de exemplo (com os tempos medidos)."""
    content = EXAMPLE.read_bytes()
    before = {"dataset": client.get("/api/dataset").json(), "top5": _top5(client)}
    started = time.perf_counter()
    preview = client.post("/api/dataset/preview", content=content, headers=OCTET)
    preview_seconds = time.perf_counter() - started
    assert preview.status_code == 200, preview.text
    body = preview.json()
    started = time.perf_counter()
    applied = client.post("/api/dataset/apply", content=content, headers={
        **OCTET, "X-Confirm-Sha256": hashlib.sha256(content).hexdigest(), "X-Expected-Version": str(body["expected_version"])})
    apply_seconds = time.perf_counter() - started
    assert applied.status_code == 200, applied.text
    print(f"\nprévia {preview_seconds:.2f}s, aplicação {apply_seconds:.2f}s")
    return {"before": before, "preview": body, "applied": applied.json()}


def test_preview_of_the_example_package_is_applicable_and_changes_nothing(client):
    before = client.get("/api/dataset").json()
    response = client.post("/api/dataset/preview", content=EXAMPLE.read_bytes(), headers=OCTET)
    body = response.json()
    assert response.status_code == 200 and body["can_apply"] is True
    assert (body["reference"]["before"], body["reference"]["after"]) == ("2026-09-14", REFERENCE)
    assert body["reference"]["sales_last_month_after"] == "2026-09"
    codes = {item["code"] for item in body["warnings"]}
    assert {"EXAMPLE_FILE", "PRODUCT_STOCK_DIVERGENCE"} <= codes
    assert client.get("/api/dataset").json()["version"] == before["version"]


def test_reference_date_is_single_across_the_engine_after_apply(client, uploaded):
    assert client.get("/api/data-quality").json()["reference"]["reference_date"] == REFERENCE
    assert client.get("/api/events").json()["reference_date"] == REFERENCE
    assert client.get("/api/capacity-plan").json()["reference_date"] == REFERENCE
    assert client.get("/api/allocation").json()["reference_date"] == REFERENCE


def test_forecast_of_every_ok_sku_starts_in_the_month_after_the_last_closed_sales(client, uploaded):
    forecasts = main.pipeline()[5]
    ok = forecasts[forecasts["status"] == "ok"]
    assert len(ok) > 0
    assert {str(months[0])[:7] for months in ok["forecast_months"]} == {"2026-10"}


def test_every_active_sku_with_forecast_has_demand_between_12_and_31_october(client, uploaded):
    dataset, forecasts = main.pipeline()[0], main.pipeline()[5]
    orders = _orders_by_sku(dataset["Carteira_Pedidos"])
    plans = main.supply_plans()
    reference, end = date(2026, 10, 12), date(2026, 10, 31)
    without_demand, checked = [], 0
    for row in forecasts.to_dict("records"):
        if row["status"] != "ok" or plans[str(row["sku"])]["discontinued"]:
            continue
        checked += 1
        # A carteira já cobre a previsão do mês quando é maior (a parte "além da carteira" zera de propósito): vale a demanda total.
        carteira, extra = daily_demand(row, orders.get(str(row["sku"]), []), reference, end)
        if sum(carteira.values()) + sum(extra.values()) <= 0:
            without_demand.append(row["sku"])
    assert checked > 0
    assert without_demand == []


def test_completed_production_orders_are_not_added_to_supply_again(client, uploaded):
    ops = read_workbook_bytes(EXAMPLE.read_bytes())["sheets"]["Ordens_Producao"]
    closed = ops["Status"].astype(str).str.strip().str.casefold().isin({"concluída", "concluida"})
    completed = set(ops.loc[closed, "Ordem"].astype(str))
    assert completed, "o exemplo deve conter OPs concluídas para o teste valer"
    op_events = [event for plan in main.supply_plans().values() for event in plan["supply_events"] if event["source"] == "op"]
    assert op_events
    assert not [event for event in op_events if event["date"] < REFERENCE]
    assert not [event for event in op_events if str(event["ref"]) in completed]


def test_no_order_is_falsely_late_after_the_reference_moves(client, uploaded):
    affected = [order for plan in main.supply_plans().values() for order in plan["affected_orders"]]
    assert not [order for order in affected if order.get("overdue_at_reference")]
    assert not [order for order in affected if order["promised_date"] < REFERENCE and order.get("uncovered_at_promise", 0) > 0]


def test_priority_queue_has_no_critical_date_before_the_reference(client, uploaded):
    queue = client.get("/api/priorities")
    assert queue.status_code == 200
    rows = queue.json()
    assert rows
    assert [row["sku"] for row in rows if row.get("critical_date") and row["critical_date"] < REFERENCE] == []


def test_sales_through_october_with_september_capacity_is_blocked_by_the_api(client):
    sales = load_workbook(main.SOURCE)["Vendas_24m"]
    october = sales[sales["Mês"] == sales["Mês"].max()].copy()
    october["Mês"] = pd.Timestamp("2026-10-01")
    content = write_workbook({"Vendas_24m": pd.concat([sales, october], ignore_index=True)}, title="vendas até out/26")
    response = client.post("/api/dataset/preview", content=content, headers={**OCTET, "X-Filename": "vendas.xlsx"})
    assert response.status_code == 422, response.text
    text = response.text
    assert "SERIES_NOT_CLOSED" in text
    assert "out/26" in text and "a data de planejamento é 14/09/2026" in text
    assert "envie Capacidade_Semanal, Estoque_Atual, Carteira_Pedidos e Ordens_Producao atualizadas" in text


def test_restore_original_brings_back_the_hash_and_the_top_five(client, uploaded):
    before = uploaded["before"]
    assert _top5(client) != before["top5"]
    restored = client.post("/api/dataset/restore-original", headers={"X-Expected-Version": str(uploaded["applied"]["version"])})
    assert restored.status_code == 200, restored.text
    after = client.get("/api/dataset").json()
    assert after["content_sha256"] == before["dataset"]["content_sha256"] and after["matches_original"] is True
    assert _top5(client) == before["top5"]
