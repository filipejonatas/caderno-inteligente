# Plano da V2 — Caderno Inteligente

## 1. Objetivo da V2

Transformar o Protótipo V1 em uma aplicação demonstrável, navegável por URLs reais e validada contra o processo atual. A V2 deve responder melhor à pergunta central do desafio:

> Quais produtos exigem ação, quanto precisa ser analisado para produção, quais parceiros ou regiões apresentam risco ou oportunidade e quais evidências sustentam a recomendação?

A V2 não deve tentar otimizar toda a fábrica nem inventar vínculos que a fonte não contém. O objetivo é elevar a aderência ao desafio, a experiência de uso e a evidência de valor para a Semana 4.

## 2. Diagnóstico do projeto atual

### 2.1 Pontos fortes que devem ser preservados

- Pipeline completo da planilha até a interface publicada.
- Fonte XLSM tratada como somente leitura.
- Validação de estrutura, tipos, duplicidades, ausências e referências.
- Sete regras determinísticas auditáveis e score reproduzível.
- Ranking oficial separado de simulações.
- Previsão por SKU com comparação entre média móvel de três meses e sazonal ingênuo de doze meses.
- Holdout temporal de três meses e seleção pelo menor WAPE.
- Recomendação operacional transparente, com lote mínimo, carteira, previsão, estoque e produção aberta.
- Ausência de dado diferenciada de valor zero.
- Capacidade apresentada como contexto familiar, sem promessa de viabilidade individual.
- Registro de casos, decisões, efeito do dado do parceiro e tempo de análise.
- Persistência local em SQLite e PostgreSQL/Supabase em produção.
- API documentada e frontend responsivo já publicados.
- Cinquenta e oito testes Python declarados e verificação de build/typecheck do frontend funcionando.

### 2.2 Lacunas mais importantes

1. **Navegação sem rotas reais.** A aplicação troca páginas por estado dentro de `App.tsx`. A URL não muda, atualizar a página perde o contexto e não é possível compartilhar um link direto.
2. **Frontend concentrado.** Quase todas as páginas e o detalhe do SKU estão em `pages.tsx`, dificultando evolução, testes e carregamento por página.
3. **Carregamento excessivo.** O frontend busca overview, prioridades, execuções, casos, B2B2C, configuração, feedback e qualidade antes de renderizar a maioria das telas.
4. **Dimensão B2B2C ainda superficial.** A V1 apresenta cobertura por parceiro, mas não oferece uma visão parceiro–SKU–período com sell-in, sell-out, estoque estimado, região, risco e recomendação comercial.
5. **Recomendação comercial incompleta.** Existe recomendação operacional por SKU global, mas ainda não existe uma ação comercial explicável por parceiro.
6. **Validação da Semana 4 ainda não está materializada.** Falta comparar o protótipo com o processo atual, registrar casos não usados no ajuste, consolidar acertos e falhas e mostrar as mudanças feitas após os testes.
7. **Pouca comparação histórica.** Execuções são armazenadas, mas o usuário não consegue comparar duas versões do ranking.
8. **Sem testes automatizados do frontend.** O build e o typecheck passam, mas rotas, filtros, estados de erro e fluxos de decisão não possuem testes próprios.
9. **Ambiente Python local inconsistente.** A `.venv` atual aponta para um Python que não existe mais, e o Python 3.14 disponível não possui todas as dependências. A suíte precisa voltar a ser reproduzível antes da evolução.
10. **Segurança adequada apenas ao protótipo.** A aplicação pública não possui autenticação nem perfis, e os endpoints de escrita podem receber dados de demonstração.

## 3. Aderência ao desafio: situação atual e alvo da V2

| Requisito do desafio | V1 | Alvo da V2 |
|---|---|---|
| Produto/SKU | Atendido | Preservar e melhorar o detalhe |
| Parceiro/canal | Parcial e separado | Visão parceiro–SKU–período e filtros |
| Sell-in e sell-out | Agregado no detalhe | Comparação por parceiro quando observada |
| Estoque | Estoque global e estoque parceiro não explorado | Separar estoque do CD de estoque estimado do parceiro |
| Demanda e tendência | Atendido por SKU | Preservar e contextualizar por período |
| Previsão | Atendido por SKU | Exibir avaliação agregada e baseline |
| Oportunidade ou risco | Atendido no nível global | Adicionar sinais comerciais por parceiro |
| Recomendação comercial | Não atendido | Repor, monitorar ou investigar com evidências |
| Recomendação operacional | Atendido | Preservar cálculo e melhorar a jornada |
| Evidências | Atendido | Unificar origem, natureza, período e limitação |
| Região | Disponível na fonte, pouco utilizada | Filtro e resumo, sem alocação fictícia |
| Validação | Parcial no código | Central de validação visível e documentada |

