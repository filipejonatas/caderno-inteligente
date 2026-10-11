import os

import pytest


@pytest.fixture(scope="session", autouse=True)
def _api_without_global_login():
    """O login global da API vem ligado por padrão; os testes de rotas o desligam (inclusive fixtures de módulo e de sessão).
    Quem testa a barreira liga de novo com monkeypatch.setenv("AUTH_REQUIRED", "true")."""
    previous = os.environ.get("AUTH_REQUIRED")
    os.environ["AUTH_REQUIRED"] = "false"
    yield
    if previous is None:
        os.environ.pop("AUTH_REQUIRED", None)
    else:
        os.environ["AUTH_REQUIRED"] = previous
