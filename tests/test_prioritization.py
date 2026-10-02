from pathlib import Path
from caderno_inteligente.indicators import build_sku_indicators
from caderno_inteligente.ingestion import load_workbook
from caderno_inteligente.prioritization import load_weights, prioritize
from caderno_inteligente.rules import evaluate_rules, load_rule_thresholds
from caderno_inteligente.transformations import normalise_dataset

SOURCE = Path("data/source/Base de Dados - Caderno Inteligente.xlsm")

def _ranking():
    data = normalise_dataset(load_workbook(SOURCE))
    indicators = build_sku_indicators(data)
    issues = evaluate_rules(indicators, load_rule_thresholds())
    return prioritize(issues, load_weights(), indicators)

def test_ranking_is_transparent_and_complete():
    ranking = _ranking()
    assert ranking["priority"].tolist() == list(range(1, len(ranking) + 1))
    assert ranking["attention_score"].is_monotonic_decreasing
    assert ranking["reasons"].map(bool).all()
    assert ranking["evidence"].map(bool).all()
    assert ranking["disclaimer"].str.contains("não é solução ótima").all()

def test_confidence_is_reduced_when_sellout_is_missing():
    ranking = _ranking()
    low_confidence = ranking.loc[ranking.confidence == "baixa"]
    assert len(low_confidence) == 20
    assert low_confidence.confidence_reason.str.contains("Sell-out não observado").all()

def test_score_equals_sum_of_configured_rule_weights():
    ranking = _ranking()
    weights = load_weights()
    first = ranking.iloc[0]
    assert first.attention_score == sum(weights[item["code"]] for item in first.reasons)

def test_ranking_exposes_operational_context_without_changing_sku_granularity():
    ranking = _ranking()
    expected_columns = {
        "critical_date",
        "critical_date_reason",
        "operational_gap_quantity",
        "projected_stock_quantity",
        "first_promised_date",
        "first_production_completion",
        "sell_in_quantity",
        "sell_out_quantity",
        "sell_in_minus_sell_out_quantity",
        "forecast_quantity",
        "analysis_scope",
        "missing_data",
    }
    assert expected_columns.issubset(ranking.columns)
    assert ranking["sku"].is_unique
    assert ranking["analysis_scope"].eq("SKU global").all()
    assert ranking["operational_gap_quantity"].ge(0).all()