## 4. Princípios obrigatórios

1. Preservar score, ranking, regras, processamento do Excel, forecast e recomendação atuais enquanto as novas funcionalidades são adicionadas.
2. Não duplicar valores globais por parceiro.
3. Não distribuir estoque, produção, capacidade ou previsão global entre parceiros sem vínculo explícito na fonte.
4. Identificar cada valor como observado, calculado, estimado, previsto ou ausente.
5. Não somar previsão e carteira quando puderem representar a mesma demanda.
6. Não apresentar capacidade por família como garantia de atendimento de um SKU.
7. Toda recomendação deve exibir evidências, limitações, confiança e revisão humana obrigatória.
8. Dados insuficientes devem gerar `não disponível` ou `investigar dados`, nunca zero inventado.
9. A V2 deve melhorar a demonstração e a validação antes de adicionar modelos mais complexos.
10. Alterações de API devem ser aditivas. Contratos existentes continuam válidos.

## 5. Arquitetura de navegação da V2

### 5.1 Dependência recomendada

Adicionar `react-router-dom`. O ganho justifica a dependência: rotas declarativas, parâmetros, query string, navegação por histórico, rota 404 e suporte confiável a links diretos.

### 5.2 Mapa de rotas

| URL | Página | Observação |
|---|---|---|
| `/` | Visão geral | Centro de decisão |
| `/guia` | Guia de uso | Deve funcionar com a API offline |
| `/prioridades` | Prioridades | Busca e filtros na URL |
| `/previsoes` | Previsão e recomendações | Todos os SKUs |
| `/skus/:sku` | Detalhe do SKU | Página compartilhável; substitui o drawer como destino principal |
| `/parceiros` | Visibilidade B2B2C | Lista, cobertura e regiões |
| `/parceiros/:codigo` | Detalhe do parceiro | Matriz parceiro–SKU–período |
| `/casos` | Casos | Acompanhamento operacional |
| `/qualidade` | Qualidade dos dados | Integridade e cobertura |
| `/cenarios` | Cenários | Simulação sem persistir pesos |
| `/execucoes` | Execuções | Snapshots e comparação |
| `/decisoes` | Decisões | Feedback humano |
| `/validacao` | Validação da V2 | Evidências da Semana 4 |
| `*` | Página não encontrada | Link para a visão geral |

### 5.3 Regras de navegação

- Menu lateral deve usar links reais e manter estado ativo pela URL.
- Filtros relevantes devem usar query parameters, por exemplo `/prioridades?familia=Escolar&confianca=baixa`.
- Voltar e avançar do navegador devem funcionar.
- Atualizar uma URL interna deve manter a página atual.
- O detalhe de SKU deve ter URL própria e botão de retorno previsível.
- O drawer pode permanecer como visualização rápida em desktop, mas deve sincronizar a URL ou encaminhar para `/skus/:sku`.
- Criar rewrite da SPA no projeto do frontend da Vercel para enviar rotas desconhecidas ao `index.html`.
- Usar lazy loading por rota para reduzir o bundle inicial.

### 5.4 Organização proposta do frontend

```text
frontend/src/
  app/
    router.tsx
    AppShell.tsx
    ErrorBoundary.tsx
  components/
    layout/
    data-display/
    feedback/
    forms/
  pages/
    overview/
    priorities/
    forecasts/
    sku-detail/
    partners/
    partner-detail/
    cases/
    quality/
    scenarios/
    runs/
    decisions/
    validation/
    guide/
    not-found/
  hooks/
    useApiResource.ts
    useUrlFilters.ts
  services/
    api.ts
  types/
```

Não é necessário fragmentar cada pequeno componente. A separação deve acompanhar páginas e responsabilidades reais.

## 6. Plano de implementação por etapas

### Etapa 0 — Recuperar a linha de base

**Prioridade:** bloqueante  
**Timebox para IA:** 45 a 90 minutos

**Status em 05/10/2026:** concluída com `.venv` em Python 3.12.14, dependências consistentes, 61 testes Python aprovados e `npm run check` aprovado. O comando consolidado é `./scripts/validate.ps1`.

#### Implementação

