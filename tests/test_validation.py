from pathlib import Path
from caderno_inteligente.ingestion import load_workbook
from caderno_inteligente.validation import validate_dataset

SOURCE = Path("data/source/Base de Dados - Caderno Inteligente.xlsm")

def test_source_passes_stage_one_validation():
    report = validate_dataset(load_workbook(SOURCE))
    assert report["errors"] == []
    assert report["sell_out_coverage"] == {"observed_pairs": 50, "possible_pairs": 250, "coverage": 0.2, "missing_data_is_not_zero": True}
    assert all(item["orphan_count"] == 0 for item in report["foreign_keys"])

def test_detects_duplicate_sku():
    data = load_workbook(SOURCE)
    data["Produtos"] = data["Produtos"].iloc[[0, 0]].copy()
    report = validate_dataset(data)
    assert any(error["code"] == "DUPLICATE_KEY" and error["sheet"] == "Produtos" for error in report["errors"])
