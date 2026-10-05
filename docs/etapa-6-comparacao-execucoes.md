# Etapa 6 — Comparação entre execuções

## Resultado

A página `/execucoes` ganhou um comparador de duas execuções. O link `/execucoes?base=1&alvo=2` pode ser compartilhado. A comparação é feita pela nova API aditiva `GET /api/run-comparisons?base=&target=`.

Para cada SKU alterado, a tela mostra:

- entradas e saídas do ranking;
- mudança de posição, score e confiança;
- sinais novos e removidos;
- decomposição da diferença de score em sinais e pesos;
- valores de evidência alterados.

A tela também compara:

- previsão e recomendação operacional por SKU;
- cobertura B2B2C por parceiro cadastrado;
- hash da planilha, data, pesos, limiares e limiares comerciais de cada execução.

Score, ranking, regras, processamento do Excel, previsão, recomendação operacional e sinais comerciais não foram alterados. A comparação apenas lê snapshots gravados. O hash do XLSM foi preservado (`03fa0ed4…803f`). Não houve deploy nem alteração de segredos.

## Snapshot ampliado

O `POST /api/runs` mantém a resposta `{"id"}` e passa a gravar a coluna opcional `comparison`, com `schema_version = 1`. O payload contém:

- **previsão por SKU:** status, modelo, próximo mês, 3 meses, WAPE, confiança e tendência;
- **recomendação operacional por SKU:** ação, quantidade, capacidade e confiança;
- **limiares comerciais** usados no registro;
- **cobertura por parceiro cadastrado:** cobertura, SKUs observados, catálogo, último sell-out e contagem de ações. Nenhum dado global é atribuído a parceiros.

Se a análise comercial falhar no momento do registro, o snapshot é gravado mesmo assim, com o motivo da falha. A seção B2B2C dessa execução aparece como indisponível na comparação.

Persistência:

- **SQLite:** a coluna é criada automaticamente com `ALTER TABLE` na primeira gravação ou leitura. Execuções existentes ficam com `comparison = NULL`.
- **PostgreSQL/Supabase:** a migração aditiva `supabase/migrations/002_run_comparison.sql` cria a coluna. O adaptador verifica se ela existe. Antes da migração, o registro continua funcionando sem o payload ampliado, e a comparação dessas execuções fica restrita ao ranking.

## Compatibilidade

| Situação | Ranking | Previsão/recomendação | B2B2C |
|---|---|---|---|
| Duas execuções da Etapa 6 | comparado | comparado | comparado |
| Uma execução anterior à Etapa 6 | comparado | recusado, com motivo | recusado, com motivo |
| Versão de snapshot diferente | comparado | recusado, com motivo | recusado, com motivo |
| Ranking sem campos necessários | recusado, com motivo | conforme payload | conforme payload |

Os limiares comerciais só são comparados quando as duas execuções os preservam. Se a execução alvo for anterior à base, a tela avisa. Se a planilha e a configuração forem iguais e mesmo assim houver diferença no ranking, a tela indica que a causa seria uma mudança de código.

## Como a mudança é explicada

Para cada SKU presente nas duas execuções, a diferença de score é decomposta:

- **sinal adicionado:** soma o peso do sinal na execução alvo;
- **sinal removido:** subtrai o peso do sinal na execução base;
- **peso alterado:** soma a diferença entre o peso do alvo e o peso da base.

Se a soma das parcelas for igual à diferença de score, a mudança está explicada. Caso contrário, o item é marcado como **Não explicado**. Quando o score fica igual mas a posição muda, a explicação informa que outros SKUs entraram, saíram ou mudaram de score. Mudanças de confiança mostram o motivo registrado na execução alvo.

## Verificação com dados reais

A API foi executada sobre **cópias** dos bancos locais. O `runtime/runs.db` original não foi alterado e continua com 1 execução, sem a nova coluna.

- **Execução legada #1 × nova #2:** o ranking foi comparado, com 41 SKUs iguais, pois a planilha é a mesma. Previsão e B2B2C foram recusadas com o motivo "registrada antes da comparação ampliada".
- **Execuções novas #2 × #3:** 0 mudanças em 41 SKUs no ranking, 50 SKUs na previsão e 8 parceiros.
- **Execução #3 × snapshot com peso de `LOW_SELLOUT_VISIBILITY` alterado de 2 para 12:**
  - 41 SKUs mudaram: 18 subiram e 21 desceram;
  - 20 SKUs tiveram score +10, e todos foram explicados pelo peso alterado (0 não explicados);
  - SKUs com score igual que desceram receberam a explicação de que outros SKUs subiram;
  - previsão e recomendação ficaram sem mudança.

