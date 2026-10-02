from pathlib import Path
from caderno_inteligente.indicators import build_sku_indicators
from caderno_inteligente.ingestion import load_workbook
from caderno_inteligente.rules import evaluate_rules, load_rule_thresholds
from caderno_inteligente.transformations import normalise_dataset

SOURCE = Path("data/source/Base de Dados - Caderno Inteligente.xlsm")

def _issues():
    data = normalise_dataset(load_workbook(SOURCE))
    return evaluate_rules(build_sku_indicators(data), load_rule_thresholds())

def test_returns_required_auditable_fields():
    issues = _issues()
    assert {"sku", "code", "description", "severity", "values_used", "data_origin"}.issubset(issues.columns)
    assert issues["values_used"].map(lambda value: isinstance(value, dict) and bool(value)).all()
    assert issues["data_origin"].map(lambda value: isinstance(value, list) and bool(value)).all()

def test_applies_all_seven_required_rules():
    codes = set(_issues()["code"])
    assert codes == {"RUP_LEAD_TIME", "RUP_SAFETY_STOCK", "ORDER_WITHOUT_PRODUCTION", "PRODUCTION_AFTER_PROMISE", "EXCESS_COVERAGE", "CAPACITY_CONFLICT", "LOW_SELLOUT_VISIBILITY"}

def test_sellout_absence_becomes_visibility_issue_not_zero_sale():
    issues = _issues()
    visibility = issues.loc[issues.code == "LOW_SELLOUT_VISIBILITY"]
    assert len(visibility) == 20
    assert all(item["sell_out_visibility"] == "não disponível" for item in visibility.values_used)

def test_thresholds_are_loaded_from_configuration():
    thresholds = load_rule_thresholds()
    assert thresholds == {"excess_coverage_days": 90, "capacity_occupation_threshold": 0.9}
