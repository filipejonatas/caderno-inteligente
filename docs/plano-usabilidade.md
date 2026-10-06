# Plano de usabilidade — mapeamento e correção

## Por que agora

A interface cresceu etapa por etapa. Cada etapa acrescentou métricas, avisos e ressalvas que são corretos isoladamente, mas que somados deixam as telas difíceis de interpretar. As próximas funcionalidades (matriz de decisão parceiro × SKU e ligação entre recomendação comercial e viabilidade operacional) vão acrescentar informação. Por isso, primeiro organizamos.

Sinais medidos no código em 05/10/2026:

| Sinal | Valor |
|---|---|
| Declarações de fonte entre 8px e 10,5px no `App.css` | 67 |
| Colunas da tabela de Previsões / da matriz do parceiro | 12 / 15 |
| Cabeçalhos de tabela e badges na Validação | 19 / 11 |
| Páginas com avisos ou ressalvas (`Alert`, `DecisionBoundary`) | 9 de 13 |
| Ocorrências visíveis de "WAPE" / "baseline" / "score" | 26 / 21 / 30 |
| Itens no menu lateral | 13 |

O processo tem duas fases, com uma revisão humana entre elas:

1. **Fase 1 — Mapeamento (sem alterar código):** a IA gera `docs/mapeamento-usabilidade.md` com o inventário, a avaliação e as propostas, e um rascunho do prompt de correção.
2. **Revisão do grupo (30 a 45 min):** aprovar, recusar ou ajustar cada proposta.
3. **Fase 2 — Correção:** a IA aplica somente o que foi aprovado.

Tempo estimado: Fase 1, de 2 a 3 horas; Fase 2, de 4 a 6 horas. O desafio termina em 17/10/2026, e a usabilidade não pode consumir o tempo das funcionalidades que ainda faltam.

---

## Prompt da Fase 1 — Mapeamento

Copie o bloco abaixo e envie para a IA.

````text
Você vai MAPEAR a usabilidade do Caderno Inteligente. NÃO altere nenhum arquivo de código, configuração ou teste nesta fase. O único arquivo que você deve criar é docs/mapeamento-usabilidade.md.

## Contexto
- Protótipo de apoio à decisão para o PCP e o Comercial de uma fabricante de cadernos (modelo B2B2C). Leia README.md, docs/architecture.md, docs/api.md e docs/roteiro-demonstracao.md antes de começar.
- Frontend: React + TypeScript + Vite em frontend/src (páginas em pages/, componentes em components.tsx e components/, estilos em App.css). Backend: FastAPI em backend/ sobre src/caderno_inteligente/.
- Para ver as telas, suba a API (.venv/Scripts/python.exe -m uvicorn backend.main:app --port 8000) e o frontend (cd frontend; npm run dev). Use a planilha real; não grave dados (não envie formulários).
- Público: pessoas de PCP e Comercial, não técnicas. A pessoa deve entender cada tela em poucos segundos e saber o que fazer em seguida.

## Princípios inegociáveis (podem ser reorganizados, nunca removidos)
1. Toda recomendação continua mostrando suas evidências, no máximo a 1 clique de distância.
2. A revisão humana obrigatória e o "não é ordem de produção" continuam claros, mas podem ser ditos uma vez, no lugar certo, em vez de repetidos.
3. Dado ausente nunca aparece como zero; observado, estimado e previsto continuam distinguíveis.
4. Falhas e limitações (por exemplo, o modelo não superar a baseline em 16 de 50 SKUs) continuam visíveis na Validação.
5. Nenhuma mudança de cálculo, score, ranking, regras, previsão ou recomendação. A Fase 2 só mexe em apresentação e navegação.

## O que mapear

