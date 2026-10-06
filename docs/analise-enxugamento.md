# Análise de enxugamento — o que cortar para o sistema ficar fácil de ler

> **Status:** análise sem alteração de código, testes, estilos ou configuração. Arquivos novos: este documento e as capturas de página inteira em [`analise-enxugamento/`](analise-enxugamento/).
> **Data da medição:** 06/10/2026 · API local · planilha de demonstração (SHA-256 `03fa0ed4…803f`, referência de vendas 08/2026) · desktop 1440×900, **página inteira com tudo expandido** (`<details>` abertos, abas abertas, "Ver mais" e "Ver evidências" clicados). Só leituras (`GET`); nenhum formulário foi enviado.
> **Régua:** o que conta é o volume total de cada tela, não a primeira dobra. Texto em bloco recolhido conta como texto existente.

## 1. Resumo executivo

O sistema tem **20.524 palavras e 2.226 números** nas 15 telas medidas (tudo expandido). A Fase 2 reorganizou, mas pouco cortou: mais de 80% do volume está em apenas 6 telas, e o grosso é **repetição** (a mesma evidência por linha, o mesmo detalhe em cada linha de uma lista), não informação nova.

**As 5 telas mais pesadas:** detalhe do parceiro (`/parceiros/KA-01`, 4.142 palavras), oportunidades (`/parceiros`, 3.873), previsão e ação (`/previsoes`, 2.759), validação (2.473) e detalhe do SKU CI-0014 (1.760).

**As 5 maiores fontes de poluição:**
1. **Evidência completa repetida por linha** (≈250 palavras e uma tabela de 12 meses × 5 colunas por vínculo parceiro–SKU): ≈ 7.500 palavras nas telas de parceiros e no contexto do SKU.
2. **Detalhe recolhido dentro de cada linha de lista**: "Ver previsão e modelo" 50× (inclui 50 tooltips de WAPE) e "Ver sinais, data e lacuna" 41×: ≈ 2.600 palavras.
3. **Colunas e selos sem informação**: confiança da previsão "alta" em 50 de 50 SKUs; "Avaliar reposição" e "Suficiente no recorte" em 12 de 12 linhas da lista de oportunidades; "Íntegra" em 12 de 12 abas.
4. **Material de auditoria na tela de decisão**: casos congelados (1.151 palavras), histórico de ajustes (220), método comercial (352 palavras, 3 telas), hash e premissas genéricas.
5. **Frases que repetem o título ou o vizinho**: a descrição sob o título (12 a 32 palavras em todas as telas, ≈300 no total), a linha de regra em 14 telas, definições de cobertura, motivo do SKU dito duas vezes no cartão.

**Meta proposta (estimada):** de 20.524 para ≈ **3.700 palavras no estado padrão** e ≈ **6.900 com todas as evidências abertas** (≈ 8.600 contando a nova página de Auditoria), ou seja, **−58% a −66%** no mesmo critério "tudo expandido". Números: de 2.226 para ≈ 430 no estado padrão (≈ 1.400 com evidências abertas). A seção 4 traz o orçamento por tela e a seção 5, as cinco telas enxutas.

## 2. Medição por tela

**Metodologia.** Chrome headless (protocolo DevTools), 1440×900, uma rota por vez. Antes de medir: abrir todos os `<details>`, mostrar todos os painéis de aba, clicar em "Ver mais" até acabar e em todos os botões de evidência fechados. *Palavras* = palavras do texto visível de `.page-content` (menu lateral e barra superior à parte: ≈ 40 por tela). *Números* = sequências numéricas do texto visível, sem códigos (CI-0014, KA-01) e sem datas completas. *Blocos* = cartões, seções, alertas, tabelas, filtros, painéis e detalhes de primeiro nível. *Avisos* = alertas, linha de regra, caixas de revisão humana e notas. *Repetição* = frase de 4+ palavras que aparece 2+ vezes na mesma tela. Script e dados brutos: `volume.mjs` e `volume.json` (fora do repositório).

Ordenado da tela mais pesada para a mais leve:

| # | Tela | Palavras | Prosa | Tabelas | Números | Blocos | Avisos | Badges | Tooltips | Colunas | Altura (px) | Repetições |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `/parceiros/KA-01` | **4.142** | 550 | 3.592 | 538 | 24 | 2 | 14 | 0 | 6 + 14 tabelas de 5 | 14.398 | 19 |
| 2 | `/parceiros` · Oportunidades | **3.873** | 530 | 3.343 | 620 | 20 | 3 | 12 | 1 | 6 + 12 tabelas de 5 | 14.136 | 13 |
| 3 | `/previsoes` (50 SKUs) | **2.759** | 147 | 2.612 | 347 | 5 | 1 | 106 | 51 | 7 | 14.709 | 6 |
| 4 | `/validacao` (4 abas) | **2.473** | 2.088 | 385 | 190 | 28 | 3 | 58 | 3 | 5 / 6 / 5 | 6.504 | 11 |
| 5 | `/skus/CI-0014` | **1.760** | 987 | 773 | 157 | 13 | 7 | 10 | 6 | 6 + 3 de 5 | 6.642 | 13 |
| 6 | `/prioridades` (41 SKUs) | 1.668 | 86 | 1.582 | 154 | 3 | 1 | 174 | 2 | 6 | 11.051 | 5 |
| 7 | `/skus/CI-0041` | 1.612 | 1.207 | 405 | 66 | 16 | 8 | 12 | 6 | 6 + 2 de 5 | 5.972 | 18 |
| 8 | `/guia` | 915 | 915 | 0 | 8 | 3 | 1 | 1 | 0 | — | 3.027 | 0 |
| 9 | `/` Início | 363 | 261 | 102 | 33 | 11 | 2 | 16 | 3 | 6 | 1.829 | 4 |
| 10 | `/parceiros` · Parceiros | 331 | 135 | 196 | 44 | 6 | 2 | 0 | 1 | 6 | 1.627 | 2 |
| 11 | `/qualidade` | 187 | 110 | 77 | 44 | 6 | 2 | 12 | 1 | 5 | 1.348 | 0 |
| 12 | `/decisoes` | 158 | 158 | 0 | 0 | 2 | 1 | 0 | 0 | — | 1.124 | 0 |
| 13 | `/casos` | 133 | 111 | 22 | 9 | 3 | 1 | 2 | 0 | 5 | 990 | 0 |
| 14 | `/execucoes` | 82 | 82 | 0 | 10 | 1 | 2 | 2 | 0 | — | 900 | 0 |
| 15 | `/cenarios` | 68 | 68 | 0 | 6 | 1 | 1 | 0 | 0 | — | 900 | 0 |
| Aprovado | **Total** | **20.524** | Aprovado | | **2.226** | Aprovado | | Aprovado | | Aprovado | | Aprovado |

