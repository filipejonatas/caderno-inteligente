from __future__ import annotations

import json
import time
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import openpyxl
import openpyxl.xml
import pytest

from caderno_inteligente.ingestion import read_workbook_bytes
from caderno_inteligente.upload_safety import ROW_MARGIN, UploadRejected, check_upload, load_upload_settings, safe_filename

SOURCE = Path("data/source/Base de Dados - Caderno Inteligente.xlsm")
SETTINGS = load_upload_settings()


def _xlsx(rows: list[list] | None = None) -> bytes:
    workbook = openpyxl.Workbook()
    workbook.active.title = "Lead_Times"
    for row in rows or [["SKU", "Família", "Lead time dias", "Lote mínimo"], ["CI-0001", "Escolar", 10, 100]]:
        workbook.active.append(row)
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _rewrite(content: bytes, replacements: dict[str, bytes], compression: int = ZIP_DEFLATED) -> bytes:
    source = ZipFile(BytesIO(content))
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression) as target:
        for entry in source.infolist():
            target.writestr(entry.filename, replacements.pop(entry.filename, source.read(entry.filename)))
        for name, data in replacements.items():
            target.writestr(name, data)
    return buffer.getvalue()


def _rejected(content: bytes, filename: str = "base.xlsx", settings: dict | None = None) -> UploadRejected:
    with pytest.raises(UploadRejected) as error:
        check_upload(content, filename, settings or SETTINGS)
    return error.value


def test_config_has_exactly_the_contract_keys() -> None:
    raw = json.loads(Path("config/dataset_upload.json").read_text(encoding="utf-8"))
    assert raw == {"max_upload_bytes": 4194304, "max_zip_entries": 300, "max_uncompressed_bytes": 52428800, "max_compression_ratio": 100,
                   "max_rows_per_sheet": 50000, "max_columns": 64, "max_versions": 20, "max_examples_per_error": 5, "header_search_rows": 5,
                   "accepted_extensions": [".xlsx", ".xlsm"]}
    assert SETTINGS == raw


def test_settings_reject_unknown_or_missing_keys(tmp_path: Path) -> None:
    extra = tmp_path / "extra.json"
    extra.write_text(json.dumps({**SETTINGS, "outra": 1}), encoding="utf-8")
    with pytest.raises(ValueError):
        load_upload_settings(extra)
    missing = tmp_path / "missing.json"
    missing.write_text(json.dumps({key: value for key, value in SETTINGS.items() if key != "max_versions"}), encoding="utf-8")
    with pytest.raises(ValueError):
        load_upload_settings(missing)


def test_packaged_source_passes_and_reports_metadata() -> None:
    content = SOURCE.read_bytes()
    info = check_upload(content, "C:\\Users\\alguem\\Base.XLSM", SETTINGS)
    assert info["filename"] == "Base.XLSM" and info["extension"] == ".xlsm"
    assert info["size_bytes"] == len(content) and len(info["sha256"]) == 64
    assert info["entries"] == 66 and info["has_macro"] is False


def test_macro_part_is_flagged_not_rejected() -> None:
    info = check_upload(_rewrite(_xlsx(), {"xl/vbaProject.bin": b"\x00" * 64}), "macro.xlsm", SETTINGS)
    assert info["has_macro"] is True


def test_file_larger_than_limit_is_413() -> None:
    error = _rejected(b"PK\x03\x04" + b"\x00" * SETTINGS["max_upload_bytes"])
    assert (error.status, error.code, error.message) == (413, "FILE_TOO_LARGE", "Arquivo maior que o limite de 4 MB.")


def test_wrong_extension_and_renamed_csv() -> None:
    error = _rejected(_xlsx(), "base.xls")
    assert (error.status, error.code, error.message) == (422, "UNSUPPORTED_TYPE", "Envie um arquivo .xlsx ou .xlsm")
    error = _rejected("SKU;Quantidade\nCI-0001;10\n".encode("utf-8"), "vendas.xlsx")
    assert (error.status, error.code) == (422, "NOT_XLSX")


def test_zip_without_workbook_or_corrupted_is_not_xlsx() -> None:
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("leia.txt", "nada")
    assert _rejected(buffer.getvalue()).code == "NOT_XLSX"
    assert _rejected(b"PK\x03\x04" + b"lixo" * 100).code == "NOT_XLSX"


def test_too_many_entries() -> None:
    extra = {f"xl/extra/{index}.xml": b"<a/>" for index in range(SETTINGS["max_zip_entries"])}
    assert _rejected(_rewrite(_xlsx(), extra)).code == "ZIP_TOO_MANY_ENTRIES"


def test_zip_bomb_with_60_mb_of_zeros_is_rejected() -> None:
    bomb = _rewrite(_xlsx(), {"xl/media/zeros.bin": b"\x00" * (60 * 1024 * 1024)})
    assert len(bomb) < SETTINGS["max_upload_bytes"]
    error = _rejected(bomb)
    assert error.status == 422 and error.code in {"ZIP_TOO_LARGE", "ZIP_RATIO"}


def test_high_compression_ratio_alone_is_rejected() -> None:
    bomb = _rewrite(_xlsx(), {"xl/media/zeros.bin": b"\x00" * (2 * 1024 * 1024)})
    assert _rejected(bomb).code == "ZIP_RATIO"


def test_openpyxl_uses_defusedxml() -> None:
    assert openpyxl.xml.DEFUSEDXML is True


