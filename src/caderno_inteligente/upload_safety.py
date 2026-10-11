from __future__ import annotations
import hashlib
import json
import re
import unicodedata
import zlib
from io import BytesIO
from pathlib import Path
from typing import Any
from xml.etree.ElementTree import ParseError
from zipfile import BadZipFile, ZipFile

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "config" / "dataset_upload.json"
_INTEGER_KEYS = ("max_upload_bytes", "max_zip_entries", "max_uncompressed_bytes", "max_compression_ratio",
                 "max_rows_per_sheet", "max_columns", "max_versions", "max_examples_per_error", "header_search_rows")
_SETTINGS_KEYS = {*_INTEGER_KEYS, "accepted_extensions"}
_ZIP_SIGNATURE = b"PK\x03\x04"
# Linhas além de max_rows_per_sheet ainda passam pela varredura até esta margem (título, linhas em branco):
# a prévia as lê com nrows limitado e aponta TOO_MANY_ROWS como erro da planilha, com a contagem.
ROW_MARGIN = 100
_CELL_REF = re.compile(r"([A-Z]{1,3})?(\d+)?$")


class UploadRejected(ValueError):
    """Arquivo recusado antes de qualquer leitura de dados; `status` é 413 (tamanho) ou 422."""

    def __init__(self, code: str, status: int, message: str):
        super().__init__(message)
        self.code = code
        self.status = status
        self.message = message


def load_upload_settings(path: str | Path | None = None) -> dict[str, Any]:
    """Lê config/dataset_upload.json com chaves estritas: nenhuma a mais, nenhuma a menos."""
    source = DEFAULT_PATH if path is None else Path(path)
    values = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(values, dict) or set(values) != _SETTINGS_KEYS:
        raise ValueError("Configuração do upload precisa ter exatamente as chaves: " + ", ".join(sorted(_SETTINGS_KEYS)))
    for key in _INTEGER_KEYS:
        if isinstance(values[key], bool) or not isinstance(values[key], int) or values[key] <= 0:
            raise ValueError(f"Parâmetro do upload inválido: {key}")
    extensions = values["accepted_extensions"]
    if not isinstance(extensions, list) or not extensions or not all(isinstance(item, str) and item.startswith(".") for item in extensions):
        raise ValueError("Parâmetro do upload inválido: accepted_extensions")
    values["accepted_extensions"] = [item.lower() for item in extensions]
    return values


def safe_filename(name: str) -> str:
    """Só o nome-base em NFC, sem caracteres de categoria Unicode C* (controle, formatação como U+202E, largura zero) nem
    separadores de linha/parágrafo (Zl/Zp), com até 120 caracteres; o caminho enviado pelo cliente é descartado."""
    text = unicodedata.normalize("NFC", str(name or ""))
    text = "".join(char for char in text if unicodedata.category(char)[0] != "C" and unicodedata.category(char) not in ("Zl", "Zp"))
    base = text.replace("\\", "/").rsplit("/", 1)[-1].strip()
    return base[:120]


def _column_index(letters: str) -> int:
    index = 0
    for letter in letters:
        index = index * 26 + ord(letter) - 64
    return index


