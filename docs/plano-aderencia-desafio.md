# Plano de aderência ao Desafio 3 — Caderno Inteligente

Complementa o [Plano da V2](plano-v2-prototipo-top.md). Origem: análise de aderência entre o PDF do desafio, a base XLSM fornecida (idêntica à de `data/source/`) e a solução atual.

## 1. Objetivo

Fechar as lacunas do PDF que ainda estão abertas, sem comprometer o que já funciona:

| # | Lacuna | Exigência do PDF |
|---|---|---|
| 1 | O modelo não prevê faturamento | "Prever demanda **e faturamento** para horizontes futuros" |
| 2 | O calendário de eventos nunca entra em cálculo | "Analisar … sazonalidade"; "calendário, campanhas" como sinais complementares |
| 3 | Os canais diretos não têm visão própria | "Parceiro/Canal" na visualização mínima; "canais diretos" como sinal; "padrões por … região, canal" |
| 4 | Faltam rótulos de ação | "Priorizar produção, Priorizar parceiro, Ampliar mix, Recomendar recompra, Repor" |

## 2. Princípios (herdados da V2 e inegociáveis)

1. **Aditivo.** Não alterar `forecasting.py` (saídas existentes), `prioritization.py`, `rules.py`, pesos, limiares nem o ranking oficial. Tudo novo vive em módulos novos e em campos/endpoints novos.
2. **Observado ≠ estimado.** Todo número novo carrega `nature` (observado, calculado, estimado) e `origin`, no padrão de `FIELD_NATURE`.
3. **Ausente não é zero.** Preço faltando gera `null` e "sem estimativa", nunca R$ 0. Nada é distribuído entre parceiros a partir de dado global.
4. **Revisão humana.** Nenhuma saída é decisão automática; toda sugestão mantém `requires_human_review`.
5. **Referência temporal da base.** "Hoje" é o mês de referência da base (2026-08), como já faz `partner_insights`.
6. **Contrato.** Todo campo novo lido pelo frontend entra em `frontend/src/test/contract-keys.json`.

## 3. Fatos da base que condicionam o desenho

Medidos na planilha em 2026-10-06:

- **Preço é único por SKU e estável:** 50 SKUs, uma vigência (2024-09-01). O preço de `Vendas_24m` é igual ao de `Precos_Produtos` em 100% das linhas.
- **Canais diretos são a maior parte do faturamento:** 68,2% das unidades e 68,2% do valor (E-commerce R$ 11,6 mi, Marketplace R$ 9,1 mi, Loja própria R$ 7,4 mi, de R$ 41,3 mi). O PDF fala em "parcela menor"; a base diz o contrário. Isso reforça a lacuna 3 e deve ser dito na demonstração.
- **Os canais diretos não têm linhas em `Sell_In`/`Sell_Out`**, embora `Parceiros_Canais` declare cobertura "Completo" e 50 SKUs. A visibilidade deles vem de `Vendas_24m`, que é faturamento (venda ao consumidor final nesses canais).
- **Inconsistência entre abas para os KAs:** `Vendas_24m` tem 50 SKUs por KA em 24 meses; `Sell_In` tem 10 SKUs por KA em 12 meses, e as quantidades não coincidem (nenhum par mês–SKU igual). Não reconciliar; sinalizar na qualidade.
- **`Forecast_Comercial`** cobre só Out/26, Nov/26 e Dez/26, em unidades, origem "Consenso S&OP". Serve de referência, não de insumo.
- **Calendário:** 5 eventos, de 15/10/2026 a 20/02/2027, com datas em texto `dd/mm/aaaa`. Três eventos caem no horizonte de 3 meses (Primavera, Black Friday, Natal); Volta às Aulas (05/01/2027) cai na janela de produção.

## 4. Etapa 0 — Pré-requisitos (meio dia)

- Reproduzir a suíte atual (`pytest` com `--basetemp` no scratchpad e `npm run check`) para ter linha de base verde.
- Congelar o hash da planilha no documento da etapa, como na Etapa 9.
- Decidir com o grupo duas pontos abertos (as recomendações padrão estão nas seções):
  - fator de evento por evidência histórica ou por tabela configurável (padrão: evidência histórica; seção 6);
  - tela nova para canais diretos ou aba dentro de Parceiros (padrão: aba; seção 7).

