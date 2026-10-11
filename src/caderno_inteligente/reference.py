"""Data de planejamento derivada dos dados (upload da planilha, U.0) e regras de coerência entre as abas.

A data de planejamento é a primeira `Semana inicial` de `Capacidade_Semanal` (decisão D3, `docs/decisions.md:146`) e vale
para todo o motor: plano de suprimento, capacidade, alocação, eventos, `decide_by` e "Decisões de hoje". O fim do último
mês de vendas fica só como `sales_last_month`. `config/supply_plan.json` aceita `"reference_date": "auto"` (padrão) ou
uma data explícita, que continua valendo como sobrescrita.

As regras de coerência bloqueiam um upload que deixaria o motor com duas "datas de hoje" ou com dupla contagem:
séries mensais só com meses fechados (D4), referência que acompanha as vendas, fotografias obrigatórias quando a
referência avança (D5) e OP aberta com conclusão antes da referência. Os avisos não bloqueiam.
"""
from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd

from .supply_plan import CLOSED_ORDER_STATUSES

REFERENCE_AUTO = "auto"
SNAPSHOT_SHEETS = ("Estoque_Atual", "Carteira_Pedidos", "Ordens_Producao", "Capacidade_Semanal")
SERIES_SHEETS = ("Vendas_24m", "Sell_In", "Sell_Out")
MAX_EXAMPLES = 5

_MONTHS = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")
_SERIES_SUBJECT = {"Vendas_24m": "Vendas vão", "Sell_In": "Sell_In vai", "Sell_Out": "Sell_Out vai"}


