# Etapa 8 — Segurança e modo de demonstração

## Resultado

Os seis itens da implementação mínima do plano foram implementados e testados:

| Item do plano | Implementação |
|---|---|
| Modo demonstração explícito | `DEMO_MODE=true` → aviso em todas as páginas com dados, vindo de `GET /api/system` (novo, aditivo) |
| Desabilitar escrita ou limpar dados com procedimento documentado | **Os dois.** `WRITE_ENABLED=false` → 403 no servidor e formulários desabilitados na interface. Limpeza por `scripts/reset_demo_data.py` (simulação por padrão, `--confirm`, backup JSON) ou `supabase/maintenance/reset_demo_data.sql` |
| CORS restrito | Só origens válidas de `CORS_ORIGINS` (sem curinga, caminho ou credenciais na URL); métodos GET/POST/PUT/OPTIONS; cabeçalho `Content-Type`; sem cookies. Em produção sem a variável, nenhuma origem externa é aceita |
| Tamanho e conteúdo de texto | Limites por campo, campos extras recusados, caracteres de controle recusados, SKU precisa existir, data válida, minutos entre 0 e 1440, cenários só com regras conhecidas, corpo até 16 KB e busca até 100 caracteres |
| Sem detalhes internos em produção | `APP_ENV=production` → erro genérico com código de referência (`X-Request-ID`); erros tratados de parceiros e validação sem caminhos ou mensagens técnicas; 422 sem ecoar o valor enviado |
| Logs sem `DATABASE_URL` | Filtro em todos os handlers remove a URL literal, qualquer connection string e `password=` — inclusive em tracebacks |

Itens adicionais, feitos por serem de baixo custo:

- **Cabeçalhos de segurança:** `nosniff`, `X-Frame-Options`, `Referrer-Policy` e `no-store` em escritas, na API e no frontend.
- **CSP no frontend** (`frontend/vercel.json`).
- **Vite:** atualizado de 6.0.11 para 6.4.3 (mesma série 6), o que removeu o único aviso *high* do `npm audit`.
- **Redirecionamento aberto:** o botão "Voltar" do detalhe do SKU só aceita caminhos internos.
- **Robustez:** `PUT /api/cases/{id}` de caso inexistente agora retorna 404. Antes, gravava um histórico órfão.

Score, ranking, regras, processamento do Excel, previsão, recomendação operacional e partição por parceiro não foram alterados. Os padrões das variáveis mantêm o comportamento local de antes: desenvolvimento, escrita habilitada e origens `localhost:5173`. O hash do XLSM foi preservado. Não houve deploy nem alteração de segredos.

## Configuração

| Variável | Padrão | Efeito |
|---|---|---|
| `APP_ENV` | `development` | `production` oculta detalhes internos. Um valor desconhecido também conta como produção (falha fechada) |
| `DEMO_MODE` | `false` | `true` exibe o aviso de dados fictícios que podem ser apagados |
| `WRITE_ENABLED` | `true` | `false` bloqueia decisões, casos e execuções |
| `CORS_ORIGINS` | `localhost:5173` e `127.0.0.1:5173` em desenvolvimento; nenhuma em produção | Origens exatas separadas por vírgula. Entradas inválidas são ignoradas e registradas no log |

Na inicialização, a API registra `api_settings environment=… demo_mode=… write_enabled=… cors_origins=<quantidade> persistence=sqlite|postgres`, sem valores sensíveis.

## Limpeza de dados de demonstração

```powershell
# Local (SQLite em runtime/)
.\.venv\Scripts\python.exe scripts\reset_demo_data.py            # conta registros, não apaga
.\.venv\Scripts\python.exe scripts\reset_demo_data.py --confirm  # backup em runtime/backups/ e limpeza

# Supabase, com DATABASE_URL definida apenas na sessão do terminal
.\.venv\Scripts\python.exe scripts\reset_demo_data.py --postgres
.\.venv\Scripts\python.exe scripts\reset_demo_data.py --postgres --confirm
```

- Por padrão, o script apaga as tabelas `feedback`, `cases`, `case_history` e `runs`. Com `--tables` dá para escolher um subconjunto, mas `cases` exige `case_history`, para não deixar histórico órfão.
- A planilha não é tocada e a `DATABASE_URL` nunca é impressa.
- `runtime/backups/` está no `.gitignore`.
- Alternativa no painel do Supabase: `supabase/maintenance/reset_demo_data.sql` (sem backup automático; exporte as tabelas antes).

## Verificação no navegador

O build de produção foi servido com os **mesmos cabeçalhos de `frontend/vercel.json`**, incluindo a CSP. A API rodou com `APP_ENV=production`, `DEMO_MODE=true` e `WRITE_ENABLED=false`.

- O aviso de demonstração e o de somente leitura apareceram.
- O botão "Registrar decisão" ficou desabilitado e o campo de observação veio limitado a 2000 caracteres.
- Um POST direto recebeu 403.
- Sete páginas foram navegadas sem nenhuma violação de CSP. As barras de risco e de cobertura receberam a largura normalmente: o React aplica os estilos via CSSOM, por isso não foi preciso `unsafe-inline`.
- O único erro no console foi o 403 provocado de propósito.
- O servidor de desenvolvimento com Vite 6.4.3 e o proxy `/api` funcionaram.

Durante as verificações, nada foi gravado nos bancos locais: as escritas estavam bloqueadas, e os testes usam bancos temporários.

## Arquivos

### Criados

