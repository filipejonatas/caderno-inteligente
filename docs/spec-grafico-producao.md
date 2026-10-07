# Spec — Gráfico de produção planejada na Fila operacional

Status: **aprovada e implementada em 2026-10-07** (decisões D1 a D4 abaixo; desvios na seção 7).

## 1. Objetivo

Mostrar em `/fila` quanto precisa ser liberado para produção a cada mês, somando todos os SKUs, no mesmo formato do gráfico de `/faturamento`. Hoje a fila responde "o que fazer em cada SKU", mas não mostra o volume total nem em que mês ele cai.

## 2. Requisitos

| # | Requisito |
|---|---|
| R1 | O gráfico mostra, por mês, a soma das **ordens planejadas** pelo **mês de liberação** (`release_date`) |
| R2 | Cada mês separa **urgente** (barra cheia: liberação dentro da janela de 4 semanas) de **depois** (barra tracejada) |
| R3 | A soma dos urgentes é igual à soma de `suggested_quantity` da fila ("sugerido agora") |
| R4 | Mês de liberação com horizonte incompleto não aparece como completo: é omitido e a tela diz quais meses ficaram de fora |
| R5 | O gráfico segue o filtro `familia` da fila; sem filtro, mostra o total da empresa |
| R6 | O rótulo diz que é **plano sugerido, não ordem liberada**, e que exige revisão humana |
| R7 | Se o gráfico falhar, a fila continua funcionando, com aviso e "Tentar novamente" |
| R8 | SKU sem plano (sem previsão) fica fora da soma e é listado; ausência nunca vira zero |
| R9 | Acessível: `role="img"` com descrição completa, legenda que não depende só da cor, valores disponíveis em tooltip |
| R10 | Nenhuma resposta atual da API muda; score, ranking, ações e quantidades não mudam |

### Critérios de aceite (planilha de hash `03fa0ed4…803f`)

Ordens planejadas por mês de liberação, medidas em 2026-10-07:

| Mês | Total (un.) | Urgente | Depois |
|---|---:|---:|---:|
| set/26 | 21.100 | 21.100 | 0 |
| out/26 | 26.800 | 1.800 | 25.000 |
| nov/26 | 26.600 | 0 | 26.600 |
| dez/26 | 32.500 | 0 | 32.500 |
| jan/27 | 26.000 | 0 | 26.000 |
| fev/27 | 6.300 | 0 | 6.300 |

- Total urgente = **22.900 un.** (igual ao "sugerido agora").
- fev/27 é omitido pela regra do mês completo (seção 3.2); jan/27 também pode ser, conforme o maior lead time. O teste usa a regra, não uma lista fixa de meses.
- Com `?familia=Escolar`, os valores batem com a soma dos SKUs da Escolar.
- `/fila` respeita o orçamento de volume; pytest, `npm run check` e axe passam.

## 3. Design

### 3.1 Backend — endpoint novo e aditivo

`/api/forecasts` traz só o total por SKU (`planned_quantity_horizon`); as ordens planejadas existem apenas em `/api/priorities/{sku}`. A agregação fica num endpoint próprio, no padrão de `/api/revenue-forecast`:

```
GET /api/production-plan
{
  "reference_date": "2026-09-14",
  "horizon_end": "2027-02-28",
  "urgent_window_end": "<data de planejamento + 4 semanas>",
  "total": {
    "months": [{ "month": "2026-09", "urgent": 21100, "later": 0, "complete": true }, ...],
    "urgent_total": 22900,
    "horizon_total": 139300
  },
  "families": [{ "family": "Escolar", "months": [...], "urgent_total": ..., "horizon_total": ... }],
  "excluded_skus": [{ "sku": "...", "reason": "sem_previsao" }],
  "omitted_months": ["2027-02"],
  "field_nature": { ... },
  "limitations": [ ... ],
  "requires_human_review": true
}
```

- Módulo novo `src/caderno_inteligente/production_plan.py` com a função pura `build_production_plan(plans, indicators, settings)`. Lê o resultado de `supply_plans()` (já em cache); não recalcula a projeção.
- `months` lista só os meses completos; `horizon_total` soma todas as ordens, inclusive as dos meses omitidos.
- Cache: reaproveita o cache do pipeline, como `revenue_forecast()`.

### 3.2 Regra do mês completo

Um mês de liberação M é **completo** quando `último dia de M + maior lead time entre os SKUs ≤ horizon_end`. Depois disso, ordens que atenderiam necessidades além do horizonte não foram planejadas, e o mês pareceria menor do que é. A regra é genérica e não depende de fevereiro.