## 5. Etapa 10 — Previsão de faturamento

> **Status: implementada** (ver [etapa-10-faturamento-estimado.md](etapa-10-faturamento-estimado.md)). Ajustes em relação ao desenho abaixo: `Precos_Produtos` é lida como aba opcional; a tabela por SKU não ganhou coluna e as limitações ficaram no "?" por causa do orçamento de volume das telas; a comparação com o forecast comercial em agregado existe só na API (a tela mostra a de cada SKU).

**Resposta ao PDF:** "prever demanda e faturamento", sempre rotulado como estimativa.

### Método

`faturamento_estimado[sku, mês] = previsão_unidades[sku, mês] × preço_vigente[sku]`

- A previsão em unidades é a que já existe (`forecast_values`), sem modificação.
- `preço_vigente` vem de `Precos_Produtos`. Fallback: último preço de `Vendas_24m` para o SKU, com `price_source` explícito. Sem nenhum dos dois: `null` e `status = "sem_preco"`.
- Agregações: SKU, família, canal-agrupador (direto × B2B não é possível, porque a previsão é global; ver limitações) e total da empresa, para 1, 2 e 3 meses.
- **Confiança herdada** de `forecast_confidence`. Nos agregados, mostrar a distribuição (quantos SKUs de confiança alta, média e baixa) e o **WAPE de backtest do faturamento** (mesmo holdout de 3 meses, ponderado por preço), para dizer a precisão em reais, não só em unidades.
- **Referência cruzada:** mostrar o `Forecast_Comercial` (S&OP) convertido em R$ ao lado, com a diferença percentual. É comparação, não substituição.
- **Linha de base de acurácia:** `Indicadores_Atuais` informa MAPE 31% e meta 20%. Citar como contexto na validação, sem afirmar ganho (regra já existente em `validation_center`).

### Entregáveis

- `src/caderno_inteligente/revenue.py` com `build_revenue_forecasts(forecasts, prices, sales)`.
- Endpoint aditivo `GET /api/revenue-forecast` (por SKU, por família e total) e campos opcionais `revenue_forecast_next_month` e `revenue_forecast_total_3m` no detalhe do SKU.
- Frontend: cartão "Faturamento estimado (3 meses)" na página Previsão e no detalhe do SKU, com selo **Estimativa**, confiança e a conta (`unidades × preço`). Série de faturamento observado dos últimos 12 meses ao lado, com selo **Observado**.
- `docs/etapa-10-faturamento-estimado.md`, `docs/calculations.md` atualizado.

### Limitações a declarar na própria tela

- Preço constante: não considera reajuste, desconto, mix de canal nem Black Friday.
- Receita **bruta**: sem impostos, devoluções ou desconto.
- A previsão é global por SKU; não há faturamento previsto por parceiro ou canal.

### Testes e aceite

- Teste unitário de cálculo (unidades × preço), de SKU sem preço (`null`, nunca zero) e de agregação (soma só dos SKUs com estimativa, informando quantos ficaram de fora).
- Teste de contrato e teste que garante que `forecasting.py` e o ranking não mudaram (snapshots de `/api/forecasts` e `/api/prioritization` idênticos antes e depois).
- Aceite: todo valor em R$ previsto exibe selo "Estimativa", confiança e fórmula; nenhum R$ aparece sem origem.

## 6. Etapa 11 — Sazonalidade e eventos (alerta e fator explícito)

> **Status: implementada** (ver [etapa-11-eventos-sazonalidade.md](etapa-11-eventos-sazonalidade.md)). Ajustes em relação ao desenho abaixo: teto do fator em 3,0 (o histórico mostra ×2,41 para Escolar); alertas e cenário ficam dentro de "Sobre a previsão" no detalhe do SKU, por causa do orçamento de blocos da tela; a faixa "Eventos próximos" do Início se chama "Eventos que pedem decisão"; o selo por SKU vai na Previsão.

**Resposta ao PDF:** "analisar sazonalidade" e usar calendário e campanhas como sinal, **sem mexer no modelo base**.

### Duas camadas separadas

