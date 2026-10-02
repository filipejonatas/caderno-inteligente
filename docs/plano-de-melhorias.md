# Plano de melhorias — Caderno Inteligente

> Status em 30/09/2026: fundação, redesign operacional, responsividade, cache, ambiente reproduzível e validações principais implementados. Evoluções posteriores de paginação, comparação histórica e exportação permanecem opcionais.

## 1. Resumo executivo

O projeto tem um núcleo de negócio bem encaminhado: regras determinísticas, pesos configuráveis, rastreabilidade das evidências, preservação da fonte XLSM e testes voltados aos cálculos críticos. O principal desnível está na camada de produto. A interface React expõe apenas parte do que a API já oferece, não comunica bem risco, confiança ou próximos passos e apresenta falhas de responsividade e de tratamento de erro.

Recomendação: adotar o React/Vite como interface principal e manter o Streamlit apenas como ferramenta interna temporária de diagnóstico. A primeira rodada deve corrigir confiabilidade e responsividade; a segunda deve redesenhar a experiência em torno da decisão do PCP; a terceira deve reforçar desempenho, testes e operação.

## 2. Diagnóstico atual

### Pontos fortes

- O XLSM é tratado como fonte somente leitura.
- Regras, indicadores e priorização estão separados da interface.
- Pesos e limiares ficam em arquivos de configuração.
- A priorização preserva evidências, limitações e nível de confiança.
- FastAPI já expõe detalhes de SKU, qualidade de dados, capacidade, cenários, feedback, casos e execuções.
- Há 23 testes Python identificados para ingestão, validação, indicadores, regras, priorização, persistência e API.
- O build de produção do frontend é concluído com sucesso.

### Problemas críticos

1. **Responsividade quebrada:** abaixo de 800 px o CSS muda a largura visual do `aside` para 70 px, mas mantém `flex-basis: 230px`. Em viewport de 390 px, o conteúdo recebe aproximadamente 160 px e fica cortado.
2. **Falhas de API não são tratadas:** um erro em qualquer uma das seis requisições iniciais rejeita o `Promise.all`; a tela permanece com traços e não explica o problema.
3. **Processamento repetido:** várias rotas recarregam e recalculam o XLSM. A abertura do dashboard dispara requisições que repetem o pipeline completo, aumentando latência e consumo.
4. **Cobertura funcional incompleta no React:** detalhe do SKU, filtros, qualidade global dos dados, evidências e feedback existem no domínio/API ou no Streamlit, mas não na interface principal.
5. **Código de frontend difícil de manter:** toda a aplicação está concentrada em um único arquivo minificado, com uso amplo de `any`, sem componentes, tipos ou camada de API.

### Problemas de experiência visual

- A interface parece um painel genérico: azul uniforme, poucos sinais semânticos e ausência de identidade própria.
- O cabeçalho ocupa muito espaço e não ajuda a tomar decisão.
- KPIs exibem somente números, sem contexto, severidade, tendência ou ação associada.
- A tabela não diferencia criticidade, confiança ou motivo da prioridade.
- Linhas parecem clicáveis pelo cursor, mas não executam ação.
- Não há estados de carregamento, vazio, erro, sucesso ou atualização.
- A navegação móvel oculta os rótulos sem oferecer ícones, menu ou alternativa acessível.
- A fonte `Inter` é declarada, mas não é carregada; normalmente ocorre fallback para Arial.
- Existe CSS residual do template Vite e ativos não utilizados, aumentando ruído do projeto.

### Problemas de qualidade e operação

- React em versão 18 está combinado com tipos React 19.
- Listas renderizadas não possuem `key`, gerando avisos no console.
- Não há scripts de lint, teste de frontend ou teste end-to-end.
- O README documenta o núcleo Python, mas não o fluxo completo FastAPI + React.
- CORS está fixo em `http://localhost:5173`, embora o servidor também possa ser aberto por `127.0.0.1`.
- O ambiente atual não oferece um Python com `pytest`, por isso a suíte não pôde ser executada nesta análise.
- Não há controle de versão Git inicializado no diretório analisado.

