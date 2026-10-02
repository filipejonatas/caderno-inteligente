from __future__ import annotations
import json
from pathlib import Path


def write_quality_report(report: dict, destination: str | Path) -> Path:
    """Persiste o relatório derivado; a fonte XLSM nunca é gravada."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return destination
