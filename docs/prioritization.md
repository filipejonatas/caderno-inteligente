# Priorização transparente

A priorização é uma **ordenação de atenção**, não uma solução ótima e não uma decisão automática de produção.

## Pontuação

A pontuação de cada SKU é a soma dos pesos das regras ativas. Os pesos ficam em [config/prioritization_weights.json](../config/prioritization_weights.json), fora do código.

| Regra | Peso |
|---|---:|
| Estoque abaixo da segurança | 10 |
| Pedido sem produção | 9 |
| Cobertura abaixo do lead time | 8 |
| Produção posterior à promessa | 8 |
| Conflito de capacidade | 5 |
| Excesso de cobertura | 3 |
| Baixa visibilidade de sell-out | 2 |

## Confiança

- **Baixa:** SKU sem sell-out observado; a lacuna é explicitada.
- **Média:** há sell-out observado, mas a cobertura da rede de parceiros permanece parcial.

Nenhum caso recebe confiança alta enquanto a cobertura de sell-out B2B permanecer parcial.

Cada linha do ranking expõe score, motivos, evidências, origem dos dados e uma ressalva de uso.

## Desempate e posição

O ranking ordena por score decrescente e, em caso de empate, pelo código do SKU. Assim, um SKU pode mudar de posição sem mudar de score, quando outros SKUs entram, saem ou mudam de pontuação.

## Prioridade não é ordem de produção

A prioridade indica **o que analisar primeiro**. A quantidade vem da recomendação operacional, calculada separadamente. Na base atual, por exemplo, o primeiro da fila (CI-0041, score 33) tem cinco sinais de risco e recomendação **sem ação necessária**: o estoque e a produção aberta já cobrem a demanda do próximo mês. O risco continua exigindo análise humana.

## Explicar uma mudança de prioridade

Em `/execucoes?base=&alvo=`, a comparação entre duas execuções decompõe a diferença de score em sinais adicionados, sinais removidos e pesos alterados (fórmula em [cálculos](calculations.md#7-comparação-entre-execuções-run_comparisonpy)).
