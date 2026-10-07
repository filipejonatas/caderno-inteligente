# Etapa 14.2 — Backtest rolante e avaliação aninhada

Terceira subetapa do [plano da Etapa 14](plano-etapa-14-modelos-candidatos.md), depois dos [candidatos](etapa-14-1-modelos-candidatos.md). **Nenhuma saída oficial mudou:** `forecasting.py` não foi editado, não há endpoint novo e nada novo é chamado pelo pipeline. Um teste confirma que a previsão oficial é idêntica antes e depois de rodar a avaliação.

## Entregas

| Arquivo | Conteúdo |
|---|---|
| [rolling_backtest.py](../src/caderno_inteligente/rolling_backtest.py) | origens rolantes, seleção por WAPE agrupado com parcimônia, viés, baseline, previsões do motor rolante, avaliação aninhada e conferência dos critérios de promoção |
| [forecast_engine_config.py](../src/caderno_inteligente/forecast_engine_config.py) e [config/forecast_engine.json](../config/forecast_engine.json) | duas chaves novas: `rolling.minimum_windows` e `nested.outer_windows` |
| `tests/test_rolling_backtest.py` | 35 testes novos (mais 4 casos de validação de config) |

## Como funciona

### Seleção por janelas rolantes (`rolling_backtest`)

- **Origens:** para 24 meses, treinos de 15, 18 e 21 meses, cada um testado nos 3 meses seguintes (cobre os últimos 9 meses, sem sobreposição). Séries mais curtas usam menos janelas; abaixo de 9 meses não há backtest rolante (`insufficient_history`).
- **Métrica:** WAPE agrupado (`Σ|erro| ÷ Σ real` somando todas as janelas), nunca a média dos WAPE. Também sai o **viés** (`Σ(previsto − real) ÷ Σ real`; negativo = subestima, o que no PCP vira ruptura) e, por janela, se o candidato vence a baseline.
- **Parcimônia, em regra de "campeão parcial":** do mais simples ao mais complexo, o desafiante só assume se seu WAPE for menor que `WAPE do campeão × (1 − 0,05)`. Isso substitui o desempate alfabético do plano: como as complexidades são todas distintas, o empate vai sempre para o modelo mais simples.
- **Conjunto de janelas:** um candidato só é comparado se tiver previsão em **todas** as janelas usadas, senão o WAPE agrupado compararia coisas diferentes. Quando um candidato exigiria mais histórico que as janelas oferecem, o conjunto de janelas é reduzido até o mínimo de `minimum_windows` (descarta-se antes o candidato de maior histórico mínimo). Cada candidato fora tem o `reason` na tabela.
- **Baseline** ("repetir o último mês", mesma definição da Central de validação) é medida nas mesmas janelas e **nunca participa da seleção**. "Supera" só com WAPE estritamente menor.
- **Sem WAPE definido** (demanda real zero nas janelas): `status = wape_indefinido` e recuo para a média móvel, como no motor atual.

### Avaliação aninhada (`nested_evaluation`)

Em cada origem externa (as 2 últimas: treino de 18 e de 21 meses), cada procedimento escolhe o modelo **só com o treino** (o procedimento recebe apenas essa fatia) e é medido nos 3 meses seguintes:

- `v1`: a seleção do motor atual (holdout de 3 meses entre média móvel e sazonal ingênuo, desempate pelo código);
- `rolling`: a seleção rolante acima;
- `baseline`: sempre repetir o último mês.

`nested_evaluation_table` agrega os 50 SKUs (WAPE e viés ponderados por demanda, SKUs que superam a baseline, placar SKU a SKU) e `promotion_criteria` confere os três critérios fixados em config. **Só confere: a decisão é da 14.5 e exige aprovação.**

### Motor rolante por SKU (`build_rolling_forecasts`)

Mesmo formato do motor atual, mais viés, janelas, WAPE e vitória da baseline e a tabela de candidatos. Insumo da 14.3; não substitui `build_demand_forecasts`.

## Resultado preliminar na base atual (hash `03fa0ed4…803f`)

Medido em 2026-10-07 com a configuração versionada.

**Seleção rolante (24 meses, 3 janelas, 6 candidatos elegíveis em todos os 50 SKUs):** o motor rolante escolheu `ses` em 13 SKUs, `seasonal_naive_12` em 12, `seasonal_level` em 11, `holt_damped` em 8, `combo_ma_sn` em 5 e `moving_average_3` em 1. Em 43 dos 50 SKUs o modelo difere do motor atual (34 média móvel, 16 sazonal ingênuo). WAPE agrupado mediano do escolhido: 6,1%. Esse número é o da seleção (otimista).

**Avaliação aninhada (a que vale para decidir):**

