from __future__ import annotations
from collections.abc import Iterable
import pandas as pd
from openpyxl.utils import get_column_letter
from .schemas import SCHEMAS, FOREIGN_KEYS

_PT_MONTHS = {"jan": "jan", "fev": "feb", "mar": "mar", "abr": "apr", "mai": "may", "jun": "jun", "jul": "jul", "ago": "aug", "set": "sep", "out": "oct", "nov": "nov", "dez": "dec"}
DEFAULT_HEADER_ROW = 3  # Layout da planilha empacotada: título, espaço e cabeçalho na linha 3.
_ERROR_CODES = {"MISSING_SHEET", "MISSING_COLUMNS", "DUPLICATE_KEY", "INVALID_DATE", "INVALID_NUMBER", "NEGATIVE_VALUE", "ORPHAN_KEY", "NORMALISE_FAILED"}


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


def _text(value) -> str | None:
    if value is None or (not isinstance(value, (list, tuple)) and pd.isna(value)):
        return None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return str(value)


def address_issue(item: dict, frame: pd.DataFrame | None, mask: pd.Series | None, *, column: str | None = None,
                  key_columns: Iterable[str] = (), header_row: int = DEFAULT_HEADER_ROW, max_examples: int = 5,
                  message: str, count: int | None = None) -> dict:
    """Acrescenta os campos de endereço (C2) a um problema: linha e célula do Excel, valor e "mais N iguais".

    Linha do Excel = header_row + 1 + posição no DataFrame; a coluna vem da posição da coluna no DataFrame.
    """
    examples: list[dict] = []
    positions = [] if frame is None or mask is None else [index for index, flag in enumerate(mask.to_numpy()) if flag]
    keys = [name for name in key_columns if frame is not None and name in frame]
    letter = get_column_letter(frame.columns.get_loc(column) + 1) if frame is not None and column in frame else None
    for position in positions[:max_examples]:
        row = header_row + 1 + position
        record = frame.iloc[position]
        examples.append({"row": row, "cell": f"{letter}{row}" if letter else None,
                         "key": " | ".join(str(record[name]) for name in keys) if keys else None,
                         "value": _text(record[column]) if column in frame else None})
    total = len(positions) if count is None else count
    first = examples[0] if examples else {}
    item.update({"severity": "error" if item["code"] in _ERROR_CODES else "warning", "column": column, "message": message,
                 "count": int(total), "examples": examples, "more": max(int(total) - len(examples), 0),
                 "row": first.get("row"), "cell": first.get("cell"), "value": first.get("value")})
    return item


def _check_sheet(sheet: str, frame: pd.DataFrame, header_row: int, max_examples: int | None) -> tuple[dict, list[dict], list[dict]]:
    """Regras por aba. Sem `max_examples`, os itens saem no formato de sempre; com número, ganham os campos de C2."""
    schema = SCHEMAS[sheet]
    errors: list[dict] = []
    warnings: list[dict] = []
    addressed = max_examples is not None
    missing_columns = sorted(set(schema.required_columns) - set(frame.columns))
    detail = {"records": len(frame), "missing_columns": missing_columns, "missing_values": {}, "duplicate_keys": 0, "invalid_dates": {}, "negative_values": {}}
    if missing_columns:
        item = {"code": "MISSING_COLUMNS", "sheet": sheet, "columns": missing_columns}
        if addressed:
            address_issue(item, None, None, max_examples=max_examples, count=len(missing_columns),
                          message=f"{sheet}: faltam as colunas {', '.join(missing_columns)}")
        errors.append(item)
        return detail, errors, warnings
    detail["missing_values"] = {column: int(frame[column].isna().sum()) for column in schema.required_columns if frame[column].isna().any()}
    if detail["missing_values"]:
        item = {"code": "MISSING_VALUES", "sheet": sheet, "values": detail["missing_values"]}
        if addressed:
            columns = list(detail["missing_values"])
            mask = frame[columns].isna().any(axis=1)
            address_issue(item, frame, mask, column=columns[0] if len(columns) == 1 else None, key_columns=schema.key_columns,
                          header_row=header_row, max_examples=max_examples,
                          message=f"{sheet}: há células obrigatórias vazias em {', '.join(columns)}")
        warnings.append(item)
    if schema.key_columns:
        duplicated = frame.duplicated(list(schema.key_columns))
        detail["duplicate_keys"] = int(duplicated.sum())
        if detail["duplicate_keys"]:
            item = {"code": "DUPLICATE_KEY", "sheet": sheet, "count": detail["duplicate_keys"]}
            if addressed:
                column = schema.key_columns[0] if len(schema.key_columns) == 1 else None
                address_issue(item, frame, duplicated, column=column, key_columns=schema.key_columns, header_row=header_row,
                              max_examples=max_examples,
                              message=f"{sheet}: {detail['duplicate_keys']} linhas repetem a chave ({', '.join(schema.key_columns)})")
            errors.append(item)
    for column in schema.date_columns:
        if column not in frame:  # Coluna de data opcional (por exemplo, Última compra/venda).
            continue
        invalid_mask = frame[column].notna() & _parse_dates(frame[column]).isna()
        invalid = int(invalid_mask.sum())
        detail["invalid_dates"][column] = invalid
        if invalid:
            item = {"code": "INVALID_DATE", "sheet": sheet, "column": column, "count": invalid}
            if addressed:
                address_issue(item, frame, invalid_mask, column=column, key_columns=schema.key_columns, header_row=header_row,
                              max_examples=max_examples, message=f"{sheet}.{column}: {invalid} datas inválidas")
            errors.append(item)
    for column in schema.non_negative_columns:
        numbers = pd.to_numeric(frame[column], errors="coerce")
        invalid_mask = frame[column].notna() & numbers.isna()
        negative_mask = numbers < 0
        invalid = int(invalid_mask.sum())
        negative = int(negative_mask.sum())
        detail["negative_values"][column] = negative
        if invalid:
            item = {"code": "INVALID_NUMBER", "sheet": sheet, "column": column, "count": invalid}
            if addressed:
                address_issue(item, frame, invalid_mask, column=column, key_columns=schema.key_columns, header_row=header_row,
                              max_examples=max_examples, message=f"{sheet}.{column}: {invalid} valores não são números")
            errors.append(item)
        if negative:
            item = {"code": "NEGATIVE_VALUE", "sheet": sheet, "column": column, "count": negative}
            if addressed:
                address_issue(item, frame, negative_mask, column=column, key_columns=schema.key_columns, header_row=header_row,
                              max_examples=max_examples, message=f"{sheet}.{column}: {negative} valores negativos")
            errors.append(item)
    return detail, errors, warnings


