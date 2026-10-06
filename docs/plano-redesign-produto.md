# Plano geral de redesign de produto — Caderno Inteligente

> **Status:** plano de produto e implementação. Este documento não altera cálculos, contratos, regras de negócio ou código do frontend.
>
> **Objetivo:** orientar uma IA desenvolvedora a melhorar a arquitetura de informação, a hierarquia visual, a responsividade e os fluxos principais do produto em etapas pequenas, verificáveis e reversíveis.
>
> **Como executar:** peça à IA: **“Execute a Etapa N do plano em `docs/plano-redesign-produto.md`.”** A IA deve ler este documento inteiro antes de editar qualquer arquivo e executar somente a etapa solicitada.

---

## 1. Resultado esperado

O produto deve deixar de se comportar como um conjunto de análises acumuladas e passar a orientar quatro trabalhos claros:

1. **Planejar produção:** saber qual SKU analisar, qual ação é sugerida e qual quantidade considerar.
2. **Atuar comercialmente:** identificar a oportunidade parceiro–SKU mais urgente e consultar sua evidência.
3. **Acompanhar decisões:** registrar decisões e conduzir casos até a conclusão.
4. **Avaliar confiança:** entender qualidade dos dados, desempenho do modelo, mudanças entre execuções e limitações.

As mudanças são principalmente de apresentação, navegação e composição. Cálculos, scores, previsões e recomendações existentes devem ser preservados, salvo autorização explícita em uma etapa futura.

---

## 2. Diagnóstico do estado atual

### 2.1 Pontos fortes a preservar

- Rotas reais e compartilháveis com React Router.
- Carregamento por página, lazy loading e cancelamento de requisições antigas.
- Filtros persistidos na URL.
- Resposta operacional no topo do detalhe do SKU.
- Distinção entre valor ausente e zero.
- Estados de carregamento, vazio, erro, atualização e somente leitura.
- Navegação por teclado, link “Pular para o conteúdo”, foco após navegação e menu móvel acessível.
- Validação resumida separada da Auditoria extensa.
- Testes de contrato, rotas, volume, teclado, contraste e axe.

### 2.2 Problemas prioritários

#### A. Duas filas para a mesma decisão

`/prioridades` informa a ordem e o motivo. `/previsoes` informa ação e quantidade. O PCP precisa trocar de tela para concluir uma única tarefa.

**Decisão:** criar uma fila operacional unificada contendo posição, SKU, ação, quantidade, motivo principal e exceções relevantes.

#### B. Conteúdo financeiro antecede a ação operacional

Em `/previsoes`, o faturamento estimado aparece antes dos filtros e da lista operacional. Na medição móvel de 375 × 812:

- o cartão de faturamento começa em aproximadamente 350 px;
- os filtros operacionais começam em aproximadamente 1.510 px;
- a lista operacional começa em aproximadamente 1.890 px;
- a página chega a aproximadamente 3.690 px.

**Decisão:** mover faturamento estimado para uma página própria em Planejamento.

#### C. Detalhe do SKU mistura quatro trabalhos

O detalhe reúne decisão operacional, previsão/modelo, eventos, faturamento, riscos e parceiros. Em 375 × 812, a página medida chegou a aproximadamente 4.898 px; o contexto comercial começou em aproximadamente 3.396 px.

**Decisão:** manter a resposta no topo e dividir o conteúdo em abas: Resumo, Evidências, Parceiros e Impacto financeiro.

#### D. Oportunidades comerciais não estão priorizadas para ação

A lista mostra oportunidades, mas não define claramente qual deve ser tratada primeiro. No celular, a página medida chegou a aproximadamente 5.338 px e cada item fechado ocupou cerca de 366–382 px.

**Decisão:** ordenar por menor cobertura e maior giro, adicionar busca e criar um cartão móvel compacto.

#### E. Cor comunica certeza indevida

