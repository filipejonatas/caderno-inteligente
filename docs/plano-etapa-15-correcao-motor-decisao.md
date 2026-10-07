# Plano da Etapa 15 — Correção do motor de decisão (G1–G5)

Plano para execução por um agente de IA (Claude Code) neste repositório. Origem: análise crítica de aderência de 2026-10-07 (PDF do Desafio 3 × base XLSM × solução). Prazo do desafio: **17/10/2026**.

O plano corrige cinco falhas que fazem a solução responder errado às perguntas centrais do PDF ("o que produzir, quanto, onde o estoque está parado, onde não dá para executar"), embora a evidência exibida esteja certa.

| Gap | Sintoma medido na base atual | Subetapa |
|---|---|---|
| **G1** Ação e quantidade contraditórias | 8 dos 10 primeiros da fila saem "Sem ação necessária"; o nº 1 (CI-0041) tem 1.046 un. prometidas para 13–14/09, estoque de 132 e OP só em 08/10 | 15.3 |
| **G2** Estoque parado no parceiro não detectado | KA-02 · CI-0009: estoque 235 → 931 em 12 meses, sell-through de 59%, rotulado "investigar divergência"; o CI-0009 nem entra na fila | 15.5 |
| **G3** Previsão sem pico e horizonte curto | A MA3 é escolhida em 34/50 SKUs; nov/26 previsto = 29,2 mil contra 34,3 mil realizados em nov/25; horizonte termina em nov/26 | 15.1 |
| **G4** Capacidade é só um selo | Linha Escolar a 90–96%, 12.960 un. livres até 28/12; Volta às Aulas pede ~10 mil un. extras em jan–fev | 15.4 |
| **G5** Cobertura com demanda errada | `Produtos.Venda média/dia` subestima o `Vendas_24m` (mediana ×1,10; CI-0014 ×1,85: 55 dias declarados contra ~30 reais) | 15.2 |

---

## 1. Decisões que o usuário aprova antes da 15.0

O agente **não começa** sem a resposta a estas decisões. O padrão recomendado vem primeiro.

| # | Decisão | Padrão recomendado | Alternativa |
|---|---|---|---|
| D1 | Revogar, para G1–G5, o princípio "não alterar previsão, ranking, regras nem quantidade oficial" | **Sim**, com versionamento (motor de previsão `v2`, regras `v2`) e comparação antes × depois registrada | Manter tudo aditivo (não corrige G1, G3 nem G5) |
| D2 | Motor de previsão oficial | **`v2` = `seasonal_level` para todo SKU com ≥ 15 meses**, com fallback `seasonal_naive_12` → `moving_average_3`; horizonte de 6 meses; sujeito ao protocolo da 15.1 | Seleção por SKU entre candidatos (mais sobreajuste com 24 meses) |
| D3 | Data de planejamento ("hoje") | **2026-09-14**, a primeira semana de `Capacidade_Semanal` | 2026-09-01 |
| D4 | Regra de capacidade | **Substituir `CAPACITY_CONFLICT`** (ocupação média > 90%) **por `CAPACITY_SHORTFALL`** (falta de capacidade após a alocação); a ocupação continua como contexto | Manter as duas |
| D5 | Rótulo do PDF para os riscos novos | Acúmulo no parceiro → **Investigar**; excesso estável no parceiro → **Monitorar**; OP acima da necessidade ou de produto descontinuado → **Investigar** ("rever OP") | Outro mapeamento |
| D6 | Tela de capacidade | **Nova rota `/capacidade`** em Planejamento, com entrada própria no `volume-budget.json` | Só um bloco no detalhe do SKU |

---

## 2. Regras de execução para o agente

1. **Uma subetapa por vez**, na ordem 15.0 → 15.6. Ao fim de cada uma, pare e informe: testes Python, `npm run check`, arquivos modificados, limitações, desvios do plano e o **nome do commit**. Quem commita é o usuário; não faça commit nem push.
2. **Testes Python:** `.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp <scratchpad>\pytest`. No sandbox, o `tmp_path` padrão dá `PermissionError`.
3. **Frontend:** `cd frontend; npm run check` (typecheck, Vitest, node --test, build e varredura do bundle).
4. **Protocolo contra viés:** limiares, origens de avaliação e casos esperados são gravados na 15.0, **antes** de rodar o código novo. Se um critério de aceite falhar, **não ajuste limiar nem caso para passar**. Registre a falha, a hipótese e pare para o usuário decidir. Mudança de expectativa em teste existente só vale com o motivo no documento da subetapa.
5. **Princípios que continuam valendo:**
   - todo campo novo tem `nature` (observado/calculado/estimado/previsto) e `origin`;
   - ausente ≠ zero;
   - dado global (estoque do CD, OP, capacidade) **nunca** é distribuído entre parceiros; agregar sinal do parceiro para o SKU é permitido, o caminho inverso não;
   - `requires_human_review` em toda sugestão;
   - campo lido pelo frontend entra em `frontend/src/test/contract-keys.json`;
   - não afrouxar o `volume-budget.json` sem decisão explícita (só a D6).
