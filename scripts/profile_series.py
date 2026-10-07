"""Perfil das séries mensais por SKU e snapshot da previsão oficial atual (Etapa 14.0).

Somente leitura: o XLSM nunca é alterado e nada do pipeline é modificado.

    python scripts/profile_series.py                       # imprime o resumo
    python scripts/profile_series.py --write docs/etapa-14-0   # grava perfil-series.csv e snapshot-previsao-v1.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from caderno_inteligente.forecasting import _monthly_series, build_demand_forecasts  # noqa: E402
from caderno_inteligente.ingestion import load_workbook  # noqa: E402
from caderno_inteligente.transformations import normalise_dataset  # noqa: E402

SOURCE = ROOT / "data" / "source" / "Base de Dados - Caderno Inteligente.xlsm"
INTERMITTENT_SHARE = 0.30  # limiar proposto para Croston; a decisão final é da 14.1
ROLLING_MIN_TRAIN = 15  # treino da primeira janela com 3 janelas de 3 meses em 24 meses


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def profile(sales: pd.DataFrame, forecasts: pd.DataFrame) -> pd.DataFrame:
    chosen = forecasts.set_index("sku")
    rows = []
    for sku in sorted(sales["SKU"].dropna().astype(str).unique()):
        series = _monthly_series(sales, sku)
        months = int(len(series))
        zeros = int((series == 0).sum())
        mean = float(series.mean()) if months else 0.0
        rows.append(
            {
                "sku": sku,
                "history_months": months,
                "zero_months": zeros,
                "zero_share": round(zeros / months, 4) if months else None,
                "mean_units": round(mean, 1),
                "cv": round(float(series.std(ddof=0)) / mean, 4) if mean > 0 else None,
                "current_model": chosen.loc[sku, "model"] if sku in chosen.index else None,
                "current_wape": chosen.loc[sku, "backtest_wape"] if sku in chosen.index else None,
            }
        )
    return pd.DataFrame(rows)


def summary(table: pd.DataFrame) -> dict:
    wape = table["current_wape"].dropna()
    return {
        "skus": int(len(table)),
        "history_months": {str(k): int(v) for k, v in table["history_months"].value_counts().sort_index().items()},
        "skus_below_rolling_min_train": int((table["history_months"] < ROLLING_MIN_TRAIN).sum()),
        "skus_below_6_months": int((table["history_months"] < 6).sum()),
        "skus_with_any_zero_month": int((table["zero_months"] > 0).sum()),
        "skus_intermittent": int((table["zero_share"].fillna(0) >= INTERMITTENT_SHARE).sum()),
        "intermittent_threshold": INTERMITTENT_SHARE,
        "zero_share_max": None if table["zero_share"].dropna().empty else float(table["zero_share"].max()),
        "cv_median": None if table["cv"].dropna().empty else round(float(table["cv"].median()), 4),
        "current_model_counts": {str(k): int(v) for k, v in table["current_model"].fillna("sem previsão").value_counts().items()},
        "current_wape_median": None if wape.empty else round(float(wape.median()), 4),
        "current_wape_mean": None if wape.empty else round(float(wape.mean()), 4),
    }


def snapshot(forecasts: pd.DataFrame, sha256: str) -> dict:
    return {
        "description": "Previsão oficial (forecasting.py, motor v1) antes da Etapa 14. Referência de regressão: com engine = v1 nada disso pode mudar.",
        "source_sha256": sha256,
        "forecasts": json.loads(forecasts.sort_values("sku").to_json(orient="records", force_ascii=False)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--write", metavar="DIR", help="grava perfil-series.csv, resumo-perfil.json e snapshot-previsao-v1.json nesta pasta")
    args = parser.parse_args()

    dataset = normalise_dataset(load_workbook(SOURCE))
    sales = dataset["Vendas_24m"]
    forecasts = build_demand_forecasts(sales)
    table = profile(sales, forecasts)
    sha256 = file_sha256(SOURCE)
    result = {"source_sha256": sha256, **summary(table)}
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if args.write:
        out = Path(args.write)
        out.mkdir(parents=True, exist_ok=True)
        table.to_csv(out / "perfil-series.csv", index=False, encoding="utf-8")
        (out / "resumo-perfil.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (out / "snapshot-previsao-v1.json").write_text(json.dumps(snapshot(forecasts, sha256), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"Gravado em {out}")


if __name__ == "__main__":
    main()