**Capturas de página inteira (1440 px, tudo expandido):** [Início](analise-enxugamento/inicio-1440.png) · [Fila de atenção](analise-enxugamento/prioridades-1440.png) · [Previsão e ação](analise-enxugamento/previsoes-1440.png) · [SKU CI-0014](analise-enxugamento/sku-ci-0014-1440.png) · [SKU CI-0041](analise-enxugamento/sku-ci-0041-1440.png) · [Oportunidades](analise-enxugamento/parceiros-oportunidades-1440.png) · [Parceiros](analise-enxugamento/parceiros-lista-1440.png) · [Detalhe do parceiro](analise-enxugamento/parceiro-ka-01-1440.png) · [Casos](analise-enxugamento/casos-1440.png) · [Qualidade](analise-enxugamento/qualidade-1440.png) · [Cenários](analise-enxugamento/cenarios-1440.png) · [Execuções](analise-enxugamento/execucoes-1440.png) · [Decisões](analise-enxugamento/decisoes-1440.png) · [Validação](analise-enxugamento/validacao-1440.png) · [Guia](analise-enxugamento/guia-1440.png). Imagens com mais de 9.000 px de altura estão cortadas em 9.000 px.

Leitura: o volume não está espalhado. As 6 primeiras telas têm 16.675 das 20.524 palavras (81%). A coluna "Tabelas" mostra que quase todo o peso é tabela repetida por linha (3.592 + 3.343 + 2.612 + 1.582 palavras). As telas de "decisão" simples (Casos, Decisões, Execuções, Cenários) já são enxutas.

**Repetições mais frequentes** (mesma tela): "Abaixo do estoque de segurança" 26× em `/prioridades` e 8× em Início; "Ver sinais, data e lacuna" 41×; "Ver previsão e modelo" 50× e "Erro médio da previsão (WAPE)" 50× em `/previsoes`; "Média móvel de 3 meses" 34× em `/previsoes`; "Vendido ao parceiro (sell-in)", "Vendido pelo parceiro (sell-out)", "Por que esta sugestão:" e "0 meses em relação à referência da base" 12× em Oportunidades e 14× em KA-01; "Lojas físicas e online" 14×.

**Informação que não varia (zero poder de decisão):** confiança da previsão = "alta" em 50/50 (`forecasts[].forecast.forecast_confidence`); tendência "estável" em 42/50; ação "Avaliar reposição" e qualidade "Suficiente no recorte" em 12/12 oportunidades; situação "Íntegra" em 12/12 abas; "Lacuna operacional" = 0 em 36 de 41 SKUs priorizados; "Dados antigos/descontínuos" = 0.

---

## 3. Inventário e classificação por tela

**Como ler.** Para cada tela: a *pergunta única* que ela deve responder e a lista de blocos de cima para baixo, com o volume atual (p = palavras, n = números, tudo expandido). **Ajuda?** diz se o bloco ajuda a responder a pergunta (sim, parcial, não). **Decisão:** MANTER, ENCURTAR, JUNTAR, MOVER ou APAGAR. Referências de linha são do estado atual do código. A coluna "Decisão do grupo" fica vazia (aprovar, recusar ou ajustar). Princípios: P1 evidência a 1 clique; P2 revisão humana dita uma vez; P3 ausente ≠ zero, observado/estimado/previsto distintos; P4 falhas visíveis na Validação; P5 sem mudar cálculo.

### 3.0 Em todas as telas (casca)

Pergunta: nenhuma; a casca só deve orientar e sumir.

| Bloco (arquivo:linha) | Hoje | Ajuda? | Decisão | Justificativa e risco | Decisão do grupo |
|---|---|---|---|---|---|
| Descrição de cada item do menu (`components.tsx:65-72`, `menuGroups`) | ≈24 p | não | APAGAR | O rótulo já diz ("Parceiros", "Confiança"); a descrição repete | Aprovado |
| Barra superior: "Dados carregados / Carregado às 09:48 (Brasília)" (`components.tsx:141-165`) | ≈12 p | parcial | ENCURTAR | "Atualizado às 09:48" + botão Atualizar. Botão Ajuda fica | Aprovado |
| Linha de regra "Apoio à decisão: toda sugestão exige revisão humana e não é ordem de produção. Ajuda" (`components.tsx:137`, `App.tsx`) | 15 p × 14 telas | só onde há sugestão | MOVER | Mostrar só em Início, Previsão e ação, SKU e Parceiros; apagar em Casos, Qualidade, Cenários, Execuções, Decisões, Validação, Guia. **P2:** continua dita onde a sugestão aparece | Aprovado |
| Abas do grupo (`components.tsx:125`) | 3–6 p | sim | MANTER | Substituem itens de menu | Aprovado |
| Descrição sob o título (`PageIntro`, `components.tsx:181`) | 12–32 p em 14 telas (≈300 p) | não | APAGAR | Repete o título. Exceção: onde a frase traz dado (Parceiros, Qualidade, Início) | Aprovado |

### 3.1 `/` Início — "Qual SKU olhar primeiro e por quê?" (363 p · 33 n)

| Bloco | Hoje | Ajuda? | Decisão | Justificativa e risco | Decisão do grupo |
|---|---|---|---|---|---|
| Descrição "O primeiro SKU da fila, o porquê…" (`OverviewPage.tsx:14`) | 17 p | não | APAGAR | Repete o título | Aprovado |
| Cartão do primeiro da fila (`OverviewPage.tsx:16-26`) | 67 p · 1 n | sim | ENCURTAR | A frase diz o motivo duas vezes ("Abaixo do estoque de segurança. Cobertura de estoque abaixo do estoque de segurança."). Ficar com 1 frase (motivo + produção 25 dias depois da promessa) e no máximo 3 sinais; 1 botão "Abrir CI-0041" (o link "Ver previsão e ação" sai: o SKU já mostra a ação). **P1** preservado | Aprovado |
| Cartão "SKUs na fila de atenção 41 de 50" (`:28`) | ≈14 p | não | APAGAR | Vira o título da fila: "Fila de atenção (41 de 50)" | Aprovado |
| Cartão "SKUs com risco de ruptura 16" (`:29`) | ≈26 p | sim | ENCURTAR | Detalhe de 20 palavras vira "15 abaixo do prazo de produção, 13 abaixo da segurança" | Aprovado |
| Cartão "Pedidos sem ordem de produção 12" (`:30`) | ≈14 p | sim | MANTER | Encurtar o detalhe a 4 palavras | Aprovado |
| Cartão "Com confiança baixa 20 de 41" (`:31`) | ≈14 p | sim | MANTER | Já tem denominador | Aprovado |
| Fila de atenção, 5 linhas × 6 colunas (`OverviewPage.tsx:33`) | 120 p · 16 n | sim | ENCURTAR | Tirar subtítulo e "+4 sinais"; colunas: posição, SKU e produto, motivo, pontos, confiança | Aprovado |
| "Detalhes" recolhido: cobertura de sell-out, decisões registradas, barras de 7 sinais (`:34-41`) | 87 p · 11 n | não | MOVER / APAGAR | Cobertura 20% → Confiança › Dados da planilha. Decisões registradas → Decisões. Barras de sinais: APAGAR (repetem a fila e o ranking) | Aprovado |

### 3.2 `/prioridades` — "Em que ordem analisar os SKUs?" (1.668 p · 154 n · 174 badges)

