# Plano da Etapa 14 — Modelos candidatos e backtest rolante

Complementa o [Plano de aderência ao Desafio 3](plano-aderencia-desafio.md) (Etapas 10 a 13, completas) e herda os princípios da [V2](plano-v2-prototipo-top.md). Esta etapa é **plano, não implementação**: nada aqui foi codificado.

## 1. Objetivo

Testar, com método, se modelos estatísticos clássicos adicionais e uma avaliação mais rigorosa melhoram a previsão de demanda por SKU, **sem perder a explicabilidade** que o PCP precisa para auditar cada número.

Hoje ([forecasting.py](../src/caderno_inteligente/forecasting.py)) cada SKU escolhe entre dois candidatos (média móvel de 3 meses e sazonal ingênuo de 12 meses) usando **um único holdout de 3 meses**. Dois problemas:

| # | Problema | Efeito |
|---|---|---|
| 1 | Poucos candidatos | Nível e tendência suave, demanda intermitente e combinações não são testados |
| 2 | Holdout único de 3 meses | A seleção é ruidosa; o WAPE do modelo vencedor é otimista porque é medido no mesmo holdout que o escolheu |

## 2. Princípios (herdados e inegociáveis)

1. **Aditivo.** `forecasting.py`, o ranking, o score, as regras e os casos congelados **não mudam** até a decisão de promoção (14.5). Tudo novo vive em módulos e endpoints novos.
2. **Explicável.** Só entram modelos que se descrevem em uma frase e se recalculam à mão. Sem caixa-preta, sem ML de aprendizado (XGBoost, redes, LSTM): 50 SKUs × 24 meses não sustentam.
3. **Sem dependência pesada.** Implementar em numpy/pandas (já presentes). Nada de `statsmodels`/`scipy`/`scikit-learn`: peso no deploy da Vercel e superfície de manutenção.
4. **Sem vazamento de futuro.** Todo parâmetro de modelo é estimado só com dados anteriores à origem de cada janela.
5. **Critério de promoção escrito antes de olhar o resultado** (seção 8). Se o desafiante não vencer, a etapa termina como achado honesto, não como fracasso.
6. **Observado ≠ estimado; ausente não é zero; revisão humana.** Todo número novo segue `FIELD_NATURE` e `requires_human_review`.
7. **Contrato.** Campo novo lido pelo frontend entra em `frontend/src/test/contract-keys.json`; o orçamento de `volume-budget.json` não é afrouxado (usar tabela, "?" e tooltip).

## 3. Fatos que condicionam o desenho

- Cada SKU tem no máximo **24 meses** de série. Isso são só 2 ciclos sazonais: **Holt-Winters/ETS sazonal completo não é validável** (as janelas de treino têm 15 a 21 meses). Fica fora; a sazonalidade entra por candidatos mais simples (14.1).
- A base declara a previsão **global por SKU** (sem canal/parceiro): a etapa não muda esse escopo.
- Medido na 14.0 ([etapa-14-0-linha-de-base.md](etapa-14-0-linha-de-base.md)): os 50 SKUs têm 24 meses e **nenhum tem mês zerado**. Croston/SBA, portanto, **não entra** nesta base (nem há limiar de intermitência em config; entra numa etapa futura se uma base nova tiver séries intermitentes), e os candidatos novos são 4. O WAPE atual já é baixo (mediana 6,4% no holdout), então o ganho esperado é modesto.
- `events.py` evita dupla contagem de evento só para `seasonal_naive_12` (linha ~220) e usa `moving_average_3` como modelo de cenário. Promover outro modelo exige revisar essa regra.

## 4. Etapa 14.0 — Linha de base e perfil da série (0,5 dia)

> **Status: implementada** (ver [etapa-14-0-linha-de-base.md](etapa-14-0-linha-de-base.md)). Resultado que muda o plano: sem demanda intermitente na base, Croston/SBA fica de fora (4 candidatos novos). Os artefatos ficaram em `docs/etapa-14-0/` e o script em `scripts/profile_series.py`.

- Rodar `pytest` (com `--basetemp` no scratchpad) e `npm run check`: linha de base verde.
- Congelar o hash da planilha no documento da etapa.
- Script de perfil (descartável, em `scripts/`): por SKU, meses de histórico, % de meses com zero, coeficiente de variação, modelo hoje escolhido. Registrar a distribuição no doc da etapa.
- Salvar o **snapshot da previsão atual** (modelo, `forecast_values`, WAPE) para provar depois que nada mudou.

## 5. Etapa 14.1 — Modelos candidatos (1 dia)

