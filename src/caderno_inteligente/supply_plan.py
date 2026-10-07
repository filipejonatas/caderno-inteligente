"""Plano de suprimento da Etapa 15: projeção semanal de estoque, ordens planejadas e ajustes de OP.

Na 15.0 só existe a configuração, gravada antes do código que a usa (protocolo da Etapa 15): a data de planejamento,
a janela de decisão, a cobertura-alvo das ordens, o limite de excesso projetado e os dias por mês usados para
converter a demanda mensal em diária. A projeção entra na 15.3.
"""
from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path
from typing import Any

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "config" / "supply_plan.json"

DEFAULT_SETTINGS: dict[str, Any] = {
    "reference_date": "2026-09-14",
    "decision_window_weeks": 4,
    "target_cover_weeks": 4,
    "excess_coverage_days": 90,
    "days_per_month": 30.4,
}


def load_supply_settings(path: str | Path | None = None) -> dict[str, Any]:
    values = dict(DEFAULT_SETTINGS)
    source = DEFAULT_PATH if path is None else Path(path)
    if source.exists() or path is not None:
        overrides = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(overrides, dict) or set(overrides) - set(values):
            raise ValueError("Configuração do plano de suprimento contém campos desconhecidos")
        values.update(overrides)
    return _validate_settings(values)


def _validate_settings(values: dict[str, Any]) -> dict[str, Any]:
    def number(key: str) -> float:
        value = values[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"Parâmetro do plano de suprimento inválido: {key}")
        return float(value)

    try:
        reference = date.fromisoformat(str(values["reference_date"]))
    except ValueError as error:
        raise ValueError("reference_date deve ser uma data AAAA-MM-DD") from error
    if reference.weekday() != 0:
        raise ValueError("reference_date deve ser uma segunda-feira, como as semanas de Capacidade_Semanal")
    values["reference_date"] = reference.isoformat()
    for key in ("decision_window_weeks", "target_cover_weeks", "excess_coverage_days"):
        if number(key) != int(number(key)) or number(key) < 1:
            raise ValueError(f"Parâmetro precisa ser inteiro ≥ 1: {key}")
        values[key] = int(values[key])
    if not 28 <= number("days_per_month") <= 31:
        raise ValueError("days_per_month deve estar entre 28 e 31")
    values["days_per_month"] = float(values["days_per_month"])
    return values
