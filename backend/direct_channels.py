"""Rotas aditivas dos canais diretos, isoladas do ranking operacional."""
from pathlib import Path
from threading import Lock
from typing import Callable

from fastapi import APIRouter, HTTPException, Query

from caderno_inteligente.direct_channels import SIGNAL_LABELS, SUGGESTION_LABELS, build_channel_findings, build_direct_channels, load_direct_channel_settings


def _signature(path: Path) -> tuple[int, int]:
    stat = path.stat()
    return stat.st_mtime_ns, stat.st_size


def create_direct_channel_router(dataset_loader: Callable, settings_file: Path, describe_error: Callable[[str, Exception], str] | None = None) -> APIRouter:
    router = APIRouter(prefix="/api")
    describe = describe_error or (lambda message, error: f"{message}: {error}")
    lock = Lock()
    cache: dict = {}

    def analysis() -> dict:
        """Reaproveita o dataset em cache do pipeline; invalida com ele e com o arquivo de limiares."""
        dataset, signature = dataset_loader(), _signature(settings_file)
        with lock:
            if cache.get("dataset") is dataset and cache.get("signature") == signature:
                return cache["result"]
            try:
                result = build_direct_channels(dataset, load_direct_channel_settings(settings_file))
            except (ValueError, KeyError) as error:
                raise HTTPException(422, describe("Análise de canais diretos bloqueada por dados/configuração inválidos", error)) from error
            cache.update(dataset=dataset, signature=signature, result=result)
            return result

    @router.get("/direct-channels")
    def direct_channels():
        """Visão observada dos canais diretos (faturamento), sem estoque por canal."""
        result = analysis()
        return {key: value for key, value in result.items() if key != "rows"}

    @router.get("/direct-channels/{channel}")
    def direct_channel(channel: str, signal: str | None = None, suggestion: str | None = None, search: str | None = Query(default=None, max_length=80)):
        result = analysis()
        summary = next((item for item in result["channels"] if item["code"] == channel), None)
        if summary is None:
            raise HTTPException(404, "Canal direto não encontrado")
        if signal is not None and signal not in SIGNAL_LABELS:
            raise HTTPException(422, "Sinal inválido")
        if suggestion is not None and suggestion not in SUGGESTION_LABELS:
            raise HTTPException(422, "Sugestão inválida")
        needle = (search or "").strip().casefold()
        rows = [
            row for row in result["rows"][channel]
            if (signal is None or signal in row["signals"]) and (suggestion is None or row["suggestion"]["code"] == suggestion)
            and (not needle or needle in row["sku"].casefold() or needle in (row["product"] or "").casefold())
        ]
        return {
            "reference_month": result["reference_month"], "channel": summary, "total": len(rows), "items": rows,
            "signal_labels": result["signal_labels"], "suggestion_labels": result["suggestion_labels"],
            "field_nature": result["field_nature"], "limitations": result["limitations"], "settings": result["settings"],
        }

    @router.get("/data-quality/channels")
    def channel_findings():
        """Achados entre abas que afetam a leitura dos canais; não reconcilia nada nem altera /api/data-quality."""
        return {"findings": analysis()["findings"]}

    return router
