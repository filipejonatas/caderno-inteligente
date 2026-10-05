# Arquitetura

```text
XLSM (somente leitura, empacotado no deploy)
        │
        ▼
Núcleo Python determinístico — src/caderno_inteligente/
  ingestão → validação → normalização → indicadores → regras → priorização
                                         └→ previsão → recomendação operacional
                                         └→ visão parceiro–SKU (comercial)
        │
        ▼
FastAPI — backend/  (pipeline em cache, routers aditivos, segurança)
        │                              │
        ▼                              ▼
React + TypeScript + Vite        SQLite local / PostgreSQL (Supabase)
frontend/                        decisões, casos, histórico e execuções
```

O protótipo apoia o PCP com sinais auditáveis. Nenhum componente libera produção, altera a planilha ou grava configuração oficial.

## Núcleo Python (`src/caderno_inteligente/`)

| Módulo | Responsabilidade |
|---|---|
| `ingestion.py`, `validation.py`, `transformations.py` | Leitura das abas com cabeçalho na linha 3, validação sem correção silenciosa e normalização em cópias internas |
| `indicators.py` | Uma linha por SKU: cobertura, carteira, produção aberta, datas, sell-in/out, capacidade familiar ([cálculos](calculations.md)) |
| `rules.py`, `prioritization.py` | Sete regras determinísticas e soma transparente de pesos ([regras](rules.md), [priorização](prioritization.md)) |
| `forecasting.py`, `recommendations.py` | Previsão mensal (média móvel 3m × sazonal 12m, holdout de 3 meses) e ação/quantidade sugerida por SKU ([Semana 3](semana-3-modelo-preditivo.md)) |
| `partner_insights.py` | Pares parceiro–SKU reais, sinais e ações comerciais ([regras comerciais](commercial-rules.md)) |
| `validation_center.py` | Linha de base, baseline de previsão, casos congelados e comportamento seguro ([Semana 4](semana-4-validacao-v2.md)) |
| `run_comparison.py`, `runs.py` | Snapshot versionado e comparação entre execuções |
| `persistence.py`, `postgres_persistence.py`, `feedback.py`, `cases.py` | Mesmo contrato em SQLite e PostgreSQL |

## Backend (`backend/`)

- `main.py` monta o pipeline e o mantém em **cache em memória**. O cache é protegido contra reconstruções concorrentes e invalidado quando mudam a data ou o tamanho do XLSM, dos pesos ou dos limiares.
- Routers aditivos:
  - `partners.py`: visão comercial;
  - `validation.py`: Central de validação;
  - `run_comparisons.py`: comparação de execuções.
- `security.py` reúne:
  - ambiente (`APP_ENV`);
  - modo demonstração (`DEMO_MODE`);
  - escrita desabilitável (`WRITE_ENABLED`);
  - CORS validado;
  - limite de corpo de 16 KB;
  - erros genéricos em produção com `X-Request-ID`;
  - cabeçalhos de segurança;
  - filtro que remove `DATABASE_URL` dos logs.
- A persistência usa SQLite em `runtime/` localmente. Quando `DATABASE_URL` existe, usa o Transaction Pooler do Supabase, com prepared statements desabilitados.
- O contrato completo dos endpoints está em [API](api.md).

## Frontend (`frontend/src/`)

- **Organização:**
  - contratos em `types*.ts`;
  - acesso à API em `api.ts`;
  - componentes em `components.tsx` e `components/`;
  - hooks em `hooks/`;
  - uma página por arquivo em `pages/`;
  - orquestração em `App.tsx`.
- **Carregamento por rota:** cada página consulta só o que exibe. As páginas usam `React.lazy`, e as leituras são canceladas ao trocar de rota.
- **Robustez:** um error boundary por rota evita tela em branco quando a página falha ou um chunk deixa de existir após um deploy.
- **Páginas estáticas:** o Guia e a 404 não consultam a API.
- **Modo da publicação:** o modo vem de `GET /api/system` e só é consultado em páginas com dados. Ele gera o aviso de demonstração ou de somente leitura e desabilita os formulários quando a escrita está bloqueada. O servidor continua aplicando a regra em qualquer caso.
- **Acessibilidade:**
  - título da aba por rota;
  - link "Pular para o conteúdo";
  - foco no título após cada navegação;
  - gaveta móvel com foco e tecla Esc;
  - contraste WCAG AA nos tokens de cor.

