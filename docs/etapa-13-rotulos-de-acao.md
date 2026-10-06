# Etapa 13 — Rótulos de ação do desafio (camada aditiva)

Quarta e última etapa do [plano de aderência ao desafio](plano-aderencia-desafio.md). O PDF pede recomendações como "Produzir, Repor, Priorizar produção, Priorizar parceiro, Ampliar mix, Recomendar recompra, Monitorar, Investigar, Sem ação necessária". Esta etapa adiciona um segundo campo, `challenge_action`, derivado dos sinais que já existiam. **Não é um motor novo**: os campos `action` existentes, o score, o ranking, a previsão e as quantidades não mudaram.

## Resultado

| Item do plano | Entrega |
|---|---|
| Módulo derivado, sem motor novo | `src/caderno_inteligente/action_labels.py`: funções puras que leem a ação operacional, a ação comercial, os alertas de evento (Etapa 11) e as sugestões dos canais diretos (Etapa 12) e devolvem rótulo, sinais usados, evidências, limitações e `requires_human_review` |
| Precedência documentada | Tabela abaixo e `docs/commercial-rules.md`. Dado insuficiente vence tudo |
| Limiares em configuração | `config/challenge_actions.json`, validado no carregamento |
| Sem dado, sem rótulo | Sem sell-out suficiente, o rótulo é "Investigar" com o motivo. Nenhum parceiro sem sell-out recebe oportunidade inferida |
| Campo opcional nas APIs | `challenge_action` em `/api/forecasts`, `/api/priorities/{sku}`, `/api/commercial-recommendations`, `/api/partners` e `/api/partners/{codigo}/skus`, e em cada SKU de `/api/direct-channels/{canal}` |
| Filtro por rótulo | Parâmetro `challenge_action` nas APIs; na tela, filtro "Rótulo" em Previsão, Parceiros (aba Parceiros), detalhe do parceiro e detalhe do canal |
| Legenda no Guia | Cada rótulo e sua definição no glossário do Guia |
| Registro da decisão | `feedback.challenge_action` opcional (migração `003_challenge_action.sql`) |
| Casos congelados | 11 casos novos (VC-09 a VC-19), um por rótulo, executados pelo mesmo rotulador do produto |

## Os rótulos e de onde vêm

| Rótulo | Quando aparece | Sinais lidos |
|---|---|---|
| **Produzir** | Há necessidade líquida de produção, sem urgência | ação `produzir` ou `produzir_validar_capacidade` |
| **Priorizar produção** | Produzir com urgência | a mesma ação **e** (posição ≤ 10 na fila de atenção **ou** decisão de evento no horizonte dentro de 30 dias) |
| **Repor** | Cobertura baixa no parceiro | `avaliar_reposicao` (`REPOSITION_OPPORTUNITY`) |
| **Priorizar parceiro** | Parceiro com várias reposições | 2 ou mais pares `Repor` no parceiro, com pelo menos um SKU entre os 10 primeiros da fila |
| **Recomendar recompra** | O parceiro vende mas parou de receber | sell-in com intervalo maior que o ritmo do próprio par (≥ 2 meses e ≥ 2× o intervalo típico), sell-out recente positivo e 3 meses de sell-in no histórico; só quando a ação comercial é monitorar |
| **Ampliar mix** | Produto ativo sem faturamento no canal | `NOT_SOLD` nos canais diretos |
| **Reativar** | Vendia e parou | `STOPPED` nos canais diretos (rótulo a mais, vindo do plano e do texto do desafio) |
| **Monitorar** | Sem urgência | excesso de cobertura, estoque do parceiro sem exceção, saída de linha ou crescimento no canal |
| **Investigar** | Faltam dados ou há divergência | histórico insuficiente, dado antigo, dado insuficiente, divergência sell-in × sell-out ou queda no canal |
| **Sem ação necessária** | Nenhum sinal | `sem_acao_necessaria` |

### Precedência

- **SKU (operacional):** investigar (previsão insuficiente) → priorizar produção ou produzir → monitorar (excesso) → sem ação.
- **Parceiro–SKU (comercial):** investigar (dado antigo, insuficiente ou divergente) → repor → recomendar recompra → monitorar.
- **Parceiro:** priorizar parceiro, só com as condições acima; senão, sem rótulo no nível do parceiro.
- **Canal direto:** ampliar mix → reativar → monitorar saída de linha → investigar queda → monitorar crescimento → sem ação.