def validate_dataset(data: dict[str, pd.DataFrame], *, header_rows: dict[str, int] | None = None, max_examples: int | None = None) -> dict:
    """Valida contratos sem alterar os DataFrames ou a fonte XLSM.

    `max_examples=None` devolve a saída de sempre; com número, cada erro ou aviso ganha endereço (C2).
    """
    header_rows = header_rows or {}
    addressed = max_examples is not None
    report = {"errors": [], "warnings": [], "sheets": {}, "foreign_keys": [], "sell_out_coverage": None}
    for sheet in SCHEMAS:
        frame = data.get(sheet)
        if frame is None:
            item = {"code": "MISSING_SHEET", "sheet": sheet}
            if addressed:
                address_issue(item, None, None, max_examples=max_examples, count=1, message=f"Aba {sheet} ausente")
            report["errors"].append(item)
            continue
        detail, errors, warnings = _check_sheet(sheet, frame, header_rows.get(sheet, DEFAULT_HEADER_ROW), max_examples)
        report["errors"].extend(errors)
        report["warnings"].extend(warnings)
        report["sheets"][sheet] = detail
    for child, child_column, parent, parent_column in FOREIGN_KEYS:
        if child not in data or parent not in data or child_column not in data[child] or parent_column not in data[parent]:
            continue
        orphaned = sorted(set(data[child][child_column].dropna()) - set(data[parent][parent_column].dropna()))
        item = {"child_sheet": child, "child_column": child_column, "parent_sheet": parent, "orphan_count": len(orphaned), "examples": orphaned[:10]}
        report["foreign_keys"].append(item)
        if orphaned:
            error = {"code": "ORPHAN_KEY", **item}
            if addressed:
                frame = data[child]
                error["sheet"] = child
                address_issue(error, frame, frame[child_column].isin(orphaned), column=child_column, key_columns=SCHEMAS[child].key_columns,
                              header_row=header_rows.get(child, DEFAULT_HEADER_ROW), max_examples=max_examples,
                              message=f"{child}.{child_column}: {len(orphaned)} códigos sem cadastro em {parent}.{parent_column}")
            report["errors"].append(error)
    if {"Sell_Out", "Parceiros_Canais", "Produtos"}.issubset(data):
        partners = data["Parceiros_Canais"]
        b2b = partners.loc[partners["Tipo"] != "Canal direto", "Código"].nunique()
        skus = data["Produtos"]["SKU"].nunique()
        observed = data["Sell_Out"][["Cliente", "SKU"]].drop_duplicates().shape[0]
        possible = b2b * skus
        report["sell_out_coverage"] = {"observed_pairs": int(observed), "possible_pairs": int(possible), "coverage": observed / possible if possible else None, "missing_data_is_not_zero": True}
    return report


def validate_sheets(data: dict[str, pd.DataFrame], sheets: Iterable[str], *, header_rows: dict[str, int] | None = None,
                    max_examples: int = 5) -> list[dict]:
    """Regras por linha só das abas pedidas (upload parcial): sem MISSING_SHEET e sem chave estrangeira."""
    header_rows = header_rows or {}
    issues: list[dict] = []
    for sheet in sheets:
        if sheet not in SCHEMAS or data.get(sheet) is None:
            continue
        _, errors, warnings = _check_sheet(sheet, data[sheet], header_rows.get(sheet, DEFAULT_HEADER_ROW), max_examples)
        issues.extend(errors)
        issues.extend(warnings)
    return issues
