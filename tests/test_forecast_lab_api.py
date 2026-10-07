from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.forecast_lab as lab_module
from backend.forecast_lab import create_forecast_lab_router
from backend.main import app

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def lab(client):
    response = client.get("/api/forecast-lab")
    assert response.status_code == 200
    return response.json()


def test_lab_is_a_laboratory_and_asks_for_human_review(lab):
    assert lab["engine"] == "v1" and lab["promotion_status"] == "pendente"
    assert lab["requires_human_review"] is True
    assert "Nada foi promovido" in lab["promotion_note"]
    assert lab["source"]["sha256"] and lab["generated_at"]
    assert set(lab["field_nature"]) == {"nested", "sensitivity", "selection", "intervals"}


def test_lab_never_changes_the_official_forecast(client):
    before = client.get("/api/forecasts").json()
    client.get("/api/forecast-lab")
    assert client.get("/api/forecasts").json() == before


def test_selection_counts_every_sku_once_per_engine(lab):
    selection = lab["selection"]

    assert selection["skus"] == 50 and selection["skipped_skus"] == 0
    assert sum(model["official_selected_skus"] for model in selection["models"]) == 50
    assert sum(model["rolling_selected_skus"] for model in selection["models"]) == 50
    assert [model["complexity"] for model in selection["models"]] == sorted(model["complexity"] for model in selection["models"])
    assert selection["changed_skus"] == len(selection["changed"]) > 0
    for item in selection["changed"]:
        assert item["official_model"] != item["rolling_model"]


def test_nested_block_matches_the_default_cell_of_the_grid(lab):
    nested = lab["nested"]
    cells = lab["sensitivity"]["cells"]
    default = [cell for cell in cells if cell["is_default"]]

    assert len(default) == 1 and len(cells) == 6
    assert default[0]["outer_train_lengths"] == nested["outer_train_lengths"] == [18, 21]
    assert default[0]["rolling_wape"] == nested["aggregate"]["rolling"]["weighted_wape"]
    assert default[0]["relative_wape_gain"] == nested["criteria"]["relative_wape_gain"]
    assert nested["skus"] == 50 and sum(nested["rolling_vs_v1"].values()) == 50


def test_grid_summary_is_consistent_and_exposes_the_non_robust_cell(lab):
    summary = lab["sensitivity"]["summary"]
    cells = lab["sensitivity"]["cells"]

    assert summary["cells"] == len(cells)
    assert summary["cells_all_met"] == sum(cell["all_met"] for cell in cells)
    assert summary["robust"] is (summary["cells_all_met"] == summary["cells"])
    assert summary["min_relative_wape_gain"] == min(cell["relative_wape_gain"] for cell in cells)
    # A combinação de 3 origens e 2 janelas mínimas reverte o resultado: a tela precisa mostrá-la, não escondê-la.
    worst = next(cell for cell in cells if cell["outer_windows"] == 3 and cell["minimum_windows"] == 2)
    assert worst["relative_wape_gain"] < 0 and worst["all_met"] is False


def test_intervals_block_is_consistent_and_never_hides_how_often_the_band_missed(lab):
    block = lab["intervals"]
    calibration = block["calibration"]

    assert block["level"] == 0.8 and block["minimum_residuals"] == 6
    assert block["skus_with_band"] == len(block["items"]) and block["skus_with_band"] + block["skus_without_band"] == 50
    for item in block["items"]:
        assert 0 <= item["lower"] <= item["point"] <= item["upper"], item["sku"]
        assert item["residuals"] >= block["minimum_residuals"] and item["month"].endswith("-01")
    assert calibration["tested_months"] > 0 and calibration["hits"] <= calibration["tested_months"]
    assert calibration["coverage"] == pytest.approx(calibration["hits"] / calibration["tested_months"], abs=1e-4)
    assert calibration["nominal_level"] == block["level"]
    assert calibration["origin_train_lengths"] and calibration["skus_tested"] <= 50


def test_lab_response_has_no_nan_and_absent_values_stay_null(lab):
    text = json.dumps(lab, allow_nan=False)
    assert "NaN" not in text
    assert all(model["median_wape"] is not None for model in lab["selection"]["models"])


def _fake_pipeline(calls):
    sales = pd.DataFrame({"Mês": pd.date_range("2024-01-01", periods=24, freq="MS"), "SKU": "S", "Quantidade faturada": [10.0 + (m % 12) for m in range(24)]})
    forecasts = pd.DataFrame([{"sku": "S", "model": "moving_average_3"}])
    built = ({"Vendas_24m": sales}, None, None, None, None, forecasts)

    def pipeline():
        calls.append(1)
        return built

    return pipeline


def _router_app(tmp_path, config_text=None):
    config = tmp_path / "forecast_engine.json"
    config.write_text(config_text if config_text is not None else (ROOT / "config/forecast_engine.json").read_text(encoding="utf-8"), encoding="utf-8")
    source = tmp_path / "source.xlsm"
    source.write_bytes(b"x")
    calls: list[int] = []
    api = FastAPI()
    api.include_router(create_forecast_lab_router(pipeline=_fake_pipeline(calls), source=source, engine_config_file=config))
    return TestClient(api), config, source


def test_invalid_engine_config_returns_422_without_running_anything(tmp_path):
    client, _, _ = _router_app(tmp_path, '{"engine": "rolling"}')
    response = client.get("/api/forecast-lab")

    assert response.status_code == 422
    assert "Configuração do motor de previsão inválida" in response.json()["detail"]


def test_result_is_cached_until_the_source_or_the_config_changes(tmp_path, monkeypatch):
    built: list[int] = []
    real = lab_module.build_forecast_lab
    monkeypatch.setattr(lab_module, "build_forecast_lab", lambda *args, **kwargs: built.append(1) or real(*args, **kwargs))
    client, config, source = _router_app(tmp_path)

    first = client.get("/api/forecast-lab").json()
    assert client.get("/api/forecast-lab").json() == first and len(built) == 1

    source.write_bytes(b"xy")  # fonte mudou (tamanho)
    client.get("/api/forecast-lab")
    assert len(built) == 2

    config.write_text(config.read_text(encoding="utf-8").replace('"parsimony_margin": 0.05', '"parsimony_margin": 0.1'), encoding="utf-8")
    client.get("/api/forecast-lab")
    assert len(built) == 3
