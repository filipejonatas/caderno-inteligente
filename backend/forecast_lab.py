"""Rota aditiva do laboratório de previsão (Etapa 14.3); lê o pipeline em cache e nunca altera a previsão oficial."""
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Callable

from fastapi import APIRouter, HTTPException

from caderno_inteligente.forecast_engine_config import load_engine_config
from caderno_inteligente.forecast_lab import build_forecast_lab


def _signature(path: Path) -> tuple[int, int]:
    stat = path.stat()
    return stat.st_mtime_ns, stat.st_size


def create_forecast_lab_router(*, pipeline: Callable, source: Path, engine_config_file: Path,
                               source_hash: Callable[[], str] | None = None,
                               describe_error: Callable[[str, Exception], str] | None = None) -> APIRouter:
    router = APIRouter(prefix="/api")
    describe = describe_error or (lambda message, error: f"{message}: {error}")
    lock = Lock()
    cache: dict[str, object] = {}

    @router.get("/forecast-lab")
    def forecast_lab():
        try:
            config = load_engine_config(engine_config_file)
        except (OSError, ValueError) as error:
            raise HTTPException(422, describe("Configuração do motor de previsão inválida", error)) from error
        built = pipeline()
        # com source_hash (base ativa do upload), o próprio hash entra na chave do cache; sem ele, a assinatura do arquivo
        source_key = source_hash() if source_hash is not None else _signature(source)
        key = (id(built), source_key, _signature(engine_config_file))
        with lock:  # o cálculo leva alguns segundos: serializa para chamadas simultâneas não o repetirem
            if cache.get("key") != key:
                body = build_forecast_lab(built[0]["Vendas_24m"], built[5], config)
                body["generated_at"] = datetime.now(timezone.utc).isoformat()
                body["source"] = {"sha256": source_key if source_hash is not None else hashlib.sha256(source.read_bytes()).hexdigest()}
                cache.update(key=key, body=body)
            return cache["body"]

    return router
