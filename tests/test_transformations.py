from pathlib import Path
import pandas as pd
from caderno_inteligente.ingestion import load_workbook
from caderno_inteligente.transformations import normalise_dataset

SOURCE = Path("data/source/Base de Dados - Caderno Inteligente.xlsm")

def test_normalises_sku_and_dates_without_changing_input():
    raw = load_workbook(SOURCE)
    source_value = raw["Forecast_Comercial"].loc[0, "Mês"]
    normalised = normalise_dataset(raw)
    assert normalised["Produtos"]["SKU"].str.fullmatch(r"CI-\d{4}").all()
    assert pd.api.types.is_datetime64_any_dtype(normalised["Forecast_Comercial"]["Mês"])
    assert raw["Forecast_Comercial"].loc[0, "Mês"] == source_value

def test_safe_normalise_returns_issue_instead_of_raising():
    from caderno_inteligente.transformations import safe_normalise
    raw = load_workbook(SOURCE)
    frame = raw["Estoque_Atual"].astype({"Estoque atual": object})
    frame.loc[0, "Estoque atual"] = "doze"
    raw["Estoque_Atual"] = frame
    normalised, issues = safe_normalise(raw)
    assert normalised is None
    assert [(item["code"], item["sheet"], item["column"], item["row"], item["value"]) for item in issues] == [
        ("INVALID_NUMBER", "Estoque_Atual", "Estoque atual", 4, "doze")]

def test_safe_normalise_on_source_matches_normalise_dataset():
    from caderno_inteligente.transformations import safe_normalise
    raw = load_workbook(SOURCE)
    normalised, issues = safe_normalise(raw)
    assert issues == []
    expected = normalise_dataset(raw)
    for sheet, frame in expected.items():
        pd.testing.assert_frame_equal(normalised[sheet], frame)