> **Status: implementada** (ver [etapa-14-1-modelos-candidatos.md](etapa-14-1-modelos-candidatos.md)). Ajustes em relação ao desenho abaixo: Croston saiu (14.0); o histórico mínimo de `ses` é 6 e o de `holt_damped` é 9; a configuração ficou em `forecast_engine_config.py`, que só aceita `engine = "v1"` até a 14.5; `SEASONAL_CODES` marca os candidatos que já embutem sazonalidade.

Novo módulo `src/caderno_inteligente/forecast_candidates.py`, mesma assinatura de `_MODELS` (`history, targets -> list[float] | None`). Os dois modelos atuais são reaproveitados, não reimplementados.

| Código | Descrição em uma frase | Parâmetros | Quando se aplica |
|---|---|---|---|
| `moving_average_3` | média dos últimos 3 meses (já existe) | — | sempre |
| `seasonal_naive_12` | mesmo mês do ano anterior (já existe) | — | ≥ 12 meses |
| `ses` | suavização exponencial simples: nível que dá mais peso ao recente | α ∈ {0,1 … 0,9}, escolhido por erro de 1 passo **só no treino** | sempre |
| `holt_damped` | nível + tendência que se amortece com o tempo (evita extrapolar crescimento infinito) | α, β, φ em grade pequena, mesma regra | ≥ 9 meses |
| `seasonal_level` | nível recente × razão sazonal do mesmo mês no ano anterior | razão limitada a [0,5; 2,0] | ≥ 15 meses |
| ~~`croston_sba`~~ | ~~demanda intermitente~~ — **descartado pela 14.0** (nenhum SKU tem mês zerado) | — | — |
| `combo_ma_sn` | média simples de `moving_average_3` e `seasonal_naive_12` | — | ≥ 12 meses |

Regras comuns: previsão nunca negativa; resultado `None` quando faltam dados (nunca zero inventado); toda grade de parâmetros é determinística (sem aleatoriedade) para o teste ser reproduzível.

**Ordem de simplicidade** (para desempate e para a regra de parcimônia): `moving_average_3` < `seasonal_naive_12` < `ses` < `combo_ma_sn` < `croston_sba` < `seasonal_level` < `holt_damped`.

Configuração em `config/forecast_engine.json` (validada no carregamento, como os demais): lista de candidatos habilitados, limiar de intermitência, nº de janelas, passo, histórico mínimo, margem de parcimônia e critérios de promoção.

## 6. Etapa 14.2 — Backtest rolante e avaliação aninhada (1 dia)

> **Status: implementada** (ver [etapa-14-2-backtest-rolante.md](etapa-14-2-backtest-rolante.md)). Ajustes em relação ao desenho abaixo: a parcimônia é uma regra de campeão parcial (do mais simples ao mais complexo), então o empate vai para o mais simples, sem desempate alfabético; um candidato só compete se tiver previsão em todas as janelas usadas; o mínimo é 1 janela (config `minimum_windows`). **Resultado preliminar:** os três critérios de promoção são atendidos na célula padrão (ganho de WAPE 21,6%), mas o ganho cai para 11% quando se usa uma origem externa de 15 meses; a 14.5 deve avaliar a grade de sensibilidade documentada, não só a célula padrão.

Novo módulo `src/caderno_inteligente/rolling_backtest.py`.

### Seleção por janelas rolantes

- **Origem rolante, horizonte 3 meses, passo 3 meses, 3 janelas** (para n = 24: treino de 15, 18 e 21 meses; teste cobre os últimos 9 meses, sem sobreposição).
- SKUs com série curta usam menos janelas; o mínimo é 1 janela com treino ≥ 6 meses (regra atual). `backtest_windows` informa quantas foram usadas.
- **Métrica de seleção:** WAPE agrupado (`Σ|erro| / Σ real` somando todas as janelas), não a média dos WAPE.
- **Métricas informativas:** viés (`Σ(previsto − real) / Σ real`, negativo = subestima, o que no PCP vira ruptura) e estabilidade (em quantas janelas o modelo vence a baseline).
- **Parcimônia:** um candidato mais complexo só vence se reduzir o WAPE agrupado em pelo menos 5% relativo (parâmetro em config) sobre o mais simples; senão fica o mais simples. Desempate final: ordem alfabética, como hoje.
- **Baseline** continua sendo "repetir o último mês" e **não participa** da seleção.

### Avaliação aninhada (para decidir a promoção)

Medir o WAPE do vencedor no mesmo teste em que foi escolhido é otimista. Para comparar **procedimentos** (o atual × o novo × a baseline) de forma justa:

