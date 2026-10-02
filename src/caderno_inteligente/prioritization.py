from __future__ import annotations
import json
from pathlib import Path
import pandas as pd


CONTEXT_COLUMNS = [
    "critical_date",
    "critical_date_reason",
    "operational_gap_quantity",
    "projected_stock_quantity",
    "first_promised_date",
    "first_production_completion",
    "sell_in_quantity",
    "sell_out_quantity",
    "sell_in_minus_sell_out_quantity",
    "forecast_quantity",
    "analysis_scope",
    "missing_data",
]


def load_weights(path: str | Path = "config/prioritization_weights.json") -> dict[str, int]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _confidence(issue_codes: set[str]) -> tuple[str, str]:
    if "LOW_SELLOUT_VISIBILITY" in issue_codes:
        return "baixa", "Sell-out não observado para o SKU; a visibilidade de canal é parcial."
    return "média", "Há sell-out observado, mas a cobertura de parceiros é parcial."


def _context_value(value):
    if isinstance(value, list):
        return value
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    return None if pd.isna(value) else value


def prioritize(issues: pd.DataFrame, weights: dict[str, int], indicators: pd.DataFrame) -> pd.DataFrame:
    """Ordena atenção por pontuação configurável; não otimiza nem decide produção."""
    if issues.empty:
        return pd.DataFrame(columns=["priority", "sku", "product", "family", "attention_score", "confidence", "confidence_reason", *CONTEXT_COLUMNS, "reasons", "evidence", "disclaimer"])
    unknown = sorted(set(issues["code"]) - set(weights))
    if unknown:
        raise ValueError(f"Regras sem peso configurado: {', '.join(unknown)}")
    context_by_sku = indicators.set_index("SKU")
    ranked_rows = []
    for sku, group in issues.groupby("sku", sort=False):
        codes = set(group["code"])
        score = int(sum(weights[code] for code in group["code"]))
        confidence, confidence_reason = _confidence(codes)
        context = context_by_sku.loc[sku]
        ranked_rows.append({
            "sku": sku,
            "product": group["product"].iloc[0],
            "family": group["family"].iloc[0],
            "attention_score": score,
            "confidence": confidence,
            "confidence_reason": confidence_reason,
            **{column: _context_value(context[column]) for column in CONTEXT_COLUMNS},
            "reasons": group[["code", "description", "severity"]].to_dict("records"),
            "evidence": group[["code", "values_used", "data_origin"]].to_dict("records"),
            "disclaimer": "Ordenação de atenção baseada em regras configuradas; não é solução ótima nem decisão automática de produção.",
        })
    result = pd.DataFrame(ranked_rows).sort_values(["attention_score", "sku"], ascending=[False, True]).reset_index(drop=True)
    result.insert(0, "priority", result.index + 1)
    return result
