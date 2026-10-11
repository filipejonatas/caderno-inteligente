"""Mescla da planilha enviada pela tela com a base ativa (D1: uma regra só).

Cada aba enviada substitui a atual; nas abas mensais (`Vendas_24m`, `Sell_In`, `Sell_Out`), só os meses enviados são
acrescentados ou substituídos. Aba ausente fica como está. A checagem de mês fechado (D4) e de coerência com a data de
planejamento fica em `reference.validate_coherence`, que roda sobre o resultado desta mescla.
"""
from __future__ import annotations

import re
from typing import Any

import pandas as pd

from .dataset_store import SHEET_TABLES
from .schemas import SCHEMAS
from .validation import _parse_dates

POLICIES = {"Vendas_24m": "serie_mensal", "Sell_In": "serie_mensal", "Sell_Out": "serie_mensal",
            "Estoque_Atual": "fotografia", "Carteira_Pedidos": "fotografia", "Ordens_Producao": "fotografia",
            "Capacidade_Semanal": "fotografia", "Forecast_Comercial": "fotografia",
            "Produtos": "cadastro", "Lead_Times": "cadastro", "Parceiros_Canais": "cadastro", "Precos_Produtos": "cadastro", "Calendario_Eventos": "cadastro"}
assert set(POLICIES) == set(SHEET_TABLES)
MONTH_COLUMN = {"Vendas_24m": "Mês", "Sell_In": "Mês", "Sell_Out": "Mês"}
POLICY_TEXT = "Cada aba enviada substitui a atual; nas abas mensais, só os meses enviados são substituídos."

# Abas que podem vir vazias: sem pedido ou sem OP aberta é uma situação real, não erro de preenchimento.
EMPTY_ALLOWED = {"Carteira_Pedidos": "nenhum pedido aberto", "Ordens_Producao": "nenhuma ordem de produção aberta"}
KEY_EXAMPLES = 5
_ISO_MONTH = re.compile(r"^\d{4}-\d{2}$")


def _issue(code: str, severity: str, sheet: str, message: str, *, column: str | None = None, count: int = 1) -> dict[str, Any]:
    """Problema no formato C2; a mescla trata a aba inteira, então não há linha nem célula."""
    return {"code": code, "severity": severity, "sheet": sheet, "column": column, "message": message, "count": count,
            "examples": [], "more": 0, "row": None, "cell": None, "value": None}


def _months(frame: pd.DataFrame, column: str) -> pd.Series:
    return _parse_dates(frame[column]).dt.to_period("M")


def _key_columns(sheet: str) -> tuple[str, ...]:
    schema = SCHEMAS.get(sheet)
    return schema.key_columns if schema else ("SKU",)


def _keys(frame: pd.DataFrame, sheet: str) -> set[str]:
    columns = [column for column in _key_columns(sheet) if column in frame]
    if not columns or frame.empty:
        return set()
    parts = []
    for column in columns:
        if column == MONTH_COLUMN.get(sheet) or column in getattr(SCHEMAS.get(sheet), "date_columns", ()):
            parsed = _parse_dates(frame[column])
            text = parsed.dt.strftime("%Y-%m" if column == MONTH_COLUMN.get(sheet) else "%Y-%m-%d")
            parts.append(text.where(parsed.notna(), frame[column].astype("string")))
        else:
            parts.append(frame[column].astype("string").str.strip())
    joined = parts[0].fillna("")
    for part in parts[1:]:
        joined = joined + " / " + part.fillna("")
    return set(joined.tolist())


def _align_month(uploaded: pd.Series, current: pd.Series, months: pd.Series) -> pd.Series:
    """O mês enviado no formato da base atual: 1º dia do mês (datetime) ou texto AAAA-MM; outro formato fica como veio."""
    if pd.api.types.is_datetime64_any_dtype(current):
        return months.dt.to_timestamp().astype(current.dtype)
    present = current.dropna()
    if len(present) and present.map(lambda value: isinstance(value, str) and bool(_ISO_MONTH.match(value))).all():
        return months.astype("string").astype(object).where(months.notna(), uploaded)
    return uploaded


