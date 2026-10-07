# Priorização transparente

A priorização é uma **ordenação de atenção**, não uma solução ótima e não uma decisão automática de produção.

## Pontuação

A pontuação de cada SKU é a soma dos pesos das regras ativas. Os pesos ficam em [config/prioritization_weights.json](../config/prioritization_weights.json), fora do código.

| Regra | Peso |
|---|---:|
| Estoque abaixo da segurança | 10 |
| Pedido sem produção | 9 |
| Falta antes da reposição (`PROJECTED_SHORTFALL`) | 9 |
| Cobertura abaixo do lead time | 8 |
| Produção posterior à promessa | 8 |
| Não cabe na capacidade (`CAPACITY_SHORTFALL`) | 7 |
| OP de produto saindo de linha (`OP_FOR_DISCONTINUED`) | 6 |
| Estoque acumulando no parceiro (`PARTNER_STOCK_BUILDUP`) | 6 |
| Excesso depois da OP (`PROJECTED_EXCESS`) | 5 |
| Excesso de cobertura | 3 |
| Baixa visibilidade de sell-out | 2 |

Os pesos das regras do plano foram gravados na Etapa 15.0, antes do código que as emite.

## Confiança

- **Baixa:** SKU sem sell-out observado; a lacuna é explicitada.
- **Média:** há sell-out observado, mas a cobertura da rede de parceiros permanece parcial.

Nenhum caso recebe confiança alta enquanto a cobertura de sell-out B2B permanecer parcial.

Cada linha do ranking expõe score, motivos, evidências, origem dos dados e uma ressalva de uso.

## Desempate e posição

O ranking ordena por score decrescente e, em caso de empate, pelo código do SKU. Assim, um SKU pode mudar de posição sem mudar de score, quando outros SKUs entram, saem ou mudam de pontuação.

## Prioridade não é ordem de produção

A prioridade indica **o que analisar primeiro**. A ação e a quantidade vêm do plano datado, calculado separadamente. Na base atual, o primeiro da fila (CI-0041) tem 1.046 un. prometidas para 13–14/09 contra estoque de 132 e OP só em 08/10: a ação é **falta inevitável** (renegociar os pedidos PED-041-1 e PED-041-2 e garantir a OP), com ordem nova de 800 un. Até a Etapa 15.3, esse mesmo SKU aparecia como "sem ação necessária"; nenhum SKU da fila fica mais sem ação quando há falta projetada.

## Explicar uma mudança de prioridade

Em `/execucoes?base=&alvo=`, a comparação entre duas execuções decompõe a diferença de score em sinais adicionados, sinais removidos e pesos alterados (fórmula em [cálculos](calculations.md#7-comparação-entre-execuções-run_comparisonpy)).