- Remover e recriar a `.venv` com uma versão suportada do Python, preferencialmente 3.12 ou 3.13.
- Instalar `requirements.txt` e `requirements-dev.txt`.
- Confirmar o carregamento do FastAPI e da planilha.
- Executar a suíte Python completa.
- Manter `npm run check` verde.
- Documentar um comando confiável para validar backend e frontend.

#### Critérios de aceite

- Todos os testes Python são coletados e executados.
- `npm run check` passa.
- Nenhum contrato existente muda.

### Etapa 1 — Rotas reais e modularização do frontend

**Prioridade:** obrigatória, requisito do usuário  
**Timebox para IA:** 3 a 4 horas

**Status:** concluída em 05/10/2026

#### Implementação

- Adicionar `react-router-dom`.
- Criar o mapa de rotas da seção 5.
- Converter botões do menu em links acessíveis.
- Separar cada página de `pages.tsx` para seu próprio módulo.
- Transformar o detalhe do SKU em página de rota.
- Manter o Guia de uso independente da API.
- Criar rota 404.
- Adicionar configuração de rewrite para deep links na Vercel.
- Preservar o mesmo design system e comportamento responsivo.

#### Resultado implementado

- Rotas reais, menu com links acessíveis, histórico do navegador e 404 adicionados com `react-router-dom`.
- Páginas existentes separadas em módulos e carregadas sob demanda.
- Filtros de Prioridades e Previsões sincronizados com query parameters.
- Detalhe compartilhável disponível em `/skus/:sku`, sem alterar seu contrato de API.
- Guia de uso independente do carregamento da API.
- Rewrite de SPA configurado em `frontend/vercel.json`.
- As rotas `/parceiros/:codigo` e `/validacao` permanecem reservadas às etapas 4 e 8, que implementam o conteúdo correspondente sem inventar dados ou granularidade.

#### Critérios de aceite

- Cada item do menu altera a URL.
- URLs internas abrem diretamente após atualização.
- Voltar e avançar funcionam.
- `/skus/CI-0041` abre diretamente o detalhe correto.
- `/guia` funciona com a API indisponível.
- Não existe regressão visual relevante.

### Etapa 2 — Carregamento por página e estados de interface

**Prioridade:** alta  
**Timebox para IA:** 2 a 3 horas

#### Implementação

- Substituir `loadDashboard()` como dependência global obrigatória por chamadas específicas de cada rota.
- Criar um hook leve para loading, erro, cancelamento e nova tentativa, sem adicionar biblioteca de cache.
- Manter em contexto apenas dados pequenos e realmente globais, como configuração e resumo do usuário.
- Carregar forecasts somente em `/previsoes` e detalhes de SKU somente em `/skus/:sku`.
- Adicionar skeletons coerentes, estados vazios e mensagens de erro por seção.
- Evitar que uma falha em feedback ou execuções impeça a visão geral de abrir.

#### Critérios de aceite

- A visão geral não depende de todos os endpoints do sistema.
- Uma falha isolada afeta apenas a página ou seção correspondente.
- Requisições antigas são canceladas ao trocar rapidamente de rota.

### Etapa 3 — Jornada visual de decisão

**Prioridade:** alta  
**Timebox para IA:** 3 a 4 horas

#### Implementação

- Reorganizar a Visão geral em três blocos: `o que exige atenção`, `ações sugeridas` e `qualidade da decisão`.
- Incluir atalhos visíveis para prioridades, previsões, parceiros e validação.
- Criar cabeçalho consistente com título, contexto, atualização e última carga.
- Padronizar filtros, tabelas, badges, alertas, tooltips e estados vazios.
- Melhorar densidade visual das tabelas sem reduzir legibilidade.
- Mostrar sempre a diferença entre prioridade de análise e ação recomendada.
- Aplicar uma hierarquia visual sóbria: uma cor primária, cores semânticas e menos elementos decorativos.
- Revisar a experiência em 390, 768, 1024 e 1440 pixels.

#### Critérios de aceite

- Em menos de 30 segundos, um usuário identifica o principal risco e abre sua evidência.
- O usuário entende por que um SKU pode ser prioridade alta e ter recomendação `sem ação necessária`.
- Não há overflow horizontal não intencional em celular.

### Etapa 4 — Visão parceiro–SKU e recomendação comercial

**Prioridade:** obrigatória para maior aderência ao desafio  
**Timebox para IA:** 5 a 7 horas

#### Dados disponíveis que sustentam a etapa