O cartão do detalhe do SKU usa aparência positiva mesmo quando a ação exige validar capacidade. “Sem ação necessária” também pode coexistir com uma pendência de capacidade.

**Decisão:** verde somente para concluído, aprovado ou validado; azul para recomendação; âmbar para revisão ou pendência; vermelho para erro, bloqueio ou risco crítico.

#### F. Casos não fecham o ciclo de trabalho

O frontend cria casos, mas não permite atualizar status, responsável ou prazo. A função `api.updateCase` já existe.

**Decisão:** transformar Casos em uma fila gerenciável e fazer dela a entrada padrão de Acompanhamento.

#### G. Navegação contém um agrupamento técnico

“Avançado” reúne Cenários e Execuções, embora sejam recursos de Planejamento e Confiança.

**Decisão:** mover Cenários para Planejamento, Execuções para Confiança e remover “Avançado”.

#### H. Responsividade genérica aumenta a densidade

Tabelas são transformadas genericamente em cartões por CSS. Isso gera itens altos e pode prejudicar a semântica de tabela em algumas combinações de navegador e leitor de tela.

**Decisão:** criar apresentações móveis específicas para listas operacionais e comerciais.

#### I. Design system fragmentado

Tokens, componentes e estilos estão distribuídos entre `App.css`, `usability.css`, `components.tsx` e componentes especializados. Existem classes antigas de cartões de previsão sem uso no JSX atual.

**Decisão:** consolidar tokens e padrões gradualmente, sem reescrever toda a interface de uma vez.

---

## 3. Arquitetura de informação recomendada

### 3.1 Menu principal

1. **Início**
2. **Planejamento**
3. **Comercial**
4. **Acompanhamento**
5. **Confiança**
6. **Ajuda**

### 3.2 Estrutura de páginas

| Área | Página recomendada | Origem atual | Decisão |
|---|---|---|---|
| Início | Início | `/` | Manter e reordenar blocos |
| Planejamento | Fila operacional | `/prioridades` + `/previsoes` | Unificar |
| Planejamento | Faturamento previsto | bloco de `/previsoes` | Criar página |
| Planejamento | Cenários | `/cenarios` | Mover de Avançado |
| Planejamento | Detalhe do SKU | `/skus/:sku` | Manter rota e dividir em abas |
| Comercial | Oportunidades | `/parceiros` | Manter e priorizar |
| Comercial | Parceiros | `/parceiros?aba=parceiros` | Manter |
| Comercial | Canais | `/parceiros?aba=diretos` | Manter como entidade distinta |
| Comercial | Detalhe do parceiro | `/parceiros/:codigo` | Manter e ordenar |
| Comercial | Detalhe do canal | `/canais/:canal` | Manter |
| Acompanhamento | Casos | `/casos` | Tornar página padrão |
| Acompanhamento | Decisões | `/decisoes` | Renomear para Histórico de decisões |
| Confiança | Validação | `/validacao` | Manter |
| Confiança | Dados da planilha | `/qualidade` | Manter |
| Confiança | Auditoria | `/auditoria` | Manter |
| Confiança | Execuções | `/execucoes` | Mover de Avançado |
| Ajuda | Guia de uso | `/guia` | Manter e atualizar |

### 3.3 Compatibilidade de URLs

- Não remover rotas existentes abruptamente.
- Preservar `/prioridades` e `/previsoes` como aliases ou redirects para a fila operacional.
- Preservar parâmetros relevantes de busca, filtro e ordenação.
- Não quebrar links existentes para SKUs, parceiros, canais, decisões ou casos.
- Toda mudança de URL deve ter teste de deep link e atualização de documentação.

---

## 4. Regras gerais para todas as etapas

### 4.1 Escopo e segurança

- Ler este documento inteiro antes de editar.
- Inspecionar `git status` antes de começar.
- Preservar mudanças existentes que não pertençam à etapa.
- Executar somente a etapa solicitada.
- Não antecipar etapas seguintes “para aproveitar”.
- Não fazer commit, push, deploy ou alterar dados persistidos.
- Não mudar cálculos, scores, previsões, recomendações ou contratos da API sem autorização explícita.
- Não tratar ausência de dado como zero.

