# Etapa 14.0 — Linha de base e perfil das séries

Primeira subetapa do [plano da Etapa 14](plano-etapa-14-modelos-candidatos.md). Nenhuma saída da aplicação mudou: só foram adicionados um script de leitura e artefatos de referência.

## O que foi feito

1. **Linha de base verde** antes de qualquer mudança (2026-10-07):
   - `pytest`: 274 testes passaram (rodado com `--basetemp` no scratchpad, por causa do `PermissionError` conhecido em `tmp_path`);
   - `npm run check` (frontend): typecheck, 344 testes Vitest, 21 testes `node --test`, build e `check:bundle` passaram.
2. **Hash da planilha congelado:** `03fa0ed400aa3f8e14de8f8232cd12727a54c85089a36672f009cae37b78803f` (igual ao registrado na Etapa 9; o XLSM não foi tocado).
3. **Script de perfil** [scripts/profile_series.py](../scripts/profile_series.py): somente leitura, com `--write DIR` para gravar os artefatos.
4. **Artefatos em [docs/etapa-14-0/](etapa-14-0/):**
   - `perfil-series.csv`: por SKU, meses de histórico, meses com zero, CV, modelo e WAPE atuais;
   - `resumo-perfil.json`: o resumo abaixo;
   - `snapshot-previsao-v1.json`: previsão oficial atual dos 50 SKUs (modelo, valores, WAPE, tendência, confiança). É a referência de regressão: com `engine = v1` nada disso pode mudar. Regerar o arquivo produz bytes idênticos (determinístico).

Para refazer: `python scripts/profile_series.py --write docs/etapa-14-0`.

## Perfil da base (planilha de hash `03fa0ed4…803f`)

| Medida | Resultado |
|---|---|
| SKUs com previsão | 50 |
| Histórico por SKU | 24 meses em **todos** os 50 |
| SKUs com menos de 15 meses (mínimo da 1ª janela rolante) | 0 |
| SKUs com algum mês de venda zero | **0** |
| Maior parcela de meses com zero | 0% |
| CV (desvio ÷ média) | mediana 0,125; de 0,078 a 0,456 |
| Modelo atual escolhido | `moving_average_3`: 34 SKUs; `seasonal_naive_12`: 16 SKUs |
| WAPE atual do modelo escolhido (holdout de 3 meses) | mediana 6,4%; média 7,0%; máximo 20,0% (CI-0031) |
| Mediana por modelo | média móvel 6,7%; sazonal ingênuo 6,0% |

## O que isso muda no plano

1. **Croston/SBA sai da lista de candidatos.** Nenhum SKU tem mês zerado, então não há demanda intermitente para tratar. O limiar de 30% fica em config só como salvaguarda para bases futuras, mas o modelo não entra na avaliação desta base. Os candidatos novos passam de 5 para **4** (`ses`, `holt_damped`, `seasonal_level`, `combo_ma_sn`).
2. **Todas as séries têm 24 meses**, então as 3 janelas rolantes (treino de 15, 18 e 21 meses) valem para os 50 SKUs. Não há caso de série curta nesta base; o tratamento continua previsto e testado com série sintética.
3. **A margem de ganho é pequena.** Com séries estáveis (CV mediano 12%) e WAPE atual já em torno de 6–7% no holdout, o esperado é um ganho modesto, se houver. Esse WAPE é otimista (medido no mesmo holdout que escolheu o modelo), e a avaliação aninhada da 14.2 mede o valor real. O critério de promoção (melhora de pelo menos 5% relativo) foi escrito exatamente para não confundir ruído com ganho; um veredito "não promover" é um resultado plausível e válido.

## Limitações

- O perfil descreve esta planilha; outra base pode ter séries curtas ou intermitentes.
- O WAPE do snapshot é o do motor v1 (holdout único) e não deve ser citado como acurácia esperada em produção.

## Próximo passo

14.1 — candidatos em `src/caderno_inteligente/forecast_candidates.py`, já sem Croston.