- Oito parceiros/canais cadastrados, com tipo, região, UF, cidade e canal principal.
- Todos os 53 pedidos da carteira possuem `Cliente/Canal` relacionado aos códigos cadastrados.
- Sell-in e sell-out mensal para 50 pares parceiro–SKU.
- Sell-out com estoque estimado do cliente e natureza do dado.
- Cinco parceiros e trinta SKUs aparecem no recorte observado de sell-out.

#### Núcleo Python

- Criar `partner_insights.py`.
- Construir uma visão por `parceiro + SKU + mês` usando somente vínculos existentes.
- Calcular, quando possível:
  - sell-in recente;
  - sell-out recente;
  - diferença no período comparável;
  - estoque estimado do parceiro;
  - cobertura aproximada baseada em sell-out observado;
  - atualidade e continuidade do dado;
  - pedidos em carteira daquele parceiro;
  - região e canal.
- Classificar a natureza de cada campo.
- Criar sinais comerciais determinísticos e configuráveis:
  - `REPOSITION_OPPORTUNITY`: giro observado e cobertura estimada baixa;
  - `PARTNER_EXCESS_RISK`: estoque estimado alto e giro baixo;
  - `SELLIN_SELLOUT_DIVERGENCE`: diferença relevante em períodos comparáveis;
  - `STALE_PARTNER_DATA`: dado antigo ou descontínuo;
  - `INSUFFICIENT_PARTNER_DATA`: sem informação suficiente.
- Gerar recomendação comercial apenas entre:
  - `avaliar reposição`;
  - `monitorar estoque do parceiro`;
  - `investigar divergência`;
  - `solicitar atualização dos dados`;
  - `sem recomendação por dados insuficientes`.
- Não usar a recomendação comercial para alterar silenciosamente o ranking operacional global.

#### API aditiva

- `GET /api/partners`
- `GET /api/partners/{codigo}`
- `GET /api/partners/{codigo}/skus`
- `GET /api/commercial-recommendations`
- Permitir filtros por parceiro, SKU, região, canal, ação e qualidade do dado.

#### Frontend

- Evoluir `/parceiros` com KPIs, filtros por região/canal e ordenação.
- Criar `/parceiros/:codigo` com:
  - resumo do parceiro;
  - cobertura e atualidade;
  - matriz de SKUs;
  - sell-in, sell-out e estoque estimado;
  - riscos e oportunidades;
  - recomendação comercial e evidências;
  - decisões já influenciadas pelo dado desse parceiro.
- No detalhe do SKU, adicionar seção `Contexto dos parceiros` sem misturar esses valores ao estoque global do CD.

#### Critérios de aceite

- Cada número pode ser rastreado ao parceiro, SKU e período de origem.
- Dados globais não são repetidos para cada parceiro.
- O sistema não recomenda reposição quando sell-out ou estoque estimado não sustentam o cálculo.
- A interface diferencia claramente recomendação comercial de recomendação operacional.

### Etapa 5 — Central de validação da Semana 4

**Prioridade:** obrigatória para a entrega da V2  
**Timebox para IA:** 4 a 6 horas

#### Objetivo

Transformar testes técnicos em evidência visível de aplicabilidade. A página `/validacao` deve responder aos quatro critérios da Semana 4.

#### Comparação com o processo atual

- Exibir linha de base informada pela empresa: 22 horas semanais de análise, 31% de erro médio do forecast, 89% de pedidos no prazo e 78% de aderência ao plano.
- Separar claramente indicadores informados dos recalculados.
- Consolidar os minutos registrados nos feedbacks sem afirmar ganho antes de haver amostra suficiente.
- Mostrar meta de tempo de análise: até 8 horas semanais.

#### Avaliação da previsão

- Comparar cada modelo candidato com uma baseline explícita.
- Consolidar:
  - SKUs elegíveis;
  - SKUs com dados insuficientes;
  - WAPE mediano e ponderado;
  - modelo vencedor por SKU;
  - quantidade de casos em que o modelo não superou a baseline.
- Não apresentar uma média isolada sem tamanho da amostra.

#### Casos representativos congelados

Criar uma pequena suíte de casos não usada para ajustar pesos ou regras:

1. ruptura com carteira e sem produção;
2. produção posterior à data prometida;
3. excesso de estoque;
4. prioridade alta sem necessidade de produção adicional;
5. forecast com dados insuficientes;
6. parceiro com oportunidade de reposição sustentada;
7. parceiro com dado ausente ou desatualizado;
8. pressão de capacidade que exige revisão humana.

Cada caso deve registrar entrada, saída esperada, saída obtida, resultado, limitação e ajuste realizado.

