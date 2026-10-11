"""Barreira global: com AUTH_REQUIRED ligado, nenhuma rota de /api responde sem login (exceto login, health e system)."""
import pytest
from fastapi.testclient import TestClient

import backend.main as main
from caderno_inteligente.auth import issue_token

SECRET = "segredo-de-teste-" + "x" * 30


class FakeUsers:
    def active_user(self, email):
        return {"email": email, "name": "Ana"} if email == "pcp@exemplo.com" else None


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("AUTH_REQUIRED", "true")
    monkeypatch.setenv("AUTH_SECRET", SECRET)
    monkeypatch.setattr(main, "user_store", lambda: FakeUsers())
    return TestClient(main.app)


@pytest.mark.parametrize("path", ["/api/overview", "/api/priorities", "/api/dataset", "/api/dataset/template", "/api/skus/cadastro", "/api/config"])
def test_data_routes_refuse_anonymous_calls(client, path):
    response = client.get(path)
    assert response.status_code == 401 and response.headers["www-authenticate"] == "Bearer"


def test_invalid_and_unknown_user_tokens_are_refused(client):
    assert client.get("/api/overview", headers={"Authorization": "Bearer lixo"}).status_code == 401
    stranger = issue_token(SECRET, "outro@exemplo.com", "X", 3600)[0]
    assert client.get("/api/overview", headers={"Authorization": f"Bearer {stranger}"}).status_code == 401


def test_public_routes_stay_open(client):
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/system").status_code == 200
    assert client.post("/api/auth/login", json={"email": "a@b.com", "password": "senha-qualquer"}).json()["detail"] == "E-mail ou senha incorretos."


def test_valid_token_passes_the_gate(client):
    token = issue_token(SECRET, "pcp@exemplo.com", "Ana", 3600)[0]
    assert client.get("/api/overview", headers={"Authorization": f"Bearer {token}"}).status_code != 401


def test_refusal_carries_cors_headers_and_preflight_is_allowed(client):
    origin = {"Origin": "http://localhost:5173"}
    assert client.options("/api/overview", headers={**origin, "Access-Control-Request-Method": "GET"}).status_code in (200, 204)
    assert client.get("/api/overview", headers=origin).status_code == 401


def test_login_is_unavailable_without_a_secret_in_production(client, monkeypatch):
    monkeypatch.delenv("AUTH_SECRET")
    monkeypatch.setattr(main, "settings", lambda: type("S", (), {"production": True})())
    assert client.get("/api/overview").status_code == 503


def test_gate_is_off_with_auth_required_false(monkeypatch):
    monkeypatch.setenv("AUTH_REQUIRED", "false")
    assert TestClient(main.app).get("/api/health").status_code == 200


def test_gate_holds_behind_a_root_path(client):
    assert TestClient(main.app, root_path="/foo").get("/foo/api/overview").status_code == 401