1. **Alerta (sempre disponível).** Para cada SKU, listar os eventos do `Calendario_Eventos` que:
   - cobrem a família do SKU (`Famílias impactadas`, separadas por `;`, ou `Todas`) e
   - se sobrepõem ao horizonte de previsão **ou** começam dentro de `lead_time + janela de segurança` a partir do mês de referência.
   Mostrar nome, datas, impacto esperado, observação e a distância em dias.
2. **Fator sazonal explícito (cenário, nunca substitui a previsão).** `previsão_base × fator`, exibida em coluna separada "Cenário com evento".

### Como definir o fator

Por **evidência histórica**, não por constante inventada:

`fator = vendas da família no mesmo período do ano anterior ÷ média mensal da família nos meses sem evento`

- Só calcular com no mínimo 12 meses de histórico da família e informar a amostra (1 ocorrência anterior por evento). Abaixo disso: **somente alerta**, com o texto "sem evidência para estimar fator".
- Eventos sem histórico direto (ex.: "Lançamento Coleção Primavera — Novos SKUs sem histórico direto") geram alerta e a recomendação de investigar; nunca fator.
- Faixa de segurança: limitar o fator a um intervalo configurável em `config/event_factors.json` (por exemplo 0,5 a 2,0) e registrar quando houver corte.

### Evitar dupla contagem

O modelo `seasonal_naive_12` já repete o mesmo mês do ano anterior, ou seja, já embute a sazonalidade. Portanto:

- Modelo escolhido = `seasonal_naive_12`: mostrar o alerta, com o texto "a previsão já incorpora a sazonalidade do ano anterior", **sem** cenário.
- Modelo escolhido = `moving_average_3`: mostrar alerta e cenário com fator.

Este é o ponto mais importante do desenho; sem ele o fator inflaria a previsão.

### Entregáveis

- `src/caderno_inteligente/events.py` (parse das datas `dd/mm/aaaa`, expansão de famílias, sobreposição com horizonte e lead time, fator histórico).
- `config/event_factors.json` (limites do fator, janela de segurança).
- Endpoint aditivo `GET /api/events` e campos opcionais `event_alerts` e `event_scenario` no detalhe do SKU e na página Previsão.
- Frontend: faixa "Eventos próximos" no Início (3 itens no máximo, na linha da V2 enxuta), selo de evento por SKU na Previsão e bloco "Cenário com evento" no detalhe do SKU, com selo **Estimativa** e a fórmula.
- Reflexo operacional informativo: no detalhe do SKU, "quantidade com cenário de evento" ao lado da quantidade oficial. A quantidade oficial **não muda**.
- `docs/etapa-11-eventos-sazonalidade.md`.

### Testes e aceite

- Casos congelados: evento de uma família, evento "Todas", SKU de família fora do evento, evento fora do horizonte, evento já terminado, família com histórico curto (só alerta) e SKU com `seasonal_naive_12` (sem cenário).
- Teste de regressão: saídas de `/api/forecasts`, `/api/prioritization` e score idênticos antes e depois.
- Aceite: nenhum fator aparece sem amostra declarada; nenhum cenário aparece para SKU cujo modelo já é sazonal.

## 7. Etapa 12 — Visão dos canais diretos

**Resposta ao PDF:** "Parceiro/Canal", "dados de canais diretos" e "padrões por canal", usando a melhor visibilidade da base.

### Escopo

Aba **Canais diretos** em Parceiros (`/parceiros?aba=diretos`), mais o detalhe `/canais/:canal`, para E-commerce, Marketplace e Loja própria. Fonte: `Vendas_24m`, `Parceiros_Canais`, `Carteira_Pedidos` e `Produtos`.

Conteúdo por canal:

- faturamento e unidades dos últimos 24 meses (**observado**), participação no total e tendência (comparação de 3 meses contra os 3 anteriores, mesma regra de `_trend`);
- ranking de SKUs do canal (curva de contribuição) e SKUs que cresceram ou caíram;
- recorrência: meses ativos por SKU e SKUs que deixaram de vender no canal (candidatos a **reativação**);
- mix: quantos dos 50 SKUs vendem no canal e quais não vendem (candidatos a **ampliar mix**);
- carteira de pedidos aberta do canal, sem alocação de produção;
- comparação direto × parceiros por SKU, só como contexto.