#### Comportamento seguro

- Testar ausência de sell-out, holdout com demanda zero, forecast insuficiente, capacidade agregada, erro de API e SKU inexistente.
- Confirmar que o sistema recusa falsa precisão e exige revisão humana.

#### API e interface

- Adicionar `GET /api/validation/summary`.
- Criar `/validacao` com KPIs, tabela de casos, desempenho dos modelos, falhas conhecidas e histórico de ajustes.
- Gerar exportação CSV ou impressão amigável do resumo, sem nova dependência.

#### Critérios de aceite

- A página distingue baseline informada, resultado recalculado e meta.
- Casos de validação não alteram pesos nem modelos.
- Falhas são mostradas, não escondidas.
- A equipe consegue usar a página como evidência na entrega da Semana 4.

### Etapa 6 — Comparação entre execuções

**Prioridade:** média  
**Timebox para IA:** 3 a 4 horas

#### Implementação

- Ampliar snapshots para preservar os campos necessários à comparação.
- Adicionar endpoint aditivo de comparação entre duas execuções.
- Exibir:
  - entradas e saídas do ranking;
  - mudança de posição e score;
  - mudança de confiança;
  - novos sinais;
  - alteração de forecast e recomendação;
  - mudança de cobertura B2B2C.
- Não criar comparação quando os snapshots não tiverem dados compatíveis; explicar a limitação.

#### Critérios de aceite

- O usuário consegue explicar por que uma prioridade mudou.
- A comparação preserva hash da fonte, data e configuração.

### Etapa 7 — Testes do frontend, acessibilidade e robustez

**Prioridade:** alta  
**Timebox para IA:** 3 a 5 horas

#### Implementação

- Adicionar Vitest, React Testing Library e ambiente DOM de teste.
- Cobrir:
  - resolução de todas as rotas;
  - link ativo do menu;
  - deep link de SKU e parceiro;
  - query parameters dos filtros;
  - loading, erro, vazio e sucesso;
  - Guia offline;
  - rota 404;
  - recomendação com dados insuficientes;
  - navegação por teclado no menu e formulários.
- Adicionar smoke test de contratos críticos do frontend contra fixtures.
- Revisar títulos, landmarks, foco, contraste e rótulos de formulário.
- Verificar que segredos de banco não aparecem no bundle.

#### Critérios de aceite

- `npm run check` executa typecheck, testes e build.
- Não há erros críticos de acessibilidade no fluxo principal.
- As rotas principais funcionam em viewport móvel e desktop.

### Etapa 8 — Segurança e modo de demonstração

**Prioridade:** média; executar após as etapas de avaliação  
**Timebox para IA:** 2 a 4 horas

#### Implementação mínima

- Adicionar configuração explícita de modo demonstração.
- Permitir desabilitar endpoints de escrita na publicação pública ou limpar dados de demonstração com procedimento documentado.
- Restringir CORS aos domínios esperados.
- Validar tamanho e conteúdo de campos de texto.
- Evitar retorno de detalhes internos em erros de produção.
- Registrar falhas da API sem imprimir `DATABASE_URL`.

#### Evolução posterior

- Supabase Auth e perfis `visualizador`, `analista` e `administrador`.
- A autenticação completa não deve bloquear a entrega da Semana 4 se não houver requisito de uso real externo.

### Etapa 9 — Documentação, deploy e demonstração

**Prioridade:** obrigatória  
**Timebox para IA:** 2 a 3 horas

#### Implementação

- Atualizar README, arquitetura, API, cálculos, regras e Guia de uso.
- Documentar o mapa de rotas e o rewrite da Vercel.
- Criar `docs/semana-4-validacao-v2.md` com método, amostra, resultados, falhas e mudanças.
- Atualizar o roteiro de demonstração para cinco minutos:
  1. problema e linha de base;
  2. visão geral;
  3. prioridade e recomendação operacional;
  4. parceiro e recomendação comercial;
  5. validação e comportamento seguro.
- Executar suíte Python, testes do frontend e build.
- Fazer smoke test das URLs publicadas depois do deploy manual.

## 7. Ordem recomendada e recorte de entrega

### V2 obrigatória — melhor retorno para a Semana 4

1. Etapa 0 — recuperar ambiente e linha de base.
2. Etapa 1 — rotas reais e modularização.
3. Etapa 2 — carregamento por página.
4. Etapa 4 — parceiro–SKU e recomendação comercial.
5. Etapa 5 — central de validação.
6. Etapa 3 — polimento da jornada visual.
7. Etapa 7 — testes e acessibilidade.
8. Etapa 9 — documentação e demonstração.

