"""Snapshot das decisões do produto para a comparação antes × depois da Etapa 15.

Somente leitura: o XLSM e as configurações não são alterados, e os bancos SQLite da API são redirecionados para um
diretório temporário (nada é gravado em runtime/). A saída é determinística (sem horário), para o diff ser legível.

    python scripts/snapshot_decisions.py                                  # grava docs/etapa-15/antes.json
    python scripts/snapshot_decisions.py --saida docs/etapa-15/depois.json
    python scripts/snapshot_decisions.py --comparar docs/etapa-15/antes.json docs/etapa-15/depois.json --saida docs/etapa-15/antes-depois.md
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

CONFIG_FILES = (
    "config/forecast_engine.json", "config/prioritization_weights.json", "config/rule_thresholds.json",
    "config/commercial_thresholds.json", "config/challenge_actions.json", "config/event_factors.json",
    "config/supply_plan.json",
)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _round(value, digits=4):
    return None if value is None else round(float(value), digits)


def build_snapshot() -> dict:
    os.environ.pop("DATABASE_URL", None)
    import backend.main as main
    from caderno_inteligente.partner_insights import build_partner_insights, load_commercial_thresholds
    from fastapi.testclient import TestClient

    original = main.FEEDBACK_DB, main.CASES_DB, main.RUNS_DB
    runtime = Path(tempfile.mkdtemp(prefix="snapshot-decisoes-"))
    main.FEEDBACK_DB, main.CASES_DB, main.RUNS_DB = runtime / "feedback.db", runtime / "cases.db", runtime / "runs.db"
    try:
        return _collect(main, TestClient(main.app), build_partner_insights, load_commercial_thresholds)
    finally:
        main.FEEDBACK_DB, main.CASES_DB, main.RUNS_DB = original


def _collect(main, client, build_partner_insights, load_commercial_thresholds) -> dict:
    dataset, _, indicators, issues, ranking, _ = main.pipeline()
    codes_by_sku: dict[str, list[str]] = {}
    for row in issues.to_dict("records"):
        codes_by_sku.setdefault(row["sku"], []).append(row["code"])
    indicator_by_sku = indicators.set_index("SKU")

    skus = []
    for item in client.get("/api/forecasts").json():
        forecast, recommendation = item["forecast"], item["operational_recommendation"]
        indicator = indicator_by_sku.loc[item["sku"]]
        skus.append({
            "sku": item["sku"], "family": item["family"], "priority": item.get("priority"), "attention_score": item.get("attention_score"),
            "signals": sorted(codes_by_sku.get(item["sku"], [])),
            "coverage_days_calculated": _round(indicator["coverage_days_calculated"], 1),
            "coverage_days_source": _round(indicator["coverage_days_source"], 1),
            "model": forecast.get("model"), "forecast_months": forecast.get("forecast_months"), "forecast_values": forecast.get("forecast_values"),
            "backtest_wape": forecast.get("backtest_wape"), "forecast_confidence": forecast.get("forecast_confidence"), "trend": forecast.get("trend"),
            "action": recommendation.get("action"), "suggested_quantity": recommendation.get("suggested_quantity"),
            "capacity_status": recommendation.get("capacity_status"), "confidence": recommendation.get("confidence"),
            "challenge_code": (item.get("challenge_action") or {}).get("code"),
        })
    skus.sort(key=lambda row: (row["priority"] is None, row["priority"] or 0, row["sku"]))

    monthly: dict[str, float] = {}
    for row in skus:
        for month, value in zip(row["forecast_months"] or [], row["forecast_values"] or []):
            monthly[month] = round(monthly.get(month, 0.0) + value, 1)

    commercial = main._enrich_challenge(build_partner_insights(dataset, load_commercial_thresholds(ROOT / "config/commercial_thresholds.json")))
    pairs = [{
        "partner": row["partner"], "sku": row["sku"], "action": row["action"], "data_quality": row["data_quality"],
        "signals": sorted(signal["code"] for signal in row["signals"]), "coverage_days": _round(row["coverage_days"], 1),
        "estimated_stock": row["estimated_stock"], "challenge_code": row["challenge_action"]["code"],
    } for row in commercial["items"]]

    revenue = client.get("/api/revenue-forecast").json()
    capacity = client.get("/api/capacity-plan")
    capacity_families = [{key: family[key] for key in ("family", "available_until_calendar_end", "planned_in_calendar", "unscheduled_quantity", "status",
                                                        "peak_need_units", "peak_status", "skus_short")}
                         for family in capacity.json()["families"]] if capacity.status_code == 200 else None
    validation = client.get("/api/validation/summary").json()["frozen_cases"]
    return {
        "source_sha256": file_sha256(main.SOURCE),
        "config_sha256": {name: file_sha256(ROOT / name) for name in CONFIG_FILES if (ROOT / name).exists()},
        "overview": client.get("/api/overview").json(),
        "forecast_total_by_month": monthly,
        "revenue_total": revenue.get("total"),
        "frozen_cases": {key: validation.get(key) for key in ("total", "passed", "failed", "not_found", "pending")},
        "action_counts": {action: sum(row["action"] == action for row in skus) for action in sorted({row["action"] for row in skus})},
        "top10": [{key: row[key] for key in ("priority", "sku", "action", "suggested_quantity", "challenge_code")} for row in skus[:10]],
        "skus": skus,
        "partner_pairs": pairs,
        "capacity": capacity_families,
    }


def _num(value) -> str:
    if value is None:
        return "—"
    return f"{value:,.0f}".replace(",", ".") if isinstance(value, (int, float)) else str(value)


def _month_total(snapshot: dict, month: str):
    return next((value for key, value in snapshot["forecast_total_by_month"].items() if key.startswith(month)), None)


def compare(before: dict, after: dict) -> str:
    """Resumo em Markdown das decisões antes × depois, com os números que a apresentação usa."""
    sku_before = {row["sku"]: row for row in before["skus"]}
    sku_after = {row["sku"]: row for row in after["skus"]}
    pair = lambda snapshot, partner, sku: next((row for row in snapshot["partner_pairs"] if row["partner"] == partner and row["sku"] == sku), {})  # noqa: E731
    lines = ["# Etapa 15 — Decisões antes × depois", "",
             "Gerado por `scripts/snapshot_decisions.py --comparar` a partir de `antes.json` (início da Etapa 15.0) e `depois.json` (fim da 15.6), na mesma planilha.", ""]
    lines += ["## Ações por SKU", "", "| Ação | Antes | Depois |", "|---|---|---|"]
    for action in sorted(set(before["action_counts"]) | set(after["action_counts"])):
        lines.append(f"| `{action}` | {before['action_counts'].get(action, 0)} | {after['action_counts'].get(action, 0)} |")
    lines += ["", "## Top 10 da fila", "", "| # | Antes | Ação antes | Depois | Ação depois | Sugerido agora |", "|---|---|---|---|---|---|"]
    for old, new in zip(before["top10"], after["top10"]):
        lines.append(f"| {new['priority']} | {old['sku']} | `{old['action']}` | {new['sku']} | `{new['action']}` | {_num(new['suggested_quantity'])} |")
    lines += ["", "## Previsão, cobertura e casos-alvo", "", "| Indicador | Antes | Depois |", "|---|---|---|",
              f"| Previsão somada nov/26 (un.) | {_num(_month_total(before, '2026-11'))} | {_num(_month_total(after, '2026-11'))} |",
              f"| Previsão somada jan/27 (un.) | {_num(_month_total(before, '2027-01'))} | {_num(_month_total(after, '2027-01'))} |",
              f"| Faturamento estimado 3 meses (R$) | {_num((before.get('revenue_total') or {}).get('revenue_total_3m'))} | {_num((after.get('revenue_total') or {}).get('revenue_total_3m'))} |",
              f"| SKUs na fila | {before['overview']['prioritized']} | {after['overview']['prioritized']} |",
              f"| Quantidade sugerida agora (un.) | {_num(sum(row['suggested_quantity'] or 0 for row in before['skus']))} | {_num(sum(row['suggested_quantity'] or 0 for row in after['skus']))} |"]
    for sku in ("CI-0041", "CI-0050", "CI-0047", "CI-0048", "CI-0009", "CI-0014", "CI-0004"):
        old, new = sku_before.get(sku, {}), sku_after.get(sku, {})
        lines.append(f"| {sku}: posição · ação · cobertura (dias) | {_num(old.get('priority'))} · `{old.get('action')}` · {_num(old.get('coverage_days_calculated'))} "
                     f"| {_num(new.get('priority'))} · `{new.get('action')}` · {_num(new.get('coverage_days_calculated'))} |")
    for partner, sku in (("KA-02", "CI-0009"), ("KA-03", "CI-0001")):
        old, new = pair(before, partner, sku), pair(after, partner, sku)
        lines.append(f"| {partner} · {sku}: ação comercial | `{old.get('action')}` | `{new.get('action')}` |")
    cases_before, cases_after = before["frozen_cases"], after["frozen_cases"]
    lines.append(f"| Casos congelados (aprovados / total / pendentes) | {cases_before['passed']} / {cases_before['total']} / {cases_before.get('pending') or 0} "
                 f"| {cases_after['passed']} / {cases_after['total']} / {cases_after.get('pending') or 0} |")
    if after.get("capacity"):
        lines += ["", "## Capacidade (depois)", "", "| Família | Livre no calendário | Sem programação | Situação | Pico: necessidade · situação |", "|---|---|---|---|---|"]
        for family in after["capacity"]:
            lines.append(f"| {family['family']} | {_num(family['available_until_calendar_end'])} | {_num(family['unscheduled_quantity'])} | `{family['status']}` "
                         f"| {_num(family['peak_need_units'])} · `{family['peak_status']}` |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--saida", default=str(ROOT / "docs" / "etapa-15" / "antes.json"))
    parser.add_argument("--comparar", nargs=2, metavar=("ANTES", "DEPOIS"))
    args = parser.parse_args()
    output = Path(args.saida)
    output.parent.mkdir(parents=True, exist_ok=True)
    if args.comparar:
        before, after = (json.loads(Path(path).read_text(encoding="utf-8")) for path in args.comparar)
        output.write_text(compare(before, after), encoding="utf-8")
        print(f"{output}: comparação gerada")
        return
    snapshot = build_snapshot()
    output.write_text(json.dumps(snapshot, ensure_ascii=False, indent=1, default=str) + "\n", encoding="utf-8")
    print(f"{output}: {len(snapshot['skus'])} SKUs, {len(snapshot['partner_pairs'])} pares parceiro–SKU")


if __name__ == "__main__":
    main()
