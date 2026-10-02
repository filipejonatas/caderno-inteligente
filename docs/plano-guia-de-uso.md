# Plano de implementação — Guia de uso

## 1. Objetivo

Adicionar ao frontend uma página de onboarding chamada **Guia de uso**, acessível pelo menu lateral, que permita a uma pessoa entender o protótipo e realizar uma demonstração sem explicação prévia da equipe.

O guia deve ser curto, visual, responsivo e independente do backend. Mesmo que a API esteja indisponível, a página precisa continuar acessível.

## 2. Escopo do MVP para o hackathon

A página terá cinco blocos:

1. **Comece por aqui** — explica em até cinco passos o fluxo recomendado de uso.
2. **O que há em cada página** — apresenta cada área do sistema, sua finalidade e um botão para abri-la.
3. **Entenda os indicadores** — glossário dos principais termos e sinais usados pelo protótipo.
4. **Limitações do protótipo** — deixa claro o que é simulação, recomendação ou dado ausente.
5. **Roteiro rápido de demonstração** — sequência de 2 a 3 minutos para a equipe apresentar a solução.

Também haverá um FAQ curto usando elementos nativos `<details>` e `<summary>`, sem instalar bibliotecas.

## 3. Conteúdo proposto

### 3.1 Fluxo recomendado

Apresentar uma sequência semelhante a:

1. Confira o panorama geral.
2. Identifique itens que exigem atenção.
3. Analise o caso e os dados disponíveis.
4. Simule um cenário antes de decidir.
5. Registre a decisão e acompanhe o resultado.

Cada passo deve informar qual página abrir em seguida.

### 3.2 Mapa das páginas

Criar um card para cada página existente:

- **Visão geral** — resumo da situação e dos principais indicadores.
- **Prioridades** — itens ordenados por urgência ou impacto.
- **Casos** — análise detalhada de cada situação.
- **Qualidade** — completude e confiabilidade dos dados.
- **B2B** — acompanhamento da operação entre empresas e seus reflexos.
- **Cenários** — comparação de alternativas antes da decisão.
- **Execuções** — histórico do processamento e atualização dos dados.
- **Decisões** — registro das ações e feedbacks realizados.

Cada card deve conter um botão **Abrir página**, que usa a navegação interna já existente, sem recarregar a aplicação.

### 3.3 Glossário

Explicar, em linguagem simples, os conceitos que aparecem na interface, por exemplo:

- pontuação de atenção;
- confiança da recomendação;
- data crítica;
- estoque projetado;
- lacuna operacional;
- dado ausente;
- níveis ou impactos B2B2C.

Os textos devem explicar como interpretar o indicador, sem prometer precisão que o protótipo não oferece.

### 3.4 Limitações e transparência

Incluir avisos objetivos:

- as recomendações apoiam a decisão humana e não executam ações automaticamente;
- alguns dados do protótipo podem ser simulados;
- baixa confiança ou dados ausentes exigem validação manual;
- uma simulação de cenário não equivale a uma ordem real de produção ou compra.

### 3.5 FAQ mínimo

Responder pelo menos:

- Como os dados são atualizados?
- O que significa um indicador com baixa confiança?
- O que fazer quando o sell-out ou outro dado está zerado?
- Uma simulação altera os dados reais?
- O sistema emite uma ordem de produção automaticamente?

## 4. Alterações técnicas

### `frontend/src/types.ts`

- Adicionar `guide` ao tipo `PageId`.

### `frontend/src/components.tsx`

- Adicionar o item **Guia de uso** ao menu lateral.
- Criar ou adicionar um ícone coerente com o conjunto atual, como livro aberto ou ajuda.
- Garantir que a lista de navegação possa rolar verticalmente em telas com pouca altura.
- Permitir que o `Topbar` esconda a ação de atualizar dados quando a página atual for o guia.

### `frontend/src/pages.tsx`