**Estimativa com execução por IA:** 22 a 32 horas, divididas em etapas independentes e sempre encerradas com testes.

### V2 enxuta — caso o prazo seja curto

1. Rotas reais e detalhe compartilhável.
2. Página de parceiro usando somente os 50 pares observados.
3. Três recomendações comerciais seguras: repor, monitorar e investigar.
4. Central de validação com oito casos congelados.
5. Testes das rotas e documentação da Semana 4.

**Estimativa com execução por IA:** 12 a 16 horas.

### Extensões depois da V2

- Comparação entre execuções.
- Autenticação e perfis.
- Detecção de anomalias, somente se superar regras simples em dados separados.
- Integrações reais com parceiros.
- Otimização de capacidade e alocação, somente com vínculos e restrições reais.

## 8. O que não implementar agora

- Chatbot genérico para consultar a planilha.
- Modelo complexo apenas para parecer mais inteligente.
- Previsão por parceiro ou região com histórico insuficiente.
- Alocação automática de capacidade por SKU.
- Ordem de produção automática.
- Benefício comercial definitivo para parceiros.
- Dados sintéticos misturados aos resultados observados sem rótulo.
- Microserviços, filas ou infraestrutura que não resolvam um critério do desafio.

## 9. Estratégia de testes da V2

### Backend

- Regressão dos contratos existentes.
- Unidade para cada novo indicador e sinal comercial.
- Granularidade e proteção contra joins cartesianos.
- Ausência versus zero.
- Períodos comparáveis de sell-in e sell-out.
- Atualidade do dado do parceiro.
- Comportamento seguro da recomendação.
- Contratos das rotas aditivas.

### Frontend

- Rotas, deep links e 404.
- Filtros sincronizados com URL.
- Estados loading, erro, vazio e sucesso.
- Guia sem API.
- Detalhe de SKU e parceiro.
- Responsividade e navegação por teclado.

### Produto

- Oito casos congelados da Semana 4.
- Comparação com baseline e amostra informada.
- Teste moderado com pelo menos três pessoas: PCP, Comercial e alguém sem contexto prévio.
- Registrar tarefa, tempo, entendimento, erro, dúvida e sugestão.

## 10. Métricas de sucesso

### Produto

- Tempo mediano para encontrar a principal prioridade.
- Tempo mediano para explicar uma recomendação.
- Percentual de usuários que distinguem prioridade de ação sugerida.
- Percentual de recomendações aceitas, alteradas, rejeitadas ou investigadas.
- Decisões influenciadas por dado do parceiro.
- Cobertura e atualidade de sell-out.

### Modelo

- SKUs elegíveis e insuficientes.
- WAPE ponderado e mediano no holdout.
- Ganho ou perda contra baseline.
- Percentual de casos em que o modelo sinaliza corretamente insuficiência de dados.

### Técnica

- Suítes Python e frontend verdes.
- Build do frontend sem erro.
- Deep links funcionando na Vercel.
- Nenhum segredo no bundle.
- Nenhuma duplicação de volume por mudança de granularidade.

## 11. Definição de pronto da V2

A V2 estará pronta quando:

- cada página possuir URL própria e compartilhável;
- atualizar uma rota interna não causar 404;
- o código do frontend estiver separado por páginas e responsabilidades;
- o usuário conseguir sair do risco global e chegar à evidência do SKU;
- o usuário conseguir analisar um parceiro, seus SKUs e a qualidade do dado;
- recomendações comerciais e operacionais estiverem claramente separadas;
- valores globais não forem distribuídos artificialmente;
- previsão e recomendação continuarem reproduzíveis e seguras;
- a página de validação apresentar baseline, casos, resultados, falhas e ajustes;
- a equipe conseguir demonstrar o fluxo completo em até cinco minutos;
- os testes Python e do frontend passarem;
- a documentação refletir exatamente o comportamento publicado.

## 12. Comando sugerido para uma IA implementar o plano

```text
Implemente a etapa N de docs/plano-v2-prototipo-top.md. Preserve os contratos existentes, score, ranking, regras, processamento do Excel, previsão e recomendação operacional. Não invente granularidade nem distribua dados globais por parceiro. Toda nova API deve ser aditiva. Ao final, execute os testes Python aplicáveis e npm run check, informe arquivos modificados, resultados, limitações e passos de deploy. Não altere segredos nem faça deploy.
```