### Por que "Ampliar mix" não é inferido para parceiros

Os parceiros B2B têm sell-out em 10 dos 50 SKUs, e a Etapa 12 mostrou que Sell_In e `Vendas_24m` não coincidem para eles. Ausência de registro, portanto, não prova que o parceiro não vende o SKU. O rótulo só sai onde a ausência é observada: os canais diretos, com faturamento completo.

## Contrato (aditivo)

- Todo `challenge_action` tem: `code`, `label`, `source` (`operational`, `commercial`, `partner` ou `channel`), `origin_action` (a ação existente que o originou), `reason`, `signals_used`, `evidence[]` (rótulo, valor, origem), `limitations[]` e `requires_human_review`.
- `GET /api/partners` retorna `challenge_action = null` quando o parceiro não se qualifica; não há rótulo "neutro" no nível do parceiro.
- Os filtros `challenge_action` validam o código (422 para valor inválido). `priorizar_parceiro` filtra pelo parceiro; os demais, pelas linhas parceiro–SKU.
- `POST /api/feedback` aceita `challenge_action` opcional, validado contra os códigos conhecidos. `GET /api/feedback` retorna o campo (`null` em decisões anteriores). `list_feedback()` manteve o formato de tupla; a leitura com o rótulo é `list_feedback_records()`.
- `frontend/src/test/contract-keys.json` ganhou os campos novos. Um teste Python compara os nomes e as definições do frontend (`CHALLENGE_NAMES` e `CHALLENGE_DEFINITIONS`) com o backend.

## Migração 003 (Supabase)

`supabase/migrations/003_challenge_action.sql` adiciona a coluna `feedback.challenge_action text`, nula e sem restrição. É aditiva e idempotente. O adaptador PostgreSQL detecta a coluna: sem a migração, a decisão é gravada sem o rótulo e a API continua funcionando. No SQLite local, a coluna é criada sozinha em bancos antigos, sem perder linhas.

## Números na planilha atual (hash `03fa0ed4…`)

| Rótulo | Ocorrências |
|---|---|
| Priorizar produção | 4 SKUs: CI-0049 (posição 5) e CI-0018 (posição 9) pela fila; CI-0036 e CI-0012 pela decisão da Coleção Primavera até 29/09 |
| Produzir | os outros 10 SKUs a produzir |
| Repor | 12 pares parceiro–SKU |
| Priorizar parceiro | 1 parceiro (Rede Ponto Criativo, KA-02): 2 reposições, incluindo CI-0015 na posição 7 |
| Investigar | 46 pares parceiro–SKU (45 sem sell-out suficiente e 1 divergência de sell-in × sell-out) e 4 SKUs em queda em cada canal direto |
| Monitorar | 37 pares com estoque do parceiro sem exceção, 6 SKUs com excesso de cobertura e, em cada canal direto, 4 SKUs em crescimento e 2 produtos em saída de linha |
| Ampliar mix, Recomendar recompra, Reativar | **nenhuma ocorrência**: os canais vendem os 50 SKUs todos os meses e todo par tem sell-in mensal sem lacuna |

Os três últimos rótulos existem, são testados e têm caso congelado, mas esta base não os dispara. Dizer isso na demonstração é mais honesto do que forçar um exemplo.

A regra de evento para "Priorizar produção" mede o **prazo de decisão**, não o aumento de demanda: a Coleção Primavera não tem histórico direto (Etapa 11) e, ainda assim, faz a decisão vencer dentro de 30 dias. A tela mostra qual critério disparou, no "?" do selo.

## Decisões de projeto

1. **Arquivo de configuração próprio** (`config/challenge_actions.json`) e não uma chave dentro de `commercial_thresholds.json`, como o plano sugeria. O carregador comercial rejeita campos desconhecidos de propósito; ampliá-lo acoplaria dois conjuntos de limiares.
2. **O campo da ação existente continua sendo a fonte.** O rótulo traz `origin_action` e a tela mostra o rótulo ao lado da ação atual, nunca no lugar dela.
3. **Previsão: sem coluna nova.** A tabela de Previsão já está no limite de quatro colunas do orçamento de volume. O rótulo aparece como selo na célula da ação, só quando acrescenta informação (Priorizar produção); nos outros casos o texto já é o mesmo. O filtro "Rótulo" cobre todos.
4. **Orçamento de volume:** um único limite mudou, `/guia` de 400 para 500 palavras, porque a página é de documentação e passou a trazer a definição dos dez rótulos. As demais telas ficaram dentro do orçamento (Previsão exatamente no limite).
5. **Casos congelados todos sintéticos.** Servem de prova das regras. Quatro rótulos não ocorrem na base, e os demais seriam sensíveis a pequenas mudanças de limiar. O motivo está em cada caso (`origin_reason`) e no histórico de ajustes.
6. **`scripts/smoke_test.py`:** a verificação "casos congelados avaliados" exigia exatamente 8 casos. Passou a exigir pelo menos 8 e todos aprovados, que é a intenção original. O número de verificações não mudou.