### 4.2 Qualidade de implementação

- Reutilizar componentes existentes quando forem adequados.
- Criar componentes novos quando um padrão ocorrer em três ou mais lugares ou quando o componente atual tiver responsabilidades conflitantes.
- Manter estado compartilhável na URL quando filtros ou abas alterarem a leitura da página.
- Estados secundários não podem bloquear a tarefa principal.
- Erro em faturamento, eventos ou contexto comercial não pode esconder a ação operacional do SKU.
- Evitar dependência de texto ou cor como único indicador de estado.

### 4.3 Validação obrigatória

Ao final de cada etapa:

1. executar typecheck;
2. executar testes do frontend;
3. executar build;
4. executar testes Node aplicáveis;
5. validar acessibilidade automatizada;
6. validar teclado nos fluxos alterados;
7. inspecionar visualmente em 375 × 812, 820 × 900 e 1440 × 900;
8. verificar `git diff` e confirmar que apenas o escopo solicitado mudou.

### 4.4 Relatório obrigatório

A IA deve terminar cada etapa informando:

1. resumo do resultado;
2. arquivos alterados;
3. decisões de produto aplicadas;
4. testes executados e resultados;
5. validação visual realizada;
6. riscos, diferenças em relação ao plano e pendências;
7. confirmação de que não fez commit, push ou deploy.

---

## 5. Etapas de implementação

## Etapa 1 — Fundamentos visuais e responsivos

### Objetivo

Corrigir a semântica visual, centralizar fundamentos mínimos e preparar os componentes responsivos usados nas próximas etapas.

### Implementação

1. Criar tokens reutilizáveis para:
   - espaçamento: 4, 8, 12, 16, 24, 32 e 48 px;
   - tipografia: metadado, corpo compacto, corpo, título de seção e título de página;
   - estados semânticos: informação, revisão, bloqueio e sucesso.
2. Criar variantes `info`, `review`, `blocked` e `success` para o cartão de resposta operacional.
3. Aplicar `review` quando houver:
   - capacidade a validar;
   - confiança baixa;
   - investigação obrigatória;
   - dados insuficientes que impeçam decisão segura.
4. Reservar verde para concluído, aprovado ou validado.
5. Criar um hook `useMediaQuery` reativo.
6. Substituir leituras diretas de `window.matchMedia` em páginas por esse hook.
7. Remover CSS comprovadamente sem uso, incluindo classes antigas de `forecast-page-card`, se a busca e os testes confirmarem que não são usadas.
8. Não reorganizar rotas ou conteúdo nesta etapa.

### Arquivos prováveis

- `frontend/src/App.css`
- `frontend/src/usability.css`
- `frontend/src/components.tsx`
- `frontend/src/pages/SkuDetailPage.tsx`
- `frontend/src/pages/PrioritiesPage.tsx`
- `frontend/src/pages/ForecastsPage.tsx`
- novo hook em `frontend/src/hooks/`
- testes de contraste, legibilidade, responsividade e ações

### Critérios de aceite

- “Produzir após validar capacidade” não usa aparência de sucesso.
- Estados semânticos não se contradizem dentro do mesmo cartão ou linha.
- Redimensionar a janela atualiza o comportamento dependente de breakpoint.
- Nenhum cálculo, endpoint ou contrato é alterado.
- Testes, typecheck, build e axe aprovados.

### Prioridade e esforço

**P0 — pequeno/médio.**

---

## Etapa 2 — Fila operacional unificada

### Objetivo

Responder em uma única página: **“Qual SKU analisar, o que fazer e quanto?”**

### Implementação