### A. Inventário do frontend (uma seção por rota)
Para cada uma das rotas (/guia, /, /prioridades, /previsoes, /skus/:sku, /parceiros, /parceiros/:codigo, /casos, /qualidade, /cenarios, /execucoes, /decisoes, /validacao, 404):
1. Objetivo da página em uma frase e a pergunta de negócio que ela responde.
2. Público principal: PCP, Comercial ou gestão/apresentação.
3. Lista de TODOS os elementos visíveis, de cima para baixo: títulos, avisos, cards de métrica, filtros, tabelas (com cada coluna), badges, botões, tooltips e textos explicativos. Para cada número: o que significa, a unidade, de qual endpoint e campo ele vem e se há contexto de comparação (por exemplo, "16 de 50").
4. Contagem: quantidade de números visíveis na primeira dobra (1440×900 e 375×812), quantidade de avisos e quantidade de colunas por tabela.
5. Capturas de tela em 1440×900 e 375×812, salvas em docs/mapeamento-usabilidade/ e referenciadas no documento.

### B. Inventário do backend
1. Tabela com todos os endpoints (método, rota, página que consome, campos efetivamente exibidos, campos retornados e não usados).
2. Endpoints que nenhuma página usa (por exemplo, /api/b2b2c/visibility e /api/capacity/{family}). Apenas registre; não proponha remover APIs, porque os contratos devem ser preservados.
3. Dados disponíveis na API que poderiam simplificar a interface (por exemplo, um texto pronto de motivo principal que substitua vários badges).

### C. Fluxos de tarefa (meça cliques e telas)
Execute e registre o caminho atual, a quantidade de cliques, os pontos de dúvida e o que a pessoa precisa interpretar:
1. PCP: "Qual SKU devo olhar primeiro hoje e por quê?"
2. PCP: "Preciso produzir este SKU? Quanto?"
3. Comercial: "Qual parceiro tem oportunidade de reposição e qual é a evidência?"
4. Gestão: "Quanto posso confiar nessas recomendações?"
5. PCP: "Registrar a decisão que tomei."
6. Apresentação: seguir o roteiro de 5 minutos de docs/roteiro-demonstracao.md.

### D. Avaliação de usabilidade
Aplique as 10 heurísticas de Nielsen e estes critérios específicos, citando o elemento e a rota:
- Hierarquia: o principal da tela está no topo e com maior destaque?
- Densidade: há mais de 4 a 6 números competindo pela atenção na primeira dobra?
- Interpretação dos números: cada número tem unidade, referência e sentido (bom ou ruim)? Percentuais e decimais estão consistentes?
- Linguagem: termos técnicos (WAPE, holdout, backtest, baseline, score, sell-in/out, lead time) sem explicação em linguagem simples.
- Repetição: o mesmo aviso ou conceito explicado em várias páginas.
- Legibilidade: textos abaixo de 12px, contraste e tabelas largas no celular.
- Consistência: mesmos conceitos com nomes, cores ou formatos diferentes entre as páginas.
- Navegação: 13 itens no menu; quais poderiam ser agrupados, rebaixados ou unidos.
- Ações: está claro qual é o próximo passo em cada tela?
Classifique cada problema pela gravidade (crítico, alto, médio ou baixo) e pela frequência (quantas telas afeta).

### E. Propostas
Para cada problema, proponha uma solução concreta, classificada como:
REMOVER, FUNDIR, REBAIXAR (levar para um detalhe, aba ou "ver mais"), RENOMEAR, REESCREVER (linguagem simples), REFORMATAR (número, unidade, cor) ou REORDENAR.
Para cada proposta, informe: rota, elemento, problema, solução, princípio inegociável afetado (se houver, e como ele é preservado), esforço (P, M ou G) e impacto (baixo, médio ou alto).
Inclua também:
1. Uma proposta de arquitetura de informação: menu com no máximo 6 ou 7 entradas principais, agrupando o restante, com a justificativa.
2. Um padrão de página: no topo, a resposta principal em uma frase; depois, até 4 números com contexto; depois, a ação; detalhes e evidências recolhidos.
3. Um padrão para números (unidades, casas decimais, percentuais, "não disponível", cores semânticas) e um glossário de termos com a versão em linguagem simples.
4. Onde as funcionalidades planejadas vão entrar sem aumentar a densidade: matriz de decisão parceiro × SKU, viabilidade operacional ao lado da recomendação comercial, faturamento previsto e visão por região e canal.

