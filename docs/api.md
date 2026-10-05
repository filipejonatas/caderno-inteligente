# API

A API FastAPI expõe prioridades, previsão, recomendação, visão comercial, qualidade, validação, feedback, casos, execuções e cenários. Nenhuma rota modifica o XLSM ou a configuração oficial. Todas as rotas novas desde a V1 são aditivas: os contratos anteriores continuam válidos.

## Índice de endpoints

| Método | Rota | Finalidade | Grava dados |
|---|---|---|---|
| GET | `/api/health` | Fonte, banco, persistência e cache | — |
| GET | `/api/system` | Ambiente, modo demonstração, escrita habilitada e limites de texto | — |
| GET | `/api/overview` | Indicadores da visão geral | — |
| GET | `/api/priorities` | Ranking oficial (`family`, `confidence`, `search`) | — |
| GET | `/api/priorities/{sku}` | Detalhe: indicador, sinais, contribuições, previsão e recomendação | — |
| GET | `/api/forecasts` | Previsão e recomendação resumida de todos os SKUs | — |
| GET | `/api/capacity/{family}` | Capacidade semanal da família | — |
| GET | `/api/data-quality` | Validação da planilha e cobertura de sell-out | — |
| GET | `/api/b2b2c/visibility` | Cobertura e nível demonstrativo por parceiro (V1) | — |
| GET | `/api/partners` | Parceiros e cobertura medida (filtros e paginação) | — |
| GET | `/api/partners/{codigo}` | Resumo do parceiro | — |
| GET | `/api/partners/{codigo}/skus` | Matriz parceiro–SKU com evidências mensais | — |
| GET | `/api/commercial-recommendations` | Sugestões comerciais entre parceiros | — |
| GET | `/api/validation/summary` | Central de validação da Semana 4 | — |
| GET | `/api/runs` · `/api/runs/{id}` | Execuções registradas | — |
| GET | `/api/run-comparisons?base=&target=` | Comparação entre duas execuções | — |
| GET | `/api/config` | Pesos, limiares e listas válidas | — |
| GET | `/api/cases` · `/api/cases/{id}/history` | Casos e histórico | — |
| GET | `/api/feedback` | Decisões registradas | — |
| POST | `/api/scenarios` | Simulação de pesos/limiares, sem persistência | — |
| POST | `/api/runs` | Registra snapshot auditável | sim (403 com `WRITE_ENABLED=false`) |
| POST | `/api/cases` · PUT `/api/cases/{id}` | Cria/atualiza caso | sim (403 com `WRITE_ENABLED=false`) |
| POST | `/api/feedback` | Registra decisão humana | sim (403 com `WRITE_ENABLED=false`) |

Respostas de erro usam `{"detail": ...}`: 404 para recurso inexistente, 403 para escrita desabilitada, 413 para corpo acima de 16 KB, 422 para validação e 500 com código de referência (`X-Request-ID`).

## `GET /api/health`

Informa disponibilidade da fonte e da persistência:

- `status`: `ok` ou `degraded`;
- `source_available`: presença do XLSM no bundle;
- `database`: `ok` ou `unavailable`;
- `persistence`: `sqlite` localmente ou `postgres` com `DATABASE_URL`;
- `cache`: situação do cache do pipeline.

## `GET /api/overview`

As métricas de ruptura distinguem SKUs únicos de ocorrências de regras:

- `rupture_sku_count`: SKUs únicos que acionaram `RUP_LEAD_TIME` ou `RUP_SAFETY_STOCK`;
- `below_lead_time_count`: SKUs únicos abaixo do lead time;
- `below_safety_stock_count`: SKUs únicos abaixo do estoque de segurança;
- `rupture_signal_count`: total de ocorrências das duas regras;
- `risk_count`: alias temporário e compatível de `rupture_sku_count`.

Um SKU que aciona as duas regras contribui uma única vez para `rupture_sku_count` e duas vezes para `rupture_signal_count`.

## `GET /api/forecasts`

Retorna uma visão consolidada, somente leitura, com um item por SKU. A resposta combina identificação, posição e score do ranking oficial quando existentes, forecast de três meses e um resumo da recomendação operacional.

- usa o mesmo pipeline em memória de prioridades e detalhe;
- não recalcula nem altera score, ranking ou regras;
- inclui SKUs fora do ranking, identificados por `priority = null`;
- mantém forecast ausente como `null`, nunca como demanda zero;
- toda recomendação retorna `requires_human_review = true`;
- capacidade familiar é somente um contexto de validação, não garantia individual.

O cálculo detalhado, as premissas e as evidências permanecem em `GET /api/priorities/{sku}`.

