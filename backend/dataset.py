"""Upload da planilha pela tela (U.1): prévia, aplicação com versões, voltar para versão, restaurar a original e modelo.

Gravar exige, nesta ordem: WRITE_ENABLED (403), DATA_SOURCE=banco (409) e login sempre (401/503), mesmo com
AUTH_REQUIRED=false (D2+D6). O corpo é o arquivo bruto (application/octet-stream), lido com corte no limite de tamanho (413).
A prévia não grava nada; a aplicação refaz a prévia inteira e grava numa transação só (`DatasetStore.apply_version`).
O log registra ação, versão e o começo do sha256, nunca e-mail nem conteúdo. Para quem não entrou, o e-mail de quem
enviou sai mascarado ("p***@dominio"). Sem a migração 005 (ou com o banco indisponível), leitura e escrita respondem 503.
"""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any, Callable
from urllib.parse import unquote

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, Response

from backend.registry import LOGIN_UNAVAILABLE, UPLOAD_LOGIN, auth_secret, login_user, optional_user
from caderno_inteligente.auth import UserStore
from caderno_inteligente.dataset_merge import POLICY_TEXT
from caderno_inteligente.dataset_store import DatasetStore, DatasetStoreError, DatasetVersionConflict, DatasetVersionNotFound
from caderno_inteligente.dataset_upload import drop_skus, engine_reference, prepare_upload
from caderno_inteligente.supply_plan import load_supply_settings
from caderno_inteligente.transformations import safe_normalise
from caderno_inteligente.upload_safety import UploadRejected, load_upload_settings, safe_filename
from caderno_inteligente.validation import validate_dataset
from caderno_inteligente.workbook_writer import write_workbook

try:  # PostgreSQL sem a migração 005: a tabela dataset_versions ou a coluna active_version_id não existem.
    from psycopg.errors import UndefinedColumn, UndefinedTable
    _MISSING_SCHEMA: tuple[type[Exception], ...] = (UndefinedTable, UndefinedColumn)
except ImportError:  # pragma: no cover - psycopg só é necessário com DATABASE_URL
    _MISSING_SCHEMA = ()

logger = logging.getLogger("caderno_inteligente.api")

EXAMPLE_FILE = Path(__file__).resolve().parents[1] / "docs/exemplos/atualizacao-2026-10.xlsx"
XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
SPREADSHEET_MODE = "A atualização da base pela tela exige a base no banco (DATA_SOURCE=banco). Esta publicação lê a planilha."
READ_ONLY = "Esta publicação está em modo somente leitura (WRITE_ENABLED=false)."
CONFLICT = "Outra pessoa atualizou a base; refaça a prévia."
MIGRATION_MISSING = "O banco ainda não tem as tabelas de versões da base; rode a migração 005 (supabase/migrations/005_dataset_uploads.sql)."
DISABLED_MESSAGES = {"planilha": SPREADSHEET_MODE, "somente_leitura": READ_ONLY, "login": UPLOAD_LOGIN, "login_indisponivel": LOGIN_UNAVAILABLE}


def _br_date(iso: str | None) -> str:
    return f"{iso[8:10]}/{iso[5:7]}/{iso[:4]}" if iso else "data desconhecida"


def mask_email(email: str | None) -> str | None:
    """"pcp@exemplo.com" → "p***@exemplo.com" (para quem não entrou)."""
    if not email:
        return email
    local, at, domain = email.partition("@")
    return f"{local[:1]}***@{domain}" if at else "***"


