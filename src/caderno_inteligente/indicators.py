from __future__ import annotations
import pandas as pd


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


def _missing_data(row: pd.Series) -> list[str]:
    fields = (
        "first_promised_date",
        "first_production_completion",
        "sell_in_quantity",
        "sell_out_quantity",
        "forecast_quantity",
    )
    return [field for field in fields if pd.isna(row[field])]


def build_sku_indicators(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Produz uma visão por SKU para consumo das etapas seguintes, sem classificar prioridade."""
    products = data["Produtos"].copy()
    stock = data["Estoque_Atual"][["SKU", "Estoque atual", "Cobertura dias", "Estoque segurança dias"]].copy()
    base = products[["SKU", "Produto", "Família", "Curva ABC", "Status", "Lead time (dias)", "Lote mínimo", "Venda média/dia"]].merge(stock, on="SKU", validate="one_to_one")
    base = base.rename(columns={
        "Família": "family", "Curva ABC": "abc_curve", "Lead time (dias)": "lead_time_days", "Lote mínimo": "minimum_lot",
        "Venda média/dia": "average_sales_per_day", "Estoque atual": "current_stock", "Cobertura dias": "coverage_days_source",
        "Estoque segurança dias": "safety_stock_days",
    })
    base["coverage_days_calculated"] = base["current_stock"] / base["average_sales_per_day"]
    base["coverage_days_difference"] = base["coverage_days_source"] - base["coverage_days_calculated"]

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
