import pandas as pd
from fastapi.testclient import TestClient

from backend.main import _rupture_summary, app


def test_rupture_summary_counts_a_sku_with_two_signals_only_once():
    issues = pd.DataFrame(
        [
            {"sku": "CI-0001", "code": "RUP_LEAD_TIME"},
            {"sku": "CI-0001", "code": "RUP_SAFETY_STOCK"},
            {"sku": "CI-0002", "code": "RUP_LEAD_TIME"},
            {"sku": "CI-0003", "code": "ORDER_WITHOUT_PRODUCTION"},
        ]
    )

    assert _rupture_summary(issues) == {
        "rupture_sku_count": 2,
        "below_lead_time_count": 2,
        "below_safety_stock_count": 1,
        "rupture_signal_count": 3,
    }


def test_overview_exposes_corrected_rupture_metrics():
    response = TestClient(app).get("/api/overview")

    assert response.status_code == 200
    payload = response.json()
    assert payload["rupture_sku_count"] <= payload["rupture_signal_count"]
    assert payload["risk_count"] == payload["rupture_sku_count"]
    assert payload["below_lead_time_count"] == payload["risk_distribution"]["RUP_LEAD_TIME"]
    assert payload["below_safety_stock_count"] == payload["risk_distribution"]["RUP_SAFETY_STOCK"]
