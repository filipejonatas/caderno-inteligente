"""Additive run comparison route; reads stored snapshots only and never touches the official pipeline."""
from typing import Callable

from fastapi import APIRouter, HTTPException, Query

from caderno_inteligente.run_comparison import compare_runs


def create_run_comparison_router(persistence: Callable) -> APIRouter:
    router = APIRouter(prefix="/api")

    # A separate path avoids the existing /api/runs/{run_id} route, whose int validation would capture "compare".
    @router.get("/run-comparisons")
    def run_comparison(base: int = Query(..., ge=1), target: int = Query(..., ge=1)):
        if base == target:
            raise HTTPException(422, "Selecione duas execuções diferentes para comparar.")
        store = persistence()
        runs = {run_id: store.get_run(run_id) for run_id in (base, target)}
        missing = [str(run_id) for run_id, run in runs.items() if run is None]
        if missing:
            raise HTTPException(404, f"Execução não encontrada: {', '.join(missing)}")
        return compare_runs(runs[base], runs[target])

    return router