6. **Navegador:** as portas 8000 e 5173 podem estar ocupadas por outra sessão; não pare esses servidores. Para testar sem gravar nos `runtime/*.db` do usuário, suba a API apontando para cópias no scratchpad (`backend.main.RUNS_DB` etc.).
7. **Configuração, não constante:** todo limiar novo fica em `config/*.json`, com validação no loader.

### Números preliminares já vistos (transparência)

A análise que originou este plano já calculou os números abaixo. Eles **não** servem para escolher limiar; são só a expectativa a confirmar.

| Medida (soma dos 50 SKUs) | MA3 | `seasonal_naive_12` | `seasonal_level` (razão limitada a 2,0) |
|---|---|---|---|
| WAPE, origem 2025-11 (dez–fev) | 23,9% | 11,1% | **8,6%** |
| WAPE, origem 2026-02 (mar–mai) | 23,5% | 11,3% | **8,3%** |
| WAPE, origem 2026-05 (jun–ago) | 7,6% | 11,7% | 7,7% |
| Viés em nov/25, origem 2025-08 | −28% | — | indisponível (< 15 meses) |

- **Previsão `seasonal_level` a partir de ago/26:** nov/26 = 36,2 mil; Escolar jan/27 = 7.642 e fev/27 = 7.642. O valor de Escolar está **travado pelo teto de 2,0**: a razão real de jan–fev é ~2,3–2,4 nos dois anos.
- **Sinais de parceiro em 12 meses:**
  - KA-02 · CI-0009: sell-through 0,59, estoque 235 → 931;
  - KA-03 · CI-0001: sell-through 0,79, estoque 259 → 343, cobertura ~297 dias;
  - a identidade estoque(t) = estoque(t−1) + SI − SO fecha com resíduo zero em 550 meses.

---

## 3. Ordem e dependências

```text
15.0 linha de base, casos-alvo e protocolo
  └─ 15.1 G3 previsão v2 (6 meses, avaliação com pico)
       └─ 15.2 G5 demanda de referência e cobertura
            └─ 15.3 G1 projeção semanal + motor de ação
                 └─ 15.4 G4 capacidade finita semanal
15.5 G2 estoque acumulando no parceiro (independente; liga-se à 15.3 no fim)
15.6 telas, validação, documentação e roteiro de demonstração
```

| Subetapa | Esforço | Corte de contingência se o prazo apertar |
|---|---|---|
| 15.0 | 0,5 dia | — |
| 15.1 | 1–1,5 dia | Manter a seleção única `seasonal_level`; adiar a recalibração das faixas |
| 15.2 | 0,5 dia | — |
| 15.3 | 2 dias | — (é o núcleo) |
| 15.4 | 1 dia | Resumo por família sem alocação por SKU |
| 15.5 | 0,5–1 dia | Sem gráfico; só sinal, rótulo e ligação com o SKU |
| 15.6 | 1,5 dia | Sem `/capacidade`: bloco no detalhe do SKU |

**Mínimo para a apresentação:** 15.0 a 15.3 e 15.5.

---

## 4. Subetapa 15.0 — Linha de base, casos-alvo e protocolo

**Objetivo:** congelar o "antes" e as expectativas, antes de qualquer código novo.

**Tarefas**

1. Rodar as duas suítes e registrar as contagens.
2. Criar `scripts/snapshot_decisions.py` (só leitura, via `fastapi.testclient`). Ele grava `docs/etapa-15/antes.json` com:
   - `/api/forecasts`, `/api/priorities` e `/api/overview`;
   - os itens de `build_partner_insights`;
   - `/api/revenue-forecast` (total por mês).

   O mesmo script, com `--saida depois.json`, será usado na 15.6.
