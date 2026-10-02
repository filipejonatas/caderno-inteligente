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