| Bloco | Hoje | Ajuda? | Decisão | Justificativa e risco | Decisão do grupo |
|---|---|---|---|---|---|
| Descrição (`PrioritiesPage.tsx:29`) | 28 p | não | APAGAR | Repete o título | Aprovado |
| Filtros: busca, família, confiança, contador (`:30-35`) | 18 p | sim | MANTER | 41 linhas justificam filtro | Aprovado |
| Subtítulo "Ranking oficial: Ordenado pela soma dos pesos…" (`:36`) | ≈20 p | não | APAGAR | Explicação do score fica no "?" do cabeçalho "Pontos" | Aprovado |
| Coluna "Posição" (`components.tsx:213`) | 41 n | sim | MANTER | Aprovado | |
| Coluna "SKU / Produto" com "produto · família" (`components.tsx:216`) | ≈250 p | parcial | ENCURTAR | Só o produto; a família já é filtro | Aprovado |
| Coluna "Motivo principal" + "+N sinais" (`components.tsx:218`) | ≈250 p | sim | ENCURTAR | Só o motivo; o "+N sinais" sai (os sinais estão no SKU, 1 clique). **P1** | Aprovado |
| **Detalhe por linha "Ver sinais, data e lacuna" (`components.tsx:220-229`)** | **41×, ≈1.150 p** | não | **APAGAR** | Repetido em cada linha; "Lacuna" é 0 em 36 de 41; sinais, data e lacuna vivem no SKU. **P1:** o botão › abre o SKU | Aprovado |
| Coluna "Pontos ?" | 41 n | sim | MANTER | Aprovado | |
| Coluna "Confiança nos dados ?" | 41 badges | sim | MANTER | Varia (baixa/média) | Aprovado |

### 3.3 `/previsoes` — "Preciso produzir? Quanto?" (2.759 p · 347 n · 106 badges · 51 tooltips)

| Bloco | Hoje | Ajuda? | Decisão | Justificativa e risco | Decisão do grupo |
|---|---|---|---|---|---|
| Descrição (`ForecastsPage.tsx:79`) | 20 p | não | APAGAR | Aprovado | |
| 2 cartões "Produção sugerida 14" e "Validar capacidade 6" (`:82-83`) | 29 p · 3 n | parcial | JUNTAR | Uma frase no lugar do título da lista: "14 SKUs para produzir · 6 com capacidade a validar" | Aprovado |
| Filtros: busca, ação, "Somente itens com atenção", contador (`:86-90`) | ≈30 p | sim | ENCURTAR | "Somente itens com atenção" vira o padrão da tela (24 de 50), com botão "Ver todos os 50" | Aprovado |
| "Mais filtros": família, confiança, tendência, ordenar (`:91-99`) | 40 p | parcial | ENCURTAR | Confiança (50/50 "alta") e tendência (42/50 "estável") não separam nada: APAGAR. Ficam família e ordenar | Aprovado |
| Coluna "SKU" com "produto · família" | ≈250 p | sim | ENCURTAR | Só o produto | Aprovado |
| Coluna "Ação operacional sugerida" + selo "Validar capacidade" | 50× | sim | MANTER | É a resposta. Selo de capacidade fica (segurança) | Aprovado |
| Coluna "Quantidade sugerida" + "Lote mínimo: 400" | 50× | parcial | ENCURTAR | Quantidade fica; "Lote mínimo" vai para o SKU (cálculo) | Aprovado |
| Coluna "Próximo mês" + "unidades previstas" | 50× | sim | ENCURTAR | Só o número; unidade no cabeçalho | Aprovado |
| Coluna "Confiança na previsão ?" (**"alta" em 50/50**) | 50 selos | não | APAGAR | Não discrimina. Se alguma vez for ≠ "alta", mostrar o selo só nessa linha. **P3:** continua no SKU | Aprovado |
| Coluna "Fila de atenção #n" | 50 n | parcial | APAGAR | A fila é outra tela; o botão "Ver detalhes" já abre o SKU, que mostra a posição | Aprovado |
| **Detalhe por linha "Ver previsão e modelo" (`:107-109`)**: tendência, 3 meses, modelo, WAPE ?, capacidade | **50×, ≈1.500 p, 50 tooltips** | não | **APAGAR** | Mesmo conteúdo no bloco "Por que esta quantidade" do SKU. **P1** preservado (1 clique no SKU) | Aprovado |
| Botão "Ver detalhes" (50×) | 100 p | sim | ENCURTAR | O SKU vira o link; um botão por linha sai | Aprovado |

### 3.4 `/skus/CI-0014` e `/skus/CI-0041` — "Preciso produzir este SKU? Quanto? Por quê?" (1.760 p e 1.612 p)

| Bloco | Hoje | Ajuda? | Decisão | Justificativa e risco | Decisão do grupo |
|---|---|---|---|---|---|
| Descrição "Posição 15… · produto · família" (`SkuDetailPage.tsx:83`) | 13 p | sim | MANTER | É o dado de contexto | Aprovado |
| Cartão de resposta: frase + justificativa + selos + botões (`:85-96`) | ≈70 p | sim | MANTER | É a resposta. A justificativa (1 frase, do backend) fica | Aprovado |
| 4 números do cartão: quantidade, previsão do próximo mês, confiança na previsão, confiança nos dados (`:97-104`) | ≈50 p · 7 n | parcial | ENCURTAR | Ficar com 3: quantidade, previsão do mês, confiança (dois selos juntos: "previsão alta · dados média") | Aprovado |
| "Revisão humana obrigatória" + texto (`:105`) | ≈20 p | parcial | ENCURTAR | Uma linha dentro do cartão ("Sugestão para revisão: não cria nem libera ordem de produção"). **P2:** este é o lugar certo no SKU | Aprovado |
| Aviso "Sem ação necessária… não significa sem risco" (`:107`, só CI-0041) | 29 p | sim | ENCURTAR | 1 frase de 12 palavras no próprio cartão ("Sem produção neste horizonte; os riscos abaixo continuam") | Aprovado |
| "Por que esta quantidade": linha de cálculo (`:112`) | ≈25 p · 4 n | sim | MANTER | É a evidência da quantidade. **P1** | Aprovado |
| … premissas genéricas (3 frases iguais em todo SKU) (`:113`) | ≈45 p | não | APAGAR | Texto fixo; vai para o Guia | Aprovado |
| … tendência, modelo, erro médio, previsão de 3 meses (`:115-120`) | ≈45 p · 8 n | parcial | ENCURTAR | Tendência e previsão de 3 meses; modelo e erro vão para uma linha pequena | Aprovado |
| … 3 mini-cartões dos meses previstos (`:121`) | ≈15 p · 3 n | não | APAGAR | O mês seguinte já está no cartão; total de 3 meses também | Aprovado |
| … limitação genérica da previsão (`:122`) | ≈20 p | não | APAGAR | Texto fixo; vai para o Guia | Aprovado |
| "Demanda e atendimento": 6 números + 2 datas + atraso (`:128-130`) | ≈75 p · 12 n | parcial | ENCURTAR | Ficar com estoque, carteira, produção aberta, cobertura em dias, prazo de produção e a frase "produção prevista 08/10, 25 dias depois da promessa". Sai: estoque projetado, lacuna (0 em 36 de 41) | Aprovado |
| "Canal e dados ausentes": sell-in, sell-out, diferença, parceiros, previsão comercial (`:131`) | ≈45 p · 5 n | parcial | ENCURTAR | Sell-out acumulado e "parceiros com sell-out" ficam; diferença sai. "Previsão comercial (planilha)" fica como linha com selo "previsto". **P3** | Aprovado |
| Caixa "Por que esta confiança nos dados?" (`:132`) | ≈15 p | não | APAGAR | Repete a explicação já dita no cartão | Aprovado |
| Caixa "Dados ausentes" + parágrafo (`:133`) | ≈20 p | sim | ENCURTAR | Uma linha: "Ausentes: sell-in, sell-out (não são zero)". **P3** | Aprovado |
| "Riscos e evidências": soma dos pontos (`:138`) | ≈25 p · 6 n | sim | MANTER | Reforça P1 | Aprovado |
| … cada sinal: severidade, nome, **descrição**, valores, origem (`:139`) | CI-0041: ≈300 p | parcial | ENCURTAR | Tirar a descrição (repete o nome) e encurtar "Origem: Planilha · aba … · coluna" para "Planilha: aba Capacidade Semanal". Ficam severidade, nome e valores | Aprovado |
| "Limitação conhecida" (`:140`) | ≈25 p | não | APAGAR | Texto fixo; Guia | Aprovado |
| Contexto dos parceiros: alerta comercial (`CommercialMatrix.tsx:52`) | 45 p | não | APAGAR | A regra do estoque do parceiro vira "estimado" no cabeçalho da coluna | Aprovado |
| … matriz do SKU (6 colunas) (`CommercialMatrix.tsx:53`) | ≈60 p/linha aberta | parcial | ENCURTAR | Colunas como em 3.6 | Aprovado |
| … "Método, natureza dos campos e limites" (`CommercialMatrix.tsx:71`) | 352 p | não | MOVER | Para a página de Auditoria | Aprovado |
| … evidência por vínculo (`CommercialMatrix.tsx:25-45`) | ≈250 p cada | sim | ENCURTAR | Ver 3.6 (≤ 90 p) | Aprovado |