1. Criar `OperationalQueuePage`.
2. Carregar prioridades, previsões e configuração em paralelo.
3. Fazer a junção pelo SKU no cliente inicialmente.
4. Tratar explicitamente um SKU que exista em apenas uma das fontes.
5. Exibir no desktop:
   - posição e SKU/produto;
   - ação sugerida;
   - quantidade sugerida;
   - motivo principal;
   - exceção de confiança ou capacidade.
6. Não exibir na fila:
   - previsão completa dos três meses;
   - cálculo de necessidade;
   - erro detalhado do modelo;
   - todos os eventos futuros;
   - evidência completa.
7. Mostrar somente itens que pedem atenção por padrão.
8. Preservar busca, família, ação, rótulo e ordenação na URL.
9. Levar detalhes e evidências para `/skus/:sku`.
10. Manter `/prioridades` e `/previsoes` como aliases ou redirects compatíveis.

### Arquivos prováveis

- `frontend/src/App.tsx`
- `frontend/src/components.tsx`
- `frontend/src/api.ts`
- `frontend/src/pages/PrioritiesPage.tsx`
- `frontend/src/pages/ForecastsPage.tsx`
- nova página `frontend/src/pages/OperationalQueuePage.tsx`
- novo componente de fila em `frontend/src/components/`
- testes de rotas, filtros, volume, teclado e acessibilidade

### Riscos

- Campos de prioridade e previsão vêm de endpoints diferentes.
- Uma falha parcial precisa ser tratada sem produzir uma recomendação incorreta.
- Parâmetros antigos da URL precisam de mapeamento documentado.

### Critérios de aceite

- Ação e quantidade são encontradas sem trocar de página.
- A lista operacional começa acima da primeira dobra no celular.
- A lista tem no máximo cinco dimensões de decisão.
- Filtros continuam compartilháveis por URL.
- A rota do SKU continua acessível em um clique.

### Prioridade e esforço

**P0 — grande.**

---

## Etapa 3 — Página de faturamento previsto

### Objetivo

Separar análise financeira da decisão operacional sem remover informação.

### Implementação

1. Criar uma página de Faturamento previsto.
2. Mover `RevenueSummaryCard` para essa página.
3. Adicionar a página à subnavegação de Planejamento.
4. Preservar:
   - total previsto;
   - gráfico observado versus estimado;
   - famílias;
   - variação;
   - erro do teste;
   - SKUs sem preço ou previsão.
5. Adicionar filtros por família e SKU quando suportados pelos dados já carregados.
6. Permitir link para `/skus/:sku?tab=impacto` quando existir detalhe financeiro do SKU.
7. A falha do faturamento não pode bloquear a fila operacional.

### Arquivos prováveis

- `frontend/src/App.tsx`
- `frontend/src/components.tsx`
- `frontend/src/components/RevenueForecast.tsx`
- `frontend/src/pages/ForecastsPage.tsx` ou a fila criada na Etapa 2
- nova página `frontend/src/pages/RevenueForecastPage.tsx`
- testes de receita, rotas, acessibilidade e volume

### Critérios de aceite

- Nenhum conteúdo financeiro antecede a lista de ações operacionais.
- Observado e estimado continuam diferenciados por texto e estilo.
- Ausência de preço ou previsão nunca aparece como R$ 0.
- A página funciona isoladamente por URL.

### Prioridade e esforço

**P0 — médio.**

---

## Etapa 4 — Detalhe do SKU orientado à tarefa

### Objetivo

Preservar a resposta operacional imediata e distribuir evidências por contexto.

### Implementação

1. Manter o cartão principal no topo.
2. Criar abas persistidas em `?tab=`:
   - `resumo`;
   - `evidencias`;
   - `parceiros`;
   - `impacto`.
3. **Resumo:** ação, quantidade, confiança, ressalvas, evento urgente e CTAs.
4. **Evidências:** cálculo, dados do SKU, riscos, origem e eventos detalhados.
5. **Parceiros:** `PartnerSkuContext`.
6. **Impacto:** `SkuRevenueBlock`.
7. Carregar conteúdo secundário somente quando necessário, se isso não exigir mudança de contrato.
8. Preservar retorno à tela de origem.
9. Preservar links para Registrar decisão e Criar caso com SKU preenchido.

