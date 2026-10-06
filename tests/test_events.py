import json
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from caderno_inteligente.events import DEFAULT_SETTINGS, build_event_analysis, load_event_settings, parse_events

ROOT = Path(__file__).resolve().parents[1]


def _sales(spike: float = 250.0, family_skus=("A",), months: int = 24) -> pd.DataFrame:
    periods = pd.period_range("2024-09", periods=months, freq="M")
    rows = [
        {"Mês": period.to_timestamp(), "SKU": sku, "Cliente/Canal": "E-commerce", "Quantidade faturada": spike if period.month == 11 else 100.0}
        for sku in family_skus for period in periods
    ]
    return pd.DataFrame(rows)


def _products(*rows) -> pd.DataFrame:
    return pd.DataFrame({"SKU": [r[0] for r in rows], "Produto": "P", "Família": [r[1] for r in rows], "Lead time (dias)": [r[2] if len(r) > 2 else 14 for r in rows]})


def _forecast(sku="A", model="moving_average_3", values=(100.0, 100.0, 100.0), status="ok") -> dict:
    ok = status == "ok"
    return {"sku": sku, "reference_month": "2026-08-01", "model": model if ok else None, "status": status,
            "forecast_months": ["2026-09-01", "2026-10-01", "2026-11-01"] if ok else [], "forecast_values": list(values) if ok else []}


def _calendar(*events) -> pd.DataFrame:
    return pd.DataFrame(events, columns=["Evento", "Início", "Fim", "Famílias impactadas", "Impacto esperado", "Observação"])


BLACK_FRIDAY = ("Black Friday", pd.Timestamp("2026-11-20"), pd.Timestamp("2026-11-30"), "Todas", "Alta", "Desconto")


def _analyse(forecasts, products, sales, calendar, prices=None, settings=None):
    return build_event_analysis(pd.DataFrame(forecasts), products, sales, calendar, settings or dict(DEFAULT_SETTINGS), prices)


def _item(result, sku="A"):
    return next(item for item in result["items"] if item["sku"] == sku)


# --- configuração e leitura do calendário -----------------------------------

def test_shipped_settings_load_and_unknown_or_invalid_values_are_rejected(tmp_path):
    assert load_event_settings(ROOT / "config/event_factors.json")["maximum_factor"] >= 1
    for bad in ({"desconhecido": 1}, {"minimum_factor": 0}, {"maximum_factor": 0.9}, {"baseline_radius_months": 0}, {"neutral_band": 1}, {"minimum_occurrences": 0}, {"no_history_markers": "x"}, {"lookahead_buffer_days": 1.5}):
        path = tmp_path / "bad.json"
        path.write_text(json.dumps(bad), encoding="utf-8")
        with pytest.raises(ValueError):
            load_event_settings(path)


def test_parse_events_splits_families_flags_no_history_and_reports_ignored_rows():
    calendar = _calendar(
        BLACK_FRIDAY,
        ("Natal", pd.Timestamp("2026-12-01"), pd.Timestamp("2026-12-23"), "Planner; Executivo", "Média", None),
        ("Lançamento", pd.Timestamp("2026-10-15"), pd.Timestamp("2026-10-31"), "Clássico", "Alta", "Novos SKUs sem histórico direto"),
        ("Sem data", pd.NaT, pd.NaT, "Todas", "Alta", None),
        ("Invertido", pd.Timestamp("2026-05-10"), pd.Timestamp("2026-05-01"), "Todas", "Alta", None),
    )
    events, ignored = parse_events(calendar, dict(DEFAULT_SETTINGS))
    by_name = {event["name"]: event for event in events}
    assert by_name["Black Friday"]["families"] is None and by_name["Natal"]["families"] == ["Planner", "Executivo"]
    assert by_name["Lançamento"]["has_history"] is False and by_name["Black Friday"]["has_history"] is True
    assert {item["event"] for item in ignored} == {"Sem data", "Invertido"} and all(item["reason"] for item in ignored)


# --- fator por evidência histórica ------------------------------------------

