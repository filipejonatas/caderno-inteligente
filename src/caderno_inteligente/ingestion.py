from __future__ import annotations
from pathlib import Path
import pandas as pd
from .schemas import SCHEMAS

HEADER_ROW_OFFSET = 2  # As duas primeiras linhas são título e espaçamento.

class IngestionError(RuntimeError):
    pass

def load_workbook(path: str | Path) -> dict[str, pd.DataFrame]:
    """Lê apenas as abas da Etapa 1; nunca grava nem modifica o XLSM de origem."""
    source = Path(path)
    if not source.is_file():
        raise IngestionError(f"Arquivo não encontrado: {source}")
    if source.suffix.lower() != ".xlsm":
        raise IngestionError("A fonte precisa ser um arquivo XLSM.")
    with pd.ExcelFile(source, engine="openpyxl") as workbook:
        missing = sorted(set(SCHEMAS) - set(workbook.sheet_names))
        if missing:
            raise IngestionError(f"Abas obrigatórias ausentes: {', '.join(missing)}")
        return {sheet: pd.read_excel(workbook, sheet_name=sheet, skiprows=HEADER_ROW_OFFSET)
                for sheet in SCHEMAS}
