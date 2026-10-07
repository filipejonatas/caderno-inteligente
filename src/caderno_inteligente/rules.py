from __future__ import annotations
import json
from pathlib import Path
from typing import Any
import pandas as pd

DEFAULT_THRESHOLDS = {"excess_coverage_days": 90, "capacity_occupation_threshold": 0.90, "registered_demand_divergence": 0.20}
DEMAND_ORIGIN = "demanda de referência (previsão oficial dos 3 próximos meses; ver demand_source)"


def load_rule_thresholds(path: str | Path = "config/rule_thresholds.json") -> dict[str, float]:
    values = json.loads(Path(path).read_text(encoding="utf-8"))
    return {**DEFAULT_THRESHOLDS, **values}


def _issue(row: pd.Series, code: str, description: str, severity: str, values: dict[str, Any], origin: list[str]) -> dict[str, Any]:
    return {"sku": row["SKU"], "product": row["Produto"], "family": row["family"], "code": code, "description": description, "severity": severity, "values_used": values, "data_origin": origin}


def _demand(row: pd.Series) -> dict[str, Any]:
    """Demanda usada na cobertura e a fonte; entradas antigas (sem demanda de referência) usam o cadastro."""
    daily = row.get("reference_daily_demand", row.get("average_sales_per_day"))
    return {"daily_demand": daily, "demand_source": row.get("demand_source") or "cadastro"}


def evaluate_rules(indicators: pd.DataFrame, thresholds: dict[str, float] | None = None) -> pd.DataFrame:
    """Avalia riscos determinísticos; não ordena prioridades nem toma decisões de produção."""
    thresholds = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    issues: list[dict[str, Any]] = []
    for _, row in indicators.iterrows():
        demand = _demand(row)
        demand_origin = DEMAND_ORIGIN if "reference_daily_demand" in row else "Produtos.Venda média/dia"
        if row["coverage_days_calculated"] < row["lead_time_days"]:
            issues.append(_issue(row, "RUP_LEAD_TIME", "Cobertura de estoque abaixo do lead time.", "alta", {"coverage_days": row["coverage_days_calculated"], "lead_time_days": row["lead_time_days"], **demand}, ["Estoque_Atual.Estoque atual", demand_origin, "Produtos.Lead time (dias)"]))
        if row["coverage_days_calculated"] < row["safety_stock_days"]:
            issues.append(_issue(row, "RUP_SAFETY_STOCK", "Cobertura de estoque abaixo do estoque de segurança.", "crítica", {"coverage_days": row["coverage_days_calculated"], "safety_stock_days": row["safety_stock_days"], **demand}, ["Estoque_Atual.Estoque atual", demand_origin, "Estoque_Atual.Estoque segurança dias"]))
        if row["backlog_order_quantity"] > 0 and row["production_order_quantity"] == 0:
            issues.append(_issue(row, "ORDER_WITHOUT_PRODUCTION", "Há pedido em carteira sem ordem de produção registrada para o SKU.", "alta", {"backlog_order_quantity": row["backlog_order_quantity"], "production_order_quantity": row["production_order_quantity"]}, ["Carteira_Pedidos.Quantidade", "Ordens_Producao.Quantidade"]))
        if pd.notna(row["first_promised_date"]) and pd.notna(row["first_production_completion"]) and row["first_production_completion"] > row["first_promised_date"]:
            delay = (row["first_production_completion"] - row["first_promised_date"]).days
            issues.append(_issue(row, "PRODUCTION_AFTER_PROMISE", "A primeira conclusão de produção é posterior à primeira data prometida do SKU.", "alta", {"first_promised_date": row["first_promised_date"].date().isoformat(), "first_production_completion": row["first_production_completion"].date().isoformat(), "delay_days": delay}, ["Carteira_Pedidos.Data prometida", "Ordens_Producao.Conclusão prevista"]))
        if row["coverage_days_calculated"] > thresholds["excess_coverage_days"]:
            issues.append(_issue(row, "EXCESS_COVERAGE", "Cobertura de estoque acima do limite de excesso configurado.", "média", {"coverage_days": row["coverage_days_calculated"], "threshold_days": thresholds["excess_coverage_days"], **demand}, ["Estoque_Atual.Estoque atual", demand_origin, "config.rule_thresholds.excess_coverage_days"]))
        if row["capacity_occupation_average"] > thresholds["capacity_occupation_threshold"]:
            issues.append(_issue(row, "CAPACITY_CONFLICT", "A ocupação média da família excede o limite configurado; requer avaliação operacional.", "alta", {"family": row["family"], "average_occupation": row["capacity_occupation_average"], "threshold": thresholds["capacity_occupation_threshold"], "available_capacity_average": row["capacity_available_average"]}, ["Capacidade_Semanal.Ocupação", "Capacidade_Semanal.Capacidade disponível", "config.rule_thresholds.capacity_occupation_threshold"]))
        if not row["has_sell_out"]:
            issues.append(_issue(row, "LOW_SELLOUT_VISIBILITY", "Não há sell-out observado para o SKU; a análise possui menor visibilidade de canal.", "média", {"sell_out_partner_count": int(row["sell_out_partner_count"]), "sell_out_visibility": row["sell_out_visibility"]}, ["Sell_Out.Cliente", "Sell_Out.SKU"]))
    columns = ["sku", "product", "family", "code", "description", "severity", "values_used", "data_origin"]
    return pd.DataFrame(issues, columns=columns).sort_values(["sku", "code"]).reset_index(drop=True)
