# Discovery e plano SDD: navegação com história, Início como painel e atalho para Usuários

> Escrito em 11/10/2026. Nenhum código foi alterado. Parte 1 = fatos verificados no código (arquivo:linha). Parte 2 = plano de implementação por IA (SDD: spec → critérios de aceite → tarefas → verificação).
> As regras do projeto continuam valendo: dado ausente nunca vira zero; campo novo lido pelo frontend entra em `frontend/src/test/contract-keys.json`; rota ou bloco novo respeita `volume-budget.json`; o usuário faz o commit.

**Pedido:** (1) a navegação deve contar uma história; (2) a tela inicial deve ser um painel em que dê para ver tudo com facilidade; (3) `/usuarios` existe, mas nenhum atalho leva até lá.

---

## Parte 1. Discovery

### 1.1 Como a navegação é hoje

| # | Fato | Onde |
|---|---|---|
| N1 | Menu superior com 8 grupos, em ordem de **área de conhecimento**, não de fluxo: Início, Planejamento, SKUs, Financeiro, Comercial, Acompanhamento, Confiança, Bastidores. | `components.tsx:71-80` |
| N2 | Cada grupo mostra só o nome (`<strong>`). Não há descrição, pergunta nem indicação de ordem. As descrições existem em `navigation[]` (`:49-68`), mas só alimentam o título da aba do navegador. | `components.tsx:113-118` |
| N3 | Abas internas (SubNav) existem só em 4 grupos (Comercial, Bastidores, Acompanhamento, Confiança). Planejamento tem 3 páginas (`/fila`, `/capacidade`, `/cenarios`) **sem abas**: chega-se a elas por botões soltos ("Ver capacidade", "Simular pesos"). | `components.tsx:82-87`, `OperationalQueuePage.tsx:100` |
| N4 | O fio entre telas é feito por links pontuais, e pára cedo. Contagem de destinos: SKU (18 links), `/fila` (4), `/capacidade` (3). A **Capacidade** termina em "Voltar à fila"; a **Validação**, em "Auditoria completa". Nenhuma tela diz "e agora?". | grep de `<Link` em `pages/` e `components/` |
| N5 | A história **já existe, mas escrita fora do produto**: o roteiro de 5 minutos (`docs/roteiro-demonstracao.md`) tem cinco atos (decisões de hoje → quem atender primeiro → capacidade → visibilidade do consumidor → por que confiar). O Guia (`/guia`) tem 3 trilhas por papel (PCP, Comercial, Gestão), mas é página estática escondida no botão "Ajuda". | `GuidePage.tsx:5-9` |
| N6 | O critério de clareza do projeto é "em 5 segundos, a pessoa sabe o que fazer a seguir", com uma pergunta por tela. Isso é a semente do storytelling: cada tela já tem uma pergunta (`docs/criterio-de-clareza.md`). | tabela do doc |
| N7 | Todo título de página vem de `navigation[]`; o foco vai ao `h1` a cada troca de rota (acessibilidade). Qualquer mudança de rótulo quebra testes de navegação, que checam os 8 nomes exatos. | `App.tsx:75-96`, `test/navigation.test.tsx:12-18` |

**Leitura:** o menu responde "o que existe", e não "o que faço agora e depois". A ordem lógica do trabalho do PCP (ver o que arde → decidir → checar se cabe → entender o impacto → confiar → ajustar a base) é a ordem do roteiro, mas o menu a embaralha (SKUs e Financeiro entre Planejamento e Comercial; Acompanhamento depois de Comercial).

### 1.2 Como o Início é hoje

