# Cálculos da Etapa 2

A Etapa 2 prepara uma visão interna por SKU. Ela não classifica risco, não atribui prioridade e não altera a base XLSM.

| Indicador | Fórmula | Fontes |
|---|---|---|
| Cobertura calculada | `estoque atual / venda média por dia` | `Estoque_Atual`, `Produtos` |
| Diferença de cobertura | `cobertura informada - cobertura calculada` | `Estoque_Atual`, `Produtos` |
| Pedidos em carteira | `soma(quantidade)` por SKU | `Carteira_Pedidos` |
| Produção em ordem | `soma(quantidade)` por SKU | `Ordens_Producao` |
| Primeira conclusão | `mínimo(conclusão prevista)` por SKU | `Ordens_Producao` |
| Estoque projetado | `estoque atual + ordens - carteira` | `Estoque_Atual`, `Ordens_Producao`, `Carteira_Pedidos` |
| Lacuna operacional | `máximo(0, carteira - estoque atual - produção aberta)` | `Estoque_Atual`, `Ordens_Producao`, `Carteira_Pedidos` |
| Data crítica | menor data disponível entre primeira promessa e primeira conclusão prevista | `Carteira_Pedidos`, `Ordens_Producao` |
| Sell-in acumulado | `soma(quantidade enviada)` por SKU | `Sell_In` |
| Sell-out acumulado | `soma(quantidade vendida)` por SKU | `Sell_Out` |
| Diferença sell-in/out | `sell-in acumulado - sell-out acumulado` | `Sell_In`, `Sell_Out` |
| Visibilidade sell-out | há ao menos um parceiro com sell-out para o SKU | `Sell_Out` |
| Capacidade familiar | primeira semana disponível e médias no horizonte | `Capacidade_Semanal` |

## Tratamento de ausência de sell-out

`has_sell_out = false` e `sell_out_visibility = "não disponível"` significam ausência de observação. O valor de sell-out é retornado como `null` e `missing_data` inclui `sell_out_quantity`; a ausência não é interpretada como venda zero.

## Escopo e interpretação

- `analysis_scope` é sempre `SKU global`: o protótipo não distribui volumes por parceiro, canal ou semana.
- `critical_date_reason` identifica se a data crítica veio de `first_promised_date` ou `first_production_completion`.
- `operational_gap_quantity` é uma lacuna para análise, não uma ordem recomendada ou uma decisão automática de produção.
- Datas e valores observacionais ausentes são retornados como `null` e relacionados em `missing_data`.

## Limite de capacidade

A capacidade é agregada por família e semana. Como não há alocação explícita de pedidos ou OPs por semana/linha, os indicadores de capacidade são contexto operacional, não cálculo de viabilidade de uma ordem específica.
