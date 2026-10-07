import pandas as pd
from fastapi.testclient import TestClient

from backend.main import app, production_plan
from caderno_inteligente.production_plan import build_production_plan


def _order(release: str, quantity: float, urgent: bool) -> dict:
    return {"release_date": release, "due_date": release, "quantity": quantity, "urgent": urgent}


def _plan(sku: str, orders: list[dict], lead_time: int = 14, horizon_end: str = "2027-02-28") -> dict:
    return {
        "sku": sku, "reference_date": "2026-09-14", "horizon_end": horizon_end, "decision_window_end": "2026-10-12",
        "lead_time_days": lead_time, "planned_orders": orders,
        "suggested_quantity": float(sum(order["quantity"] for order in orders if order["urgent"])),
        "planned_quantity_horizon": float(sum(order["quantity"] for order in orders)),
    }


def _inputs(plans: dict, families: dict, statuses: dict | None = None):
    indicators = pd.DataFrame({"SKU": list(families), "family": list(families.values())})
    forecasts = pd.DataFrame({"sku": list(plans), "status": [(statuses or {}).get(sku, "ok") for sku in plans]})
    return plans, indicators, forecasts


def _months(block: dict) -> dict:
    return {row["month"]: (row["urgent"], row["later"]) for row in block["months"]}


def test_orders_are_summed_by_release_month_and_split_urgent_from_later():
    plans, indicators, forecasts = _inputs({
        "A": _plan("A", [_order("2026-09-14", 400, True), _order("2026-11-02", 200, False)]),
        "B": _plan("B", [_order("2026-09-20", 100, True), _order("2026-10-20", 300, False)]),
    }, {"A": "F1", "B": "F1"})
    result = build_production_plan(plans, indicators, forecasts)
    months = _months(result["total"])
    assert months["2026-09"] == (500, 0) and months["2026-10"] == (0, 300) and months["2026-11"] == (0, 200)
    assert result["requires_human_review"] is True and result["horizon_end"] == "2027-02-28"


def test_urgent_total_equals_suggested_quantity_and_families_add_up_to_total():
    plans, indicators, forecasts = _inputs({
        "A": _plan("A", [_order("2026-09-14", 400, True)]),
        "B": _plan("B", [_order("2026-10-01", 200, True), _order("2026-12-01", 600, False)]),
        "C": _plan("C", [_order("2026-11-10", 50, False)]),
    }, {"A": "F1", "B": "F2", "C": "F2"})
    result = build_production_plan(plans, indicators, forecasts)
    assert result["total"]["urgent_total"] == sum(plan["suggested_quantity"] for plan in plans.values()) == 600
    assert result["total"]["horizon_total"] == 1250
    for key in ("urgent_total", "horizon_total"):
        assert sum(family[key] for family in result["families"]) == result["total"][key]
    for index, row in enumerate(result["total"]["months"]):
        rows = [family["months"][index] for family in result["families"]]
        assert sum(r["urgent"] for r in rows) == row["urgent"] and sum(r["later"] for r in rows) == row["later"]


def test_month_is_omitted_when_lead_time_reaches_past_the_horizon():
    # Horizonte em 28/02 e lead time de 27 dias: janeiro fecha (31/01 + 27 = 27/02), fevereiro não.
    plans, indicators, forecasts = _inputs({
        "A": _plan("A", [_order("2027-01-20", 100, False), _order("2027-02-05", 80, False)], lead_time=27),
    }, {"A": "F1"})
    result = build_production_plan(plans, indicators, forecasts)
    assert result["omitted_months"] == ["2027-02"] and "2027-01" in _months(result["total"])
    # O total do horizonte continua contando a ordem do mês omitido; só o gráfico não a mostra.
    assert result["total"]["horizon_total"] == 180
    # Limite inclusivo: 31/01 + 28 = 28/02 ainda cabe; com 29 dias, janeiro também deixa de ser completo.
    plans["A"]["lead_time_days"] = 28
    assert build_production_plan(plans, indicators, forecasts)["omitted_months"] == ["2027-02"]
    plans["A"]["lead_time_days"] = 29
    assert build_production_plan(plans, indicators, forecasts)["omitted_months"] == ["2027-01", "2027-02"]


def test_sku_without_forecast_is_listed_and_never_counted_as_zero():
    plans, indicators, forecasts = _inputs({
        "A": _plan("A", [_order("2026-09-14", 400, True)]),
        "B": _plan("B", []),
    }, {"A": "F1", "B": "F2"}, statuses={"B": "insufficient_data"})
    result = build_production_plan(plans, indicators, forecasts)
    assert result["excluded_skus"] == [{"sku": "B", "reason": "sem_previsao"}]
    assert [family["family"] for family in result["families"]] == ["F1"]
    assert result["total"]["urgent_total"] == 400


def test_no_sku_with_forecast_returns_empty_months_not_zeros():
    plans, indicators, forecasts = _inputs({"A": _plan("A", [])}, {"A": "F1"}, statuses={"A": "insufficient_data"})
    result = build_production_plan(plans, indicators, forecasts)
    assert result["total"]["months"] == [] and result["horizon_end"] is None and result["excluded_skus"][0]["sku"] == "A"


def test_api_matches_the_queue_and_the_spec_acceptance_numbers():
    client = TestClient(app)
    body = client.get("/api/production-plan").json()
    forecasts = client.get("/api/forecasts").json()
    suggested = sum(item["operational_recommendation"]["suggested_quantity"] or 0 for item in forecasts)
    horizon = sum(item["operational_recommendation"].get("planned_quantity_horizon") or 0 for item in forecasts)
    assert body["total"]["urgent_total"] == suggested
    assert body["total"]["horizon_total"] == horizon
    assert sum(row["urgent"] for row in body["total"]["months"]) == suggested
    # Nenhum mês exibido é incompleto e nenhum mês omitido aparece no gráfico.
    shown = {row["month"] for row in body["total"]["months"]}
    assert shown.isdisjoint(body["omitted_months"])
    assert body["requires_human_review"] is True and body["limitations"]


def test_family_totals_match_the_skus_of_the_family():
    client = TestClient(app)
    body = client.get("/api/production-plan").json()
    forecasts = client.get("/api/forecasts").json()
    for family in body["families"]:
        skus = [item for item in forecasts if item["family"] == family["family"]]
        assert family["urgent_total"] == sum(item["operational_recommendation"]["suggested_quantity"] or 0 for item in skus)


def test_production_plan_reuses_the_pipeline_cache():
    assert production_plan() is production_plan()