### Arquivos prováveis

- `frontend/src/pages/SkuDetailPage.tsx`
- `frontend/src/components/EventAlerts.tsx`
- `frontend/src/components/RevenueForecast.tsx`
- `frontend/src/components/PartnerSkuContext.tsx`
- novo componente de abas ou extensão do padrão existente
- testes de SKU, eventos, receita, teclado, rotas e acessibilidade

### Critérios de aceite

- Ação e CTAs aparecem na primeira tela de 375 × 812.
- O conteúdo inicial do SKU fica abaixo de aproximadamente 1.600 px no conjunto de dados de demonstração.
- Contexto comercial e financeiro não são carregados ou exibidos antes de serem necessários, quando tecnicamente viável.
- Falha de dados secundários não bloqueia a ação operacional.
- A aba selecionada pode ser compartilhada por URL.

### Prioridade e esforço

**P1 — médio.**

---

## Etapa 5 — Comercial priorizado e responsivo

### Objetivo

Responder: **“Qual oportunidade comercial deve ser tratada primeiro?”**

### Implementação

1. Renomear o grupo de menu “Parceiros” para “Comercial”, preservando rotas.
2. Em Oportunidades, ordenar por padrão:
   - menor cobertura de estoque;
   - maior giro no desempate;
   - parceiro e SKU como desempate estável final.
3. Adicionar busca por parceiro, SKU e produto.
4. Adicionar controle de ordenação e persistir na URL.
5. Criar `OpportunityCard` para celular.
6. Limitar o cartão fechado a aproximadamente 220 px.
7. Exibir evidência sob demanda e manter apenas uma evidência aberta por vez.
8. Remover repetição de tooltips idênticos quando todas as linhas têm a mesma ação.
9. Usar sempre:
   - “cobertura de estoque” para dias disponíveis;
   - “cobertura de dados de sell-out” para completude da base.
10. No detalhe do parceiro, mostrar por padrão ações e insuficiências antes dos demais SKUs.

### Arquivos prováveis

- `frontend/src/components.tsx`
- `frontend/src/pages/B2BPage.tsx`
- `frontend/src/pages/PartnerDetailPage.tsx`
- `frontend/src/components/CommercialMatrix.tsx`
- `frontend/src/usability.css`
- testes comerciais, filtros, responsividade, teclado e acessibilidade

### Critérios de aceite

- A primeira oportunidade é a mais urgente segundo a ordenação documentada.
- Busca e ordenação ficam na URL.
- Cartão móvel fechado não excede aproximadamente 220 px.
- Uma oportunidade pode ser entendida sem abrir sua evidência.
- Parceiro e SKU permanecem navegáveis.

### Prioridade e esforço

**P0/P1 — médio.**

---

## Etapa 6 — Acompanhamento de casos e decisões

### Objetivo

Fechar o ciclo entre recomendação, decisão e acompanhamento.

### Implementação

1. Renomear o grupo “Decisões” para “Acompanhamento”.
2. Fazer Casos ser a entrada padrão do grupo.
3. Adicionar edição de status, responsável e prazo usando `api.updateCase`.
4. Adicionar filtros por status e responsável.
5. Destacar casos abertos vencidos sem depender somente da cor.
6. Renomear visualmente `/decisoes` para “Histórico de decisões”.
7. Manter registro de decisão a partir do detalhe do SKU.
8. Quando `/decisoes` for aberto sem SKU, não selecionar silenciosamente o primeiro SKU: exigir escolha ou busca explícita.
9. Usar `aria-live="polite"` para sucesso e `role="alert"` para erro.
10. Preservar a lista durante salvamento ou falha de um item.

### Arquivos prováveis

