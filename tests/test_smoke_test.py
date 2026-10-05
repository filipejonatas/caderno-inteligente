import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import backend.main as main
from scripts.smoke_test import Response, main as smoke_main

ROOT = Path(__file__).resolve().parents[1]
BACKEND, FRONTEND = "http://api.test", "http://localhost:5173"
VERCEL_HEADERS = {item["key"].lower(): item["value"] for item in json.loads((ROOT / "frontend/vercel.json").read_text(encoding="utf-8"))["headers"][0]["headers"]}
INDEX = '<!doctype html><html><head><script type="module" src="/assets/index.js"></script></head><body><div id="root"></div></body></html>'


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "RUNS_DB", tmp_path / "runs.db")
    monkeypatch.setattr(main, "CASES_DB", tmp_path / "cases.db")
    monkeypatch.setattr(main, "FEEDBACK_DB", tmp_path / "feedback.db")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    return TestClient(main.app)


def requester(client, *, frontend_headers=VERCEL_HEADERS, bundle="console.log('ok')", spa_rewrite=True):
    def request(method, url, headers, body):
        if url.startswith(BACKEND):
            response = client.request(method, url[len(BACKEND):], headers=headers, content=body)
            return Response(response.status_code, {k.lower(): v for k, v in response.headers.items()}, response.content)
        path = url[len(FRONTEND):]
        if path.startswith("/assets/"):
            return Response(200, {"content-type": "text/javascript"}, bundle.encode())
        if path not in ("", "/") and not spa_rewrite:
            return Response(404, {}, b"Not Found")
        return Response(200, {"content-type": "text/html", **frontend_headers}, INDEX.encode())
    return request


def test_full_smoke_passes_against_real_api_and_vercel_headers(client, capsys):
    assert smoke_main(["--backend", BACKEND, "--frontend", FRONTEND, "--expect-environment", "development"], requester(client)) == 0
    output = capsys.readouterr().out
    assert "FALHA" not in output
    assert "sondagem de escrita recusada (nada gravado)" in output
    assert client.get("/api/feedback").json() == []  # the write probe never records data


def test_readonly_expectation_fails_when_writes_are_enabled(client, capsys):
    assert smoke_main(["--backend", BACKEND, "--expect-readonly"], requester(client)) == 1
    assert "FALHA backend · WRITE_ENABLED = False" in capsys.readouterr().out


def test_readonly_deployment_passes_with_expectation(client, monkeypatch):
    from dataclasses import replace
    monkeypatch.setattr(main, "SETTINGS", replace(main.SETTINGS, write_enabled=False, demo_mode=True))
    assert smoke_main(["--backend", BACKEND, "--expect-readonly", "--expect-demo"], requester(client)) == 0


def test_missing_spa_rewrite_and_headers_are_reported(client, capsys):
    assert smoke_main(["--backend", BACKEND, "--frontend", FRONTEND], requester(client, frontend_headers={}, spa_rewrite=False)) == 1
    output = capsys.readouterr().out
    assert "FALHA frontend · /prioridades entrega a SPA (rewrite)" in output
    assert "FALHA frontend · Content-Security-Policy presente" in output


def test_secret_in_bundle_is_reported(client, capsys):
    leaking = requester(client, bundle='const u="postgresql://u:p@h/db"')
    assert smoke_main(["--backend", BACKEND, "--frontend", FRONTEND], leaking) == 1
    assert "sem segredos" in capsys.readouterr().out


def test_network_failure_is_a_failed_check_not_a_crash(capsys):
    def offline(method, url, headers, body):
        raise ConnectionError("recusada")
    assert smoke_main(["--backend", BACKEND], offline) == 1
    assert "FALHA rede" in capsys.readouterr().out
