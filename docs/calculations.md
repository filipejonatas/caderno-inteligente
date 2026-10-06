# Cálculos

Todos os cálculos são determinísticos, partem da planilha somente leitura e mantêm dado ausente como `null`, nunca como zero. A unidade de análise operacional é sempre o **SKU global** (`analysis_scope = "SKU global"`); nada é distribuído por parceiro, canal ou semana.

## 1. Indicadores por SKU (`indicators.py`)

| Indicador | Fórmula | Fontes |
|---|---|---|
| Cobertura calculada | `estoque atual / venda média por dia` | `Estoque_Atual`, `Produtos` |
| Diferença de cobertura | `cobertura informada - cobertura calculada` | `Estoque_Atual`, `Produtos` |
| Pedidos em carteira | `soma(quantidade)` por SKU | `Carteira_Pedidos` |
| Produção em ordem | `soma(quantidade)` por SKU | `Ordens_Producao` |
| Primeira conclusão | `mínimo(conclusão prevista)` por SKU | `Ordens_Producao` |
| Estoque projetado | `estoque atual + ordens - carteira` | `Estoque_Atual`, `Ordens_Producao`, `Carteira_Pedidos` |
| Lacuna operacional | `máximo(0, carteira - estoque atual - produção aberta)` | idem |
| Data crítica | menor data disponível entre primeira promessa e primeira conclusão prevista; `critical_date_reason` informa qual foi usada | `Carteira_Pedidos`, `Ordens_Producao` |
| Sell-in / sell-out acumulados | `soma` por SKU | `Sell_In`, `Sell_Out` |
| Diferença sell-in/out | `sell-in - sell-out` | `Sell_In`, `Sell_Out` |
| Visibilidade de sell-out | existe ao menos um parceiro com sell-out para o SKU | `Sell_Out` |
| Capacidade familiar | primeira semana disponível e médias de ocupação no horizonte | `Capacidade_Semanal` |

- `has_sell_out = false` significa ausência de observação. O sell-out fica `null` e `missing_data` inclui `sell_out_quantity`.
- A **lacuna operacional** é uma quantidade para análise, não uma ordem recomendada.
- A **capacidade** é agregada por família e semana. A fonte não aloca pedidos ou OPs a semanas ou linhas, então ela é contexto, não viabilidade de uma ordem.

## 2. Regras e priorização

Sete regras geram sinais com valores usados e origem. O score é a soma dos pesos configurados dos sinais ativos. Detalhes em [regras](rules.md) e [priorização](prioritization.md).

## 3. Previsão de demanda (`forecasting.py`)

- **Série:** faturamento mensal por SKU (`Vendas_24m`), com meses sem venda preenchidos com zero entre o primeiro e o último mês observado.
- **Histórico mínimo:** 6 meses. Abaixo disso, `status = insufficient_data` e nenhuma previsão numérica é gerada.
- **Candidatos:**
  - média móvel de 3 meses, aplicada de forma recursiva;
  - sazonal ingênuo de 12 meses (mesmo mês do ano anterior).
- **Holdout:** os 3 últimos meses são reservados. O modelo de menor WAPE vence e, em caso de empate, a ordem alfabética do código decide.
- **WAPE:** `Σ|real − previsto| / Σ real` nos 3 meses do holdout. Se a demanda real soma zero, o WAPE fica `null`.
- **Confiança da previsão:**
  - alta: WAPE ≤ 20%;
  - média: WAPE ≤ 40%;
  - baixa: WAPE acima de 40% ou indefinido.
- **Tendência:** compara a média dos 3 meses recentes com a dos 3 anteriores.
  - Variação acima de 10% → crescente; abaixo de −10% → decrescente; caso contrário, estável.
  - Com média anterior zero: crescente se a recente for positiva, estável se também for zero.
- **Horizonte:** 3 meses (`forecast_values`); `forecast_next_month` é o primeiro deles.

### 3.1 Faturamento estimado (`revenue.py`)

```text
faturamento estimado do mês = previsão em unidades do mês × preço unitário vigente do SKU
```

- **Preço vigente:** `Precos_Produtos` (aba opcional). Sem preço válido (> 0) nela, usa o último preço faturado do SKU em `Vendas_24m`. Sem nenhum, o SKU fica sem estimativa (`null`, nunca zero). Divergência entre as duas fontes é sinalizada em `price_conflict`; vale o preço da tabela.
- **Agregação:** soma apenas SKUs com estimativa; os demais são listados em `skus_excluded`.
- **Erro em reais (`backtest_wape`):** com o modelo escolhido para cada SKU, soma `|real − previsto| × preço` no teste dos últimos 3 meses e divide pelo faturamento real × preço, por SKU e mês.
- **Variação:** estimativa de 3 meses contra o faturamento observado nos 3 meses anteriores dos mesmos SKUs.
- **Forecast comercial:** `Forecast_Comercial` × mesmo preço, somente nos meses em comum com a previsão; é comparação, não erro.
- **Limites:** preço constante, receita bruta, global por SKU. Estimativa, não faturamento realizado.

