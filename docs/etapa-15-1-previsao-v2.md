# Etapa 15.1 — Previsão v2: horizonte de 6 meses e avaliação em meses de pico

Segunda subetapa do [plano da Etapa 15](plano-etapa-15-correcao-motor-decisao.md). Corrige o **G3**: a previsão oficial não chegava ao pico de novembro nem à Volta às Aulas, e a acurácia exibida (6–9%) era medida só em meses planos.

## 1. O que mudou

| | Antes (v1) | Depois (v2) |
|---|---|---|
| Modelo | Média móvel de 3 meses ou sazonal ingênuo, escolhido por SKU no holdout jun–ago/26 | **Mês do ano anterior ajustado pelo nível** (`seasonal_level`) para todo SKU com ≥ 15 meses; recua para sazonal ingênuo e média móvel. Sem seleção por SKU |
| Modelos usados na base | MA3 em 34 SKUs, sazonal ingênuo em 16 | `seasonal_level` nos 50 |
| Horizonte | 3 meses (set–nov/26) | **6 meses (set/26–fev/27)**; `forecast_next_month` e `forecast_total_3m` mantêm o significado |
| Limite da razão sazonal | 0,5–2,0 (só no laboratório) | 0,5–3,0, em `config/forecast_engine.json` → `seasonal_level.ratio_bounds` |
| Erro e confiança | Holdout único dos últimos 3 meses | 7 origens rolantes (2025-11 a 2026-05), cada uma prevendo os 3 meses seguintes só com os dados de até então |

**Arquivos:**

- **Código:**
  - `official_forecast.py` (novo): despacha pelo `engine`; cadeia, origens, janelas e erros separados em pico e normal.
  - `forecasting.py`: intocado (o v1 continua reproduzível, com teste contra o snapshot da 14.0).
  - `forecast_candidates.py`: `seasonal_level(..., ratio_bounds)` público.
  - `forecast_engine_config.py`: `engine` `v2`, seções `official` e `seasonal_level`.
- **Avaliação:**
  - `rolling_backtest.py`: `peak_evaluation` e `peak_promotion_criteria`.
  - `forecast_lab.py`: bloco `peak_evaluation`, status de promoção e faixa marcada `nao_calibrada`.
  - `validation_center.py`: avaliação rolante com pico, caso do tipo `forecast_aggregate`, verificações `between` e `min`.
- **Consumidores:**
  - `revenue.py`: telas e campos de 3 meses continuam com 3 meses; `revenue_total_6m` novo; referência comercial em out–dez; erro do teste em R$ vindo do mesmo teste rolante.
  - `events.py`: sem cenário para modelo sazonal.
  - `backend/main.py`: pipeline usa o motor configurado, e a assinatura do cache inclui `forecast_engine.json`.
  - `backend/validation.py`: caso pendente não é "falha conhecida". O problema vinha da 15.0 e apareceu na verificação no navegador.

## 2. Protocolo e decisão de promoção

As origens (2025-11 a 2026-05), os meses de pico `[11, 1, 2]` e os critérios foram gravados na 15.0, antes do código. Resultado na base, 50 SKUs:

| Motor | WAPE total | WAPE no pico | Viés no pico | WAPE nos meses normais | SKUs melhores que a baseline |
|---|---|---|---|---|---|
| **v2 (oficial, teto 3,0)** | **8,0%** | **7,9%** | **+0,7%** | 8,0% | **45** |
| v1 | 10,1% | 13,2% | −5,3% | 8,9% | 40 |
| v2 com teto 2,0 | 8,4% | 9,2% | −1,7% | 8,0% | 45 |
| Baseline (repete o último mês) | 18,9% | 26,8% | −0,9% | 15,9% | — |

| Critério (fixado na 15.0) | Resultado | Atende |
|---|---|---|
| WAPE ≤ 95% do v1 | redução de 20,7% | sim |
| \|viés no pico\| ≤ 10% | +0,7% | sim |
| Viés agregado não piora > 2 p.p. | melhora 3,9 p.p. | sim |
| SKUs melhores que a baseline ≥ v1 | 45 × 40 | sim |

Os quatro critérios foram atendidos, e `engine` passou para `v2`. O teto de 3,0 estava justificado antes do teste (razão de ~2,3–2,4 em Escolar nos dois anos); a tabela mostra também o teto 2,0, que só perde no pico.

**Ressalva importante:** com 15 meses mínimos de histórico, **nenhuma origem testável alcança novembro como mês-alvo**. Os meses de pico efetivamente testados são janeiro e fevereiro. Novembro é conferido pelo VC-28 (faixa de 0,95× a 1,20× de nov/25). O limite está dito na tela de Validação e nas limitações da avaliação.

## 3. Efeito na base

**Previsão oficial somada (un.):**

| Mês | v1 | v2 | Referência |
|---|---|---|---|
| set/26 | 25.682 | 26.765 | set/25: 25.392 |
| out/26 | 25.722 | 26.425 | out/25: 24.991 |
| **nov/26** | **29.235** | **36.203** | nov/25: 34.259 |
| dez/26 | — | 28.386 | dez/25: 26.718 |
| jan/27 | — | 33.896 | jan/26: 31.613 |
| fev/27 | — | 32.874 | fev/26: 30.601 |

**Outros efeitos:**