- `frontend/src/components.tsx`
- `frontend/src/pages/CasesPage.tsx`
- `frontend/src/pages/FeedbackPage.tsx`
- `frontend/src/api.ts`
- testes de formulários, teclado, segurança, rotas e acessibilidade

### Critérios de aceite

- Um caso pode ser criado, atribuído, atualizado e concluído pelo frontend.
- A atualização de um caso não bloqueia os demais.
- Erro do servidor mantém valores anteriores e oferece nova tentativa.
- O registro de decisão nunca usa um SKU implícito sem confirmação do usuário.

### Prioridade e esforço

**P1 — médio.**

---

## Etapa 7 — Navegação final, documentação e limpeza

### Objetivo

Concluir a arquitetura recomendada e remover resíduos das estruturas anteriores.

### Implementação

1. Mover Cenários para Planejamento.
2. Mover Execuções para Confiança.
3. Remover o grupo “Avançado”.
4. Atualizar menu, subnavegação, títulos, Guia e documentação.
5. Preservar URLs antigas com aliases ou redirects.
6. Remover componentes, propriedades e CSS comprovadamente obsoletos.
7. Consolidar regras duplicadas entre `App.css` e `usability.css` sem uma reescrita cosmética ampla.
8. Atualizar testes de rotas, navegação, volume, teclado e acessibilidade.
9. Corrigir avisos de migração do React Router 7 se isso não exigir atualização ampla de dependências.
10. Fazer validação visual final de todas as rotas.

### Critérios de aceite

- Menu contém Início, Planejamento, Comercial, Acompanhamento e Confiança; Ajuda permanece acessível.
- Não existe grupo “Avançado”.
- Nenhum deep link anterior resulta em 404.
- Guia e README refletem a arquitetura final.
- Não restam estilos ou componentes sem referência identificáveis por busca estática.

### Prioridade e esforço

**P1/P2 — médio.**

---

## 6. Regras do design system final

### 6.1 Cores semânticas

| Estado | Cor principal | Uso |
|---|---|---|
| Informação/recomendação | Azul | Ação sugerida ainda não confirmada |
| Revisão necessária | Âmbar | Capacidade, confiança, dado antigo ou investigação |
| Bloqueio/erro/risco crítico | Vermelho | Ação impedida ou falha crítica |
| Sucesso | Verde | Concluído, aprovado, validado ou salvo |
| Neutro | Cinza/slate | Metadados e ausência de prioridade |

### 6.2 Densidade

- Uma lista de decisão deve ter no máximo cinco dimensões principais.
- Informação constante em todas as linhas deve sair da linha e virar contexto da seção.
- Badges devem indicar exceções, não decorar dados normais.
- Evidência detalhada deve estar a um clique, não sempre expandida.
- Uma tela de decisão deve responder sua pergunta principal antes de gráficos ou metodologia.

### 6.3 Tabelas e listas

- Tabela para comparação horizontal em desktop.
- Lista/cartão específico para decisão sequencial no celular.
- Não depender de `display: block` genérico sobre qualquer `<table>`.
- Cabeçalhos e rótulos devem continuar disponíveis a leitores de tela.
- Linhas clicáveis precisam ter ação equivalente em botão ou link com nome acessível.

### 6.4 Filtros

- Busca e filtros principais sempre visíveis.
- Filtros raros em “Mais filtros”.
- Contagem do resultado próxima aos filtros.
- “Limpar filtros” só aparece quando há filtro ativo.
- Estado relevante sempre refletido na URL.

### 6.5 Formulários e feedback

- Rótulos explícitos e exemplos somente como apoio.
- Campo inválido deve ter mensagem associada ao próprio controle.
- Sucesso anunciado por `aria-live="polite"`.
- Erro anunciado com `role="alert"`.
- Durante salvamento, bloquear somente a ação afetada.
- Manter os valores digitados quando o servidor falhar.

### 6.6 Ações destrutivas