### 3.2 Eventos e sazonalidade (`events.py`)

```text
fator do mês (família) = média das ocorrências de [unidades do mês ÷ média dos meses sem evento num raio de 6 meses]
cenário do mês = previsão base × fator do mês  (fator 1 sem evento ou sem evidência)
data de decisão = início do evento − lead time do SKU
```

- **Linha de base:** meses sem evento que afete a família, raio de 6 meses, mínimo de 3 meses; acompanha a tendência da família.
- **Fator:** média das ocorrências (mínimo de 1 e 12 meses de histórico da família), limitada por `config/event_factors.json` (padrão 0,5 a 3,0, com `capped` registrado).
- **Alerta:** evento que cobre a família, não terminou e (começa até o fim do horizonte **ou** `início − lead time − 30 dias` cai dentro do horizonte).
- **Sem dupla contagem:** SKU com previsão `seasonal_naive_12` só recebe alerta.
- **Sem fator inventado:** evento sem histórico direto, família com histórico curto ou sem ocorrência mensurável geram só alerta.
- **Quantidade oficial:** não muda; o cenário mostra a quantidade que resultaria se o próximo mês fosse afetado.

## 4. Recomendação operacional (`recommendations.py`)

```text
demanda a cobrir   = máximo(previsão do próximo mês, carteira)     # não soma, para evitar dupla contagem
segurança (unid.)  = venda média por dia × dias de segurança
necessidade bruta  = máximo(0, demanda a cobrir + segurança − estoque atual − produção aberta)
quantidade sugerida = arredondamento para cima ao múltiplo do lote mínimo
```

**Ação sugerida:**

| Situação | Ação |
|---|---|
| Previsão insuficiente | `investigar_dados`, sem quantidade (`null`) |
| Quantidade > 0 com `CAPACITY_CONFLICT` | `produzir_validar_capacidade` |
| Quantidade > 0 sem conflito de capacidade | `produzir` |
| Quantidade = 0 com `EXCESS_COVERAGE` | `monitorar_excesso` |
| Demais casos | `sem_acao_necessaria` |

**Confiança da recomendação:** parte da confiança da previsão.

- Cai para baixa quando não há sell-out observado.
- Cai de alta para média quando há pressão de capacidade.

Toda recomendação tem `requires_human_review = true` e não cria nem libera ordem de produção.

## 5. Visão comercial parceiro–SKU (`partner_insights.py`)

Usa apenas chaves reais parceiro–SKU–mês. O estoque considerado é o estoque estimado do último sell-out do próprio parceiro, nunca o estoque do CD. Cobertura no parceiro = `estoque estimado / (média mensal de sell-out / 30)`; giro zero ou ausente gera cobertura `null`.

Sinais, limiares e precedência das ações estão em [regras comerciais](commercial-rules.md).

## 6. Central de validação (`validation_center.py`)

- **Baseline de previsão:** repete o último mês observado antes do holdout. Não participa da seleção do modelo. O modelo selecionado só "supera" a baseline com WAPE estritamente menor; empate conta como não superou.
- **WAPE mediano:** mediana dos WAPE por SKU.
- **WAPE ponderado:** `Σ erros absolutos / Σ demanda real` somando os SKUs com demanda no holdout.
- **Casos congelados:** comparam a saída obtida pelas mesmas funções de regras, previsão e recomendação com a saída esperada registrada em `config/validation_center.json`.
- **Tempo de análise:** soma, média e mediana dos minutos informados nas decisões. Antes de 20 registros, não há comparação com a linha de base.

## 7. Comparação entre execuções (`run_comparison.py`)

Para cada SKU presente nas duas execuções, a diferença de score é decomposta usando os pesos gravados em cada uma:

```text
Δ score = Σ peso_alvo(sinais adicionados) − Σ peso_base(sinais removidos) + Σ (peso_alvo − peso_base)(sinais mantidos)
```

Quando a soma das parcelas difere de `Δ score`, o item é marcado como não explicado. A posição pode mudar com score igual quando outros SKUs entram, saem ou mudam de score; o desempate do ranking é por código do SKU.
