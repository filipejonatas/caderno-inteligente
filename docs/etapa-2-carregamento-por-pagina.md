# Etapa 2 — Carregamento por página

## Escopo implementado

O shell deixa de depender de `loadDashboard()`. A função legada continua exportada para compatibilidade, mas não é usada pela aplicação. Nenhuma API ou regra de negócio foi alterada.

| Página | Leituras |
|---|---|
| Visão geral | `/overview`, `/priorities`, `/data-quality` |
| Prioridades | `/priorities` |
| Previsões | `/forecasts` |
| Casos | `/cases`, `/priorities`, `/config` |
| Qualidade | `/data-quality` |
| Parceiros | `/b2b2c/visibility` |
| Cenários | `/config` |
| Execuções | `/runs` |
| Decisões | `/feedback`, `/priorities`, `/config` |
| Detalhe de SKU | `/priorities/{sku}` |
| Guia e página não encontrada | Nenhuma |

Configuração é consultada apenas pelas páginas que a utilizam. Não foi criado contexto global porque não há, nesta etapa, informação de usuário ou outro dado que precise ser global.

## Ciclo de consulta

- `useApiResource` controla carregamento, erro, nova tentativa e atualização.
- Troca de rota, troca de SKU, atualização e desmontagem cancelam a leitura anterior via `AbortController`.
- Respostas antigas são ignoradas mesmo se o transporte não respeitar o cancelamento.
- `PageResource` compõe dependências tipadas por página, skeleton inicial, erro com retry e aviso em atualizações malsucedidas.
- Atualização preserva dados anteriores e estado dos formulários; erro de atualização permanece visível.
- Previsões e detalhes continuam com consultas próprias; previsão também responde ao botão de atualizar do cabeçalho.
- Estados vazios existentes foram preservados; parceiros recebeu um estado vazio explícito.
- Falha em feedback, casos ou execuções não bloqueia a Visão geral pelo carregamento do frontend.

## Arquivos alterados/criados

- `frontend/src/App.tsx`
- `frontend/src/api.ts`
- `frontend/src/hooks/useApiResource.ts` (novo)
- `frontend/src/components/PageResource.tsx` (novo)
- `frontend/src/pages/shared.ts`
- `frontend/src/pages/OverviewPage.tsx`
- `frontend/src/pages/PrioritiesPage.tsx`
- `frontend/src/pages/CasesPage.tsx`
- `frontend/src/pages/FeedbackPage.tsx`
- `frontend/src/pages/QualityPage.tsx`
- `frontend/src/pages/B2BPage.tsx`
- `frontend/src/pages/ScenariosPage.tsx`
- `frontend/src/pages/RunsPage.tsx`
- `frontend/src/pages/ForecastsPage.tsx`
- `frontend/src/pages/SkuDetailPage.tsx`
- `frontend/scripts/test-page-data.mjs` (novo)
- Este relatório (novo).

## Verificações realizadas

```powershell
# Raiz do repositório
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider
# 61 passed

cd frontend
node --test scripts/test-page-data.mjs
# 5 passed
npm run check
# Typecheck e build Vite aprovados
```

Os cinco testes Node verificam isolamento de endpoints da Visão geral, consulta de uma única página, erro HTTP e nova tentativa, propagação de AbortSignal e leituras dedicadas de previsão/SKU. Usam Node e TypeScript já existentes, sem instalar dependências. Não são testes de interface React.

Backend, cálculos, score, ranking, sete regras, previsão, recomendação operacional, processamento do XLSM, segredos e configuração de deploy não foram editados. Não houve criação de granularidade por parceiro nem distribuição de dados globais. O build atualizou artefatos locais ignorados em `frontend/dist`.

## Limitações e validação manual pendente

- Sem cache entre rotas: retornar a uma página refaz suas consultas. Esse comportamento é intencional e não adiciona biblioteca.
- Dependências de uma mesma página são carregadas em conjunto: falha em uma delas apresenta erro da página, não um painel parcial. Outras rotas permanecem independentes.
- A Visão geral ainda requer `/overview`, que pode ter dependências internas do backend. A mudança elimina acoplamento de consultas no frontend, não redefine contratos ou dependências internas da API.
- AbortController interrompe a espera do cliente; não garante interrupção do processamento já iniciado no servidor.
- Não foi executado teste E2E/visual em navegador nesta etapa. O ciclo React de navegação rápida deve ser verificado manualmente, além dos testes de transporte.
- Skeletons existentes foram reutilizados; polimento visual amplo pertence à etapa 3.

Checklist manual: abrir `/guia` com a API desligada; simular falhas em `/feedback` e `/runs` e confirmar abertura da Visão geral; navegar rapidamente entre rotas e SKUs; observar cancelamentos na aba Network; testar retry, atualização de previsões e formulários após salvar; verificar estados vazios.

## Deploy manual — não executado

1. Revisar o diff e executar os comandos de validação acima.
2. Publicar somente o frontend conforme `docs/deploy-vercel-supabase.md`: Root Directory `frontend`, build `npm run build`, saída `dist`.
3. Manter `VITE_API_URL` apontando para a API existente, sem inserir credenciais. A variável é incorporada no build.
4. Preservar o rewrite SPA de `frontend/vercel.json` para deep links.
5. Não há migração de banco, mudança de backend ou novo segredo exigidos por esta etapa.
6. Após publicação manual, executar o checklist de navegação, falhas e atualização. Nenhum deploy foi realizado durante a implementação.
