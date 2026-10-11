from __future__ import annotations
import pandas as pd
from .schemas import SCHEMAS
from .validation import DEFAULT_HEADER_ROW, _parse_dates, address_issue

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


def safe_normalise(data: dict[str, pd.DataFrame], *, header_rows: dict[str, int] | None = None,
                   max_examples: int = 5) -> tuple[dict[str, pd.DataFrame] | None, list[dict]]:
    """normalise_dataset sem exceção: texto em coluna numérica vira Issue INVALID_NUMBER com endereço, nunca erro 500."""
    header_rows = header_rows or {}
    issues: list[dict] = []
    for sheet, frame in data.items():
        for column in NUMERIC_COLUMNS.get(sheet, ()):
            if column not in frame:
                continue
            invalid = frame[column].notna() & pd.to_numeric(frame[column], errors="coerce").isna()
            if invalid.any():
                issues.append(address_issue({"code": "INVALID_NUMBER", "sheet": sheet}, frame, invalid, column=column,
                                            key_columns=SCHEMAS[sheet].key_columns,
                                            header_row=header_rows.get(sheet, DEFAULT_HEADER_ROW), max_examples=max_examples,
                                            message=f"{sheet}.{column}: {int(invalid.sum())} valores não são números"))
    if issues:
        return None, issues
    try:
        return normalise_dataset(data), []
    except (ValueError, TypeError) as error:
        return None, [address_issue({"code": "NORMALISE_FAILED", "sheet": None}, None, None, max_examples=max_examples, count=1,
                                    message=f"Não foi possível padronizar os dados: {error}")]
