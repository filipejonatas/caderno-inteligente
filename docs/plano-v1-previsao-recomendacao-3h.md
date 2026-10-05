# Plano de implementação em 3 horas — previsão por SKU e recomendação operacional

## 1. Objetivo da entrega

Adicionar ao Protótipo V1 uma camada preditiva pequena, auditável e demonstrável que responda:

1. qual é a tendência de demanda de cada SKU;
2. qual é a previsão para os próximos três meses;
3. qual quantidade deve ser considerada para produção no próximo ciclo;
4. quais dados, premissas e limitações sustentam a recomendação.

A implementação deve preservar o ranking, o score, as regras atuais, o processamento do Excel e os contratos já consumidos pelo frontend. Os novos campos serão aditivos e aparecerão no detalhe do SKU.

## 2. Recorte obrigatório

### Dentro do escopo

- previsão mensal de quantidade por SKU;
- seleção automática entre duas técnicas simples;
- backtest usando os três últimos meses conhecidos;
- tendência crescente, estável ou decrescente;
- erro do modelo e confiança;
- recomendação operacional quantitativa e explicável;
- apresentação no drawer atual de detalhe do SKU;
- testes automatizados;
- documentação do modelo, arquitetura e limitações.

### Fora do escopo desta entrega

- previsão por parceiro, canal ou região;
- faturamento previsto;
- treinamento em serviço externo;
- LLM, chatbot ou texto generativo;
- otimização matemática da capacidade;
- criação automática de ordem de produção;
- alteração do score ou do ranking oficial;
- novas tabelas no Supabase;
- nova página completa no frontend;
- novas dependências Python ou JavaScript.

## 3. Decisão de modelagem

Implementar um modelo preditivo híbrido e explicável usando apenas `pandas` e a biblioteca padrão.

Para cada SKU, comparar:

1. **Média móvel de três meses**: adequada para demanda recente e mudanças graduais;
2. **Sazonal ingênuo de 12 meses**: usa o valor do mesmo mês do ano anterior e captura sazonalidade anual simples.

O sistema deve testar ambos nos três últimos meses conhecidos e selecionar o de menor WAPE. Se o sazonal não possuir histórico suficiente, utilizar apenas a média móvel.

Essa escolha é adequada para o hackathon porque:

- é reproduzível e rápida;
- funciona com os 24 meses disponíveis;
- permite comparação objetiva com uma alternativa simples;
- é explicável para o usuário e para a banca;
- não inventa precisão que os dados não sustentam.

### Regras do histórico

- agregar `Vendas_24m` por `Mês` e `SKU`, somando `Quantidade faturada`;
- ordenar os meses cronologicamente;
- reindexar a série mensal entre o primeiro e o último mês observado;
- mês ausente dentro desse intervalo representa quantidade faturada zero;
- nunca usar `Forecast_Comercial` como valor realizado ou como entrada do modelo;
- manter `Forecast_Comercial` atual como referência separada para comparação.

### Backtest

- reservar os três últimos meses de cada SKU como holdout;
- gerar previsões usando somente os meses anteriores ao mês previsto;
- calcular:

```text
WAPE = soma(|real - previsto|) / soma(real)
```

- se a soma real do holdout for zero, retornar WAPE nulo e confiança baixa;
- selecionar o candidato com menor WAPE válido;
- depois da seleção, recalcular a previsão usando todo o histórico disponível.

### Previsão futura

- horizonte: três meses;
- previsões nunca podem ser negativas;
- arredondar valores apresentados para uma casa decimal;
- a média móvel deve ser recursiva: cada mês previsto passa a compor a janela do mês seguinte;
- o sazonal usa o valor do mesmo mês do ano anterior;
- se houver menos de seis meses válidos, não produzir previsão e informar dados insuficientes.

### Tendência

Comparar a média dos três meses mais recentes com a média dos três meses anteriores:

```text
variação > +10%  → crescente
variação < -10%  → decrescente
demais casos     → estável
```

Quando a base de comparação for zero, não calcular percentual; retornar tendência crescente somente se o período recente for positivo, acompanhada de confiança baixa.

### Confiança preditiva

```text
WAPE <= 20%       → alta
20% < WAPE <= 40% → média
WAPE > 40%        → baixa
WAPE ausente      → baixa
```

Confiança representa desempenho no holdout, não garantia sobre o futuro.

## 4. Contrato da previsão

Criar `src/caderno_inteligente/forecasting.py` com uma função pública equivalente a:

```python
build_demand_forecasts(sales: pd.DataFrame, horizon: int = 3, holdout: int = 3) -> pd.DataFrame
```

Uma linha por SKU, com:

```text
sku
reference_month
history_months
model
model_label
forecast_months
forecast_values
forecast_next_month
forecast_total_3m
trend
trend_change_ratio
backtest_wape
forecast_confidence
status
limitation
```

`forecast_months` e `forecast_values` devem ser listas JSON compatíveis e possuir exatamente três itens quando `status == "ok"`.

Valores aceitos:

