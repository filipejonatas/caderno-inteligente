# Caderno Inteligente

Aplicação de apoio à decisão do PCP. O sistema lê uma base XLSM sem alterá-la, valida os dados, calcula indicadores e regras auditáveis, ordena SKUs para atenção e registra decisões humanas. SQLite é usado localmente; quando `DATABASE_URL` está configurada, a persistência usa PostgreSQL/Supabase.

O ranking não é uma decisão automática de produção. Cada prioridade preserva motivos, evidências, origem dos dados, limitações e nível de confiança.

## Arquitetura

```text
XLSM somente leitura
        ↓
Núcleo Python determinístico
        ↓
FastAPI com cache do pipeline
        ↓
React + TypeScript + Vite
        ↓
SQLite local ou PostgreSQL/Supabase em produção
```

## Requisitos

- Python 3.11, 3.12 ou 3.13 — recomendado: 3.12;
- Node.js 18 ou superior;
- npm.

## Preparar o ambiente

### Backend

No PowerShell, a partir da raiz do projeto:

Use Python 3.12 ou 3.13. O projeto não oferece suporte a Python 3.14.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

### Frontend

```powershell
cd frontend
npm install
cd ..
```

## Executar

Use dois terminais.

Terminal 1 — API:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2 — frontend:

```powershell
cd frontend
npm run dev
```

Acesse `http://127.0.0.1:5173`.

## Validar

Para executar todas as verificações com um único comando, a partir da raiz:

```powershell
.\scripts\validate.ps1
```

O script valida as dependências instaladas, executa toda a suíte Python e roda o typecheck e o build do frontend.

Comandos individuais:

Testes Python:

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider
```

Tipos e build do frontend:

```powershell
cd frontend
npm run check
```

## Interface

- **`/guia` — Guia de uso:** onboarding estático, disponível mesmo sem a API;
- **`/` — Visão geral:** pulso da operação, riscos e itens mais urgentes;
- **`/prioridades` — Prioridades:** busca e filtros por família e confiança preservados na URL;
- **`/previsoes` — Previsão e recomendações:** forecast, confiança e ação sugerida;
- **`/skus/:sku` — Detalhe do SKU:** página compartilhável com indicadores, riscos, valores utilizados e origem;
- **`/casos` — Casos:** responsável, prazo e status operacional;
- **`/qualidade` — Qualidade:** cobertura, integridade e lacunas dos dados;
- **`/parceiros` — Visibilidade B2B2C:** cobertura de sell-out por parceiro;
- **`/cenarios` — Cenários:** simulações que não alteram o ranking oficial;
- **`/execucoes` — Execuções:** snapshots auditáveis da fonte e do ranking;
- **`/decisoes` — Decisões:** feedback do PCP separado da base XLSM.
- **`/validacao` — Validação:** comparação com o processo atual, previsão contra baseline, casos congelados, comportamento seguro, falhas e ajustes, com exportação CSV e impressão.

O frontend usa rotas reais no navegador, lazy loading por página e uma rota 404. O arquivo `frontend/vercel.json` redireciona deep links para o `index.html`, permitindo abrir ou atualizar diretamente uma URL interna na Vercel.

## Configuração

- Pesos: `config/prioritization_weights.json`;
- Limiares: `config/rule_thresholds.json`;
- Casos congelados e linha de base da validação: `config/validation_center.json`;
- Origem permitida pela API: variável `CORS_ORIGINS`, separada por vírgulas;
- Nível de log: variável `LOG_LEVEL`.
- PostgreSQL/Supabase: variável secreta `DATABASE_URL`. Na ausência dela, o backend usa SQLite.
- URL pública da API no frontend: `VITE_API_URL`. Na ausência dela, o frontend usa `/api`.

O cache do backend é invalidado automaticamente quando a planilha ou um dos arquivos de configuração é alterado.

Copie `.env.example` e `frontend/.env.example` apenas quando precisar sobrescrever os valores locais. Nunca versione os arquivos `.env` reais.

## Publicar com Vercel e Supabase

O deploy utiliza dois projetos Vercel ligados ao mesmo repositório:

1. **Backend:** Root Directory na raiz, entrypoint `backend.main:app` configurado em `pyproject.toml`;
2. **Frontend:** Root Directory em `frontend`, framework Vite e saída `dist`.

Antes de publicar:

1. execute `supabase/migrations/001_initial.sql` no Supabase;
2. configure no backend a URL do **Transaction Pooler**, porta 6543, em `DATABASE_URL`;
3. configure `CORS_ORIGINS` com o domínio exato do frontend;
4. configure `VITE_API_URL` no frontend com a URL do backend seguida de `/api`;
5. valide `https://URL-DO-BACKEND/api/health`.

Mais detalhes estão em [Deploy com Vercel e Supabase](docs/deploy-vercel-supabase.md).

## Documentação

- [Arquitetura](docs/architecture.md)
- [API](docs/api.md)
- [Decisões técnicas](docs/decisions.md)
- [Deploy com Vercel e Supabase](docs/deploy-vercel-supabase.md)
- [Plano de melhorias](docs/plano-de-melhorias.md)
- [Etapa 5 — Central de validação](docs/etapa-5-validacao.md)
