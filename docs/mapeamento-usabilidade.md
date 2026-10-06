# Mapeamento de usabilidade — Caderno Inteligente (Fase 1)

> **Status:** mapeamento sem alteração de código, testes, estilos ou configuração. Único arquivo novo: este documento e as capturas em [`docs/mapeamento-usabilidade/`](mapeamento-usabilidade/).
> **Data da medição:** 05/10/2026 (API local, planilha de demonstração SHA-256 `03fa0ed4…803f`, referência de vendas 08/2026).
> **Como foi feito:** leitura de `README.md`, `docs/architecture.md`, `docs/api.md`, `docs/roteiro-demonstracao.md` e de todo o código de `frontend/src`; API (`uvicorn`) e frontend (`npm run dev`) rodando localmente; Chrome headless controlado por script (protocolo DevTools) abriu cada rota em **1440×900** e **375×812**, mediu a primeira dobra e salvou as capturas. Só foram feitas leituras (`GET`). **Nenhum formulário foi enviado e nenhum dado foi gravado.**

## 1. Resumo executivo

O produto está correto e honesto com os limites dos dados, mas a interface responde mal às quatro perguntas de quem usa. Os cinco problemas mais graves:

1. **"Motivo principal" não é o principal (crítico).** A API devolve os sinais em ordem alfabética de código e a tela exibe o primeiro. Em **27 de 41 SKUs** o motivo exibido não é o de maior peso; em **13 de 41** é "Baixa visibilidade de sell-out" (o de menor peso). No CI-0041 aparece "Capacidade pressionada" (peso 5) e o sinal crítico "Abaixo do estoque de segurança" (peso 10) fica em 5º (`components.tsx:182`, `OverviewPage.tsx:15`).
2. **A resposta de "preciso produzir? quanto?" fica fora da tela (crítico).** Em `/previsoes` a tabela tem 11 colunas e 1.428 px num contêiner de 1.070 px: "Quantidade" fica cortada e "Capacidade" e "Ver detalhes" só aparecem com rolagem horizontal. Em `/skus/:sku` a ação sugerida começa 1,7 tela abaixo da dobra no desktop e 2,7 no celular. No celular, `/previsoes` tem 18.727 px de rolagem (50 cartões).
3. **O mesmo aviso é repetido de 5 a 7 vezes por tela** (9 telas) e há **três "confianças" e duas "previsões" com nomes quase iguais** na mesma página, sem rótulo que as distinga (`/previsoes`, `/skus/:sku`, `/`).
4. **Linguagem técnica e texto pequeno.** WAPE, baseline, holdout, backtest, sell-in/out e lead time aparecem sem tradução; só 4 tooltips existem. **100 das 197 declarações de `font-size` do `App.css` ficam abaixo de 12 px** (67 em 10,5 px ou menos); no detalhe do SKU os rótulos das métricas renderizam a 8,5 px.
5. **Comercial sem caminho curto e sem próximo passo.** As 12 oportunidades de reposição (5 parceiros) só aparecem abrindo cada parceiro (7 cliques e rolagem horizontal; a coluna da ação comercial é a última e fica cortada em 1440 px). O detalhe do SKU não tem "Registrar decisão"; a decisão exige 4 a 7 cliques em outra página e o SKU deve ser escolhido de novo.

Também relevantes: a Validação tem 5.092 px (10.409 px no celular) e exige rolar 4,3 telas até "Comportamento seguro"; o plano cita 13 itens de menu e 12/15 colunas, mas o **menu real tem 11 itens** e medi 11 colunas em Previsões e 8 na matriz do parceiro (seção 5, nota de método).

## 2. Inventário do frontend (A)

### 2.0 Elementos comuns a todas as rotas

| Elemento | Onde no código | Conteúdo | Observações |
|---|---|---|---|
| Link "Pular para o conteúdo" | `App.tsx:85` | Foco no título | Bom para teclado |
| Menu lateral | `components.tsx:47-96` | **11 itens**, cada um com ícone, rótulo e descrição (10,5 px): Guia de uso, Visão geral, Prioridades, Previsão e recomendações, Casos, Qualidade, Visibilidade B2B2C, Cenários, Execuções, Decisões, Validação | Em 1440×900 ocupa a altura toda; "Previsão e recomendações" quebra em 3 linhas. No celular vira gaveta (botão ☰) |
| Nota do menu | `components.tsx:93` | "Sistema de apoio à decisão · Não libera produção automaticamente" (10,5 px) | Aviso permanente em todas as páginas |
| Barra superior | `components.tsx:98-110` | Kicker (descrição da página, 10,5 px), `h1` com o nome da página, estado ("Dados carregados"), "Última carga: dd/mm/aaaa, hh:mm:ss (Brasília)" (11 px, tooltip), botão "Atualizar" | A hora é do navegador, não da planilha. Nas páginas estáticas mostra "Conteúdo de orientação / Não consulta a API" |
| Cabeçalho da página | `components.tsx:135` (`PageIntro`) | Eyebrow (10,5 px, caixa alta) + `h2` + descrição + ação | **Segundo título** abaixo do `h1` da barra superior (ex.: "Prioridades" e "Prioridades explicáveis") |
| Faixa de modo | `components.tsx:123` | "Demonstração" e/ou "Somente leitura" | Não aparece no ambiente local (`demo_mode=false`, `write_enabled=true`); **não capturado** |
| Estados | `components.tsx:190-200` | Carregando (skeleton), erro com "Tentar novamente", vazio | Estados de erro não capturados (API estava no ar) |

Convenções das tabelas abaixo: **Origem** = `endpoint.campo`. "Contexto" indica se há referência de comparação junto ao número.

Capturas: `mapeamento-usabilidade/<rota>-1440x900.png` e `…-375x812.png` (primeira dobra de cada rota; nomes na seção 2.15).

### 2.1 `/guia` — Guia de uso (`pages/GuidePage.tsx`)

- **Objetivo / pergunta:** orientar o primeiro uso. "Como uso isto e o que posso (ou não) concluir?"
- **Público:** quem chega pela primeira vez (PCP, Comercial) e quem apresenta.
- **Não consulta a API** (único conteúdo que funciona offline).

Elementos, de cima para baixo:

1. Cabeçalho "Entenda o Caderno Inteligente em poucos minutos" + botão "Começar pela visão geral" (L44).
2. Painel escuro "Do sinal à decisão, em cinco passos" com 5 passos numerados (L45-54; texto de apoio 9,5–11 px).
3. "O que há em cada página": 10 cartões (eyebrow 8,5 px, título, descrição, link "Abrir página") (L55-57). Repete o menu.
4. "Entenda os indicadores": **glossário de 9 termos** (L19-29, L58): Pontuação de atenção, Confiança, Data crítica, Lacuna operacional, Recomendação operacional, Recomendação comercial, "WAPE e baseline" (juntos), Dado ausente, Nível B2B2C.
5. "O que este protótipo não faz": 5 itens (L60).
6. "Roteiro de demonstração · 5 minutos": 5 itens com tempo; cita "22 h semanais" (valor fixo no código, não vem da API) (L61).
7. "Dúvidas frequentes": 8 perguntas recolhidas (L63).
8. Faixa final "Pronto para explorar?" + botão "Abrir visão geral" (L64).

| Contagem | 1440×900 | 375×812 |
|---|---|---|
| Números na primeira dobra | 7 tokens (5 são os números dos passos) | 3 |
| Avisos | 1 (bloco "O que este protótipo não faz") + nota do menu | idem |
| Tabelas | 0 | 0 |

Problemas observados: "Nível B2B2C" é explicado, mas **nenhuma tela mostra esse nível** (`partnerLevelTone` em `shared.ts:59` não é usado); "sell-in/sell-out", "lead time", "holdout", "backtest" e "MAPE" não estão no glossário; 765 palavras.

### 2.2 `/` — Visão geral (`pages/OverviewPage.tsx`)

- **Objetivo / pergunta:** "O que exige atenção agora e por quê?"
- **Público:** PCP (principal); gestão/apresentação.
- **Endpoints:** `GET /api/overview`, `GET /api/priorities`, `GET /api/data-quality`.

Elementos, de cima para baixo:

1. Cabeçalho "Centro de decisão — Da atenção à decisão humana" (L11).
2. Seção "01 · O que exige atenção" + botão "Ver prioridades" (L13).
3. **Cartão "Primeiro da fila · prioridade #1"** (L14-17): SKU e produto; badges com **todos os sinais** (5 no CI-0041) mais "Confiança baixa"; uma frase (`reasons[0].description`); botão "Abrir evidências de CI-0041".
4. Quatro cartões (L19-22):

| Número | Significa | Unidade | Origem | Contexto |
|---|---|---|---|---|
| 41 SKUs priorizados | SKUs com ao menos um sinal | SKUs | `overview.prioritized` | "de 50 SKUs monitorados" (`total_skus`) |
| 16 SKUs com risco de ruptura | SKUs únicos abaixo do lead time ou da segurança | SKUs | `overview.rupture_sku_count` | "15 abaixo do lead time · 13 abaixo da segurança" (15 + 13 ≠ 16: há SKUs nos dois; não é explicado) |
| 12 Pedidos sem OP | Pedidos em carteira sem ordem de produção | pedidos (rótulo) | `overview.order_without_production` | "validar o atendimento operacional" (sem denominador) |
| 20 Baixa confiança | SKUs priorizados com confiança baixa | SKUs | `overview.low_confidence` | "sell-out não observado" (sem "de 41") |

5. "Fila de atenção" (L24): tabela compacta, 5 linhas, **7 colunas** (Prioridade, SKU/Produto, Família, Motivo principal, Score ⓘ, Confiança ⓘ, abrir) + selo "Ranking oficial" + legenda "Prioridade de análise · não é autorização de produção".
6. Seção "02 · Ações sugeridas" (L27): aviso `DecisionBoundary` (L28) e 4 atalhos (L29-34): Consultar previsão e ação, Verificar parceiros, Validar os dados, Registrar decisão humana (cada um com título, subtítulo e nota em 3 níveis de texto).
7. Seção "03 · Qualidade da decisão" (L37): três cartões (L38-42):

| Número | Significa | Origem | Contexto |
|---|---|---|---|
| 20% Cobertura de sell-out | Pares parceiro–SKU com sell-out observado | `data-quality.sell_out_coverage.coverage` | "50 de 250 pares observados" |
| 0 Decisões registradas | Feedbacks salvos | `overview.decision_count` | nenhum |
| 0 Influenciadas por dado parceiro | Decisões com efeito "aumentou confiança" ou "alterou decisão" | `overview.partner_data_influenced_decision_count` | nenhum |

8. Aviso "Limite da evidência observada" (L43, tom de alerta quando a cobertura < 100%).
9. "Sinais que compõem a análise": 7 barras (L44) com `overview.risk_distribution` (20, 20, 15, 13, 12, 6, 6).

