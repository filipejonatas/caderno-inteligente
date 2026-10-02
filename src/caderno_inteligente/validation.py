from __future__ import annotations
import pandas as pd
from .schemas import SCHEMAS, FOREIGN_KEYS

_PT_MONTHS = {"jan": "jan", "fev": "feb", "mar": "mar", "abr": "apr", "mai": "may", "jun": "jun", "jul": "jul", "ago": "aug", "set": "sep", "out": "oct", "nov": "nov", "dez": "dec"}


def _parse_dates(series: pd.Series) -> pd.Series:
    """Aceita datas Excel/ISO e meses abreviados em português, sem mudar a fonte."""
    raw = series.astype("string").str.strip()
    month_mask = raw.str.match(r"^[A-Za-zç]{3}/\d{2}$", na=False)
    parsed = pd.to_datetime(raw.where(~month_mask), errors="coerce", dayfirst=True, format="mixed")
    normalized = raw.where(~month_mask).copy()
    normalized.loc[month_mask] = raw.loc[month_mask].str.replace(
        r"^([A-Za-zç]{3})/",
        lambda match: _PT_MONTHS.get(match.group(1).lower(), match.group(1)) + "/",
        regex=True,
    )
    parsed.loc[month_mask] = pd.to_datetime(normalized.loc[month_mask], format="%b/%y", errors="coerce")
    return parsed


def validate_dataset(data: dict[str, pd.DataFrame]) -> dict:
    """Valida contratos sem alterar os DataFrames ou a fonte XLSM."""
    report = {"errors": [], "warnings": [], "sheets": {}, "foreign_keys": [], "sell_out_coverage": None}
    for sheet, schema in SCHEMAS.items():
        frame = data.get(sheet)
        if frame is None:
            report["errors"].append({"code": "MISSING_SHEET", "sheet": sheet})
            continue
        missing_columns = sorted(set(schema.required_columns) - set(frame.columns))
        detail = {"records": len(frame), "missing_columns": missing_columns, "missing_values": {}, "duplicate_keys": 0, "invalid_dates": {}, "negative_values": {}}
        if missing_columns:
            report["errors"].append({"code": "MISSING_COLUMNS", "sheet": sheet, "columns": missing_columns})
            report["sheets"][sheet] = detail
            continue
        detail["missing_values"] = {column: int(frame[column].isna().sum()) for column in schema.required_columns if frame[column].isna().any()}
        if detail["missing_values"]:
            report["warnings"].append({"code": "MISSING_VALUES", "sheet": sheet, "values": detail["missing_values"]})
        if schema.key_columns:
            detail["duplicate_keys"] = int(frame.duplicated(list(schema.key_columns)).sum())
            if detail["duplicate_keys"]:
                report["errors"].append({"code": "DUPLICATE_KEY", "sheet": sheet, "count": detail["duplicate_keys"]})
        for column in schema.date_columns:
            invalid = int((frame[column].notna() & _parse_dates(frame[column]).isna()).sum())
            detail["invalid_dates"][column] = invalid
            if invalid:
                report["errors"].append({"code": "INVALID_DATE", "sheet": sheet, "column": column, "count": invalid})
        for column in schema.non_negative_columns:
            numbers = pd.to_numeric(frame[column], errors="coerce")
            invalid = int((frame[column].notna() & numbers.isna()).sum())
            negative = int((numbers < 0).sum())
            detail["negative_values"][column] = negative
            if invalid:
                report["errors"].append({"code": "INVALID_NUMBER", "sheet": sheet, "column": column, "count": invalid})
            if negative:
                report["errors"].append({"code": "NEGATIVE_VALUE", "sheet": sheet, "column": column, "count": negative})
        report["sheets"][sheet] = detail
    for child, child_column, parent, parent_column in FOREIGN_KEYS:
        if child not in data or parent not in data or child_column not in data[child] or parent_column not in data[parent]:
            continue
        orphaned = sorted(set(data[child][child_column].dropna()) - set(data[parent][parent_column].dropna()))
        item = {"child_sheet": child, "child_column": child_column, "parent_sheet": parent, "orphan_count": len(orphaned), "examples": orphaned[:10]}
        report["foreign_keys"].append(item)
        if orphaned:
            report["errors"].append({"code": "ORPHAN_KEY", **item})
    if {"Sell_Out", "Parceiros_Canais", "Produtos"}.issubset(data):
        partners = data["Parceiros_Canais"]
        b2b = partners.loc[partners["Tipo"] != "Canal direto", "Código"].nunique()
        skus = data["Produtos"]["SKU"].nunique()
        observed = data["Sell_Out"][["Cliente", "SKU"]].drop_duplicates().shape[0]
        possible = b2b * skus
        report["sell_out_coverage"] = {"observed_pairs": int(observed), "possible_pairs": int(possible), "coverage": observed / possible if possible else None, "missing_data_is_not_zero": True}
    return report
