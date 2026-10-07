# Etapa 15.0 — Linha de base, casos-alvo e protocolo

Primeira subetapa do [plano da Etapa 15](plano-etapa-15-correcao-motor-decisao.md) (correção G1–G5). Registra o "antes" e grava, **antes de qualquer código novo**, os casos esperados, os limiares e as origens de avaliação. Nenhuma previsão, regra, ranking ou quantidade oficial mudou nesta subetapa.

## 1. Decisões aprovadas (2026-10-07)

O usuário aprovou D1 a D6 no padrão recomendado:

| # | Decisão |
|---|---|
| D1 | Previsão, regras, ranking e quantidade oficiais podem mudar na Etapa 15, com versionamento e comparação antes × depois |
| D2 | Motor oficial `v2` = `seasonal_level` para todo SKU com ≥ 15 meses (fallback `seasonal_naive_12` → `moving_average_3`), horizonte de 6 meses, sujeito ao critério de promoção da 15.1 |
| D3 | Data de planejamento = 2026-09-14 (primeira semana de `Capacidade_Semanal`) |
| D4 | `CAPACITY_SHORTFALL` substitui `CAPACITY_CONFLICT`; a ocupação média fica como contexto |
| D5 | Acúmulo no parceiro → Investigar; excesso estável no parceiro → Monitorar; rever OP → Investigar |
| D6 | Nova rota `/capacidade` em Planejamento, com entrada própria no `volume-budget.json` |

## 2. Linha de base

- **Planilha:** `data/source/Base de Dados - Caderno Inteligente.xlsm`, SHA-256 `03fa0ed400aa3f8e14de8f8232cd12727a54c85089a36672f009cae37b78803f`, igual ao `frozen_source_sha256` da central de validação e à planilha entregue com o desafio.
- **Antes das mudanças:** 398 testes Python; `npm run check` com 355 testes Vitest, 21 testes node e build OK.
- **Depois da 15.0:** 418 testes Python (20 novos em `tests/test_etapa15_protocolo.py`); frontend inalterado nas contagens (355 + 21) e build OK.

### Snapshot "antes" (`docs/etapa-15/antes.json`)

Gerado por `scripts/snapshot_decisions.py` (só leitura; os bancos da API vão para um diretório temporário, e `runtime/` não é tocado). A saída é determinística: rodar duas vezes dá o mesmo resultado (há teste).

**Ações por SKU (50 SKUs):**

| Ação | SKUs |
|---|---|
| Sem ação necessária | 30 |
| Produzir | 12 |
| Monitorar excesso | 6 |
| Produzir após validar capacidade | 2 |

**Top 10 da fila:**

| Posição | SKU | Ação | Quantidade | Rótulo do desafio |
|---|---|---|---|---|
| 1 | CI-0041 | Sem ação necessária | 0 | Sem ação necessária |
| 2 | CI-0050 | Sem ação necessária | 0 | Sem ação necessária |
| 3 | CI-0025 | Sem ação necessária | 0 | Sem ação necessária |
| 4 | CI-0033 | Sem ação necessária | 0 | Sem ação necessária |
| 5 | CI-0049 | Produzir | 300 | Priorizar produção |
| 6 | CI-0002 | Sem ação necessária | 0 | Sem ação necessária |
| 7 | CI-0015 | Sem ação necessária | 0 | Sem ação necessária |
| 8 | CI-0017 | Sem ação necessária | 0 | Sem ação necessária |
| 9 | CI-0018 | Produzir | 500 | Priorizar produção |
| 10 | CI-0048 | Sem ação necessária | 0 | Sem ação necessária |

**Previsão e faturamento:**

- Previsão oficial somada (`v1`): set/26 = 25.682, out/26 = 25.722, **nov/26 = 29.235 un.** (nov/25 realizado: 34.259).
- Faturamento estimado em 3 meses: R$ 5,04 mi; WAPE de backtest de 6,7% (holdout jun–ago, sem pico).

