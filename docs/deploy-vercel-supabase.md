# Deploy com Vercel e Supabase

Este guia pressupõe que todas as mudanças locais foram testadas. Ele não contém credenciais reais e não deve receber senhas em commits.

## 1. Supabase

1. Crie um projeto.
2. Abra o SQL Editor e execute `supabase/migrations/001_initial.sql`. Em seguida, execute `supabase/migrations/002_run_comparison.sql` (aditiva; adiciona a coluna opcional `runs.comparison`).
3. Em **Connect**, escolha **Transaction pooler**.
4. Copie a connection string da porta `6543` e acrescente `sslmode=require` se ainda não estiver presente.
5. Confirme no Table Editor que RLS está habilitado e que não existem políticas públicas nas quatro tabelas.

Formato esperado:

```text
postgresql://postgres.PROJECT_REF:PASSWORD@POOLER_HOST:6543/postgres?sslmode=require
```

## 2. Backend na Vercel

Importe o repositório e mantenha a raiz como Root Directory. A Vercel encontra o FastAPI por meio de:

```toml
[tool.vercel]
entrypoint = "backend.main:app"
```

Configure somente no projeto backend:

```text
DATABASE_URL=<connection string do Transaction Pooler>
CORS_ORIGINS=https://DOMINIO-DO-FRONTEND.vercel.app
LOG_LEVEL=INFO
APP_ENV=production
DEMO_MODE=true
WRITE_ENABLED=true
```

- `APP_ENV=production` oculta detalhes internos nas respostas de erro; a causa fica no log da Vercel, já sem `DATABASE_URL`.
- `DEMO_MODE=true` exibe o aviso de publicação de demonstração.
- Para uma publicação aberta sem registro de dados, use `WRITE_ENABLED=false`: decisões, casos e execuções retornam 403 e a interface desabilita os formulários.
- Para limpar dados de demonstração, execute `supabase/maintenance/reset_demo_data.sql` no SQL Editor ou `python scripts/reset_demo_data.py --postgres --confirm` com `DATABASE_URL` no ambiente do terminal (gera backup JSON antes).

Depois do deploy, valide:

```text
GET https://DOMINIO-DO-BACKEND.vercel.app/api/health
```

O retorno deve indicar `status: ok`, `database: ok` e `persistence: postgres`.

## 3. Frontend na Vercel

Importe o mesmo repositório em um segundo projeto e configure:

```text
Root Directory: frontend
Framework: Vite
Build command: npm run build
Output directory: dist
```

Variável do frontend:

```text
VITE_API_URL=https://DOMINIO-DO-BACKEND.vercel.app/api
```

Essa variável é pública por definição e deve conter apenas a URL da API. Nunca use prefixo `VITE_` em senhas ou chaves privilegiadas.

## 4. Ajuste final de CORS

Após conhecer o domínio definitivo do frontend, atualize `CORS_ORIGINS` no projeto backend e faça novo deploy. Separe múltiplas origens por vírgula.

Não use `*`: a API possui operações de escrita. CORS também não substitui autenticação.

## 5. Smoke test

1. Abra o health check.
2. Carregue a Visão geral.
3. Abra uma prioridade.
4. Execute um cenário.
5. Crie e atualize um caso.
6. Registre uma decisão.
7. Registre uma execução.
8. Faça redeploy do backend.
9. Confirme que casos, feedbacks e execuções continuam presentes.
10. Revise os logs da Function e o console do navegador.

## 6. Desenvolvimento local

Sem `DATABASE_URL`, o backend usa automaticamente os bancos SQLite em `runtime/`. O proxy do Vite mantém `/api` apontando para `127.0.0.1:8000`, portanto `VITE_API_URL` também é opcional localmente.

Para testar deliberadamente com Supabase, defina `DATABASE_URL` apenas na sessão local ou em um `.env` não versionado. O projeto não carrega `.env` automaticamente; exporte a variável no terminal ou use a configuração da sua IDE.