3. Gravar na configuração, com os valores abaixo e antes de implementar:
   - `config/forecast_engine.json`, bloco `evaluation`: origens mensais de **2025-11 a 2026-05**, horizonte 3, meses de pico `[11, 1, 2]`, critérios de promoção da seção 5;
   - `config/supply_plan.json` (novo): `reference_date: "2026-09-14"`, `decision_window_weeks: 4`, `target_cover_weeks: 4`, `excess_coverage_days: 90`, `days_per_month: 30.4`;
   - `config/commercial_thresholds.json`: `buildup_months: 6`, `buildup_max_sell_through: 0.90`, `buildup_min_stock_growth: 0.30`, `stock_identity_tolerance: 1`;
   - `config/prioritization_weights.json`: os pesos novos da 15.3, 15.4 e 15.5, todos de uma vez:
     - `PROJECTED_SHORTFALL` 9, `OP_FOR_DISCONTINUED` 6, `PROJECTED_EXCESS` 5;
     - `CAPACITY_SHORTFALL` 7, `PARTNER_STOCK_BUILDUP` 6.

     Até as subetapas correspondentes, nenhuma regra emite esses códigos.
4. Escrever os casos congelados novos em `config/validation_center.json` (seção 10) e registrar no histórico de ajustes que o **VC-04** ("CI-0041 sem ação") será revisto na 15.3, com o motivo.
5. Criar `docs/etapa-15-0-linha-de-base.md`: hash da planilha (`03fa0ed4…`, igual ao de `frozen_source_sha256`), contagens de testes, decisões D1–D6 aprovadas e a tabela de números preliminares.

**Aceite:** suítes verdes; `antes.json` gerado; os casos novos existem e **falham** (esperado) ou ficam marcados como pendentes até a subetapa responsável.

**Commit:** `chore(etapa-15.0): linha de base, casos-alvo e protocolo da correção G1–G5`

---

## 5. Subetapa 15.1 — G3: previsão `v2` com horizonte de 6 meses e avaliação em pico

**Objetivo:** prever o pico de novembro e a Volta às Aulas e mostrar a acurácia medida **em meses de pico**, não só em meses planos.

**Desenho**

- **`forecast_engine_config.py`:** aceitar `engine: "v2"`. Ler `official.model_chain` (padrão `["seasonal_level", "seasonal_naive_12", "moving_average_3"]`), `official.horizon_months` (6) e `seasonal_level.ratio_bounds` (padrão `[0.5, 3.0]`, alinhado ao teto de `event_factors.json`). A troca do teto 2,0 → 3,0 tem justificativa prévia: a razão de Escolar foi ~2,3–2,4 nos dois anos. Mesmo assim, a avaliação mostra as duas versões.
- **`forecast_candidates.py`:** `SEASONAL_RATIO_BOUNDS` passa a vir da configuração (o padrão do módulo continua 2,0, para o laboratório reproduzir a 14.x).
- **`forecasting.py`:**
  - `build_demand_forecasts(sales, engine_config=None)`. Com `v1`, o caminho atual fica **byte a byte idêntico** (o snapshot da 14.0 continua passando).
  - Com `v2`:
    - modelo = primeiro da cadeia aplicável ao histórico, sem seleção por SKU;
    - `forecast_months` e `forecast_values` com 6 meses;
    - `forecast_total_3m` continua sendo a soma dos 3 primeiros, e entra `forecast_total_6m`;
    - `backtest_wape` e `forecast_confidence` passam a vir do WAPE agregado do SKU nas origens de `evaluation` (com pico), não do holdout jun–ago;
    - `trend` não muda.
- **Consumidores dos 6 meses:** procure todo uso de `forecast_values` e `forecast_months` (`revenue.py`, `events.py`, `validation_center.py`, frontend). As telas e os totais rotulados "3 meses" usam explicitamente os 3 primeiros. Faturamento ganha `total_6m` aditivo.
- **`rolling_backtest.py`:** nova `peak_evaluation(sales, engines, origins, horizon, peak_months)`. Ela devolve, para `v1`, `v2` e a baseline `naive_last`: WAPE e viés agregados, **WAPE e viés só nos meses de pico** e só nos meses normais, e o número de SKUs que batem a baseline. Exposta em `/api/forecast-lab` como `peak_evaluation`.
- **Critério de promoção** (já gravado na 15.0). O `v2` só vira oficial se **todos** valerem:
  1. WAPE agregado ≤ 95% do `v1`;
  2. |viés nos meses de pico| ≤ 10%;
  3. o viés agregado não piora mais de 2 p.p.;
  4. o `v2` bate a baseline em ≥ tantos SKUs quanto o `v1`.

  Se falhar: `engine` fica `v1`, o agente para e reporta.