class ReferenceDateError(ValueError):
    """Referência que não pode ser derivada; `code` é REFERENCE_MISSING ou REFERENCE_NOT_MONDAY."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _br_date(value: date) -> str:
    return f"{value.day:02d}/{value.month:02d}/{value.year}"


def _br_month(period: pd.Period) -> str:
    return f"{_MONTHS[period.month - 1]}/{period.year % 100:02d}"


def _dates(frame: pd.DataFrame | None, column: str) -> pd.Series:
    if frame is None or column not in frame:
        return pd.Series(dtype="datetime64[ns]")
    return pd.to_datetime(frame[column], errors="coerce")


def derive_reference_date(dataset: dict[str, pd.DataFrame]) -> date:
    """Primeira `Semana inicial` de `Capacidade_Semanal` (conjunto já normalizado); precisa ser segunda-feira."""
    weeks = _dates(dataset.get("Capacidade_Semanal"), "Semana inicial").dropna()
    if weeks.empty:
        raise ReferenceDateError("REFERENCE_MISSING", "Capacidade_Semanal não tem semana válida; a data de planejamento sai da primeira semana")
    first = weeks.min().date()
    if first.weekday() != 0:
        raise ReferenceDateError("REFERENCE_NOT_MONDAY", f"A primeira semana de Capacidade_Semanal ({_br_date(first)}) precisa ser uma segunda-feira")
    return first


def resolve_supply_settings(settings: dict[str, Any], dataset: dict[str, pd.DataFrame]) -> dict[str, Any]:
    """Cópia das configurações do plano com `"auto"` trocado pela data derivada (ISO) e `reference_source`."""
    resolved = dict(settings)
    if str(resolved.get("reference_date")) == REFERENCE_AUTO:
        resolved["reference_date"] = derive_reference_date(dataset).isoformat()
        resolved["reference_source"] = "auto"
    else:
        resolved.setdefault("reference_source", "config")
    return resolved


def _last_month(dataset: dict[str, pd.DataFrame], sheet: str) -> pd.Period | None:
    months = _dates(dataset.get(sheet), "Mês").dropna()
    return None if months.empty else months.max().to_period("M")


def series_last_months(dataset: dict[str, pd.DataFrame]) -> dict[str, str | None]:
    """Último mês de cada série mensal (AAAA-MM), ou None quando a aba falta ou não tem mês válido."""
    return {sheet: None if (month := _last_month(dataset, sheet)) is None else str(month) for sheet in SERIES_SHEETS}


def reference_info(dataset: dict[str, pd.DataFrame], settings: dict[str, Any]) -> dict[str, Any]:
    """Resumo para a tela: referência, de onde ela veio e até onde vão as séries."""
    resolved = resolve_supply_settings(settings, dataset)
    months = series_last_months(dataset)
    return {
        "reference_date": resolved["reference_date"], "reference_source": resolved["reference_source"],
        "sales_last_month": months["Vendas_24m"], "series_last_months": months,
    }


def _issue(code: str, severity: str, message: str, *, sheet: str | None = None, column: str | None = None,
           examples: list[dict[str, Any]] | None = None, count: int | None = None) -> dict[str, Any]:
    examples = examples or []
    shown = examples[:MAX_EXAMPLES]
    total = len(examples) if count is None else count
    total = max(total, 1)
    first = shown[0] if shown else {}
    return {
        "code": code, "severity": severity, "sheet": sheet, "column": column, "message": message, "count": total,
        "examples": shown, "more": total - len(shown),
        "row": first.get("row"), "cell": first.get("cell"), "value": first.get("value"),
    }


def _example(key: str | None = None, value: str | None = None) -> dict[str, Any]:
    return {"row": None, "cell": None, "key": key, "value": value}


def _not_closed_message(sheet: str, last: pd.Period, reference: date) -> str:
    return (f"{_SERIES_SUBJECT[sheet]} até {_br_month(last)}, mas a data de planejamento é {_br_date(reference)}; "
            "envie Capacidade_Semanal, Estoque_Atual, Carteira_Pedidos e Ordens_Producao atualizadas")


def _fixed_message(sheet: str, last: pd.Period, reference: date) -> str:
    return (f"{_SERIES_SUBJECT[sheet]} até {_br_month(last)}, mas a data de planejamento está fixa em {_br_date(reference)} em "
            "config/supply_plan.json; troque reference_date para \"auto\" (ou para a nova segunda-feira) antes de aplicar")


def _not_advanced_message(previous_sales: pd.Period, sales_last: pd.Period, reference: date) -> str:
    return (f"As vendas avançaram de {_br_month(previous_sales)} para {_br_month(sales_last)}, mas a data de planejamento não avançou "
            f"junto com as vendas (continua {_br_date(reference)}); envie Capacidade_Semanal, Estoque_Atual, Carteira_Pedidos e "
            "Ordens_Producao atualizadas")


def _open_rows(frame: pd.DataFrame | None) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame()
    if "Status" not in frame:
        return frame
    return frame[~frame["Status"].astype(str).str.strip().str.casefold().isin(CLOSED_ORDER_STATUSES)]


def validate_coherence(dataset: dict[str, pd.DataFrame], reference: date | None, previous: dict[str, Any] | None = None, *,
                       sent_sheets: set[str] | None = None, reference_source: str = REFERENCE_AUTO) -> dict[str, list[dict[str, Any]]]:
    """Regras de coerência entre a referência e as abas (conjunto normalizado).

    `previous` = {"reference_date", "sales_last_month"} da base ativa; `sent_sheets` = abas presentes no upload (None fora dele).
    Sem `reference`, ela é derivada aqui e os problemas de derivação viram erro. `reference_source="config"` = data fixa em
    config/supply_plan.json (a mesma que o motor usa): série além dela bloqueia com REFERENCE_FIXED_IN_CONFIG, porque enviar
    as fotografias não muda a referência.
    """
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    if reference is None:
        try:
            reference = derive_reference_date(dataset)
        except ReferenceDateError as error:
            errors.append(_issue(error.code, "error", error.message, sheet="Capacidade_Semanal", column="Semana inicial"))
            return {"errors": errors, "warnings": warnings}
    reference_month = pd.Period(reference, freq="M")
    fixed = reference_source == "config"
    if fixed:
        warnings.append(_issue("REFERENCE_FROM_CONFIG", "warning",
                               f"A data de planejamento está fixa em {_br_date(reference)} em config/supply_plan.json; a primeira semana "
                               "de Capacidade_Semanal não muda a referência do motor", examples=[_example(value=reference.isoformat())]))

    # D4: só meses fechados nas séries mensais.
    lasts = {sheet: _last_month(dataset, sheet) for sheet in SERIES_SHEETS}
    for sheet, last in lasts.items():
        if last is None:
            continue
        code = "SERIES_NOT_CLOSED"
        if last >= reference_month and fixed:
            code, message = "REFERENCE_FIXED_IN_CONFIG", _fixed_message(sheet, last, reference)
        elif last > reference_month:
            message = _not_closed_message(sheet, last, reference)
        elif last == reference_month:
            message = (f"{_br_month(last)} ainda não fechou: as abas mensais aceitam só meses anteriores ao da data de planejamento "
                       f"({_br_date(reference)})")
        else:
            continue
        errors.append(_issue(code, "error", message, sheet=sheet, column="Mês", examples=[_example(value=str(last))]))

    sales_last = lasts["Vendas_24m"]
    if previous:
        previous_reference = date.fromisoformat(str(previous["reference_date"])[:10]) if previous.get("reference_date") else None
        previous_sales = pd.Period(str(previous["sales_last_month"])[:7], freq="M") if previous.get("sales_last_month") else None
        # Com SERIES_NOT_CLOSED em Vendas_24m (ou data fixa no config) a causa já foi dita: sem mensagem repetida.
        sales_flagged = fixed or any(item["sheet"] == "Vendas_24m" for item in errors)
        if (sales_last is not None and previous_sales is not None and previous_reference is not None and not sales_flagged
                and sales_last > previous_sales and reference <= previous_reference):
            errors.append(_issue("REFERENCE_NOT_ADVANCED", "error", _not_advanced_message(previous_sales, sales_last, reference),
                                 sheet="Capacidade_Semanal", column="Semana inicial", examples=[_example(value=reference.isoformat())]))
        # D5: com a referência nova, as quatro fotografias precisam vir no mesmo envio.
        if sent_sheets is not None and previous_reference is not None and reference > previous_reference:
            missing = [sheet for sheet in SNAPSHOT_SHEETS if sheet not in sent_sheets]
            if missing:
                errors.append(_issue(
                    "SNAPSHOTS_REQUIRED", "error",
                    f"A data de planejamento avançou de {_br_date(previous_reference)} para {_br_date(reference)}; envie também: {', '.join(missing)}",
                    examples=[_example(key=sheet) for sheet in missing], count=len(missing),
                ))

    # OP aberta que já deveria ter terminado seria somada de novo ao estoque (recebimento no dia da referência).
    ops = _open_rows(dataset.get("Ordens_Producao"))
    if not ops.empty and "Conclusão prevista" in ops:
        finish = _dates(ops, "Conclusão prevista")
        mask = finish < pd.Timestamp(reference)  # NaT nunca é anterior
        late = ops[mask].assign(_finish=finish[mask]).sort_values(["_finish", "Ordem"])
        if not late.empty:
            first = late.iloc[0]
            errors.append(_issue(
                "OPEN_OP_BEFORE_REFERENCE", "error",
                f"{first['Ordem']} ({first.get('Status')}) tem conclusão prevista em {_br_date(first['_finish'].date())}, antes da data de "
                "planejamento; marque como Concluída ou atualize a data",
                sheet="Ordens_Producao", column="Conclusão prevista",
                examples=[_example(str(row["Ordem"]), _br_date(row["_finish"].date())) for _, row in late.iterrows()],
            ))

    orders = _open_rows(dataset.get("Carteira_Pedidos"))
    if not orders.empty and "Data prometida" in orders:
        promised = _dates(orders, "Data prometida")
        mask = promised < pd.Timestamp(reference)
        overdue = orders[mask].assign(_promised=promised[mask]).sort_values(["_promised", "Pedido"])
        if not overdue.empty:
            first = overdue.iloc[0]
            warnings.append(_issue(
                "OVERDUE_ORDER", "warning",
                f"{first['Pedido']} tem data prometida em {_br_date(first['_promised'].date())}, antes da data de planejamento "
                f"({_br_date(reference)}); pedido vencido: confirme se já foi entregue",
                sheet="Carteira_Pedidos", column="Data prometida",
                examples=[_example(str(row["Pedido"]), _br_date(row["_promised"].date())) for _, row in overdue.iterrows()],
            ))

    if sales_last is not None and sales_last < reference_month and (reference_month - sales_last).n > 1:
        warnings.append(_issue(
            "REFERENCE_GAP", "warning",
            f"Há meses sem vendas entre {_br_month(sales_last)} e a data de planejamento ({_br_date(reference)})",
            sheet="Vendas_24m", column="Mês", examples=[_example(value=str(sales_last))],
        ))

    products, stock = dataset.get("Produtos"), dataset.get("Estoque_Atual")
    if products is not None and stock is not None and {"SKU", "Estoque atual"} <= set(products) and {"SKU", "Estoque atual"} <= set(stock):
        merged = (products[["SKU", "Estoque atual"]].astype({"SKU": str})
                  .merge(stock[["SKU", "Estoque atual"]].astype({"SKU": str}), on="SKU", suffixes=("_produtos", "_estoque")))
        left = pd.to_numeric(merged["Estoque atual_produtos"], errors="coerce")
        right = pd.to_numeric(merged["Estoque atual_estoque"], errors="coerce")
        merged = merged.assign(_produtos=left, _estoque=right)
        divergent = merged[left.notna() & right.notna() & (left != right)].sort_values("SKU")
        if not divergent.empty:
            warnings.append(_issue(
                "PRODUCT_STOCK_DIVERGENCE", "warning",
                f"Produtos.Estoque atual difere de Estoque_Atual em {len(divergent)} SKUs; o cálculo usa Estoque_Atual",
                sheet="Produtos", column="Estoque atual",
                examples=[_example(row["SKU"], f"{row['_produtos']:g} × {row['_estoque']:g}") for _, row in divergent.iterrows()],
            ))
    return {"errors": errors, "warnings": warnings}
