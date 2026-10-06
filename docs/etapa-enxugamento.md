# Etapa de enxugamento

Aplica as decisões aprovadas em [analise-enxugamento.md](analise-enxugamento.md) (todas marcadas "Aprovado", mais o orçamento da seção 4 e os padrões da seção 6). **Só apresentação e navegação:** nenhum cálculo, score, ranking, regra, previsão, recomendação, processamento do Excel ou contrato da API mudou. Nenhum campo foi removido da API (a interface apenas deixou de exibir vários) e nenhum campo novo foi criado (ver [api.md](api.md)).

Medição "antes" (06/10/2026, análise) e "depois" (mesma planilha, SHA-256 `03fa0ed4…803f`, mesma API, mesmo script de Chrome headless, 1440×900, página inteira, **tudo expandido**: `<details>` e abas abertos, "Ver mais" e "Ver evidências" clicados). Capturas: antes em [`analise-enxugamento/`](analise-enxugamento/), depois em [`etapa-enxugamento/`](etapa-enxugamento/) (mesmos nomes, mais `previsoes-todos-1440.png` e `auditoria-1440.png`).

## 1. Volume antes × depois

| Tela | Palavras antes | Palavras depois | Números antes | Números depois | Teto (seção 4) | Situação |
|---|---|---|---|---|---|---|
| Detalhe do parceiro (KA-01) | 4.142 | **1.442** | 538 | 322 | 1.574 | dentro |
| Oportunidades (`/parceiros`) | 3.873 | **1.343** | 620 | 378 | 1.318 | **+25** |
| Previsão e ação (50 SKUs / padrão com 24) | 2.759 | **518** / 289 | 347 | 105 / 54 | 730 | dentro |
| Validação | 2.473 | **357** | 190 | 55 | 300 | **+57** |
| SKU CI-0014 | 1.760 | **585** | 157 | 94 | 670 | dentro |
| Fila de atenção (41 SKUs) | 1.668 | **491** | 154 | 84 | 550 | dentro |
| SKU CI-0041 | 1.612 | **554** | 66 | 40 | 550 | **+4** |
| Guia | 915 | **411** | 8 | 3 | 400 | **+11** |
| Início | 363 | **194** | 33 | 18 | 200 | dentro |
| Parceiros (lista) | 331 | **164** | 44 | 28 | 120 | **+44** (ver nota) |
| Dados da planilha | 187 | **49** | 44 | 4 | 70 | dentro |
| Registrar decisão | 158 | **107** | 0 | 0 | 120 | dentro |
| Casos | 133 | **99** | 9 | 9 | 110 | dentro |
| Execuções | 82 | **46** | 10 | 10 | 60 | dentro |
| Cenários | 68 | **32** | 6 | 5 | 55 | dentro |
| **Total (15 telas)** | **20.524** | **6.392** (−69%) | **2.226** | **1.155** (−48%) | ≈ 6.900 | |
| Auditoria (nova; recebeu o que saiu das telas de decisão) | — | 2.031 | — | 116 | sem teto de leitura | |
| **Total com Auditoria** | 20.524 | **8.423** (−59%) | 2.226 | **1.271** (−43%) | ≈ 8.600 | |

**O que ficou acima do teto (e por quê):**
- **Validação (+57):** tabela "Processo atual" mantém os selos informado/recalculado/meta (princípio 3) e a aba de modelos conta tudo expandido, incluindo a lista dos 16 SKUs (princípio 4).
- **Oportunidades (+25):** a evidência por vínculo ficou em ≈ 90 a 95 palavras (teto 90), com 12 abertas.
- **Parceiros (lista, +44):** o teto de 120 supôs menos linhas; com 8 parceiros (≈ 13 palavras por linha) mais 70 fixas o valor realista é ≈ 175. **Proposta: ajustar o teto para 175.**
- **Guia (+11) e CI-0041 (+4):** margem pequena; ficam para a revisão do grupo.
- **Números** não têm teto total no orçamento (só fixos); a redução de 48% vem das colunas e das evidências cortadas.

## 2. Decisões aplicadas