### 3.5 `/parceiros` · Oportunidades — "Qual parceiro tem oportunidade de reposição?" (3.873 p · 620 n)

| Bloco | Hoje | Ajuda? | Decisão | Justificativa e risco | Decisão do grupo |
|---|---|---|---|---|---|
| Descrição com contagem (`B2BPage.tsx:39`) | 21 p | sim | MANTER | Traz dado: "5 de 8 parceiros têm sugestão (12 no total)" | Aprovado |
| 3 cartões (`:42-44`) | 34 p · 3 n | não | APAGAR | A frase acima já diz 12 e 5 de 8; "50 combinações" e "45 sem base" não ajudam esta decisão | Aprovado |
| Nota de cobertura "A cobertura usa só o sell-out registrado…" (`:46`) | 25 p | não | APAGAR | Está no "?" do sell-out. **P3** preservado | Aprovado |
| Filtros região e canal (`:47`) | 19 p | parcial | MANTER | Aprovado | |
| Abas Oportunidades / Parceiros (`:48`) | 4 p | sim | MANTER | Aprovado | |
| Alerta "Recomendação comercial, não operacional" (`CommercialMatrix.tsx:52`) | 45 p | não | APAGAR | A linha de regra cobre a revisão; o estoque do parceiro é "estimado" no cabeçalho | Aprovado |
| Colunas "Ação comercial" + selo de qualidade (12× "Avaliar reposição", 12× "Suficiente no recorte") | ≈60 p | não | APAGAR | Constantes nesta aba. Em outras listas, o selo só aparece quando ≠ "Suficiente". **P3** | Aprovado |
| Colunas parceiro/SKU, estoque estimado + "08/2026 · estimado", cobertura, giro (`CommercialMatrix.tsx:56-62`) | ≈20 p/linha | sim | ENCURTAR | Tirar "08/2026 · estimado" repetido 12×; cabeçalho "Estoque estimado" já diz | Aprovado |
| **Evidência por linha (`CommercialMatrix.tsx:25-45`)**: 5 números, motivo, escopo, sinais, atualidade, natureza, comparação, fórmula de cobertura, tabela de 12 meses × 5 colunas, pedidos, nota | **12×, ≈250 p** | sim | **ENCURTAR** | Ficar com: motivo (1 frase), 3 números (sell-in, sell-out, estoque) e tabela de 12 meses com 3 colunas (mês, enviado, vendido). Sai: escopo, sinais, atualidade, natureza, comparação, fórmula, nota. **P1 e P3** preservados (a natureza "estimado" vai no cabeçalho) | Aprovado |
| "Método, natureza dos campos e limites configurados" (`CommercialMatrix.tsx:71`) | 352 p · 10 n | não | MOVER | Página de Auditoria | Aprovado |

### 3.6 `/parceiros` · Parceiros (331 p) e `/parceiros/KA-01` (4.142 p · 538 n)

Pergunta do detalhe: "Quais SKUs deste parceiro pedem reposição ou atenção, e qual a evidência?"

| Bloco | Hoje | Ajuda? | Decisão | Justificativa e risco | Decisão do grupo |
|---|---|---|---|---|---|
| **Lista:** 3 cartões + nota (`B2BPage.tsx:42-46`) | ≈60 p | não | APAGAR | Igual a 3.5 | Aprovado |
| Lista: tabela de 6 colunas; "10 de 50 SKUs · último sell-out 08/2026" 8× (`B2BPage.tsx:51`) | ≈200 p | parcial | ENCURTAR | Cobertura só em % ; "último sell-out" sai (igual em todos) | Aprovado |
| **Detalhe:** 4 cartões (`PartnerDetailPage.tsx:30`) | 33 p · 4 n | parcial | JUNTAR | Uma linha sob o nome: "Cobertura 20% (10 de 50 SKUs) · 4 oportunidades · último sell-out 08/2026" | Aprovado |
| Detalhe: filtros SKU exato, ação, qualidade (`:31`) | 31 p | parcial | ENCURTAR | 14 linhas não precisam de filtro; manter só "Ação" e só quando houver > 25 vínculos | Aprovado |
| Alerta comercial (`CommercialMatrix.tsx:52`) | 45 p | não | APAGAR | Igual a 3.5 | Aprovado |
| Matriz (6 colunas) com selo "Suficiente no recorte" 14× e "Monitorar estoque do parceiro" 6× | ≈300 p | parcial | ENCURTAR | Colunas: parceiro/SKU, ação, estoque, cobertura (dias), giro; selo só se ≠ suficiente | Aprovado |
| **Evidência por linha, 14×** | ≈3.300 p | sim | ENCURTAR | Igual a 3.5 (≤ 90 p) | Aprovado |
| "Método…" (352 p) e "Limitações" (41 p) (`PartnerDetailPage.tsx:34`) | 393 p | não | MOVER | Auditoria | Aprovado |
| Paginação (`PartnerDetailPage.tsx:33`) | 5 p | parcial | ENCURTAR | Só aparece com mais de 50 vínculos | Aprovado |

### 3.7 `/validacao` — "Quanto posso confiar nessas recomendações?" (2.473 p · 190 n · 58 badges)

