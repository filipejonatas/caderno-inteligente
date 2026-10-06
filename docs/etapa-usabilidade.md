# Etapa de usabilidade (Fase 2)

Aplica as propostas aprovadas em [mapeamento-usabilidade.md](mapeamento-usabilidade.md) (40 propostas, todas com decisão "Aprovado"), a arquitetura de informação (seção 7.1) e os padrões (7.2 a 7.4). **Só apresentação e navegação:** nenhum cálculo, score, ranking, regra, previsão, recomendação, processamento do Excel ou contrato da API foi alterado, e nenhum campo novo foi criado (ver [api.md](api.md)).

Medições "antes" são as do mapeamento (05/10/2026); "depois" foram feitas em 06/10/2026 com a mesma planilha (SHA-256 `03fa0ed4…803f`), a mesma API e o mesmo método (Chrome headless, 1440×900 e 375×812). Capturas "depois" em [`etapa-usabilidade/`](etapa-usabilidade/) (mesmos nomes das capturas "antes" em [`mapeamento-usabilidade/`](mapeamento-usabilidade/), mais `parceiros-lista-*`).

## 1. Propostas aplicadas

| Grupo | Propostas | O que mudou |
|---|---|---|
| 1 | E01, E22, E38 | O motivo principal passa a ser o sinal de maior peso (pesos de `GET /api/config`; desempate por severidade) e os badges seguem a mesma ordem. Ação "Produzir" em azul (tom `info`), vermelho só para risco. Ícone de busca, selo de confiança e nome/código do parceiro corrigidos |
| 2 | E02–E06, E21, E36 | Previsão e ação: tabela de 7 colunas que cabe em 1440 px (ação e quantidade logo após o SKU; previsão, modelo e capacidade em "Ver previsão e modelo"). Detalhe do SKU: resposta no topo (ação, quantidade, por quê, botões), 4 números, "Confiança na previsão" e "Confiança nos dados do SKU" rotuladas, "Previsão comercial (planilha)" × "Previsão do modelo", blocos recolhíveis, evidências com rótulos em português, unidades e %, e a soma "33 = 10 + 8 + 8 + 5 + 2" |
| 3 | E07, E10–E12, E31 | Menu de 6 entradas + Ajuda; abas entre rotas do grupo; uma única linha de regra sob o título; sem eyebrow nem kicker; nomes únicos por página; vocabulário de projeto removido ("Semana 4", "Etapa 6", "nesta etapa", "snapshot", "só ranking") |
| 4 | E14, E34, E37 | Início reorganizado (frase, 4 números com "de N", ação, fila de 5, detalhes recolhidos); cartões redundantes removidos; definição de cobertura dita uma vez |
| 5 | E15–E18 | Matriz com 5 colunas e evidência na própria linha ("Ver evidências", aberta sozinha quando há um só vínculo); Parceiros abre em "Oportunidades" (lista única das 12, via `commercial-recommendations?action=avaliar_reposicao`) com aba "Parceiros" (`?aba=parceiros`) em linhas |
| 6 | E23, E24 | Validação: resumo em uma frase, 4 cartões, "Falhas conhecidas" sempre visíveis e abas (Processo atual, Modelos de previsão, Casos de teste, Segurança e limitações); casos recolhidos, abertos quando falham; "16 de 50" no cartão e no resumo |
| 7 | E26–E28 | "Registrar decisão" e "Criar caso" no SKU levam a `?sku=` com o SKU preenchido (inclusive fora do ranking); rótulos novos ("O que você decidiu?", "O dado do parceiro ajudou?"; **valores enviados inalterados**); Casos e Decisões como abas; botão "+ Novo caso" removido |
| 8 | E08, E19, E20, E32, E33, E39, E13, E29, E30, E35, E41, E43 | Glossário em "?" (`Hint`) e no Guia; padrão de números (`displayQuantity`, `displayPercent`, `displayShare`, `displayDays`, datas curtas, "Não disponível"); textos do backend localizados no cliente (`localizeText`); piso de 12 px; tabelas viram cartões no celular; "Ver mais" (10 no celular, 25 no desktop); Guia com trilhas por papel; Qualidade com "12 de 12 abas íntegras"; Cenários e Execuções enxutos; "Mais filtros"; limitações do parceiro recolhidas |