## `GET /api/b2b2c/visibility`

Cada parceiro recebe uma classificação demonstrativa derivada da cobertura de SKUs com sell-out observado:

- `Sem visibilidade`: 0%;
- `Essencial`: acima de 0% e abaixo de 40%;
- `Conectado`: de 40% até abaixo de 80%;
- `Estratégico`: 80% ou mais.

A resposta também informa `next_level`, a quantidade adicional de SKUs necessária e uma descrição do dado requerido. Essa classificação não representa acordo comercial firmado.

## `GET /api/feedback` e `POST /api/feedback`

Além de SKU, ação, observação e usuário, o feedback aceita:

- `partner_data_effect`: `nao_utilizado`, `confirmou`, `aumentou_confianca` ou `alterou_decisao`;
- `analysis_minutes`: número inteiro não negativo e opcional.

Bancos SQLite existentes são migrados de modo aditivo. Registros anteriores recebem `partner_data_effect = "nao_utilizado"` e `analysis_minutes = null`. Em produção, o mesmo contrato é preservado pelo adaptador PostgreSQL/Supabase.

O overview expõe `decision_count` e `partner_data_influenced_decision_count`. O segundo contabiliza decisões com efeito `aumentou_confianca` ou `alterou_decisao`.

## Etapa 4 — APIs comerciais aditivas

Os endpoints existentes não mudaram. As novas leituras não alteram ranking, previsão ou recomendação operacional.

- `GET /api/partners`: todos os parceiros/canais cadastrados e cobertura medida.
- `GET /api/partners/{codigo}`: resumo, referência, método e limitação de atribuição de decisões.
- `GET /api/partners/{codigo}/skus`: pares reais daquele parceiro, métricas e evidências mensais.
- `GET /api/commercial-recommendations`: pares reais, filtráveis entre parceiros.

Filtros exatos nas listas: `partner`, `sku`, `region`, `channel`, `action`, `data_quality`. A lista de SKUs do parceiro recebe o código pelo caminho, sem parâmetro `partner`. `action` aceita `avaliar_reposicao`, `monitorar_estoque`, `investigar_divergencia`, `solicitar_atualizacao`, `dados_insuficientes`; `data_quality` aceita `sufficient`, `stale`, `insufficient`.

Listas retornam envelope com `reference_month`, `total`, `items`, `limit`, `offset`, `thresholds`, `field_nature`, `limitation`. Paginação: `limit` padrão 200, entre 1 e 500; `offset` não negativo. Resumo do parceiro representa seus vínculos completos, mesmo quando a matriz está filtrada. Meses são `YYYY-MM`; datas de pedidos são ISO.

Valores ausentes são nulos; números observados iguais a zero continuam zero. Cada item comercial contém parceiro/SKU, meses efetivamente usados, períodos mensais e pedidos da carteira. Dados globais de estoque/capacidade/forecast não são incluídos. `reference_month` é a referência da base, não a data atual.

Parceiro inexistente retorna 404. Filtro enumerado inválido, paginação inválida ou dados/configuração comercial inválidos retornam 422. Atribuição de decisões por parceiro é explicitamente indisponível: `decisions.attribution_available=false`, `decisions.items=null`, com justificativa.

Método e regras: `docs/commercial-rules.md`.

## Etapa 5 — `GET /api/validation/summary`

Leitura aditiva e somente leitura para a Central de validação (`/validacao`). Reutiliza o pipeline cacheado, a previsão e a recomendação existentes; não altera pesos, limiares, modelos, ranking nem arquivos. Configuração: `config/validation_center.json`.

Campos principais:

- `process_comparison`: uma linha por indicador da empresa, com `informed` (natureza `informado`), `recalculated` (natureza `recalculado`, com `comparable` e `reason`) e `target` (natureza `meta` ou `null`). Valores não recalculáveis são `null`, nunca zero.
- `analysis_time`: decisões registradas, registros com minutos, soma, média e mediana; `comparison_allowed=false` enquanto a amostra for menor que `minimum_sample`.
- `forecast_evaluation`: holdout de 3 meses por SKU para cada candidato, para o modelo selecionado e para a baseline `naive_last` (último mês observado). Inclui SKUs elegíveis e insuficientes, WAPE mediano e ponderado, vitórias por modelo, SKUs que não superaram a baseline (empate conta como não superou) e lista por SKU.
- `frozen_cases`: os oito casos congelados com entrada, esperado, obtido, verificações, resultado (`passou`, `falhou`, `nao_encontrado`), limitação e ajuste. `source_matches_frozen=false` indica que a planilha mudou desde o congelamento.
- `safe_behavior`: verificações executadas a cada consulta (`aprovado`/`reprovado`) e as cobertas por teste automatizado (`coberto_por_teste`).
- `known_failures`, `known_limitations`, `adjustments` e `requires_human_review=true`.