- **Escolar jan+fev/27:** 19.920 un. (jan+fev/26: 17.580). O VC-28 passa (≥ 15.822).
- **Faturamento estimado:** em 3 meses, de R$ 5,04 mi para R$ 5,61 mi (+14,6% sobre os 3 meses anteriores, pelo pico de novembro); em 6 meses, R$ 11,94 mi. Contra o forecast comercial em out–dez, o modelo fica 5,4% acima (antes: −4,3% em out–nov).
- **Eventos:** o horizonte vai até 28/02/2027, então Natal e Volta às Aulas entram como alerta. Não há mais cenário com fator, porque os 50 SKUs têm previsão sazonal e o fator contaria o pico duas vezes.
- **Faixa P10–P90:** cobriu 48% contra 80% nominais e foi **escondida** no laboratório, com a nota. A recalibração com os resíduos do v2 ficou para depois (corte de contingência previsto no plano).
- **Fila e quantidades:** o ranking não mudou (as regras não usam a previsão). A quantidade ainda usa só o próximo mês, e só 2 SKUs mudaram:
  - CI-0026: de "sem ação" para "produzir 300";
  - CI-0042: produzir de 400 para 600.

  A projeção que usa o horizonte inteiro é a 15.3.
- **Casos congelados:** 30 casos; 21 aprovados, 9 pendentes, 0 reprovados. VC-28 liberado e aprovado. O histórico de ajustes registra a troca do modelo, com `changed_weights_or_models: true`.

## 4. Telas

- **Validação:** a manchete passou a dizer "erro médio de 8,0% contra 18,9% da previsão simples; nos meses de pico, 7,9% contra 26,8%". O cartão mostra "normais 8,0% · pico 7,9%", e o processo atual exibe "WAPE ponderado (origens rolantes com pico)".
- **Laboratório:** nova tabela "Avaliação com meses de pico" (4 motores) com o selo dos critérios. "Motor atual" virou "Motor v1" ou "Motor oficial", conforme o contexto, e a faixa não calibrada não aparece.
- **Detalhe do SKU:** "erro médio de 5,2% em 7 testes com meses de pico" (antes: "no teste dos últimos 3 meses").
- **Glossário (Ajuda e "?"):** WAPE, teste e confiança descritos como testes em meses já vendidos, incluindo pico.

Verificado no navegador, com uma API própria na porta 8010 e bancos copiados no scratchpad: Validação, aba Modelos, detalhe do CI-0014 e Faturamento, sem erros no console. As portas 8000 e 5173 tinham servidores de outra sessão (o da 8000 com código anterior) e não foram tocadas.

## 5. Testes

- **Python:** 433 aprovados (418 na 15.0). Novos em `tests/test_forecast_v2.py` (13):
  - cadeia de fallback;
  - histórico curto sem zero inventado;
  - 6 meses com campos de 3 meses intactos;
  - teto vindo da configuração;
  - despacho v1 idêntico;
  - origens sem futuro;
  - erro de pico × normal;
  - avaliação sintética com pico;
  - leitura dos agregados do VC-28;
  - snapshot `docs/etapa-15/snapshot-previsao-v2.json`;
  - critérios e novembro na base real.

  Mais 1 em `test_etapa15_protocolo.py`: caso pendente não é falha conhecida.
- **Frontend:** 357 Vitest (2 novos: tabela de pico e faixa escondida), 21 node e build OK.

**Expectativas alteradas** (todas consequência direta da promoção):

| Teste | Antes | Agora | Motivo |
|---|---|---|---|
| `test_forecast_engine_config` | `engine == "v1"` | `v2`, com `official` e `seasonal_level` | promoção |
| `test_forecast_lab_api` | "pendente" | "promovido" e critérios atendidos | promoção |
| `test_forecasts_api`, `test_explainability_api` | 3 meses | 6 meses; `forecast_total_3m` = soma dos 3 primeiros | horizonte |
| `test_revenue` | unidades = previsão inteira | unidades = 3 primeiros meses; `revenue_total_6m` | horizonte |
| `test_events` | exigia SKU com cenário na API | API sem cenário (tudo sazonal); o cenário da média móvel é testado com o v1 na base real | dupla contagem |
| `test_validation_api` | nenhum ajuste muda modelo | mudança só com evidência `docs/etapa-15-*` | promoção registrada |
| `test_forecast_candidates` | "oficial = snapshot 14.0" | "motor v1 = snapshot 14.0" | o v1 continua reproduzível |
| `test_etapa15_protocolo` | 10 pendentes | 9 (VC-28 liberado) | protocolo |
| `forecast-lab.test.tsx` | rótulo "Motor atual" | "Motor v1" | o v1 deixou de ser o atual |

## 6. Limitações

- **Novembro não é testado** pela avaliação rolante (só pelo VC-28). A acurácia de pico medida é a de jan–fev.
- **Sem seleção por SKU:** em 5 SKUs o v2 não superou a baseline (aparecem em Falhas conhecidas).
- **Lançamentos e campanhas novas** (ex.: Coleção Primavera) continuam só como alerta: a previsão repete a sazonalidade observada.
- **Faixa de previsão** escondida até ser recalibrada.
- **A recomendação de quantidade ainda usa só o próximo mês;** os meses 2–6 entram na projeção semanal da 15.3.

## 7. Próximo passo

15.2 — demanda de referência e cobertura (G5), usando a previsão v2 de M+1 a M+3. Ela libera o VC-30.

**Commit sugerido:** `feat(etapa-15.1): previsão sazonal v2 com horizonte de 6 meses e avaliação em meses de pico`
