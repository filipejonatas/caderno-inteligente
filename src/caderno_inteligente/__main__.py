from __future__ import annotations
import argparse
from pathlib import Path
from .ingestion import load_workbook
from .quality_report import write_quality_report
from .validation import validate_dataset


def main() -> int:
    parser = argparse.ArgumentParser(description="Valida a base XLSM do Caderno Inteligente sem modificá-la.")
    parser.add_argument("source", type=Path, help="Caminho do XLSM original")
    parser.add_argument("--report", type=Path, default=Path("runtime/reports/quality_report.json"))
    args = parser.parse_args()
    report = validate_dataset(load_workbook(args.source))
    output = write_quality_report(report, args.report)
    print(f"Relatório gerado: {output}")
    print(f"Erros: {len(report['errors'])}; avisos: {len(report['warnings'])}")
    return 1 if report["errors"] else 0

if __name__ == "__main__":
    raise SystemExit(main())