Falha da persistência não derruba a rota: o tempo de análise volta vazio, com nota explicativa, e a falha é listada em `known_failures`. Configuração de validação inválida retorna 422.

## Etapa 6 — Comparação entre execuções

Mudanças aditivas em contratos existentes:

- `POST /api/runs` continua retornando `{"id": ...}`. O snapshot passa a preservar também um payload `comparison` (versão `schema_version = 1`) com previsão e recomendação operacional por SKU, limiares comerciais e cobertura B2B2C por parceiro cadastrado.
- `GET /api/runs` acrescenta `comparison_schema_version` (`null` em execuções anteriores).
- `GET /api/runs/{id}` acrescenta `comparison` (`null` em execuções anteriores).

### `GET /api/run-comparisons?base={id}&target={id}`

Compara dois snapshots gravados, sem recalcular nada. A rota é separada de `/api/runs/{id}` para não conflitar com a validação inteira do identificador.

- `base`, `target`: metadados com id, data, hash da planilha, SKUs no ranking e versão do snapshot.
- `context`: `source_changed`, `weights_changes`, `thresholds_changes` e `commercial_thresholds` (indisponível em snapshots anteriores).
- `ranking`: `entered`, `exited`, `changed` e `summary`. Cada item alterado traz posição e score base/alvo, `position_delta` (positivo = subiu), `score_delta`, `signals_added`, `signals_removed`, `score_breakdown` (sinal adicionado, removido ou peso alterado, com o delta), `score_delta_explained`, `explanation` e `evidence_changes` (valores de evidência dos sinais mantidos).
- `forecasts`: mudanças por SKU em previsão e recomendação, com `delta` numérico quando aplicável.
- `b2b_coverage`: mudanças por parceiro cadastrado em cobertura, SKUs observados e último sell-out.
- `comparable`, `notes`, `limitations`.

Seção sem dados compatíveis retorna `{"available": false, "reason": "..."}`. Isso ocorre com snapshot anterior à Etapa 6, versão de snapshot diferente, ranking sem os campos necessários ou análise comercial indisponível no registro. Base igual ao alvo ou id menor que 1 retorna 422; execução inexistente retorna 404.

## Etapa 8 — Segurança e modo de demonstração

### `GET /api/system` (novo, aditivo)

Retorna `environment`, `demo_mode`, `write_enabled`, `text_limits` (`note`, `user_name`, `owner`, `case_action`, `analysis_minutes`) e `notice`. Não consulta o banco e não expõe segredos nem dados de conexão.

### Escrita desabilitável

Com `WRITE_ENABLED=false`, `POST /api/feedback`, `POST /api/cases`, `PUT /api/cases/{id}` e `POST /api/runs` retornam **403** com `detail` explicativo. Leituras e `POST /api/scenarios` (simulação sem persistência) continuam disponíveis.

### Validação de entrada

- Decisões e casos recusam campos desconhecidos (422) e exigem SKU existente na base atual (422).
- Limites: `sku` 32, `note` 2000, `user_name` 80, `owner` 80, `action` do caso 200, `analysis_minutes` entre 0 e 1440. `due_date` vazio ou `AAAA-MM-DD` válido. `run_id` ≥ 1.
- Texto com caracteres de controle é recusado; quebras de linha e tabulação são permitidas. Espaços nas pontas são removidos.
- `PUT /api/cases/{id}` de caso inexistente retorna 404, sem gravar histórico órfão.
- `POST /api/scenarios` aceita somente regras e limiares conhecidos. Pesos ficam entre 0 e 100, `excess_coverage_days` entre 1 e 3650 e `capacity_occupation_threshold` entre 0 e 2.
- `GET /api/priorities`: `search`, `family` e `confidence` com até 100 caracteres.
- Corpo de `POST` e `PUT` acima de 16 KB retorna 413.

### Erros, cabeçalhos e CORS

- Toda resposta traz `X-Request-ID`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` e `Referrer-Policy: no-referrer`.
- Erro não tratado retorna 500 com `detail` contendo o código de referência. Em `APP_ENV=production` a mensagem é genérica; em desenvolvimento inclui o tipo e a mensagem, já sem connection strings.
- Em produção, erros 422 de validação retornam somente `type`, `loc` e `msg`, sem ecoar o valor enviado.
- CORS aceita apenas as origens válidas de `CORS_ORIGINS`, os métodos GET, POST, PUT e OPTIONS e o cabeçalho `Content-Type`, sem credenciais.