| Grupo | Aplicado |
|---|---|
| 1. Casca | Menu sem descrições; barra superior "Atualizado às 11:09"; linha de regra só em Início, Previsão e ação e Parceiros; descrições sob o título removidas (ficam onde há dado: Parceiros, Dados da planilha, Previsão e ação); abas do grupo Confiança com Auditoria |
| 2. Listas | **Fila de atenção:** 5 colunas, uma linha curta por SKU, sem "+N sinais", família, data crítica nem lacuna. **Previsão e ação:** 4 colunas (SKU, ação, quantidade, próximo mês), sem detalhe por linha (50 tooltips saíram), sem coluna de confiança (vira selo só se ≠ "alta"), padrão "só o que pede atenção" (24 de 50) com botão "Ver os 50 SKUs" (`?todos=1`), sem filtros de confiança e tendência, 2 cartões viraram a frase do cabeçalho |
| 3. SKU | Cartão de resposta com a frase de necessidade ("Necessidade: 1.327 a cobrir + 434 de segurança − 1.490 em estoque − 0 em produção = 271 un.; arredondada ao lote mínimo de 400"), 3 números, linha de revisão humana; sem premissas fixas, meses previstos, limitação fixa, estoque projetado, lacuna, diferença sell-in − sell-out, caixa "Por que esta confiança", descrição de cada sinal, "Limitação conhecida"; "Sobre a previsão" em uma linha; "Dados do SKU" e "Riscos e evidências" compactos |
| 4. Parceiros | Oportunidades sem cartões, nota e alerta; colunas "Ação" e "Qualidade" omitidas quando todas as linhas são iguais; evidência de 3 números + motivo + tabela de 3 colunas; lista de parceiros com 5 colunas; detalhe do parceiro com uma linha-resumo no lugar de 4 cartões, filtro só de ação e só com mais de 25 vínculos, paginação só com mais de 50; método comercial e limitações do parceiro foram para a Auditoria |
| 5. Validação e Auditoria | Resumo de 2 frases, 3 cartões, falhas conhecidas (casos sintéticos viram 1 linha), 2 abas (Processo atual, Modelos), tempo de análise em 1 linha, lista dos 16 SKUs em 3 colunas. Nova rota **`/auditoria`**: casos congelados, verificações de segurança, limitações, histórico de ajustes, método comercial, hash e datas |
| 6. Demais telas | **Início:** frase única, 3 cartões, fila de 5; sem "Detalhes". **Dados da planilha:** 2 cartões, tabela só quando há aba a revisar. **Casos, Cenários, Execuções, Decisões:** sem descrições e subtítulos; contadores de Casos em uma linha. **Guia:** sem bloco de passos, 11 termos de uma frase, 3 limites, 4 perguntas |
| 7. Teste de volume | `frontend/src/test/volume.test.tsx` + `volume-budget.json` |

## 3. Decisões não aplicadas ou ajustadas

| Item | Diferença e motivo |
|---|---|
| Linha de regra no SKU | **Não aplicada.** O SKU ficou só com a linha "Revisão humana obrigatória" dentro do cartão da ação; a linha de regra no topo diria a mesma coisa duas vezes (princípio 2) |
| Cobertura de sell-out e "Decisões registradas" saindo do Início | A cobertura (20%) já estava em Dados da planilha. O contador de decisões **não foi recolocado em Decisões**: a Validação mostra "0 de 20 decisões com tempo informado". Pode voltar se o grupo quiser |
| Oportunidades ordenadas por "dura" | Não aplicada: a ordem continua a da API (por parceiro). Exige decidir o critério de ordenação |
| "Ver previsão e ação" no cartão do Início | Removido, como proposto; o SKU já traz a ação |
| Filtros de Previsão | Ficaram Buscar, Ação, Família e Ordenar (não só os 2 da proposta). `atencao`, `confianca` e `tendencia` na URL são ignorados (a URL ainda abre) |
| Evidência por vínculo ≤ 90 palavras | Quase: ≈ 90 a 95 medido |
| Tetos de Validação, Guia e Parceiros (lista) | Acima, ver seção 1 |
| Teste de volume | Mede o **texto fixo, por linha e por evidência** com as fixtures (poucas linhas), não o total real. O total real continua sendo medido pelo script de Chrome com a planilha, fora do CI |

## 4. Fluxos de tarefa (contados pelo caminho; telas conferidas em 1440×900)