- `backend/security.py`
- `scripts/reset_demo_data.py`
- `supabase/maintenance/reset_demo_data.sql`
- `frontend/src/hooks/useSystemInfo.ts`
- `frontend/src/test/security.test.tsx`
- `tests/test_security.py`
- `docs/etapa-8-seguranca-modo-demo.md`

### Modificados

- `backend/main.py`: configuração, CORS, tratamento de erros, modelos com limites, bloqueio de escrita, SKU existente, 404 de caso e `GET /api/system`.
- `backend/partners.py` e `backend/validation.py`: mensagem de erro sem detalhes técnicos em produção. A assinatura recebe um parâmetro opcional, então é compatível com o uso anterior.
- `frontend/src/App.tsx` e `frontend/src/components.tsx`: leitura do modo e `SystemBanner`.
- `frontend/src/api.ts`: `api.system` e mensagens legíveis para erros 422 em lista.
- `frontend/src/pages/FeedbackPage.tsx`, `CasesPage.tsx` e `RunsPage.tsx`: limites nos campos e estado somente leitura.
- `frontend/src/pages/SkuDetailPage.tsx`: `isInternalPath`.
- `frontend/src/App.css`: aviso.
- `frontend/vercel.json`: cabeçalhos e CSP.
- `frontend/package.json` e `package-lock.json`: Vite 6.4.3.
- `frontend/src/test/{setup.ts,utils.tsx,fixtures.ts,contracts.test.ts,contract-keys.json}` e `tests/test_frontend_contracts.py`: rota `system`, contrato e tempo de espera dos testes.
- `.env.example`, `.gitignore`, `README.md`, `docs/api.md`, `docs/decisions.md` e `docs/deploy-vercel-supabase.md`.

## Validação

```powershell
# Raiz
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider
# 187 passed: 143 anteriores + 43 de segurança + 1 de contrato (/api/system)

cd frontend
npm run check
# typecheck ✓ · Vitest 131 passed · node --test 20 passed · build ✓ · bundle sem segredos ✓
```

- Na primeira execução completa após a atualização do Vite, um teste falhou por tempo: o carregamento da rota levou 1,28 s, acima do limite padrão de 1 s das consultas assíncronas. O mesmo arquivo passou isolado três vezes. O limite foi ampliado para 5 s em todos os testes, e o `npm run check` completo passou duas vezes seguidas.
- Neste ambiente, o pytest usa `--basetemp` em uma pasta gravável, como nas etapas anteriores.

## Limitações

1. **Sem autenticação.** Com a escrita habilitada, qualquer pessoa com acesso à URL pode registrar decisões e casos. Para publicação aberta, use `WRITE_ENABLED=false` ou limpe os dados depois. Supabase Auth e perfis continuam como evolução posterior, conforme o plano.
2. **Sem limite de taxa** (rate limiting). Um volume alto de requisições não é contido pela API; depende da proteção da Vercel.
3. **Limite de 16 KB do corpo.** Ele usa o `Content-Length` declarado. Corpos enviados em partes (chunked), sem esse cabeçalho, não são barrados por ele, mas continuam sujeitos aos limites de cada campo.
4. **CSP.** Usa `connect-src 'self' https:`, porque o domínio da API muda por publicação. Depois de definir o domínio, dá para restringir `connect-src` a ele.
5. **Mensagens de validação.** Os textos gerados pelo Pydantic (por exemplo, "String should have at most 2000 characters") continuam em inglês. A interface acrescenta o nome do campo em português, e os limites dos campos impedem a maioria desses casos.
6. **Validação de SKU.** Decisões e casos agora exigem SKU existente na planilha atual. Clientes que enviavam SKUs inexistentes passam a receber 422. Essa é uma mudança intencional de validação; os formatos de requisição e resposta válidos não mudaram.
7. **`npm audit`.** Restam 4 avisos *moderate*:
   - **Vitest/@vitest/mocker:** só no ambiente de testes.
   - **react-router:** a correção existe apenas na v7. A aplicação só navega para caminhos internos, e o retorno do SKU foi endurecido.
   - **Script do esbuild:** a política de scripts do npm 11 não executa o pós-instalação do esbuild. O binário da plataforma é instalado como dependência opcional, e o build funciona.
8. **Limpeza de dados.** A limpeza remove todos os registros das tabelas escolhidas; não há marcação de registros por publicação.

## Deploy manual — não executado

1. Revisar os arquivos e executar as validações acima.
2. **Backend:** no projeto da Vercel, configure as variáveis abaixo. Nenhum segredo muda; `DATABASE_URL` permanece como está.
   - `APP_ENV=production`;
   - `CORS_ORIGINS` com o domínio exato do frontend;
   - `DEMO_MODE=true`, se for uma demonstração;
   - `WRITE_ENABLED=false`, se a publicação for aberta e não precisar de registros.
3. Publicar o backend e validar:
   - `/api/health`;
   - `/api/system`, que deve refletir as variáveis;
   - com `WRITE_ENABLED=false`, um `POST /api/feedback` deve retornar 403;
   - o cabeçalho `X-Request-ID` nas respostas.
4. **Frontend:** publicar normalmente (Root Directory `frontend`, `npm run build`, saída `dist`). O `vercel.json` passa a enviar CSP e os cabeçalhos de segurança.
5. Validar o frontend:
   - abrir as páginas principais com as ferramentas do navegador e confirmar que não há violações de CSP no console;
   - confirmar o aviso de demonstração ou de somente leitura;
   - testar os links diretos.
6. Se a CSP bloquear a chamada à API, confira se o `VITE_API_URL` usa `https://`.
7. Para limpar dados de demonstração, use o SQL Editor ou o script `--postgres --confirm` seguindo a seção acima, de preferência fora do horário de uso.
