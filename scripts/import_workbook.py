"""Importa a planilha XLSM para o banco (fase 3). Rodado uma vez; a planilha nunca é alterada.

Lê com a mesma ingestão da API (.xlsm ou .xlsx), bloqueia se a validação encontrar erros (impressos com endereço) e grava uma
tabela por aba, registrando a base como a versão "original" do histórico.

    python scripts/import_workbook.py                     # SQLite local (runtime/dataset.db)
    python scripts/import_workbook.py --postgres          # usa DATABASE_URL do ambiente (nunca impressa)
    python scripts/import_workbook.py --postgres --replace  # substitui uma importação anterior

Antes, no PostgreSQL, rode supabase/migrations/004_dataset_and_auth.sql. Depois, configure DATA_SOURCE=banco na API.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from caderno_inteligente.dataset_store import Database, DatasetStore, DatasetStoreError  # noqa: E402
from caderno_inteligente.ingestion import IngestionError, load_workbook, read_workbook_bytes  # noqa: E402
from caderno_inteligente.transformations import safe_normalise  # noqa: E402
from caderno_inteligente.upload_safety import UploadRejected  # noqa: E402
from caderno_inteligente.validation import validate_dataset  # noqa: E402

DEFAULT_SOURCE = ROOT / "data/source/Base de Dados - Caderno Inteligente.xlsm"
DEFAULT_SQLITE = ROOT / "runtime/dataset.db"


def build_database(postgres: bool, sqlite_path: Path) -> Database:
    if postgres:
        url = os.getenv("DATABASE_URL")
        if not url:
            raise SystemExit("DATABASE_URL não definida no ambiente.")
        return Database(database_url=url)
    return Database(sqlite_path=sqlite_path)


def _describe(issue: dict) -> str:
    """Erro de validação com o endereço dos exemplos (aba, linha, coluna), quando houver."""
    text = str(issue.get("message") or issue)
    where = [f"{issue.get('sheet')}!{item['cell']}" for item in issue.get("examples") or [] if isinstance(item, dict) and item.get("cell")]
    return f"{text} (ex.: {', '.join(where)})" if where else text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="planilha XLSM de origem")
    parser.add_argument("--postgres", action="store_true", help="grava no PostgreSQL da DATABASE_URL")
    parser.add_argument("--sqlite", type=Path, default=DEFAULT_SQLITE, help="arquivo SQLite local (sem --postgres)")
    parser.add_argument("--replace", action="store_true", help="substitui dados já importados (perde o cadastro feito pela tela)")
    args = parser.parse_args(argv)

    header_rows: dict[str, int] = {}
    try:
        if args.source.suffix.lower() == ".xlsx":
            if not args.source.is_file():
                raise IngestionError(f"Arquivo não encontrado: {args.source}")
            read = read_workbook_bytes(args.source.read_bytes())
            dataset, header_rows = read["sheets"], read["header_rows"]
        else:
            dataset = load_workbook(args.source)
    except (IngestionError, UploadRejected) as error:
        print(f"Planilha não lida: {error}", file=sys.stderr)
        return 1
    # Valida antes de gravar: texto em coluna numérica ou data inválida bloqueiam, sem traceback.
    normalised, issues = safe_normalise(dataset, header_rows=header_rows, max_examples=5)
    if normalised is not None:
        issues = validate_dataset(normalised, header_rows=header_rows, max_examples=5)["errors"]
    if issues:
        print("A planilha tem erros de validação; nada foi gravado:", file=sys.stderr)
        for issue in issues:
            print(f"  - {_describe(issue)}", file=sys.stderr)
        return 1
    store = DatasetStore(build_database(args.postgres, args.sqlite))
    try:
        if not store.is_empty() and not args.replace:
            raise DatasetStoreError("O banco já tem dados importados. Use --replace para substituir (o cadastro feito pela tela será perdido).")
        version = store.apply_version(dataset, action="original", user_email="script", filename=args.source.name,
                                      file_sha256=hashlib.sha256(args.source.read_bytes()).hexdigest(),
                                      size_bytes=args.source.stat().st_size, inactive_skus=set())["version"]
    except DatasetStoreError as error:
        print(str(error), file=sys.stderr)
        return 1
    rows = sum(len(frame) for frame in dataset.values())
    print(f"Importadas {len(dataset)} abas ({rows} linhas) para {store.db.kind}. Versão dos dados: {version}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