## 2. Propostas aplicadas com ajuste ou não aplicadas por completo

| Proposta | O que ficou diferente e por quê |
|---|---|
| E10 | O `h1` da barra é o título único e o eyebrow/kicker saíram. O `h2` virou uma pergunta curta e fixa por página ("O que olhar primeiro", "Preciso produzir? Quanto?"); a **frase de resposta dinâmica** existe só em Início, detalhe do SKU, Parceiros, Qualidade e Validação. Nas demais, uma frase dinâmica exigiria dados que a página não carrega |
| E16 | Cartões no celular por CSS sobre a mesma tabela (um único DOM), não por componente separado; evita texto duplicado e testes frágeis |
| E20 | Feito no cliente (`localizeText`); não foi criado campo `*_display` no backend, para manter o contrato intacto |
| E24 | Cores de tom nos cartões e frases de veredito; **sem setas** de bom/ruim |
| E29 | Os nomes das abas vêm da planilha (ex.: "Ordens Producao"); só `_` virou espaço. Corrigir acentos exigiria mapear nomes de origem |
| E34 | "Investigar dados" só aparece se > 0; os cartões de Qualidade viram "Situação da base"; "Decisões" e "Influenciadas" ficaram em uma linha |
| E35 | A barra mostra "Carregado às 21:45 (Brasília)" (sem segundos). **O mês de referência dos dados não entrou na barra** porque nenhum endpoint global o fornece; ele continua em Parceiros e na Validação |
| E39 | O roteiro de 5 minutos saiu do Guia e passou a ser apontado para `docs/roteiro-demonstracao.md` |
| E07 | A legenda da tabela de prioridades ficou só para leitor de tela; a nota fixa do menu foi removida. O aviso "Sem ação necessária… não significa sem risco" e a linha de revisão humana do cartão da ação foram mantidos (exceção e lugar da ação) |

Fora de escopo (continua no roadmap): atualizar o status de casos (`PUT /api/cases/{id}` sem tela), expor `Valor faturado (R$)` para faturamento previsto, mês de referência global.

## 3. Fluxos antes × depois

"Antes" = mapeamento, seção 4. "Depois" = medido nas telas novas, 06/10/2026 (cliques contados pelo caminho; **nenhum formulário foi enviado**).

| Fluxo | Antes | Depois |
|---|---|---|
| 1. Qual SKU primeiro e por quê | 0 cliques (1 p/ evidências); a frase usava o 1º sinal alfabético ("Capacidade pressionada") | 0 cliques (1 p/ evidências); o motivo é "Abaixo do estoque de segurança" e a frase cita a produção 25 dias depois da promessa. Números na dobra: 4 cartões com "de N" |
| 2. Preciso produzir? Quanto? | 3 cliques + digitação + rolagem horizontal; ação do SKU a 1,7 tela (celular 2,7) | Menu "Produção" → aba "Previsão e ação" → busca: ação e quantidade na própria linha, **sem rolagem horizontal** (a tabela cabe: 1.055 px de 1.055 px). No SKU a resposta está em y=375 (celular y=455): **0 rolagem**. Para abrir o SKU a partir de Início: 1 clique |
| 3. Oportunidade de reposição e evidência | 7 cliques (≈ 27 para as 12) | **2 cliques** (Parceiros → "Ver evidências"); as 12 em uma lista, primeira linha em y=874 |
| 4. Quanto confiar | 1 clique, mas "16 de 50" em frase só a 4,8 telas | 1 clique; veredito em y=351 e falhas conhecidas em y≈730 (acima das abas) |
| 5. Registrar a decisão | 4 a ≈ 11 interações; SKU a escolher de novo | **2 cliques no mínimo** (botão "Registrar decisão" no SKU → registrar), SKU já preenchido |
| 6. Roteiro de 5 min | 1 clique + ≈ 8 telas de rolagem | 1 clique + 3 trocas de aba na Validação; ação do SKU na primeira dobra; Validação cai de 5.092 para 1.899 px |

