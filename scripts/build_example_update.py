"""Gera o pacote de exemplo da atualização pela tela (docs/exemplos/atualizacao-2026-10.xlsx).

DADOS FICTÍCIOS e determinísticos, derivados da base de 14/09/2026 por regras fixas (sem sorteio), com setembro nas abas
mensais e fotografias de 12/10/2026. As regras estão em docs/exemplos/README.md. A planilha de origem nunca é alterada.

    python scripts/build_example_update.py            # grava docs/exemplos/atualizacao-2026-10.xlsx
    python scripts/build_example_update.py --check    # confere o arquivo gravado contra as regras (sai com 1 se divergir)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from caderno_inteligente.ingestion import IngestionError, load_workbook  # noqa: E402
from caderno_inteligente.supply_plan import CLOSED_ORDER_STATUSES  # noqa: E402
from caderno_inteligente.workbook_writer import EXAMPLE_MARKER, README_SHEET, SHEET_ORDER, write_workbook  # noqa: E402

DEFAULT_SOURCE = ROOT / "data/source/Base de Dados - Caderno Inteligente.xlsm"
DEFAULT_OUTPUT = ROOT / "docs/exemplos/atualizacao-2026-10.xlsx"
NEW_REFERENCE = date(2026, 10, 12)  # segunda-feira
SHIFT = timedelta(days=28)
MONTH = "2026-09"
PREVIOUS_MONTH = "2026-08"
YEAR_AGO_MONTH = "2025-09"
RECENT_MONTHS = ("2026-06", "2026-07", "2026-08")
YEAR_AGO_RECENT = ("2025-06", "2025-07", "2025-08")
FACTOR_RANGE = (0.5, 2.0)
EXTRA_WEEKS = 4
TITLE = "Caderno Inteligente — atualização de exemplo (outubro/2026)"
NOTES = [
    f"{EXAMPLE_MARKER} — arquivo de exemplo fictício gerado por scripts/build_example_update.py a partir da base de 14/09/2026; não é dado real.",
    "Vendas_24m, Sell_In e Sell_Out: só setembro/2026, projetado do mesmo mês de 2025 pela tendência dos últimos 3 meses de cada SKU.",
    "Estoque_Atual: estoque de 14/09 mais o que as OPs concluídas até 12/10 produziram, menos o consumo de setembro.",
    "Carteira_Pedidos e Ordens_Producao: itens antigos reemitidos 28 dias à frente (PV-EX-… e OP-EX-…); OPs vencidas ficam Concluídas.",
    "Capacidade_Semanal: semanas a partir de 12/10/2026; as 4 semanas finais repetem a última semana observada, sem ordens planejadas.",
    "Forecast_Comercial: Out/26 sai, Nov/26 e Dez/26 ficam e Jan/27 é a média de Nov/26 e Dez/26. Cadastros não são enviados.",
]
_DATE_FORMAT = "%d/%m/%Y"


def _round(value: float) -> int:
    return int(math.floor(value + 0.5))  # arredonda meio para cima, sem o desvio do round() do Python


def _parse(text: str) -> date:
    return pd.to_datetime(text, format=_DATE_FORMAT).date()


def _fmt(day: date) -> str:
    return day.strftime(_DATE_FORMAT)


def _is_open(status) -> bool:
    return str(status).strip().casefold() not in CLOSED_ORDER_STATUSES


def _sales(dataset):
    by_pair: dict[tuple[str, str, str], int] = {}
    by_sku: dict[tuple[str, str], int] = {}
    for record in dataset["Vendas_24m"].to_dict("records"):
        quantity = int(record["Quantidade faturada"])
        by_pair[(record["SKU"], record["Cliente/Canal"], record["Mês"])] = quantity
        key = (record["SKU"], record["Mês"])
        by_sku[key] = by_sku.get(key, 0) + quantity
    return by_pair, by_sku


def _vendas(dataset, by_pair, by_sku):
    frame = dataset["Vendas_24m"]
    rows, sku_total = [], {}
    for record in frame[frame["Mês"] == PREVIOUS_MONTH].to_dict("records"):
        sku, client = record["SKU"], record["Cliente/Canal"]
        recent = sum(by_sku.get((sku, m), 0) for m in RECENT_MONTHS)
        base = sum(by_sku.get((sku, m), 0) for m in YEAR_AGO_RECENT)
        factor = min(max(recent / base, FACTOR_RANGE[0]), FACTOR_RANGE[1]) if base else 1.0
        quantity = _round(by_pair[(sku, client, YEAR_AGO_MONTH)] * factor)
        price = float(record["Preço unitário (R$)"])
        sku_total[sku] = sku_total.get(sku, 0) + quantity
        rows.append({**record, "Mês": MONTH, "Quantidade faturada": quantity, "Valor faturado (R$)": round(quantity * price, 2)})
    return pd.DataFrame(rows, columns=frame.columns), sku_total


def _sell(dataset, sku_total, by_sku):
    sell_in, sell_out = dataset["Sell_In"], dataset["Sell_Out"]

    def ratio(sku):
        previous = by_sku.get((sku, PREVIOUS_MONTH), 0)
        return sku_total.get(sku, 0) / previous if previous else 1.0

    in_rows, sent = [], {}
    for record in sell_in[sell_in["Mês"] == PREVIOUS_MONTH].to_dict("records"):
        quantity = _round(int(record["Quantidade enviada"]) * ratio(record["SKU"]))
        sent[(record["Cliente"], record["SKU"])] = quantity
        in_rows.append({**record, "Mês": MONTH, "Quantidade enviada": quantity})
    out_rows = []
    for record in sell_out[sell_out["Mês"] == PREVIOUS_MONTH].to_dict("records"):
        quantity = _round(int(record["Quantidade vendida"]) * ratio(record["SKU"]))
        stock = max(0, int(record["Estoque estimado cliente"]) + sent[(record["Cliente"], record["SKU"])] - quantity)
        out_rows.append({**record, "Mês": MONTH, "Quantidade vendida": quantity, "Estoque estimado cliente": stock})
    return pd.DataFrame(in_rows, columns=sell_in.columns), pd.DataFrame(out_rows, columns=sell_out.columns)


def _orders(dataset):
    frame = dataset["Ordens_Producao"]
    kept, reissued, produced = [], [], {}
    for record in frame.to_dict("records"):
        end, start = _parse(record["Conclusão prevista"]), _parse(record["Início previsto"])
        if _is_open(record["Status"]) and end < NEW_REFERENCE:
            produced[record["SKU"]] = produced.get(record["SKU"], 0) + int(record["Quantidade"])
            reissued.append({**record, "Início previsto": _fmt(max(start + SHIFT, NEW_REFERENCE)),
                             "Conclusão prevista": _fmt(end + SHIFT), "Status": "Planejada"})
            record = {**record, "Status": "Concluída"}
        elif str(record["Status"]).strip().casefold() in ("planejada", "liberada") and start < NEW_REFERENCE:
            record = {**record, "Status": "Em produção"}
        kept.append(record)
    for number, record in enumerate(reissued, start=1):
        record["Ordem"] = f"OP-EX-{number:04d}"
    return pd.DataFrame(kept + reissued, columns=frame.columns), produced


def _portfolio(dataset):
    frame = dataset["Carteira_Pedidos"]
    kept, reissued = [], []
    for record in frame.to_dict("records"):
        promised = _parse(record["Data prometida"])
        if promised >= NEW_REFERENCE:
            kept.append(record)
        else:  # vencido na base antiga: reemitido 28 dias à frente (nunca antes da nova referência)
            reissued.append({**record, "Data prometida": _fmt(max(promised + SHIFT, NEW_REFERENCE))})
    for number, record in enumerate(reissued, start=1):
        record["Pedido"] = f"PV-EX-{number:04d}"
    return pd.DataFrame(kept + reissued, columns=frame.columns)


def _stock(dataset, sku_total, produced):
    frame = dataset["Estoque_Atual"]
    rows = []
    for record in frame.to_dict("records"):
        sku = record["SKU"]
        consumption = _round(sku_total.get(sku, 0) / 30 * 28)
        stock = max(0, int(record["Estoque atual"]) + produced.get(sku, 0) - consumption)
        updated = {**record, "Estoque atual": stock}
        if consumption > 0:
            updated["Cobertura dias"] = _round(stock / (consumption / 28))
        rows.append(updated)
    return pd.DataFrame(rows, columns=frame.columns)


def _capacity(dataset):
    frame = dataset["Capacidade_Semanal"]
    weeks = pd.to_datetime(frame["Semana inicial"])
    rows = frame[weeks >= pd.Timestamp(NEW_REFERENCE)].to_dict("records")
    last_week = weeks.max()
    for step in range(1, EXTRA_WEEKS + 1):
        for record in frame[weeks == last_week].to_dict("records"):
            maximum, base = int(record["Capacidade máxima"]), int(record["Compromissos base"])
            rows.append({**record, "Semana inicial": last_week + pd.DateOffset(days=7 * step), "Ordens planejadas": 0,
                         "Capacidade comprometida": base, "Capacidade disponível": maximum - base,
                         "Ocupação": round(base / maximum, 2)})
    return pd.DataFrame(rows, columns=frame.columns)


def _forecast(dataset):
    frame = dataset["Forecast_Comercial"]
    rows = []
    for sku in dict.fromkeys(frame["SKU"]):
        part = {r["Mês"]: r for r in frame[frame["SKU"] == sku].to_dict("records")}
        nov, dec = part["Nov/26"], part["Dez/26"]
        january = _round((int(nov["Previsão unidades"]) + int(dec["Previsão unidades"])) / 2)
        rows += [nov, dec, {**dec, "Mês": "Jan/27", "Previsão unidades": january}]
    return pd.DataFrame(rows, columns=frame.columns)


def build_example(dataset: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Regras fixas e sem sorteio: a mesma base de entrada sempre devolve o mesmo pacote."""
    by_pair, by_sku = _sales(dataset)
    vendas, sku_total = _vendas(dataset, by_pair, by_sku)
    sell_in, sell_out = _sell(dataset, sku_total, by_sku)
    orders, produced = _orders(dataset)
    return {"Vendas_24m": vendas, "Sell_In": sell_in, "Sell_Out": sell_out,
            "Estoque_Atual": _stock(dataset, sku_total, produced), "Carteira_Pedidos": _portfolio(dataset),
            "Ordens_Producao": orders, "Capacidade_Semanal": _capacity(dataset), "Forecast_Comercial": _forecast(dataset)}


