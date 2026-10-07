from __future__ import annotations
from typing import Any

import pandas as pd

# Etapa 15.2: a cobertura passa a usar a demanda de referência (previsão oficial dos 3 próximos meses), não o campo
# cadastrado `Produtos.Venda média/dia`, que fica abaixo do vendido em boa parte dos SKUs.
DEMAND_SETTINGS = {"days_per_month": 30.4, "registered_demand_divergence": 0.20}
DEMAND_SOURCES = {
    "previsao_3m": "média da previsão oficial dos 3 próximos meses",
    "vendas_3m": "média de Vendas_24m nos 3 últimos meses",
    "cadastro": "Produtos.Venda média/dia (cadastro)",
}
REFERENCE_MONTHS = 3


def _sum_by_sku(frame: pd.DataFrame, source_column: str, output_column: str) -> pd.DataFrame:
    return frame.groupby("SKU", as_index=False)[source_column].sum().rename(columns={source_column: output_column})


def build_capacity_indicators(capacity: pd.DataFrame) -> pd.DataFrame:
    """Resume a capacidade por família; a primeira semana é uma referência, não uma alocação de OP."""
    ordered = capacity.sort_values(["Família", "Semana inicial"])
    first = ordered.groupby("Família", as_index=False).first()
    average = ordered.groupby("Família", as_index=False).agg(
        capacity_occupation_average=("Ocupação", "mean"),
        capacity_available_average=("Capacidade disponível", "mean"),
        capacity_weeks=("Semana inicial", "size"),
    )
    first = first[["Família", "Semana inicial", "Capacidade máxima", "Capacidade comprometida", "Capacidade disponível", "Ocupação"]].rename(columns={
        "Semana inicial": "capacity_reference_week", "Capacidade máxima": "capacity_maximum_reference_week",
        "Capacidade comprometida": "capacity_committed_reference_week", "Capacidade disponível": "capacity_available_reference_week",
        "Ocupação": "capacity_occupation_reference_week",
    })
    return first.merge(average, on="Família", validate="one_to_one")


def _critical_date(row: pd.Series) -> tuple[pd.Timestamp | None, str | None]:
    """Select the earliest available operational date and identify its source."""
    promised = row["first_promised_date"]
    completion = row["first_production_completion"]
    if pd.notna(promised) and (pd.isna(completion) or promised <= completion):
        return promised, "first_promised_date"
    if pd.notna(completion):
        return completion, "first_production_completion"
    return None, None


def _forecast_daily(forecasts: pd.DataFrame | None, days: float) -> dict[str, float]:
    if forecasts is None or forecasts.empty:
        return {}
    result = {}
    for row in forecasts.to_dict("records"):
        values = list(row.get("forecast_values") or [])[:REFERENCE_MONTHS]
        if row.get("status") == "ok" and len(values) == REFERENCE_MONTHS and sum(values) > 0:
            result[str(row["sku"])] = sum(values) / REFERENCE_MONTHS / days
    return result


def _sales_daily(sales: pd.DataFrame | None, days: float) -> dict[str, float]:
    if sales is None or sales.empty:
        return {}
    months = pd.to_datetime(sales["Mês"]).dt.to_period("M")
    recent = months >= months.max() - (REFERENCE_MONTHS - 1)
    totals = sales.loc[recent].groupby("SKU")["Quantidade faturada"].sum()
    return {str(sku): float(total) / REFERENCE_MONTHS / days for sku, total in totals.items() if total > 0}


def reference_demand(base: pd.DataFrame, data: dict[str, pd.DataFrame], forecasts: pd.DataFrame | None, settings: dict[str, Any]) -> pd.DataFrame:
    """Demanda diária de referência por SKU: previsão oficial → vendas recentes → cadastro, com a fonte declarada."""
    days = float(settings["days_per_month"])
    forecast, sales = _forecast_daily(forecasts, days), _sales_daily(data.get("Vendas_24m"), days)
    values, sources = [], []
    for sku, registered in zip(base["SKU"], base["average_sales_per_day"]):
        for source, value in (("previsao_3m", forecast.get(sku)), ("vendas_3m", sales.get(sku)), ("cadastro", registered)):
            if value is not None and pd.notna(value) and value > 0:
                values.append(float(value))
                sources.append(source)
                break
        else:
            values.append(None)
            sources.append(None)
    return pd.DataFrame({"reference_daily_demand": values, "demand_source": sources}, index=base.index)


def registered_demand_warning(indicators: pd.DataFrame, threshold: float) -> dict[str, Any] | None:
    """Aviso de qualidade: SKUs cuja venda média cadastrada difere da demanda de referência acima do limite."""
    rows = indicators[indicators["data_quality_warnings"].map(lambda codes: "REGISTERED_DEMAND_DIVERGENCE" in codes)]
    if rows.empty:
        return None
    items = [{
        "sku": row["SKU"], "registered_daily_demand": round(float(row["average_sales_per_day"]), 2),
        "reference_daily_demand": round(float(row["reference_daily_demand"]), 2),
        "ratio": round(float(row["registered_vs_reference_ratio"]), 3), "demand_source": row["demand_source"],
        "coverage_days_registered": None if pd.isna(row["coverage_days_registered"]) else round(float(row["coverage_days_registered"]), 1),
        "coverage_days_calculated": None if pd.isna(row["coverage_days_calculated"]) else round(float(row["coverage_days_calculated"]), 1),
    } for _, row in rows.sort_values("registered_vs_reference_ratio", ascending=False).iterrows()]
    return {
        "code": "REGISTERED_DEMAND_DIVERGENCE", "sheet": "Produtos", "column": "Venda média/dia", "threshold": threshold,
        "count": len(items), "items": items,
        "description": "A venda média cadastrada difere da demanda de referência (previsão oficial) em mais que o limite; a cobertura usa a demanda de referência.",
    }