## 3. Direção proposta para o frontend

### Princípio de produto

A interface deve responder rapidamente a três perguntas:

1. O que precisa de atenção agora?
2. Por que esse SKU está priorizado e quão confiável é o sinal?
3. Qual ação humana precisa ser registrada ou acompanhada?

### Estrutura de navegação

- **Visão geral:** resumo operacional, distribuição de riscos, confiança e itens mais urgentes.
- **Prioridades:** filtros, ordenação e lista completa orientada à ação.
- **Detalhe do SKU:** indicadores, evidências, capacidade, canal, histórico e feedback.
- **Casos:** quadro/lista por status, responsável e prazo.
- **Qualidade dos dados:** erros, avisos, cobertura, atualidade e origem.
- **Cenários:** parâmetros claramente separados do ranking oficial e comparação antes/depois.
- **Execuções:** snapshots auditáveis, comparação e identificação da fonte.

### Linguagem visual

- Base neutra clara, com azul-petróleo como cor institucional e cores semânticas reservadas para risco.
- Tokens para cor, espaçamento, raio, sombra e tipografia.
- Vermelho somente para crítico; âmbar para atenção; verde para situação saudável; cinza para dado ausente.
- Cards compactos com título, valor, contexto e ação.
- Badges consistentes para severidade, confiança e status.
- Tabela com cabeçalho fixo, densidade confortável, alinhamento numérico e detalhe em drawer lateral.
- Sidebar recolhível no desktop e drawer/bottom navigation no mobile.
- Gráficos apenas onde ajudam a comparar risco, confiança, cobertura e evolução.

## 4. Plano de execução

### Fase 0 — Decisão técnica e linha de base (0,5–1 dia)

**Objetivo:** reduzir ambiguidade antes do redesenho.

- Confirmar React como interface principal e Streamlit como fallback temporário.
- Inicializar Git e criar `.gitignore` para `node_modules`, `dist`, caches, bancos de runtime e artefatos locais conforme a política do projeto.
- Documentar comandos únicos para instalar, iniciar e validar backend e frontend.
- Registrar métricas de linha de base: tempo de carregamento, número de leituras do XLSM, erros de console e comportamento em 390/768/1440 px.

**Critério de aceite:** qualquer pessoa consegue iniciar o projeto a partir do README e reproduzir a linha de base.

### Fase 1 — Estabilidade e responsividade (2–3 dias)

**Frontend**

- Dividir `App.tsx` em páginas, componentes, tipos, hooks e serviço de API.
- Remover `any` dos contratos principais e modelar respostas da API.
- Implementar estados de loading, erro, vazio, sucesso e retry.
- Validar `response.ok` antes de interpretar JSON; impedir erros não tratados.
- Corrigir `key` nas listas e alinhar versões de React e `@types/react`.
- Corrigir o breakpoint móvel; substituir a sidebar fixa por drawer ou navegação compacta funcional.
- Remover template CSS/ativos não utilizados e carregar a tipografia escolhida de modo explícito.

**Backend**

- Criar cache do pipeline com invalidação por data/hash do XLSM e arquivos de configuração.
- Evitar recalcular o mesmo pipeline em múltiplas rotas da abertura inicial.
- Padronizar respostas e erros; adicionar modelos de resposta Pydantic.
- Mover caminhos e origens CORS para configuração de ambiente.

**Critérios de aceite**

- Nenhum erro ou aviso no console no fluxo principal.
- Tela utilizável em 390, 768, 1024 e 1440 px.
- Falha do backend gera mensagem acionável e botão de tentar novamente.
- Uma abertura do dashboard não relê o XLSM para cada card/endpoint.

### Fase 2 — Redesign orientado à decisão (4–6 dias)