Não há exclusão como fluxo principal no estado atual. Se for adicionada:

- usar botão com texto específico, nunca apenas ícone;
- pedir confirmação informando entidade e consequência;
- manter Cancelar como opção segura;
- oferecer desfazer quando tecnicamente possível;
- não usar vermelho para ações não destrutivas.

---

## 7. Priorização consolidada

| Iniciativa | Prioridade | Esforço |
|---|---|---|
| Corrigir semântica de cores | P0 | Pequeno/médio |
| Fila operacional unificada | P0 | Grande |
| Separar faturamento | P0 | Médio |
| Cartão móvel de oportunidade | P0 | Médio |
| Ordenar oportunidades por urgência | P1 | Pequeno |
| Reestruturar detalhe do SKU | P1 | Médio |
| Permitir atualização de casos | P1 | Médio |
| Reorganizar navegação | P1 | Médio |
| Padronizar estados e feedback | P1 | Médio |
| Consolidar design system | P1 | Médio |
| Busca comercial adicional | P2 | Pequeno |
| Índice interno da Auditoria | P2 | Pequeno |
| Limpeza de CSS e avisos técnicos | P2 | Pequeno |

---

## 8. Prompt recomendado para executar uma etapa

Use este prompt no mesmo repositório, trocando `N` pelo número desejado:

```markdown
Execute a Etapa N do plano em `docs/plano-redesign-produto.md`.

Antes de editar:
1. Leia o documento inteiro.
2. Inspecione o estado atual do repositório e o git status.
3. Verifique os arquivos e testes relacionados à etapa.

Regras:
- Execute somente a Etapa N; não antecipe etapas seguintes.
- Preserve mudanças existentes fora do escopo.
- Preserve cálculos, scores, previsões, recomendações e contratos da API,
  salvo autorização explícita na etapa.
- Não faça commit, push ou deploy.
- Faça as alterações de código e testes necessárias; não entregue apenas outro plano.
- Tome decisões de implementação compatíveis com os critérios de aceite do documento.
- Se houver diferença entre o plano e o código atual, explique e escolha a alternativa
  que preserve a intenção de produto e a compatibilidade.

Validação obrigatória:
- typecheck;
- testes do frontend;
- testes Node aplicáveis;
- build;
- acessibilidade automatizada;
- teclado nos fluxos alterados;
- inspeção visual em 375 × 812, 820 × 900 e 1440 × 900.

Ao concluir, informe:
1. resultado entregue;
2. arquivos alterados;
3. decisões de produto aplicadas;
4. testes e resultados;
5. validação visual;
6. riscos ou pendências;
7. confirmação de que não houve commit, push ou deploy.
```

### Forma curta

Depois que a IA já conhecer as regras do repositório, basta usar:

```text
Execute a Etapa 1 do plano em docs/plano-redesign-produto.md.
Implemente e valide tudo o que pertence à etapa, sem antecipar as demais.
```

---

## 9. Checklist final do programa

- [ ] A ação operacional aparece antes de faturamento e metodologia.
- [ ] Prioridade, ação e quantidade estão na mesma fila.
- [ ] `/prioridades` e `/previsoes` continuam abrindo de forma compatível.
- [ ] O detalhe do SKU tem abas compartilháveis.
- [ ] Oportunidades estão ordenadas por urgência.
- [ ] Cartões móveis são compactos e semanticamente acessíveis.
- [ ] Casos podem ser atualizados e concluídos.
- [ ] Nenhum formulário escolhe um SKU silenciosamente.
- [ ] Cenários estão em Planejamento.
- [ ] Execuções estão em Confiança.
- [ ] “Avançado” foi removido.
- [ ] Cores comunicam estado, não apenas categoria.
- [ ] Erros secundários não bloqueiam a tarefa principal.
- [ ] Guia, README, rotas e testes refletem a arquitetura final.
- [ ] Typecheck, testes, build, axe e validação manual foram aprovados.

