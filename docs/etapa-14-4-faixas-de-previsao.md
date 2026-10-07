# Etapa 14.4 — Faixas de previsão (P10–P90)

Quinta subetapa do [plano da Etapa 14](plano-etapa-14-modelos-candidatos.md), depois do [laboratório](etapa-14-3-laboratorio-previsao.md). **Nenhuma saída oficial mudou:** as faixas existem só no motor rolante (desafiante), aparecem apenas no laboratório da Validação e não entram no score, no ranking nem em nenhuma recomendação.

## Resultado em uma frase

A faixa de 80% (P10–P90) **cobriu 48% dos meses testados fora da amostra**, bem abaixo dos 80% nominais. Ela é uma indicação, não uma garantia, e a tela diz isso. Não foi ajustada para "acertar" a cobertura.

## Como a faixa é calculada

1. **Erros relativos:** em cada mês das janelas de teste do backtest rolante, `(real − previsto) ÷ previsto` para o modelo escolhido do SKU. Previsão zero não tem erro relativo e fica de fora; nunca vira erro zero.
2. **Quantis:** o 10º e o 90º percentil desses erros (interpolação linear). Exige pelo menos `minimum_residuals` (6) erros; com 3 janelas há 9. Sem isso o SKU fica **sem faixa** (`null`), nunca com faixa inventada.
3. **Aplicação:** `previsão × (1 + quantil)` para cada um dos 3 meses. A faixa **nunca é negativa e sempre contém a previsão pontual**. Se os erros fossem todos do mesmo lado (previsão sempre abaixo do real, por exemplo), a faixa se estende até a previsão em vez de deixá-la de fora. Isso alarga a faixa, não a estreita.
4. **Quando não há faixa:** série curta (poucos erros), demanda real zero nas janelas (`wape_indefinido`) ou recuo do modelo escolhido para a média móvel na hora de prever.

Configuração em `config/forecast_engine.json` (chave `intervals`: `lower_quantile` 0,1; `upper_quantile` 0,9; `minimum_residuals` 6), validada no carregamento.

## Calibração fora da amostra (`interval_calibration`)

A pergunta que importa para o PCP é se a faixa acerta. Em cada origem externa, o motor rolante escolhe o modelo e calcula os quantis **só com dados anteriores a ela**; depois se conta quantos dos 3 meses seguintes caíram dentro da faixa.

| Medida (base atual, hash `03fa0ed4…803f`) | Valor |
|---|---|
| Nível nominal | 80% |
| Meses testados | 150 (50 SKUs × 3 meses) |
| Dentro da faixa | 72 |
| **Cobertura observada** | **48%** |
| Largura mediana (faixa ÷ previsão) | 13% |
| Origens testadas | só a de treino de 21 meses |

Por que só uma origem: na origem de 18 meses o backtest interno tem 1 janela (3 erros, menos que os 6 exigidos), então não há faixa. Os 150 meses são todos do **mesmo trimestre**. Medida pouco robusta, mas suficiente para mostrar que a faixa é estreita demais.

### Por que a faixa ficou estreita (hipóteses, não conclusões)

- Os erros usados vêm das janelas em que o modelo foi **escolhido**: são otimistas (o modelo foi selecionado por errar pouco ali). Fora da amostra o erro costuma ser maior.
- São poucos erros por SKU (6 a 9), e o P10/P90 de uma amostra tão pequena fica perto do mínimo e do máximo observados.
- Os erros dos 3 meses de um mesmo trimestre são correlacionados.

### O que não foi feito (decisão para você)

Alargar a faixa por um fator para aproximar a cobertura de 80% (por exemplo, calibrar o fator na própria avaliação fora da amostra) é possível, mas com 1 trimestre de dados o fator sairia calibrado em uma amostra pequena e seria apresentado como se fosse mais confiável do que é. Preferi mostrar a cobertura real e deixar a decisão para a 14.5 (ou para quando houver mais origens).

## O que a tela mostra

No laboratório (aba "Modelos de previsão" da Validação), seção **Faixa de previsão**:

- a frase de cobertura: "Fora da amostra, a faixa de 80% cobriu 48% dos 150 meses testados. Ficou abaixo do esperado: use-a como indicação, não como garantia." (o aviso aparece quando a cobertura fica mais de 5 pontos abaixo do nível; sem meses testados: "Não houve meses suficientes para medir se a faixa acerta.");
- quantos SKUs ficaram sem faixa, se houver;
- lista recolhida com SKU, mês, previsão e faixa estimada do próximo mês;
- o "?" explica o cálculo, o mínimo de erros e que a faixa nunca é negativa, sempre contém a previsão e não entra no ranking nem no score.

O volume das telas ficou dentro do orçamento (`volume-budget.json` intocado).

## API

`GET /api/forecast-lab` ganhou o bloco `intervals`: `level`, `lower_quantile`, `upper_quantile`, `minimum_residuals`, `skus_with_band`, `skus_without_band`, `calibration` (`tested_months`, `hits`, `coverage`, `nominal_level`, `skus_tested`, `origin_train_lengths`, `median_relative_width`) e `items[]` (SKU, modelo, mês, previsão, faixa e nº de erros). Cada registro de `build_rolling_forecasts` tem `forecast_interval` (3 meses de `lower` e `upper`, ou `null`). Natureza dos campos: estimado.

## Desempenho

Ao somar a calibração, o laboratório ficou mais pesado. Medi e vi que a maior parte do custo era remontar a série mensal de cada SKU em cada uma das 6 células da grade. Agora as séries são montadas uma vez (`series_by_sku`) e reaproveitadas; o cálculo completo caiu de cerca de 5,5–6,8 s para 2,6–3,6 s nesta máquina, com resultados idênticos (um teste compara com e sem reaproveitamento). A resposta continua em cache até a planilha ou a configuração mudarem.

## Testes e verificação

- `pytest`: 398 testes passam (372 + 26: quantis e faixa à mão, mínimo de erros, previsão zero, faixa nunca negativa e sempre contendo a previsão, série curta e `wape_indefinido` sem faixa, faixa maior com histórico mais ruidoso, calibração contando acertos fora da amostra — inclusive com futuro de 1000 que nenhuma faixa cobre —, validação da config nova, bloco `intervals` da API e reaproveitamento de séries).
- `npm run check`: 355 testes Vitest (353 + 2), 21 `node --test`, typecheck, build e `check:bundle` passam.
- Contrato `forecastLab` ampliado e verificado contra a API real.
- Navegador: seção renderizada com a resposta real do endpoint injetada (as portas 8000 e 5173 estavam com servidores de outra conversa, que não parei).

## Limitações

- Faixa empírica com 6 a 9 erros por SKU: indicativa. A cobertura observada (48%) mostra que subestima a incerteza.
- A cobertura foi medida em uma única origem (um trimestre) e depende de erros otimistas de seleção.
- A faixa vale para o motor rolante, que não é o oficial. O motor atual não tem faixa; se o motor rolante for promovido (14.5), a faixa vem junto, com o mesmo aviso.
- Faixa por mês, não por trimestre: somar as faixas dos 3 meses não dá a faixa do total.

## Próximo passo

14.5 — decisão de promoção. Para decidir, olhar a grade inteira da 14.3 e a cobertura da faixa desta etapa. Registro de rumo: as duas escolhas de desenho que mudaram o resultado (`minimum_windows` e a restrição de origens) foram feitas depois de ver números, e a faixa estreita é mais uma razão para não prometer ganho de acurácia antes de ter mais origens.
