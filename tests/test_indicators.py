from pathlib import Path
import pandas as pd
import pytest
from caderno_inteligente.indicators import build_sku_indicators
from caderno_inteligente.ingestion import load_workbook
from caderno_inteligente.transformations import normalise_dataset

SOURCE = Path("data/source/Base de Dados - Caderno Inteligente.xlsm")

def test_builds_one_consistent_row_per_sku():
    indicators = build_sku_indicators(normalise_dataset(load_workbook(SOURCE)))
    assert len(indicators) == 50
    assert indicators["SKU"].is_unique
    assert indicators["coverage_days_calculated"].notna().all()
    # A base possui 50 pares parceiro × SKU com sell-out, distribuídos por 30 SKUs.
    assert indicators["has_sell_out"].sum() == 30
    assert indicators["sell_out_visibility"].eq("não disponível").sum() == 20

def test_calculates_projected_stock_transparently():
    indicators = build_sku_indicators(normalise_dataset(load_workbook(SOURCE)))
    row = indicators.loc[indicators["SKU"] == "CI-0001"].iloc[0]
    assert row["projected_stock_quantity"] == pytest.approx(row["current_stock"] + row["production_order_quantity"] - row["backlog_order_quantity"])

def test_operational_gap_is_never_negative():
    indicators = build_sku_indicators(normalise_dataset(load_workbook(SOURCE)))
    expected = (
        indicators["backlog_order_quantity"]
        - indicators["current_stock"]
        - indicators["production_order_quantity"]
    ).clip(lower=0)
    assert indicators["operational_gap_quantity"].ge(0).all()
    assert indicators["operational_gap_quantity"].equals(expected)

def test_critical_date_uses_earliest_available_date_and_reports_missing_dates():
    indicators = build_sku_indicators(normalise_dataset(load_workbook(SOURCE)))
    dated = indicators[indicators["critical_date"].notna()]
    for _, row in dated.iterrows():
        available_dates = [
            value
            for value in (row["first_promised_date"], row["first_production_completion"])
            if pd.notna(value)
        ]
        assert row["critical_date"] == min(available_dates)
        assert row["critical_date_reason"] in {
            "first_promised_date",
            "first_production_completion",
        }

    without_dates = indicators[
        indicators["first_promised_date"].isna()
        & indicators["first_production_completion"].isna()
    ]
    assert not without_dates.empty
    assert without_dates["critical_date"].isna().all()
    assert without_dates["critical_date_reason"].isna().all()
    assert without_dates["missing_data"].map(
        lambda fields: "first_promised_date" in fields and "first_production_completion" in fields
    ).all()

def test_missing_sell_out_stays_null_and_is_explained():
    indicators = build_sku_indicators(normalise_dataset(load_workbook(SOURCE)))
    without_sell_out = indicators[~indicators["has_sell_out"]]
    assert without_sell_out["sell_out_quantity"].isna().all()
    assert without_sell_out["missing_data"].map(lambda fields: "sell_out_quantity" in fields).all()

def test_capacity_is_aggregated_by_family():
    indicators = build_sku_indicators(normalise_dataset(load_workbook(SOURCE)))
    assert indicators["capacity_weeks"].min() > 0
    assert indicators["capacity_occupation_average"].between(0, 1).all()
