from __future__ import annotations
import pandas as pd
from .schemas import SCHEMAS
from .validation import _parse_dates

SKU_COLUMNS = ("SKU",)
DATE_COLUMNS = {sheet: schema.date_columns for sheet, schema in SCHEMAS.items()}
NUMERIC_COLUMNS = {sheet: schema.non_negative_columns for sheet, schema in SCHEMAS.items()}


def _normalise_sku(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip().str.upper()


def normalise_dataset(data: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Cria cópias internas com tipos consistentes; não altera a fonte nem os DataFrames de entrada."""
    normalised = {sheet: frame.copy(deep=True) for sheet, frame in data.items()}
    for sheet, frame in normalised.items():
        for column in SKU_COLUMNS:
            if column in frame:
                frame[column] = _normalise_sku(frame[column])
        for column in DATE_COLUMNS.get(sheet, ()):
            if column in frame:
                frame[column] = _parse_dates(frame[column])
        for column in NUMERIC_COLUMNS.get(sheet, ()):
            if column in frame:
                frame[column] = pd.to_numeric(frame[column], errors="raise")
    return normalised