def create_dataset_router(*, production: Callable[[], bool], data_source: Callable[[], str], store: Callable[[], DatasetStore],
                          users: Callable[[], UserStore], write_access, settings_file: Path,
                          current_info: Callable[[], dict[str, Any]], engine_summary: Callable[[dict | None], dict[str, Any]],
                          original_loader: Callable[[], dict[str, pd.DataFrame]], on_change: Callable[[], None],
                          describe_error: Callable[[str, Exception], str],
                          supply_settings: Callable[[], dict[str, Any]] | None = None) -> APIRouter:
    """`supply_settings` devolve config/supply_plan.json (padrão: `load_supply_settings()`); a prévia e a versão gravada usam a
    mesma data de planejamento que o motor (`resolve_supply_settings`)."""
    router = APIRouter(prefix="/api/dataset")
    plan_settings = supply_settings or load_supply_settings
    write_check = getattr(write_access, "dependency", write_access)  # Depends(...) ou a função de checagem

    def upload_settings() -> dict[str, Any]:
        return load_upload_settings(settings_file)

    def database_mode() -> None:
        if data_source() != "banco":
            raise HTTPException(409, SPREADSHEET_MODE)

    def login(request: Request) -> dict[str, str]:
        return login_user(request, users, production)

    def unavailable(error: Exception) -> HTTPException:
        if isinstance(error, DatasetStoreError):
            return HTTPException(503, str(error))
        logger.warning("dataset_store_unavailable error_type=%s", type(error).__name__)
        return HTTPException(503, MIGRATION_MISSING)

    def store_state() -> dict[str, Any]:
        """Estado da base (versão e versão ativa); 503 com a mensagem do banco quando falta a migração 005."""
        try:
            return store().state()
        except (DatasetStoreError, *_MISSING_SCHEMA) as error:
            raise unavailable(error) from error

    def store_ready() -> None:
        store_state()

    editor = [write_access, Depends(database_mode), Depends(store_ready)]

    async def read_body(request: Request, limit: int) -> bytes:
        """Corpo com corte em `limit`: 413 mesmo sem Content-Length (envio em partes)."""
        declared = request.headers.get("content-length", "")
        too_large = UploadRejected("FILE_TOO_LARGE", 413, f"Arquivo maior que o limite de {limit / (1024 * 1024):g} MB.")
        if declared.isdigit() and int(declared) > limit:
            raise too_large
        chunks, received = [], 0
        async for chunk in request.stream():
            received += len(chunk)
            if received > limit:
                raise too_large
            chunks.append(chunk)
        return b"".join(chunks)

    def rejected(error: UploadRejected) -> JSONResponse:
        return JSONResponse({"detail": error.message, "code": error.code}, status_code=error.status)

    def blocked(preview: dict) -> JSONResponse:
        count = len(preview["errors"])
        noun = "erro que bloqueia" if count == 1 else "erros que bloqueiam"
        return JSONResponse(jsonable_encoder({"detail": f"A planilha tem {count} {noun} a aplicação.", "preview": preview}), status_code=422)

    def log(action: str, version: Any, sha: str | None) -> None:
        logger.info("dataset_upload action=%s version=%s sha=%s", action, version, (sha or "")[:12])

    def reference_fields(dataset: dict[str, pd.DataFrame]) -> dict[str, Any]:
        """A referência que o motor usará com este conjunto (inclusive data fixa em config/supply_plan.json)."""
        return engine_reference(safe_normalise(dataset)[0], plan_settings())

    def active_state(current: dict[str, pd.DataFrame], inactive: set[str]) -> dict[str, Any]:
        """Versão e referência da base ativa, do conjunto carregado agora (sem os inativos, como o motor o vê), não do cache."""
        found = reference_fields(drop_skus(current, inactive))
        return {"version": store().version(), "reference_date": found["reference_date"], "sales_last_month": found["sales_last_month"]}

    def before_engine() -> dict[str, Any] | None:
        try:
            return engine_summary(None)
        except Exception as error:  # noqa: BLE001 - a prévia continua sem o "antes"; a causa vai para o log redigido.
            logger.warning("dataset_upload engine_before_failed error_type=%s", type(error).__name__)
            return None

    def preview_of(content: bytes, filename: str) -> tuple[dict, dict | None]:
        current_store = store()
        try:
            current, inactive = current_store.load_dataset(include_inactive=True), current_store.inactive_skus()
            edited = current_store.edited_skus()
        except (DatasetStoreError, *_MISSING_SCHEMA) as error:
            raise unavailable(error) from error
        return prepare_upload(content, filename, current=current, state=active_state(current, inactive),
                              settings=upload_settings(), engine=engine_summary, current_engine=before_engine(),
                              edited_skus=edited, inactive_skus=inactive, describe_error=describe_error,
                              supply_settings=plan_settings())

    def write(dataset: dict[str, pd.DataFrame], *, action: str, user: dict, expected_version: int | None = None, **fields) -> dict[str, Any]:
        if "reference_date" not in fields or "sales_last_month" not in fields:
            found = reference_fields(drop_skus(dataset, set(fields.get("inactive_skus") or ())))
            fields.setdefault("reference_date", found["reference_date"])
            fields.setdefault("sales_last_month", found["sales_last_month"])
        try:
            saved = store().apply_version(dataset, action=action, user_email=user["email"], expected_version=expected_version,
                                          keep=upload_settings()["max_versions"], **fields)
        except DatasetVersionConflict as error:
            raise HTTPException(409, CONFLICT) from error
        except DatasetStoreError as error:
            raise HTTPException(422, describe_error("Não foi possível gravar a base", error)) from error
        on_change()
        log("apply" if action == "upload" else action, saved["version"], saved["content_sha256"])
        return {"version": saved["version"], "version_id": saved["version_id"], "reference_date": fields["reference_date"],
                "sales_last_month": fields["sales_last_month"], "content_sha256": saved["content_sha256"], "pruned_versions": saved["pruned"]}

    def expected_version_header(request: Request, *, required: bool) -> int | None:
        raw = (request.headers.get("x-expected-version") or "").strip()
        if not raw and not required:
            return None
        if not raw.isdigit():
            raise HTTPException(422, "Envie X-Expected-Version com a versão da prévia.")
        expected = int(raw)
        if expected != store_state()["version"]:
            raise HTTPException(409, CONFLICT)
        return expected

    @router.get("")
    def dataset_status(request: Request):
        settings = upload_settings()
        info = current_info()
        source = data_source()
        version = active_id = active = None
        if source == "banco":
            state = store_state()
            version, active_id, active = state["version"], state["active_version_id"], state["active"]
        if active is not None:
            origin = active["action"]
        elif source != "banco" or info.get("matches_original"):
            origin = "original"
        else:
            origin = "desconhecida"  # base importada pela linha de comando, sem versão no histórico
        reason = None
        if source != "banco":
            reason = "planilha"
        else:
            try:
                write_check()
            except HTTPException:
                reason = "somente_leitura"
        if reason is None and auth_secret(production()) is None:
            reason = "login_indisponivel"
        viewer = optional_user(request, users, production)
        if reason is None and viewer is None:
            reason = "login"
        uploaded_by = active["user_email"] if active else None
        return {
            "data_source": source, "version": version, "active_version_id": active_id, "origin": origin,
            "reference_date": info.get("reference_date"), "reference_source": info.get("reference_source"),
            "sales_last_month": info.get("sales_last_month"), "content_sha256": info.get("content_sha256"),
            "source_sha256": info.get("source_sha256"), "matches_original": info.get("matches_original"),
            "uploaded_by": uploaded_by if viewer else mask_email(uploaded_by), "uploaded_at": active["created_at"] if active else None,
            "filename": active["filename"] if active else None,
            "upload_enabled": reason is None, "upload_disabled_reason": reason, "upload_disabled_message": DISABLED_MESSAGES.get(reason),
            "max_upload_bytes": settings["max_upload_bytes"], "accepted_extensions": settings["accepted_extensions"],
            "max_versions": settings["max_versions"], "policy": POLICY_TEXT,
        }

    @router.get("/template")
    def template():
        # Com os inativos: reenviar o modelo não apaga um SKU só porque ele está inativo.
        dataset = store().load_dataset(include_inactive=True) if data_source() == "banco" else original_loader()
        reference = current_info().get("reference_date")
        content = write_workbook(dataset, title=f"Caderno Inteligente — modelo de atualização (base de {_br_date(reference)})")
        name = f"modelo-caderno-inteligente-{reference or 'base'}.xlsx"
        return Response(content, media_type=XLSX_MEDIA_TYPE, headers={"Content-Disposition": f'attachment; filename="{name}"'})

    @router.get("/example")
    def example():
        """Pacote de exemplo fictício (docs/exemplos): serve para treinar o envio; a prévia o marca como exemplo."""
        if not EXAMPLE_FILE.is_file():
            raise HTTPException(404, "O arquivo de exemplo não está disponível nesta publicação.")
        return Response(EXAMPLE_FILE.read_bytes(), media_type=XLSX_MEDIA_TYPE,
                        headers={"Content-Disposition": f'attachment; filename="{EXAMPLE_FILE.name}"'})

    @router.post("/preview", dependencies=editor)
    async def preview(request: Request, user: dict = Depends(login)):
        settings = upload_settings()
        filename = safe_filename(unquote(request.headers.get("x-filename") or ""))
        try:
            content = await read_body(request, settings["max_upload_bytes"])
            result, _ = await run_in_threadpool(preview_of, content, filename)
        except UploadRejected as error:
            return rejected(error)
        log("preview", result["expected_version"], result["file"]["sha256"])
        if not result["can_apply"]:
            return blocked(result)
        return jsonable_encoder(result)

    @router.post("/apply", dependencies=editor)
    async def apply(request: Request, user: dict = Depends(login)):
        settings = upload_settings()
        filename = safe_filename(unquote(request.headers.get("x-filename") or ""))
        try:
            content = await read_body(request, settings["max_upload_bytes"])
        except UploadRejected as error:
            return rejected(error)
        confirm = (request.headers.get("x-confirm-sha256") or "").strip().lower()
        if confirm != hashlib.sha256(content).hexdigest():
            return JSONResponse({"detail": "O arquivo enviado não é o mesmo da prévia (X-Confirm-Sha256); refaça a prévia.",
                                 "code": "CONFIRM_MISMATCH"}, status_code=422)
        expected = expected_version_header(request, required=True)
        try:
            result, merged = await run_in_threadpool(preview_of, content, filename)
        except UploadRejected as error:
            return rejected(error)
        if merged is None:
            return blocked(result)
        summary = {**result, "engine": {**result["engine"], "before": None}}
        file = result["file"]
        saved = await run_in_threadpool(lambda: write(
            merged, action="upload", user=user, expected_version=expected, filename=file["filename"], file_sha256=file["sha256"],
            size_bytes=file["size_bytes"], reference_date=result["reference"]["after"],
            sales_last_month=result["reference"]["sales_last_month_after"], summary=jsonable_encoder(summary),
            inactive_skus=store().inactive_skus()))
        return jsonable_encoder({**saved, "preview": result})

    @router.get("/versions")
    def versions(request: Request):
        settings = upload_settings()
        if data_source() != "banco":
            return {"data_source": data_source(), "active_version_id": None, "max_versions": settings["max_versions"], "items": []}
        active_id = store_state()["active_version_id"]
        try:
            rows = store().list_versions()
        except (DatasetStoreError, *_MISSING_SCHEMA) as error:
            raise unavailable(error) from error
        signed_in = optional_user(request, users, production) is not None
        items = [{**{key: value for key, value in row.items() if key != "summary"}, "active": row["id"] == active_id,
                  "user_email": row["user_email"] if signed_in else mask_email(row["user_email"])} for row in rows]
        return {"data_source": "banco", "active_version_id": active_id, "max_versions": settings["max_versions"], "items": items}

    def checked(dataset: dict[str, pd.DataFrame]) -> None:
        errors = validate_dataset(dataset, max_examples=upload_settings()["max_examples_per_error"])["errors"]
        if errors:
            found = "; ".join(item["message"] for item in errors[:3])
            raise HTTPException(422, f"A versão guardada não passa na validação: {found}.")

    @router.post("/versions/{version_id}/restore", dependencies=editor)
    def restore(version_id: int, request: Request, user: dict = Depends(login)):
        expected = expected_version_header(request, required=True)
        try:
            dataset, inactive, row = store().version_snapshot(version_id)
        except DatasetVersionNotFound as error:
            raise HTTPException(404, str(error)) from error
        checked(dataset)
        saved = write(dataset, action="restore", user=user, expected_version=expected, restored_from=version_id,
                      filename=row["filename"], file_sha256=row["file_sha256"], size_bytes=row["size_bytes"], inactive_skus=inactive)
        return {**saved, "restored_from": version_id, "preview": None}

    @router.post("/restore-original", dependencies=editor)
    def restore_original(request: Request, user: dict = Depends(login)):
        expected = expected_version_header(request, required=True)
        dataset = original_loader()
        checked(dataset)
        saved = write(dataset, action="original", user=user, expected_version=expected, inactive_skus=set())
        return {**saved, "restored_from": None, "preview": None}

    return router
