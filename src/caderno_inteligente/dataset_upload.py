"""Prévia e preparação do upload da planilha pela tela (U.1): nada aqui grava no banco.

`prepare_upload` confere o arquivo, lê as abas enviadas, valida com endereço, mescla com a base ativa (D1), confere a
coerência com a data de planejamento (D3–D5), calcula o efeito no motor e devolve a prévia (C6) com o conjunto mesclado,
pronto para `DatasetStore.apply_version`, só quando não há erro. Dado ausente nunca vira zero e toda prévia exige revisão humana.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Callable

import pandas as pd

from .dataset_merge import POLICIES, POLICY_TEXT, merge_upload
from .dataset_store import SKU_SHEETS, encode_frame, normalise_sku
from .ingestion import read_workbook_bytes
from .reference import REFERENCE_AUTO, ReferenceDateError, resolve_supply_settings, series_last_months, validate_coherence
from .transformations import safe_normalise
from .upload_safety import check_upload
from .validation import validate_dataset, validate_sheets

LIMITATIONS = [
    "A prévia não grava nada; aplicar substitui a base para todos os usuários.",
    "As janelas fixas de avaliação da previsão e da projeção no parceiro (forecast_engine.json, partner_projection.json) não mudam com a base nova (D11).",
    "Os casos congelados da validação continuam sendo os da base original; com a base nova, os casos de origem 'base' aparecem como base anterior (D8).",
    "O efeito no motor é uma estimativa do pipeline sobre o conjunto mesclado; confira as recomendações antes de agir.",
]
ENGINE_SKIPPED = "Não calculado: a planilha tem erros que bloqueiam a aplicação."
ENGINE_FAILED = "O motor não conseguiu calcular com a base nova; nada foi gravado."


def _issue(code: str, severity: str, message: str, *, sheet: str | None = None, column: str | None = None, count: int = 1,
           examples: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Problema no formato C2 para regras de arquivo e de aba inteira (sem linha nem célula)."""
    examples = examples or []
    first = examples[0] if examples else {}
    return {"code": code, "severity": severity, "sheet": sheet, "column": column, "message": message, "count": count,
            "examples": examples, "more": max(count - len(examples), 0),
            "row": first.get("row"), "cell": first.get("cell"), "value": first.get("value")}


def _error_key(error: dict) -> tuple:
    """Mesmo critério de backend/registry.py: um erro que já existe na base atual não bloqueia o upload."""
    return (error.get("code"), error.get("sheet") or error.get("child_sheet"), error.get("column") or error.get("child_column"))


def _issue_key(issue: dict) -> tuple:
    return issue.get("code"), issue.get("sheet"), issue.get("column")


def _without_address(issue: dict) -> dict:
    """Nas abas mensais a posição no conjunto mesclado não é a linha do arquivo: fica só a chave e o valor."""
    examples = [{**example, "row": None, "cell": None} for example in issue.get("examples", [])]
    return {**issue, "examples": examples, "row": None, "cell": None}


def drop_skus(dataset: dict[str, pd.DataFrame], skus: set[str]) -> dict[str, pd.DataFrame]:
    """O conjunto como o motor o vê: sem as linhas dos SKUs inativos (mesmo filtro de `DatasetStore.load_dataset`)."""
    if not skus:
        return dict(dataset)
    return {sheet: frame[~frame["SKU"].map(normalise_sku).isin(skus)].reset_index(drop=True) if "SKU" in frame else frame
            for sheet, frame in dataset.items()}


def engine_reference(normalised: dict[str, pd.DataFrame] | None, supply_settings: dict[str, Any] | None = None) -> dict[str, str | None]:
    """A referência que o motor usará com este conjunto normalizado: `resolve_supply_settings` sobre config/supply_plan.json.

    Devolve {"reference_date" (ISO), "reference_source" ("auto"/"config"), "sales_last_month"}; None quando não dá para derivar.
    Sem `supply_settings`, vale "auto" (primeira semana de Capacidade_Semanal).
    """
    if normalised is None:
        return {"reference_date": None, "reference_source": None, "sales_last_month": None}
    sales = series_last_months(normalised)["Vendas_24m"]
    try:
        resolved = resolve_supply_settings(supply_settings or {"reference_date": REFERENCE_AUTO}, normalised)
    except ReferenceDateError:
        return {"reference_date": None, "reference_source": REFERENCE_AUTO, "sales_last_month": sales}
    return {"reference_date": resolved["reference_date"], "reference_source": resolved["reference_source"], "sales_last_month": sales}


def reference_of(normalised: dict[str, pd.DataFrame] | None, supply_settings: dict[str, Any] | None = None) -> tuple[str | None, str | None]:
    """(data de planejamento ISO, último mês de vendas) de um conjunto normalizado; None quando não dá para derivar."""
    found = engine_reference(normalised, supply_settings)
    return found["reference_date"], found["sales_last_month"]