### Mapa de rotas

| URL | Página | Dados consultados |
|---|---|---|
| `/guia` | Guia de uso | Nenhum (funciona com a API fora do ar) |
| `/` | Visão geral | `overview`, `priorities`, `data-quality` |
| `/prioridades` | Prioridades — filtros `busca`, `familia`, `confianca` na URL | `priorities` |
| `/previsoes` | Previsão e recomendações — filtros `busca`, `familia`, `acao`, `confianca`, `tendencia`, `atencao`, `ordem` | `forecasts` |
| `/skus/:sku` | Detalhe do SKU (compartilhável) | `priorities/{sku}`, `commercial-recommendations?sku=` |
| `/casos` | Casos | `cases`, `priorities`, `config` |
| `/qualidade` | Qualidade dos dados | `data-quality` |
| `/parceiros` | Parceiros e canais — filtros `regiao`, `canal`, `ordem` | `partners` |
| `/parceiros/:codigo` | Detalhe do parceiro — filtros `sku`, `acao`, `qualidade`, `offset` | `partners/{codigo}`, `partners/{codigo}/skus` |
| `/cenarios` | Simulação de cenários | `config`, `POST scenarios` |
| `/execucoes` | Execuções; comparação em `?base=&alvo=` | `runs`, `run-comparisons` |
| `/decisoes` | Decisões (feedback do PCP) | `feedback`, `priorities`, `config` |
| `/validacao` | Central de validação | `validation/summary` |
| `*` | Página não encontrada | Nenhum |

Códigos de SKU e de parceiro são codificados na URL com `encodeURIComponent`, por exemplo `/parceiros/Loja%20pr%C3%B3pria`.

## Publicação (Vercel + Supabase)

O deploy usa dois projetos Vercel do mesmo repositório.

- **Backend:**
  - Root Directory na raiz, com entrypoint `backend.main:app` (definido em `pyproject.toml`);
  - `vercel.json` empacota `config/**`, `data/source/**` e `src/caderno_inteligente/**`;
  - a Function não escreve no filesystem.
- **Frontend:**
  - Root Directory `frontend`, build `npm run build` e saída `dist`;
  - o `frontend/vercel.json` define as regras abaixo.

### Regras do `frontend/vercel.json`

- **Rewrite:** `"source": "/(.*)" → "/index.html"`. Abrir ou atualizar qualquer rota interna entrega a SPA, e o React Router resolve a página. Arquivos existentes em `dist/` continuam sendo servidos diretamente.
- **Cabeçalhos:**
  - `Content-Security-Policy` sem `unsafe-inline` e com `connect-src 'self' https:`, porque o domínio da API varia;
  - `X-Content-Type-Options: nosniff`;
  - `X-Frame-Options: DENY`;
  - `Referrer-Policy: no-referrer`;
  - `Permissions-Policy`.

O passo a passo, as variáveis e o smoke test estão em [Deploy com Vercel e Supabase](deploy-vercel-supabase.md).

## Testes

- **Python:** `pytest` cobre núcleo, API, persistência, segurança, contrato com o frontend e o próprio smoke test.
- **Frontend:** `npm run check` executa, em ordem:
  1. typecheck;
  2. Vitest + Testing Library + axe-core (rotas, teclado, estados, acessibilidade, contraste e contratos);
  3. testes `node --test`;
  4. build;
  5. varredura de segredos no bundle.
- **Contrato entre as camadas:** `frontend/src/test/contract-keys.json` lista os campos que o frontend lê. O arquivo é validado contra as fixtures no Vitest e contra a API real no pytest.