- Em cada **origem externa** (as 2 últimas: n−6 e n−3), cada procedimento escolhe o modelo **só com dados anteriores à origem** (janelas internas) e então é medido nos 3 meses seguintes.
- O resultado é o WAPE ponderado (e o viés) de cada procedimento nas mesmas janelas externas, SKU a SKU e no agregado.
- Isso é o que vai para o veredito de promoção. O WAPE de seleção continua sendo o exibido por SKU.

### Entregáveis

- Funções puras e testáveis: `rolling_origins(n, horizon, step, windows)`, `rolling_backtest(series, models)`, `nested_evaluation(series, procedures)`.
- Saída por SKU: modelo escolhido, WAPE agrupado, viés, janelas, tabela por candidato (WAPE, viés, janelas vencidas), `status` e `limitation`.

## 7. Etapa 14.3 — API e tela de Validação (0,5 a 1 dia)

> **Status: implementada** (ver [etapa-14-3-laboratorio-previsao.md](etapa-14-3-laboratorio-previsao.md)). Ajustes em relação ao desenho abaixo: a rota é `GET /api/forecast-lab`; o bloco entrou na aba "Modelos de previsão" e inclui a **grade de sensibilidade** (config `sensitivity`), que mostra também a combinação que reprova; o volume das telas ficou dentro do orçamento sem alteração; o cálculo ganhou memória e cache (a primeira chamada leva alguns segundos).

- Endpoint **aditivo** `GET /api/forecast-lab` (ou `/api/forecasts/challenger`): por SKU, campeão atual × desafiante, tabela de candidatos e veredito agregado. Não altera `/api/forecasts`.
- Bloco novo **"Modelos candidatos"** em Bastidores › Validação (tabela por modelo: SKUs em que vence, WAPE agrupado, viés; linha da baseline). Sem coluna nova nas telas de operação, por causa do orçamento de volume; detalhe no "?" e no tooltip.
- Rótulos novos em `MODEL_LABELS`; entradas de glossário curtas (cuidado: o limite de palavras do `/guia` já foi subido uma vez, 400 → 500, e não sobe de novo sem decisão explícita).
- Campos novos em `contract-keys.json`; selo de natureza "estimado" nos números.

## 8. Etapa 14.4 — Intervalos de previsão (opcional, 0,5 dia; é o primeiro corte se o prazo apertar)

- Faixa empírica P10–P90 dos 3 meses, derivada dos **resíduos relativos** das janelas rolantes. Só calculada com pelo menos 6 resíduos válidos; senão `null` ("sem faixa"), nunca faixa inventada.
- Mostrar como "faixa estimada" ao lado da previsão pontual, com a limitação escrita: tamanho de amostra pequeno, faixa indicativa.
- Uso no PCP: ver o risco de produzir a menos ou a mais. Não entra no score nem no ranking.

## 9. Etapa 14.5 — Decisão de promoção (0,5 dia + decisão do usuário)

### Critério (fixado agora, antes de ver os números)

O motor novo substitui o atual **somente se, na avaliação aninhada**:

1. WAPE agregado ponderado do novo procedimento ≤ **95%** do WAPE do atual (melhora relativa de pelo menos 5%);
2. o viés absoluto agregado não piora mais que **2 pontos percentuais**;
3. o novo procedimento supera a baseline em **pelo menos tantos SKUs** quanto o atual.

Se qualquer item falhar: **não promover**. O desafiante fica como "laboratório" e o achado entra no relatório ("testamos X modelos adicionais com backtest rolante; o ganho não passou do critério").

### Se promover: mapa de impacto

A promoção é uma etapa à parte, só com aprovação explícita, porque muda saídas oficiais. Flag em `config/forecast_engine.json` (`engine: "v1" | "rolling"`, padrão `v1`). Precisam ser revisados:

| Ponto | Por quê |
|---|---|
| `forecasting.py` (saídas, `MODEL_LABELS`, `_MODELS`) | motor de seleção muda |
| `revenue.py` | importa `_backtest` e `_monthly_series`; faturamento estimado muda |
| `events.py` | dupla contagem só trata `seasonal_naive_12`; `seasonal_level`/`combo_ma_sn` também embutem sazonalidade |
| `validation_center.py` | usa `_MODELS` e `MODEL_LABELS` para recomputar holdouts e baseline |
| `action_labels.py` e regras | dependem do status e da confiança da previsão |
| `run_comparison.py` | troca de modelo entre execuções vira diferença legítima; explicar na tela |
| `config/validation_center.json` | casos congelados e resultados esperados |
| Snapshots de teste | regenerar com justificativa registrada no doc |