def _merge_series(sheet: str, current: pd.DataFrame, uploaded: pd.DataFrame) -> tuple[pd.DataFrame, list[str], list[str]]:
    column = MONTH_COLUMN[sheet]
    uploaded = uploaded.reset_index(drop=True)
    sent = _months(uploaded, column)
    existing = _months(current, column)
    sent_set = set(sent.dropna())
    uploaded[column] = _align_month(uploaded[column], current[column], sent)
    uploaded = uploaded.astype(current.dtypes.to_dict(), errors="ignore")
    kept = current[~existing.isin(sent_set)]
    merged = pd.concat([kept, uploaded], ignore_index=True)
    order = pd.concat([existing[~existing.isin(sent_set)], sent], ignore_index=True)
    if existing.dropna().is_monotonic_increasing:
        # Base em ordem de mês: o resultado continua em ordem de mês (ordenação estável).
        merged = merged.iloc[order.sort_values(kind="mergesort", na_position="last").index]
    else:
        # Base em outra ordem (a planilha original vem por SKU): as linhas mantidas ficam como estão e as enviadas vêm depois, por mês.
        merged = pd.concat([merged.iloc[: len(kept)], merged.iloc[len(kept):].iloc[sent.sort_values(kind="mergesort", na_position="last").index]])
    merged = merged.reset_index(drop=True).astype(current.dtypes.to_dict(), errors="ignore")
    before = set(existing.dropna())
    added = sorted(str(month) for month in sent_set - before)
    replaced = sorted(str(month) for month in sent_set & before)
    return merged, added, replaced


def merge_upload(current: dict[str, pd.DataFrame], uploaded: dict[str, pd.DataFrame]) -> tuple[dict[str, pd.DataFrame], list[dict[str, Any]], list[dict[str, Any]]]:
    """(conjunto mesclado, relatório por aba, problemas). Aba com erro fica como a atual; o erro bloqueia a aplicação."""
    merged = dict(current)
    reports: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    for sheet in SHEET_TABLES:
        if sheet not in current and sheet not in uploaded:
            continue
        policy = POLICIES[sheet]
        before = current.get(sheet)
        rows_before = None if before is None else len(before)
        report = {"sheet": sheet, "policy": policy, "status": "mantida", "header_row": None,
                  "rows_before": rows_before, "rows_received": None, "rows_after": rows_before,
                  "months_added": [], "months_replaced": [], "keys_added": 0, "keys_removed": 0,
                  "keys_added_examples": [], "keys_removed_examples": []}
        reports.append(report)
        if sheet not in uploaded:
            continue
        sent = uploaded[sheet]
        report["rows_received"] = len(sent)
        expected = list(before.columns) if before is not None else list(SCHEMAS[sheet].required_columns if sheet in SCHEMAS else sent.columns)
        missing = [column for column in expected if column not in sent.columns]
        if missing:
            issues.append(_issue("MISSING_COLUMNS", "error", sheet, f"{sheet} não tem as colunas: {', '.join(missing)}",
                                 column=", ".join(missing), count=len(missing)))
            continue
        extra = [str(column) for column in sent.columns if column not in expected]
        if extra:
            issues.append(_issue("EXTRA_COLUMNS_IGNORED", "warning", sheet, f"{sheet}: colunas ignoradas: {', '.join(extra)}",
                                 column=", ".join(extra), count=len(extra)))
        sent = sent[expected]
        if sent.empty:
            if sheet not in EMPTY_ALLOWED:
                issues.append(_issue("EMPTY_SHEET", "error", sheet, f"{sheet} veio sem nenhuma linha de dados", count=0))
                continue
            issues.append(_issue("EMPTY_SHEET", "warning", sheet, f"{sheet} veio vazia: {EMPTY_ALLOWED[sheet]}", count=0))
        if policy == "serie_mensal" and before is not None:
            result, report["months_added"], report["months_replaced"] = _merge_series(sheet, before, sent)
            report["status"] = "mesclada"
        else:
            result = sent.reset_index(drop=True)
            report["status"] = "substituida"
        merged[sheet] = result
        report["rows_after"] = len(result)
        old_keys = set() if before is None else _keys(before, sheet)
        new_keys = _keys(result, sheet)
        added, removed = sorted(new_keys - old_keys), sorted(old_keys - new_keys)
        report.update(keys_added=len(added), keys_removed=len(removed),
                      keys_added_examples=added[:KEY_EXAMPLES], keys_removed_examples=removed[:KEY_EXAMPLES])
    return {name: merged[name] for name in SHEET_TABLES if name in merged}, reports, issues
