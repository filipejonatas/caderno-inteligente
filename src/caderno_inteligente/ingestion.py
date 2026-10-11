from __future__ import annotations
from io import BytesIO
from pathlib import Path
import pandas as pd
from .schemas import SCHEMAS

HEADER_ROW_OFFSET = 2  # As duas primeiras linhas são título e espaçamento.
OPTIONAL_SHEETS = ("Precos_Produtos",)  # Lidas se existirem; sua ausência não bloqueia o pipeline.
OPTIONAL_COLUMNS = {"Precos_Produtos": ("SKU", "Preço unitário (R$)", "Vigência fictícia")}
ACCEPTED_EXTENSIONS = (".xlsx", ".xlsm")
EXAMPLE_MARKER = "arquivo de exemplo fictício"  # Texto no LEIA_ME do pacote de exemplo (D9).

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
        wanted = [*SCHEMAS, *(sheet for sheet in OPTIONAL_SHEETS if sheet in workbook.sheet_names)]
        return {sheet: pd.read_excel(workbook, sheet_name=sheet, skiprows=HEADER_ROW_OFFSET)
                for sheet in wanted}


def _row_labels(raw: pd.DataFrame, position: int) -> set[str]:
    return {str(value).strip() for value in raw.iloc[position].tolist() if pd.notna(value)}


def detect_header_row(raw: pd.DataFrame, required_columns, search_rows: int = 5) -> int | None:
    """Primeira linha (1-based, como no Excel) entre as `search_rows` iniciais que contém todas as colunas obrigatórias."""
    required = set(required_columns)
    for position in range(min(search_rows, len(raw))):
        if required <= _row_labels(raw, position):
            return position + 1
    return None


def _missing_header(raw: pd.DataFrame, required_columns, search_rows: int) -> list[str]:
    """Colunas obrigatórias que faltam na linha mais parecida com um cabeçalho."""
    required = list(required_columns)
    best = max((_row_labels(raw, position) for position in range(min(search_rows, len(raw)))),
               key=lambda labels: len(set(required) & labels), default=set())
    return [column for column in required if column not in best]


def read_workbook_bytes(content: bytes, *, search_rows: int = 5, max_rows: int | None = None) -> dict:
    """Lê uma planilha enviada (bytes) sem exigir abas: detecta o cabeçalho de cada aba conhecida e ignora as demais.

    XML com expansão de entidade (defusedxml) vira `UploadRejected` 422 `XML_UNSAFE`; arquivo ilegível ou corrompido por dentro
    (qualquer erro do leitor) vira 422 `NOT_XLSX`, nunca 500. Cada aba é lida com no máximo `max_rows` + 1 linhas de dados
    (padrão: max_rows_per_sheet de config/dataset_upload.json), para a prévia ainda apontar TOO_MANY_ROWS sem ler o excesso.
    A varredura de colunas/linhas (`upload_safety.scan_worksheets`) roda antes, em `check_upload`.
    """
    from defusedxml import DefusedXmlException
    from .upload_safety import UploadRejected, load_upload_settings

    limit = (load_upload_settings()["max_rows_per_sheet"] if max_rows is None else max_rows) + 1

    known = {**{sheet: schema.required_columns for sheet, schema in SCHEMAS.items()}, **OPTIONAL_COLUMNS}
    result = {"sheets": {}, "header_rows": {}, "missing_header": {}, "ignored_sheets": [], "example_marker": False}
    try:
        with pd.ExcelFile(BytesIO(content), engine="openpyxl") as workbook:
            for sheet in workbook.sheet_names:
                if sheet not in known:
                    result["ignored_sheets"].append(sheet)
                    if sheet == "LEIA_ME":
                        notes = pd.read_excel(workbook, sheet_name=sheet, header=None, nrows=limit)
                        text = " ".join(str(value) for value in notes.to_numpy().ravel() if pd.notna(value))
                        result["example_marker"] = EXAMPLE_MARKER in text.lower()
                    continue
                raw = pd.read_excel(workbook, sheet_name=sheet, header=None, nrows=search_rows)
                header_row = detect_header_row(raw, known[sheet], search_rows)
                if header_row is None:
                    result["missing_header"][sheet] = _missing_header(raw, known[sheet], search_rows)
                    continue
                # Relê com skiprows para manter a mesma inferência de tipos de load_workbook.
                result["sheets"][sheet] = pd.read_excel(workbook, sheet_name=sheet, skiprows=header_row - 1, nrows=limit)
                result["header_rows"][sheet] = header_row
    except UploadRejected:
        raise
    except Exception as error:  # noqa: BLE001 - planilha corrompida por dentro (TypeError, ParseError, InvalidFileException...) é 422.
        # O openpyxl embrulha a recusa do defusedxml num ValueError genérico: procura a causa na cadeia antes do NOT_XLSX.
        cause: BaseException | None = error
        while cause is not None and not isinstance(cause, DefusedXmlException):
            cause = cause.__cause__ or cause.__context__
        if cause is not None:
            raise UploadRejected("XML_UNSAFE", 422, "A planilha contém XML inseguro (expansão de entidades) e foi recusada.") from error
        raise UploadRejected("NOT_XLSX", 422, "Não foi possível ler o arquivo como planilha .xlsx ou .xlsm.") from error
    return result