### Cuidados com a base

- **Sem estoque por canal.** `Estoque_Atual` só tem `CD Central`. Não inventar estoque de e-commerce ou de loja. A tela deve dizer "estoque do CD, não do canal".
- **Cobertura "Completo" em `Parceiros_Canais` não é sustentada por `Sell_Out`** (nenhuma linha dos canais diretos). Declarar que a visibilidade vem de faturamento e adicionar um aviso em **Qualidade**.
- **Inconsistência Sell-In × Vendas_24m dos KAs** (seção 3): adicionar como achado de qualidade, sem tentar reconciliar. Não afeta os cálculos existentes.
- Dizer na tela e no roteiro que os canais diretos concentram 68% do faturamento da base.

### Entregáveis

- `src/caderno_inteligente/direct_channels.py` e rotas `GET /api/direct-channels` e `GET /api/direct-channels/{canal}` em `backend/`.
- Frontend: aba, detalhe do canal, filtros por URL (`canal`, `familia`) e entradas em `contract-keys.json`.
- Dois achados novos no relatório de qualidade (cobertura declarada × observada; Sell-In × faturamento dos KAs).
- `docs/etapa-12-canais-diretos.md`.

### Testes e aceite

- Teste de agregação por canal (soma dos três canais + KAs = total de `Vendas_24m`), de SKU sem venda no canal (aparece como não vendido, nunca zero de venda) e de ausência de estoque por canal.
- Aceite: o usuário vê, no mínimo, produto, canal, faturamento observado, tendência, carteira e sugestão para cada canal direto, com selo de natureza dos dados.

## 8. Etapa 13 — Rótulos de ação que faltam (camada aditiva)

**Resposta ao PDF:** ações "Priorizar produção, Repor, Priorizar parceiro, Ampliar mix, Recomendar recompra, Monitorar, Investigar, Sem ação necessária".

### Estado atual × meta

| Ação do PDF | Hoje | Fonte do sinal (já existente ou das etapas anteriores) |
|---|---|---|
| Produzir | existe (`produzir`, `produzir_validar_capacidade`) | previsão, estoque, carteira |
| Repor | existe como `avaliar_reposicao` (parceiro) | `REPOSITION_OPPORTUNITY` |
| Monitorar | existe (`monitorar_excesso`, `monitorar_estoque`) | excesso |
| Investigar | existe | dados insuficientes, divergência |
| Sem ação necessária | existe | — |
| **Priorizar produção** | falta | posição no ranking oficial + ação `produzir*` + evento próximo (Etapa 11) |
| **Priorizar parceiro** | falta | parceiros com maior número de pares `REPOSITION_OPPORTUNITY` para SKUs de alta prioridade |
| **Ampliar mix** | falta | SKU que vende bem no canal/parceiro ou na família, e o parceiro não vende; só quando houver dado (Etapas 12 e sell-out) |
| **Recomendar recompra** | falta | par parceiro–SKU com intervalo entre envios acima do padrão do próprio par e sell-out recente positivo |
| **Reativar** | falta | SKU/canal que vendia e parou (Etapa 12) |

### Regras de desenho

- **Rótulo derivado, não novo motor.** Um módulo `action_labels.py` apenas lê sinais já calculados (`signals`, `action`, ranking, alertas de evento) e emite um segundo campo `challenge_action` com `label`, `signals_used`, `evidence` e `limitations`. O campo `action` existente continua igual.
- **Precedência documentada**, em tabela, no `docs/commercial-rules.md` (dado insuficiente vence tudo; depois risco de ruptura; depois excesso; depois oportunidade).
- **Limiares em configuração** (`config/commercial_thresholds.json`, chave nova `challenge_actions`), com validação no carregamento, como já ocorre nos demais limiares.
- **Sem dado, sem rótulo:** "Ampliar mix" e "Recomendar recompra" só saem para pares com sell-out observado suficiente; caso contrário, "Investigar" com o motivo. Nada é inferido para parceiros sem sell-out (5 de 8 canais).
- Ações de recompra e mix em B2B exigem a série de sell-in por parceiro (apenas 12 meses e 10 SKUs por KA); declarar essa limitação junto do rótulo.