- **`events.py`:** o cenário com fator só existe para modelo **fora** de `SEASONAL_CODES` (hoje o teste é só `seasonal_naive_12`). Isso evita contar o pico duas vezes. Os alertas continuam; lançamento sem histórico continua só alerta.
- **Faixas P10–P90:** recalibrar com resíduos das origens de `evaluation`. Se a cobertura ficar mais de 10 p.p. abaixo da nominal, `intervals.status = "nao_calibrada"` e a interface **esconde** a faixa com uma nota.
- **`validation_center.evaluate_forecasts`:** usar as mesmas origens com pico; a manchete da Validação passa a ser "WAPE em meses normais × meses de pico".

**Testes**

- `v1` idêntico ao `docs/etapa-14-0/snapshot-previsao-v1.json`.
- Novo snapshot `docs/etapa-15/snapshot-previsao-v2.json` para o oficial.
- Cadeia de fallback com séries de 12, 6 e 2 meses.
- Teto da razão vindo da configuração.
- `peak_evaluation` numa série sintética com pico anual, em que a MA3 erra e o modelo sazonal acerta.
- `events`: sem cenário para `seasonal_level`.

**Aceite:** VC-28; manchete da Validação com o WAPE de pico; faturamento de nov/26 maior que o atual e coerente com a previsão.

**Commit:** `feat(etapa-15.1): previsão sazonal v2 com horizonte de 6 meses e avaliação em meses de pico`

---

## 6. Subetapa 15.2 — G5: demanda de referência e cobertura

**Objetivo:** todas as regras de ruptura e excesso usam a demanda real ou prevista, não o campo cadastrado.

**Desenho**

- **`indicators.build_sku_indicators(data, forecasts=None, settings=None)`:**
  - `reference_daily_demand` = média da previsão oficial M+1..M+3 ÷ `days_per_month`;
  - fallbacks: média real dos últimos 3 meses de `Vendas_24m` e depois `Venda média/dia`, com `demand_source` informando qual foi usada;
  - `coverage_days_calculated` mantém o nome (contrato) e passa a ser `estoque ÷ reference_daily_demand`;
  - campos novos `coverage_days_registered` (estoque ÷ `Venda média/dia`), `registered_vs_reference_ratio` e `demand_source`;
  - `coverage_days_source` continua como veio da planilha.
- **`recommendations`:** o estoque de segurança em unidades usa `reference_daily_demand`.
- **`rules.py`:** atualizar `values_used` e `data_origin` das regras de cobertura (`RUP_LEAD_TIME`, `RUP_SAFETY_STOCK`, `EXCESS_COVERAGE`).
- **`validation.py` / `/api/data-quality`:** aviso `REGISTERED_DEMAND_DIVERGENCE` quando |razão − 1| > 0,20 (limiar em `rule_thresholds.json`), listando os SKUs.
- **`backend/main.py::_build_pipeline`:** a previsão é calculada **antes** dos indicadores.

**Testes:** escolha da fonte e fallbacks; o CI-0014 com cobertura < 55 dias; o aviso lista o CI-0014 (×1,85) e o CI-0004 (×1,66).

**Aceite:** VC-30; o aviso aparece em Dados da planilha; a fila muda e a mudança aparece no `antes × depois`.

**Commit:** `fix(etapa-15.2): cobertura pela demanda prevista e alerta de divergência do cadastro`

---

## 7. Subetapa 15.3 — G1: projeção semanal de estoque e motor de ação

**Objetivo:** a ação e a quantidade de cada SKU saem de uma projeção datada (estoque + OP no prazo − demanda − carteira), de modo que **nenhum SKU com falta projetada fique "Sem ação necessária"**.

**Novo módulo `src/caderno_inteligente/supply_plan.py`**

1. **`planning_calendar(reference_date, horizon_end)`:** semanas começando na segunda, alinhadas a `Capacidade_Semanal`, de 2026-09-14 até o fim do horizonte de previsão (fev/27).
2. **`weekly_demand(forecast, backlog, calendar)`:**
   - em cada mês, demanda = max(previsão do mês, carteira com data no mês), a mesma regra anti-dupla-contagem de hoje;
   - a carteira entra na semana da data prometida; a vencida antes de `reference_date` entra na semana 0 como `overdue`;
   - o restante (`max(0, previsão − carteira do mês)`) é rateado pelos dias do mês dentro de cada semana, só a partir de `reference_date` (setembro conta 17 de 30 dias).
