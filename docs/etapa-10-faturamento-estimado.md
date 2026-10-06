# Etapa 10 — Previsão de faturamento (estimativa)

Primeira etapa do [plano de aderência ao desafio](plano-aderencia-desafio.md). Responde à exigência do PDF "prever demanda **e faturamento**" sem tocar na previsão em unidades, no score, no ranking, nas regras ou na recomendação operacional.

## Resultado

| Item do plano | Entrega |
|---|---|
| `faturamento = previsão em unidades × preço vigente` | `src/caderno_inteligente/revenue.py` (`build_revenue_forecasts`); camada derivada, só lê `forecasting.py` |
| Preço vigente | `Precos_Produtos` (aba opcional, lida se existir). Fallback: último preço faturado em `Vendas_24m`, com `price_source` explícito. Sem nenhum dos dois: `status = sem_preco`, valores `null` |
| Rotulado como estimativa | Selo **Estimativa** em todo valor previsto, **Observado** no que vem da planilha, `nature` e `field_nature` na API e "?" com fórmula e limitações |
| Confiança herdada | `forecast_confidence` de cada SKU; nos agregados, `confidence_distribution` (a tela destaca só quando algum SKU não tem confiança alta) |
| Erro em reais | `backtest_wape` do faturamento: erro absoluto em R$ do teste dos últimos 3 meses ÷ faturamento real, por SKU e mês, com o mesmo modelo escolhido |
| Referência S&OP | `commercial_reference`: `Forecast_Comercial` × mesmo preço, **só nos meses em comum** com a previsão. É comparação, não erro, e não substitui a estimativa |
| Série observada | Últimos 12 meses de `Valor faturado (R$)` ao lado dos 3 meses estimados (barras cheias × tracejadas) |
| Agregações | SKU, família e total da empresa; SKU sem preço ou sem previsão fica fora da soma e é listado |

## Contrato (aditivo)

- `GET /api/revenue-forecast`: `items[]` (um por SKU), `families[]`, `total`, `formula`, `field_nature` e `limitations`.
- `GET /api/priorities/{sku}`: novo campo opcional `revenue_forecast` (o item do SKU). É `null` se a estimativa falhar, sem derrubar o detalhe operacional.
- `GET /api/forecasts`, `/api/priorities` e os demais endpoints **não ganharam nenhum campo**.
- `frontend/src/test/contract-keys.json` ganhou o endpoint `revenueForecast` e os campos novos de `skuDetail`.

## Tela

- **Produção › Previsão e ação:** cartão "Faturamento estimado" no topo (gráfico e tabela Escopo × Estimativa × Variação × Erro do teste, com o total da empresa na primeira linha). Se a estimativa falhar, aparece um aviso com "Tentar novamente" e a tela operacional segue intacta.
- **Detalhe do SKU:** bloco "Faturamento estimado" com o cálculo mês a mês (unidades × preço), a série observada e a comparação com o forecast comercial.
- Sem preço ou sem previsão, a tela diz o motivo e **não mostra valor em R$**. Ausência não é faturamento zero.

## Números na planilha atual (hash `03fa0ed4…`)

| Medida | Valor |
|---|---|
| Faturamento estimado, set a nov/2026 | R$ 5.038.491 (50 de 50 SKUs, todos com confiança alta) |
| Observado nos 3 meses anteriores, mesmos SKUs | R$ 4.896.192 (estimativa 2,9% acima) |
| Erro do teste (WAPE em R$) | 6,7% no total; 5,2% a 9,1% por família |
| Forecast comercial × modelo (out e nov) | R$ 3.578.610 × R$ 3.423.882 (modelo 4,3% abaixo) |
| Conflito entre preço da tabela e das vendas | 0 SKUs |

Leitura honesta: o modelo atual é mais plano que o ano anterior. Em nov/2025 o faturamento observado foi R$ 2,18 mi, contra R$ 1,81 mi estimados para nov/2026. A estimativa não incorpora Black Friday nem campanhas; isso é o escopo da Etapa 11.

## Decisões de projeto

1. **`Precos_Produtos` é opcional no carregamento** (`OPTIONAL_SHEETS` em `ingestion.py`). Não foi incluída em `SCHEMAS`, para não tornar a aba obrigatória nem alterar a validação da planilha, o relatório de qualidade ou os testes existentes.
2. **A tupla de `pipeline()` não mudou.** A estimativa é calculada à parte e fica em cache enquanto o pipeline em cache for o mesmo objeto, então invalida junto com ele.
3. **Respeito ao orçamento de volume** (`frontend/src/test/volume-budget.json`, definido na etapa de enxugamento): o teste de volume não foi afrouxado. Para caber, a tabela por SKU não ganhou coluna (o limite é 4), os números ficaram em tabelas, as limitações foram para o "?" (glossário) e a lista de SKUs fora da estimativa ficou em tooltip. A comparação S&OP em agregado existe na API, mas a tela mostra só a de cada SKU.
4. **Sem tooltips nas barras do gráfico**, para não inflar a contagem de números; o gráfico tem rótulo acessível e os valores estão nas tabelas.

## Limitações (declaradas na tela)

- Preço constante: não considera reajuste, desconto, campanha nem mix de canal. A base tem uma única vigência de preço (2024-09-01).
- Receita bruta, sem impostos, devoluções ou bonificações.
- Previsão global por SKU: não existe faturamento previsto por parceiro, canal ou região.
- A confiança é a da previsão em unidades; o erro em reais é o do período de teste, não uma garantia futura.

## Arquivos

### Criados

- `src/caderno_inteligente/revenue.py`
- `tests/test_revenue.py`
- `frontend/src/types-revenue.ts`
- `frontend/src/components/RevenueForecast.tsx`
- `frontend/src/test/revenue.test.tsx`
- `docs/etapa-10-faturamento-estimado.md`

### Modificados

- `src/caderno_inteligente/ingestion.py` (aba opcional)
- `backend/main.py` (endpoint, cache e campo no detalhe do SKU)
- `frontend/src/api.ts`, `types.ts`, `pages/shared.ts` (formatos e glossário), `pages/ForecastsPage.tsx`, `pages/SkuDetailPage.tsx`, `usability.css`
- `frontend/src/test/fixtures.ts`, `utils.tsx`, `contracts.test.ts`, `contract-keys.json` e `tests/test_frontend_contracts.py`
- `docs/api.md`, `docs/calculations.md`, `docs/semana-3-modelo-preditivo.md`, `README.md` e `docs/plano-aderencia-desafio.md`

## Validação

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider
cd frontend; npm run check
```

- **Python:** 209 testes passando (15 novos em `tests/test_revenue.py`: cálculo, preço da tabela × vendas, preço ausente ou zero, SKU sem previsão, agregação, WAPE em R$, referência S&OP, inalterabilidade da previsão em unidades e contrato da API).
- **Frontend:** 176 testes do Vitest, 21 do `node --test`, typecheck, build e varredura de segredos no bundle passando, incluindo volume e acessibilidade das telas alteradas.
- **Regressão:** o hash SHA-256 das respostas de `/api/forecasts`, `/api/priorities`, `/api/overview` e `/api/data-quality` é idêntico antes e depois da etapa.
- **Navegador:** conferido com a API real em `/previsoes` e `/skus/CI-0014`, sem erros no console.

## Não feito nesta etapa

- Sem deploy, sem alteração de segredos e sem alteração da planilha.
- O `scripts/smoke_test.py` não inclui o endpoint novo, para não mudar a contagem de verificações documentada na Etapa 9.
- A visão de faturamento por parceiro, canal ou região não existe: a base só sustenta previsão global por SKU.