| # | Fato | Onde |
|---|---|---|
| I1 | O Início **já é um painel**: 4 cartões de indicador, "Decisões de hoje" (5 linhas), mosaico 2×2 (falta de estoque por semana, faturamento por família, top 5 SKUs, canais diretos). | `OverviewPage.tsx:16-27` |
| I2 | O título visível é "Indicadores" e a descrição do `navigation` é "Indicadores": o nome conta o que é (números), não a pergunta. O critério de clareza diz que o Início responde "O que olho primeiro?" com **o primeiro SKU da fila e o porquê, em uma frase**. Isso **não está mais na tela** (o componente `AttentionFocus` existe em `components/`, mas o Início não o usa; comentário em `OverviewPage.tsx:10` confirma que a fila ficou no Planejamento). O documento de clareza está desatualizado em relação ao código. | `OverviewPage.tsx:10`, `docs/criterio-de-clareza.md` linha do Início |
| I3 | Os 4 cartões cobrem: faturamento, ruptura, produção a liberar, pedidos sem OP. **Não cobrem** o que o roteiro destaca: capacidade (Escolar não cabe), visibilidade do consumidor (75,1%), confiança (erro de 8,0%, 34/34 casos), base ativa/data de planejamento. Cada um desses vive em outra página e o Início não sinaliza que existe. | `OverviewPanel.tsx:39-57`; roteiro §2-§5 |
| I4 | Três dos quatro cartões levam a `/fila`; ruptura usa `?sinal=ruptura`. O painel **mostra** mas pouco **encaminha**: só o bloco de faturamento e o de canais têm botão "Ver…". | `OverviewPanel.tsx:166,188` |
| I5 | O Início tem orçamento de volume apertado: `fixed 215`, `blocks 8`, `numbers 20`, `alerts 1`. Hoje o painel usa 8 blocos (intro, 4 cartões contam como 1 lista, decisões, 4 gráficos). **Adicionar blocos exige reabrir o orçamento conscientemente** (uma decisão, não um ajuste silencioso). | `test/volume-budget.json:4-14` |
| I6 | Cada bloco carrega e falha sozinho (`useApiResource` + `BlockError`). Qualquer card novo precisa seguir isso; o resto da página não pode cair junto. | `OverviewPanel.tsx:15-22` |
| I7 | A API já fornece o necessário para quase tudo: `overview` (ruptura, decisões de hoje, estoque projetado), `revenueForecast`, `productionPlan`, `directChannels`. Para capacidade, visibilidade, confiança e base ativa existem endpoints próprios (`/capacidade`, `/carteira`, `/validacao`, `/dados/atualizar`) que o Início **não** chama hoje. Isso é custo de rede e de partida a frio na Vercel (primeira leitura da planilha é a mais lenta). | `App.tsx:42-49`, roteiro "Antes de apresentar" |

**Leitura:** o pedido "dashboard onde fique fácil visualizar tudo" não está atendido porque o painel mostra **uma fatia** (dinheiro e ruptura), não **o fluxo inteiro**. Falta (a) a pergunta da tela, (b) o resumo de cada etapa seguinte e (c) o convite para avançar.

### 1.3 Por que `/usuarios` não tem atalho

| # | Fato | Onde |
|---|---|---|
| U1 | A rota existe e é tratada como "página estática" (sem refresh, sem banner). | `App.tsx:83,96,99,122` |
| U2 | **O único atalho** é o botão "Usuários" dentro do cartão da tela **Atualizar dados** (que fica em Bastidores › Atualizar dados). Ou seja: a pessoa precisa saber que cadastrar usuário mora dentro de "atualizar a base". | `DatasetUpload.tsx:196` |
| U3 | `/usuarios` **não está** em `navigation[]`, nem em `menuGroups`, nem em `subNavigation`. Por isso `groupFor('/usuarios')` devolve `undefined`: nenhum item do menu fica ativo e nenhuma sub-aba aparece quando se está na página. O título vem de um caso especial hardcoded em `App.tsx:83`. | `components.tsx:49-87` |
| U4 | O nome do usuário no topo (`topbar-user`) é um `<span>` sem link. É o lugar onde a maioria dos produtos põe "minha conta / usuários". | `components.tsx:154` |
| U5 | Permissão: **não há papéis**; qualquer usuário logado cadastra outros (`docs/decisions.md:252`). A API do POST exige `WRITE_ENABLED=true`; o GET exige só login. Então um atalho visível para todos é coerente com a regra atual, mas a tela precisa dizer, sem rodeio, quando o cadastro está desabilitado (hoje o erro só aparece depois de enviar). | `docs/api.md:417` |
| U6 | Testes que travam o desenho atual: o menu tem exatamente 8 itens (`navigation.test.tsx:12`); `toda rota de página pertence a exatamente um grupo` (`:50`) — ao inserir `/usuarios` em `navigation[]`, ele precisa de dono; `login-gate` testa `/usuarios` sem sessão. | `test/` |