def _number_message(issue: dict) -> str:
    """INVALID_NUMBER agregado com o primeiro endereço: "Vendas_24m!D10: 'abc' não é número; e mais N"."""
    where = f"{issue['sheet']}!{issue['cell']}" if issue.get("cell") else issue.get("sheet") or "planilha"
    first = next(iter(issue.get("examples") or []), {})
    if not issue.get("cell") and first.get("key"):
        where += f" ({first['key']})"
    if not issue.get("cell") and issue.get("column"):
        where += f", coluna {issue['column']}"
    value = issue.get("value") if issue.get("value") is not None else first.get("value")
    message = f"{where}: '{value}' não é número" if value is not None else f"{where}: valor não é número"
    extra = int(issue.get("count") or 1) - 1
    return message + (f"; e mais {extra}" if extra > 0 else "")


def inactive_removed(merged: dict[str, pd.DataFrame], inactive: set[str], sent: set[str]) -> list[str]:
    """SKUs inativos que deixam de existir em Produtos com o upload (o cadastro e a inativação somem junto)."""
    products = merged.get("Produtos")
    if "Produtos" not in sent or not inactive or products is None or "SKU" not in products:
        return []
    return sorted(set(inactive) - set(products["SKU"].map(normalise_sku)))


def _rows_by_sku(frame: pd.DataFrame | None) -> dict[str, list[dict[str, Any]]]:
    if frame is None or "SKU" not in frame:
        return {}
    _, rows = encode_frame(frame)
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(normalise_sku(row.get("SKU")) or "", []).append(row)
    return grouped


def registry_overrides(current: dict[str, pd.DataFrame], merged: dict[str, pd.DataFrame], sent: set[str], edited: set[str]) -> list[str]:
    """SKUs cadastrados pela tela cuja linha em Produtos, Lead_Times ou Estoque_Atual muda com o upload (D10)."""
    if not edited:
        return []
    changed: set[str] = set()
    for sheet in SKU_SHEETS:
        if sheet not in sent:
            continue
        before, after = _rows_by_sku(current.get(sheet)), _rows_by_sku(merged.get(sheet))
        changed |= {sku for sku in edited if before.get(sku) != after.get(sku)}
    return sorted(changed)