| Contagem | 1440×900 | 375×812 |
|---|---|---|
| Números na primeira dobra | 11 tokens (9 de negócio: 41, 50, 16, 15, 13, 12, 20, #1, 33; mais "01" e "1" de rótulos) | 2 |
| Avisos | 2 (`DecisionBoundary`, "Limite da evidência observada") + nota do menu; ambos abaixo da dobra | idem |
| Colunas da tabela | 7 | 7 (660 px em contêiner de 343 px: rolagem horizontal) |
| Altura | 2.292 px | 3.582 px |

Observação: no celular o cartão do primeiro da fila começa em y=469 e os quatro cartões de números ficam abaixo da dobra.

### 2.3 `/prioridades` — Prioridades (`pages/PrioritiesPage.tsx`)

- **Objetivo / pergunta:** "Qual é a ordem completa de análise e por que cada SKU está nela?"
- **Público:** PCP.
- **Endpoint:** `GET /api/priorities` (filtros aplicados no cliente; URL guarda `busca`, `familia`, `confianca`).

Elementos:

1. Cabeçalho "Prioridades explicáveis" (L25).
2. Aviso `DecisionBoundary` "Prioridade de análise não é ordem de produção" (L26) — 4 linhas no celular.
3. Filtros (L27-32): Buscar, Família, Confiança, contador "41 de 41 SKUs", "Limpar filtros".
4. "Ranking oficial" (L33) + `PriorityTable` (`components.tsx:176-188`): legenda repetindo o aviso e **9 colunas**:

| Coluna | Significa | Origem | Observações |
|---|---|---|---|
| Prioridade | Posição no ranking (1–41) | `priorities[].priority` | Sem unidade; bolha azul nas 3 primeiras |
| SKU / Produto | Código e nome | `sku`, `product` | |
| Família | | `family` | |
| Motivo principal | Primeiro sinal da lista + "+N sinais" | `reasons[0]` | **Primeiro em ordem alfabética de código, não o mais grave** (seção 5, P01) |
| Data crítica | Primeira data prometida ou conclusão prevista + origem | `critical_date`, `critical_date_reason` | "Sem data operacional" quando ausente |
| Lacuna operacional | Carteira − estoque − produção aberta, se positiva | `operational_gap_quantity` | "0" em **36 de 41** linhas; legenda "Quantidade para análise" (sem unidade) |
| Score ⓘ | Soma dos pesos dos sinais | `attention_score` | Sem escala nem máximo; tooltip |
| Confiança ⓘ | Qualidade da evidência (baixa/média/alta) | `confidence` | 20 baixas e 21 médias |
| (abrir) | Botão › | | A linha inteira também abre o SKU |

| Contagem | 1440×900 | 375×812 |
|---|---|---|
| Números na primeira dobra | 24 tokens (contador + 5 linhas × posição, "+N sinais", lacuna, score) | 2 (a tabela fica abaixo da dobra) |
| Avisos | 1 (+ legenda da tabela + nota do menu) | idem |
| Colunas | 9 | 9 (781 px em contêiner de 343 px) |
| Altura | 3.157 px | 3.743 px |

Defeito visual: o ícone de busca sobrepõe o placeholder "Buscar SKU ou produto" (captura `prioridades-1440x900.png`).

### 2.4 `/previsoes` — Previsão e recomendações (`pages/ForecastsPage.tsx`)

- **Objetivo / pergunta:** "Preciso produzir este SKU? Quanto?" para todos os 50 SKUs.
- **Público:** PCP.
- **Endpoint:** `GET /api/forecasts` (filtros no cliente; URL guarda `busca`, `familia`, `acao`, `confianca`, `tendencia`, `atencao`, `ordem`).

Elementos:

1. Cabeçalho "Previsão e recomendações" (L72).
2. Aviso `DecisionBoundary` (L74) **e** aviso "Revisão humana obrigatória" (L75): juntos ocupam ~190 px da dobra.
3. Quatro cartões (L77-80):

| Número | Significa | Origem | Contexto |
|---|---|---|---|
| 50 SKUs previstos | `forecast.status = ok` | `forecasts[].forecast.status` | "50 SKUs analisados" (redundante: todos) |
| 14 Produção sugerida | ação "Produzir" (12) + "Produzir após validar capacidade" (2) | `operational_recommendation.action` | "itens que pedem avaliação" |
| 6 Validar capacidade | SKUs com família pressionada, **mesmo os "Sem ação necessária"** | `operational_recommendation.capacity_status` | "contexto familiar pressionado" |
| 0 Investigar dados | sem previsão ou ação "investigar dados" | `forecast.status`, `action` | "sem previsão confiável" |

4. Filtros (L82-91): Buscar, Família, Ação (5 opções), Confiança, Tendência (4), Ordenar por (4), caixa "Somente itens com atenção", contador "50 de 50 SKUs", "Limpar filtros" → **7 controles**.
5. "Visão operacional consolidada" + selo "Sugestões para revisão" (L92). Tabela (L94) com **11 colunas** (10 com texto visível + "Detalhes" só para leitor de tela):

| Coluna | Significa | Unidade | Origem |
|---|---|---|---|
| SKU | código + produto · família | — | `sku`, `product`, `family` |
| Prioridade | #posição ou "Fora do ranking" (9 SKUs) | — | `priority` |
| Tendência | crescente/estável/decrescente | — | `forecast.trend` (sem o % de variação) |
| Próximo mês | demanda prevista | unidades (sem unidade no cabeçalho) | `forecast.forecast_next_month` |
| 3 meses | demanda prevista | idem | `forecast.forecast_total_3m` |
| Modelo / WAPE ⓘ | modelo escolhido + erro no teste de 3 meses | % (0–1 formatado, 1 casa) | `forecast.model_label`, `backtest_wape` |
| Confiança | **confiança da previsão** (alta nos 50 SKUs) | — | `forecast.forecast_confidence` |
| Ação operacional sugerida | ação | — | `operational_recommendation.action_label` |
| Quantidade | quantidade sugerida + "Lote: n" | unidades | `suggested_quantity`, `minimum_lot` |
| Capacidade | "Validar capacidade" ou "Sem garantia individual" | — | `capacity_status` |
| Detalhes | botão "Ver detalhes" | — | abre `/skus/:sku` |

6. No celular a tabela some e aparecem **50 cartões** (L97) com 3 badges e 6 pares rótulo/valor.

| Contagem | 1440×900 | 375×812 |
|---|---|---|
| Números na primeira dobra | 15 tokens | 5 |
| Avisos | 2 + nota do menu | 2 |
| Colunas | 11 (tabela 1.428 px em contêiner de 1.070 px: "Quantidade" começa em x=1298 e termina em x=1397, com o contêiner acabando em x=1387; "Capacidade" e "Detalhes" ficam fora da tela) | cartões |
| Altura | 3.744 px | **18.727 px** |

### 2.5 `/skus/:sku` — Detalhe do SKU (`pages/SkuDetailPage.tsx`)

- **Objetivo / pergunta:** "Por que este SKU está na fila e devo produzir? Quanto?" (evidências completas).
- **Público:** PCP; também Comercial (contexto dos parceiros).
- **Endpoints:** `GET /api/priorities/{sku}` e `GET /api/commercial-recommendations?sku=`.
- Capturas: `sku-ci-0041-*` (prioridade #1, "Sem ação necessária") e `sku-ci-0014-*` ("Produzir após validar capacidade", 400 un.).

Elementos, de cima para baixo (valores do CI-0014 entre parênteses):

1. Cabeçalho: eyebrow "Prioridade #15", título do SKU, "produto · família", botão **"Voltar"** (único botão da página) (L38).
2. Aviso `DecisionBoundary` (L40).
3. (Só se a ação for "sem ação necessária") aviso "Sem ação necessária de produção não significa sem risco" (L41).
4. Resumo (L43): Score (14), Confiança (média — **do ranking**), Família.
5. "Demanda e atendimento" (L44-48) + selo do escopo ("SKU global"): Estoque atual (1.490), Carteira (1.327), Produção aberta (0), Estoque projetado, Lacuna operacional (+ "Quantidade para análise"), Cobertura em dias (+ "Lead time: n dias"); datas "Primeira data prometida" e "Primeira conclusão prevista"; "Intervalo de risco entre datas" (dias). Valores: `indicator.*`.
6. "Canal e confiança" (L49-54): Sell-in acumulado (3.868), Sell-out acumulado (3.737), Diferença observada (131), Parceiros com sell-out (2), **Forecast disponível (2.788)** (`indicator.forecast_quantity`, que é a Forecast_Comercial da planilha); caixa "Por que esta confiança?"; caixa "Dados ausentes" (ou "Dados principais disponíveis").
7. "Previsão e ação operacional sugerida" (L55-64), com selo de confiança (**da recomendação**): Tendência (estável, −2,2%), Modelo selecionado (+ "24 meses analisados"), "Erro no backtest" (7,4%, "WAPE nos 3 meses reservados"), Próximo mês (1.246,3), **Próximos 3 meses (3.810,5)**, Quantidade sugerida (400, "próximo mês"); 3 meses previstos; **cartão da ação** (selo "Validar capacidade", texto da justificativa e linha de cálculo "Demanda a cobrir 1.327 + Segurança 433,6 − Estoque 1.490 − Produção aberta 0"); caixa "Revisão humana obrigatória"; texto de limitação da previsão.
8. "Riscos e evidências" (L65): um cartão por sinal (severidade, nome, descrição, **valores usados**, "Origem: planilha.coluna").
9. "Limitação conhecida" (L66).
10. "Contexto dos parceiros" (`PartnerSkuContext.tsx`): texto introdutório, aviso "Recomendação comercial, não operacional" (4 frases), "Matriz parceiro–SKU" (8 colunas, ver 2.8) e N blocos "Evidências de KA-xx · SKU", mais "Método, natureza dos campos e limites configurados".

| Contagem | 1440×900 | 375×812 |
|---|---|---|
| Números na primeira dobra | 14 (CI-0041 e CI-0014) | 2 (CI-0041) / 4 (CI-0014) |
| Avisos / caixas de ressalva | **7** (CI-0041) e **6** (CI-0014) | idem |
| Início da ação sugerida | y=1.665 / y=1.523 (≈1,7–1,9 tela) | y=2.423 / y=2.204 (≈2,7–3,0 telas) |
| Altura | 3.816 / 3.221 px | 5.329 / 4.467 px |
| Tabelas | matriz 8 colunas + 1 de origem mensal (5 col.) por parceiro, dentro de `<details>` | idem |

Fatos relevantes: **nenhum botão ou link leva a "Registrar decisão" ou "Criar caso"** (verificado: 0 links para `/decisoes` e `/casos`). O `score_contributions` (peso de cada sinal) vem na resposta, mas **não é exibido**; o score aparece sem decomposição. Em "Riscos e evidências" os campos aparecem com o nome técnico traduzido por troca de `_` por espaço (ex.: "average occupation 0.9325", "delay days 25", "sell out visibility não disponível"; `SkuDetailPage.tsx:65`).

### 2.6 `/parceiros` — Parceiros e canais (`pages/B2BPage.tsx`)

- **Objetivo / pergunta:** "Qual parceiro ou canal tem oportunidade de reposição e quanto sabemos dele?"
- **Público:** Comercial.
- **Endpoint:** `GET /api/partners` (URL: `regiao`, `canal`, `ordem`; padrão **ordem por nome**).
- Observação: o item do menu chama-se "Visibilidade B2B2C"; o título da página é "Parceiros e canais".

Elementos:

1. Cabeçalho "Parceiros e canais" + "Referência mensal da base: 08/2026" (L21).
2. Aviso "Visibilidade medida, não presumida" (L23).
3. Quatro cartões (L24):

| Número | Significa | Origem | Contexto |
|---|---|---|---|
| 8 Parceiros neste filtro | | `partners.items` | "de 8 cadastrados" |
| 50 Pares com sell-out | pares parceiro–SKU observados | soma de `items.observed_skus` | "pares observados, não SKUs distintos" |
| 12 Avaliar reposição | sugestões comerciais | soma de `action_counts.avaliar_reposicao` | "revisão humana" |
| 45 Dados insuficientes | vínculos sem base para recomendar | soma de `quality_counts.insufficient` | — |

4. Filtros: Região, Canal, Ordenar (Nome, Cobertura observada, Sugestões de reposição) (L25).
5. Cartões de parceiro (L28), 8 no total, cada um com: nome e "código · tipo" (**colados**, sem espaço: "Casa das IdeiasKA-05 · Distribuidor"), selo "NN% observado", região · canal, barra de progresso, "observados/total" ("10/50 SKUs do catálogo observados"), "vínculos reais com SKU", "Último sell-out: 08/2026", "N sugestões de reposição · N dados antigos/descontínuos", botão "Abrir parceiro e evidências". Textos de 9–9,5 px.

| Contagem | 1440×900 | 375×812 |
|---|---|---|
| Números na primeira dobra | 29 | 7 |
| Avisos | 1 + nota do menu | 1 |
| Altura | 1.583 px | 3.390 px |

Fatos: cinco parceiros mostram "20% observado" e três mostram "0%": o selo não diferencia. A oportunidade (12 no total, 5 parceiros) só aparece no rodapé pequeno do cartão e na ordenação opcional.

### 2.7 `/parceiros/:codigo` — Detalhe do parceiro (`pages/PartnerDetailPage.tsx`)

- **Objetivo / pergunta:** "Quais SKUs deste parceiro pedem reposição, investigação ou dado novo, e qual a evidência?"
- **Público:** Comercial.
- **Endpoints:** `GET /api/partners/{codigo}` e `GET /api/partners/{codigo}/skus` (50 por página; URL: `sku`, `acao`, `qualidade`, `offset`).

Elementos:

1. Cabeçalho (nome, "código · região · canal") + "Voltar aos parceiros" (L28).
2. Quatro cartões (L30): Cobertura observada 20% ("10 de 50 SKUs do catálogo"); Último sell-out 08/2026 ("referência: 08/2026"); Vínculos reais 14 ("sell-in/out ou carteira, sem produto cartesiano"); Dados antigos/descontínuos 0.
3. Filtros (L31): SKU exato + botão "Filtrar SKU", Ação comercial (5), Qualidade (3), "Limpar filtros".
4. `CommercialMatrix` (ver 2.8).
5. Paginação "1–14 de 14", Anterior/Próxima (L33).
6. Aviso "Decisões influenciadas por este parceiro: atribuição indisponível" (L34), no **final** da página; o texto termina com "…nesta etapa".

| Contagem | 1440×900 | 375×812 |
|---|---|---|
| Números na primeira dobra | 69 (matriz de 14 linhas começa na dobra) | 9 |
| Avisos | 2 | 2 |
| Altura | 3.198 px | 3.950 px |

### 2.8 Componente compartilhado: matriz parceiro–SKU (`components/CommercialMatrix.tsx`, usado em `/parceiros/:codigo` e `/skus/:sku`)

1. Aviso "Recomendação comercial, não operacional" (L12): 4 frases (limitação da API + diferença só em meses comparáveis + referência).
2. "Matriz parceiro–SKU" (L13): subtítulo "14 de 14 vínculos neste filtro…". Tabela de **8 colunas** (L14), 1.180 px mínimos:

| Coluna | Significa | Unidade | Origem |
|---|---|---|---|
| Parceiro / SKU | links para parceiro e SKU + produto | — | `partner_name`, `sku`, `product` |
| Sell-in recente | enviado ao parceiro nos meses listados | unidades | `sell_in_recent`, `sell_in_months` |
| Sell-out recente | vendido pelo parceiro | unidades | `sell_out_recent`, `sell_out_months` |
| Diferença comparável | sell-in − sell-out só nos meses em comum (pode ser negativa: −1) | unidades | `comparable_difference` |
| Estoque estimado | estoque do parceiro, estimado e não auditado | unidades | `estimated_stock`, `stock_month` |
| Cobertura estimada | estoque ÷ (giro mensal ÷ 30) | dias (1 casa) | `coverage_days` |
| Carteira | pedidos em carteira + nº de pedidos | unidades | `backlog_quantity`, `backlog_order_count` |
| Qualidade / ação comercial | selo de qualidade + **ação sugerida** | — | `data_quality`, `action_label` |

   **A ação (a resposta) é a última coluna: em 1440×900 ela vai de x=1296 a x=1497 e o contêiner termina em x=1387.**
3. Um `<details>` **por vínculo** (L23-34), abaixo da tabela, fechado: "Evidências de KA-01 · CI-0011 — Avaliar reposição". Ao abrir: escopo, sinais, atualidade, natureza do sell-out, comparação (sell-in − sell-out = diferença), fórmula da cobertura, razão da recomendação (texto da API), tabela mensal de 5 colunas (Mês, Enviado, Vendido, Estoque estimado, Natureza declarada; 12 linhas) e pedidos da carteira.
4. `<details>` "Método, natureza dos campos e limites configurados" (L35): 19 campos e 9 limiares (nomes técnicos em inglês, ex.: `reposition_coverage_days`).

### 2.9 `/casos` — Casos (`pages/CasesPage.tsx`)

- **Objetivo / pergunta:** "O que está em acompanhamento e quem cuida?"
- **Público:** PCP/gestão.
- **Endpoints:** `GET /api/cases`, `GET /api/priorities`, `GET /api/config`; `POST /api/cases` (não executado).

Elementos: cabeçalho "Casos operacionais" + botão "+ Novo caso" (rola até o formulário na mesma dobra) (L26); três contadores "2 casos abertos / 1 em investigação / 0 concluídos" (L27, calculados no cliente); "Fila de casos": tabela de **5 colunas** (SKU + #id, Status, Responsável, Prazo, Atualizado) (L28); "Criar caso": SKU (só dos 41 priorizados), Responsável, Status (5 opções), Prazo, botão "Criar caso" (L29).

| Contagem | 1440×900 | 375×812 |
|---|---|---|
| Números na primeira dobra | 11 | 11 |
| Avisos | 0 | 0 |
| Altura | 900 px | 1.312 px |

Fatos: **não existe ação para atualizar um caso** (`api.updateCase` existe, mas nenhuma tela o usa), então o status nunca avança e "concluídos" não muda pela interface. Os campos `action` e `note` do caso não são exibidos nem preenchíveis.

### 2.10 `/qualidade` — Qualidade dos dados (`pages/QualityPage.tsx`)

- **Objetivo / pergunta:** "Posso confiar na planilha?"
- **Público:** gestão/apresentação; PCP em dúvida.
- **Endpoint:** `GET /api/data-quality`.

Elementos: cabeçalho (L9); quatro cartões (L10): Registros avaliados 11.296 ("12 abas carregadas"), Erros bloqueantes 0 ("validações da fonte"), Chaves órfãs 0 ("integridade referencial"), Cobertura sell-out 20% ("50 de 250 pares"); "Cobertura da fonte": tabela de **5 colunas** (Aba, Registros, Duplicidades, Colunas ausentes, Situação) com **12 linhas, todas "Íntegra"** (L11; nomes de aba vindos do Excel, ex.: "Carteira Pedidos", "Ordens Producao", "Sell In"); caixa "Como interpretar a cobertura" (L12).

| Contagem | 1440×900 | 375×812 |
|---|---|---|
| Números na primeira dobra | 38 (cartões + linhas da tabela) | 17 |
| Avisos | 1 | 1 |
| Altura | 1.158 px | 1.447 px |

### 2.11 `/cenarios` — Cenários (`pages/ScenariosPage.tsx`)

- **Objetivo / pergunta:** "E se eu mudar o peso de um sinal?"
- **Público:** gestão/analista (uso avançado).
- **Endpoints:** `GET /api/config`; `POST /api/scenarios` (não executado).

Elementos: cabeçalho "Simulação de cenários" (L15); **2 controles deslizantes** ("Excesso de cobertura" e "Conflito de capacidade", escala 0–20, com "Oficial: 3/5" em 9,5 px) e botão "Executar simulação" (L16); painel escuro "Nenhuma alteração é persistida" (L16), com metade da largura; depois da simulação, "Resultado simulado" com `PriorityTable` de 10 linhas e selo "Cenário hipotético" (L17).

Fatos: o cabeçalho diz "Teste pesos", mas **só 2 dos 7 pesos** podem ser alterados. Números na primeira dobra: 4 (3, 3, 5, 5). Altura 900 / 976 px.

### 2.12 `/execucoes` — Execuções (`pages/RunsPage.tsx`, `components/RunComparisonView.tsx`)

- **Objetivo / pergunta:** "O que mudou entre duas execuções e por quê?"
- **Público:** gestão/auditoria.
- **Endpoints:** `GET /api/runs`; `GET /api/run-comparisons?base=&target=`; `POST /api/runs` (não executado).

Elementos: cabeçalho "Execuções registradas" + botão "Registrar execução atual" (L31); "Comparar execuções": estado vazio "São necessárias duas execuções" (existe **1** execução; a comparação **não pôde ser capturada** porque exigiria gravar uma segunda) (L33-42); "Histórico": linha do tempo com "Execução #1", "41 SKUs", selo "só ranking", data e hash de 16 caracteres (L45). Com 2+ execuções (visto só no código): formulário Base/Alvo; seções "Fonte e configuração", "Ranking oficial" (4 cartões: Entraram/saíram, Mudaram, Score ou confiança, Sem explicação), "Previsão e recomendação operacional", "Cobertura B2B2C", limitações (`RunComparisonView.tsx:41-98`).

Números na primeira dobra: 12; altura 900 / 867 px.

### 2.13 `/decisoes` — Decisões (`pages/FeedbackPage.tsx`)

- **Objetivo / pergunta:** "Registrar a decisão que tomei."
- **Público:** PCP.
- **Endpoints:** `GET /api/feedback`, `GET /api/priorities`, `GET /api/config`; `POST /api/feedback` (não executado).

Elementos: cabeçalho "Feedback do PCP" (L28); formulário "Registrar decisão" (L30-37): SKU (select, **só os 41 priorizados**, padrão = 1º do ranking), Ação tomada (Aceita, Alterada, Rejeitada, Investigar), Efeito do dado do parceiro (4 opções), Tempo de análise em minutos (opcional, rótulo "Opcional" a 8 px), Usuário, Observação, botão "Registrar decisão"; "Histórico recente" (estado vazio: 0 decisões; cada item teria SKU, 2 selos, observação, minutos, usuário e data).

Fatos: nenhum campo é marcado como obrigatório; o formulário não sabe de qual SKU a pessoa veio; a decisão **não guarda qual recomendação foi aceita ou rejeitada**. Números na primeira dobra: 0. Altura 985 / 1.264 px.

### 2.14 `/validacao` — Central de validação (`pages/ValidationPage.tsx`)

- **Objetivo / pergunta:** "Quanto posso confiar nessas recomendações?"
- **Público:** gestão/apresentação (e Comercial/PCP em dúvida).
- **Endpoint:** `GET /api/validation/summary`.

Elementos, de cima para baixo:

1. Cabeçalho "Central de validação" + "Exportar CSV" + "Imprimir resumo" (L85); eyebrow "Semana 4 · Aplicabilidade".
2. Aviso "Evidência, não promessa de ganho" (L87).
3. Quatro cartões (L90-95):

| Número | Significa | Origem | Contexto |
|---|---|---|---|
| 8/8 Casos aprovados | casos congelados que passaram | `frozen_cases.passed/total` | "0 falha(s) · 0 não encontrado(s) · 2 sintético(s)" |
| 6,9% WAPE ponderado | erro médio ponderado do modelo escolhido, nos 3 meses de teste | `forecast_evaluation.models[selecionado].weighted_wape` | "baseline: 8% · 50 SKUs" (6,9% e 8%: casas decimais diferentes; o roteiro diz 8,0%) |
| 16 Não superou a baseline | SKUs em que o modelo não foi melhor que "repetir o último mês" | `forecast_evaluation.did_not_beat_baseline_skus` | "de 50 SKUs elegíveis · 0 não comparável(is)" |
| 7/7 Comportamento seguro | verificações executadas | `safe_behavior` | "executadas, nenhuma reprovada · 1 coberta(s) por teste" |

4. "Comparação com o processo atual" (L97-109): tabela de **5 colunas** × 4 linhas (Indicador, Informado pela empresa, Recalculado no protótipo, Meta, Observação): Tempo de análise (22 horas/semana; não disponível; 8 horas/semana), Erro médio do forecast (31% MAPE; 6,9% WAPE, "não comparável diretamente"; sem meta), Pedidos no prazo (89%; não disponível; 96%), Aderência ao plano (78%; não disponível; sem meta); fonte da linha de base.
5. "Tempo de análise registrado" (L111-120): 5 números (decisões 0, com tempo 0, minutos somados "—", média "—", amostra "insuficiente · mínimo 20") + nota + botão "Registrar decisão". Aqui o ausente aparece como "—"; em outros pontos, como "Não disponível".
6. "Desempenho dos modelos" (L122-143): tabela de **6 colunas** × 4 linhas (Modelo, Papel, SKUs avaliados "50 de 50", WAPE mediano, WAPE ponderado ⓘ, Escolhido em); faixa com 5 números (50 elegíveis, 0 insuficientes, 34 superaram, 16 não superaram, 0 holdout sem demanda); `<details>` "Ver os 16 SKU(s) em que o modelo não superou a baseline" (tabela de 5 colunas × 16 linhas); 3 limitações.
7. "Casos representativos congelados" (L145-156): **8 cartões sempre abertos** (entrada, esperado × obtido, limitação, ajuste), ≈2.045 px.
8. "Comportamento seguro" (L158-160): 8 verificações.
9. "Falhas conhecidas" (3 itens) + "Limitações permanentes" (4) e "Histórico de ajustes" (5 itens) (L162-171).
10. Rodapé: SHA-256, referência de vendas, data de geração (L172).

| Contagem | 1440×900 | 375×812 |
|---|---|---|
| Números na primeira dobra | 22 | 9 |
| Avisos | 1 em destaque + 2 notas + 3 listas de ressalvas | idem |
| Tabelas | 5 col. × 4 linhas; 6 col. × 4 linhas; 5 col. × 16 linhas (recolhida) | 760–899 px em contêiner de 343 px |
| Altura | **5.092 px** | **10.409 px** |
| Posição das seções (desktop / celular) | Comparação y=598 / 972; Desempenho y=1.365 / 2.006; Casos y=1.855 / 2.727; Comportamento seguro **y=3.900 / 8.143**; Falhas y=4.360 / 8.928 | |

### 2.15 `*` — Página não encontrada (`pages/NotFoundPage.tsx`)

Cartão "404 · Página não encontrada" + botão "Voltar para a visão geral". 1 número, 0 avisos. Sem problemas relevantes, exceto que o título da aba e o `h1` dizem "Página não encontrada" sem sugerir as páginas mais prováveis.

### 2.16 Quadro-resumo e capturas

Medições automáticas (1440×900 | 375×812). "Tokens numéricos" = quantidade de números exibidos na primeira dobra, excluindo códigos de SKU/parceiro e datas completas; inclui números de tabelas, rótulos e contadores, então **superestima os "números de negócio"** (exemplo em 2.2). "Menor fonte" = menor `font-size` calculado entre elementos visíveis do conteúdo.

| Rota | Tokens na dobra | Avisos (página toda) | Colunas por tabela | Altura (px) | Menor fonte | Capturas |
|---|---|---|---|---|---|---|
| `/guia` | 7 \| 3 | 1 | — | 2.669 \| 5.545 | 8,5 px | [1440](mapeamento-usabilidade/guia-1440x900.png) · [375](mapeamento-usabilidade/guia-375x812.png) |
| `/` | 11 \| 2 | 2 | 7 | 2.292 \| 3.582 | 10,5 px | [1440](mapeamento-usabilidade/visao-geral-1440x900.png) · [375](mapeamento-usabilidade/visao-geral-375x812.png) |
| `/prioridades` | 24 \| 2 | 1 | 9 | 3.157 \| 3.743 | 10,5 px | [1440](mapeamento-usabilidade/prioridades-1440x900.png) · [375](mapeamento-usabilidade/prioridades-375x812.png) |
| `/previsoes` | 15 \| 5 | 2 | 11 | 3.744 \| 18.727 | 8,5 px (celular) / 10 px | [1440](mapeamento-usabilidade/previsoes-1440x900.png) · [375](mapeamento-usabilidade/previsoes-375x812.png) |
| `/skus/CI-0041` | 14 \| 2 | 7 | 8 (+5 por parceiro) | 3.816 \| 5.329 | 8 px | [1440](mapeamento-usabilidade/sku-ci-0041-1440x900.png) · [375](mapeamento-usabilidade/sku-ci-0041-375x812.png) |
| `/skus/CI-0014` | 14 \| 4 | 6 | 8 (+5 por parceiro) | 3.221 \| 4.467 | 8 px | [1440](mapeamento-usabilidade/sku-ci-0014-1440x900.png) · [375](mapeamento-usabilidade/sku-ci-0014-375x812.png) |
| `/parceiros` | 29 \| 7 | 1 | — (8 cartões) | 1.583 \| 3.390 | 9 px | [1440](mapeamento-usabilidade/parceiros-1440x900.png) · [375](mapeamento-usabilidade/parceiros-375x812.png) |
| `/parceiros/KA-01` | 69 \| 9 | 2 | 8 (+5 por vínculo) | 3.198 \| 3.950 | 10,5 px | [1440](mapeamento-usabilidade/parceiro-ka-01-1440x900.png) · [375](mapeamento-usabilidade/parceiro-ka-01-375x812.png) |
| `/parceiros/KA-01?sku=CI-0011` | 41 \| 9 | 2 | 8 (+5) | 1.192 \| 1.775 | 10,5 px | [1440](mapeamento-usabilidade/parceiro-ka-01-sku-1440x900.png) · [375](mapeamento-usabilidade/parceiro-ka-01-sku-375x812.png) |
| `/casos` | 11 \| 11 | 0 | 5 | 900 \| 1.312 | 10,5 px | [1440](mapeamento-usabilidade/casos-1440x900.png) · [375](mapeamento-usabilidade/casos-375x812.png) |
| `/qualidade` | 38 \| 17 | 1 | 5 | 1.158 \| 1.447 | 10,5 px | [1440](mapeamento-usabilidade/qualidade-1440x900.png) · [375](mapeamento-usabilidade/qualidade-375x812.png) |
| `/cenarios` | 4 \| 4 | 1 | — (10 linhas após simular) | 900 \| 976 | 9 px | [1440](mapeamento-usabilidade/cenarios-1440x900.png) · [375](mapeamento-usabilidade/cenarios-375x812.png) |
| `/execucoes` | 12 \| 12 | 0 | — | 900 \| 867 | 9,5 px | [1440](mapeamento-usabilidade/execucoes-1440x900.png) · [375](mapeamento-usabilidade/execucoes-375x812.png) |
| `/decisoes` | 0 \| 0 | 0 | — | 985 \| 1.264 | 8 px | [1440](mapeamento-usabilidade/decisoes-1440x900.png) · [375](mapeamento-usabilidade/decisoes-375x812.png) |
| `/validacao` | 22 \| 9 | 1 + notas | 5, 6, 5 | 5.092 \| 10.409 | 10,8 px | [1440](mapeamento-usabilidade/validacao-1440x900.png) · [375](mapeamento-usabilidade/validacao-375x812.png) |
| 404 | 1 \| 1 | 0 | — | 900 \| 812 | 11 px | [1440](mapeamento-usabilidade/404-1440x900.png) · [375](mapeamento-usabilidade/404-375x812.png) |

Volume de texto visível por rota (palavras) e números na página inteira (tokens numéricos, mesma regra): `/guia` 765 · 16; `/` 442 · 35; `/prioridades` 925 · 171; `/previsoes` 1.569 · 371; `/skus/CI-0041` 765 · 65; `/skus/CI-0014` 651 · 107; `/parceiros` 400 · 70; `/parceiros/KA-01` 823 · 304; `/casos` 121 · 11; `/qualidade` 151 · 44; `/cenarios` 57 · 4; `/execucoes` 63 · 12; `/decisoes` 119 · 0; `/validacao` 2.239 · 183.

Frequência de termos técnicos no texto visível (soma das rotas com os maiores valores): WAPE 7 em `/validacao` e 1–2 em `/previsoes`/`/skus` (mais 50 rótulos "WAPE" nos cartões do celular); baseline 8 em `/validacao` e 4 em `/guia`; holdout 8 em `/validacao`; sell-out 15 em `/validacao`, 13 em `/prioridades`, 10 em `/parceiros`; revisão humana 11 em `/validacao` e 4 em `/skus/CI-0041`; expressões equivalentes a "não é ordem de produção / não libera / não autoriza" 3 em `/`, `/previsoes`, `/validacao` e 3–4 em cada SKU, **fora** a nota fixa do menu em todas as páginas.

## 3. Inventário do backend (B)

Fonte: `backend/main.py`, `backend/partners.py`, `backend/validation.py`, `backend/run_comparisons.py`, `frontend/src/api.ts`, `frontend/src/types*.ts` e respostas reais da API em 05/10/2026.

**Método do "não usado":** comparei, por nome de campo, o JSON real de cada endpoint com o código de `pages/`, `components/` e `components.tsx`, e conferi manualmente os casos duvidosos. É uma heurística: um campo pode ser lido sem ser exibido (por exemplo, para ordenar ou filtrar). Os campos abaixo foram verificados um a um; a lista não é exaustiva para respostas muito grandes (marcado "entre outros").

### 3.1 Todos os endpoints

| Método | Rota | Página que consome | Campos efetivamente exibidos | Campos retornados e não usados |
|---|---|---|---|---|
| GET | `/api/health` | nenhuma (smoke test e operação) | — | todos |
| GET | `/api/system` | `App.tsx` (faixa de modo e formulários) | `demo_mode`, `write_enabled`, `notice`, `text_limits.*` (limites dos campos) | `environment`, `text_limits.case_action` |
| GET | `/api/overview` | `/` | `total_skus`, `prioritized`, `rupture_sku_count`, `below_lead_time_count`, `below_safety_stock_count`, `order_without_production`, `low_confidence`, `risk_distribution`, `decision_count`, `partner_data_influenced_decision_count` | `risk_count` (alias), `rupture_signal_count` (28), `excess_count` (6), `confidence_distribution` (média 21, baixa 20) |
| GET | `/api/priorities` | `/`, `/prioridades`, `/casos` e `/decisoes` (lista de SKUs), resultado de `/cenarios` | `priority`, `sku`, `product`, `family`, `attention_score`, `confidence`, `reasons[]` (código, severidade, descrição), `critical_date`, `critical_date_reason`, `operational_gap_quantity` | `confidence_reason`, `projected_stock_quantity`, `first_promised_date`, `first_production_completion`, `sell_in_quantity`, `sell_out_quantity`, `sell_in_minus_sell_out_quantity`, `forecast_quantity`, `analysis_scope`, `missing_data`, `evidence[]`, `disclaimer` (estes só aparecem no detalhe, que consulta `/api/priorities/{sku}`). Os filtros `family`, `confidence`, `search` do servidor não são usados (a filtragem é no cliente) |
| GET | `/api/priorities/{sku}` | `/skus/:sku` | `indicator.*` (estoque, carteira, produção aberta, estoque projetado, lacuna, cobertura, lead time, datas, sell-in/out, parceiros com sell-out, forecast, ausentes), `priority[0]` (posição, score, confiança, motivo da confiança), `forecast.*`, `operational_recommendation.*` (ação, quantidade, confiança, justificativa, cálculo, status de capacidade), `issues[]` (código, severidade, descrição, valores usados, origem), `limitation` | **`score_contributions[]` (peso de cada sinal no score)**; `operational_recommendation.assumptions[]`, `.limitations[]`, `.raw_quantity`, `.requires_human_review`; `indicator.abc_curve`, `average_sales_per_day`, `coverage_days_source`, `coverage_days_difference`, `capacity_*` (semana de referência, máxima, comprometida, disponível, ocupação, média, nº de semanas), `sell_out_visibility`; `priority.disclaimer` |
| GET | `/api/forecasts` | `/previsoes` | `sku`, `product`, `family`, `priority`, `forecast.trend/status/forecast_next_month/forecast_total_3m/model_label/backtest_wape/forecast_confidence`, `operational_recommendation.action/action_label/suggested_quantity/minimum_lot/capacity_status` | `attention_score`, `confidence` e `confidence_reason` (do ranking), `forecast.reference_month/history_months/model/forecast_months/forecast_values/trend_change_ratio/limitation`, `operational_recommendation.confidence/confidence_reason/requires_human_review` |
| POST | `/api/scenarios` | `/cenarios` | `ranking[]` (via `PriorityTable`), `warning` | demais campos do ranking simulado; só 2 dos 7 pesos são enviados |
| GET | `/api/b2b2c/visibility` | **nenhuma** (ver 3.2) | — | todos: `partners[].level`, `next_level`, `next_level_required_skus`, `next_level_requirement`, `months_observed`, `note`, `classification_disclaimer` |
| GET | `/api/capacity/{family}` | **nenhuma** (ver 3.2) | — | todos: semanas, linha, capacidade máxima, comprometida, disponível, ocupação, limitação |
| GET | `/api/data-quality` | `/qualidade`; `/` (cobertura) | `sheets.*.records`, `.duplicate_keys`, `.missing_columns`, `errors` (contagem), `foreign_keys[].orphan_count`, `sell_out_coverage.coverage/observed_pairs/possible_pairs` | `warnings`, `sheets.*.missing_values/invalid_dates/negative_values`, `foreign_keys[].child_sheet/child_column/parent_sheet/examples`, `sell_out_coverage.missing_data_is_not_zero` |
| GET | `/api/partners` | `/parceiros` | `reference_month`, `total`, `items[].code/name/type/region/channel/observed_skus/linked_skus/total_catalog_skus/coverage/latest_sell_out_month`, `action_counts.avaliar_reposicao`, `quality_counts.stale/insufficient` | `items[].state/city/backlog_quantity`, `action_counts.monitorar_estoque/investigar_divergencia/solicitar_atualizacao/dados_insuficientes`, `quality_counts.sufficient`, `thresholds`, `field_nature`, `limitation` (a página usa texto próprio) |
| GET | `/api/partners/{codigo}` | `/parceiros/:codigo` | `partner.name/code/region/channel/coverage/observed_skus/total_catalog_skus/latest_sell_out_month/linked_skus`, `quality_counts.stale`, `reference_month`, `decisions.reason` | `partner.type/state/city/backlog_quantity`, `action_counts.*`, `quality_counts.sufficient/insufficient`, `thresholds`, `decisions.attribution_available/items` |
| GET | `/api/partners/{codigo}/skus` | `/parceiros/:codigo` (matriz, 50 por página) | `sell_in_recent/months`, `sell_out_recent/months`, `comparable_*`, `estimated_stock`, `stock_month`, `coverage_days`, `backlog_*`, `data_quality`, `action_label`, `signals[].label`, `age_months`, `missing_months`, `data_nature`, `average_monthly_sell_out`, `recommendation_reason`, `periods[]`, `orders[]`, `thresholds`, `field_nature`, `limitation` | `window_months`, `divergence_ratio`, `action` (código; só o rótulo é exibido), `requires_human_review` |
| GET | `/api/commercial-recommendations` | `/skus/:sku` (somente com `sku=`) | mesmos campos da matriz | os filtros `partner`, `region`, `channel`, `action`, `data_quality` não são usados por nenhuma tela. Com `action=avaliar_reposicao` a resposta traz as **12 oportunidades de 5 parceiros numa só chamada** |
| GET | `/api/validation/summary` | `/validacao` | quase tudo (também no CSV exportado) | `analysis_time.median_minutes_per_decision`, `forecast_evaluation.insufficient_sku_list`, `forecast_evaluation.items[].selected_model/candidate_wapes/holdout_actual_total`, `frozen_cases.frozen_source_sha256` |
| GET | `/api/runs` | `/execucoes` | `id`, `created_at`, `source_hash`, `prioritized_skus`, `comparison_schema_version` | nenhum |
| GET | `/api/runs/{id}` | **nenhuma** | — | todos (`comparison` completo) |
| GET | `/api/run-comparisons` | `/execucoes?base=&alvo=` | ranking, previsões, cobertura B2B2C, contexto e limitações (ver `RunComparisonView.tsx`) | **não verificado com dados reais**: só existe 1 execução e não gravei outra |
| GET | `/api/config` | `/cenarios` (2 pesos), `/casos` (`case_statuses`), `/decisoes` (`actions`, `partner_data_effects`) | `weights.EXCESS_COVERAGE`, `weights.CAPACITY_CONFLICT`, `case_statuses`, `actions`, `partner_data_effects` | `thresholds`, os outros 5 pesos |
| GET | `/api/cases` | `/casos` | `id`, `sku`, `status`, `owner`, `due_date`, `updated_at` | `run_id`, `action`, `note`, `created_at` |
| GET | `/api/cases/{id}/history` | **nenhuma** | — | todos |
| POST/PUT | `/api/cases`, `/api/cases/{id}` | `/casos` usa só `POST`; **`PUT` não é usado por nenhuma tela** (`api.updateCase` existe sem uso) | — | — |
| GET | `/api/feedback` | `/decisoes` | `sku`, `action`, `partner_data_effect`, `note`, `analysis_minutes`, `user_name`, `created_at` | nenhum relevante |
| POST | `/api/feedback`, `/api/runs` | `/decisoes`, `/execucoes` (não executados nesta fase) | — | — |

### 3.2 Endpoints que nenhuma página usa (apenas registro; os contratos devem ser preservados)

| Endpoint | Observação |
|---|---|
| `GET /api/b2b2c/visibility` | Há leitor em `api.ts` (`dashboardReaders.b2b`, `loadDashboard`), mas nenhuma página o inclui em `PAGE_FIELDS`. O Guia ainda explica o "Nível B2B2C" (Sem visibilidade, Essencial, Conectado, Estratégico) e `partnerLevelTone` (`shared.ts:59`) existe, mas **nenhuma tela mostra esse nível**. O menu ainda se chama "Visibilidade B2B2C" |
| `GET /api/capacity/{family}` | Exemplo real (Escolar): semanas com ocupação de 92%, 94% etc. e capacidade máxima de 12.000. A tela diz apenas "Capacidade pressionada"; o número aparece só em "Riscos e evidências" como `average occupation 0.9325` |
| `GET /api/runs/{id}` | A comparação usa `/api/run-comparisons` |
| `GET /api/cases/{id}/history` e `PUT /api/cases/{id}` | O caso não pode ser atualizado pela interface, e o histórico não é exibido |
| `GET /api/health` | Uso operacional (smoke test) |

### 3.3 Dados já disponíveis que simplificariam a interface

| # | O que a API já entrega | Como simplifica (apenas apresentação) |
|---|---|---|
| 1 | `reasons[]` (com `severity`) + `GET /api/config.weights` | Calcular o **motivo principal** como o sinal de maior peso e ordenar os badges por peso. Hoje a API devolve os sinais em ordem alfabética de código e a tela usa o primeiro. Opção aditiva: campo `main_reason` na resposta |
| 2 | `score_contributions[]` (peso por sinal, só no detalhe) | Exibir "Score 33 = 10 + 8 + 8 + 5 + 2" em vez de 5 cartões sem peso; reforça o princípio 1 |
| 3 | `operational_recommendation.action_label`, `suggested_quantity`, `rationale[]`, `calculation` | Montar uma **frase de resposta** no topo do SKU: "Produzir 400 unidades após validar capacidade" + uma linha de porquê. Os textos de `rationale` usam decimais com ponto ("1246.3", "270.6") e precisam de formatação pt-BR |
| 4 | `forecast.forecast_confidence` (alta em 50/50) × `confidence` (ranking: 20 baixas, 21 médias) × `operational_recommendation.confidence` | Já existem três níveis distintos; basta rotulá-los ("confiança nos dados do SKU", "confiança na previsão") em vez de três selos chamados "confiança" |
| 5 | `GET /api/commercial-recommendations?action=avaliar_reposicao` | Uma lista única de **12 oportunidades** (parceiro, SKU, estoque estimado, cobertura em dias, giro mensal) substitui o percurso parceiro a parceiro |
| 6 | `partners.items[].action_counts` (5 ações) e `quality_counts` | Um selo "4 oportunidades · 4 sem dados" por parceiro em vez de barra, "10/50", "vínculos reais", "último sell-out" e contagens em texto de 9 px |
| 7 | `GET /api/b2b2c/visibility` (`level`, `next_level_requirement`) | Selo único por parceiro com próximo passo ("observar mais 10 SKUs para chegar a 40%"). Atenção: a classificação é demonstrativa; só adotar se o grupo quiser mantê-la |
| 8 | `forecast_evaluation.beat_baseline_skus` (34), `did_not_beat_baseline_skus` (16) e `known_failures[]` (frases prontas) | Veredito de uma frase no topo da Validação: "Em 16 de 50 SKUs a previsão do modelo não foi melhor que repetir o último mês" |
| 9 | `overview.confidence_distribution` (média 21, baixa 20) | Dar denominador a "Baixa confiança 20" ("20 de 41") |
| 10 | `critical_date`, `first_production_completion`, `positiveDelayDays` (já calculado no cliente) | Frase "produção só em 08/10, 25 dias depois da promessa" no lugar de duas datas e um "intervalo de risco" |
| 11 | `GET /api/capacity/{family}` e `issues[].values_used.average_occupation/threshold` | "Linha Escolar 93% ocupada (limite 90%)" no lugar de "Capacidade pressionada" |
| 12 | `requires_human_review` (sempre `true`) | Não precisa ser lembrado em cada bloco: uma declaração única e persistente basta |
| 13 | `GET /api/validation/summary.known_failures[]` e `known_limitations[]` | Já são frases curtas; podem alimentar a faixa "Limitações" da Validação sem texto novo |

### 3.4 Dados ainda inexistentes na API para as funcionalidades planejadas

- **Faturamento previsto:** a aba `Vendas_24m` da planilha tem `Preço unitário (R$)` e `Valor faturado (R$)`, mas nenhum endpoint os expõe; a previsão atual é de **quantidade**. Exige campo novo e aditivo (não é decisão desta fase).
- **Região e canal:** `region` e `channel` já existem em `/api/partners` e na matriz. Falta apenas agrupar na tela.
- **Matriz de decisão parceiro × SKU:** a API só devolve vínculos reais (95 no total, de 400 combinações possíveis: 8 parceiros × 50 SKUs; 14 para KA-01). Não há como "preencher" combinações sem dado, e a interface não deve fingir que há.

## 4. Fluxos de tarefa (C)

Os caminhos foram percorridos no navegador (script de controle) e conferidos no código. Posições (`y`) são pixels desde o topo da página; a dobra mede 900 px (desktop) e 812 px (celular). Fluxos que gravariam dados (5) foram **contados no código, sem enviar o formulário**.

### 4.1 PCP — "Qual SKU devo olhar primeiro hoje e por quê?"

| Item | Resultado |
|---|---|
| Caminho atual | Abrir `/` (rota inicial). O CI-0041 aparece na dobra (y=344; no celular y=469). Para evidências: botão "Abrir evidências de CI-0041" → `/skus/CI-0041` |
| Cliques / telas | **0** cliques para saber qual SKU; **1** clique e 2 telas para as evidências |
| Rolagem | Nenhuma para o "qual". No SKU, "Riscos e evidências" começa em y=1.913 (2,1 telas) |
| O que a pessoa precisa interpretar | 5 badges de sinais coloridos + "Confiança baixa" (também em badge); 4 cartões (41, 16, 12, 20); o que é "score" |
| Pontos de dúvida | (a) A frase sob o cartão é a descrição do **primeiro sinal em ordem alfabética** ("A ocupação média da família excede o limite…"), mas o sinal crítico é "Abaixo do estoque de segurança" (P01). (b) 15 + 13 ≠ 16 no cartão de risco, sem explicação de sobreposição. (c) "Baixa confiança 20" não diz "de 41". (d) O aviso que explica que prioridade não é ordem de produção fica na seção 02 (y=1.145), abaixo da dobra |

### 4.2 PCP — "Preciso produzir este SKU? Quanto?"

| Item | Resultado |
|---|---|
| Caminho atual (CI-0014) | Menu → "Previsão e recomendações" (1) → Buscar "CI-0014" (1 clique + digitação) → ler a linha (a quantidade está no limite da tela e "Ver detalhes" fora dela: rolagem horizontal) → "Ver detalhes" (1) → `/skus/CI-0014` → rolar até y=1.523 ("Ação sugerida") e y=1.588 (linha de cálculo) |
| Cliques / telas | **3** cliques + 1 digitação + 1 rolagem horizontal; **3** telas (`/`, `/previsoes`, `/skus/…`) |
| Rolagem vertical | 1,7 tela no desktop; 2,7 no celular (ação em y=2.204) |
| Variante no celular | `/previsoes` vira 50 cartões, 18.727 px; a busca é obrigatória para chegar a um SKU |
| O que a pessoa precisa interpretar | Ação ("Produzir após validar capacidade"), quantidade 400 e **lote 400** (parecem a mesma coisa), selo "Validar capacidade", WAPE, três "confianças" |
| Pontos de dúvida | CI-0041: a linha mostra "Sem ação necessária · 0 · Lote: 400 · Validar capacidade" (quatro sinais aparentemente contraditórios; a explicação "sem ação não é sem risco" só existe no detalhe). Cartão "Produção sugerida 14" = 12 "Produzir" + 2 "Produzir após validar capacidade". "Validar capacidade 6" conta SKUs com família pressionada **mesmo sem ação** de produção. A justificativa usa "1246.3" e "270.6" (ponto decimal) enquanto a tela usa "1.246,3" |

### 4.3 Comercial — "Qual parceiro tem oportunidade de reposição e qual é a evidência?"

| Item | Resultado |
|---|---|
| Caminho atual | Menu "Visibilidade B2B2C" (1) → cartões ordenados **por nome** → Ordenar: "Sugestões de reposição" (2) → Papelaria Horizonte (4 sugestões) → "Abrir parceiro e evidências" (1) → 14 vínculos misturados → Ação comercial: "Avaliar reposição" (2) → 4 linhas; a coluna da ação está cortada → rolagem horizontal → expandir "Evidências de KA-01 · CI-0011" (1; o resumo fica abaixo da tabela, não na linha) |
| Cliques / telas | **7** cliques, 2 telas e 1 rolagem horizontal para a **primeira** oportunidade |
| Para ver as 12 oportunidades | Repetir para os 5 parceiros: cada um exige "Voltar" (1) + abrir parceiro (1) + filtro de ação (2) + expandir evidência (1) = 5 cliques → **≈ 27 cliques** (cálculo a partir do percurso, sem contar rolagens) |
| O que a pessoa precisa interpretar | "Pares com sell-out 50 — pares observados, não SKUs distintos"; "Dados insuficientes 45"; "20% observado" igual em 5 parceiros; "Diferença comparável" (pode ser negativa); "Estoque estimado" × "observado"; cobertura em dias contra o limite de 30 dias (só aparece no texto da evidência) |
| Pontos de dúvida | A oportunidade é o dado mais importante e aparece no rodapé do cartão em 9–9,5 px; não existe lista com as 12 (a API as entrega numa chamada, ver 3.3 item 5); nome e código do parceiro aparecem colados |

### 4.4 Gestão — "Quanto posso confiar nessas recomendações?"

| Item | Resultado |
|---|---|
| Caminho atual | Menu "Validação" (1). Dobra: aviso "Evidência, não promessa de ganho" + 4 cartões (8/8; 6,9% com "baseline: 8%"; 16; 7/7) + início da tabela "Comparação com o processo atual" |
| Cliques / telas | **1** clique para ver os números; **3** cliques / 3 telas para completar (`/` → "Baixa confiança 20", `/qualidade` → cobertura 20%) |
| Rolagem | A frase que diz "o modelo não superou a baseline em 16 de 50 SKU(s)" só aparece em "Falhas conhecidas" (y=4.360, 4,8 telas); na dobra há apenas o número 16 |
| O que a pessoa precisa interpretar | WAPE, baseline, holdout, "informado / recalculado / meta", "caso congelado", "sintético", "coberto por teste" |
| Pontos de dúvida | Nenhum cartão diz se o número é bom ou ruim. Na página `/previsoes` a confiança da previsão é **"alta" em 50 de 50** SKUs; em `/` a confiança do ranking é "baixa" em 20 de 41: as duas informações parecem contradizer-se sem explicação. A baseline aparece como "8%" ao lado de "6,9%" (casas decimais diferentes; o roteiro diz 8,0%) |

### 4.5 PCP — "Registrar a decisão que tomei"

| Item | Resultado |
|---|---|
| Caminho atual (após analisar o CI-0014) | `/skus/CI-0014` **não tem** botão ou link para registrar (0 links para `/decisoes` e `/casos`; único botão: "Voltar"). Menu "Decisões" (1) → SKU (o formulário vem com o 1º do ranking; abrir e escolher = 2) → [Ação tomada: padrão "Aceita"] → [Efeito do dado do parceiro: padrão "Não utilizado"] → [Tempo, Usuário, Observação, opcionais] → "Registrar decisão" (1) |
| Cliques / telas | **4 cliques no mínimo** (só padrões) a **≈ 11 interações** no preenchimento completo; 2 telas. Nada foi enviado |
| O que a pessoa precisa interpretar | "Efeito do dado do parceiro" (4 opções); "Ação tomada" (aceita o quê?) |
| Pontos de dúvida | O SKU analisado não vem preenchido; a lista exclui os 9 SKUs fora do ranking; o registro não guarda qual recomendação (ação e quantidade) foi aceita, alterada ou rejeitada; nenhum campo é marcado como obrigatório; sem confirmação visível além da mensagem curta |

### 4.6 Apresentação — roteiro de 5 minutos (`docs/roteiro-demonstracao.md`)

Posições medidas em 1440×900 (celular entre parênteses).

| Minuto | Passo do roteiro | Onde está o conteúdo | Cliques / rolagens | Atrito |
|---|---|---|---|---|
| 0:00–1:00 | `/validacao`, "Comparação com o processo atual": 22 h, 89%/96%, 31% (MAPE), 78% | Tabela em y=598 (972): só as 2 primeiras linhas cabem na dobra | 1 rolagem curta | O roteiro cita "só 20% dos pares têm sell-out" nesta tela, mas esse número **não existe em `/validacao`**: está em `/`, `/qualidade` e `/parceiros/:codigo` |
| 1:00–2:00 | `/`: CI-0041 #1, score 33, 5 sinais; 16/15/13, 12, 20 | Tudo na dobra (CI-0041 em y=344; cartões logo abaixo) | 0 | A mensagem "não é ordem de produção" é um aviso em y≈1.145 (seção 02), fora da dobra: +1,3 tela de rolagem para mostrá-lo |
| 2:00–3:00 | Clicar "Abrir evidências de CI-0041" e ver "Sem ação necessária"; abrir `/skus/CI-0014` e mostrar 400 un., 1.327, 433, 1.490, 0, 271 | CI-0041: ação em y=1.665; CI-0014: ação em y=1.523 e linha de cálculo em y=1.588 | 1 clique + 2 rolagens de ≈1,7–1,9 tela | O "271" da necessidade aparece só como "270.6" (texto com ponto decimal) e o "1.327" como "previsão (1246.3) e carteira (1327.0)" |
| 3:00–4:00 | `/parceiros` → KA-01 → `/parceiros/KA-01?sku=CI-0011`: 132, 151/mês, ≈26 dias, "Avaliar reposição" | Linha na dobra; a coluna "Qualidade / ação comercial" vai de x=1.296 a x=1.497 (contêiner termina em x=1.387); evidência: resumo em y=827 | 1 clique (evidências) + rolagem horizontal | O "151/mês" só existe dentro da evidência ("151,3"); o roteiro cita E-commerce próprio como "dados insuficientes", que exige abrir `/parceiros` (fora do percurso de abas) |
| 4:00–5:00 | `/validacao`: WAPE 6,9% × 8,0%; 16 de 50; 8/8 casos; 7/7 verificações | "Desempenho dos modelos" y=1.365; "Casos congelados" y=1.855; "Comportamento seguro" y=3.900 (celular: 2.006, 2.727, 8.143) | 3 rolagens longas em 60 s (≈ 4,3 telas até o último bloco) | A tela mostra "baseline: 8%" (o roteiro diz 8,0%) |

Soma aproximada: **1 clique obrigatório** (as demais telas ficam em abas já abertas) e **≈ 8 telas de rolagem vertical** (desktop) para alcançar os trechos citados.

### 4.7 Antes × depois (estimado)

"Antes" = medido ou contado acima. "Depois" = **estimativa** assumindo a aprovação das propostas indicadas; deve ser remedido na Fase 2.

| Fluxo | Cliques antes | Cliques depois | Rolagem antes | Rolagem depois | Números a interpretar antes → depois | Propostas |
|---|---|---|---|---|---|---|
| 1. Qual SKU primeiro e por quê | 0 (1 p/ evidências) | 0 (1) | 0 (evidências a 2,1 telas) | 0 | 4 cartões + 5 badges → 1 frase + 3–4 números | E01, E07, E14, E36 |
| 2. Preciso produzir? Quanto? | 3 + digitação + rolagem horizontal | 1–2 | 1,7 tela (2,7 no celular) | 0 | ≈ 14 números e 3 confianças → 1 frase com quantidade + 3 números | E02–E06, E21 |
| 3. Oportunidade de reposição e evidência | 7 (primeira) / ≈ 27 (12) | 2 | 1 rolagem horizontal por parceiro | 0 | 4 cartões + 8 colunas → 1 lista de 12 com 4 colunas | E15–E18 |
| 4. Quanto confiar | 1–3 telas, 3 cliques | 1 | até 4,8 telas para ler "16 de 50" em frase | 0 | 4 cartões técnicos → 1 veredito + 4 números com sentido | E19, E23–E24, E05 |
| 5. Registrar a decisão | 4 a ≈ 11 interações | 2 mínimo | 0 | 0 | 4 rótulos técnicos → 3 perguntas simples | E26–E28 |
| 6. Roteiro de 5 min | 1 clique + 5 trocas de aba | 1 clique + 5 trocas | ≈ 8 telas | ≤ 3 telas | — | E04, E15, E23 |

---

## 5. Problemas (D)

**Escala.** Gravidade: **crítico** (leva a interpretar errado o dado central ou esconde a resposta), **alto** (atrapalha uma das 6 tarefas), **médio** (confunde ou cansa), **baixo** (acabamento). Frequência: número de rotas afetadas (de 14 mais o 404).

**Nota de método (divergências com o plano).** O plano e o enunciado citam **13 itens de menu** (o menu real tem **11**; 13 é o número de URLs do mapa de rotas, contando os dois detalhes), **12 e 15 colunas** (medi **11** em `/previsoes`, das quais 10 com cabeçalho visível, e **8** na matriz do parceiro; as tabelas de evidência mensal têm 5) e **19 cabeçalhos e 11 badges** na Validação (medi 16 cabeçalhos nas 3 tabelas visíveis e 58 badges, contando os do conteúdo recolhido). A diferença é de critério de contagem; usei os valores medidos. O plano também cita 67 declarações de fonte entre 8 e 10,5 px: **confere** (67; 100 abaixo de 12 px, de 197 declarações em `App.css`).

### 5.1 Tabela de problemas (ordenada por gravidade)

| ID | Gravidade | Frequência | Problema | Onde (rota · elemento · arquivo:linha) | Critério / heurística |
|---|---|---|---|---|---|
| P01 | **Crítico** | 3 rotas (`/`, `/prioridades`, `/cenarios`) | "Motivo principal" é o 1º sinal da lista, e a API ordena por código alfabético. Em 27 de 41 SKUs não é o de maior peso; em 13 de 41 é "Baixa visibilidade de sell-out" (peso 2, o menor). CI-0041: aparece "Capacidade pressionada" (peso 5), o crítico "Abaixo do estoque de segurança" (peso 10) é o 5º. A frase do cartão do primeiro da fila usa a mesma descrição | `/` · cartão do 1º da fila · `OverviewPage.tsx:15`; `/prioridades` · coluna "Motivo principal" · `components.tsx:178,182`; `shortReason` `components.tsx:154-162` | Nielsen 2 (correspondência com o mundo real), 5 (prevenção de erros); interpretação |
| P02 | **Crítico** | 3 (`/previsoes`, `/skus/:sku`, matriz) | A resposta de "produzir? quanto?" fica fora da dobra: tabela de 11 colunas com 1.428 px em contêiner de 1.070 px ("Quantidade" cortada; "Capacidade" e "Ver detalhes" fora da tela); no SKU a ação sugerida está a 1,7 (desktop) a 2,7 telas (celular) do topo; no celular são 18.727 px de cartões | `/previsoes` · tabela · `ForecastsPage.tsx:94`, CSS `.forecast-page-table .data-table { min-width: 1320px }` (`App.css:276`); `/skus/:sku` · ordem das seções · `SkuDetailPage.tsx:43-65`; cartões `ForecastsPage.tsx:97` | Hierarquia; ações; Nielsen 1, 7 |
| P03 | Alto | 9 rotas | O mesmo aviso se repete 5 a 7 vezes por tela: `DecisionBoundary` (4 rotas), "Revisão humana obrigatória" (Previsões, SKU, Validação), legenda da tabela, nota fixa do menu (todas), "Sem ação necessária… não significa sem risco", "Recomendação comercial, não operacional", "Limitação conhecida"… Em `/previsoes` ocupam ≈190 px da dobra | `components.tsx:93,131-133,178`; `ForecastsPage.tsx:74-75`; `SkuDetailPage.tsx:40-41,61,66`; `OverviewPage.tsx:28`; `PrioritiesPage.tsx:26`; `CommercialMatrix.tsx:12`; `ValidationPage.tsx:87` | Repetição; densidade; Nielsen 8 |
| P04 | Alto | 4 (`/`, `/previsoes`, `/skus/:sku`, `/validacao`) | Três "confianças" e duas "previsões" com nomes quase iguais: ranking (baixa 20 / média 21 de 41), previsão (alta 50/50) e recomendação (selo no bloco da previsão); "Próximos 3 meses 3.810,5" (modelo) e "Forecast disponível 2.788" (Forecast_Comercial, na seção "Canal e confiança"). No CI-0041: 2.245 × 2.264. Compromete o princípio 3 (previsto/estimado distinguíveis) e a pergunta "quanto confiar" | `SkuDetailPage.tsx:43,50,51,56,58`; `ForecastsPage.tsx:95` (coluna "Confiança"); `OverviewPage.tsx:22` | Consistência; interpretação; Nielsen 4 |
| P05 | Alto | 8 | Termos técnicos sem tradução: WAPE (cabeçalho, 50 rótulos no celular, "Erro no backtest"), baseline, holdout, backtest, sell-in/out, lead time, score, MAPE, "chaves órfãs", "integridade referencial". Só há 4 tooltips no app; o glossário está só no Guia (9 termos; sem sell-in/out, lead time, holdout, backtest, MAPE). "Backtest" (SKU) e "holdout" (Previsões, Validação) nomeiam a mesma coisa | `components.tsx:178`; `ForecastsPage.tsx:94,97`; `SkuDetailPage.tsx:58`; `ValidationPage.tsx:92,93,122-138`; `QualityPage.tsx:10`; `GuidePage.tsx:19-29` | Linguagem; Nielsen 2, 10 |
| P06 | Alto | 8 | Densidade na primeira dobra: 69 tokens numéricos em `/parceiros/:codigo`, 41 em `?sku=`, 38 em `/qualidade`, 29 em `/parceiros`, 24 em `/prioridades`, 22 em `/validacao` (1440×900). No celular, cabeçalhos e avisos consomem a dobra e sobram 2 a 5 números. `/previsoes`: 4 cartões + 7 controles + tabela de 11 colunas | ver 2.16; `ForecastsPage.tsx:76-91`; `PartnerDetailPage.tsx:30-31` | Densidade; Nielsen 8 |
| P07 | Alto | 3 (`/parceiros/:codigo`, `/skus/:sku`, matriz) | A matriz parceiro–SKU tem 8 colunas e 1.180 px; a **ação comercial é a última coluna e fica cortada** (x=1.296–1.497; contêiner termina em x=1.387). A evidência de cada vínculo está em `<details>` soltos abaixo da tabela (14 sumários para KA-01), longe da linha | `CommercialMatrix.tsx:14,23-34`; CSS `.commercial-table { min-width: 1180px }` (`App.css:446`) | Hierarquia; ações; princípio 1 (evidência ≤ 1 clique, mas descolada da linha) |
| P08 | Alto | 6 (`/skus/:sku`, `/previsoes`, `/parceiros`, `/qualidade`, `/casos`, `/decisoes`) | Falta o próximo passo: o SKU só tem "Voltar"; "12 sugestões" em `/parceiros` não leva a lista; Previsões só oferece "Ver detalhes"; Qualidade e Casos terminam sem ação; o formulário de decisão não sabe de qual SKU a pessoa veio | `SkuDetailPage.tsx:38`; `B2BPage.tsx:24`; `FeedbackPage.tsx:30-37` | Ações; Nielsen 3, 7 |
| P09 | Alto | 2 (`/parceiros`, matriz) | Não existe visão das oportunidades de reposição: ordem padrão por nome; as 12 oportunidades (5 parceiros) só se veem por parceiro (7 cliques para a primeira; ≈27 para todas); o endpoint de lista única existe e não é usado | `B2BPage.tsx:14,18,25,28`; `api.ts:84` | Ações; hierarquia; Nielsen 7 |
| P10 | Alto | 14 | Fontes abaixo de 12 px: 100 das 197 declarações de `font-size` em `App.css` (67 em ≤ 10,5 px). Renderizado: rótulos das métricas do SKU 8,5 px (≈ 66 elementos em CI-0041), eyebrows 8,5–10,5 px, cartões de parceiro 9–9,5 px, passos do Guia 9,5 px, rótulos de filtro 10–12 px, cabeçalhos de tabela e badges 11 px, descrição do menu 10,5 px, cartões de Previsões no celular 8,5 px (300 elementos). O teste de contraste cobre as cores, não o tamanho | `App.css:49-61,82,94,106,111,117,143,173-181,194-204,243-249` e blocos de sobrescrita `394-405` | Legibilidade; Nielsen 6 |
| P11 | Alto | 1 (a mais importante para gestão) | A Validação tem 5.092 px (10.409 no celular), 58 badges e 8 casos congelados sempre abertos (≈2.045 px). Não há veredito em uma frase: "16" é um número sem sentido sem "de 50"; a frase só aparece em "Falhas conhecidas" a 4,8 telas. O bloco "Comportamento seguro" fica a 4,3 telas | `ValidationPage.tsx:90-95,145-156,158-171` | Hierarquia; interpretação; princípio 4 |
| P12 | Médio | 9 | Formatos de número inconsistentes: percentual com no máximo 1 casa, então o zero final some ("baseline: 8%" ao lado de "6,9%"; "6%" para um erro real de 6,03% na linha do CI-0041 em Previsões); decimais com ponto em textos do backend ("1246.3", "270.6", "400.0", "151.333 unidades/mês", "26.2 dias") contra "1.246,3" e "26,2" na tela; ocupação "0.9325" em vez de 93,3%; ausente como "Não disponível", "—", "Não calculado", "Sem comparação percentual" e "não disponível"; 5 formatos de data (`13/09/2026`, `13 de set. de 2026`, `08/2026`, `2026-09-13`, `29/09/2026, 10:52`); unidades omitidas em estoque, carteira e previsão | `shared.ts:38-42`; `components.tsx:168-174`; `SkuDetailPage.tsx:46,65`; `ValidationPage.tsx:34,116`; `CommercialMatrix.tsx:29-30` | Consistência; interpretação |
| P13 | Médio | 13 | Títulos e nomes duplicados: cada página tem `h1` na barra e `h2` no cabeçalho ("Prioridades" e "Prioridades explicáveis"), mais o kicker da barra e o eyebrow (a mesma ideia 3 vezes: menu, kicker, eyebrow). Menu ≠ título: "Visibilidade B2B2C" × "Parceiros e canais"; "Decisões" × "Feedback do PCP"; "Previsão e recomendações" repetido nos dois | `components.tsx:47-59,98-110,135`; `App.tsx:60-63`; `routes.test.tsx:9-20` | Consistência; hierarquia; Nielsen 4 |
| P14 | Médio | todas as rotas | Menu com 11 itens planos, sem grupos, com rótulo + descrição de 10,5 px; mistura fluxo diário, comercial, gestão, registro e ferramentas avançadas; "Previsão e recomendações" quebra em 3 linhas | `components.tsx:47-59,87-92` | Navegação; Nielsen 6 |
| P15 | Médio | 6 | Cartões sem sentido nem referência: "16 SKUs com risco" (15 + 13 ≠ 16), "12 Pedidos sem OP", "20 Baixa confiança" (sem "de 41"), "0 Decisões", "0 Influenciadas por dado parceiro", "50 SKUs previstos / 50 SKUs analisados" (redundante), "0 Investigar dados", "0 Erros bloqueantes", "0 Chaves órfãs", "Produção sugerida 14" (12 + 2) | `OverviewPage.tsx:19-22,38-42`; `ForecastsPage.tsx:77-80`; `QualityPage.tsx:10` | Interpretação dos números |
| P16 | Médio | 6 | Tabelas largas no celular: `/prioridades` (781 px em 343), matriz do parceiro (1.180 px), tabelas de Validação (760–899 px), tabela da Visão geral (660 px). A rolagem horizontal só é indicada a leitores de tela (rótulo da região) | `components.tsx:178`; `CommercialMatrix.tsx:14`; `ValidationPage.tsx:98,123`; `App.css:436,446,479` | Legibilidade; Nielsen 7 |
| P17 | Médio | 4 | Vocabulário interno do projeto vaza para a interface: "Evidência da Semana 4" (menu), "Semana 4 · Aplicabilidade" (Validação), "snapshot anterior à Etapa 6" (Execuções), "…nesta etapa" (parceiro), "só ranking", "snapshots", "produto cartesiano" | `components.tsx:58`; `ValidationPage.tsx:85`; `RunComparisonView.tsx:21`; `PartnerDetailPage.tsx:30,34`; `RunsPage.tsx:45` | Linguagem; Nielsen 2 |
| P18 | Médio | 2 (`/skus/:sku`, `/`) | O score não é decomposto: `score_contributions` (peso de cada sinal) vem na API e não é exibido; "33" aparece sem a soma dos pesos, enquanto "Riscos e evidências" mostra a severidade, não o peso | `SkuDetailPage.tsx:43,65`; `types.ts:274` | Princípio 1 (reforço); interpretação |
| P19 | Médio | 2 (`/skus/:sku`, parceiro) | "Riscos e evidências" e a evidência comercial mostram chaves técnicas: "average occupation 0.9325", "threshold", "available capacity average", "delay days", "sell out visibility", e "Origem: Capacidade_Semanal.Ocupação · config.rule_thresholds…". Método comercial lista `reposition_coverage_days` etc. em inglês | `SkuDetailPage.tsx:65`; `CommercialMatrix.tsx:35` | Linguagem; consistência |
| P20 | Médio | 1 | Formulário de decisão: "Efeito do dado do parceiro" e "Ação tomada" não dizem o que se decide; select só com os 41 SKUs priorizados (9 ficam de fora); rótulo "Opcional" a 8 px; `/casos` tem um botão "+ Novo caso" que só rola para um formulário já visível na mesma tela | `FeedbackPage.tsx:30-37`; `CasesPage.tsx:26,29` | Ações; Nielsen 2, 5 |
| P21 | Médio | 13 | "Última carga: 05/10/2026, 21:45:55 (Brasília)" em toda página é a hora do navegador. A data que importa para o negócio ("dados até 08/2026") só aparece em `/parceiros`, no rodapé da Validação e nas evidências | `components.tsx:106`; `ValidationPage.tsx:172` | Interpretação; Nielsen 1 |
| P22 | Médio | 1 | `/qualidade` ocupa a tela com 12 linhas, todas "Íntegra", e usa os nomes da planilha ("Carteira Pedidos", "Ordens Producao", "Sell In") | `QualityPage.tsx:11` | Densidade; linguagem |
| P23 | Médio | 1 (`/casos`) | Casos só podem ser criados: `PUT /api/cases/{id}` e o histórico existem e não são usados; "concluídos" nunca muda; `action` e `note` do caso não são exibidos. (Lacuna funcional: **fora do escopo da Fase 2**; registrar para o roadmap) | `CasesPage.tsx:26-29`; `api.ts:97` | Controle do usuário (Nielsen 3) |
| P24 | Baixo | 1 | `/cenarios`: o texto diz "Teste pesos", mas só 2 de 7 pesos são ajustáveis; painel escuro ocupa metade da largura para repetir "nenhuma alteração é persistida"; "Oficial: 3" a 9,5 px | `ScenariosPage.tsx:15-16`; `App.css:212-217` | Consistência; legibilidade |
| P25 | Baixo | 1 | `/execucoes` com uma execução mostra o cartão "Comparar execuções" com estado vazio e o selo técnico "só ranking" | `RunsPage.tsx:33-42,45` | Linguagem; Nielsen 8 |
| P26 | Baixo | 3 (`/prioridades`, `/parceiros`, `/skus/:sku`) | Defeitos visuais: ícone de busca sobre o placeholder em `/prioridades`; nome e código do parceiro colados no cartão ("Casa das IdeiasKA-05 · Distribuidor"); selo de confiança esticado na largura toda no resumo do SKU; "20% observado" idêntico em 5 cartões | `PrioritiesPage.tsx:28`; `B2BPage.tsx:28`; `SkuDetailPage.tsx:43` | Acabamento |

### 5.2 Avaliação pelas 10 heurísticas de Nielsen

| # | Heurística | Situação | Problemas |
|---|---|---|---|
| 1 | Visibilidade do estado do sistema | Bom: "Dados carregados", "Falha na consulta", skeletons, foco no título. Falha: a hora da carga destaca-se mais que a referência dos dados | P21 |
| 2 | Correspondência com o mundo real | Fraca: WAPE, baseline, holdout, backtest, sell-in/out, lead time e vocabulário de projeto (Semana 4, Etapa 6, snapshot) | P01, P05, P17, P19 |
| 3 | Controle e liberdade do usuário | Parcial: filtros na URL e "Limpar filtros" são bons; casos não podem ser atualizados; sem atalho para voltar a uma lista de oportunidades | P08, P09, P23 |
| 4 | Consistência e padrões | Fraca: três "confianças", duas "previsões", menu ≠ título, formatos de data e percentual | P04, P12, P13 |
| 5 | Prevenção de erros | Parcial: formulários validam no servidor; o "motivo principal" induz a erro; campo de decisão sem contexto | P01, P20 |
| 6 | Reconhecer em vez de lembrar | Parcial: 11 itens de menu; legibilidade baixa de rótulos de 8,5–11 px | P10, P14 |
| 7 | Flexibilidade e eficiência | Fraca para tarefas frequentes: 7 cliques para uma oportunidade; decisão sem pré-preenchimento | P02, P08, P09 |
| 8 | Estética e design minimalista | Fraca: 5–7 avisos por tela, 11 colunas, 58 badges na Validação | P03, P06, P11, P15, P22 |
| 9 | Ajudar a reconhecer e corrigir erros | Bom: mensagens de erro traduzidas (`api.ts`), "Tentar novamente"; erros de formulário em português | — |
| 10 | Ajuda e documentação | Existe o Guia (offline), mas o glossário é curto e não está no ponto de uso | P05 |

### 5.3 Pontos positivos a preservar

Evidências a no máximo 1 clique (SKU → "Riscos e evidências"; matriz → `<details>`); "Dado ausente" distinto de zero ("Não disponível", "Sem período comparável", "Dados insuficientes"); separação visual "informado / recalculado / meta"; falhas visíveis na Validação; filtros e comparações compartilháveis pela URL; Guia que funciona sem API; foco e rótulos de acessibilidade (zero violações no teste do axe).

---

## 6. Propostas (E)

Tipos: REMOVER, FUNDIR, REBAIXAR (para detalhe, aba ou "ver mais"), RENOMEAR, REESCREVER (linguagem simples), REFORMATAR (número, unidade, cor), REORDENAR. **Todas só mexem em apresentação e navegação** (princípio 5). Esforço: P (até 2 h), M (2–6 h), G (mais de 6 h). A coluna "Decisão do grupo" fica vazia: aprovar, recusar ou ajustar.

| ID | Tipo | Rota · elemento | Problema | Solução | Princípio afetado e como é preservado | Esforço | Impacto | Decisão do grupo |
|---|---|---|---|---|---|---|---|---|
| E01 | REORDENAR | `/`, `/prioridades`, `/cenarios` · "Motivo principal" e frase do cartão do 1º da fila (`components.tsx:182`, `OverviewPage.tsx:15`) | P01: mostra o 1º sinal alfabético | Exibir como principal o sinal de maior peso (pesos de `/api/config`, já carregável) e ordenar os badges por peso decrescente; a frase usa a descrição desse sinal. Alternativa: campo aditivo `main_reason` no backend | 5: não muda score, ranking nem regras, só a ordem de exibição. 1: todos os sinais continuam (+N sinais) e no detalhe | P (M se for campo no backend) | Alto | Aprovado |
| E02 | REORDENAR | `/previsoes` · tabela (`ForecastsPage.tsx:94`) | P02: ação e quantidade fora da tela | Colocar "Ação sugerida" e "Quantidade" logo após SKU; fixar a coluna SKU; tornar o SKU um link para o detalhe, sem depender do botão do fim da linha | 1: o detalhe fica a 1 clique, sem rolagem horizontal | P | Alto | Aprovado |
| E03 | REBAIXAR | `/previsoes` · colunas Tendência, "3 meses", Modelo/WAPE, Capacidade | P02, P06: 11 colunas | Manter 6 (SKU, Prioridade, Ação, Quantidade, Próximo mês, Confiança da previsão); mover as demais para a linha expandida ("Ver cálculo") | 1: evidências a 1 clique na própria linha; 3: "Dados insuficientes" continua explícito | M | Alto | Aprovado |
| E04 | REORDENAR | `/skus/:sku` · ordem das seções (`SkuDetailPage.tsx:43-65`) | P02: ação a 1,7–2,7 telas | Ordem nova: título, **resposta em uma frase** ("Produzir 400 un. após validar capacidade"), quantidade e confiança, botões de ação (E26), depois blocos recolhidos "Por quê" (cálculo), "Dados do SKU", "Riscos e evidências", "Parceiros". O bloco do cálculo abre por padrão | 1: evidências a 1 clique; 2: revisão humana dita uma vez no cartão da ação | M | Alto | Aprovado |
| E05 | FUNDIR | `/skus/:sku`, `/previsoes`, `/` · três selos "Confiança" | P04 | Dois rótulos fixos em todo o app: "Confiança nos dados do SKU" (ranking) e "Confiança na previsão". Remover o terceiro selo (recomendação) do cabeçalho do bloco e deixar o motivo em uma linha | 3: continua visível por que a confiança é baixa (`confidence_reason`) | M | Alto | Aprovado |
| E06 | RENOMEAR | `/skus/:sku` · "Forecast disponível" e "Próximos 3 meses" | P04 | "Previsão comercial (planilha)" e "Previsão do modelo (3 meses)", cada uma com selo "previsto" | 3: previsto, estimado e observado distinguíveis | P | Médio | Aprovado |
| E07 | FUNDIR | todas · avisos (`components.tsx:93,131`; `ForecastsPage.tsx:74-75`; `SkuDetailPage.tsx:40-41,61`) | P03 | Uma única linha fixa sob o título: "Apoio à decisão: toda sugestão exige revisão humana e não é ordem de produção" com "?" para o Guia. Remover `DecisionBoundary` e "Revisão humana obrigatória" das 4 rotas; manter só avisos de exceção (ex.: "Sem ação necessária… não significa sem risco") e uma linha dentro do cartão da ação. Legenda da tabela passa a `sr-only` | 2: dito uma vez, no lugar certo (cabeçalho + cartão da ação) | M | Alto | Aprovado |
| E08 | REESCREVER | todas · termos técnicos | P05 | Aplicar o glossário da seção 7.4 com "?" no primeiro uso por tela; trocar "backtest" por "teste nos últimos 3 meses" em todo o app | 4: o termo técnico continua no "?" e na Validação | M | Alto | Aprovado |
| E10 | REMOVER | todas · eyebrow e kicker (`components.tsx:98-110,135`) | P13 | Remover o eyebrow; manter o `h1` da barra como título; o `h2` do cabeçalho vira a **frase de resposta** da página | acessibilidade preservada (h1 único) | M | Médio | Aprovado |
| E11 | RENOMEAR | menu e títulos | P13 | Nome único por página (seção 7.1): ex.: "Parceiros" no menu e no título | — | P | Médio | Aprovado |
| E12 | FUNDIR | menu (`components.tsx:47-59`) | P14: 11 itens planos | 6 entradas + Ajuda (seção 7.1); URLs antigas continuam válidas | deep links preservados | M | Alto | Aprovado |
| E13 | REBAIXAR | `/prioridades` · colunas "Data crítica" e "Lacuna operacional" | P06: lacuna = 0 em 36 de 41 linhas | Levar as duas para a linha expandida; manter Posição, SKU, Motivo (E01), Confiança, Score | 1: abrir a linha mostra tudo + "Abrir SKU" | M | Médio | Aprovado |
| E14 | REORDENAR | `/` · seções 02 e 03 (`OverviewPage.tsx:26-45`) | P03, P06, P15 | Topo: frase ("CI-0041 é o primeiro: abaixo da segurança e produção 25 dias após a promessa"), 4 números com contexto (41 de 50; 16 em risco; 12 pedidos sem OP; 20 de 41 com confiança baixa), botão "Abrir CI-0041". Remover os atalhos que repetem o menu (parceiros, qualidade); mover "Qualidade da decisão" e as barras de sinais para uma seção recolhida "Detalhes" | 1: fila e evidências a 1 clique; 3: cobertura 20% (50 de 250) continua visível | M | Alto | Aprovado |
| E15 | REBAIXAR | matriz (`CommercialMatrix.tsx:14,23-34`) | P07 | Reduzir a 5 colunas: Parceiro/SKU, **Ação comercial**, Estoque estimado, Cobertura (dias), Giro mensal. Sell-in/out, diferença, carteira e meses vão para a linha expandida, que substitui os `<details>` soltos | 1: evidência na própria linha; 3: "estimado" e "Sem período comparável" mantidos | G | Alto | Aprovado |
| E16 | REORDENAR | matriz no celular | P16 | Cartões de 4 campos (padrão de Previsões) com "Ver evidências" | idem | M | Médio | Aprovado |
| E17 | FUNDIR | `/parceiros` · cartões e ordenação (`B2BPage.tsx:14,25,28`) | P09 | Ordem padrão por oportunidades; frase "5 parceiros com 12 oportunidades de reposição"; aba "Oportunidades" com lista única (`/api/commercial-recommendations?action=avaliar_reposicao`): Parceiro, SKU, Estoque, Cobertura, Giro; clique expande a evidência | 1: evidência a 1 clique; 3: canais sem sell-out seguem "Dados insuficientes" | G | Alto | Aprovado |
| E18 | REBAIXAR | `/parceiros` · cartões e avisos | P06, P26 | Cartões viram linhas (Parceiro, Região · Canal, Cobertura, Oportunidades, Sem dados); estatísticas finas ("vínculos reais", "último sell-out") vão para o detalhe; corrigir o espaçamento nome/código; "Pares com sell-out… não SKUs distintos" → "Combinações parceiro–SKU com venda informada" | 3 | M | Médio | Aprovado |
| E19 | REFORMATAR | todas · números | P12 | Padrão da seção 7.3 (percentual, unidade, ausente, data) | 3: "Não disponível" nunca vira 0 | M | Médio | Aprovado |
| E20 | REFORMATAR | `/skus/:sku`, parceiro · textos de `rationale` e `recommendation_reason` | P12 | Formatar números em pt-BR e arredondar ("1.246 un.", "26 dias"): no cliente ou com campo aditivo `*_display` | 5: mesmo valor, outra grafia; revisar testes de texto do pytest | M | Médio | Aprovado |
| E21 | REESCREVER | `/skus/:sku` · "Riscos e evidências" (`SkuDetailPage.tsx:65`) | P19 | Dicionário de rótulos: "Ocupação média da família 93,3% (limite 90%)", "Atraso 25 dias", "Cobertura 6 dias (prazo de produção 21 dias)"; "Origem" em "Planilha: aba Capacidade_Semanal" | 1: mesmos valores, agora legíveis | M | Médio | Aprovado |
| E22 | REFORMATAR | badges · cores | P13 | Cores semânticas (7.3): vermelho só para risco crítico/alto; ações (Produzir, Investigar) em azul; "sem dado" em cinza | 3: ausente em cinza com texto | P | Médio | Aprovado |
| E23 | REBAIXAR | `/validacao` (`ValidationPage.tsx:90-171`) | P11 | Veredito em uma frase + os 4 cartões no topo; abas "Processo atual", "Modelos", "Casos", "Segurança e falhas". Casos viram linhas recolhidas (título + resultado), **abertos por padrão se falharam ou não foram encontrados** | 4: "16 de 50" e a lista de falhas ficam na aba inicial; nada é removido | G | Alto | Aprovado |
| E24 | REESCREVER | `/validacao` · cartões | P05, P11 | "Erro médio da previsão 6,9% (previsão simples: 8,0%)"; "Modelo não foi melhor em 16 de 50 SKUs"; seta/cor indicando bom ou ruim | 4 | P | Alto | Aprovado |
| E26 | REORDENAR | `/skus/:sku` → `/decisoes`, `/casos` | P08, P20 | Botões "Registrar decisão" e "Criar caso" no SKU, levando a `?sku=` com o SKU preenchido (aceitar também SKUs fora do ranking) | 2: a decisão continua humana e explícita | M | Alto | Aprovado |
| E27 | REESCREVER | `/decisoes` · rótulos (`FeedbackPage.tsx:30-37`) | P20 | "O que você decidiu?" (Aceitei a sugestão, Ajustei, Rejeitei, Vou investigar); "O dado do parceiro ajudou?" (Não usei, Confirmou minha análise, Aumentou minha confiança, Mudou minha decisão); tempo: "Minutos gastos (opcional)". **Valores enviados não mudam** | contratos preservados | P | Médio | Aprovado |
| E28 | FUNDIR | `/casos` + `/decisoes` | P20 | Mesma entrada de menu, duas abas; remover o botão "+ Novo caso" (`CasesPage.tsx:26`) | rotas preservadas | M | Médio | Aprovado |
| E29 | REBAIXAR | `/qualidade` (`QualityPage.tsx:11`) | P22 | "12 de 12 abas íntegras" + "Ver abas" (abre sozinho se houver "Revisar"); nomes legíveis; "Chaves órfãs" → "Registros sem vínculo" | 3 | P | Baixo | Aprovado |
| E30 | REBAIXAR | `/cenarios`, `/execucoes` | P24, P25 | Grupo "Avançado"; cenários: "Simular 2 pesos" e remover o painel escuro; execuções: ocultar "Comparar" até haver 2; "só ranking" → "sem previsão e parceiros" | — | P | Baixo | Aprovado |
| E31 | REESCREVER | menu, Validação, Execuções, parceiro | P17 | "Evidência da Semana 4" → "Confiança nas recomendações"; remover "Semana 4 · Aplicabilidade", "Etapa 6", "nesta etapa" | — | P | Médio | Aprovado |
| E32 | REFORMATAR | `App.css` | P10 | Piso de 12 px para texto visível (exceto `sr-only`); rótulos em caixa baixa; revisar quebras de layout | contraste mantido (`contrast.test.ts`) | M | Alto | Aprovado |
| E33 | REFORMATAR | celular · `/prioridades`, `/previsoes` | P16, P02 | Prioridades em cartões de 4 campos; Previsões com 10 cartões + "Ver mais" (hoje 18.727 px) | 1 | M | Alto | Aprovado |
| E34 | REMOVER | cartões redundantes (`ForecastsPage.tsx:77-80`, `OverviewPage.tsx:38-42`, `QualityPage.tsx:10`) | P15 | Remover "SKUs previstos 50/50"; juntar "Decisões" e "Influenciadas" numa linha; "Investigar dados" só se > 0; "Erros/Chaves órfãs" viram um selo "Sem erros"; todo cartão com "de N" e sentido | 3 | P | Médio | Aprovado |
| E35 | REFORMATAR | barra superior (`components.tsx:106`) | P21 | "Dados até 08/2026 · carregado às 21:45" onde o mês de referência existir; sem segundos | 3 | P | Baixo | Aprovado |
| E36 | REFORMATAR | `/skus/:sku` · resumo | P18 | "Score 33 = 10 + 8 + 8 + 5 + 2" com `score_contributions` | 1 reforçado | P | Médio | Aprovado |
| E37 | REMOVER | duplicatas de definição de cobertura (`OverviewPage.tsx:43`, `QualityPage.tsx:12`, `B2BPage.tsx:23`) | P03 | Uma definição no "?" do número "Cobertura de sell-out" | 3 | P | Médio | Aprovado |
| E38 | REFORMATAR | `/prioridades`, `/parceiros`, `/skus` | P26 | Corrigir ícone de busca, espaçamento do cartão, selo esticado | — | P | Baixo | Aprovado |
| E39 | REESCREVER | `/guia` | P05 | Trocar os 10 cartões que repetem o menu por 3 trilhas (PCP, Comercial, Gestão); completar o glossário; levar o roteiro de 5 min para `docs` | — | M | Médio | Aprovado |
| E41 | REBAIXAR | `/previsoes` · filtros (`ForecastsPage.tsx:82-91`) | P06 | Visíveis: busca, Ação e "Só o que exige atenção"; o resto em "Mais filtros" (URL inalterada) | deep links preservados | P | Médio | Aprovado |
| E43 | REBAIXAR | `/parceiros/:codigo` · aviso de atribuição (`PartnerDetailPage.tsx:34`) | P03, P17 | Mover para "Limitações" recolhido; remover "nesta etapa" | 2 | P | Baixo | Aprovado |

---

## 7. Arquitetura de informação, padrões e glossário propostos

### 7.1 Menu (de 11 para 6 entradas + Ajuda)

| Entrada | Quem | Reúne (rotas continuam válidas) | Justificativa |
|---|---|---|---|
| **Início** | todos | `/` | Responde "o que olhar primeiro" |
| **Produção** | PCP | `/prioridades`, `/previsoes`, `/skus/:sku` (abas "Fila de atenção" e "Previsão e ação") | Mesma tarefa: decidir o que produzir |
| **Parceiros** | Comercial | `/parceiros`, `/parceiros/:codigo` (abas "Oportunidades" e "Parceiros") | Hoje chamada "Visibilidade B2B2C" |
| **Confiança** | gestão | `/validacao`, `/qualidade` | Duas respostas à mesma pergunta |
| **Decisões** | PCP | `/decisoes`, `/casos` | Registro e acompanhamento |
| **Avançado** | analista | `/cenarios`, `/execucoes` | Uso esporádico |
| **Ajuda** (ícone "?" na barra) | novatos | `/guia` | Sai do menu, continua offline |

### 7.2 Padrão de página

```text
[Título]                                   [Regra de uso fixa, 1 linha]
Resposta principal em UMA frase
  "CI-0014: produzir 400 un. após validar capacidade."
Até 4 números, cada um com unidade, referência e sentido
  [400 un. sugeridas] [Demanda a cobrir 1.327 un.] [Confiança na previsão: alta] [Capacidade: validar]
Ação principal           [Registrar decisão] [Criar caso]
▸ Por quê (cálculo)  ▸ Evidências  ▸ Dados e limitações   (recolhidos; o cálculo abre)
```

Regras: nada além da resposta, dos 4 números e da ação na primeira dobra (1440×900 e 375×812); toda evidência a 1 clique; avisos de exceção só onde mudam a leitura.

### 7.3 Padrão de números

| Tipo | Formato | Exemplo | Regra |
|---|---|---|---|
| Quantidade | milhar com ponto, 0 casas, unidade | 1.327 un. | decimais só em demanda prevista < 100 |
| Percentual de cobertura | 0 casas | 20% | sempre com "de N" quando for contagem (50 de 250) |
| Percentual de erro | 1 casa fixa | 6,9% · 8,0% | nunca cortar o zero final |
| Dias | 0 casas + "dias" | 26 dias | cobertura e prazo |
| Data | `dd/mm/aaaa`; mês `mm/aaaa` | 13/09/2026 | um único formato |
| Ausente | "Não disponível" | — | nunca "0", "—" ou vazio; zero só quando observado |
| Natureza | selo "observado", "estimado", "previsto" | | 3: sempre distinguíveis |
| Cor | verde = favorável, âmbar = atenção, vermelho = risco crítico/alto, azul = ação/informação, cinza = ausente | | texto sempre acompanha a cor |

### 7.4 Glossário (linguagem simples)

| Termo técnico | Versão simples | Onde |
|---|---|---|
| Score / pontuação de atenção | Pontos de atenção: soma dos pesos dos problemas encontrados | tooltip no score |
| WAPE | Erro médio da previsão (quanto, em %, a previsão errou nos últimos 3 meses) | tooltip |
| Baseline | Previsão simples de comparação (repete o último mês) | tooltip |
| Holdout / backtest | Teste nos últimos 3 meses | texto |
| Sell-in | Vendido ao parceiro | rótulo |
| Sell-out | Vendido pelo parceiro ao consumidor | rótulo |
| Lead time | Prazo de produção (dias) | rótulo |
| Cobertura (dias) | Por quantos dias o estoque dura no ritmo atual | tooltip |
| OP | Ordem de produção | primeira ocorrência |
| Caso congelado | Exemplo de teste fixado antes de medir | Validação |
| Chaves órfãs | Registros sem vínculo com o cadastro | Qualidade |
| Dado ausente | Informação que não existe na planilha (não é zero) | tooltip |

### 7.5 Onde entram as funcionalidades planejadas sem aumentar a densidade

| Funcionalidade | Onde | Como |
|---|---|---|
| Matriz de decisão parceiro × SKU | Parceiros → aba "Matriz" | Só vínculos reais (95 de 400 combinações); padrão = exceções (ação ≠ monitorar); uma ação por célula; clique expande a evidência existente |
| Viabilidade operacional ao lado da recomendação comercial | linha expandida da oportunidade | Uma linha "Pode atender? Estoque do CD 1.490 · produção aberta 0 · capacidade: validar" com link ao SKU; dados globais **não** são distribuídos entre parceiros |
| Faturamento previsto | número no cabeçalho de Parceiros e linha expandida | Selo "previsto"; exige expor `Valor faturado (R$)`, hoje ausente da API (campo aditivo) |
| Região e canal | Parceiros → alternador "Agrupar por região / canal" | Os filtros já existem; vira agrupamento com subtotais, sem página nova |

---

## 8. Riscos

**Testes que precisarão mudar** (`frontend/src`):
- `test/routes.test.tsx`: lista de rotas com rótulo do menu e `h2` esperados (E10–E12, E31); link "Visibilidade B2B2C" com `aria-current`.
- `test/keyboard.test.tsx` e `test/a11y.test.tsx`: títulos `h1`/`h2`, ordem de foco, nomes de região de tabela (E02, E10, E15).
- `test/filters-states.test.tsx`: textos "Revisão humana obrigatória", "Dados insuficientes", colunas da tabela de Previsões (E03, E07).
- `test/fixtures.ts` e `contract-keys.json`: se `main_reason` ou `*_display` forem adicionados (campos aditivos).
- `test/contrast.test.ts`: acrescentar verificação do piso de 12 px (E32).
- Scripts (`frontend/scripts`): `test-decision-journey.mjs` verifica "Prioridade de análise não é ordem de produção", os atalhos da Visão geral e o texto da cobertura (E07, E14, E37); `test-validation-page.mjs` verifica "Não superou a baseline em 1 de 2" e rótulos da Validação (E23, E24); `test-page-data.mjs` não deve mudar.

**Contratos que não podem mudar:** todos os endpoints e campos de `docs/api.md`; valores enviados em `POST /api/feedback` e `POST /api/cases` (E27 muda só rótulos); parâmetros de URL dos filtros (`busca`, `familia`, `acao`, `confianca`, `tendencia`, `atencao`, `ordem`, `regiao`, `canal`, `sku`, `qualidade`, `offset`, `base`, `alvo`); rotas existentes (deep links); Guia offline; `pytest` de contrato (`tests/test_frontend_contracts.py`). Qualquer campo novo deve ser aditivo e documentado.

**Roteiro de demonstração afetado** (`docs/roteiro-demonstracao.md`): ordem das abas (menu agrupado); "só 20% dos pares" citado em `/validacao` (corrigir a tela de origem); "271" e "8,0%" (E19, E20); posição de "Avaliar reposição" e evidências (E15, E17); "Comportamento seguro" em aba (E23); atalho "Abrir evidências de CI-0041" (E14).

**Outros riscos:** E01 muda o motivo exibido em 27 de 41 SKUs (comunicar ao grupo); E20 pode afetar testes de texto do backend; E23 e E15 são os maiores esforços; E32 pode quebrar layouts em 375 px.

---

## 9. Apêndice — rascunho do prompt da Fase 2

````text
Você vai CORRIGIR a usabilidade do Caderno Inteligente aplicando SOMENTE as propostas aprovadas em docs/mapeamento-usabilidade.md (coluna "Decisão do grupo" = aprovar ou ajustar). Leia o mapeamento inteiro antes de começar.

## Propostas aprovadas, nesta ordem
Sugestão de ordem por grupo, quando aprovadas: (1) E01, E22, E38; (2) E02–E06, E36, E21; (3) E07, E10–E12, E31; (4) E14, E34, E37; (5) E15–E18; (6) E23, E24; (7) E26–E28; (8) E08, E19, E20, E32, E33, E39.

## Arquitetura de informação aprovada
Decisão do grupo: aprovada (proposta: seção 7.1; rotas existentes que deixarem o menu continuam funcionando por URL; não quebre deep links.)

## Padrões aprovados
Decisão do grupo: aprovada (padrão de página 7.2, de números 7.3 e glossário 7.4)

## Restrições
1. Não altere cálculos, score, ranking, regras, previsão, recomendação, processamento do Excel ou contratos da API. Se precisar de um campo novo para a interface, ele deve ser ADITIVO e documentado em docs/api.md.
2. Preserve os princípios: evidências a no máximo 1 clique; revisão humana clara (dita uma vez, no lugar certo); dado ausente nunca como zero; observado, estimado e previsto distinguíveis; falhas visíveis na Validação (inclusive "16 de 50").
3. Mantenha o Guia funcionando sem API, os deep links, os filtros na URL, o modo demonstração e o modo somente leitura.
4. Acessibilidade: zero violações do axe (frontend/src/test/a11y.test.tsx), contraste AA e textos com no mínimo 12px, exceto rótulos auxiliares justificados.
5. Testes: atualize os testes afetados (frontend/src/test, frontend/scripts e frontend/src/test/contract-keys.json; ver seção 8 do mapeamento). Não apague um teste sem substituí-lo por um equivalente.
6. Atualize docs/roteiro-demonstracao.md e o Guia de uso se a navegação mudar.

## Entrega
- Implemente em passos pequenos, um grupo de propostas por vez, rodando npm run check ao final de cada grupo.
- Ao final, rode os testes Python (.venv/Scripts/python.exe -m pytest -p no:cacheprovider) e npm run check.
- Verifique no navegador, em 375×812 e 1440×900, as rotas alteradas e os 6 fluxos de tarefa do mapeamento (seção 4). Registre os cliques antes × depois.
- Crie docs/etapa-usabilidade.md com: propostas aplicadas, propostas não aplicadas e o motivo, capturas antes × depois, fluxos antes × depois, arquivos modificados, resultados dos testes, limitações e passos de deploy.
- Não altere segredos e não faça deploy.
````