```text
model: moving_average_3 | seasonal_naive_12 | null
trend: crescente | estável | decrescente | indeterminada
forecast_confidence: alta | média | baixa
status: ok | insufficient_data
```

## 5. Recomendação operacional derivada

Criar `src/caderno_inteligente/recommendations.py` com uma função pura que receba o indicador atual do SKU e sua previsão.

### Cálculo

Usar o primeiro mês previsto como horizonte do próximo ciclo:

```text
estoque_seguranca_quantidade = venda_media_dia × dias_estoque_seguranca

demanda_a_cobrir = máximo(
    previsão_do_próximo_mês,
    pedidos_em_carteira
)

necessidade_bruta = máximo(
    0,
    demanda_a_cobrir
    + estoque_seguranca_quantidade
    - estoque_atual
    - produção_aberta
)
```

Arredondar a necessidade para cima pelo lote mínimo:

```text
quantidade_sugerida = ceil(necessidade_bruta / lote_mínimo) × lote_mínimo
```

Se o lote mínimo for zero ou ausente, usar a necessidade bruta arredondada para cima.

### Importante

- usar `max(previsão, carteira)`, e não somar os dois, para reduzir risco de dupla contagem;
- não limitar automaticamente pela capacidade, pois a capacidade está agregada por família e semana;
- quando houver conflito de capacidade, sinalizar necessidade de validação humana;
- não criar ordem de produção automaticamente;
- não alterar o ranking oficial.

### Ação sugerida

```text
previsão indisponível                  → investigar_dados
quantidade > 0 e conflito capacidade   → produzir_validar_capacidade
quantidade > 0                         → produzir
quantidade == 0 e excesso identificado → monitorar_excesso
quantidade == 0                         → sem_acao_necessaria
```

### Confiança da recomendação

- começar com a confiança do forecast;
- reduzir para baixa quando não houver sell-out observado;
- limitar a média quando houver conflito de capacidade;
- explicar explicitamente cada redução.

### Contrato

```text
action
action_label
horizon
suggested_quantity
raw_quantity
minimum_lot
forecast_next_month
backlog_quantity
safety_stock_quantity
current_stock
open_production_quantity
capacity_status
confidence
confidence_reason
rationale
calculation
assumptions
limitations
requires_human_review
```

`calculation` deve conter os valores usados, e não apenas uma frase.

## 6. Integração ao pipeline e à API

### `backend/main.py`

1. Calcular forecasts dentro de `_build_pipeline`, uma única vez junto ao cache existente.
2. Acrescentar o DataFrame de forecasts ao retorno interno do pipeline sem quebrar os consumidores atuais.
3. Ajustar `data()` de forma compatível ou criar um helper específico; evitar espalhar mudanças desnecessárias.
4. No `GET /api/priorities/{sku}`, adicionar:

```json
{
  "forecast": {},
  "operational_recommendation": {}
}
```

5. Manter intactos `indicator`, `issues`, `priority`, `score_contributions` e `limitation`.
6. Se a previsão falhar por dados insuficientes, responder `200` com `status: insufficient_data`; não retornar erro 500.
7. Não adicionar endpoint novo se o detalhe existente for suficiente para a demonstração.

### Cache

O forecast deve reutilizar o cache atual. Nenhum cálculo deve ocorrer novamente a cada abertura do drawer enquanto a assinatura dos arquivos não mudar.

## 7. Frontend mínimo

### `frontend/src/types.ts`

Adicionar tipos `DemandForecast` e `OperationalRecommendation` e incluí-los em `SkuDetail`.

### `frontend/src/pages.tsx`

No `SkuDrawer`, inserir uma seção antes de “Riscos e evidências”:

```text
Previsão e recomendação
```

Exibir:

- tendência;
- modelo selecionado;
- previsão do próximo mês;
- total previsto para três meses;
- erro WAPE do backtest;
- confiança;
- ação sugerida;
- quantidade sugerida;
- status de capacidade;
- fórmula com os valores usados;
- selo “Requer validação humana”.

Quando os dados forem insuficientes:

- mostrar um estado informativo;
- explicar a limitação;
- não exibir quantidade igual a zero como se fosse recomendação válida.

### Design

- reutilizar `SectionCard`, `Badge`, grids e tokens existentes;
- adicionar somente o CSS estritamente necessário;
- manter responsividade do drawer;
- não criar gráficos nesta versão se isso ameaçar o prazo;
- uma lista simples dos três meses e valores é suficiente.

## 8. Testes obrigatórios

### `tests/test_forecasting.py`

Criar séries sintéticas e cobrir:

1. série sazonal seleciona ou aceita o modelo sazonal quando seu erro é menor;
2. série recente suave seleciona média móvel quando seu erro é menor;
3. previsão contém exatamente três meses;
4. previsões nunca são negativas;
5. tendência crescente, estável e decrescente;
6. histórico insuficiente retorna `insufficient_data`;
7. holdout não é utilizado como entrada da previsão avaliada;
8. WAPE e confiança seguem as faixas documentadas.

