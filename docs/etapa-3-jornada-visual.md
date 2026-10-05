# Etapa 3 — Jornada visual de decisão

## Entrega

A interface foi reorganizada sem alterar contratos ou cálculos de negócio.

### Visão geral

1. **O que exige atenção:** primeiro SKU da fila oficial, todos os sinais desse SKU, confiança e botão direto para evidências; métricas operacionais e cinco primeiras prioridades.
2. **Ações sugeridas:** próximos passos de análise, com atalhos para previsão e recomendação do primeiro SKU, parceiros, validação dos dados e registro de decisão.
3. **Qualidade da decisão:** cobertura observada de sell-out, decisões registradas, influência dos dados de parceiros e distribuição dos sinais.

A ordem recebida do backend é preservada. O destaque não constitui uma nova regra nem classifica o primeiro motivo como o risco mais grave. Todas as razões do primeiro SKU são exibidas.

O bloco de ações não inventa recomendação operacional ou quantidade a partir do score. Os valores efetivos continuam nas telas de previsões e detalhe do SKU. Isso preserva o carregamento de forecasts somente na rota própria, implementado na etapa 2.

### Padrões compartilhados

- Cabeçalho com título, contexto, status real de consulta, atualização e última carga bem-sucedida no navegador, em horário de Brasília.
- A última carga não significa atualização da planilha; falhas não sobrescrevem o horário da última consulta bem-sucedida.
- Atualização também disponível no detalhe do SKU, preservando dados anteriores quando a nova consulta falha.
- Componente de alerta, distinção explícita entre prioridade de análise e ação de produção, tooltip acessível para score, confiança e WAPE.
- Explicação específica quando a recomendação do SKU é `sem_acao_necessaria`: ausência de produção adicional não elimina sinais de risco.
- Filtros com rótulos visíveis, contagem de resultados e limpeza; filtro de confiança das prioridades contempla alta, média e baixa.
- Tabelas com texto mais legível, espaçamento compacto, botão nomeado para evidências e região de scroll focável.
- Legenda nas tabelas de ranking reforça que prioridade não autoriza produção, inclusive em cenários.
- Foco visível e menu lateral inerte/oculto para tecnologia assistiva quando fechado em telas pequenas.
- Uma cor primária, cores semânticas para sinais e remoção de gradientes/ornamentos dos principais elementos.

O rótulo do intervalo entre primeira promessa e primeira conclusão foi corrigido para “Intervalo de risco entre datas”, sem mudar seu cálculo: não há alocação pedido–OP que comprove atraso efetivo.

## Arquivos modificados

| Arquivo | Alteração |
|---|---|
| `frontend/src/App.tsx` | Contexto de status da rota, estado do cabeçalho e atualização de SKU |
| `frontend/src/App.css` | Jornada, padrões visuais, legibilidade, foco e responsividade |
| `frontend/src/components.tsx` | Cabeçalho, alertas, explicação, tooltips, menu e tabela |
| `frontend/src/components/PageResource.tsx` | Publicação de status da rota e alerta de atualização |
| `frontend/src/hooks/useApiResource.ts` | Horário da última carga bem-sucedida |
| `frontend/src/pages/OverviewPage.tsx` | Três blocos e atalhos de decisão |
| `frontend/src/pages/PrioritiesPage.tsx` | Explicação, filtros e limpeza |
| `frontend/src/pages/ForecastsPage.tsx` | Status de carga, alertas e distinção da ação operacional |
| `frontend/src/pages/SkuDetailPage.tsx` | Status, atualização, explicação e preservação em falha |

### Arquivos novos

- `frontend/src/hooks/usePageLoadStatus.ts`: contexto leve, somente metadados da consulta, sem globalizar dados de negócio.
- `frontend/scripts/test-decision-journey.mjs`: cinco testes de renderização com fixtures sintéticas isoladas dos dados da aplicação.
- `docs/etapa-3-jornada-visual.md`: este relatório.