| Fluxo | Antes (Fase 2) | Depois |
|---|---|---|
| 1. Qual SKU primeiro e por quê | 0 cliques (1 p/ evidências); cartão com frase repetida, 5 selos, 4 cartões e botão extra | 0 cliques (1 p/ evidências); 1 frase ("Abaixo do estoque de segurança. Produção prevista para 08/10/2026, 25 dias depois da data prometida."), 3 selos, 3 cartões |
| 2. Preciso produzir? Quanto? | Menu → aba → busca; 50 linhas com detalhe em cada uma | Menu → aba: **24 linhas** (só o que pede atenção) com ação e quantidade; 3 cliques até a evidência (SKU) |
| 3. Oportunidade e evidência | 2 cliques; lista com 6 colunas, 3 cartões, alerta, nota | 2 cliques; lista de 5 colunas, sem cartões nem alerta |
| 4. Quanto confiar | 1 clique; 4 cartões, 4 abas, 2.473 palavras | 1 clique; resumo de 2 frases, 3 números, falhas conhecidas, 357 palavras; detalhes em "Auditoria completa" |
| 5. Registrar decisão | 2 cliques no mínimo (SKU → botão → registrar) | igual |
| 6. Roteiro de 5 min | Validação com 4 abas | Validação com 2 abas e o botão "Auditoria completa"; `docs/roteiro-demonstracao.md` atualizado |

Alturas de página (px): Validação 6.504 → 2.591; Previsão e ação (50 SKUs) 14.709 → 3.486; Fila de atenção 11.051 → 2.876; detalhe do parceiro 14.398 → 9.881; Início 1.829 → 1.069.

## 5. Arquivos modificados

- **Novos:** `frontend/src/pages/AuditoriaPage.tsx`, `frontend/src/test/volume.test.tsx`, `frontend/src/test/volume-budget.json`, `docs/etapa-enxugamento.md`, `docs/etapa-enxugamento/` (capturas).
- **Frontend:** `App.tsx`, `components.tsx`, `components/CommercialMatrix.tsx`, `components/PartnerSkuContext.tsx`, `pages/` (`B2BPage`, `CasesPage`, `FeedbackPage`, `ForecastsPage`, `GuidePage`, `OverviewPage`, `PartnerDetailPage`, `PrioritiesPage`, `QualityPage`, `RunsPage`, `ScenariosPage`, `SkuDetailPage`, `ValidationPage`), `types.ts` (`PageId`), `usability.css`.
- **Testes atualizados (nenhum apagado sem substituto):** `routes`, `a11y`, `filters-states`, `robustness`, `usability` e os scripts `test-decision-journey` e `test-validation-page` (casos congelados passam a ser verificados na Auditoria).
- **Documentação:** `README.md`, `docs/architecture.md`, `docs/api.md`, `docs/roteiro-demonstracao.md`.
- Backend, `config/`, `contract-keys.json`, segredos e planilha: **sem alteração**.

## 6. Testes

- `npm run check`: **aprovado**. 164 testes Vitest (inclui 14 de volume e 2 de legibilidade), 21 testes Node, build e varredura de segredos; **zero violações do axe** nas 15 rotas (inclui `/auditoria`), em desktop e celular.
- `pytest`: **193 aprovados** (com `--basetemp` em outra pasta, porque o diretório temporário padrão negava acesso).
- Com a API e o frontend rodando ao mesmo tempo, os primeiros testes de cada arquivo estouraram o tempo de espera de 5 s algumas vezes (carga da máquina, não do código). Com os servidores parados, o `npm run check` passa inteiro.

## 7. Limitações

- O teste de volume é uma trava de regressão com dados sintéticos; não substitui medir a planilha real.
- Não medi o contraste dos blocos novos (só as cores, em `contrast.test.ts`) nem o celular com a mesma régua.
- As tabelas viram cartões no celular com `display: block`; leitores de tela podem perder a semântica de tabela nesse tamanho.
- A comparação de execuções e os estados de erro, demonstração e somente leitura não foram capturados.
- O texto de apoio de partes do SKU vem de campos do backend (`confidence_reason`, `recommendation_reason`) e não foi encurtado.

## 8. Passos de deploy

Sem mudança de variáveis, banco ou backend. Nenhum deploy foi feito.

1. `cd frontend && npm run check`; `.venv\Scripts\python.exe -m pytest -p no:cacheprovider`.
2. Publicar o frontend como em [deploy-vercel-supabase.md](deploy-vercel-supabase.md); a rota nova `/auditoria` é resolvida pelo rewrite do `frontend/vercel.json`.
3. Rodar o smoke test somente leitura e abrir as abas do [roteiro](roteiro-demonstracao.md); acrescentar `/auditoria` se for mostrar a Auditoria.
