# Regras determinísticas

As regras retornam uma ocorrência por SKU quando a condição é satisfeita. Cada ocorrência contém código, descrição, severidade, valores usados e campos de origem. Elas não ordenam prioridades nem liberam produção.

## Regras dos indicadores

| Código | Condição | Severidade |
|---|---|---|
| `RUP_LEAD_TIME` | cobertura calculada < lead time | alta |
| `RUP_SAFETY_STOCK` | cobertura calculada < estoque de segurança | crítica |
| `ORDER_WITHOUT_PRODUCTION` | há carteira e a quantidade de OP é zero | alta |
| `PRODUCTION_AFTER_PROMISE` | primeira conclusão de OP > primeira data prometida | alta |
| `EXCESS_COVERAGE` | cobertura calculada > 90 dias configurados | média |
| `LOW_SELLOUT_VISIBILITY` | SKU sem sell-out observado | média |

A cobertura calculada usa a demanda diária de referência (previsão oficial dos 3 próximos meses); `values_used` traz `daily_demand` e `demand_source`.

## Regras do plano datado (Etapa 15)

| Código | Condição | Severidade |
|---|---|---|
| `PROJECTED_SHORTFALL` | falta projetada ou pedido atrasado antes que uma reposição nova possa chegar (data de planejamento + lead time) | crítica |
| `CAPACITY_SHORTFALL` | alguma ordem planejada não cabe na capacidade livre da linha até a data de necessidade | alta |
| `OP_FOR_DISCONTINUED` | há OP aberta para produto em descontinuação | alta |
| `PARTNER_STOCK_BUILDUP` | algum parceiro com estoque acumulando no SKU (ver [regras comerciais](commercial-rules.md)) | média |
| `PROJECTED_EXCESS` | depois da chegada da OP, o estoque projetado passa de 90 dias de demanda + segurança | média |

`CAPACITY_CONFLICT` (ocupação média da família > 90%) foi substituída por `CAPACITY_SHORTFALL` na Etapa 15.4; o código continua reconhecido em execuções antigas.

## Limites configuráveis

Os limites de excesso e de divergência do cadastro estão em [config/rule_thresholds.json](../config/rule_thresholds.json); os do plano (data de planejamento, janela de decisão, cobertura-alvo, excesso projetado) em [config/supply_plan.json](../config/supply_plan.json). Alterações de regra ou limiar devem ser registradas em `docs/decisions.md` e no histórico de ajustes da validação.

## Limitação de atraso

A fonte não associa uma OP específica a um pedido. `PRODUCTION_AFTER_PROMISE` compara a primeira conclusão de OP com a primeira promessa do SKU (sinal de risco). A data de falta de `PROJECTED_SHORTFALL` vem da projeção diária, com a carteira priorizada sobre a previsão; também é estimativa.

## Uso dos sinais

- O score do [ranking](prioritization.md) soma os pesos dos sinais ativos de cada SKU.
- A [recomendação operacional](calculations.md#4-plano-de-suprimento-e-recomendação-operacional-supply_planpy-recommendationspy) usa o plano datado; `CAPACITY_SHORTFALL` exige validar capacidade e `EXCESS_COVERAGE` sustenta "monitorar excesso".
- Em **Cenários**, pesos (0 a 100) e o limiar `excess_coverage_days` (1 a 3650) podem ser simulados sem alterar a configuração oficial; o plano datado é o mesmo da execução oficial.
- Os sinais comerciais por parceiro (`REPOSITION_OPPORTUNITY`, `PARTNER_STOCK_BUILDUP`, `PARTNER_EXCESS_RISK`, `SELLIN_SELLOUT_DIVERGENCE`, `STALE_PARTNER_DATA`, `INSUFFICIENT_PARTNER_DATA`) têm ações próprias; só o acúmulo sobe para o score do SKU.