def _canonical(value):
    if value is None or value is pd.NaT or (isinstance(value, float) and math.isnan(value)):
        return None
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return round(float(value), 6)
    return str(value)


def package_sha256(sheets: dict[str, pd.DataFrame]) -> str:
    """Hash do conteúdo (não dos bytes do ZIP): abas em ordem fixa, valores normalizados."""
    payload = {name: {"columns": [str(c) for c in frame.columns],
                      "rows": [[_canonical(v) for v in row] for row in frame.itertuples(index=False, name=None)]}
               for name, frame in sorted(sheets.items())}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def read_package(path: Path) -> dict[str, pd.DataFrame]:
    with pd.ExcelFile(path, engine="openpyxl") as workbook:
        return {name: pd.read_excel(workbook, sheet_name=name, skiprows=2) for name in workbook.sheet_names if name != README_SHEET}


def generate(source: Path) -> tuple[dict[str, pd.DataFrame], bytes]:
    example = build_example(load_workbook(source))
    return example, write_workbook(example, title=TITLE, notes=NOTES, sheets=SHEET_ORDER)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--saida", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true", help="não grava; confere o arquivo existente")
    args = parser.parse_args(argv)
    try:
        example, content = generate(args.source)
    except IngestionError as error:
        print(f"Planilha não lida: {error}", file=sys.stderr)
        return 1
    if args.check:
        if not args.saida.is_file():
            print(f"Arquivo ausente: {args.saida}", file=sys.stderr)
            return 1
        if package_sha256(read_package(args.saida)) != package_sha256(example):
            print("O pacote gravado difere das regras; rode scripts/build_example_update.py.", file=sys.stderr)
            return 1
        print(f"Pacote de exemplo conferido: {args.saida.name}")
        return 0
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    args.saida.write_bytes(content)
    print(f"Gravado {args.saida} ({len(content) / 1024:.0f} KB, {len(example)} abas, dados fictícios).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