**Leitura:** é uma falha de **arquitetura de informação**, não de código: a rota foi criada como dependência da tela de upload e nunca ganhou lugar próprio. Duas pessoas diferentes a procurariam em lugares diferentes (menu "Bastidores" ou o nome no topo).

### 1.4 Restrições herdadas do sistema de design

- Identidade "ordem de produção": papel `#f4f6f9`, tinta `#16213a`, azul-caneta `#2d3fe0`, Archivo variável condensada (`--condensed`), raios 6/12, 5 tamanhos `--text-*` (memória `redesign-folha-pautada`). **Não é uma página nova:** o trabalho aqui é de estrutura e conteúdo, dentro dos tokens.
- Cor só para urgência/estado/ação (`criterio-de-clareza.md`). Azul só ação e link. Testes `contrast`, `legibility`, `a11y`, `clarity`, `volume` guardam isso.
- Menu superior horizontal vira gaveta abaixo de 820 px (`styles.css:659-675`); 8 itens já apertam em 960-1180 px (`:644-657`). **Um 9º item de menu não cabe sem quebrar o layout.**
- Animação de entrada já aplicada a todos os blocos (`styles.css:636-640`); evitar somar outra.
- Container de 1100 px (`styles.css:89`): o painel cabe em 2 colunas, não em 3.

### 1.5 Perguntas em aberto (decidir antes do código)

| # | Pergunta | Recomendação |
|---|---|---|
| Q1 | Reordenar e renomear os 8 grupos do menu para seguir a história, ou manter o menu e contar a história **dentro** do Início? | Manter 8 grupos e os nomes (custo baixo, testes e URLs intactos); reordenar para seguir o fluxo; acrescentar uma **linha de pergunta** em cada grupo (ver §2.3). Renomear só se o usuário pedir. |
| Q2 | Onde fica Usuários? | No **menu do usuário** no topo (nome vira botão com "Usuários" e "Sair"), **e** como aba em Bastidores. Dois caminhos, nenhum item de menu novo. |
| Q3 | O Início mostra "tudo" ou o resumo de cada etapa com link? | Resumo de **5 etapas** com 1 número e 1 frase cada, links para a tela completa. Não duplicar gráficos. |
| Q4 | Quanto custa chamar 3 endpoints a mais no Início? | Medir antes (tarefa T0). Se a partida a frio passar de ~3 s, a etapa vira resumo vindo do `overview` (campo novo no backend) em vez de 3 chamadas. |
| Q5 | Abrir o orçamento de volume do Início? | Sim, de forma explícita e justificada em `volume-budget.json` (hoje 8 blocos; proposta 9, trocando o bloco "Indicadores" por "A jornada"). |

---

## Parte 2. Plano de implementação (SDD)

### 2.1 Spec (o quê)

**S1. Atalho para Usuários.** Toda pessoa logada alcança `/usuarios` em ≤ 2 cliques a partir de qualquer tela, sem passar por Atualizar dados. Em `/usuarios`, o menu e o título ficam coerentes (item de Bastidores ativo, aba "Usuários" ativa).

**S2. Início como painel da jornada.** O Início passa a responder "O que olho primeiro?" e mostra **uma faixa por etapa** do trabalho do PCP, na ordem em que se faz:

| Etapa | Pergunta | Número-âncora (fonte) | Vai para |
|---|---|---|---|
| 1. Ver | O que arde agora? | SKUs com risco de ruptura (`overview.rupture_sku_count`) | `/fila?sinal=ruptura` |
| 2. Decidir | O que decido hoje? | Decisões até a data X (`overview.decisions_today.count`) | `/fila` |
| 3. Caber | Dá para produzir? | Semanas/linhas sem capacidade (`/api/capacity`) | `/capacidade` |
| 4. Atender | Quem recebe primeiro e quanto rende? | R$ sem cobertura (`overview`/carteira) e faturamento previsto | `/parceiros`, `/faturamento` |
| 5. Confiar | Posso confiar? | Erro da previsão e casos aprovados (`/api/validation`) | `/validacao` |

Mantém: cartões de indicador e mosaico atuais, **abaixo** da jornada (continuam sendo o "ver tudo"). Cada faixa carrega e falha sozinha; falha diz "indisponível", nunca zero.