| Bloco | Hoje | Ajuda? | Decisão | Justificativa e risco | Decisão do grupo |
|---|---|---|---|---|---|
| Descrição (`ValidationPage.tsx:98`) | 24 p | não | APAGAR | Aprovado | |
| Resumo "Em resumo" (`:102`) | 62 p · 5 n | sim | ENCURTAR | 2 frases: "Em 16 de 50 SKUs o modelo não foi melhor do que repetir o último mês. Erro médio 6,9% contra 8,0%." | Aprovado |
| 4 cartões (`:108-111`) | 57 p · 13 n | parcial | ENCURTAR | Ficam 3: casos de teste 8/8; erro médio 6,9% (simples 8,0%); "pior em 16 de 50". "Comportamento seguro 7/7" vira 1 linha ("7 de 7 verificações passaram") | Aprovado |
| "Falhas conhecidas" (3 itens) (`:114`) | 79 p | sim | ENCURTAR | **P4:** fica visível. Os 2 itens sobre entradas sintéticas viram 1 linha ("2 casos usam entrada sintética") | Aprovado |
| Abas (`:118`) | 11 p | parcial | JUNTAR | Duas abas bastam: "Processo atual" e "Modelos". Casos e segurança saem para a Auditoria | Aprovado |
| Aba Processo: tabela de 5 colunas com "Observação" longa (`:121-133`) | 188 p · 10 n | sim | ENCURTAR | 4 colunas; observação vira "?" | Aprovado |
| Aba Processo: "Tempo de análise registrado" (5 números, nota) (`:134-145`) | 62 p · 4 n | não | ENCURTAR | Uma linha: "Tempo de análise: sem dados suficientes (0 de 20 decisões)". Ausente ≠ 0 (**P3**) | Aprovado |
| Aba Modelos: tabela de 6 colunas (`:147-160`) | 349 p · 52 n | parcial | ENCURTAR | 3 colunas: modelo, erro ponderado, SKUs em que foi melhor | Aprovado |
| Aba Modelos: faixa de 5 números + 3 limitações | ≈90 p | não | ENCURTAR | Só "melhor em 34, pior em 16 de 50"; limitações em 1 linha | Aprovado |
| Aba Modelos: lista dos 16 SKUs em que não superou (`:163`) | 171 p | sim | MANTER | **P4**; recolhida; 3 colunas (SKU, erro do modelo, erro simples) | Aprovado |
| **Aba Casos: 8 casos congelados (`:171-185`)** | **1.151 p · 91 n** | não | **MOVER** | Auditoria. Na Validação fica 1 linha "8 de 8 casos passaram" com link. **P4:** se algum falhar, entra em "Falhas conhecidas" | Aprovado |
| Aba Segurança: 8 verificações (`:187`), limitações permanentes (63 p), histórico de ajustes (220 p) | 457 p | não | MOVER | Auditoria | Aprovado |
| Rodapé: SHA-256, referência, geração (`:196`) | 14 p | não | MOVER | Auditoria | Aprovado |

### 3.8 `/guia`, `/qualidade`, `/casos`, `/cenarios`, `/execucoes`, `/decisoes`

| Tela · bloco | Hoje | Ajuda? | Decisão | Justificativa e risco | Decisão do grupo |
|---|---|---|---|---|---|
| **Guia** (915 p) — "Toda sugestão exige revisão humana" + 5 passos (`GuidePage.tsx:33`) | 83 p | não | APAGAR | Repete a linha de regra e as trilhas | Aprovado |
| Guia — trilhas PCP/Comercial/Gestão (`:43`) | 150 p | sim | MANTER | Aprovado | |
| Guia — glossário de 16 termos (`:46`) | 310 p | parcial | ENCURTAR | Só termos que aparecem nas telas após o corte, 1 frase de até 12 palavras cada | Aprovado |
| Guia — "O que este protótipo não faz" (5 itens) (`:47`) | 58 p | parcial | ENCURTAR | 3 itens | Aprovado |
| Guia — 8 perguntas frequentes (`:48`) | 275 p | parcial | ENCURTAR | 4 perguntas | Aprovado |
| **Qualidade** (187 p) — descrição + 3 cartões (registros avaliados 11.296, situação, cobertura) (`QualityPage.tsx:14-15`) | 56 p · 6 n | parcial | ENCURTAR | "Registros avaliados" não decide nada: APAGAR; ficam situação e cobertura | Aprovado |
| Qualidade — nota sobre dado ausente (`:16`) | 23 p | não | APAGAR | Está no "?" | Aprovado |
| Qualidade — tabela de 12 abas, **todas "Íntegra"** (`:17-19`) | 89 p · 38 n | não | APAGAR | Mostrar a tabela só quando houver aba com problema ("Revisar"). Hoje basta "12 de 12 abas íntegras". **P3:** a cobertura de sell-out (20%) continua | Aprovado |
| **Casos** (133 p) — descrição, 3 contadores, tabela, formulário (`CasesPage.tsx:31-34`) | 133 p | sim | ENCURTAR | Tirar descrição e subtítulos; contadores viram 1 linha | Aprovado |
| **Cenários** (68 p) — descrição + sliders (`ScenariosPage.tsx:15-16`) | 68 p | sim | ENCURTAR | Tirar descrição (27 p) e "Peso oficial" repetido | Aprovado |
| **Execuções** (82 p) — descrição + nota + histórico (`RunsPage.tsx:31-45`) | 82 p | sim | ENCURTAR | Tirar descrição; nota "São necessárias duas execuções" fica | Aprovado |
| **Decisões** (158 p) — descrição + formulário + histórico (`FeedbackPage.tsx:34-44`) | 158 p | sim | ENCURTAR | Tirar descrição e subtítulos ("Três respostas bastam…") | Aprovado |

### 3.9 Nova página: Auditoria (destino do que sai das telas de decisão)

Rota proposta: `/auditoria` (aba "Auditoria" no grupo Confiança). Recebe: casos congelados (1.151 p), verificações de comportamento seguro (≈170 p), limitações permanentes (63 p), histórico de ajustes (220 p), método e natureza dos campos comerciais (352 p), hash da planilha, referência e data de geração. Estimativa: ≈ 1.600 palavras. **Não é tela de decisão**: não tem orçamento de leitura rápida, mas também não aparece no fluxo. **P4:** qualquer falha ou caso não aprovado sobe para "Falhas conhecidas" na Validação.

---

## 4. Orçamento por tela

**Regra de contagem:** a mesma da medição (texto visível de `.page-content`, tudo expandido). O teto "tudo expandido" = palavras fixas + linhas × palavras por linha + evidências abertas × 90. **Evidência por item (linha de parceiro ou SKU aberta): no máximo 90 palavras e 40 números.** Tela de decisão: no máximo 250 palavras fixas, 12 números fixos, 6 blocos, tabelas de até 5 colunas e 1 aviso. A Auditoria é isolada e não tem teto de leitura rápida.