def prepare_upload(content: bytes, filename: str, *, current: dict[str, pd.DataFrame], state: dict[str, Any], settings: dict[str, Any],
                   engine: Callable[[dict[str, pd.DataFrame]], dict[str, Any]], current_engine: dict[str, Any] | None,
                   edited_skus: set[str], inactive_skus: set[str] | None = None,
                   describe_error: Callable[[str, Exception], str] | None = None,
                   supply_settings: dict[str, Any] | None = None) -> tuple[dict[str, Any], dict[str, pd.DataFrame] | None]:
    """(prévia, conjunto mesclado ou None). Nada é gravado.

    `current` = base ativa com os SKUs inativos (`load_dataset(include_inactive=True)`); `state` = {"version", "reference_date",
    "sales_last_month"} da base ativa; `settings` = config/dataset_upload.json; `supply_settings` = config/supply_plan.json (a
    referência da prévia é a mesma que o motor usará: data fixa ali vence a primeira semana). `UploadRejected` (413/422) sobe.
    """
    file_info = check_upload(content, filename, settings)
    max_examples = settings["max_examples_per_error"]
    read = read_workbook_bytes(content, search_rows=settings["header_search_rows"])
    uploaded, header_rows = read["sheets"], read["header_rows"]
    sent = set(uploaded)
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    for sheet, columns in read["missing_header"].items():
        errors.append(_issue("MISSING_COLUMNS", "error", f"{sheet}: cabeçalho não encontrado nas {settings['header_search_rows']} primeiras linhas; "
                             f"faltam as colunas {', '.join(columns)}", sheet=sheet, column=", ".join(columns), count=len(columns)))
    for sheet, frame in uploaded.items():
        if len(frame) > settings["max_rows_per_sheet"]:
            errors.append(_issue("TOO_MANY_ROWS", "error", f"{sheet} tem {len(frame)} linhas; o limite é {settings['max_rows_per_sheet']} por aba",
                                 sheet=sheet, count=len(frame)))
    if not uploaded and not read["missing_header"]:
        errors.append(_issue("NO_KNOWN_SHEETS", "error", "A planilha não tem nenhuma das abas da base (por exemplo Vendas_24m ou Capacidade_Semanal)"))

    # Regras por linha nas abas enviadas, com o endereço do arquivo enviado.
    for item in validate_sheets(uploaded, sorted(sent), header_rows=header_rows, max_examples=max_examples):
        (errors if item["severity"] == "error" else warnings).append(item)

    merged, reports, merge_issues = merge_upload(current, uploaded)
    for report in reports:
        report["header_row"] = header_rows.get(report["sheet"])
    reported = {(item["code"], item["sheet"]) for item in errors}
    for item in merge_issues:
        if item["severity"] == "error" and (item["code"], item["sheet"]) in reported:
            continue
        (errors if item["severity"] == "error" else warnings).append(item)

    # Base inteira depois da mescla: só os erros novos (chave estrangeira, sobretudo); os por linha das abas enviadas já saíram acima.
    addressed = {sheet: row for sheet, row in header_rows.items() if POLICIES.get(sheet) != "serie_mensal"}
    baseline = {_error_key(item) for item in validate_dataset(current)["errors"]}
    for item in validate_dataset(merged, header_rows=addressed, max_examples=max_examples)["errors"]:
        if _error_key(item) in baseline or (item["code"] != "ORPHAN_KEY" and item.get("sheet") in sent):
            continue
        errors.append(_without_address(item) if POLICIES.get(item.get("sheet")) == "serie_mensal" else item)

    normalised, normalise_issues = safe_normalise(merged, header_rows=addressed, max_examples=max_examples)
    seen = {_issue_key(item) for item in errors}
    errors.extend(item for item in normalise_issues if _issue_key(item) not in seen)
    resolved = engine_reference(normalised, supply_settings)
    reference_after, sales_after = resolved["reference_date"], resolved["sales_last_month"]
    if normalised is not None:
        previous = {"reference_date": state.get("reference_date"), "sales_last_month": state.get("sales_last_month")}
        coherence = validate_coherence(normalised, date.fromisoformat(reference_after) if reference_after else None,
                                       previous if previous["reference_date"] else None, sent_sheets=sent,
                                       reference_source=resolved["reference_source"] or REFERENCE_AUTO)
        errors.extend(coherence["errors"])
        warnings.extend(coherence["warnings"])
    errors = [{**item, "message": _number_message(item)} if item.get("code") == "INVALID_NUMBER" else item for item in errors]

    if read["example_marker"]:
        warnings.append(_issue("EXAMPLE_FILE", "warning", "Este é um arquivo de exemplo fictício: não use os números para decidir.", sheet="LEIA_ME"))
    if file_info["has_macro"]:
        warnings.append(_issue("MACRO_IGNORED", "warning", "A planilha tem macros; elas foram ignoradas (só os dados das abas são lidos)."))
    overrides = registry_overrides(current, merged, sent, set(edited_skus))
    if overrides:
        warnings.append(_issue("REGISTRY_OVERRIDE", "warning",
                               f"O upload sobrescreve o cadastro feito pela tela em {len(overrides)} SKUs",
                               sheet="Produtos", column="SKU", count=len(overrides),
                               examples=[{"row": None, "cell": None, "key": sku, "value": None} for sku in overrides[:max_examples]]))

    removed = inactive_removed(merged, set(inactive_skus or ()), sent)
    if removed:
        warnings.append(_issue("INACTIVE_SKU_REMOVED", "warning",
                               f"{len(removed)} SKUs inativos não estão na aba Produtos enviada e deixam de existir na base",
                               sheet="Produtos", column="SKU", count=len(removed),
                               examples=[{"row": None, "cell": None, "key": sku, "value": None} for sku in removed[:max_examples]]))

    after, engine_error = None, ENGINE_SKIPPED
    if not errors:
        try:
            after, engine_error = engine(drop_skus(merged, set(inactive_skus or ()))), None
        except Exception as error:  # noqa: BLE001 - qualquer falha do motor vira erro público na prévia, nunca 500.
            message = describe_error(ENGINE_FAILED, error) if describe_error else ENGINE_FAILED
            errors.append(_issue("ENGINE_FAILED", "error", message))
            engine_error = message

    before_reference = state.get("reference_date")
    preview = {
        "file": {"filename": file_info["filename"], "size_bytes": file_info["size_bytes"], "sha256": file_info["sha256"],
                 "extension": file_info["extension"], "has_macro": file_info["has_macro"], "example": bool(read["example_marker"])},
        "expected_version": int(state.get("version") or 0),
        "can_apply": not errors,
        "policy": POLICY_TEXT,
        "sheets": reports,
        "ignored_sheets": read["ignored_sheets"],
        "errors": errors,
        "warnings": warnings,
        "reference": {"before": before_reference, "after": reference_after,
                      "advanced": bool(before_reference and reference_after and date.fromisoformat(reference_after) > date.fromisoformat(str(before_reference)[:10])),
                      "sales_last_month_before": state.get("sales_last_month"), "sales_last_month_after": sales_after},
        "registry_overrides": {"count": len(overrides), "skus": overrides},
        "engine": {"before": current_engine, "after": after, "error": engine_error},
        "requires_human_review": True,
        "limitations": list(LIMITATIONS),
    }
    return preview, (merged if not errors else None)