def _missing_data(row: pd.Series) -> list[str]:
    fields = (
        "first_promised_date",
        "first_production_completion",
        "sell_in_quantity",
        "sell_out_quantity",
        "forecast_quantity",
    )
    return [field for field in fields if pd.isna(row[field])]


def build_sku_indicators(data: dict[str, pd.DataFrame], forecasts: pd.DataFrame | None = None, settings: dict[str, Any] | None = None) -> pd.DataFrame:
    """Produz uma visão por SKU para consumo das etapas seguintes, sem classificar prioridade.

    Com `forecasts`, a cobertura usa a demanda de referência (Etapa 15.2); sem ela, as vendas recentes e, por último, o
    cadastro. `coverage_days_registered` guarda a conta antiga para comparação.
    """
    settings = {**DEMAND_SETTINGS, **(settings or {})}
    products = data["Produtos"].copy()
    stock = data["Estoque_Atual"][["SKU", "Estoque atual", "Cobertura dias", "Estoque segurança dias"]].copy()
    base = products[["SKU", "Produto", "Família", "Curva ABC", "Status", "Lead time (dias)", "Lote mínimo", "Venda média/dia"]].merge(stock, on="SKU", validate="one_to_one")
    base = base.rename(columns={
        "Família": "family", "Curva ABC": "abc_curve", "Lead time (dias)": "lead_time_days", "Lote mínimo": "minimum_lot",
        "Venda média/dia": "average_sales_per_day", "Estoque atual": "current_stock", "Cobertura dias": "coverage_days_source",
        "Estoque segurança dias": "safety_stock_days",
    })
    base = base.join(reference_demand(base, data, forecasts, settings))
    base["coverage_days_registered"] = base["current_stock"] / base["average_sales_per_day"]
    base["coverage_days_calculated"] = base["current_stock"] / base["reference_daily_demand"]
    base["coverage_days_difference"] = base["coverage_days_source"] - base["coverage_days_calculated"]
    base["registered_vs_reference_ratio"] = base["reference_daily_demand"] / base["average_sales_per_day"]
    limit = float(settings["registered_demand_divergence"])
    base["data_quality_warnings"] = [
        ["REGISTERED_DEMAND_DIVERGENCE"] if pd.notna(ratio) and abs(ratio - 1) > limit else []
        for ratio in base["registered_vs_reference_ratio"]
    ]

    orders = data["Ordens_Producao"]
    order_totals = _sum_by_sku(orders, "Quantidade", "production_order_quantity")
    first_completion = orders.groupby("SKU", as_index=False)["Conclusão prevista"].min().rename(columns={"Conclusão prevista": "first_production_completion"})
    backlog = data["Carteira_Pedidos"]
    backlog_totals = _sum_by_sku(backlog, "Quantidade", "backlog_order_quantity")
    first_promise = backlog.groupby("SKU", as_index=False)["Data prometida"].min().rename(columns={"Data prometida": "first_promised_date"})
    sell_in = _sum_by_sku(data["Sell_In"], "Quantidade enviada", "sell_in_quantity")
    sell_out = _sum_by_sku(data["Sell_Out"], "Quantidade vendida", "sell_out_quantity")
    visibility = data["Sell_Out"].groupby("SKU", as_index=False)["Cliente"].nunique().rename(columns={"Cliente": "sell_out_partner_count"})
    forecast = _sum_by_sku(data["Forecast_Comercial"], "Previsão unidades", "forecast_quantity")
    capacity = build_capacity_indicators(data["Capacidade_Semanal"])

    for table in (order_totals, first_completion, backlog_totals, first_promise, sell_in, sell_out, visibility, forecast):
        base = base.merge(table, on="SKU", how="left", validate="one_to_one")
    base = base.merge(capacity, left_on="family", right_on="Família", how="left", validate="many_to_one").drop(columns="Família")
    # Ausência em tabelas de documentos abertos significa que não há quantidade
    # aberta. Já sell-in, sell-out e forecast ausentes permanecem nulos: ausência
    # de observação não pode ser apresentada como quantidade zero.
    zero_fill = ["production_order_quantity", "backlog_order_quantity", "sell_out_partner_count"]
    base[zero_fill] = base[zero_fill].fillna(0)
    base["projected_stock_quantity"] = base["current_stock"] + base["production_order_quantity"] - base["backlog_order_quantity"]
    base["operational_gap_quantity"] = (
        base["backlog_order_quantity"] - base["current_stock"] - base["production_order_quantity"]
    ).clip(lower=0)
    base["sell_in_minus_sell_out_quantity"] = base["sell_in_quantity"] - base["sell_out_quantity"]
    base["has_sell_out"] = base["sell_out_partner_count"] > 0
    base["sell_out_visibility"] = base["has_sell_out"].map({True: "parcial observada", False: "não disponível"})
    critical = base.apply(_critical_date, axis=1, result_type="expand")
    base[["critical_date", "critical_date_reason"]] = critical
    base["analysis_scope"] = "SKU global"
    base["missing_data"] = base.apply(_missing_data, axis=1)
    return base.sort_values("SKU").reset_index(drop=True)