| Tela | Palavras fixas | Por linha | Evidência por item | Números fixos | Blocos | Colunas | Avisos | **Teto (tudo expandido)** | Hoje | Acima do teto |
|---|---|---|---|---|---|---|---|---|---|---|
| Início | 200 | 12 (5 linhas) | — | 16 | 5 | 5 | 1 | **200** | 363 | +163 (+82%) |
| Fila de atenção | 60 | 12 (41) | — | 6 | 3 | 5 | 0 | **550** | 1.668 | +1.118 (3,0×) |
| Previsão e ação | 80 | 13 (50) | — | 6 | 3 | 4 | 0 | **730** (24 linhas por padrão: 390) | 2.759 | +2.029 (3,8×) |
| SKU CI-0014 | 340 | 14 (3 vínculos) | 90 | 35 | 5 | 5 | 1 | **670** | 1.760 | +1.090 (2,6×) |
| SKU CI-0041 | 340 | 14 (2 vínculos) | 90 | 35 | 5 | 5 | 1 | **550** | 1.612 | +1.062 (2,9×) |
| Parceiros · Oportunidades | 70 | 14 (12) | 90 | 6 | 3 | 5 | 0 | **1.318** | 3.873 | +2.555 (2,9×) |
| Parceiros · Lista | 120 | — | — | 20 | 3 | 5 | 0 | **120** | 331 | +211 (2,8×) |
| Detalhe do parceiro | 90 | 16 (14) | 90 | 8 | 3 | 5 | 0 | **1.574** | 4.142 | +2.568 (2,6×) |
| Casos | 110 | — | — | 8 | 3 | 5 | 0 | **110** | 133 | +23 |
| Dados da planilha (Qualidade) | 70 | — | — | 8 | 2 | 0 (tabela só se houver problema) | 0 | **70** | 187 | +117 (2,7×) |
| Cenários | 55 | — | — | 6 | 1 | — | 0 | **55** | 68 | +13 |
| Execuções | 60 | — | — | 10 | 2 | — | 0 | **60** | 82 | +22 |
| Registrar decisão | 120 | — | — | 0 | 2 | — | 0 | **120** | 158 | +38 |
| Guia | 400 | — | — | 8 | 4 | — | 0 | **400** | 915 | +515 (2,3×) |
| Validação | 300 | — | — | 20 | 5 | 4 | 1 | **300** | 2.473 | +2.173 (8,2×) |
| Auditoria (nova) | — | — | — | — | — | — | — | ≈1.700 (isolada) | — | — |
| **Total (sem Auditoria)** | | | | | **≈ 6.900** | **20.524** | **−66%** |

Com a Auditoria (≈ 1.700 palavras, material que hoje está nas telas), o total fica em ≈ 8.600 palavras (−58%). No estado padrão (evidências recolhidas, Previsão com 24 linhas) a soma é ≈ 3.700 palavras.

**Justificativa dos tetos:** uma pessoa lê ≈ 200 palavras em um minuto; telas de decisão acima de 250 palavras deixam de ser "olhadas" e passam a ser "lidas". Listas pesam por linha porque a pessoa varre, não lê: 12 a 16 palavras por linha (SKU, produto, uma ação, dois números). Evidência é lida por um item de cada vez, por isso tem teto próprio.

---

## 5. Telas enxutas propostas (as 5 mais pesadas)

Textos em linguagem simples. Números reais da API de 06/10/2026. "▸" = recolhido (só evidência, P1). Contagem estimada de palavras ao lado.

### 5.1 `/parceiros/KA-01` — de 4.142 para ≈ 320 palavras (estado padrão) · teto 1.574 com tudo aberto

```text
Papelaria Horizonte                                              [Voltar]
KA-01 · Sudeste · Lojas físicas e online
Cobertura de sell-out 20% (10 de 50 SKUs) · 4 oportunidades de reposição · último sell-out 08/2026

Ação  [Todas ▾]                                                14 SKUs

SKU / Produto                 Ação sugerida          Estoque   Dura    Vende/mês
CI-0011  Caderno A5 Verde     Avaliar reposição      132 un.   26 dias 151 un.   ▸ Evidências
CI-0014  Caderno Escolar      Avaliar reposição      102 un.   24 dias 125 un.   ▸ Evidências
CI-0026  Caderno A5 Azul      Avaliar reposição      119 un.   28 dias 126 un.   ▸ Evidências
CI-0029  Planner Semanal      Avaliar reposição      133 un.   23 dias 178 un.   ▸ Evidências
CI-0002  Caderno A5 Rosa      Monitorar estoque      181 un.  128 dias ...        ▸ Evidências
…
… (4 SKUs sem dados suficientes aparecem como "Não disponível", nunca como 0)

▾ CI-0011 · Papelaria Horizonte                                        (≤ 90 palavras)
  O estoque estimado (132 un.) dura 26 dias no ritmo de 151 un. por mês, abaixo dos
  30 dias configurados. Avaliar reposição; não há quantidade autorizada.
  Enviado 483 · Vendido 454 · Estoque estimado 132 (08/2026)
  Mês      Enviado  Vendido        Pedido em carteira: PED-011-1, 620 un.,
  09/2025       83       96        prometido para 14/09/2026
  … (12 meses)
```

- **Some da tela:** 4 cartões, filtros de SKU e qualidade, alerta comercial, selo "Suficiente no recorte" 14×, escopo/sinais/atualidade/natureza/fórmula de cada evidência, "Método…" (352 p), "Limitações", paginação.
- **Fica (P3):** "Sem dados suficientes" e "Não disponível" (nunca 0); "estimado" no cabeçalho "Estoque estimado"; coluna "Vende/mês" é o sell-out observado.
- **Palavras:** cabeçalho 35 + tabela 14 linhas × 16 = 224 + filtro 6 ≈ **265 a 320**.

### 5.2 `/parceiros` · Oportunidades — de 3.873 para ≈ 240 palavras · teto 1.318

```text
Onde há oportunidade de reposição
5 de 8 parceiros têm sugestão de reposição (12 no total). Dados até 08/2026.
Região [Todas ▾]  Canal [Todos ▾]            [Oportunidades (12)]  Parceiros (8)

Parceiro               SKU / Produto             Estoque   Dura     Vende/mês
Papelaria Horizonte    CI-0011 Caderno A5 Verde  132 un.   26 dias  151 un.   ▸ Evidências
Papelaria Horizonte    CI-0014 Caderno Escolar   102 un.   24 dias  125 un.   ▸ Evidências
Rede Ponto Criativo    CI-0027 Caderno A5 Rosa    67 un.   14 dias  144 un.   ▸ Evidências
…                                                                     (12 linhas)
```

- **Some:** 3 cartões, nota de cobertura, alerta comercial, colunas "Ação" e "Qualidade" (iguais nas 12 linhas), "08/2026 · estimado" 12×, "Método…".
- Ordenar por "dura" (menor primeiro) como padrão: o que acaba antes aparece antes.
- **Palavras:** 70 fixas + 12 × 14 = **≈ 240**.

### 5.3 `/previsoes` — de 2.759 para ≈ 390 palavras (24 linhas) · teto 730 (50 linhas)