def test_factor_comes_from_family_history_and_scenario_multiplies_only_event_months():
    result = _analyse([_forecast()], _products(("A", "F1")), _sales(spike=250), _calendar(BLACK_FRIDAY), prices={"A": 10.0})
    evidence = result["events"][0]["families"][0]
    assert evidence["factor"] == pytest.approx(2.5, abs=0.01) and evidence["occurrences"] == 2 and evidence["evidence_status"] == "aumento"
    scenario = _item(result)["scenario"]
    assert scenario["factors"][:2] == [None, None] and scenario["factors"][2] == pytest.approx(2.5, abs=0.01)
    assert scenario["scenario_units"][:2] == [100.0, 100.0] and scenario["scenario_units"][2] == pytest.approx(250.0, abs=1)
    assert scenario["incremental_units_3m"] == pytest.approx(150.0, abs=1)
    assert scenario["scenario_revenue_total_3m"] == pytest.approx(scenario["scenario_total_3m"] * 10.0, abs=0.01)
    assert scenario["base_revenue_total_3m"] == 3000.0 and scenario["nature"] == "estimado"
    assert scenario["next_month_affected"] is False


def test_factor_is_capped_and_the_cut_is_recorded():
    result = _analyse([_forecast()], _products(("A", "F1")), _sales(spike=500), _calendar(BLACK_FRIDAY), settings={**DEFAULT_SETTINGS, "maximum_factor": 2.0})
    evidence = result["events"][0]["families"][0]
    assert evidence["factor_raw"] == pytest.approx(5.0, abs=0.05) and evidence["factor"] == 2.0 and evidence["capped"] is True
    assert _item(result)["scenario"]["factors"][2] == 2.0


def test_family_without_enough_history_gets_alert_only_never_a_factor():
    result = _analyse([_forecast()], _products(("A", "F1")), _sales(months=10), _calendar(BLACK_FRIDAY))
    evidence = result["events"][0]["families"][0]
    assert evidence["factor"] is None and evidence["evidence_status"] == "sem_evidencia" and "apenas alerta" in evidence["note"]
    item = _item(result)
    assert item["alerts"] and item["scenario"] is None and "só há alerta" in item["scenario_note"]


def test_event_without_direct_history_is_alert_only():
    launch = ("Lançamento", pd.Timestamp("2026-10-15"), pd.Timestamp("2026-10-31"), "Todas", "Alta", "Novos SKUs sem histórico direto")
    result = _analyse([_forecast()], _products(("A", "F1")), _sales(), _calendar(launch))
    evidence = result["events"][0]["families"][0]
    assert evidence["evidence_status"] == "sem_historico_direto" and evidence["factor"] is None
    item = _item(result)
    assert item["alerts"][0]["event"] == "Lançamento" and item["scenario"] is None
    assert result["family_factors"] == []


def test_calendar_impact_without_historical_lift_is_flagged_not_hidden():
    result = _analyse([_forecast()], _products(("A", "F1")), _sales(spike=102), _calendar(BLACK_FRIDAY))
    evidence = result["events"][0]["families"][0]
    assert evidence["evidence_status"] == "sem_alteracao" and "evidência não" in evidence["note"]


# --- sem dupla contagem ------------------------------------------------------

def test_seasonal_model_gets_alert_but_no_scenario_to_avoid_double_counting():
    result = _analyse([_forecast(model="seasonal_naive_12")], _products(("A", "F1")), _sales(), _calendar(BLACK_FRIDAY))
    item = _item(result)
    assert item["alerts"] and item["scenario"] is None and item["scenario_applicable"] is False
    assert "já incorpora a sazonalidade" in item["scenario_note"]


def test_sku_without_forecast_has_no_scenario_and_says_why():
    result = _analyse([_forecast(status="insufficient_data")], _products(("A", "F1")), _sales(), _calendar(BLACK_FRIDAY))
    item = _item(result)
    assert item["scenario"] is None and "Sem previsão" in item["scenario_note"]


# --- janela de alerta --------------------------------------------------------

