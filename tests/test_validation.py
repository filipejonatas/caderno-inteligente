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

def test_validate_dataset_without_new_parameters_keeps_current_output():
    data = load_workbook(SOURCE)
    assert validate_dataset(data) == validate_dataset(data, header_rows=None, max_examples=None)
    report = validate_dataset(data)
    assert set(report) == {"errors", "warnings", "sheets", "foreign_keys", "sell_out_coverage"}
    assert all("severity" not in item and "cell" not in item for item in report["warnings"])

def test_invalid_number_carries_excel_address():
    data = load_workbook(SOURCE)
    frame = data["Vendas_24m"].astype({"Quantidade faturada": object})
    frame.loc[6, "Quantidade faturada"] = "abc"  # Cabeçalho na linha 3: posição 6 = linha 10.
    data["Vendas_24m"] = frame
    report = validate_dataset(data, header_rows={"Vendas_24m": 3}, max_examples=5)
    issue = next(item for item in report["errors"] if item["code"] == "INVALID_NUMBER")
    assert {key: issue[key] for key in ("sheet", "row", "column", "cell", "value", "severity", "count", "more")} == {
        "sheet": "Vendas_24m", "row": 10, "column": "Quantidade faturada", "cell": "D10", "value": "abc",
        "severity": "error", "count": 1, "more": 0}
    assert issue["examples"][0]["key"].startswith("2024-09")
    assert issue["message"]

def test_repeated_errors_keep_five_examples_and_count_the_rest():
    from caderno_inteligente.validation import validate_sheets
    data = load_workbook(SOURCE)
    frame = data["Vendas_24m"].astype({"Quantidade faturada": object})
    frame.loc[:39, "Quantidade faturada"] = "x"
    data["Vendas_24m"] = frame
    issues = validate_sheets(data, ["Vendas_24m"], header_rows={"Vendas_24m": 1})
    issue = next(item for item in issues if item["code"] == "INVALID_NUMBER")
    assert issue["count"] == 40 and len(issue["examples"]) == 5 and issue["more"] == 35
    assert [example["row"] for example in issue["examples"]] == [2, 3, 4, 5, 6]
    assert all(item["code"] not in {"MISSING_SHEET", "ORPHAN_KEY"} for item in issues)

def test_duplicate_and_orphan_issues_point_to_rows():
    data = load_workbook(SOURCE)
    data["Lead_Times"] = data["Lead_Times"].copy()
    data["Lead_Times"].loc[2, "SKU"] = data["Lead_Times"].loc[0, "SKU"]
    data["Sell_In"] = data["Sell_In"].copy()
    data["Sell_In"].loc[1, "SKU"] = "CI-9999"
    report = validate_dataset(data, max_examples=5)
    duplicate = next(item for item in report["errors"] if item["code"] == "DUPLICATE_KEY" and item["sheet"] == "Lead_Times")
    assert duplicate["row"] == 6 and duplicate["cell"] == "A6"
    orphan = next(item for item in report["errors"] if item["code"] == "ORPHAN_KEY" and item["child_sheet"] == "Sell_In" and item["child_column"] == "SKU")
    assert orphan["sheet"] == "Sell_In" and orphan["row"] == 5 and orphan["value"] == "CI-9999"