3. **`project_stock(...)`:** por semana: demanda, carteira, chegada de OP (pela `Conclusão prevista`), estoque projetado no fim, estoque de segurança em unidades (`reference_daily_demand × dias de segurança`), `below_ss` e `shortfall`.
4. **`plan_orders(...)`:**
   - quantidade por período (cobre `target_cover_weeks` a partir da semana de necessidade), arredondada ao lote mínimo;
   - liberação = data de necessidade − lead time;
   - se a liberação cair antes de `reference_date`, a parte não coberta vira `late` (não se resolve com ordem nova);
   - **SKU `Descontinuando` não recebe ordem nova**: só cobre a carteira confirmada com o que já existe.
5. **`op_adjustments(...)`:** para cada OP aberta:
   - **reduzir/cancelar** se o SKU é `Descontinuando` (manter só o necessário para a carteira);
   - **reduzir** se, depois da chegada, a cobertura projetada passa de `excess_coverage_days` (redução arredondada para baixo ao lote, nunca abaixo da necessidade do horizonte);
   - **antecipar** se há falta antes da chegada e a data de necessidade ≥ `reference_date + lead time`.
6. **`decide(...)`:** ação principal pela precedência abaixo, mais `secondary_actions`.

| Código | Rótulo na tela | Quando | Rótulo do PDF |
|---|---|---|---|
| `investigar_dados` | Investigar dados | Sem previsão | Investigar |
| `atraso_inevitavel` | Renegociar prazo e garantir OP | Falta em semana < `reference_date + lead time`: nem ordem nova nem antecipação chegam a tempo; lista os pedidos afetados | Priorizar produção |
| `antecipar_op` | Antecipar OP | Falta antes da chegada de uma OP que ainda pode chegar a tempo | Priorizar produção |
| `produzir` | Produzir | Ordem planejada no horizonte; com liberação dentro de `decision_window_weeks` **e** (top-N da fila ou evento próximo), o rótulo vira Priorizar produção, como hoje | Produzir / Priorizar produção |
| `rever_op` | Rever OP | OP de SKU descontinuado ou OP que gera excesso projetado | Investigar (D5) |
| `monitorar_excesso` | Monitorar excesso | Cobertura projetada > limite sem OP a rever | Monitorar |
| `sem_acao_necessaria` | Sem ação necessária | **Só se** estoque projetado ≥ estoque de segurança em todas as semanas e sem excesso | Sem ação necessária |

Precedência: `investigar_dados` > `atraso_inevitavel` > `antecipar_op` > `produzir` urgente > `rever_op` > `produzir` > `monitorar_excesso` > `sem_acao_necessaria`.

**Saída da recomendação operacional.** Mesmos campos de hoje e mais estes (todos aditivos e no contrato):

- `suggested_quantity`: soma das ordens planejadas com liberação dentro de `decision_window_weeks` ("o que decidir agora");
- `planned_quantity_horizon`;
- `planned_orders[]` (semana de liberação, semana de necessidade, quantidade, motivo);
- `op_adjustments[]` (OP, ajuste, quantidade sugerida, motivo);
- `affected_orders[]` (pedido, cliente/canal, quantidade, data prometida, dias de atraso);
- `first_shortfall_week`;
- `projection[]` (semanas);
- `calculation` como cascata: demanda do horizonte → − estoque → − OP no prazo → + estoque de segurança → arredondamento ao lote.

**Demais arquivos**

- **`recommendations.py`:** `build_operational_recommendation` vira um invólucro que chama `supply_plan`.
- **`rules.py`:** `evaluate_rules(indicators, thresholds, plan=None)` emite as regras novas a partir do plano:
  - `PROJECTED_SHORTFALL`: falta antes de `reference_date + lead time`;
  - `OP_FOR_DISCONTINUED`;
  - `PROJECTED_EXCESS`.

  As regras atuais ficam; `PRODUCTION_AFTER_PROMISE` continua como evidência.
- **`action_labels.label_operational`:** mapear os códigos novos (tabela acima).
- **`backend/main.py::_build_pipeline`:** previsão → indicadores → plano → regras → ranking. O cenário de evento (`event_analysis`) recalcula a quantidade com o motor novo, ou omite `quantity` quando o modelo já é sazonal.
- **`validation_center`:**
  - VC-04 revisto: o CI-0041 deixa de ser "sem ação" (histórico de ajustes com o motivo: a projeção datada mostra 914 un. de pedidos sem cobertura até a chegada da OP-7840);
  - `safe_behavior_checks` ganha as invariantes I1–I3.