- Criar design tokens e componentes base: botão, badge, card, campo, tabela, skeleton, alerta, drawer e modal.
- Redesenhar a Visão geral com KPIs semânticos, riscos por tipo, confiança e prioridades urgentes.
- Implementar filtros de prioridades: busca, família, risco, confiança, canal/parceiro e sell-out disponível.
- Exibir motivo principal, score, severidade e confiança diretamente na tabela.
- Abrir detalhe do SKU em página ou drawer, consumindo `/api/priorities/{sku}` e `/api/capacity/{family}`.
- Adicionar página de qualidade usando `/api/data-quality`.
- Integrar registro e histórico de feedback.
- Melhorar Casos com status legíveis, responsável, prazo, atualização e histórico.
- Comparar cenário oficial versus simulado, destacando alterações no ranking.

**Critérios de aceite**

- O usuário encontra e explica uma prioridade sem consultar dados brutos.
- O detalhe mostra evidência, origem, limitação e confiança.
- Todas as capacidades centrais do PRD ficam acessíveis no React.
- Cores nunca são o único meio de comunicar status.

### Fase 3 — Qualidade, testes e observabilidade (2–4 dias)

- Adicionar ESLint, formatter e verificação de tipos em scripts separados.
- Criar testes unitários para formatação, filtros e serviço de API.
- Criar testes de componentes para loading, erro, vazio e dados preenchidos.
- Criar smoke tests end-to-end para visão geral, detalhe, feedback, casos e cenário.
- Adicionar checagem de acessibilidade automatizada e revisão por teclado.
- Tornar a suíte Python executável por ambiente reproduzível e integrá-la ao fluxo de validação.
- Adicionar logs estruturados para duração do pipeline, hash da fonte e falhas de leitura.

**Critérios de aceite**

- Um comando valida frontend e backend.
- Fluxos críticos possuem teste automatizado.
- Regressões de responsividade e acessibilidade são detectadas antes da entrega.

### Fase 4 — Evolução posterior (opcional)

- Paginação/virtualização para bases maiores.
- Comparação entre execuções e explicação das mudanças de ranking.
- Exportação de visão filtrada e trilha de auditoria.
- Autenticação e autorização somente se o protótipo deixar de ser estritamente local.
- Avaliação de anomalias apenas depois de métricas e regras determinísticas estarem validadas.

## 5. Backlog priorizado

| Prioridade | Item | Impacto | Esforço estimado |
|---|---|---:|---:|
| P0 | Corrigir layout móvel e navegação responsiva | Muito alto | Baixo |
| P0 | Tratar loading/erro/retry das APIs | Muito alto | Baixo |
| P0 | Cachear pipeline do XLSM | Muito alto | Médio |
| P0 | Refatorar `App.tsx` e criar tipos | Alto | Médio |
| P1 | Redesenhar visão geral e tabela de prioridades | Muito alto | Médio |
| P1 | Implementar detalhe do SKU e evidências | Muito alto | Médio |
| P1 | Implementar filtros e qualidade dos dados | Alto | Médio |
| P1 | Integrar feedback e melhorar casos | Alto | Médio |
| P2 | Testes de frontend, E2E e acessibilidade | Alto | Médio |
| P2 | Padronizar API, configuração e logs | Alto | Médio |
| P2 | Atualizar README e ambiente reproduzível | Médio | Baixo |
| P3 | Comparação histórica e exportação | Médio | Médio/alto |

## 6. Sequência recomendada de entregas

1. **Entrega A — Fundação confiável:** responsividade, tratamento de erro, tipos, estrutura de componentes e cache.
2. **Entrega B — Interface operacional:** nova visão geral, prioridades com filtros e detalhe explicável.
3. **Entrega C — Fluxo completo:** qualidade, feedback, casos, cenários e execuções.
4. **Entrega D — Garantia de qualidade:** testes, acessibilidade, documentação e observabilidade.

O redesenho visual deve começar junto da correção estrutural da Fase 1. Aplicar apenas uma nova paleta sobre o componente atual produziria uma melhora superficial e manteria os problemas de uso, manutenção e responsividade.
