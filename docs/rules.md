# Regras determinísticas — Etapa 3

As regras retornam uma ocorrência por SKU quando a condição é satisfeita. Cada ocorrência contém código, descrição, severidade, valores usados e campos de origem. Elas não ordenam prioridades nem liberam produção.

| Código | Condição | Severidade |
|---|---|---|
| `RUP_LEAD_TIME` | cobertura calculada < lead time | alta |
| `RUP_SAFETY_STOCK` | cobertura calculada < estoque de segurança | crítica |
| `ORDER_WITHOUT_PRODUCTION` | há carteira e a quantidade de OP é zero | alta |
| `PRODUCTION_AFTER_PROMISE` | primeira conclusão de OP > primeira data prometida | alta |
| `EXCESS_COVERAGE` | cobertura calculada > 90 dias configurados | média |
| `CAPACITY_CONFLICT` | ocupação média da família > 90% configurados | alta |
| `LOW_SELLOUT_VISIBILITY` | SKU sem sell-out observado | média |

## Limites configuráveis

Os limites de excesso e capacidade estão em [config/rule_thresholds.json](../config/rule_thresholds.json). Alterações de regra ou limiar devem ser registradas em `docs/decisions.md` e aprovadas antes de alterar o comportamento de produção.

## Limitação de atraso

A fonte não associa uma OP específica a um pedido. Assim, `PRODUCTION_AFTER_PROMISE` compara a primeira conclusão de OP com a primeira promessa do SKU e deve ser interpretada como sinal de risco, não confirmação de atraso de atendimento.
