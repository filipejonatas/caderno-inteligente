# Caderno Inteligente

Protótipo de apoio à decisão do PCP em uma cadeia B2B2C. Ele lê uma base XLSM sem alterá-la e, a partir dela:

- valida os dados e calcula indicadores e regras auditáveis;
- ordena SKUs para atenção;
- prevê a demanda e sugere ações operacionais (por SKU) e comerciais (por parceiro);
- registra as decisões humanas.

**Nenhuma saída é uma decisão automática.** Cada prioridade e recomendação mostra motivos, evidências, origem dos dados, limitações, nível de confiança e exige revisão humana. Dado ausente é tratado como ausente, nunca como zero, e dados globais (estoque do CD, produção, capacidade, forecast) não são distribuídos entre parceiros.

## O que o protótipo responde

| Pergunta do PCP | Onde |
|---|---|
| O que exige atenção agora e por quê? | Visão geral e Prioridades: ranking por soma transparente de pesos de sete regras |
| Preciso produzir? Quanto? | Detalhe do SKU e Previsão: previsão de 3 meses, ação e quantidade sugerida, com o cálculo |
| Algum parceiro tem risco ou oportunidade? | Parceiros: matriz parceiro–SKU com sell-in, sell-out, estoque estimado e sugestão comercial |
| Quanto vamos faturar nos próximos meses? | Previsão e ação: faturamento estimado (previsão em unidades × preço vigente), sempre rotulado como estimativa, com erro do teste e, no SKU, o cálculo |
| Que evento do calendário vem aí e quando decidir? | Início e Previsão: alertas de eventos com data de decisão (início − lead time); no SKU, evidência histórica e cenário com evento, sempre como estimativa |
| Quanto confiar na análise? | Qualidade e Validação: cobertura de sell-out, baseline de previsão, casos congelados e falhas conhecidas |
| Por que a prioridade mudou? | Execuções: comparação entre snapshots, com decomposição do score |
| O que foi decidido? | Casos e Decisões: responsável, prazo, ação, efeito do dado do parceiro e tempo de análise |

## Arquitetura

```text
XLSM somente leitura → núcleo Python determinístico → FastAPI (cache do pipeline) → React + TypeScript + Vite
                                                         └→ SQLite local / PostgreSQL (Supabase) em produção
```

Detalhes, módulos, mapa de rotas, rewrite e cabeçalhos da Vercel estão em [Arquitetura](docs/architecture.md).

## Requisitos

- Python 3.11, 3.12 ou 3.13 (recomendado: 3.12; 3.14 não é suportado);
- Node.js 18 ou superior (recomendado: 20 ou mais recente) e npm.

## Preparar o ambiente

No PowerShell, a partir da raiz do projeto:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
cd frontend
npm install
cd ..
```

## Executar

Use dois terminais.

```powershell
# Terminal 1 — API
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

```powershell
# Terminal 2 — frontend
cd frontend
npm run dev
```

Acesse `http://127.0.0.1:5173`. O Vite encaminha `/api` para `127.0.0.1:8000`.

## Interface

O menu tem 6 entradas (Início, Produção, Parceiros, Confiança, Decisões, Avançado) e o botão **Ajuda** (guia) na barra superior. As rotas agrupadas aparecem como abas e continuam abrindo por URL.

| URL | Menu · página |
|---|---|
| `/guia` | Ajuda: trilhas por papel (PCP, Comercial, Gestão), glossário e perguntas frequentes. Funciona com a API fora do ar |
| `/` | Início: primeiro da fila e o porquê, 3 números e fila de atenção |
| `/prioridades` | Produção › Fila de atenção: ranking oficial com filtros na URL (`busca`, `familia`, `confianca`); o motivo principal é o sinal de maior peso; uma linha curta por SKU |
| `/previsoes` | Produção › Previsão e ação: ação e quantidade sugeridas por SKU; por padrão, só os que pedem atenção |
| `/skus/:sku` | Detalhe compartilhável: ação sugerida no topo, cálculo, dados do SKU, riscos e evidências, contexto dos parceiros; botões "Registrar decisão" e "Criar caso" |
| `/parceiros` | Parceiros › Oportunidades (padrão) e `?aba=parceiros`; filtros `regiao`, `canal`, `ordem` |
| `/parceiros/:codigo` | Matriz parceiro–SKU com evidências mensais na própria linha |
| `/casos` | Decisões › Casos; aceita `?sku=` |
| `/qualidade` | Confiança › Dados da planilha: integridade, lacunas e cobertura de sell-out |
| `/cenarios` | Avançado › Cenários: simulação de 2 pesos sem alterar o ranking oficial |
| `/execucoes` | Avançado › Execuções: `?base=&alvo=` compara duas execuções |
| `/decisoes` | Decisões › Registrar decisão; aceita `?sku=` |
| `/validacao` | Confiança › Validação: resumo, 3 números, falhas conhecidas e 2 abas, com exportação CSV e impressão |
| `/auditoria` | Confiança › Auditoria: casos de teste congelados, verificações de segurança, limitações, histórico de ajustes e método comercial |

Rotas inexistentes mostram uma página 404. O `frontend/vercel.json` redireciona deep links para o `index.html`, permitindo abrir ou atualizar qualquer URL interna.

## Validar

Tudo de uma vez, a partir da raiz:

```powershell
.\scripts\validate.ps1
```

Comandos individuais:

```powershell
# Testes Python: núcleo, API, persistência, segurança, contrato com o frontend e smoke test
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider
```