## Formato de docs/mapeamento-usabilidade.md
1. Resumo executivo (até 10 linhas) com os 5 problemas mais graves.
2. Inventário do frontend (A).
3. Inventário do backend (B).
4. Fluxos de tarefa (C), com uma tabela antes × depois estimada.
5. Problemas (D), em tabela ordenada por gravidade.
6. Propostas (E), em tabela com uma coluna "Decisão do grupo" vazia (aprovar, recusar ou ajustar).
7. Arquitetura de informação, padrão de página, padrão de números e glossário propostos.
8. Riscos: testes que precisarão mudar (frontend/src/test e frontend/scripts), contratos que não podem mudar e pontos do roteiro de demonstração afetados.
9. Apêndice: rascunho do prompt da Fase 2, preenchido a partir do modelo em docs/plano-usabilidade.md, deixando as propostas como "[aguardando decisão do grupo]".

## Regras
- Não altere código, testes, estilos ou configuração. Se algo impedir a execução (API fora do ar, por exemplo), registre e siga com a leitura do código.
- Cite rotas, arquivos e linhas (frontend/src/pages/X.tsx:linha) em cada problema.
- Seja específico: "mover o card X para a aba Detalhes" é útil; "simplificar a página" não é.
- Não invente dados nem números; use os da API real e indique a data.
````

---

## Revisão do grupo (entre as fases)

1. Abrir `docs/mapeamento-usabilidade.md` e ler o resumo e as capturas de tela.
2. Na tabela de propostas, preencher a coluna "Decisão do grupo" com aprovar, recusar ou ajustar (com o ajuste).
3. Conferir a arquitetura de informação proposta e o glossário.
4. Definir o recorte da Fase 2, de preferência os itens de impacto alto e esforço P ou M.

---

## Prompt da Fase 2 — Correção (modelo)

A IA da Fase 1 deixa este modelo preenchido no apêndice do mapeamento. Revise as propostas aprovadas e envie.

````text
Você vai CORRIGIR a usabilidade do Caderno Inteligente aplicando SOMENTE as propostas aprovadas em docs/mapeamento-usabilidade.md (coluna "Decisão do grupo" = aprovar ou ajustar). Leia o mapeamento inteiro antes de começar.

## Propostas aprovadas, nesta ordem
[Lista numerada copiada da tabela de propostas: rota · elemento · solução · ajuste do grupo]

## Arquitetura de informação aprovada
[Menu final, agrupamentos e rotas. Rotas existentes que deixarem o menu continuam funcionando por URL; não quebre deep links.]

## Padrões aprovados
[Padrão de página, padrão de números e glossário aprovados]

## Restrições
1. Não altere cálculos, score, ranking, regras, previsão, recomendação, processamento do Excel ou contratos da API. Se precisar de um campo novo para a interface, ele deve ser ADITIVO e documentado em docs/api.md.
2. Preserve os princípios: evidências a no máximo 1 clique; revisão humana clara (dita uma vez, no lugar certo); dado ausente nunca como zero; observado, estimado e previsto distinguíveis; falhas visíveis na Validação.
3. Mantenha o Guia funcionando sem API, os deep links, os filtros na URL, o modo demonstração e o modo somente leitura.
4. Acessibilidade: continue com zero violações do axe (frontend/src/test/a11y.test.tsx), contraste AA e textos com no mínimo 12px, exceto rótulos auxiliares justificados.
5. Testes: atualize os testes afetados (frontend/src/test, frontend/scripts e frontend/src/test/contract-keys.json) refletindo o novo comportamento. Não apague um teste sem substituí-lo por um equivalente.
6. Atualize docs/roteiro-demonstracao.md e o Guia de uso se a navegação mudar.

## Entrega
- Implemente em passos pequenos, um grupo de propostas por vez, rodando npm run check ao final de cada grupo.
- Ao final, rode os testes Python (.venv/Scripts/python.exe -m pytest -p no:cacheprovider) e npm run check.
- Verifique no navegador, em 375×812 e 1440×900, as rotas alteradas e os 6 fluxos de tarefa do mapeamento. Registre os cliques antes × depois.
- Crie docs/etapa-usabilidade.md com: propostas aplicadas, propostas não aplicadas e o motivo, capturas antes × depois, fluxos antes × depois, arquivos modificados, resultados dos testes, limitações e passos de deploy.
- Não altere segredos e não faça deploy.
````
