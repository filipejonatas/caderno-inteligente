from pathlib import Path
import pytest
from caderno_inteligente.ingestion import IngestionError, load_workbook

SOURCE = Path("data/source/Base de Dados - Caderno Inteligente.xlsm")

def test_loads_required_sheets_without_mutating_source():
    before = SOURCE.stat().st_mtime_ns
    data = load_workbook(SOURCE)
    assert {"Produtos", "Sell_Out", "Capacidade_Semanal"}.issubset(data)
    assert len(data["Produtos"]) == 50
    assert SOURCE.stat().st_mtime_ns == before

def test_rejects_missing_file():
    with pytest.raises(IngestionError, match="não encontrado"):
        load_workbook("inexistente.xlsm")