### `tests/test_recommendations.py`

Cobrir:

1. fórmula da necessidade;
2. uso de `max(forecast, backlog)` para evitar dupla contagem;
3. arredondamento por lote mínimo;
4. quantidade nunca negativa;
5. conflito de capacidade exige revisão humana;
6. ausência de sell-out reduz confiança;
7. forecast insuficiente resulta em `investigar_dados` sem quantidade enganosa.

### Teste de contrato da API

Atualizar `tests/test_explainability_api.py` para verificar:

- presença de `forecast` e `operational_recommendation`;
- três pontos de previsão em um SKU válido;
- presença de evidências e limitações;
- recomendação marcada para revisão humana;
- campos antigos continuam presentes.

### Verificações finais

```powershell
python -m pytest -p no:cacheprovider
cd frontend
npm run check
```

## 9. Documentação da Semana 3

Criar `docs/semana-3-modelo-preditivo.md` contendo:

1. problema e recorte;
2. tarefa executada pelo modelo;
3. alternativas comparadas;
4. razão da escolha automática por WAPE;
5. origem e qualidade dos dados;
6. fluxo de processamento;
7. retroalimentação atual:
   - feedback humano é registrado;
   - ele ainda não retreina o modelo automaticamente;
   - poderá ser usado para recalibrar regras e confiança futuramente;
8. segurança e privacidade;
9. limitações;
10. decisão humana obrigatória;
11. plano de validação da Semana 4.

Atualizar `docs/decisions.md` com a decisão do modelo e deixar claro que a recomendação é apoio à análise.

## 10. Cronograma de 3 horas

### 00:00–00:15 — Preparação

- confirmar suíte verde;
- criar contratos de forecast e recomendação;
- separar um exemplo de SKU para a demo.

### 00:15–01:00 — Forecast

- implementar agregação mensal;
- implementar os dois candidatos;
- implementar holdout, WAPE, seleção, tendência e confiança;
- escrever testes unitários.

### 01:00–01:35 — Recomendação e API

- implementar fórmula e arredondamento por lote;
- implementar ação, confiança, premissas e limitações;
- integrar ao cache e ao detalhe do SKU;
- atualizar teste de contrato.

### 01:35–02:10 — Frontend

- adicionar tipos;
- criar a seção no drawer;
- tratar sucesso e dados insuficientes;
- ajustar responsividade.

### 02:10–02:35 — Validação

- executar testes Python;
- executar `npm run check`;
- corrigir apenas falhas relacionadas;
- testar manualmente um SKU com previsão e um caso de baixa confiança.

### 02:35–02:50 — Material da Semana 3

- escrever justificativa do modelo;
- documentar arquitetura, fluxo, retroalimentação e limitações;
- preparar roteiro de demonstração de dois minutos.

### 02:50–03:00 — Entrega

- revisar `git diff`;
- confirmar ausência de segredos;
- commit e push;
- aguardar deploy;
- testar `/api/health` e um detalhe de SKU publicado.

## 11. Critérios de aceite

- um SKU válido mostra três meses de previsão;
- o método é escolhido por comparação no holdout;
- o erro de backtest fica visível;
- a tendência fica visível;
- a recomendação mostra quantidade e cálculo;
- lote mínimo é respeitado;
- restrição de capacidade não é ocultada;
- falta de dados não vira previsão zero;
- recomendação exige revisão humana;
- score e ranking permanecem iguais aos anteriores;
- nenhuma nova dependência é adicionada;
- testes Python e `npm run check` passam;
- documentação responde às perguntas da Semana 3.

## 12. Roteiro curto de demonstração

1. Abrir a Visão geral e explicar que o sistema reúne os sinais operacionais.
2. Abrir um SKU prioritário.
3. Mostrar estoque, carteira, produção aberta e sell-in/sell-out.
4. Mostrar os três meses previstos e o modelo escolhido pelo menor erro histórico.
5. Mostrar a quantidade sugerida e abrir a fórmula usada.
6. Destacar confiança, restrição de capacidade e revisão humana.
7. Registrar feedback para demonstrar retroalimentação e rastreabilidade.

## 13. Prompt para a IA implementadora

> Implemente integralmente `docs/plano-v1-previsao-recomendacao-3h.md`, respeitando o timebox e o recorte. Não adicione dependências, páginas novas ou migrations. Preserve contratos existentes, score, ranking, regras e processamento do Excel. Adicione forecast e recomendação apenas como campos aditivos no detalhe do SKU. A previsão deve comparar média móvel de três meses e sazonal ingênuo de doze meses em holdout de três meses, escolher o menor WAPE e sinalizar dados insuficientes. A recomendação deve ser transparente, respeitar lote mínimo, não somar previsão e carteira, não prometer viabilidade individual de capacidade e sempre exigir revisão humana. Implemente testes unitários e de contrato, atualize a documentação da Semana 3 e execute toda a suíte Python e `npm run check`. Ao final, informe arquivos modificados, resultados dos testes, limitações e passos de deploy. Não altere segredos nem faça deploy.
