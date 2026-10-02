from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class SheetSchema:
    required_columns: tuple[str, ...]
    key_columns: tuple[str, ...] = ()
    date_columns: tuple[str, ...] = ()
    non_negative_columns: tuple[str, ...] = ()


SCHEMAS: dict[str, SheetSchema] = {
    "Produtos": SheetSchema(("SKU", "Produto", "Família", "Lead time (dias)", "Estoque atual", "Cobertura (dias)", "Venda média/dia"), ("SKU",), non_negative_columns=("Lead time (dias)", "Estoque atual", "Cobertura (dias)", "Venda média/dia")),
    "Vendas_24m": SheetSchema(("Mês", "SKU", "Cliente/Canal", "Quantidade faturada"), ("Mês", "SKU", "Cliente/Canal"), ("Mês",), ("Quantidade faturada",)),
    "Estoque_Atual": SheetSchema(("SKU", "Estoque atual", "Cobertura dias", "Estoque segurança dias"), ("SKU",), non_negative_columns=("Estoque atual", "Cobertura dias", "Estoque segurança dias")),
    "Carteira_Pedidos": SheetSchema(("Pedido", "SKU", "Cliente/Canal", "Quantidade", "Data prometida", "Status"), ("Pedido",), ("Data prometida",), ("Quantidade",)),
    "Ordens_Producao": SheetSchema(("Ordem", "SKU", "Quantidade", "Início previsto", "Conclusão prevista", "Status"), ("Ordem",), ("Início previsto", "Conclusão prevista"), ("Quantidade",)),
    "Capacidade_Semanal": SheetSchema(("Semana inicial", "Linha", "Família", "Capacidade máxima", "Capacidade disponível", "Ocupação"), ("Semana inicial", "Linha"), ("Semana inicial",), ("Capacidade máxima", "Capacidade disponível", "Ocupação")),
    "Sell_In": SheetSchema(("Mês", "Cliente", "SKU", "Quantidade enviada"), ("Mês", "Cliente", "SKU"), ("Mês",), ("Quantidade enviada",)),
    "Sell_Out": SheetSchema(("Mês", "Cliente", "SKU", "Quantidade vendida", "Estoque estimado cliente", "Natureza do dado"), ("Mês", "Cliente", "SKU"), ("Mês",), ("Quantidade vendida", "Estoque estimado cliente")),
    "Forecast_Comercial": SheetSchema(("SKU", "Mês", "Previsão unidades", "Origem previsão"), ("SKU", "Mês"), ("Mês",), ("Previsão unidades",)),
    "Calendario_Eventos": SheetSchema(("Evento", "Início", "Fim", "Famílias impactadas", "Impacto esperado"), ("Evento",), ("Início", "Fim")),
    "Parceiros_Canais": SheetSchema(("Código", "Nome fictício", "Tipo", "Cobertura de sell-out"), ("Código",), ("Última compra/venda",)),
    "Lead_Times": SheetSchema(("SKU", "Família", "Lead time dias", "Lote mínimo"), ("SKU",), non_negative_columns=("Lead time dias", "Lote mínimo")),
}

FOREIGN_KEYS = (
    ("Estoque_Atual", "SKU", "Produtos", "SKU"), ("Carteira_Pedidos", "SKU", "Produtos", "SKU"),
    ("Ordens_Producao", "SKU", "Produtos", "SKU"), ("Lead_Times", "SKU", "Produtos", "SKU"),
    ("Sell_In", "SKU", "Produtos", "SKU"), ("Sell_Out", "SKU", "Produtos", "SKU"),
    ("Forecast_Comercial", "SKU", "Produtos", "SKU"), ("Vendas_24m", "SKU", "Produtos", "SKU"),
    ("Sell_In", "Cliente", "Parceiros_Canais", "Código"), ("Sell_Out", "Cliente", "Parceiros_Canais", "Código"),
)