Alturas de página (px, 1440 | 375): Início 2.292 → 1.271 | 3.582 → 2.423; `/previsoes` 3.744 → 2.708 | **18.727 → 3.830**; `/validacao` 5.092 → 1.899 | 10.409 → 2.864; `/parceiros/KA-01` 3.198 → 2.108 | 3.950 → 5.085; detalhe do SKU CI-0014 3.221 → 2.774 | 4.467 → 4.813. **Pioraram:** o celular da matriz (cartões altos) e do SKU (resposta e blocos). `/parceiros` cresce (1.583 → 1.908) porque agora traz a lista das 12 oportunidades.

Honesto sobre números na primeira dobra: em 1440×900 o Início passou de 11 para 15 tokens numéricos (a fila subiu na página); o ganho é de conteúdo (motivo correto, "de N", aviso único), não de contagem bruta.

## 4. Arquivos modificados

- **Novo:** `frontend/src/usability.css`, `frontend/src/test/usability.test.tsx`, `frontend/src/test/legibility.test.ts`, `docs/etapa-usabilidade.md` e `docs/etapa-usabilidade/` (capturas).
- **Frontend:** `App.tsx`, `App.css` (piso de 12 px; regras antigas de colunas ocultas removidas), `components.tsx`, `components/CommercialMatrix.tsx`, `components/RunComparisonView.tsx`, `pages/` (`B2BPage`, `CasesPage`, `FeedbackPage`, `ForecastsPage`, `GuidePage`, `OverviewPage`, `PartnerDetailPage`, `PrioritiesPage`, `QualityPage`, `RunsPage`, `ScenariosPage`, `SkuDetailPage`, `ValidationPage`, `shared.ts`).
- **Testes atualizados:** `routes`, `a11y`, `keyboard`, `robustness`, `filters-states` (títulos, menu, rótulos, comportamento de linha) e os scripts `test-decision-journey`, `test-validation-page`, `test-run-comparison` (ordem de compilação de `shared`, textos novos). Nenhum teste foi apagado sem substituto: o teste do aviso `DecisionBoundary` virou o da linha de regra; "duas execuções" e a lista de rotas foram mantidos com os nomes novos.
- **Documentação:** `README.md`, `docs/architecture.md`, `docs/api.md` (sem mudança de contrato), `docs/roteiro-demonstracao.md`.
- Backend, `config/`, `contract-keys.json` e planilha: **sem alteração**.

## 5. Testes

- `npm run check` (typecheck, Vitest, `node --test`, build, varredura de segredos): **aprovado**, 144 testes Vitest (142 + 2 de legibilidade) e 20 testes Node; **zero violações do axe** nas 14 rotas, em desktop e celular.
- `pytest` (`-p no:cacheprovider`): **193 aprovados**. Neste ambiente foi preciso `--basetemp` em outra pasta, porque o diretório temporário padrão do sistema negava acesso (problema do ambiente, não do código).
- Novos testes: ordenação por peso, formatos e `localizeText`; abas e linha de regra única; linha expansível da fila; detalhe do SKU com resposta e botões; `?sku=` fora do ranking; oportunidades e evidência na linha; abas da Validação; piso de 12 px nos CSS.

## 6. Limitações

- O teste de 12 px lê as declarações de CSS; não mede o texto renderizado. Rótulos `sr-only` não têm tamanho.
- Tabelas viram cartões no celular com `display: block`; leitores de tela podem perder a semântica de tabela nesse tamanho.
- Contraste continua verificado só pelas cores (`contrast.test.ts`); não medi o contraste dos novos blocos renderizados.
- Não capturados: faixas de demonstração/somente leitura, estados de erro e a comparação de execuções (há 1 execução e eu não gravei outra).
- Os "depois" do fluxo 2 dependem de a pessoa passar pelo menu e pela aba; de Início há atalho direto apenas para o primeiro SKU.

## 7. Passos de deploy

Sem mudança de variáveis, banco ou backend. Nenhum deploy foi feito.

1. `cd frontend && npm run check`; `.venv\Scripts\python.exe -m pytest -p no:cacheprovider`.
2. Publicar o frontend como já documentado em [deploy-vercel-supabase.md](deploy-vercel-supabase.md) (as rotas agrupadas continuam resolvidas pelo rewrite do `frontend/vercel.json`).
3. Rodar o smoke test somente leitura contra a publicação e abrir as abas do [roteiro](roteiro-demonstracao.md) (as URLs não mudaram).