**Parceiros:** 95 pares parceiro–SKU. KA-02 · CI-0009 = `investigar_divergencia`; KA-03 · CI-0001 = `monitorar_estoque` sem sinal.

## 3. O que foi gravado antes do código

| Onde | O quê | Usado em |
|---|---|---|
| `config/forecast_engine.json` → `evaluation` | Origens de 2025-11 a 2026-05, horizonte 3, meses de pico `[11, 1, 2]`, \|viés no pico\| ≤ 10% | 15.1 |
| `config/supply_plan.json` (novo) | `reference_date` 2026-09-14, janela de decisão de 4 semanas, cobertura-alvo de 4 semanas, excesso projetado > 90 dias, 30,4 dias/mês | 15.2 e 15.3 |
| `config/commercial_thresholds.json` | `buildup_months` 6, sell-through ≤ 0,90, crescimento do estoque ≥ 30%, tolerância da conta de estoque de 1 un. | 15.5 |
| `config/prioritization_weights.json` | `PROJECTED_SHORTFALL` 9, `CAPACITY_SHORTFALL` 7, `OP_FOR_DISCONTINUED` 6, `PARTNER_STOCK_BUILDUP` 6, `PROJECTED_EXCESS` 5 | 15.3 a 15.5 |
| `config/validation_center.json` | Casos VC-20 a VC-30 e duas entradas no histórico de ajustes | 15.1 a 15.5 |

Todos os loaders rejeitam campos desconhecidos, então as chaves novas ganharam validação:

- **`forecast_engine_config.py`:** seção `evaluation` (mês válido, primeira origem ≤ última, meses de pico distintos entre 1 e 12, viés em (0, 1)).
- **`supply_plan.py`:** `load_supply_settings` (data ISO numa segunda-feira, inteiros ≥ 1, 28 ≤ dias/mês ≤ 31). O módulo só tem a configuração; a projeção entra na 15.3.
- **`partner_insights.py`:** janela de acúmulo inteira de 2 a 12 meses e sell-through em (0, 1].

### Casos congelados da Etapa 15

A central de validação passou a aceitar `pending_until`. O caso fica listado como **Pendente**, não é executado e não conta como aprovado nem como reprovado. Cada subetapa remove a marca dos seus casos.

| ID | Alvo | Esperado (resumo) | Pendente até |
|---|---|---|---|
| VC-20 | CI-0041 | `atraso_inevitavel`; pedidos PED-041-1 e PED-041-2 afetados; Priorizar produção | 15.3 |
| VC-21 | CI-0050 | `OP_FOR_DISCONTINUED`; `rever_op` na OP-7849; quantidade nova 0 | 15.3 |
| VC-22 | CI-0047 | o mesmo, na OP-7846 | 15.3 |
| VC-23 | CI-0048 | `PROJECTED_EXCESS`; ajuste na OP-7847 | 15.3 |
| VC-24 | CI-0009 | entra na fila; `PROJECTED_EXCESS` + `PARTNER_STOCK_BUILDUP`; `rever_op` na OP-7808 | 15.5 |
| VC-25 | KA-02 · CI-0009 | `PARTNER_STOCK_BUILDUP`, sem `SELLIN_SELLOUT_DIVERGENCE`; `conter_reposicao`; Investigar | 15.5 |
| VC-26 | KA-03 · CI-0001 | `PARTNER_STOCK_BUILDUP` ou `PARTNER_EXCESS_RISK` | 15.5 |
| VC-27 | KA-01 · CI-0029 | continua `avaliar_reposicao` (guarda de regressão) | **ativo, passa** |
| VC-28 | previsão agregada | nov/26 entre 32.546 e 41.111 un.; Escolar jan+fev/27 ≥ 15.822 un. | 15.1 |
| VC-29 | família Escolar | status de pico em {pré-produção, insuficiente, a confirmar}, com números | 15.4 |
| VC-30 | CI-0014 | cobertura ≤ 54 dias; aviso `REGISTERED_DEMAND_DIVERGENCE` | 15.2 |