### Entregáveis

- `src/caderno_inteligente/action_labels.py`; campo opcional `challenge_action` em `/api/partners/...`, `/api/commercial-recommendations` e `/api/forecasts`.
- Frontend: filtro por rótulo em Parceiros e em Previsão, coluna "Ação do desafio" ao lado da ação atual, e legenda com a definição de cada rótulo no Guia.
- Registro de decisão: o campo do rótulo entra no feedback como dado opcional (sem migração destrutiva; seguir o padrão da migração 002).
- `docs/etapa-13-rotulos-de-acao.md`.

### Testes e aceite

- Tabela-verdade: um teste por rótulo e um por conflito de precedência; teste de que o campo `action` original e o score não mudam.
- Aceite: os nove rótulos do PDF podem aparecer na solução, cada um com evidências e limitações; cada um tem pelo menos um caso congelado em `config/validation_center.json`.

## 9. Sequência, esforço e dependências

| Ordem | Etapa | Esforço | Depende de | Risco |
|---|---|---|---|---|
| 0 | Linha de base e decisões | 0,5 dia | — | baixo |
| 1 | Etapa 10 — Faturamento | 1 a 1,5 dia | — | baixo (cálculo simples) |
| 2 | Etapa 11 — Eventos | 1,5 a 2 dias | 10 (reaproveita o selo de estimativa) | médio (dupla contagem; amostra de 1 ano) |
| 3 | Etapa 12 — Canais diretos | 2 dias | — | médio (inconsistências de abas) |
| 4 | Etapa 13 — Rótulos de ação | 1,5 dia | 11 e 12 (fornecem sinais de evento e reativação) | médio (precedência e escopo) |
| 5 | Validação e documentação | 1 dia | todas | baixo |

Total estimado: 7 a 8 dias úteis. As etapas 10 e 12 podem andar em paralelo. Se o prazo apertar, o corte recomendado é: 10, 11 e 13 sem os rótulos "Ampliar mix" e "Recomendar recompra", deixando a Etapa 12 enxuta (só visão de faturamento por canal).

## 10. Validação e demonstração

- **Regressão geral:** `pytest` e `npm run check` verdes; snapshots do ranking, do score e da previsão em unidades inalterados.
- **Casos congelados novos** em `config/validation_center.json`: pelo menos um por etapa, com resultado esperado e justificativa.
- **Roteiro de demonstração (`docs/roteiro-demonstracao.md`)**: acrescentar a história "Black Friday chegando": evento no Início → SKU de família afetada → faturamento estimado com selo → cenário com evento → canal direto que mais vende o SKU → rótulo "Priorizar produção" com evidências.
- **Relatório da Semana 4:** registrar os números datados e o hash da planilha, e não afirmar ganho de acurácia nem de tempo antes da amostra mínima já definida.
- **Teste moderado com 3 usuários** (pendente da V2): incluir uma tarefa por etapa nova.

## 11. Fora do escopo (declarar na defesa)

- Previsão de faturamento por parceiro, canal ou região (a base só sustenta previsão global por SKU).
- Estoque por canal e por parceiro além do estimado já informado no `Sell_Out`.
- Otimização de produção, vínculo pedido–ordem e alocação de capacidade por SKU (a base não contém o vínculo).
- Elasticidade de preço, desconto de campanha e reajustes futuros.
- Retreinamento automático por feedback.

## 12. Matriz de aderência após o plano

| Exigência do PDF | Situação atual | Após o plano |
|---|---|---|
| Prever demanda | atendida | atendida |
| Prever faturamento | **não atendida** | atendida (estimativa rotulada) |
| Sazonalidade e calendário | **parcial** (só `seasonal_naive_12`) | atendida (alerta e cenário explícito) |
| Padrões por canal | **não atendida** | atendida para canais diretos |
| Padrões por região | parcial (filtro) | parcial (continua; registrar como limitação) |
| Ações do PDF | parcial (5 de 9) | atendida (9 de 9, com restrição de dados) |
| Viabilidade operacional | parcial | parcial (capacidade continua como contexto; declarado) |
| Observado × estimado | atendida | atendida, estendida aos novos campos |