| Procedimento | WAPE ponderado | Viés ponderado | SKUs que superam a baseline |
|---|---|---|---|
| Baseline (último mês) | 17,0% | +8,5% | — |
| Motor atual (`v1`) | 9,0% | −4,3% | 23 de 50 |
| Motor rolante | 7,0% | −1,9% | 30 de 50 |

Placar SKU a SKU: o rolante é melhor em 28, igual em 9 e pior em 13.

**Critérios de promoção fixados na 14.1:** ganho relativo de WAPE de 21,6% (mínimo 5%), viés absoluto 2,4 p.p. **menor** (limite: piorar no máximo 2 p.p.), 30 × 23 SKUs superando a baseline. Os três critérios são atendidos.

### Sensibilidade (e uma correção de rumo registrada)

O resultado acima **não deve ser lido como veredito**, por duas razões:

1. **Amostra efetivamente pequena.** As duas origens externas são os mesmos dois trimestres para os 50 SKUs; eles compartilham a mesma sazonalidade e não são 50 observações independentes.
2. **Ele depende de uma regra que mudei durante a etapa.** O primeiro rascunho usava `minimum_windows = 2` (que eu havia acrescentado, contrariando o plano, que dizia "mínimo de 1 janela"). Ao testar mais origens externas, o resultado inverteu na origem mais curta, porque com 2 janelas o motor rolante precisava descartar `seasonal_naive_12` e `combo_ma_sn` quando só há 15 meses. Voltei ao valor do plano (1). Isso foi feito depois de ver os números, e por isso registro todas as células:

| Origens externas | `minimum_windows = 1` (valor atual) | `minimum_windows = 2` (descartado) |
|---|---|---|
| 1 (treino 21) | ganho de WAPE 22,6% | 22,6% |
| 2 (18 e 21; padrão) | **21,6%** | 14,4% |
| 3 (15, 18 e 21) | 11,0% | **−26,7%** |

Com `minimum_windows = 1` o motor rolante supera o atual em todas as combinações, mas o ganho cai de 22% para 11% quando a origem de 15 meses entra (a de menor histórico). A produção sempre usa 24 meses (3 janelas com todos os candidatos); as origens curtas medem um regime mais difícil que o de uso. **Para a 14.5, usar a grade inteira e não só a célula padrão.**

## Decisões de desenho a registrar

- `minimum_windows` (padrão 1) e `nested.outer_windows` (padrão 2) são chaves novas de `config/forecast_engine.json`, validadas no carregamento.
- `v1_procedure` repete a regra do motor atual; um teste confirma que ela reproduz o modelo oficial escolhido nos 50 SKUs, para a comparação não derivar se `forecasting.py` mudar.
- Séries entre 6 e 8 meses recebem `status = insufficient_rolling_history` (sem previsão rolante); o motor atual continua valendo para elas. Não ocorre na base atual.

## Testes

- `pytest`: 351 testes passam (312 anteriores + 39 desta etapa). `npm run check` não foi rodado porque nenhum arquivo do frontend mudou.
- **Origens rolantes:** [15, 18, 21] para 24 meses; descarte de janelas curtas; entradas inválidas.
- **À mão:** série constante (todos empatam em 0, vence o mais simples); série exatamente sazonal (vence o sazonal ingênuo com WAPE 0); WAPE e viés da baseline em 1..24 (12 ÷ 129 no aninhado).
- **Sem vazamento:** alterar só os 3 últimos meses não muda o WAPE das janelas de treino 15 e 18 de nenhum candidato; e o procedimento do aninhado recebe só o treino (tamanhos 18 e 21).
- **Regras:** parcimônia (margem 99% trava no mais simples; padrão escolhe o sazonal), baseline fora da seleção, série curta, mínimo de janelas, demanda zero.
- **Critérios de promoção:** todos atendidos, ganho de 4%, ganho exatamente no limiar, viés fora e dentro do limite, menos SKUs superando a baseline e WAPE indefinido.
- **Base real:** os 50 SKUs com 3 janelas e 6 candidatos elegíveis; avaliação aninhada completa; previsão oficial inalterada.

## Limitações

- O backtest mede o passado; a vantagem pode não se repetir (a base parece ter sazonalidade comum a todos os SKUs).
- Seleção por poucas janelas de 3 meses continua ruidosa; a parcimônia reduz, não elimina.
- O WAPE de seleção por SKU (`backtest_wape`) é otimista; use a avaliação aninhada para comparar motores.
- Nada daqui autoriza afirmar ganho de acurácia no relatório antes da 14.5 e da amostra mínima já definida.

## Próximo passo

14.3 — endpoint aditivo `/api/forecast-lab` e bloco "Modelos candidatos" na Validação, mostrando campeão × desafiante, a tabela de candidatos, a avaliação aninhada e a grade de sensibilidade.