```text
Preciso produzir? Quanto?
14 SKUs para produzir · 6 com capacidade a validar            Buscar [ SKU ou produto ]
Ação [Todas ▾]  Família [Todas ▾]  Ordenar [Posição na fila ▾]
Mostrando os 24 SKUs que pedem atenção de 50 SKUs.              [Ver os 50]

SKU / Produto                  Ação sugerida                         Quantidade  Próximo mês
CI-0030  Refil A5 Pautado      Produzir                              1.000 un.   928 un.
CI-0010  Estojo Inteligente    Produzir                                900 un.   638 un.
CI-0004  Planner Semanal       Produzir                                800 un.   501 un.
CI-0014  Caderno Escolar       Produzir após validar capacidade        400 un.  1.246 un.
CI-0041  Caderno Escolar Rosa  Sem ação necessária · Validar capacidade 0 un.    755 un.
…
```

- **Some:** descrição, 2 cartões (viram a frase), "Mais filtros" (confiança e tendência não separam nada), coluna "Confiança na previsão" (50/50 "alta"; passa a aparecer na linha só se for diferente), coluna "Fila de atenção", "Lote mínimo", "Ver previsão e modelo" 50× e 50 tooltips, "Ver detalhes" 50×.
- **Fica (P1):** clicar no SKU abre o detalhe com cálculo e evidências.
- **Palavras:** 80 fixas + 24 × 13 = **≈ 390**; com os 50 SKUs ≈ 730.

### 5.4 `/validacao` — de 2.473 para ≈ 300 palavras · Auditoria à parte

```text
Quanto confiar nas recomendações
Em 16 de 50 SKUs, o modelo não foi melhor do que repetir o último mês. No conjunto, o erro
médio é de 6,9% (repetir o último mês: 8,0%). 8 de 8 casos de teste passaram.

[ Erro médio 6,9% (simples: 8,0%) ]  [ Modelo pior em 16 de 50 SKUs ]  [ Casos de teste 8 de 8 ]

Falhas conhecidas
• O modelo não superou a previsão simples em 16 de 50 SKUs.            ▸ Ver os 16 SKUs
• 2 casos de teste usam entrada sintética (a planilha não tem esse exemplo).
Verificações de segurança: 7 de 7 passaram.      Auditoria completa →

[ Processo atual ]  Modelos
Indicador                      Informado   Recalculado       Meta
Tempo de análise do PCP        22 h/sem    Não disponível    8 h/sem
Erro médio da previsão         31% (MAPE)  6,9% (WAPE)*      —       *não é comparável
Pedidos atendidos no prazo     89%         Não disponível    96%
Aderência ao plano             78%         Não disponível    —
Tempo registrado: sem dados suficientes (0 de 20 decisões).
```

- **Vai para a Auditoria:** 8 casos congelados (1.151 p), 8 verificações de segurança, limitações permanentes, histórico de ajustes, hash e data de geração.
- **P4 preservado:** "16 de 50" aparece no resumo, no cartão e nas falhas conhecidas; a lista dos 16 SKUs fica a 1 clique.
- **Palavras:** resumo 45 + cartões 25 + falhas 45 + tabela 60 + frases 30 ≈ **250 a 300**.

### 5.5 `/skus/CI-0014` — de 1.760 para ≈ 400 palavras · teto 670 com 3 evidências abertas

```text
CI-0014 · Caderno Escolar · Escolar · posição 15 na fila de atenção             [Voltar]
Produzir após validar capacidade · 400 un.
Demanda a cobrir 1.327 un. (carteira), mais 434 de segurança, menos 1.490 em estoque e 0 em
produção: faltam 271; arredondado ao lote mínimo de 400.
[ Quantidade 400 un. ] [ Previsão do próximo mês 1.246 un. ] [ Confiança: previsão média · dados média ]
Capacidade da família a validar. Sugestão para revisão humana: não cria nem libera ordem de produção.
[ Registrar decisão ]  [ Criar caso ]

▾ Por que esta quantidade
  1.327 + 434 − 1.490 − 0 = 271 → lote mínimo 400
  Tendência estável (−2,2%) · Modelo: média móvel de 3 meses · Previsão de 3 meses: 3.811 un.
▸ Dados do SKU   Estoque 1.490 · Carteira 1.327 · Produção aberta 0 · Dura 55 dias · Prazo de produção 21 dias
                 Sell-out acumulado 3.737 · 2 parceiros com sell-out · Ausentes: nenhum
▾ Riscos e evidências   14 pontos = 5 + 9
  Capacidade pressionada (alta)         Ocupação 93,3% (limite 90%) · Capacidade livre 810 un./semana
  Pedido sem produção (alta)            Carteira 1.327 un. · Produção aberta 0 un.
Parceiros com sugestão para este SKU: 3   ▸ Papelaria Horizonte  Avaliar reposição  ▸ Evidências
```

- **Some:** premissas fixas, 3 mini-cartões de meses, limitação fixa, "Por que esta confiança" duplicada, descrição de cada sinal, "Origem" longa, alerta comercial, método (352 p), estoque projetado, lacuna, diferença sell-in − sell-out.
- **P2 e P3 preservados:** linha de revisão humana no cartão; "Ausentes" explícito; "previsto" no rótulo da previsão do modelo.
- **Palavras:** resposta 85 + cálculo 40 + dados 40 + riscos 60 + parceiros 40 + cabeçalho 20 ≈ **285 a 340** (CI-0041 com 5 sinais: ≈ 380).

---

## 6. Padrões para não voltar a poluir

### 6.1 Linguagem
1. **Uma frase de resposta por tela** e depois os dados; sem parágrafo de apresentação sob o título.
2. **Frases com até 20 palavras**, um assunto por frase, verbo no início quando for ação ("Avaliar reposição").
3. **Cada número com unidade, referência e sentido**: "132 un.", "26 dias (limite 30)", "16 de 50". Número sem referência não entra.
4. **Nenhum jargão sem tradução**: WAPE, baseline, holdout, sell-in/out, lead time e MAPE aparecem só como "erro médio da previsão", "previsão simples", "teste nos últimos 3 meses", "vendido ao parceiro", "vendido pelo parceiro", "prazo de produção". O termo técnico vive no "?" e no Guia.
5. **Ausente é "Não disponível"** (nunca "—" nem 0).
6. **Definição fica no "?" ou no Guia, nunca na tela**; um aviso novo precisa substituir um existente.

### 6.2 Visual
1. **Dois níveis de destaque por tela**: o título/resposta e o resto. Sem cartões dentro de cartões, sem bloco com borda colorida dentro de bloco com borda colorida.
2. **Cor só com significado** (vermelho = risco, âmbar = atenção, verde = favorável, azul = ação, cinza = ausente), nunca decoração.
3. **Selo só quando varia**: se a coluna tem o mesmo valor em todas as linhas, a coluna sai; o selo aparece apenas na exceção.
4. **Lista = linha de ≤ 5 colunas e ≤ 16 palavras**; o detalhe de uma linha vive na página do item, a 1 clique.
5. **Evidência por item ≤ 90 palavras**; tabela mensal de até 3 colunas.
6. **Auditoria isolada**: método, hash, casos congelados e histórico de ajustes ficam na página de Auditoria.