- **Persistência:** `action` é texto livre no Supabase e no SQLite (sem migração). Confirme que `run_comparison` aceita códigos novos.

**Testes**

- Um caso sintético por ação.
- `weekly_demand` sem dupla contagem; carteira vencida na semana 0.
- Arredondamento ao lote.
- Descontinuado sem ordem nova.
- Invariantes na base real; VC-20 a VC-24.

**Aceite:** I1–I3 verdes; VC-20 a VC-24 verdes; no `antes × depois`, nenhum dos 10 primeiros sai "Sem ação necessária" sem projeção que justifique.

**Commit:** `feat(etapa-15.3): projeção semanal de estoque e ações coerentes com a fila`

---

## 8. Subetapa 15.4 — G4: capacidade finita semanal

**Objetivo:** responder "onde a oportunidade não pode ser executada" com números por família e semana, e com os pedidos e clientes afetados.

**Novo módulo `src/caderno_inteligente/capacity_plan.py`**

- **Entrada:** `planned_orders` e `op_adjustments` (antecipações) de todos os SKUs, e `Capacidade_Semanal` (coluna `Capacidade disponível`, que **já desconta** compromissos base e OPs existentes, conforme o LEIA_ME).
- **Premissas declaradas na tela e no doc:**
  - capacidade em unidades homogêneas dentro da família;
  - a ordem consome capacidade na **semana de início**, como na definição de "Ordens planejadas";
  - "compromissos base" é demanda não detalhada (hipótese H5, não validada);
  - **não há capacidade informada depois da semana de 28/12/2026**.
- **Alocação:**
  1. ordenar por data de necessidade, depois curva ABC, depois posição na fila;
  2. consumir na semana de liberação; se faltar, antecipar semana a semana até `reference_date` (pré-produção, com registro das semanas usadas);
  3. o que sobrar vira `unscheduled_quantity`, com status `insuficiente`;
  4. liberação depois do calendário vira `a_confirmar` (nunca "ok" nem "insuficiente").
- **Antecipação de OP:** viável se houver capacidade na semana-alvo.
- **Saídas:**
  - por SKU: `capacity_status` ∈ {`ok`, `pre_producao`, `insuficiente`, `a_confirmar`} e `executable_quantity`;
  - por família e semana: disponível, alocado e restante;
  - por família: falta total, primeira semana de falta, demanda de pico e **pedidos e clientes afetados** (da carteira dos SKUs com falta).
- **Regra (D4):** `CAPACITY_SHORTFALL` substitui `CAPACITY_CONFLICT`; a ocupação média fica como campo de contexto.
- **API:**
  - `GET /api/capacity-plan`, nova (famílias, semanas, faltas, premissas, `field_nature`);
  - `/api/capacity/{family}` ganha `allocated` e `remaining` de forma aditiva.

**Testes:** alocação que cabe, que exige pré-produção, que falta e que cai fora do calendário; invariante I4 (alocado ≤ disponível em toda família e semana); VC-29.

**Aceite:** a Linha Escolar mostra a necessidade de jan–fev/27 contra a capacidade livre até 28/12, com o resultado explícito (pré-produção, falta ou a confirmar) e os SKUs e clientes envolvidos.

**Commit:** `feat(etapa-15.4): plano de capacidade semanal finita e viabilidade por família`

---

## 9. Subetapa 15.5 — G2: estoque acumulando no parceiro

**Objetivo:** detectar o caso que abre o PDF ("venda para o parceiro que parece bom resultado, mas o produto está parado") e ligá-lo à OP do SKU.

**Desenho em `partner_insights.py`**

- **Janela de `buildup_months` (6):**
  - `sell_in_6m`, `sell_out_6m`, `sell_through_6m`;
  - `stock_start`, `stock_end`, `stock_growth`;
  - `stock_identity_consistent`: resíduo de estoque(t) − (estoque(t−1) + SI − SO) ≤ tolerância em todos os meses.
- **`PARTNER_STOCK_BUILDUP`:** dados suficientes e não antigos **e** `sell_through_6m ≤ 0,90` **e** `stock_growth ≥ 0,30` **e** `stock_end ≥ minimum_excess_stock` **e** cobertura ≥ `excess_coverage_days`.
- **`PARTNER_EXCESS_RISK`:** remover a trava `low_monthly_sell_out` (giro ≤ 30 un./mês); passa a ser cobertura ≥ 90 dias e estoque ≥ 100, sem crescimento.
- **`SELLIN_SELLOUT_DIVERGENCE`:** só quando a identidade **não** fecha. Se fecha, a diferença SI − SO é estoque acumulado, não erro de dado.
- **Ações comerciais:**
  - `conter_reposicao`: "Não repor; acionar sell-out com o parceiro" → Investigar (D5);
  - `monitorar_excesso_parceiro` → Monitorar;
  - precedência: dado antigo > insuficiente > divergência (identidade não fecha) > acúmulo > reposição > excesso > monitorar.
