# Etapa 7 — Testes do frontend, acessibilidade e robustez

## Resultado

O frontend ganhou testes automatizados com Vitest, React Testing Library, jsdom e axe-core. Agora o `npm run check` executa, em ordem:

1. typecheck;
2. testes Vitest;
3. testes `node --test` existentes;
4. build;
5. varredura de segredos no `dist/`.

A revisão de acessibilidade encontrou e corrigiu problemas reais de contraste, foco, ARIA, tabelas roláveis e títulos. A aplicação também ganhou um error boundary por rota.

Nada mudou em score, ranking, regras, processamento do Excel, previsão, recomendação operacional ou contratos de API. Não há API nova. O hash do XLSM foi preservado. Não houve deploy nem alteração de segredos.

## Cobertura dos testes

| Item do plano | Onde |
|---|---|
| Resolução de todas as rotas, em desktop e celular | `routes.test.tsx`: 11 rotas × 2 viewports, com h1, h2, título da aba e landmark `main` |
| Link ativo do menu | `routes.test.tsx`: `aria-current="page"` só no item ativo, inclusive em rota filha (`/parceiros/:codigo`) |
| Deep link de SKU e parceiro | `routes.test.tsx`: códigos com espaço e barra codificados; o SKU não carrega o dashboard; a comparação de execuções abre pela URL |
| Query parameters dos filtros | `filters-states.test.tsx`: prioridades (leitura inicial, busca, confiança e limpeza), previsões (ação e atenção) e parceiro (qualidade levada à API) |
| Loading, erro, vazio e sucesso | `filters-states.test.tsx`: estado acessível de carregamento, erro HTTP com retry, erro de rede, vazios explicados, falha isolada do contexto comercial e SKU inexistente |
| Guia offline | `routes.test.tsx`: com `fetch` rejeitando, o guia renderiza sem nenhuma chamada |
| Rota 404 | `routes.test.tsx`: sem chamadas à API e com link para a visão geral |
| Recomendação com dados insuficientes | `filters-states.test.tsx`: sem quantidade, sem zero, com revisão humana no detalhe e na lista |
| Teclado no menu e formulários | `keyboard.test.tsx`: link "pular para o conteúdo", menu desktop, gaveta móvel (foco, Esc, `inert`, `aria-expanded`), Enter nas linhas da tabela e ordem de tabulação e envio dos formulários de decisão e de caso |
| Smoke test de contratos com fixtures | `contracts.test.ts` + `tests/test_frontend_contracts.py`: a mesma lista de 14 endpoints é conferida nas fixtures e na API real |
| Títulos, landmarks, foco e rótulos | `a11y.test.tsx`: axe-core em 14 páginas × 2 viewports, com zero violações de qualquer gravidade, e toda tabela rolável focável e nomeada |
| Contraste | `contrast.test.ts`: 16 pares texto/fundo calculados a partir dos tokens reais do `App.css` |
| Segredos no bundle | `scripts/check-bundle-secrets.mjs`, executado após o build |
| Robustez | `robustness.test.tsx`: resposta malformada contida na rota, JSON inválido e cancelamento da leitura ao trocar de rota |

Os testes usam somente fixtures sintéticas tipadas (`src/test/fixtures.ts`, com códigos `TEST-*` e `KA T1`). Por serem tipadas, o `tsc` falha se divergirem dos contratos TypeScript.

O arquivo `src/test/contract-keys.json` lista os campos que o frontend lê em cada endpoint. O pytest confirma que a API real entrega todos eles. Um campo só é dispensado quando está dentro de uma lista vazia ou de um valor nulo, e um teste negativo garante que um campo ausente é detectado.

## Correções feitas a partir da revisão

| Problema | Correção |
|---|---|
| `--slate-500` (texto secundário em toda a interface) tinha contraste de 3,8 a 4,0:1, abaixo do AA | Mudou para `#5b6b7f`, com 5,1:1 ou mais sobre os fundos usados |
| A linha focada da tabela de prioridades tinha `outline: none` com mais especificidade que o foco global, deixando o foco quase invisível | `:focus-visible` explícito para linhas e campos |
| A barra de progresso dos parceiros usava `aria-label` sem papel ARIA (axe: `aria-prohibited-attr`) | `role="progressbar"` com valores e nome por parceiro |
| A tabela de previsões tinha cabeçalho vazio | Rótulo acessível "Detalhes" |
| As tabelas de Casos e Qualidade rolavam horizontalmente no celular sem receber foco de teclado (encontrado com o axe no Chromium real) | `tabIndex=0`, `role="region"` e nome acessível, como as demais tabelas |
| A comparação de execuções e a validação tinham saltos de títulos (`h3` → `h5`) | Ajustados para `h4` |
| O título da aba era sempre o mesmo | `Página · Caderno Inteligente` por rota |
| Não havia atalho para pular o menu | Link "Pular para o conteúdo" e foco no título da página após cada navegação |
| A gaveta do menu no celular não recebia foco, não fechava com Esc e o botão não expunha o estado | Foco no primeiro item, Esc fecha e devolve o foco, `aria-expanded` e `aria-controls` |
| Um erro de renderização ou um chunk ausente após o deploy deixava a tela em branco | `RouteErrorBoundary` por rota, com recarregar, tentar novamente e voltar à visão geral; o menu continua utilizável |
| SKU com histórico insuficiente não mostrava "Revisão humana obrigatória" | Aviso exibido também nesse caso, deixando claro que ausência de previsão não é demanda zero |

