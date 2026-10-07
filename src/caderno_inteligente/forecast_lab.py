"""Laboratório de previsão (Etapas 14.3 e 15.1): motores lado a lado, sem alterar nada oficial.

Reúne o que as etapas 14.1 e 14.2 calculam (candidatos, seleção rolante, avaliação aninhada e grade de sensibilidade) e,
desde a 15.1, a avaliação com meses de pico que decide a promoção do motor v2 (`peak_evaluation`). O motor oficial é o de
`config/forecast_engine.json`; o motor rolante da 14.x continua só no laboratório.
"""
from __future__ import annotations

import math
from statistics import median
from typing import Any

import pandas as pd

from .forecast_candidates import CANDIDATES
from .forecast_engine_config import load_engine_config
from .official_forecast import ENGINE_LABELS
from .rolling_backtest import (
    BASELINE_LABEL,
    BASELINE_MODEL,
    build_rolling_forecasts,
    interval_calibration,
    nested_evaluation_table,
    peak_evaluation,
    sensitivity_grid,
    series_by_sku,
    summarize_sensitivity,
)

FIELD_NATURE = {
    "nested": {"nature": "calculado", "origin": "Vendas_24m: cada procedimento escolhe o modelo só com dados anteriores à origem e é medido nos 3 meses seguintes"},
    "sensitivity": {"nature": "calculado", "origin": "a mesma avaliação aninhada refeita para cada combinação de origens externas e mínimo de janelas"},
    "intervals": {"nature": "estimado", "origin": "quantis dos erros relativos do motor rolante nas janelas de teste de Vendas_24m; a cobertura é medida fora da amostra"},
    "selection": {"nature": "estimado", "origin": "backtest rolante em Vendas_24m; o WAPE de seleção é otimista porque mede no mesmo teste em que escolheu"},
    "peak_evaluation": {"nature": "calculado", "origin": "Vendas_24m: origens rolantes fixadas no protocolo (config/forecast_engine.json → evaluation), com o erro separado em meses de pico e normais"},
}
INTERVAL_TOLERANCE = 0.10  # faixa com cobertura mais de 10 p.p. abaixo da nominal não é mostrada

LIMITATIONS = [
    "Laboratório: nenhuma previsão, ranking, score ou recomendação oficial usa o motor rolante da Etapa 14. O motor oficial v2 foi promovido na Etapa 15.1 pela avaliação com meses de pico.",
    "A avaliação mede o passado recente; as origens de teste são os mesmos trimestres para todos os SKUs, que compartilham sazonalidade. Não são 50 observações independentes.",
    "O erro de seleção por SKU é otimista. Para comparar motores vale a avaliação aninhada.",
    "A grade mostra quanto o veredito muda com duas escolhas de desenho. Uma das combinações (3 origens e 2 janelas mínimas) reverte o resultado, por exigir que o motor rolante abra mão dos modelos sazonais com pouco histórico.",
    "Faixa de previsão: estimativa empírica com poucos erros por SKU (9 com 3 janelas); a faixa sempre contém a previsão pontual e não entra no score nem no ranking.",
    "A previsão continua global por SKU: sem canal, parceiro ou região.",
]