- **Ligação com o SKU:**
  - as percepções de parceiro passam a ser calculadas uma vez no `pipeline()`;
  - os indicadores ganham `partner_buildup_pairs` (parceiro, sell-through, estoque inicial → final);
  - regra SKU `PARTNER_STOCK_BUILDUP`;
  - em `supply_plan`, se o SKU tem acúmulo e OP aberta, o `op_adjustment` cita a evidência do parceiro;
  - **nunca** distribuir o estoque do CD para parceiros.
- **Rótulo de parceiro:** "Priorizar parceiro" continua igual.

**Testes:** sintéticos de acúmulo, excesso estável, divergência com identidade quebrada e reposição. Na base: VC-25, VC-26 e VC-27; KA-01 · CI-0029 continua "Repor".

**Aceite:** o CI-0009 entra na fila com `PROJECTED_EXCESS` e `PARTNER_STOCK_BUILDUP` e ação `rever_op` sobre a OP-7808; a matriz do KA-02 mostra "Estoque acumulando".

**Commit:** `feat(etapa-15.5): estoque acumulando no parceiro e ligação com a OP do SKU`

---

## 10. Casos congelados novos (gravados na 15.0)

Registrar em `config/validation_center.json`, com `origin: "base"` e `limitation`, mais um caso sintético por ação na suíte de testes.

| ID | SKU / par | Esperado | Subetapa |
|---|---|---|---|
| VC-20 | CI-0041 | ação ≠ `sem_acao_necessaria`; principal `atraso_inevitavel`; `affected_orders` contém PED-041-1 (KA-05, 512, 13/09) e PED-041-2 (KA-02, 534, 14/09); rótulo Priorizar produção | 15.3 |
| VC-21 | CI-0050 | `OP_FOR_DISCONTINUED`; ação `rever_op`; ajuste de redução/cancelamento na OP-7849 (1.600); `suggested_quantity = 0` | 15.3 |
| VC-22 | CI-0047 | o mesmo, na OP-7846 (400) | 15.3 |
| VC-23 | CI-0048 | `PROJECTED_EXCESS`; ajuste "reduzir" na OP-7847 (2.000) | 15.3 |
| VC-24 | CI-0009 | entra na fila (`ranked: true`); `PROJECTED_EXCESS`; ação `rever_op` na OP-7808 | 15.3 / 15.5 |
| VC-25 | KA-02 · CI-0009 | `PARTNER_STOCK_BUILDUP`; **sem** `SELLIN_SELLOUT_DIVERGENCE`; rótulo Investigar com o motivo de acúmulo | 15.5 |
| VC-26 | KA-03 · CI-0001 | `PARTNER_STOCK_BUILDUP` ou `PARTNER_EXCESS_RISK` | 15.5 |
| VC-27 | KA-01 · CI-0029 | continua `avaliar_reposicao` / Repor (guarda de regressão) | 15.5 |
| VC-28 | total nov/26 e Escolar | previsão oficial de nov/26 entre 0,95× e 1,20× de 34.259; Escolar jan+fev/27 ≥ 0,9 × (8.622 + 8.958) com o teto da configuração | 15.1 |
| VC-29 | família Escolar | o plano de capacidade informa pré-produção, falta ou "a confirmar" para jan–fev/27, nunca "ok" sem números | 15.4 |
| VC-30 | CI-0014 | cobertura nova < 55 dias; aviso `REGISTERED_DEMAND_DIVERGENCE` | 15.2 |

**Invariantes** (em `safe_behavior_checks` e nos testes):

- **I1** — nenhum SKU com estoque projetado < 0 no horizonte sai `sem_acao_necessaria`.
- **I2** — consequência de I1: todo SKU do top 10 com `sem_acao_necessaria` tem projeção ≥ estoque de segurança em todas as semanas.
- **I3** — toda ordem planejada é múltiplo do lote mínimo.
- **I4** — alocado ≤ disponível em toda família e semana.
- **I5** — nenhum sinal de parceiro nasce de dado ausente.

> **Atenção ao VC-28:** o teto de 3,0 está justificado a priori. Se o VC-28 falhar com o teto, **não** mude o caso. Reporte.

