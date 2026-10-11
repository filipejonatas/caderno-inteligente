"""Rotas /api/users: só quem entrou lista e cadastra; sem cadastro público."""
import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient

from backend.registry import create_registry_router
from caderno_inteligente.auth import UserStore, issue_token
from caderno_inteligente.dataset_store import Database

SECRET = "segredo-de-teste-" + "x" * 30


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTH_SECRET", SECRET)
    monkeypatch.delenv("AUTH_REQUIRED", raising=False)
    database = Database(sqlite_path=tmp_path / "dataset.db")
    UserStore(database).create_user("pcp@exemplo.com", "Ana PCP", "senha-gerada-no-teste")
    state = {"writable": True}

    def guard():
        if not state["writable"]:
            raise HTTPException(403, "Somente leitura.")

    app = FastAPI()
    app.include_router(create_registry_router(production=lambda: False, data_source=lambda: "banco", store=lambda: None,
                                              users=lambda: UserStore(database), write_access=Depends(guard), on_change=lambda: None))
    auth = {"Authorization": "Bearer " + issue_token(SECRET, "pcp@exemplo.com", "Ana PCP", 3600)[0]}
    return TestClient(app), auth, state, database


def test_requires_login_even_without_auth_required(env):
    client, _, _, _ = env
    assert client.get("/api/users").status_code == 401
    assert client.post("/api/users", json={"email": "novo@exemplo.com", "name": "Novo", "password": "senha-forte-123"}).status_code == 401


def test_create_and_list_users(env):
    client, auth, _, database = env
    response = client.post("/api/users", json={"email": " Novo@Exemplo.com ", "name": "Novo", "password": "senha-forte-123"}, headers=auth)
    assert response.status_code == 201 and response.json() == {"email": "novo@exemplo.com", "name": "Novo"}
    assert UserStore(database).authenticate("novo@exemplo.com", "senha-forte-123") is not None
    items = client.get("/api/users", headers=auth).json()["items"]
    assert [item["email"] for item in items] == ["novo@exemplo.com", "pcp@exemplo.com"]
    assert all("password" not in item and "password_hash" not in item for item in items)


def test_duplicate_short_password_invalid_email_and_read_only(env):
    client, auth, state, _ = env
    body = {"email": "pcp@exemplo.com", "name": "", "password": "senha-forte-123"}
    assert client.post("/api/users", json=body, headers=auth).status_code == 409
    assert client.post("/api/users", json={**body, "email": "a@b.com", "password": "curta"}, headers=auth).status_code == 422
    assert client.post("/api/users", json={**body, "email": "sem-arroba"}, headers=auth).status_code == 422
    state["writable"] = False
    assert client.post("/api/users", json={**body, "email": "a@b.com"}, headers=auth).status_code == 403