## 10. Etapa 14.6 — Testes, documentação e demonstração (0,5 dia)

### Testes

- **Modelos:** um teste por candidato com série de resposta conhecida calculada à mão (SES com α fixo, Holt amortecido, razão sazonal e seu limite).
- **Sem vazamento:** alterar valores futuros à origem não muda a previsão da janela.
- **Origens rolantes:** índices corretos para n = 24, série curta, série no limite do mínimo.
- **Regras:** parcimônia (empate técnico fica no mais simples), baseline fora da seleção, `None` quando faltam dados, intermitência abaixo/acima do limiar.
- **Regressão:** com `engine = v1`, o snapshot de 14.0 fica idêntico (previsão, ranking, score, rótulos).
- **Aninhada:** teste com série sintética em que o vencedor da seleção é sabidamente enganoso, e a avaliação aninhada o revela.
- **Contrato e volume:** `contract-keys.json` e `volume-budget.json` verdes.
- **Casos congelados:** pelo menos um novo em `config/validation_center.json` (por exemplo, SKU intermitente em que a média móvel superestima).

### Documentação

- `docs/etapa-14-modelos-candidatos.md`: perfil da base, resultados datados, hash da planilha, veredito de promoção, limitações. Linhas novas em `docs/calculations.md` (seção 3) e `docs/decisions.md`.
- Roteiro de demonstração: história curta "por que este modelo para este SKU", com a tabela de candidatos e a faixa estimada.
- Relatório da Semana 4: números datados; **não afirmar ganho** que o critério não confirmou. Citar o MAPE de 31% de `Indicadores_Atuais` só como contexto, nunca como comparação direta (métricas e escopos diferentes).

## 11. Sequência, esforço e risco

| Ordem | Subetapa | Esforço | Depende de | Risco |
|---|---|---|---|---|
| 1 | 14.0 Linha de base e perfil | 0,5 dia | — | baixo |
| 2 | 14.1 Modelos candidatos | 1 dia | 14.0 | médio (parâmetros e séries curtas) |
| 3 | 14.2 Backtest rolante e aninhado | 1 dia | 14.1 | médio (índices e vazamento) |
| 4 | 14.3 API e Validação | 0,5 a 1 dia | 14.2 | baixo (orçamento de volume) |
| 5 | 14.4 Intervalos (opcional) | 0,5 dia | 14.2 | baixo |
| 6 | 14.5 Decisão de promoção | 0,5 dia + decisão | 14.2 e 14.3 | **alto se promover** (muda saídas oficiais) |
| 7 | 14.6 Testes, docs e demonstração | 0,5 dia | todas | baixo |

Total: 4 a 5 dias úteis (3,5 a 4 sem os intervalos). **Corte recomendado se apertar:** 14.0 a 14.3 e 14.6, sem 14.4, deixando a promoção para depois da demonstração.

## 12. Riscos e mitigação

| Risco | Mitigação |
|---|---|
| Superajuste da seleção (mais candidatos = mais chance de "ganhar por sorte") | parcimônia de 5%, janelas rolantes, avaliação aninhada |
| Amostra pequena (2 ciclos sazonais) | não usar Holt-Winters; razão sazonal limitada; declarar limitação |
| Mudar números oficiais sem querer | flag `engine` com padrão `v1`, teste de regressão com snapshot |
| Tela mais pesada | só tabela em Validação; sem coluna nova; orçamento intocado |
| Resultado "não melhorou" visto como fracasso | critério escrito antes; achado publicável |

## 13. Fora do escopo

- Modelos de aprendizado de máquina (árvores, redes, LSTM) e regressores externos (preço, campanha, clima).
- Previsão por canal, parceiro ou região, e reconciliação hierárquica.
- Retreinamento automático por feedback.
- **Quantidade sugerida a fabricar** (previsão menos estoque, estoque de segurança, lead time): é cálculo determinístico, não IA, e é o candidato natural à **Etapa 15**. A faixa da 14.4 alimentaria o estoque de segurança.

## 14. Aceite da etapa

- Linha de base: suíte verde e snapshot da previsão atual guardado.
- Seis candidatos (os 2 atuais + `ses`, `holt_damped`, `seasonal_level`, `combo_ma_sn`; Croston descartado pelo perfil da 14.0) implementados, testados e sem dependência nova.
- Backtest rolante e avaliação aninhada reproduzíveis, sem vazamento.
- Endpoint e bloco de Validação mostrando campeão × desafiante por SKU e o veredito agregado.
- Veredito de promoção documentado pelo critério da seção 9; com `engine = v1`, nenhuma saída oficial mudou.