def test_alert_window_uses_lead_time_and_buffer_and_ignores_past_or_other_families():
    near = ("Perto", pd.Timestamp("2026-12-20"), pd.Timestamp("2026-12-31"), "F1", "Alta", None)      # fora do horizonte, dentro de lead+janela
    far = ("Longe", pd.Timestamp("2027-04-15"), pd.Timestamp("2027-05-10"), "F1", "Média", None)    # decisão só depois
    past = ("Passado", pd.Timestamp("2026-06-01"), pd.Timestamp("2026-06-30"), "F1", "Alta", None)
    other = ("Outra", pd.Timestamp("2026-10-01"), pd.Timestamp("2026-10-31"), "F2", "Alta", None)
    result = _analyse([_forecast()], _products(("A", "F1", 20)), _sales(), _calendar(near, far, past, other))
    alerts = {alert["event"]: alert for alert in _item(result)["alerts"]}
    assert set(alerts) == {"Perto"}
    assert alerts["Perto"]["decision_date"] == "2026-11-30" and alerts["Perto"]["in_horizon"] is False
    by_name = {event["name"]: event for event in result["events"]}
    assert by_name["Passado"]["past"] is True and by_name["Perto"]["skus_alerted"] == 1 and by_name["Longe"]["skus_alerted"] == 0


def test_event_inside_horizon_is_flagged_in_horizon_and_decision_date_is_start_minus_lead():
    result = _analyse([_forecast()], _products(("A", "F1", 20)), _sales(), _calendar(BLACK_FRIDAY))
    alert = _item(result)["alerts"][0]
    assert alert["in_horizon"] is True and alert["decision_date"] == "2026-10-31" and alert["days_to_start"] == 81


def test_event_layer_does_not_change_the_forecast_input():
    frame = pd.DataFrame([_forecast()])
    before = frame.copy(deep=True)
    build_event_analysis(frame, _products(("A", "F1")), _sales(), _calendar(BLACK_FRIDAY), dict(DEFAULT_SETTINGS))
    pd.testing.assert_frame_equal(before, frame)


# --- API sobre a base real ---------------------------------------------------

@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_api_events_contract_and_labels(client):
    body = client.get("/api/events").json()
    assert body["limitations"] and body["field_nature"]["factor"]["nature"] == "estimado"
    assert len(body["items"]) == client.get("/api/overview").json()["total_skus"]
    names = {event["name"]: event for event in body["events"]}
    assert {"Black Friday", "Natal", "Volta às Aulas", "Lançamento Coleção Primavera", "Dia das Mães"} <= set(names)
    assert names["Lançamento Coleção Primavera"]["has_history"] is False
    assert all(family["factor"] is None for family in names["Lançamento Coleção Primavera"]["families"])
    black_friday = names["Black Friday"]
    assert black_friday["in_horizon"] is True and len(black_friday["families"]) == 6
    assert all(family["factor"] and family["occurrences"] >= 1 for family in black_friday["families"])


def test_api_scenario_is_base_times_factor_and_seasonal_skus_have_none(client):
    forecasts = {item["sku"]: item["forecast"] for item in client.get("/api/forecasts").json()}
    seen_scenario = seen_seasonal = 0
    for item in client.get("/api/events").json()["items"]:
        forecast = forecasts[item["sku"]]
        if forecast["model"] == "seasonal_naive_12":
            seen_seasonal += 1
            assert item["scenario"] is None and "já incorpora" in item["scenario_note"]
        if item["scenario"]:
            seen_scenario += 1
            scenario = item["scenario"]
            assert scenario["base_units"] == [round(v, 1) for v in forecast["forecast_values"]]
            for base, factor, units in zip(scenario["base_units"], scenario["factors"], scenario["scenario_units"]):
                assert units == pytest.approx(base * (1.0 if factor is None else factor), abs=0.11)
            assert scenario["quantity"]["official"] is not None
    assert seen_scenario > 0 and seen_seasonal > 0


def test_api_sku_detail_carries_event_fields_and_keeps_official_quantity(client):
    detail = client.get("/api/priorities/CI-0001").json()
    assert detail["event_alerts"] and {"event", "decision_date", "evidence", "in_horizon"} <= set(detail["event_alerts"][0])
    scenario = detail["event_scenario"]["scenario"]
    assert scenario and scenario["quantity"]["official"] == detail["operational_recommendation"]["suggested_quantity"]
    listed = next(item for item in client.get("/api/events").json()["items"] if item["sku"] == "CI-0001")
    assert detail["event_alerts"] == listed["alerts"]


def test_api_forecasts_and_priorities_do_not_gain_event_fields(client):
    for item in client.get("/api/forecasts").json():
        assert not any("event" in key or "scenario" in key for key in {**item, **item["forecast"]})
    for item in client.get("/api/priorities").json():
        assert not any("event" in key or "scenario" in key for key in item)