- Criar o componente `GuidePage`.
- Usar os componentes visuais existentes, como `PageIntro`, `SectionCard`, `Badge` e `Icon`, para manter consistência.
- Receber `onNavigate(page: PageId)` para os atalhos de cada página.
- Manter todo o conteúdo estático no frontend; o guia não deve fazer requisições à API.

### `frontend/src/App.tsx`

- Importar e renderizar `GuidePage` no `switch` de páginas.
- Renderizar o guia antes das verificações globais de carregamento e erro da API. Assim, ele permanece utilizável mesmo com o backend offline.
- Ao navegar por um atalho do guia, atualizar a página selecionada e levar a janela ao topo.
- Ocultar o botão de atualização do `Topbar` enquanto o guia estiver aberto.

### `frontend/src/App.css`

- Criar estilos para o fluxo em etapas, cards de páginas, glossário, avisos, roteiro e FAQ.
- Reaproveitar cores, espaçamentos, bordas e tipografia atuais.
- Evitar blocos longos de texto; priorizar cards, listas curtas e boa hierarquia visual.
- Validar que o menu continue acessível ao adicionar o novo item.
- Incluir estados de foco visíveis e respeitar as regras existentes de responsividade.

## 5. Ordem de implementação para a IA

1. Atualizar os tipos e o catálogo de navegação.
2. Criar a estrutura e o conteúdo da `GuidePage`.
3. Ligar os botões do guia à navegação existente.
4. Ajustar o fluxo de carregamento para o guia funcionar sem a API.
5. Estilizar a página usando o design atual como base.
6. Ajustar menu e topo para desktop e mobile.
7. Executar verificações automatizadas e revisar visualmente as telas.

Estimativa para execução por IA: **1 a 2 horas**, incluindo validação e pequenos ajustes visuais.

## 6. Critérios de aceite

- O menu lateral contém **Guia de uso** e destaca o item quando selecionado.
- O guia abre em desktop e mobile sem depender da API.
- Uma pessoa nova entende o fluxo principal do protótipo em menos de cinco minutos.
- Todas as páginas atuais são descritas e possuem um atalho funcional.
- Os principais indicadores e limitações estão explicados em linguagem simples.
- O botão de atualizar dados não aparece no guia.
- Os atalhos navegam para a página correta e posicionam a visualização no topo.
- O FAQ funciona por teclado e mouse.
- Não há rolagem horizontal em `390 x 844`.
- O menu permanece utilizável em `1366 x 768` e `1440 x 900`.
- O console do navegador não apresenta novos erros.
- A checagem TypeScript/build do frontend passa sem erros.

## 7. Validação

### Automatizada

- Executar o comando de checagem ou build já definido em `frontend/package.json`.
- Não adicionar uma nova biblioteca de testes apenas para esta etapa.
- Confirmar que os testes existentes do projeto continuam passando.

### Manual

1. Abrir o guia com o backend ativo.
2. Interromper o backend e confirmar que o guia ainda abre.
3. Testar todos os botões **Abrir página**.
4. Percorrer o FAQ apenas com teclado.
5. Validar os tamanhos `1440 x 900`, `1366 x 768` e `390 x 844`.
6. Conferir contraste, foco, legibilidade e ausência de conteúdo cortado.

## 8. Fora do escopo desta versão

- tour com balões sobrepostos à interface;
- vídeo tutorial;
- persistência de progresso do usuário;
- central de ajuda administrável por CMS;
- busca no conteúdo do guia;
- internacionalização;
- analytics de onboarding;
- alterações no backend ou banco de dados.

Esses recursos podem ser avaliados depois do hackathon, conforme o feedback dos usuários.

## 9. Prompt sugerido para a implementação

> Implemente o plano descrito em `docs/plano-guia-de-uso.md`. Preserve a arquitetura e o design system existentes. Crie uma página estática e responsiva chamada “Guia de uso”, acessível pelo menu lateral e funcional mesmo quando a API estiver offline. Inclua atalhos para todas as páginas, glossário, limitações, FAQ e roteiro de demonstração. Não adicione dependências nem altere o backend. Ao final, execute as verificações do frontend e informe os arquivos modificados e os testes realizados.
