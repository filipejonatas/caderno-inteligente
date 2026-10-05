# API

A API FastAPI expõe prioridades, qualidade, feedback, execuções, casos, cenários e visibilidade B2B2C. Nenhuma rota modifica o XLSM ou a configuração oficial.

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