Não houve mudança em APIs, backend, score, ranking, regras, XLSM, previsão, recomendação operacional, granularidade de parceiro, banco ou segredos. Não houve instalação de dependências. O build atualizou a saída local ignorada em `frontend/dist`.

## Verificações

```powershell
# Raiz
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider
# 61 passed

cd frontend
node --test scripts/test-page-data.mjs scripts/test-decision-journey.mjs
# 10 passed (5 consultas + 5 renderização)

npm run check
# Typecheck e build Vite aprovados

cd ..
git diff --check
# Aprovado
```

Os novos testes verificam os três blocos, links codificados corretamente, preservação da prioridade recebida, estado vazio, distinção entre ranking e produção, horário real/ausente de carga e semântica de alertas/tooltips. São testes de renderização estática, não testes completos de interação React.

### Responsividade na aplicação real

Foram verificadas as 11 rotas abaixo com a API local real em quatro larguras: **390, 768, 1024 e 1440 pixels**.

`/`, `/prioridades`, `/previsoes`, `/skus/CI-0041`, `/qualidade`, `/parceiros`, `/casos`, `/decisoes`, `/cenarios`, `/execucoes`, `/guia`.

**44 verificações, nenhuma falha de carregamento e nenhum overflow horizontal do documento.** Menu fechado inerte também confirmado em larguras móveis.

A janela do navegador interno limita sua largura mínima a 700 pixels. Para verificar as larguras exatas, foram usados iframes de mesma origem com a aplicação real, medindo `innerWidth` e `documentElement.scrollWidth`. A rolagem vertical pode reduzir a largura útil em 15 pixels. As tabelas largas mantêm scroll horizontal intencional dentro da própria região.

Foi encontrado e corrigido um overflow a 390 pixels provocado pelo posicionamento absoluto de um rótulo acessível. A região da tabela agora ancora esse rótulo.

A abertura do destaque para `/skus/CI-0041` e a presença da evidência foram confirmadas por acionamento programático do handler React e inspeção da rota. Cliques nativos retornaram `action_uncertain`; tentativa de teclado não acionou a navegação pela ferramenta. A captura de imagem retornou `UnknownVizError`. Portanto, não há screenshot entregue nem afirmação de teste completo por clique nativo.

## Limitações e aceite pendente

- O critério de identificar o risco e abrir a evidência em menos de 30 segundos exige teste com pessoas; não foi validado.
- A compreensão real de prioridade alta versus `sem ação necessária` precisa de validação humana. A explicação está implementada e sua renderização foi testada.
- Geometria, carregamento e conteúdo foram inspecionados no navegador. Revisão visual por screenshot e interação nativa completa ficaram limitadas pela ferramenta.
- A central de validação da etapa 5 não existe nesta entrega: o atalho de validação abre a página atual de Qualidade.
- O bloco de ações sugeridas da Visão geral orienta a jornada; não duplica previsões ou recomendações operacionais nem cria uma nova API.
- Não houve auditoria completa com leitor de tela, dispositivos físicos ou outros navegadores.

Checklist humano recomendado: abrir o primeiro SKU sem orientação; explicar a diferença entre score e ação; navegar por teclado; abrir tooltips e fechar com Escape; limpar filtros; atualizar o SKU; simular falha de atualização; verificar o layout no celular.

## Deploy manual — não executado

1. Revisar os arquivos e executar as verificações acima.
2. Publicar apenas o frontend conforme `docs/deploy-vercel-supabase.md`: Root Directory `frontend`, build `npm run build`, saída `dist`.
3. Manter `VITE_API_URL` apontando para a API existente e preservar o rewrite SPA em `frontend/vercel.json`.
4. Nenhuma nova variável, segredo, API ou migração de banco é necessária.
5. Após publicação, validar deep link de SKU, atualização, horário de carga, quatro viewports, navegação de evidências, filtros e tooltips.

Nenhum deploy foi realizado nesta etapa.
