# Etapa 15 — Decisões antes × depois

Gerado por `scripts/snapshot_decisions.py --comparar` a partir de `antes.json` (início da Etapa 15.0) e `depois.json` (fim da 15.6), na mesma planilha.

## Ações por SKU

| Ação | Antes | Depois |
|---|---|---|
| `antecipar_op` | 0 | 1 |
| `atraso_inevitavel` | 0 | 21 |
| `monitorar_excesso` | 6 | 0 |
| `produzir` | 12 | 21 |
| `produzir_validar_capacidade` | 2 | 2 |
| `rever_op` | 0 | 5 |
| `sem_acao_necessaria` | 30 | 0 |

## Top 10 da fila

| # | Antes | Ação antes | Depois | Ação depois | Sugerido agora |
|---|---|---|---|---|---|
| 1 | CI-0041 | `sem_acao_necessaria` | CI-0041 | `atraso_inevitavel` | 800 |
| 2 | CI-0050 | `sem_acao_necessaria` | CI-0047 | `atraso_inevitavel` | 0 |
| 3 | CI-0025 | `sem_acao_necessaria` | CI-0017 | `atraso_inevitavel` | 200 |
| 4 | CI-0033 | `sem_acao_necessaria` | CI-0025 | `atraso_inevitavel` | 0 |
| 5 | CI-0049 | `produzir` | CI-0037 | `atraso_inevitavel` | 0 |
| 6 | CI-0002 | `sem_acao_necessaria` | CI-0049 | `atraso_inevitavel` | 600 |
| 7 | CI-0015 | `sem_acao_necessaria` | CI-0004 | `atraso_inevitavel` | 1.600 |
| 8 | CI-0017 | `sem_acao_necessaria` | CI-0002 | `atraso_inevitavel` | 0 |
| 9 | CI-0018 | `produzir` | CI-0015 | `atraso_inevitavel` | 200 |
| 10 | CI-0048 | `sem_acao_necessaria` | CI-0018 | `atraso_inevitavel` | 1.000 |

## Previsão, cobertura e casos-alvo

| Indicador | Antes | Depois |
|---|---|---|
| Previsão somada nov/26 (un.) | 29.235 | 36.203 |
| Previsão somada jan/27 (un.) | — | 33.896 |
| Faturamento estimado 3 meses (R$) | 5.038.491 | 5.612.822 |
| SKUs na fila | 41 | 43 |
| Quantidade sugerida agora (un.) | 7.700 | 22.900 |
| CI-0041: posição · ação · cobertura (dias) | 1 · `sem_acao_necessaria` · 6 | 1 · `atraso_inevitavel` · 5 |
| CI-0050: posição · ação · cobertura (dias) | 2 · `sem_acao_necessaria` · 10 | 11 · `rever_op` · 9 |
| CI-0047: posição · ação · cobertura (dias) | 14 · `sem_acao_necessaria` · 10 | 2 · `atraso_inevitavel` · 9 |
| CI-0048: posição · ação · cobertura (dias) | 10 · `sem_acao_necessaria` · 10 | 18 · `rever_op` · 8 |
| CI-0009: posição · ação · cobertura (dias) | — · `sem_acao_necessaria` · 55 | 29 · `rever_op` · 110 |
| CI-0014: posição · ação · cobertura (dias) | 15 · `produzir_validar_capacidade` · 55 | 17 · `atraso_inevitavel` · 30 |
| CI-0004: posição · ação · cobertura (dias) | 28 · `produzir` · 30 | 7 · `atraso_inevitavel` · 15 |
| KA-02 · CI-0009: ação comercial | `investigar_divergencia` | `conter_reposicao` |
| KA-03 · CI-0001: ação comercial | `monitorar_estoque` | `monitorar_excesso_parceiro` |
| Casos congelados (aprovados / total / pendentes) | 20 / 30 / 10 | 30 / 30 / 0 |

## Capacidade (depois)

| Família | Livre no calendário | Sem programação | Situação | Pico: necessidade · situação |
|---|---|---|---|---|
| Clássico | 39.240 | 540 | `insuficiente` | 18.000 · `a_confirmar` |
| Escolar | 12.960 | 8.720 | `insuficiente` | 20.800 · `insuficiente` |
| Planner | 22.560 | 1.520 | `insuficiente` | 10.000 · `a_confirmar` |
| Acessórios | 122.000 | 0 | `a_confirmar` | 18.600 · `a_confirmar` |
| Executivo | 23.940 | 0 | `a_confirmar` | 3.000 · `a_confirmar` |
| Refis | 136.500 | 0 | `a_confirmar` | 14.500 · `a_confirmar` |