### 3.3 Frontend

- Extrair de `RevenueTrend` um componente genérico `MonthlyBars` (série cheia, série tracejada, legendas). Faturamento e detalhe de canal continuam idênticos por fora.
- Componente novo `components/ProductionPlanChart.tsx`: barras empilhadas (urgente embaixo, depois em cima), uma linha-resumo ("22.900 un. para liberar agora") e uma nota dos meses omitidos. Link para `/capacidade`.
- `OperationalQueuePage`: carregamento próprio (`useApiResource(api.productionPlan)`), entre os filtros e a lista; falha isolada (R7).
- Tipos em `types-production.ts`; método `api.productionPlan`.

### 3.4 Orçamento de volume

`/fila` hoje permite 4 blocos e 8 números fora de tabelas. Eixo com meses em texto ("set"), valores no `aria-label`, no tooltip e no "?". Pela decisão D1, o gráfico entra como bloco próprio e o limite de `/fila` sobe de 4 para **5 blocos**, com o motivo registrado em `volume-budget.json`. Nenhum outro limite muda.

## 4. Decisões aprovadas

| # | Decisão |
|---|---|
| D1 | O gráfico é um bloco próprio; o limite de `/fila` sobe para 5 blocos, com motivo registrado |
| D2 | As OPs já existentes **não** entram nesta versão (usam data de conclusão, não de liberação); ficam para uma v2 |
| D3 | Mês incompleto é omitido, e a tela diz quais meses ficaram de fora |
| D4 | Implementação em branch separada (`claude/grafico-producao-fila`), fora da limpeza do repositório |

## 5. Tarefas

| # | Tarefa | Verificação |
|---|---|---|
| T1 | `production_plan.py`: agregação, regra do mês completo, SKUs excluídos | `tests/test_production_plan.py`: urgente = Σ sugerido; Σ famílias = total; mês omitido com dados sintéticos; SKU sem plano fora e nunca zero |
| T2 | `GET /api/production-plan` em `backend/main.py` | Teste de API: 200; endpoints existentes sem mudança; mesmo objeto em cache |
| T3 | Contrato: `contract-keys.json`, `fixtures.ts`, `tests/test_frontend_contracts.py` | Contrato verde nos dois lados |
| T4 | Extrair `MonthlyBars` de `RevenueTrend` | Testes de faturamento e canal sem mudança |
| T5 | `ProductionPlanChart`, `api.productionPlan` e tipos | Vitest: barras e legenda, filtro de família, erro com a fila intacta, `aria-label` |
| T6 | Integração em `/fila` e orçamento (D1) | `volume.test.tsx`, `a11y.test.tsx`, `usability.test.tsx` verdes |
| T7 | Documentação: `api.md`, `calculations.md` (regra do mês completo), README | Links relativos verificados |
| T8 | Validação final | pytest, `npm run check` completo e conferência com a API real |

Commits: backend (T1–T3), frontend (T4–T6), docs (T7).

## 6. Fora do escopo

- Cortar o plano pela capacidade (continua em `/capacidade`).
- Histórico de produção realizada (a base não tem).
- Exportação CSV.

## 7. Desvios na implementação

| Item da spec | O que foi feito e por quê |
|---|---|
| `build_production_plan(plans, indicators, settings)` | A assinatura é `(plans, indicators, forecasts)`: para saber se o SKU tem previsão (R8) é preciso o `status` da previsão; as datas e o lead time já vêm do próprio plano |
| Campo `complete` em `months[]` | Não existe: `months[]` só traz meses completos e os demais vão para `omitted_months`, então o campo seria sempre `true`. Entrou `max_lead_time_days`, que explica a regra |
| D1 (5 blocos em `/fila`) | **Não foi preciso.** O gráfico coube nos 4 blocos atuais. O limite que pesou foi o de números (8): os meses omitidos aparecem só pelo nome ("fev"), como no eixo, sem o ano |
| Link para `/capacidade` no gráfico | Não entrou: o cabeçalho da fila já tem o botão "Ver capacidade" |
| Valores por mês em tooltip | Estão no `aria-label` do gráfico e no "?" ao lado do total; `<title>` por barra contaria como texto da tela no orçamento de volume |

Resultado na planilha atual: set/26 21.100 agora; out/26 1.800 agora e 25.000 depois; nov/26 26.600; dez/26 32.500; jan/27 26.000; fevereiro omitido. Total agora 22.900 un.; no horizonte, 139.300 un.