**S3. Navegação que conta a história.**
- Menu reordenado pela sequência acima: Início, Planejamento, Financeiro, Comercial, SKUs, Acompanhamento, Confiança, Bastidores (decisão Q1; confirmar com o usuário).
- Cada página termina com um rodapé "**Próximo passo**" (um link, uma frase) que a liga à etapa seguinte da jornada; a última etapa devolve ao Início.
- Planejamento ganha SubNav (Fila, Capacidade, Cenários); hoje são botões soltos (N3).
- O Guia deixa de ser o único lugar da história: a jornada do Início é a versão viva dele; o Guia aponta para ela.

### 2.2 O que NÃO muda (limites)
Rotas e URLs (todas as existentes continuam abrindo); regras de cálculo; contrato da API existente (só campos novos, opcionais); paleta e tipografia; autenticação e permissões (continua sem papéis).

### 2.3 Design (como; dentro do sistema existente)

- **Conceito:** a jornada é uma **régua de produção** horizontal, como a "pauta" do projeto: 5 etapas em linha sobre um fio de 2 px; a etapa com mais urgência leva a margem vermelha (mesma regra da fila), as demais ficam em tinta. Número grande condensado (`--condensed`, `--text-page`), pergunta em `--text-meta`. Sem ícones decorativos, sem numeração fingida: aqui a numeração **é** válida porque o conteúdo é uma sequência (ver, decidir, caber, atender, confiar).
- **Alinhamento:** à esquerda; 5 colunas ≥ 1100 px, 2 colunas ≤ 820 px, 1 coluna ≤ 480 px (a ordem vertical mantém a sequência).
- **Menu:** cada item ganha `title`/`aria-describedby` com a pergunta da área; sem texto extra no menu visível (8 itens já apertam).
- **Menu do usuário:** o `span.topbar-user` vira `<details>`/botão com 2 itens: "Usuários" e "Sair". Foco visível, Esc fecha, funciona na gaveta mobile.
- **Rodapé "Próximo passo":** componente `NextStep` com uma linha: *"Fila vista. Agora: ver se cabe na linha →"*; sem animação própria.
- **Movimento:** nenhum novo. A jornada herda a entrada já existente do `.section-card`.

### 2.4 Tarefas (ordem de execução, cada uma verificável)

| # | Tarefa | Arquivos | Verificação |
|---|---|---|---|
| T0 | **Medir** custo de `/api/capacity` e `/api/validation` na partida a frio; decidir Q4. | nenhum (relatório curto neste doc) | tempos registrados; decisão anotada |
| T1 | **Usuários no menu do usuário e em Bastidores.** Entrada `users` em `navigation[]`, aba em `subNavigation.backstage`, caminho em `menuGroups.backstage.paths`; remover caso especial de `App.tsx:83`. Menu do usuário no `Topbar`. | `components.tsx`, `App.tsx`, `styles.css` | `groupFor('/usuarios')` = backstage; teste novo: link "Usuários" no topo leva a `/usuarios` com aba ativa; `navigation.test` atualizado (abas de Bastidores passam a 5) |
| T2 | **Aviso de cadastro desabilitado** em `/usuarios` quando `systemInfo.write_enabled === false` (botão desabilitado com o motivo, como em Atualizar dados). | `UsersPage.tsx`, `App.tsx` (hoje página estática não lê `systemInfo`) | `users.test`: com escrita desligada, botão desabilitado e mensagem visível |
| T3 | **SubNav de Planejamento** (Fila, Capacidade, Cenários); manter os botões atuais. | `components.tsx` | `navigation.test`: abas de Planejamento e item ativo |
| T4 | **Componente `NextStep`** + texto por rota em um mapa único (`journey.ts`: etapa, pergunta, próximo). Aplicar em Fila, Capacidade, Oportunidades/Parceiros, Faturamento, Validação. | `components/NextStep.tsx`, `journey.ts`, 5 páginas | teste: cada rota da jornada tem exatamente 1 `NextStep` e o link existe em `navigation[]`; última etapa aponta para `/` |
| T5 | **`JourneyStrip` no Início** com as 5 etapas; cada etapa em hook próprio (`useApiResource`), estados carregando/erro/vazio. | `components/JourneyStrip.tsx`, `OverviewPage.tsx`, `styles.css` | `home-dashboard.test`: valores da API, link de cada etapa, falha de uma etapa não derruba as outras, sem "R$ 0"/"0" quando indisponível |
| T6 | **Reordenar o menu** (S3) após confirmação de Q1; ajustar testes que checam a ordem. | `components.tsx`, `navigation.test.tsx` | teste dos 8 nomes na nova ordem |
| T7 | **Contrato e orçamento:** novos campos em `contract-keys.json` (se T0 pedir campo no `overview`), `volume-budget.json` de `/` (9 blocos; justificar no `description`), `/usuarios` e rotas que ganham `NextStep`. | `test/*.json` | `volume.test`, `contracts.test` verdes |
| T8 | **Atualizar documentos:** `criterio-de-clareza.md` (linha do Início, hoje desatualizada), `roteiro-demonstracao.md` (abrir pela jornada), `GuidePage` (aponta para a jornada), `api.md` linha de `/usuarios`. | `docs/`, `GuidePage.tsx` | revisão de texto |