---

## 11. Subetapa 15.6 — Telas, validação, documentação e roteiro

**Frontend** (orçamento de volume mantido, exceto a D6)

- **Fila (`OperationalQueue.tsx`):**
  - ação com os rótulos novos;
  - "Quantidade" = `suggested_quantity`, com `planned_quantity_horizon` no tooltip;
  - motivo principal vindo da projeção ("1.046 un. prometidas até 14/09, OP só em 08/10").
- **Detalhe do SKU:**
  - bloco "Plano" com a cascata da quantidade;
  - ordens planejadas, ajustes de OP, pedidos afetados e status de capacidade;
  - tabela semanal com até 8 linhas visíveis e "ver todas".
- **`/capacidade` (D6):** uma tabela família × semana (restante e alocado), destaque nas faltas e nos itens "a confirmar", e premissas no "?".
- **Matriz do parceiro:** coluna de risco "Estoque acumulando", com sell-through de 6 meses e estoque inicial → final.
- **Validação:** manchete "WAPE em meses normais × meses de pico"; faixa escondida se não calibrada.
- **Guia:** glossário dos códigos novos (`atraso_inevitavel`, `antecipar_op`, `rever_op`, `conter_reposicao`).
- **Contrato e testes:** `types*.ts`, `contract-keys.json`, `fixtures.ts`; `volume-budget.json` só com a entrada da rota nova.

**Validação e comparação**

- Rodar `scripts/snapshot_decisions.py --saida docs/etapa-15/depois.json`.
- Gerar `docs/etapa-15/antes-depois.md` com:
  - ações do top 10 antes × depois;
  - posição do CI-0009;
  - previsão de nov/26 e de Escolar jan–fev;
  - cobertura de CI-0014 e CI-0004;
  - resultado da Linha Escolar;
  - pares de parceiro com acúmulo.
- Verificar no navegador com a API apontando para cópias dos bancos no scratchpad: fila, detalhe do CI-0041, CI-0009 e CI-0050, `/capacidade` e matriz do KA-02. Sem erro no console.

**Documentação**

- `docs/etapa-15-1…15-5-*.md` (um por subetapa, no padrão das anteriores).
- `calculations.md`, `rules.md`, `commercial-rules.md`, `decisions.md` (D1–D6) e `README.md` (tabela "O que o protótipo responde").
- `roteiro-demonstracao.md` reescrito em torno de quatro casos:
  1. **CI-0041:** promessa sem cobertura → renegociar e priorizar;
  2. **KA-02 · CI-0009:** estoque parado no parceiro → não repor e rever a OP-7808;
  3. **CI-0050:** OP de produto descontinuado;
  4. **Linha Escolar:** Volta às Aulas contra a capacidade.

**Commit:** `feat(etapa-15.6): telas, validação e roteiro com o motor de decisão corrigido`

---

## 12. Fora do escopo desta etapa

- Tendência ano contra ano (G7), alocação de produto escasso entre parceiros e regiões (G8) e reconciliação `Sell_In` × `Vendas_24m` (G9). Ficam para depois; a 15.4 só **lista** os pedidos afetados.
- ML, LLM ou novos candidatos de previsão.
- Redesign visual; novas telas além de `/capacidade`.
- Migração no Supabase (não é necessária: `action` é texto livre). Se o agente achar uma restrição, para e reporta.
- Deploy, smoke test e teste com usuários: continuam pendentes e são do usuário.

## 13. Riscos

| Risco | Mitigação |
|---|---|
| Horizonte de 6 meses quebra telas e totais rotulados "3 meses" | Campos de 3 meses mantêm a semântica; os de 6 meses são aditivos; buscar todos os consumidores na 15.1 |
| A data de planejamento muda o que conta como atraso | Fica em configuração (D3); a escolha e o efeito aparecem no doc da 15.3 |
| A granularidade semanal vem de uma previsão mensal | Rateio por dias declarado como estimativa; carteira entra na data real |
| Muitos testes antigos mudam de expectativa | Cada expectativa alterada é listada com o motivo no doc da subetapa; o VC-04 vai para o histórico de ajustes |
| O `v2` não passa no critério de promoção | O agente para e reporta; o usuário decide (não ajustar limiar) |
| "Compromissos base" já podem incluir a demanda regular de Escolar (H5) | Premissa exposta na tela; o resultado é apresentado como "sob a premissa X" |
| Prazo (17/10) | Cortes de contingência da seção 3; o mínimo para apresentar é 15.0–15.3 + 15.5 |