def scan_worksheets(archive: ZipFile, settings: dict[str, Any]) -> None:
    """Varre em stream (defusedxml) cada xl/worksheets/*.xml antes do pandas: célula além de `max_columns` ou linha além de
    `max_rows_per_sheet` + ROW_MARGIN recusa o arquivo sem montar a grade (bomba de colunas/linhas: uma célula em XFD faz o
    leitor preencher 16.384 colunas por linha)."""
    from defusedxml import DefusedXmlException
    from defusedxml.ElementTree import iterparse

    max_columns, max_rows = settings["max_columns"], settings["max_rows_per_sheet"] + ROW_MARGIN
    too_many_columns = UploadRejected("TOO_MANY_COLUMNS", 422, f"A planilha tem colunas além do limite de {max_columns} por aba.")
    too_many_rows = UploadRejected("TOO_MANY_ROWS", 422, f"A planilha tem linhas além do limite de {settings['max_rows_per_sheet']} por aba.")
    for entry in archive.infolist():
        if not (entry.filename.startswith("xl/worksheets/") and entry.filename.endswith(".xml")):
            continue
        row_number = 0
        column = 0
        try:
            with archive.open(entry) as stream:
                for event, element in iterparse(stream, events=("start", "end"), forbid_dtd=True):
                    tag = element.tag.rsplit("}", 1)[-1]
                    if event == "end":
                        if tag == "row":
                            element.clear()
                        continue
                    if tag == "row":
                        # Sem o atributo r, a linha é a seguinte à anterior (como o openpyxl lê).
                        reference = element.get("r")
                        row_number = int(reference) if reference and reference.isdigit() else row_number + 1
                        column = 0
                        if row_number > max_rows:
                            raise too_many_rows
                    elif tag == "c":
                        match = _CELL_REF.match(element.get("r") or "")
                        letters, digits = (match.group(1), match.group(2)) if match else (None, None)
                        column = _column_index(letters) if letters else column + 1
                        if column > max_columns:
                            raise too_many_columns
                        if digits and int(digits) > max_rows:
                            raise too_many_rows
        except UploadRejected:
            raise
        except DefusedXmlException as error:
            raise UploadRejected("XML_UNSAFE", 422, "A planilha contém XML inseguro (expansão de entidades) e foi recusada.") from error
        except (ParseError, ValueError, OSError, EOFError, BadZipFile, zlib.error) as error:
            raise UploadRejected("NOT_XLSX", 422, "Não foi possível ler o arquivo como planilha .xlsx ou .xlsm.") from error


def check_upload(content: bytes, filename: str, settings: dict[str, Any]) -> dict[str, Any]:
    """Confere tamanho, extensão e o ZIP do xlsx sem descompactar nada; levanta UploadRejected na primeira falha."""
    name = safe_filename(filename)
    if len(content) > settings["max_upload_bytes"]:
        limit = settings["max_upload_bytes"] / (1024 * 1024)
        raise UploadRejected("FILE_TOO_LARGE", 413, f"Arquivo maior que o limite de {limit:g} MB.")
    extension = Path(name).suffix.lower()
    if extension not in settings["accepted_extensions"]:
        raise UploadRejected("UNSUPPORTED_TYPE", 422, "Envie um arquivo .xlsx ou .xlsm")
    not_xlsx = UploadRejected("NOT_XLSX", 422, "O arquivo não é uma planilha .xlsx ou .xlsm válida.")
    if not content.startswith(_ZIP_SIGNATURE):
        raise not_xlsx
    try:
        with ZipFile(BytesIO(content)) as archive:
            entries = archive.infolist()
    except BadZipFile as error:
        raise not_xlsx from error
    if len(entries) > settings["max_zip_entries"]:
        raise UploadRejected("ZIP_TOO_MANY_ENTRIES", 422, f"A planilha tem mais de {settings['max_zip_entries']} partes internas.")
    uncompressed = sum(entry.file_size for entry in entries)
    if uncompressed > settings["max_uncompressed_bytes"]:
        raise UploadRejected("ZIP_TOO_LARGE", 422, "A planilha descompactada passa do limite permitido.")
    ratio = settings["max_compression_ratio"]
    if any(entry.file_size > ratio * max(entry.compress_size, 1) for entry in entries):
        raise UploadRejected("ZIP_RATIO", 422, "A planilha tem compressão suspeita (possível bomba de ZIP).")
    names = {entry.filename for entry in entries}
    if "xl/workbook.xml" not in names:
        raise not_xlsx
    with ZipFile(BytesIO(content)) as archive:
        scan_worksheets(archive, settings)
    return {"sha256": hashlib.sha256(content).hexdigest(), "size_bytes": len(content), "extension": extension,
            "filename": name, "entries": len(entries), "uncompressed_bytes": uncompressed,
            "has_macro": "xl/vbaProject.bin" in names}