## Limitações

- Os rótulos são demonstrativos e exigem revisão humana; nenhum cria ordem de produção nem altera a quantidade oficial.
- O estoque do parceiro é estimado; não há estoque por canal direto.
- Os limiares (10 primeiros da fila, 30 dias de decisão, 2 reposições, 3 meses de sell-in e 2 meses sem sell-in) não foram validados pela empresa.
- O rótulo gravado na decisão não é exibido no histórico de decisões (orçamento de volume); fica disponível na API para a validação de aceitação por rótulo.
- A decisão por parceiro continua sem atribuição: o feedback não registra o código do parceiro.

## Arquivos

### Criados

- `src/caderno_inteligente/action_labels.py` e `config/challenge_actions.json`
- `supabase/migrations/003_challenge_action.sql`
- `tests/test_action_labels.py`
- `frontend/src/types-actions.ts`, `components/ChallengeAction.tsx` e `test/actions.test.tsx`
- `docs/etapa-13-rotulos-de-acao.md`

### Modificados

- Backend: `backend/main.py` (rótulos em Previsão e SKU, enriquecimento comercial, feedback), `backend/partners.py` (gancho de enriquecimento e filtro), `backend/direct_channels.py`, `backend/validation.py`
- Núcleo: `feedback.py`, `persistence.py`, `postgres_persistence.py` e `validation_center.py` (avaliador dos casos de rótulo)
- Configuração: `config/validation_center.json` (casos VC-09 a VC-19 e entrada no histórico de ajustes)
- Frontend: `types.ts`, `types-commercial.ts`, `types-channels.ts`, `pages/shared.ts` (nomes e definições), `ForecastsPage.tsx`, `SkuDetailPage.tsx`, `FeedbackPage.tsx`, `B2BPage.tsx`, `PartnerDetailPage.tsx`, `ChannelDetailPage.tsx`, `GuidePage.tsx`, `components/CommercialMatrix.tsx` e `components/ChannelViews.tsx`
- Testes: `fixtures.ts`, `contract-keys.json`, `usability.test.tsx`, `channels.test.tsx`, `scripts/test-decision-journey.mjs`, `volume-budget.json`, `tests/test_validation_api.py`, `tests/test_validation_center.py` e `scripts/smoke_test.py`
- Docs: `api.md`, `calculations.md`, `commercial-rules.md`, `deploy-vercel-supabase.md`, `README.md` e `plano-aderencia-desafio.md`

## Validação

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider
cd frontend; npm run check
```

- **Python:** 274 testes passando. Os novos cobrem: tabela-verdade de cada rótulo e de cada conflito de precedência, ausência de dado como "Investigar", janela do evento, limiares, filtros da API, vocabulário idêntico ao do frontend, caso congelado por rótulo, gravação do rótulo na decisão, migração de um SQLite antigo sem perder linhas e a migração 003 aditiva.
- **Frontend:** 223 testes do Vitest, 21 do `node --test`, typecheck, build e varredura de segredos passando.
- **Regressão:** o hash das respostas de `/api/forecasts` (sem o campo novo), `/api/priorities`, `/api/overview` e `/api/data-quality` é idêntico ao de antes da Etapa 10. A planilha está intacta.
- **Casos congelados:** 19 de 19 passando na Central de validação.
- **Navegador:** conferido com a API real em `/previsoes?rotulo=priorizar_producao` e `/parceiros?aba=parceiros`, sem erros.

## Não feito nesta etapa

- Sem deploy e sem alteração de segredos. **A migração 003 precisa ser executada manualmente no Supabase** para o rótulo ser gravado em produção; sem ela, o resto funciona.
- Os endpoints novos continuam fora do `scripts/smoke_test.py`.
- Sem rótulo "Ampliar mix" para parceiros B2B e sem rótulo no nível de região.