A tela foi verificada em 375 e 1440 pixels, sem overflow horizontal do documento. O console não registrou erros da aplicação; apareceram apenas reconexões do Vite e avisos já existentes do React Router.

## Arquivos

### Criados

- `src/caderno_inteligente/run_comparison.py`
- `backend/run_comparisons.py`
- `supabase/migrations/002_run_comparison.sql`
- `frontend/src/types-runs.ts`
- `frontend/src/components/RunComparisonView.tsx`
- `frontend/scripts/test-run-comparison.mjs`
- `tests/test_run_comparison.py`
- `tests/test_run_comparisons_api.py`
- `tests/test_postgres_runs.py`
- `docs/etapa-6-comparacao-execucoes.md`

### Modificados

- `backend/main.py`: payload do snapshot e registro do router.
- `src/caderno_inteligente/runs.py`: coluna opcional e migração SQLite.
- `src/caderno_inteligente/persistence.py`: parâmetro opcional `comparison`.
- `src/caderno_inteligente/postgres_persistence.py`: detecção da coluna e fallback.
- `frontend/src/pages/RunsPage.tsx`: seletor, comparação e indicação de compatibilidade.
- `frontend/src/api.ts`: método `runComparison`.
- `frontend/src/types.ts`: campo opcional `comparison_schema_version`.
- `frontend/src/App.css`: estilos da comparação.
- `frontend/scripts/test-page-data.mjs`: leitura dedicada da comparação.
- `README.md`, `docs/api.md`, `docs/architecture.md`, `docs/decisions.md` e `docs/deploy-vercel-supabase.md`.

## Validação

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider
# 127 passed: 106 anteriores + 21 novos

cd frontend
node --test scripts/*.mjs
# 20 passed
npm run check
# Typecheck + build aprovados
```

Neste ambiente, o pytest precisou de `--basetemp` em uma pasta gravável. Sem isso, os testes que usam `tmp_path` falham com `PermissionError` antes de executar.

## Limitações

1. Execuções registradas antes desta etapa, incluindo a execução #1 local e as de produção, comparam apenas o ranking. Previsão, recomendação e cobertura não podem ser reconstruídas retroativamente.
2. A explicação decompõe o score em sinais e pesos. A causa operacional de um sinal novo aparece nos valores de evidência, que dependem do que o ranking gravou.
3. Uma mudança de código entre execuções com a mesma planilha e a mesma configuração é sinalizada, mas a comparação não identifica a versão do código, porque o snapshot não grava o commit.
4. Cenários simulados não são gravados como execução pela interface. O teste com pesos alterados gravou o snapshot diretamente pela camada de persistência.
5. O payload aumenta cada snapshot em cerca de 20 KB (o snapshot completo tem cerca de 95 KB), e não há limpeza ou retenção automática de execuções.
6. A seleção de execuções lista todas as execuções, sem paginação.
7. O link `/execucoes?base=&alvo=` mostra um aviso se uma das execuções não existir no banco do ambiente aberto. IDs locais e de produção são diferentes.

## Deploy manual — não executado

1. Revisar os arquivos e executar as validações acima.
2. **Supabase:** no SQL Editor, executar `supabase/migrations/002_run_comparison.sql`. A migração é aditiva e idempotente. Sem ela, a aplicação continua funcionando, mas novas execuções não preservam o payload ampliado.
3. **Backend:** publicar com a configuração atual. Não há variável nem segredo novo. Validar:
   - `/api/health`;
   - `POST /api/runs` duas vezes;
   - `GET /api/runs`, conferindo `comparison_schema_version = 1` nas novas execuções;
   - `GET /api/run-comparisons?base=A&target=B`.
4. Confirmar que `GET /api/runs/{id}` de execuções antigas continua respondendo, com `comparison: null`.
5. **Frontend:** Root Directory `frontend`, build `npm run build`, saída `dist`. Manter `VITE_API_URL` e o rewrite SPA.
6. Validar `/execucoes`, o deep link `/execucoes?base=A&alvo=B`, a atualização da página e uma comparação entre uma execução antiga e uma nova, que deve mostrar previsão e B2B2C como indisponíveis com o motivo.