def test_billion_laughs_in_shared_strings_is_rejected_as_xml_unsafe() -> None:
    entities = "".join(f'<!ENTITY lol{index} "{("&lol%d;" % (index - 1)) * 10}">' for index in range(1, 10))
    payload = (
        '<?xml version="1.0"?><!DOCTYPE sst [<!ENTITY lol0 "lol">' + entities + ']>'
        '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="1" uniqueCount="1"><si><t>&lol9;</t></si></sst>'
    ).encode("utf-8")
    base = _xlsx([["SKU"], ["texto"]])
    # O openpyxl grava texto sem tabela compartilhada; o tipo no [Content_Types].xml faz o leitor abrir a parte maliciosa.
    content_types = ZipFile(BytesIO(base)).read("[Content_Types].xml").replace(
        b"</Types>", b'<Override PartName="/xl/sharedStrings.xml" '
        b'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/></Types>')
    content = _rewrite(base, {"xl/sharedStrings.xml": payload, "[Content_Types].xml": content_types})
    check_upload(content, "risco.xlsx", SETTINGS)  # O ZIP em si é pequeno; quem barra é a leitura do XML.
    with pytest.raises(UploadRejected) as error:
        read_workbook_bytes(content)
    assert (error.value.status, error.value.code) == (422, "XML_UNSAFE")


def test_safe_filename() -> None:
    assert safe_filename("../../etc/passwd.xlsx") == "passwd.xlsx"
    assert safe_filename("C:\\pasta\\base\x00\x1f.xlsx") == "base.xlsx"
    assert len(safe_filename("a" * 300 + ".xlsx")) == 120
    assert safe_filename("") == ""


def test_safe_filename_drops_unicode_format_and_c1_characters_and_normalises_nfc() -> None:
    # RLO (U+202E) faria o nome aparecer invertido; largura zero, BOM, C1 e separador de linha também saem.
    assert safe_filename("base\u202e\u200b\ufeff\u0085\u009b.xlsx") == "base.xlsx"
    assert safe_filename("Planilha\u00a0de\u2028maio.xlsx") == "Planilha\u00a0demaio.xlsx"
    decomposed = "Previsa\u0303o.xlsx"  # "ã" decomposto (NFD) vira o caractere único (NFC).
    assert safe_filename(decomposed) == "Previs\u00e3o.xlsx"


def _sheet_xml(rows: str) -> bytes:
    return ('<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f"<sheetData>{rows}</sheetData></worksheet>").encode("utf-8")


def test_column_bomb_xfd_is_rejected_quickly_before_pandas() -> None:
    """2.000 linhas com uma célula em XFD (~15 KB) faziam o leitor montar 16.384 colunas por linha (99 s / 800 MB)."""
    rows = "".join(f'<row r="{index}"><c r="XFD{index}"><v>1</v></c></row>' for index in range(1, 2001))
    bomb = _rewrite(_xlsx(), {"xl/worksheets/sheet1.xml": _sheet_xml(rows)})
    assert len(bomb) < 20 * 1024
    started = time.perf_counter()
    error = _rejected(bomb)
    assert time.perf_counter() - started < 2
    assert (error.status, error.code) == (422, "TOO_MANY_COLUMNS")


def test_column_limit_counts_cells_without_reference() -> None:
    cells = "<c><v>1</v></c>" * (SETTINGS["max_columns"] + 1)
    assert _rejected(_rewrite(_xlsx(), {"xl/worksheets/sheet1.xml": _sheet_xml(f"<row>{cells}</row>")})).code == "TOO_MANY_COLUMNS"
    within = "<c><v>1</v></c>" * SETTINGS["max_columns"]
    check_upload(_rewrite(_xlsx(), {"xl/worksheets/sheet1.xml": _sheet_xml(f"<row>{within}</row>")}), "ok.xlsx", SETTINGS)


def test_row_bomb_far_row_index_or_too_many_rows_is_rejected() -> None:
    far = SETTINGS["max_rows_per_sheet"] + ROW_MARGIN + 1
    error = _rejected(_rewrite(_xlsx(), {"xl/worksheets/sheet1.xml": _sheet_xml(f'<row r="{far}"><c r="A{far}"><v>1</v></c></row>')}))
    assert (error.status, error.code) == (422, "TOO_MANY_ROWS")
    small = {**SETTINGS, "max_rows_per_sheet": 10}
    rows = "".join(f"<row><c><v>{index}</v></c></row>" for index in range(10 + ROW_MARGIN + 1))
    assert _rejected(_rewrite(_xlsx(), {"xl/worksheets/sheet1.xml": _sheet_xml(rows)}), settings=small).code == "TOO_MANY_ROWS"
    # Até a margem passa: a prévia lê com nrows limitado e aponta TOO_MANY_ROWS como erro da planilha.
    rows = "".join(f"<row><c><v>{index}</v></c></row>" for index in range(10 + ROW_MARGIN))
    check_upload(_rewrite(_xlsx(), {"xl/worksheets/sheet1.xml": _sheet_xml(rows)}), "ok.xlsx", small)


def test_malformed_or_dtd_worksheet_is_rejected_by_the_scan() -> None:
    duplicated = _sheet_xml('<row r="1"><c r="A1" r="B1"><v>1</v></c></row>')
    assert _rejected(_rewrite(_xlsx(), {"xl/worksheets/sheet1.xml": duplicated})).code == "NOT_XLSX"
    dtd = b'<?xml version="1.0"?><!DOCTYPE worksheet [<!ENTITY a "x">]>' + _sheet_xml("").split(b"?>", 1)[1]
    assert _rejected(_rewrite(_xlsx(), {"xl/worksheets/sheet1.xml": dtd})).code == "XML_UNSAFE"


def test_settings_require_max_columns(tmp_path: Path) -> None:
    missing = tmp_path / "sem-colunas.json"
    missing.write_text(json.dumps({key: value for key, value in SETTINGS.items() if key != "max_columns"}), encoding="utf-8")
    with pytest.raises(ValueError):
        load_upload_settings(missing)
