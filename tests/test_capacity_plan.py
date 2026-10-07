"""Etapa 15.4: capacidade semanal finita por linha."""
from __future__ import annotations

import pandas as pd
import pytest
from fastapi.testclient import TestClient

import backend.main as main
from caderno_inteligente.capacity_plan import build_capacity_plan


def _capacity(available: dict[str, float], family: str = "Escolar") -> pd.DataFrame:
    return pd.DataFrame([{"Semana inicial": pd.Timestamp(week), "Linha": f"Linha {family}", "Família": family, "Capacidade máxima": 1000.0,
                          "Capacidade disponível": value, "Ocupação": 0.9} for week, value in available.items()])


def _plans(*orders, sku="X"):
    return {sku: {"planned_orders": [{"due_date": due, "release_date": release, "quantity": float(quantity), "urgent": urgent}
                                     for due, release, quantity, urgent in orders]}}


INDICATORS = pd.DataFrame([{"SKU": "X", "family": "Escolar", "abc_curve": "A"}, {"SKU": "Y", "family": "Escolar", "abc_curve": "B"}])
WEEKS = {"2026-09-14": 300.0, "2026-09-21": 300.0, "2026-09-28": 300.0}


def _run(plans, available=WEEKS, orders=None):
    return build_capacity_plan(plans, INDICATORS, _capacity(available), orders, "2026-09-14", [1])


def test_order_that_fits_in_its_release_week_is_ok():
    result = _run(_plans(("2026-10-10", "2026-09-28", 200, False)))
    order = result["skus"]["X"]["orders"][0]
    assert order["status"] == "ok" and order["allocations"] == [{"week_start": "2026-09-28", "quantity": 200.0}]
    week = next(item for item in result["families"][0]["weeks"] if item["week_start"] == "2026-09-28")
    assert week["allocated"] == 200 and week["remaining"] == 100


def test_order_larger_than_its_week_uses_earlier_weeks_as_pre_production():
    order = _run(_plans(("2026-10-10", "2026-09-28", 500, False)))["skus"]["X"]["orders"][0]
    assert order["status"] == "pre_producao" and [item["week_start"] for item in order["allocations"]] == ["2026-09-28", "2026-09-21"]


def test_what_does_not_fit_before_the_need_is_unscheduled_and_never_moved_later():
    result = _run(_plans(("2026-09-30", "2026-09-21", 800, True)))
    order = result["skus"]["X"]["orders"][0]
    assert order["status"] == "insuficiente" and order["unscheduled"] == 200  # só 14/09 e 21/09 servem
    assert all(item["week_start"] <= "2026-09-21" for item in order["allocations"])
    assert result["skus"]["X"]["status_now"] == "insuficiente" and result["families"][0]["first_shortfall_due"] == "2026-09-30"


def test_release_after_the_calendar_is_to_be_confirmed_not_ok_nor_short():
    order = _run(_plans(("2026-11-20", "2026-11-02", 100, False)))["skus"]["X"]["orders"][0]
    assert order["status"] == "a_confirmar" and order["allocations"] == []


def test_earlier_need_is_served_first_and_allocated_never_exceeds_available():
    plans = {**_plans(("2026-10-20", "2026-09-28", 600, False), sku="Y"), **_plans(("2026-10-05", "2026-09-21", 600, True), sku="X")}
    result = _run(plans)
    assert result["skus"]["X"]["orders"][0]["status"] == "pre_producao"
    assert result["skus"]["Y"]["orders"][0]["status"] == "insuficiente"
    for week in result["families"][0]["weeks"]:
        assert 0 <= week["allocated"] <= week["available"] and week["remaining"] >= 0


def test_family_summary_lists_short_skus_affected_orders_and_peak():
    orders = pd.DataFrame([{"Pedido": "PED-1", "SKU": "X", "Cliente/Canal": "KA-01", "Quantidade": 50.0}])
    result = _run(_plans(("2027-01-10", "2026-09-28", 2000, False)), orders=orders)
    family = result["families"][0]
    assert family["status"] == "insuficiente" and family["skus_short"] == ["X"]
    assert family["affected_orders"] == [{"order": "PED-1", "sku": "X", "client": "KA-01", "quantity": 50.0}]
    assert family["peak_need_units"] == 2000 and family["peak_status"] == "insuficiente"
    assert family["available_until_calendar_end"] == 900


# ------------------------------------------------------------------------------------------ base real


@pytest.fixture(scope="module")
def client():
    return TestClient(main.app)


def test_escolar_line_cannot_absorb_back_to_school(client):
    body = client.get("/api/capacity-plan").json()
    escolar = next(family for family in body["families"] if family["family"] == "Escolar")
    assert escolar["available_until_calendar_end"] == 12960 and escolar["status"] == "insuficiente"
    assert escolar["peak_status"] == "insuficiente" and escolar["unscheduled_quantity"] > 0
    assert {"CI-0014", "CI-0041"} <= set(escolar["skus_short"])
    for family in body["families"]:
        for week in family["weeks"]:
            assert week["allocated"] <= week["available"] + 1e-6
    assert body["requires_human_review"] is True and body["assumptions"]


def test_capacity_rule_replaces_the_average_occupation_rule(client):
    detail = client.get("/api/priorities/CI-0014").json()
    codes = {item["code"] for item in detail["issues"]}
    assert "CAPACITY_SHORTFALL" in codes and "CAPACITY_CONFLICT" not in codes
    recommendation = detail["operational_recommendation"]
    assert recommendation["capacity_status"] == "requires_review" and recommendation["capacity"]["status"] == "insuficiente"
    assert any(line.startswith("Capacidade:") for line in recommendation["rationale"])
    weeks = client.get("/api/capacity/Escolar").json()["weeks"]
    assert all("allocated" in week and "remaining" in week for week in weeks)