**Resultado atual:** 30 casos, 20 aprovados, 10 pendentes, 0 reprovados, 0 não encontrados.

O histórico de ajustes registra:

- a inclusão desses casos;
- que o **VC-04** ("CI-0041 sem ação") será revisto na 15.3, porque 914 un. prometidas para 13 e 14/09 ficam sem cobertura até a OP-7840 (08/10).

**O que cada subetapa precisa criar para os seus casos:**

- campos novos no resultado obtido: `affected_order_ids`, `challenge_code`, `op_adjusted_orders`, `data_quality_warnings`;
- tipos novos de caso: `forecast_aggregate` (15.1) e `capacity_family` (15.4);
- formatos novos de verificação: `between`, `min` (15.1) e `in` (15.4).

O formato `includes_any` já existe (usado no VC-26).

## 4. Números preliminares já vistos

Repetidos do plano, para deixar claro o que foi observado antes do protocolo. Não foram usados para escolher limiares.

| WAPE agregado (50 SKUs) | MA3 | `seasonal_naive_12` | `seasonal_level` (teto 2,0) |
|---|---|---|---|
| origem 2025-11 | 23,9% | 11,1% | 8,6% |
| origem 2026-02 | 23,5% | 11,3% | 8,3% |
| origem 2026-05 | 7,6% | 11,7% | 7,7% |

Com o teto de 2,0, Escolar fica em 7.642 un. por mês em jan–fev/27. A razão real foi de ~2,3–2,4 nos dois anos, por isso o plano usa teto de 3,0 (igual a `event_factors.json`). A 15.1 mostra as duas versões.

## 5. Arquivos

- **Novos:**
  - `src/caderno_inteligente/supply_plan.py` (só a configuração);
  - `config/supply_plan.json`;
  - `scripts/snapshot_decisions.py`;
  - `docs/etapa-15/antes.json`;
  - `tests/test_etapa15_protocolo.py`;
  - este documento.
- **Alterados:**
  - `config/forecast_engine.json`, `config/commercial_thresholds.json`, `config/prioritization_weights.json`, `config/validation_center.json`;
  - `src/caderno_inteligente/forecast_engine_config.py`, `partner_insights.py` (só defaults e validação) e `validation_center.py` (`pendente`, `pending`, `includes_any`, campo `family`);
  - `scripts/smoke_test.py`: exige aprovação dos casos executados, descontando os pendentes;
  - `tests/test_validation_api.py`: 30 casos;
  - frontend: `types-validation.ts`, `ValidationPage.tsx` (rótulo Pendente, contagem sem pendentes, casos pendentes fechados por padrão), `CommercialMatrix.tsx` (nomes dos limiares novos), `test/contract-keys.json` (`frozen_cases.pending`), `test/fixtures.ts`.

## 6. Limitações desta subetapa

- **Os pesos novos já aparecem em `/api/config`,** e os limiares de acúmulo aparecem no bloco "Método" de Comercial, mas nenhuma regra os usa até a 15.3–15.5. O teste `test_new_rule_weights_exist_but_no_rule_emits_them_yet` garante isso.
- **Cenários ainda diz "Simular 2 dos 7 pesos"** e usa `CAPACITY_CONFLICT`. O texto e o controle mudam na 15.4, quando a regra for substituída (D4).
- **Comparação de execuções:** uma execução gravada antes e outra depois da 15.0 aparecem com "Pesos alterados" e "Limiares alterados". É o comportamento correto.

## 7. Próximo passo

15.1 — previsão `v2` com horizonte de 6 meses e avaliação em meses de pico. Ela remove a marca do VC-28.

**Commit sugerido:** `chore(etapa-15.0): linha de base, casos-alvo e protocolo da correção G1–G5`