def _clean(value: Any) -> Any:
    """JSON seguro: ausente continua nulo (nunca zero) e floats vêm arredondados."""
    if isinstance(value, dict):
        return {key: _clean(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(item) for item in value]
    if isinstance(value, float):
        return round(value, 4) if math.isfinite(value) else None
    return value


def _selection(records: list[dict[str, Any]], official: dict[str, str], enabled: list[str]) -> dict[str, Any]:
    rows = [record for record in records if record.get("model") and record.get("candidates")]
    models = []
    for code in sorted(enabled, key=lambda item: CANDIDATES[item].complexity):
        candidate = CANDIDATES[code]
        wapes = [
            entry["wape"] for record in rows for entry in record["candidates"]
            if entry["model"] == code and entry["eligible"] and entry["wape"] is not None
        ]
        models.append(
            {
                "model": code,
                "label": candidate.label,
                "description": candidate.description,
                "complexity": candidate.complexity,
                "min_history_months": candidate.min_history,
                "official_selected_skus": sum(official.get(record["sku"]) == code for record in rows),
                "rolling_selected_skus": sum(record["model"] == code for record in rows),
                "evaluated_skus": len(wapes),
                "median_wape": median(wapes) if wapes else None,
            }
        )
    changed = [
        {
            "sku": record["sku"],
            "official_model": official.get(record["sku"]),
            "official_model_label": CANDIDATES[official[record["sku"]]].label if official.get(record["sku"]) in CANDIDATES else None,
            "rolling_model": record["model"],
            "rolling_model_label": record["model_label"],
            "rolling_wape": record["backtest_wape"],
        }
        for record in rows if official.get(record["sku"]) != record["model"]
    ]
    return {
        "skus": len(rows),
        "skipped_skus": len(records) - len(rows),
        "changed_skus": len(changed),
        "models": models,
        "changed": changed,
    }


def _intervals(records: list[dict[str, Any]], calibration: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    settings = config["intervals"]
    ready = [record for record in records if record.get("forecast_interval")]
    level = settings["upper_quantile"] - settings["lower_quantile"]
    coverage = calibration.get("coverage") if calibration else None
    calibrated = coverage is not None and coverage >= level - INTERVAL_TOLERANCE
    return {
        "status": "calibrada" if calibrated else "nao_calibrada",
        "status_note": None if calibrated else (
            f"A faixa cobriu {coverage:.0%} dos meses testados contra {level:.0%} prometidos; não é mostrada até ser recalibrada."
            if coverage is not None else "Sem meses testados para medir a cobertura; a faixa não é mostrada."
        ),
        "lower_quantile": settings["lower_quantile"],
        "upper_quantile": settings["upper_quantile"],
        "level": round(settings["upper_quantile"] - settings["lower_quantile"], 4),
        "minimum_residuals": settings["minimum_residuals"],
        "skus_with_band": len(ready),
        "skus_without_band": sum(1 for record in records if record.get("model") and not record.get("forecast_interval")),
        "calibration": calibration,
        "items": [
            {
                "sku": record["sku"],
                "model": record["model"],
                "model_label": record["model_label"],
                "month": record["forecast_months"][0],
                "point": record["forecast_values"][0],
                "lower": record["forecast_interval"]["lower"][0],
                "upper": record["forecast_interval"]["upper"][0],
                "residuals": record["forecast_interval"]["residuals"],
            }
            for record in ready
        ],
    }


def build_forecast_lab(sales: pd.DataFrame, official_forecasts: pd.DataFrame, config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = load_engine_config() if config is None else config
    official = {str(row["sku"]): str(row["model"]) for row in official_forecasts.to_dict("records") if row.get("model")}
    series_map = series_by_sku(sales)  # montadas uma vez: refazer a série de cada SKU em cada cálculo é o maior custo
    records = build_rolling_forecasts(sales, config, series_map=series_map)
    nested = nested_evaluation_table(sales, config, series_map)
    cells = sensitivity_grid(sales, config, series_map)
    default = next((cell for cell in cells if cell["is_default"]), None)
    peaks = peak_evaluation(sales, config, series_map)
    promoted = config["engine"] == "v2"
    if promoted:
        note = ("Motor v2 promovido na Etapa 15.1: atende aos quatro critérios da avaliação com meses de pico."
                if peaks["criteria"]["all_met"] else
                "Atenção: o motor v2 está configurado como oficial, mas não atende a todos os critérios da avaliação com meses de pico.")
    else:
        note = "Nada foi promovido: as previsões oficiais seguem o motor v1."
    result = {
        "engine": config["engine"],
        "official_engine_label": ENGINE_LABELS[config["engine"]],
        "promotion_status": "promovido" if promoted else "pendente",
        "promotion_note": note,
        "config": {
            "candidates": list(config["candidates"]),
            "rolling": config["rolling"],
            "nested": config["nested"],
            "parsimony_margin": config["parsimony_margin"],
            "promotion": config["promotion"],
        },
        "baseline": {"model": BASELINE_MODEL, "label": BASELINE_LABEL},
        "selection": _selection(records, official, list(config["candidates"])),
        "nested": {
            "outer_windows": config["nested"]["outer_windows"],
            "outer_train_lengths": None if default is None else default["outer_train_lengths"],
            "skus": nested["skus"],
            "aggregate": nested["aggregate"],
            "rolling_vs_v1": nested["rolling_vs_v1"],
            "criteria": nested["criteria"],
        },
        "sensitivity": {"cells": cells, "summary": summarize_sensitivity(cells)},
        "peak_evaluation": peaks,
        "intervals": _intervals(records, interval_calibration(sales, config, series_map), config),
        "limitations": LIMITATIONS,
        "field_nature": FIELD_NATURE,
        "requires_human_review": True,
    }
    return _clean(result)
