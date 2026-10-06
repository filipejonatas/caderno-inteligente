"""Canais diretos (E-commerce, Marketplace, Loja própria): visão observada a partir do faturamento.

Camada aditiva e somente leitura. A fonte é `Vendas_24m` (faturamento, que nos canais diretos é a venda ao
consumidor), cruzada com cadastro, produtos e carteira. Não há estoque por canal na base: o único estoque é o do CD.
Não altera previsão, score, ranking nem regras.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

DEFAULT_SETTINGS: dict[str, Any] = {"trend_months": 3, "trend_band": 0.1, "inactive_months": 2, "concentration_share": 0.8}
CLOSED_STATUSES = {"cancelado", "concluído", "entregue", "faturado"}
VALUE = "Valor faturado (R$)"
UNITS = "Quantidade faturada"

SUGGESTION_LABELS = {
    "avaliar_ampliacao_mix": "Avaliar ampliação de mix",
    "avaliar_reativacao": "Avaliar reativação",
    "investigar_queda": "Investigar queda",
    "monitorar_saida_de_linha": "Monitorar saída de linha",
    "acompanhar_crescimento": "Acompanhar crescimento",
    "sem_acao_necessaria": "Sem ação necessária",
}
SIGNAL_LABELS = {
    "NOT_SOLD": "Sem faturamento no canal",
    "STOPPED": "Parou de vender no canal",
    "DECLINING": "Em queda",
    "GROWING": "Em crescimento",
    "DISCONTINUING_PRODUCT": "Produto em descontinuação",
    "OPEN_BACKLOG": "Pedido em carteira",
}
FIELD_NATURE = {
    "revenue": {"nature": "observado", "origin": "Vendas_24m.Valor faturado (R$); nos canais diretos, venda ao consumidor"},
    "units": {"nature": "observado", "origin": "Vendas_24m.Quantidade faturada"},
    "trend": {"nature": "calculado", "origin": "média mensal dos últimos meses ÷ média dos meses anteriores (mesma regra da previsão)"},
    "backlog": {"nature": "observado na fonte", "origin": "Carteira_Pedidos, pedidos não encerrados; sem alocação de produção"},
    "suggestion": {"nature": "sugestão determinística para revisão humana", "origin": "sinais deste módulo e config/direct_channel_thresholds.json"},
    "stock": {"nature": "ausente", "origin": "Estoque_Atual só tem o CD Central; a base não tem estoque por canal"},
}
LIMITATIONS = [
    "Visibilidade vem do faturamento (Vendas_24m); os canais diretos não têm linhas em Sell_In nem em Sell_Out.",
    "Não há estoque por canal: o estoque exibido no resto do sistema é o do CD Central.",
    "Tendência compara meses recentes com os anteriores e pode refletir sazonalidade, não só mudança de demanda.",
    "SKU sem faturamento no canal é exibido como não vendido, sem valor; não é tratado como venda zero.",
    "A carteira de pedidos não é alocada à produção; é apenas contexto.",
    "A sugestão é determinística, demonstrativa e exige revisão humana.",
]


def load_direct_channel_settings(path: str | Path | None = None) -> dict[str, Any]:
    values = dict(DEFAULT_SETTINGS)
    if path is not None:
        overrides = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(overrides, dict) or set(overrides) - set(values):
            raise ValueError("Configuração de canais diretos contém campos desconhecidos")
        values.update(overrides)
    return _validate_settings(values)


def _validate_settings(values: dict[str, Any]) -> dict[str, Any]:
    if set(values) != set(DEFAULT_SETTINGS):
        raise ValueError("Parâmetro de canais diretos desconhecido")
    for key, value in values.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"Parâmetro de canais diretos inválido: {key}")
    for key in ("trend_months", "inactive_months"):
        if int(values[key]) != values[key] or values[key] < 1:
            raise ValueError(f"Parâmetro precisa ser inteiro positivo: {key}")
        values[key] = int(values[key])
    if values["trend_months"] > 12 or values["inactive_months"] > 12:
        raise ValueError("Janelas de canais diretos devem ter no máximo 12 meses")
    if not 0 <= values["trend_band"] < 1 or not 0 < values["concentration_share"] <= 1:
        raise ValueError("Faixa de tendência ou participação de concentração inválida")
    return values


def _round(value: float | None, digits: int = 2) -> float | None:
    return None if value is None or not math.isfinite(value) else round(float(value), digits)


def _iso(period: pd.Period | None) -> str | None:
    return None if period is None else period.start_time.date().isoformat()


def _trend(recent: float | None, previous: float | None, band: float) -> tuple[str, float | None]:
    if recent is None or previous is None:
        return "indeterminada", None
    if previous == 0:
        return ("crescente", None) if recent > 0 else ("estável", 0.0)
    change = (recent - previous) / previous
    return ("crescente" if change > band else "decrescente" if change < -band else "estável"), change


def _prepare_sales(sales: pd.DataFrame) -> pd.DataFrame:
    frame = sales.copy()
    frame["period"] = pd.to_datetime(frame["Mês"]).dt.to_period("M")
    frame[UNITS] = pd.to_numeric(frame[UNITS], errors="coerce")
    frame[VALUE] = pd.to_numeric(frame[VALUE], errors="coerce") if VALUE in frame else float("nan")
    return frame


def direct_channel_codes(partners: pd.DataFrame) -> list[str]:
    return [str(code) for code in partners.loc[partners["Tipo"] == "Canal direto", "Código"].dropna()]


def _open_orders(orders: pd.DataFrame) -> pd.DataFrame:
    return orders[~orders["Status"].astype(str).str.casefold().isin(CLOSED_STATUSES)]


def _sku_rows(code: str, frame: pd.DataFrame, products: pd.DataFrame, orders: pd.DataFrame, window: dict[str, Any], settings: dict[str, Any]) -> list[dict]:
    last_period, months = window["last"], settings["trend_months"]
    recent = list(pd.period_range(last_period - (months - 1), last_period, freq="M"))
    previous = list(pd.period_range(last_period - (2 * months - 1), last_period - months, freq="M"))
    year_ago = [p - 12 for p in recent]
    own = frame[frame["Cliente/Canal"] == code]
    others = frame[~frame["Cliente/Canal"].isin(window["direct_codes"])]
    all_channels_recent = frame[frame["period"].isin(recent)].groupby("SKU")[UNITS].sum()
    own_total = own[VALUE].sum(min_count=1)
    open_orders = _open_orders(orders[orders["Cliente/Canal"] == code])

    def units_in(rows: pd.DataFrame, periods: list[pd.Period]) -> float | None:
        subset = rows[rows["period"].isin(periods)]
        return None if subset.empty else float(subset[UNITS].sum())

    rows = []
    for _, product in products.iterrows():
        sku = str(product["SKU"])
        sold = own[(own["SKU"] == sku) & (own[UNITS] > 0)]
        status = None if pd.isna(product.get("Status")) else str(product["Status"])
        base = {"sku": sku, "product": None if pd.isna(product.get("Produto")) else str(product["Produto"]),
                "family": None if pd.isna(product.get("Família")) else str(product["Família"]), "product_status": status}
        backlog = open_orders[open_orders["SKU"] == sku]
        backlog_info = {"backlog_open_quantity": _round(float(backlog["Quantidade"].sum()), 1) if not backlog.empty else None, "backlog_open_orders": int(len(backlog))}
        if sold.empty:
            signals = ["NOT_SOLD"] + (["OPEN_BACKLOG"] if len(backlog) else [])
            rows.append({**base, "months_sold": 0, "first_month": None, "last_month": None, "units_24m": None, "revenue_24m": None, "share_in_channel": None,
                         "rank": None, "cumulative_share": None, "units_recent": None, "units_previous": None, "trend": "indeterminada", "change_ratio": None,
                         "yoy_ratio": None, "partners_units_recent": None, "direct_share_of_sku_recent": None, **backlog_info, "signals": signals})
            continue
        sku_rows = own[own["SKU"] == sku]
        recent_units, previous_units = units_in(sku_rows, recent), units_in(sku_rows, previous)
        trend, change = _trend(recent_units, previous_units, settings["trend_band"])
        year_units = units_in(sku_rows, year_ago)
        partner_units = units_in(others[others["SKU"] == sku], recent)
        total_recent = all_channels_recent.get(sku)
        revenue = sold[VALUE].sum(min_count=1)
        last_sold = sold["period"].max()
        signals = []
        if (last_period - last_sold).n >= settings["inactive_months"]:
            signals.append("STOPPED")
        elif trend == "crescente":
            signals.append("GROWING")
        elif trend == "decrescente":
            signals.append("DECLINING")
        if status and status.casefold().startswith("descontinu"):
            signals.append("DISCONTINUING_PRODUCT")
        if len(backlog):
            signals.append("OPEN_BACKLOG")
        rows.append({
            **base, "months_sold": int(sold["period"].nunique()), "first_month": _iso(sold["period"].min()), "last_month": _iso(last_sold),
            "units_24m": _round(float(sold[UNITS].sum()), 1), "revenue_24m": None if pd.isna(revenue) else _round(float(revenue)),
            "share_in_channel": None if pd.isna(revenue) or not own_total else _round(float(revenue) / float(own_total), 4),
            "rank": None, "cumulative_share": None, "units_recent": _round(recent_units, 1), "units_previous": _round(previous_units, 1),
            "trend": trend, "change_ratio": _round(change, 4), "yoy_ratio": None if not year_units or recent_units is None else _round((recent_units - year_units) / year_units, 4),
            "partners_units_recent": _round(partner_units, 1),
            "direct_share_of_sku_recent": None if not total_recent or recent_units is None else _round(recent_units / float(total_recent), 4),
            **backlog_info, "signals": signals,
        })
    ranked = sorted((row for row in rows if row["revenue_24m"] is not None), key=lambda row: (-row["revenue_24m"], row["sku"]))
    cumulative = 0.0
    for position, row in enumerate(ranked, start=1):
        cumulative += row["share_in_channel"] or 0.0
        row["rank"], row["cumulative_share"] = position, _round(min(cumulative, 1.0), 4)
    for row in rows:
        row["suggestion"] = _suggestion(row)
    rows.sort(key=lambda row: (row["rank"] is None, row["rank"] or 0, row["sku"]))
    return rows


def _suggestion(row: dict[str, Any]) -> dict[str, Any]:
    signals = row["signals"]
    if "NOT_SOLD" in signals and (row["product_status"] or "").casefold().startswith("descontinu"):
        code, reason = "monitorar_saida_de_linha", "Produto em descontinuação e sem faturamento no canal; não ampliar mix."
    elif "NOT_SOLD" in signals:
        code, reason = "avaliar_ampliacao_mix", "Produto ativo sem nenhum faturamento neste canal nos 24 meses."
    elif "STOPPED" in signals:
        code, reason = "avaliar_reativacao", f"Sem faturamento desde {row['last_month']}, depois de vender em {row['months_sold']} meses."
    elif "DISCONTINUING_PRODUCT" in signals:
        code, reason = "monitorar_saida_de_linha", "Produto em descontinuação ainda vendido no canal."
    elif "DECLINING" in signals:
        code, reason = "investigar_queda", "Média mensal recente abaixo da faixa neutra em relação aos meses anteriores."
    elif "GROWING" in signals:
        code, reason = "acompanhar_crescimento", "Média mensal recente acima da faixa neutra em relação aos meses anteriores."
    else:
        code, reason = "sem_acao_necessaria", "Sem sinal de queda, parada, crescimento relevante ou lacuna de mix."
    return {"code": code, "label": SUGGESTION_LABELS[code], "reason": reason, "requires_human_review": True}


def _channel_summary(code: str, partner: pd.Series, frame: pd.DataFrame, rows: list[dict], window: dict[str, Any], settings: dict[str, Any],
                     orders: pd.DataFrame, sell_out_rows: int, catalog_size: int, totals: dict[str, float | None]) -> dict[str, Any]:
    own = frame[frame["Cliente/Canal"] == code]
    last_period, months = window["last"], settings["trend_months"]
    recent = list(pd.period_range(last_period - (months - 1), last_period, freq="M"))
    previous = list(pd.period_range(last_period - (2 * months - 1), last_period - months, freq="M"))
    all_months = list(pd.period_range(window["first"], last_period, freq="M"))
    monthly_units = own.groupby("period")[UNITS].sum()
    monthly_value = own.groupby("period")[VALUE].sum(min_count=1)

    def window_sum(series: pd.Series, periods: list[pd.Period]) -> float | None:
        values = [series.get(p) for p in periods]
        return None if any(v is None or pd.isna(v) for v in values) else float(sum(values))

    revenue_recent, revenue_previous = window_sum(monthly_value, recent), window_sum(monthly_value, previous)
    trend, change = _trend(revenue_recent, revenue_previous, settings["trend_band"])
    year_ago = window_sum(monthly_value, [p - 12 for p in recent])
    revenue = own[VALUE].sum(min_count=1)
    units = own[UNITS].sum()
    sold_rows = sorted((row for row in rows if row["revenue_24m"] is not None), key=lambda row: -row["revenue_24m"])
    shares = [row["share_in_channel"] or 0.0 for row in sold_rows]
    reached, skus_for_target = 0.0, 0
    for share in shares:
        skus_for_target += 1
        reached += share
        if reached >= settings["concentration_share"]:
            break
    open_orders = _open_orders(orders[orders["Cliente/Canal"] == code])
    declared_skus = pd.to_numeric(partner.get("SKUs com sell-out"), errors="coerce")
    signal_counts: dict[str, int] = {}
    suggestion_counts: dict[str, int] = {}
    for row in rows:
        for signal in row["signals"]:
            signal_counts[signal] = signal_counts.get(signal, 0) + 1
        suggestion_counts[row["suggestion"]["code"]] = suggestion_counts.get(row["suggestion"]["code"], 0) + 1
    observed_skus = int(own.loc[own[UNITS] > 0, "SKU"].nunique())
    return {
        "code": code, "name": None if pd.isna(partner.get("Nome fictício")) else str(partner["Nome fictício"]),
        "region": None if pd.isna(partner.get("Região")) else str(partner["Região"]),
        "declared_coverage": None if pd.isna(partner.get("Cobertura de sell-out")) else str(partner["Cobertura de sell-out"]),
        "declared_skus": None if pd.isna(declared_skus) else int(declared_skus), "sell_out_rows": sell_out_rows,
        "observed_skus": observed_skus, "catalog_skus": catalog_size,
        "revenue_24m": None if pd.isna(revenue) else _round(float(revenue)), "units_24m": _round(float(units), 1),
        "share_of_revenue": None if pd.isna(revenue) or not totals["revenue"] else _round(float(revenue) / totals["revenue"], 4),
        "share_of_units": None if not totals["units"] else _round(float(units) / totals["units"], 4),
        "revenue_recent": _round(revenue_recent), "revenue_previous": _round(revenue_previous), "trend": trend, "change_ratio": _round(change, 4),
        "yoy_ratio": None if not year_ago or revenue_recent is None else _round((revenue_recent - year_ago) / year_ago, 4),
        "monthly": {"months": [_iso(p) for p in all_months],
                    "revenue": [None if pd.isna(monthly_value.get(p)) else _round(float(monthly_value.get(p))) for p in all_months],
                    "units": [None if p not in monthly_units.index else _round(float(monthly_units[p]), 1) for p in all_months]},
        "concentration": {"top5_share": _round(sum(shares[:5]), 4) if shares else None, "skus_for_target_share": skus_for_target if shares else None, "target_share": settings["concentration_share"]},
        "backlog": {"open_orders": int(len(open_orders)), "open_quantity": _round(float(open_orders["Quantidade"].sum()), 1) if len(open_orders) else None,
                    "skus": int(open_orders["SKU"].nunique())},
        "signal_counts": signal_counts, "suggestion_counts": suggestion_counts,
    }


def build_channel_findings(data: dict[str, pd.DataFrame]) -> list[dict[str, Any]]:
    """Inconsistências entre abas que afetam a leitura dos canais; nada é reconciliado."""
    findings: list[dict[str, Any]] = []
    partners, sales = data["Parceiros_Canais"], _prepare_sales(data["Vendas_24m"])
    direct = partners[partners["Tipo"] == "Canal direto"]
    sell_out = data["Sell_Out"]
    claims = []
    for _, row in direct.iterrows():
        code = str(row["Código"])
        rows = int((sell_out["Cliente"] == code).sum())
        declared = pd.to_numeric(row.get("SKUs com sell-out"), errors="coerce")
        billed = int(sales.loc[(sales["Cliente/Canal"] == code) & (sales[UNITS] > 0), "SKU"].nunique())
        if str(row.get("Cobertura de sell-out")).casefold() == "completo" and rows == 0:
            claims.append({"channel": code, "declared_coverage": str(row["Cobertura de sell-out"]), "declared_skus": None if pd.isna(declared) else int(declared),
                           "sell_out_rows": rows, "billing_observed_skus": billed})
    if claims:
        findings.append({
            "code": "DIRECT_COVERAGE_NOT_IN_SELL_OUT", "severity": "atenção", "affects": [claim["channel"] for claim in claims],
            "title": "Cobertura dos canais diretos sem Sell_Out",
            "treatment_label": "Usa Vendas_24m",
            "summary": "O cadastro declara cobertura de sell-out completa, mas a aba Sell_Out não tem nenhuma linha desses canais.",
            "evidence": claims,
            "treatment": "A visão dos canais diretos usa o faturamento de Vendas_24m, que nesses canais é a venda ao consumidor; Sell_Out não é usado para eles.",
        })
    b2b = partners[partners["Tipo"] != "Canal direto"]["Código"].astype(str).tolist()
    sell_in = data["Sell_In"].copy()
    if b2b and not sell_in.empty:
        sell_in["period"] = pd.to_datetime(sell_in["Mês"]).dt.to_period("M")
        billed = sales[sales["Cliente/Canal"].isin(b2b)].groupby(["Cliente/Canal", "SKU", "period"])[UNITS].sum().rename("billed")
        sent = sell_in.groupby(["Cliente", "SKU", "period"])["Quantidade enviada"].sum().rename("sent")
        sent.index = sent.index.set_names(["Cliente/Canal", "SKU", "period"])
        both = pd.concat([billed, sent], axis=1, join="inner")
        if len(both) and (both["billed"] == both["sent"]).mean() < 0.95:
            ratio = (both["sent"] / both["billed"].where(both["billed"] > 0)).dropna()
            findings.append({
                "code": "KA_SELL_IN_DIFFERS_FROM_BILLING", "severity": "atenção", "affects": sorted(sell_in["Cliente"].astype(str).unique().tolist()),
                "title": "Sell_In difere do faturado",
                "treatment_label": "Não reconciliado",
                "summary": "Para os mesmos parceiros, SKUs e meses, a quantidade enviada em Sell_In difere do faturado em Vendas_24m, e as abas cobrem períodos e SKUs diferentes.",
                "evidence": {
                    "overlapping_pairs": int(len(both)), "equal_pairs": int((both["billed"] == both["sent"]).sum()),
                    "median_sell_in_over_billing": None if ratio.empty else _round(float(ratio.median()), 2),
                    "billing_skus_per_partner": int(sales[sales["Cliente/Canal"].isin(b2b)].groupby("Cliente/Canal")["SKU"].nunique().max()),
                    "sell_in_skus_per_partner": int(sell_in.groupby("Cliente")["SKU"].nunique().max()),
                    "billing_months": int(sales["period"].nunique()), "sell_in_months": int(sell_in["period"].nunique()),
                },
                "treatment": "Não reconciliado. A análise comercial dos parceiros segue usando Sell_In e Sell_Out; a visão dos canais diretos usa só Vendas_24m.",
            })
    return findings


def build_direct_channels(data: dict[str, pd.DataFrame], settings: dict[str, Any] | None = None) -> dict[str, Any]:
    settings = _validate_settings(dict(settings or DEFAULT_SETTINGS))
    partners, products, orders = data["Parceiros_Canais"], data["Produtos"], data["Carteira_Pedidos"]
    frame = _prepare_sales(data["Vendas_24m"])
    codes = direct_channel_codes(partners)
    last, first = frame["period"].max(), frame["period"].min()
    window = {"last": last, "first": first, "direct_codes": codes}
    totals = {"revenue": None if frame[VALUE].isna().all() else float(frame[VALUE].sum()), "units": float(frame[UNITS].sum())}
    direct_frame = frame[frame["Cliente/Canal"].isin(codes)]
    channels, rows_by_channel = [], {}
    for code in codes:
        partner = partners[partners["Código"].astype(str) == code].iloc[0]
        rows = _sku_rows(code, frame, products, orders, window, settings)
        rows_by_channel[code] = rows
        sell_out_rows = int((data["Sell_Out"]["Cliente"] == code).sum())
        channels.append(_channel_summary(code, partner, frame, rows, window, settings, orders, sell_out_rows, int(products["SKU"].nunique()), totals))
    direct_revenue = direct_frame[VALUE].sum(min_count=1)
    return {
        "reference_month": _iso(last), "settings": settings,
        "totals": {
            "direct_revenue_24m": None if pd.isna(direct_revenue) else _round(float(direct_revenue)), "total_revenue_24m": _round(totals["revenue"]),
            "direct_share_of_revenue": None if pd.isna(direct_revenue) or not totals["revenue"] else _round(float(direct_revenue) / totals["revenue"], 4),
            "direct_share_of_units": None if not totals["units"] else _round(float(direct_frame[UNITS].sum()) / totals["units"], 4),
        },
        "channels": channels, "rows": rows_by_channel, "findings": build_channel_findings(data),
        "signal_labels": SIGNAL_LABELS, "suggestion_labels": SUGGESTION_LABELS, "field_nature": FIELD_NATURE, "limitations": LIMITATIONS,
    }