Dependências: T1, T2, T3 são independentes entre si e podem ir em paralelo; T4 depende de T3; T5 depende de T0 e T4 (reusa `journey.ts`); T6 por último dos de código; T7 acompanha cada tarefa; T8 fecha.

### 2.5 Critérios de aceite (globais)

1. De qualquer tela logada, "Usuários" está a ≤ 2 cliques; em `/usuarios` o menu e a aba refletem a posição.
2. O Início mostra a pergunta "O que olho primeiro?" respondida na primeira dobra (1440×900): a etapa mais urgente e seu número, sem rolar.
3. As 5 etapas aparecem na ordem do roteiro, cada uma com 1 número, 1 frase e 1 link; uma etapa que falha não derruba as demais e nunca mostra zero.
4. Toda página da jornada diz qual é o próximo passo; seguindo só esses links, chega-se do Início à Validação e volta ao Início.
5. Nenhuma URL existente deixa de abrir; `routes.test` e `login-gate.test` continuam verdes.
6. Acessibilidade: foco visível no menu do usuário, Esc fecha, `axe` sem violações novas, tab order segue a sequência da jornada.
7. Responsivo: 1440, 820 e 375 px sem rolagem horizontal; menu em gaveta continua com Usuários alcançável.
8. `npm run check` (typecheck, vitest, testes node, build, check:bundle) passa; screenshots 1440 e 375 do Início e de `/usuarios` anexados à revisão.

### 2.6 Verificação por IA (como o executor prova que terminou)

- Rodar `npm run check` em `frontend/` e colar a saída.
- Subir `api` e `frontend` (`.claude/launch.json`), entrar com o usuário de demonstração e capturar: Início (1440 e 375), menu do usuário aberto, `/usuarios` com a aba ativa, seguir os links "Próximo passo" de ponta a ponta.
- Passada de revisão **separada** (`code-reviewer`/`verifier`), não pelo mesmo contexto que implementou.
- Não declarar pronto com `test.skip`, `.only` ou testes de fachada.

### 2.7 Riscos

| # | Risco | Mitigação |
|---|---|---|
| R1 | 3 chamadas novas no Início deixam a primeira carga lenta na Vercel. | T0 mede; se necessário, agregar no `overview` (campo opcional, contrato atualizado). |
| R2 | Reordenar o menu desorienta quem já usa. | É só ordem, nomes e URLs ficam; confirmar Q1 antes de T6. |
| R3 | Orçamento de volume vira "mais um bloco" sem critério. | T7 troca "Indicadores" pela jornada e escreve o motivo no JSON. |
| R4 | Menu do usuário quebra na gaveta mobile ou com leitor de tela. | Critério 6 e 7; teste de teclado já existe (`keyboard.test`). |
| R5 | Usuário sem permissão de escrita vê o atalho e esbarra no erro. | T2. |

### 2.8 Entrega sugerida em duas partes

- **Parte A (rápida, baixo risco):** T1, T2, T3 — resolve o atalho de Usuários e dá coerência ao Planejamento.
- **Parte B:** T0, T4, T5, T6, T7, T8 — a jornada e o novo Início.
