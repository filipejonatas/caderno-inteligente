# Etapa 9 — Documentação, deploy e demonstração

## Resultado

| Item do plano | Entrega |
|---|---|
| Atualizar README, arquitetura, API, cálculos, regras e Guia de uso | `README.md` reescrito para a V2; `docs/architecture.md` consolidado; `docs/api.md` com índice completo de endpoints; `docs/calculations.md` consolidado; `docs/rules.md` e `docs/prioritization.md` atualizados; Guia de uso (`/guia`) com páginas, glossário, perguntas e roteiro atualizados |
| Documentar mapa de rotas e rewrite da Vercel | Seções "Mapa de rotas" e "Publicação" em `docs/architecture.md`, tabela de rotas no README e cabeçalhos/rewrite em `docs/deploy-vercel-supabase.md` |
| Criar `docs/semana-4-validacao-v2.md` | Método, amostra, resultados, falhas, mudanças da V1 para a V2 e protocolo do teste moderado com usuários |
| Roteiro de demonstração de cinco minutos | `docs/roteiro-demonstracao.md`, nos cinco blocos do plano, com URLs diretas, números reais, preparação, plano B e perguntas prováveis; versão resumida no Guia |
| Executar suíte Python, testes do frontend e build | Ver Validação |
| Smoke test das URLs publicadas | `scripts/smoke_test.py`: smoke test somente leitura para rodar após o deploy manual. Validado por HTTP contra servidores locais (o deploy não foi feito nesta etapa) |

Nada foi alterado em score, ranking, regras, processamento do Excel, previsão, recomendação operacional ou APIs. A única mudança de código da aplicação é o texto do Guia de uso. O hash do XLSM foi preservado. Não houve deploy nem alteração de segredos.

## Smoke test

```powershell
.\.venv\Scripts\python.exe scripts\smoke_test.py --backend https://API --frontend https://APP --expect-environment production [--expect-readonly] [--expect-demo]
```

São 44 verificações quando o frontend é informado, mais uma para cada expectativa de modo (`--expect-environment`, `--expect-readonly`, `--expect-demo`), até 47. Elas cobrem backend, dados, comercial, validação, segurança (CORS e sondagem de escrita) e frontend (rewrite, cabeçalhos e bundle sem segredos).

- **Nenhum dado é gravado:** a única requisição de escrita usa um SKU inexistente e precisa ser recusada.
- **Dependências:** apenas a biblioteca padrão do Python.
- **Saída:** código 1 quando qualquer item falha.

Execuções locais por HTTP, com o build servido usando os cabeçalhos reais de `frontend/vercel.json`:

| Configuração da API | Resultado |
|---|---|
| Padrão de desenvolvimento (CORS só para `localhost:5173`) com frontend em `:4173` | 44/45. A falha esperada foi "CORS aceita o frontend": o script detectou corretamente a origem fora de `CORS_ORIGINS` |
| `APP_ENV=production`, `DEMO_MODE=true`, `WRITE_ENABLED=false` e `CORS_ORIGINS` com o frontend | 47/47; a sondagem de escrita recebeu 403 |

`tests/test_smoke_test.py` roda o script contra a API real (com banco isolado) e um frontend simulado com os cabeçalhos do `vercel.json`. Os testes confirmam:

- aprovação na configuração correta;
- falhas quando faltam rewrite ou CSP, quando o modo esperado diverge, quando há segredo no bundle e quando a rede está indisponível;
- que a sondagem de escrita não grava nada.

## Arquivos

### Criados

- `docs/semana-4-validacao-v2.md`
- `docs/roteiro-demonstracao.md`
- `docs/etapa-9-documentacao-demo.md`
- `scripts/smoke_test.py`
- `tests/test_smoke_test.py`

### Modificados

- `README.md`
- `docs/architecture.md`, `docs/api.md`, `docs/calculations.md`, `docs/rules.md`, `docs/prioritization.md`, `docs/deploy-vercel-supabase.md` e `docs/decisions.md`
- `frontend/src/pages/GuidePage.tsx`: descrições das páginas, glossário (recomendações operacional e comercial, WAPE e baseline), perguntas frequentes (prioridade × produção, comparação de execuções, modos demonstração e somente leitura), fluxo em cinco passos e roteiro de 5 minutos

## Validação

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider
# 193 passed: 187 anteriores + 6 do smoke test

cd frontend
npm run check
# typecheck ✓ · Vitest 131 passed · node --test 20 passed · build ✓ · bundle sem segredos ✓
```

- Os links relativos de `README.md` e `docs/*.md` foram verificados por script, sem links quebrados.
- O Guia foi conferido no build servido com CSP: 5 passos, roteiro de 5 minutos, 8 perguntas e 10 páginas, sem overflow horizontal.
- Neste ambiente, o pytest usa `--basetemp` em uma pasta gravável, como nas etapas anteriores.

## Limitações

1. **Deploy não executado:** o smoke test das URLs publicadas precisa ser rodado por quem fizer o deploy. Aqui ele foi validado contra servidores locais equivalentes.
2. **Números datados:** os números do relatório da Semana 4 e do roteiro valem para a planilha atual (hash `03fa0ed4…803f`). A Central de validação sempre mostra os valores atualizados.
3. **Teste com usuários:** o teste moderado (PCP, Comercial e uma pessoa sem contexto) não foi realizado. O protocolo e a planilha de registro estão no relatório da Semana 4.
4. **Documentos de plano:** os planos antigos em `docs/plano-*.md` foram mantidos como histórico e não foram reescritos; a referência atual é a listada no README.
5. **Limite de tempo do smoke test:** o tempo limite de cada requisição é de 60 s, pensado para a primeira chamada serverless, que é mais lenta. Execuções seguidas são mais rápidas.

## Deploy manual — não executado

1. Revisar os arquivos e executar as validações acima.
2. **Supabase:** confirmar que `001_initial.sql` e `002_run_comparison.sql` foram executadas.
3. **Backend:** publicar com `DATABASE_URL`, `CORS_ORIGINS` (domínio exato do frontend) e `APP_ENV=production`. Para demonstração, acrescentar `DEMO_MODE=true`; para publicação aberta sem registro, `WRITE_ENABLED=false`.
4. **Frontend:** publicar com Root Directory `frontend`, `npm run build`, saída `dist` e `VITE_API_URL=https://BACKEND/api`.
5. Rodar `scripts/smoke_test.py` com as URLs publicadas e as expectativas de modo; o resultado esperado é `N/N verificações aprovadas`.
6. Seguir a "Conferência manual complementar" em `docs/deploy-vercel-supabase.md`.
7. Ensaiar o `docs/roteiro-demonstracao.md` cronometrando cada bloco.