## Verificação no navegador real

Com a API e a planilha reais, o axe-core foi executado no Chromium com todas as regras, inclusive contraste, em 14 rotas, a 375 e a 1440 pixels:

- **resultado:** zero violações e nenhum overflow horizontal do documento;
- **console:** nenhum erro da aplicação.

Na primeira rodada, o axe apontou contraste baixo no botão "Atualizar". A causa era o painel do navegador estar oculto: a transição de opacidade do estado desabilitado fica parada em t=0 nessa situação. Concluídas as animações, o botão mede contraste normal. Não era um defeito da aplicação.

## Arquivos

### Criados

- `frontend/vitest.config.ts`
- `frontend/src/test/setup.ts`
- `frontend/src/test/utils.tsx`
- `frontend/src/test/fixtures.ts`
- `frontend/src/test/contract.ts`
- `frontend/src/test/contract-keys.json`
- `frontend/src/test/routes.test.tsx`
- `frontend/src/test/keyboard.test.tsx`
- `frontend/src/test/filters-states.test.tsx`
- `frontend/src/test/a11y.test.tsx`
- `frontend/src/test/contrast.test.ts`
- `frontend/src/test/contracts.test.ts`
- `frontend/src/test/robustness.test.tsx`
- `frontend/src/components/RouteErrorBoundary.tsx`
- `frontend/scripts/check-bundle-secrets.mjs`
- `tests/test_frontend_contracts.py`
- `docs/etapa-7-testes-acessibilidade.md`

### Modificados

- `frontend/package.json` e `frontend/package-lock.json`: devDependencies e scripts `test`, `test:watch`, `test:node`, `check:bundle` e `check`.
- `frontend/src/App.tsx`: título por rota, link de pular, foco no título e error boundary.
- `frontend/src/components.tsx`: gaveta acessível, `aria-expanded` no botão de menu, h1 focável e `ProgressBar` com papel ARIA.
- `frontend/src/App.css`: token de contraste, foco visível e link de pular.
- Páginas `SkuDetailPage`, `ForecastsPage`, `CasesPage`, `QualityPage`, `B2BPage` e `ValidationPage`, além de `RunComparisonView`: as correções da tabela acima.
- `README.md` e `docs/decisions.md`.

## Validação

```powershell
# Raiz
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider
# 143 passed: 127 anteriores + 16 de contrato

cd frontend
npm run check
# typecheck ✓ · Vitest 114 passed · node --test 20 passed · build ✓ · bundle sem segredos ✓
```

O `scripts/validate.ps1` já chama `npm run check`, então passa a executar também os testes do frontend.

Neste ambiente, o pytest precisou de `--basetemp` em uma pasta gravável, pela mesma restrição de sandbox das etapas anteriores.

## Limitações

1. **Ambiente de teste:** o jsdom não tem layout nem cálculo de cores. Contraste e rolagem são testados por regras estruturais e pelos tokens do CSS. A auditoria no Chromium real foi manual nesta etapa e não está automatizada no `npm run check`, porque não há navegador headless instalado no projeto.
2. **Contraste:** o teste cobre os pares de tokens e badges principais, não todas as cores fixas do CSS (por exemplo, o hero do guia). A auditoria no Chromium cobriu as 14 rotas renderizadas.
3. **Estado padrão das páginas:** os testes das páginas de Casos e Decisões usam fixtures. A gravação real é coberta pelos testes Python.
4. **Navegação por teclado:** foi testada com `user-event` e com axe. Não houve teste com leitores de tela reais (NVDA, VoiceOver) nem o teste moderado com usuários previsto na seção 9 do plano.
5. **`npm audit`:** aponta 6 avisos.
   - Cinco vêm de dependências já existentes: Vite 6.0.11 fixado, esbuild e react-router/react-router-dom.
   - Um vem do Vitest, que é novo, mas só de desenvolvimento.
   - O único que chega à produção é o do react-router (redirecionamento aberto via `<Link>`/`useNavigate` com barra invertida). A aplicação só navega para caminhos internos, e o retorno do detalhe do SKU exige caminho iniciado por `/`. A atualização não foi feita para não introduzir mudanças incompatíveis; vale avaliar em uma etapa de segurança.
6. **Avisos de console:** os avisos de "future flags" do React Router v7 continuam aparecendo no console de desenvolvimento e nos testes. Não são erros.

## Deploy manual — não executado

1. Revisar os arquivos e executar as validações acima.
2. **Backend:** não há mudança de backend nesta etapa, apenas um teste novo. Nenhum redeploy é necessário.
3. **Frontend:** Root Directory `frontend`, build `npm run build`, saída `dist`. A Vercel instala as devDependencies para o build, mas não executa os testes. Manter `VITE_API_URL` e o rewrite SPA.
4. **Opcional:** usar `npm run check` como comando de build na Vercel para bloquear deploys com testes falhando. Isso aumenta o tempo de build em cerca de 1 minuto.
5. **Validar após publicar:**
   - o título da aba muda por página;
   - Tab mostra o link "Pular para o conteúdo";
   - no celular, o menu abre com foco e fecha com Esc;
   - as tabelas de Casos e Qualidade rolam pelo teclado;
   - os deep links continuam funcionando.
