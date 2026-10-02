# Priorização transparente — Etapa 4

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