```powershell
# Frontend: typecheck, Vitest + Testing Library + axe-core, testes node, build e varredura de segredos no bundle
cd frontend
npm run check
```

Durante o desenvolvimento, `npm run test:watch` reexecuta os testes do frontend. Os testes usam fixtures sintéticas (`frontend/src/test/fixtures.ts`). O arquivo `frontend/src/test/contract-keys.json` lista os campos que o frontend lê e é validado contra a API real por `tests/test_frontend_contracts.py`.

## Configuração

| Item | Onde |
|---|---|
| Pesos do ranking | `config/prioritization_weights.json` |
| Limiares das regras | `config/rule_thresholds.json` |
| Limiares comerciais | `config/commercial_thresholds.json` |
| Fator de eventos (teto, janela de linha de base, antecedência) | `config/event_factors.json` |
| Linha de base, casos congelados e histórico de ajustes da validação | `config/validation_center.json` |

Variáveis de ambiente do backend (exemplo em `.env.example`):

| Variável | Padrão | Efeito |
|---|---|---|
| `DATABASE_URL` | — | Secreta. PostgreSQL/Supabase pelo Transaction Pooler; sem ela, SQLite em `runtime/` |
| `CORS_ORIGINS` | `localhost:5173` e `127.0.0.1:5173` em desenvolvimento | Origens exatas, sem caminho e sem curinga. Em produção, sem valor, nenhuma origem externa é aceita |
| `APP_ENV` | `development` | `production` retorna erros genéricos com código de referência |
| `DEMO_MODE` | `false` | `true` exibe aviso de dados fictícios que podem ser apagados |
| `WRITE_ENABLED` | `true` | `false` bloqueia decisões, casos e execuções (403); consultas e simulações continuam |
| `LOG_LEVEL` | `INFO` | Nível de log; os logs nunca imprimem `DATABASE_URL` |

No frontend, `VITE_API_URL` é a URL pública da API (com `https://`). Sem ela, o frontend usa `/api`. O cache do backend é invalidado automaticamente quando a planilha ou os arquivos de pesos e limiares mudam. Nunca versione arquivos `.env` reais.

**Limpeza de dados de demonstração:** `python scripts/reset_demo_data.py` apenas conta os registros. Com `--confirm`, faz backup em JSON e limpa. Com `--postgres`, usa a `DATABASE_URL` do ambiente. A planilha nunca é alterada.

## Publicar com Vercel e Supabase

O deploy usa dois projetos Vercel do mesmo repositório:

1. **Backend:** Root Directory na raiz, entrypoint `backend.main:app` (em `pyproject.toml`);
2. **Frontend:** Root Directory `frontend`, framework Vite e saída `dist`.

Antes de publicar:

1. execute `supabase/migrations/001_initial.sql` e `supabase/migrations/002_run_comparison.sql` no Supabase, nessa ordem;
2. configure no backend `DATABASE_URL` (Transaction Pooler, porta 6543), `CORS_ORIGINS` com o domínio exato do frontend e `APP_ENV=production`;
3. se for demonstração aberta, configure também `DEMO_MODE=true` e, opcionalmente, `WRITE_ENABLED=false`;
4. configure no frontend `VITE_API_URL` com a URL do backend seguida de `/api`.

Depois de publicar, rode o smoke test (somente leitura):

```powershell
.\.venv\Scripts\python.exe scripts\smoke_test.py --backend https://URL-DO-BACKEND --frontend https://URL-DO-FRONTEND --expect-environment production
```

Passo a passo completo em [Deploy com Vercel e Supabase](docs/deploy-vercel-supabase.md).

## Documentação

**Produto e demonstração**

- [Roteiro de demonstração — 5 minutos](docs/roteiro-demonstracao.md)
- [Semana 4 — Validação da V2](docs/semana-4-validacao-v2.md)
- [Semana 3 — Modelo preditivo](docs/semana-3-modelo-preditivo.md)
- [Plano da V2](docs/plano-v2-prototipo-top.md)
- [Plano de aderência ao desafio](docs/plano-aderencia-desafio.md)

**Referência técnica**

- [Arquitetura e mapa de rotas](docs/architecture.md)
- [API](docs/api.md)
- [Cálculos](docs/calculations.md), [regras](docs/rules.md), [priorização](docs/prioritization.md) e [regras comerciais](docs/commercial-rules.md)
- [Decisões técnicas](docs/decisions.md)
- [Deploy com Vercel e Supabase](docs/deploy-vercel-supabase.md)

**Registro das etapas da V2**

- [Etapa 2 — Carregamento por página](docs/etapa-2-carregamento-por-pagina.md)
- [Etapa 3 — Jornada visual](docs/etapa-3-jornada-visual.md)
- [Etapa 4 — Parceiros e recomendação comercial](docs/etapa-4-parceiros-comercial.md)
- [Etapa 5 — Central de validação](docs/etapa-5-validacao.md)
- [Etapa 6 — Comparação entre execuções](docs/etapa-6-comparacao-execucoes.md)
- [Etapa 7 — Testes do frontend, acessibilidade e robustez](docs/etapa-7-testes-acessibilidade.md)
- [Etapa 8 — Segurança e modo de demonstração](docs/etapa-8-seguranca-modo-demo.md)
- [Etapa 9 — Documentação, deploy e demonstração](docs/etapa-9-documentacao-demo.md)
- [Etapa 10 — Previsão de faturamento (plano de aderência ao desafio)](docs/etapa-10-faturamento-estimado.md)
- [Etapa 11 — Sazonalidade e eventos (plano de aderência ao desafio)](docs/etapa-11-eventos-sazonalidade.md)