### 6.3 Teste automático de volume (descrito; não implementado)
`frontend/src/test/volume.test.tsx` renderiza cada rota com `mockApi()` e as fixtures, abre `<details>` e abas, e mede em `main`: palavras, números, blocos, colunas por tabela e avisos. Os tetos ficam em `frontend/src/test/volume-budget.json` (um objeto por rota com `fixed`, `perRow`, `perEvidence`, `numbers`, `blocks`, `columns`, `alerts`). O teste **falha** com a rota, a métrica e o excesso ("/previsoes: 812 palavras > 730") e imprime a tabela de volume. Como as fixtures têm poucas linhas, o teto é aplicado em `fixed + linhas_da_fixture × perRow` e há um segundo teste, por rota, que garante que o texto fixo (sem tabelas) respeita `fixed`. Uma regra extra pega repetição: nenhuma frase de 4+ palavras pode aparecer mais de 2 vezes numa tela fora de tabelas. O mesmo script de medição por Chrome (`volume.mjs`) serve para uma checagem com a planilha real, fora do CI.

---

## 7. Riscos

**Testes que mudariam** (`frontend/src/test`, `frontend/scripts`):
- `usability.test.tsx`: "Ver sinais, data e lacuna", "Mais filtros", linha de regra em `/prioridades`, nomes das abas da Validação ("Casos de teste", "Segurança e limitações"), `Em resumo`, "Falhas conhecidas".
- `filters-states.test.tsx`: filtros de confiança e tendência em Previsão e ação, "Somente itens com atenção" como padrão, "Dados insuficientes" na linha, `Revisão humana obrigatória` no SKU.
- `routes.test.tsx`, `a11y.test.tsx` e `keyboard.test.tsx`: títulos (`h2`) permanecem; se as descrições saírem, nenhum teste de título quebra. Nova rota `/auditoria` entra nas listas.
- `legibility.test.ts`: sem mudança.
- `scripts/test-decision-journey.mjs`: "Detalhes: qualidade da evidência" e "Ausência de sell-out nunca é tratada como venda zero" (Início); evidência da matriz comercial (`0 un.<small>08/2026`).
- `scripts/test-validation-page.mjs`: textos de casos congelados, "Coberto por teste", "Base alterada desde o congelamento" e `Não superou a baseline em 1 de 2.` passam a ser verificados na Auditoria e na lista de falhas.
- `contract-keys.json` e pytest de contrato: sem mudança, porque nenhum campo da API deixa de existir; a interface só passa a **não exibir** alguns.

**Contratos que não podem mudar:** todos os endpoints e campos de `docs/api.md`; URLs e parâmetros dos filtros existentes; valores enviados em `POST /api/feedback` e `POST /api/cases`; Guia funcionando sem API. A rota nova `/auditoria` é só frontend (o rewrite do `frontend/vercel.json` já atende qualquer URL interna).

**Roteiro de demonstração afetado** (`docs/roteiro-demonstracao.md`): minuto 0:00 (tabela "Processo atual" fica; a frase "só 20%…" passa para Confiança › Dados da planilha); 2:00 (CI-0014: "271", "434" e "1.327" ficam no bloco "Por que esta quantidade"; a previsão de 3 meses e a premissa de "não somar previsão e carteira" saem do SKU); 3:00 (evidência mensal: a tabela passa de 5 para 3 colunas, sem "Estoque estimado" mensal); 4:00 (casos congelados: "8 de 8" passa a ser uma linha com link para a Auditoria; "7 de 7 verificações" também).

**Outros riscos:**
- Cortar "Lote mínimo" da lista e as premissas do SKU exige que o cálculo continue legível no SKU (linha de cálculo mantida).
- Tornar "Somente itens com atenção" o padrão em Previsão esconde 26 SKUs "sem ação necessária" até o clique em "Ver os 50"; a contagem "24 de 50" fica sempre visível para não parecer que faltam SKUs.
- Remover as colunas "Ação" e "Qualidade" da aba Oportunidades só vale enquanto a aba listar apenas "Avaliar reposição"; se o filtro mudar, o componente deve voltar a mostrar a coluna.
- A pessoa de Comercial perde, na lista, o campo "Sinais" da evidência; ele continua no motivo da sugestão (1 frase vinda do backend).
- Mexer nos textos do backend não é necessário: todos os cortes são de exibição.

---

## 8. Apêndice — rascunho do prompt da fase de implementação

````text
Você vai ENXUGAR o Caderno Inteligente aplicando SOMENTE as decisões "aprovar" ou "ajustar" de docs/analise-enxugamento.md (coluna "Decisão do grupo"). Leia o documento inteiro antes de começar.

## Decisões aprovadas, nesta ordem
Decisão do grupo: Aprovado.
Ordem sugerida, quando aprovadas: (1) casca: menu sem descrições, barra superior, linha de regra só onde há sugestão, descrições sob o título; (2) listas: /prioridades e /previsoes (remover detalhe por linha, colunas sem informação, "atenção" como padrão); (3) detalhe do SKU; (4) parceiros: lista de oportunidades, detalhe do parceiro e evidência de ≤ 90 palavras; (5) Validação enxuta e nova página /auditoria; (6) Início, Qualidade, Casos, Cenários, Execuções, Decisões e Guia; (7) teste de volume.

## Orçamento e padrões aprovados
Decisão do grupo: Aprovado.
(orçamento da seção 4; padrões da seção 6)

## Restrições
1. Só apresentação e navegação. Não altere cálculos, score, ranking, regras, previsão, recomendação, processamento do Excel nem contratos da API; não remova campos da API (apenas pare de exibi-los). Campo novo só aditivo e documentado em docs/api.md.
2. Preserve: evidências a no máximo 1 clique; revisão humana dita uma vez no lugar certo; dado ausente nunca como zero e observado/estimado/previsto distinguíveis; falhas e limitações visíveis na Validação (inclusive "16 de 50"). Se um corte tocar um princípio, siga a forma de preservação indicada no documento.
3. Prefira APAGAR a recolher. Não esconda em "ver mais" o que o documento mandou apagar.
4. Mantenha o Guia sem API, deep links, filtros na URL, modo demonstração e somente leitura. As rotas existentes continuam abrindo.
5. Acessibilidade: zero violações do axe, contraste AA, texto com no mínimo 12px.
6. Testes: atualize os testes afetados (seção 7) sem apagar nenhum sem substituto, e implemente o teste de volume da seção 6.3 com o orçamento aprovado.
7. Atualize docs/roteiro-demonstracao.md, o Guia e o README se a navegação ou os textos mudarem.

## Entrega
- Passos pequenos, um grupo por vez, com `npm run check` ao final de cada grupo.
- Ao final: pytest (.venv/Scripts/python.exe -m pytest -p no:cacheprovider, com --basetemp se o diretório temporário negar acesso) e `npm run check`.
- Meça de novo o volume (palavras, números, blocos, colunas) de todas as telas, tudo expandido, com o mesmo método do documento, e registre antes × depois e o que ficou acima do teto.
- Verifique no navegador, em 1440×900, as telas alteradas e os 6 fluxos de tarefa (docs/mapeamento-usabilidade.md, seção 4).
- Crie docs/etapa-enxugamento.md com: decisões aplicadas e não aplicadas (e o motivo), volume antes × depois por tela, capturas antes × depois, arquivos modificados, resultados dos testes, limitações e passos de deploy.
- Não altere segredos e não faça deploy.
````
