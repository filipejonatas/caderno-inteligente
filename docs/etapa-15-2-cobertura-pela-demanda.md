# Etapa 15.2 — Cobertura pela demanda de referência

Terceira subetapa do [plano da Etapa 15](plano-etapa-15-correcao-motor-decisao.md). Corrige o **G5**: a cobertura de estoque usava `Produtos.Venda média/dia`, um campo cadastrado que fica abaixo do vendido em boa parte dos SKUs. Isso superestimava a cobertura (escondia ruptura) nos SKUs que crescem e a subestimava (escondia excesso) nos que caem.

## 1. O que mudou

**Demanda diária de referência**, por SKU, com a fonte declarada em `demand_source`:

1. `previsao_3m`: média da previsão oficial (motor v2) dos 3 próximos meses (set–nov/26) ÷ 30,4 dias;
2. `vendas_3m`: média de `Vendas_24m` nos 3 últimos meses, se não houver previsão;
3. `cadastro`: `Produtos.Venda média/dia`, só como último recurso.

Na base, os 50 SKUs usam `previsao_3m`.

**Indicadores (`indicators.py`):**

- `coverage_days_calculated` mantém o nome (contrato) e passa a ser estoque ÷ demanda de referência.
- Campos novos:
  - `coverage_days_registered` (a conta antiga, para comparação);
  - `reference_daily_demand`, `demand_source`;
  - `registered_vs_reference_ratio` (demanda de referência ÷ cadastro);
  - `data_quality_warnings`.
- `build_sku_indicators(data, forecasts=None, settings=None)`: sem previsão, usa vendas e depois cadastro. Os dias por mês vêm de `config/supply_plan.json`.

**Demais arquivos:**

- **Regras (`rules.py`):** ruptura (lead time e estoque de segurança) e excesso usam a nova cobertura. `values_used` passa a trazer `daily_demand` e `demand_source`, e a origem diz "demanda de referência (previsão oficial dos 3 próximos meses)".
- **Quantidade (`recommendations.py`):** o estoque de segurança em unidades usa a demanda de referência (recua para o cadastro em entradas sem ela, como os casos sintéticos).
- **Aviso de qualidade:** `REGISTERED_DEMAND_DIVERGENCE` em `/api/data-quality` quando \|razão − 1\| > 0,20. O limite está em `config/rule_thresholds.json` → `registered_demand_divergence`, gravado no plano antes do código. A lista vem ordenada pela maior razão.
- **Pipeline (`backend/main.py`):** a previsão é calculada antes dos indicadores; o cache também invalida com `config/supply_plan.json`.

## 2. Decisão tomada durante a subetapa

O caso congelado **VC-03** ("Excesso de estoque", CI-0044, de antes da Etapa 15) falhou. Com a previsão de set–nov (que inclui a Black Friday), a cobertura do CI-0044 cai de 110 para **84,8 dias**, abaixo do limite de 90.

Pelo protocolo, nem caso nem limite foram ajustados para passar. As duas alternativas medidas foram levadas ao usuário:

| Demanda da cobertura | CI-0044 | CI-0014 | SKUs com aviso | VC-03 |
|---|---|---|---|---|
| **Previsão dos 3 próximos meses (plano)** | 84,8 dias | 30,5 dias | 32 | falha |
| Vendas dos 3 últimos meses | 98,8 dias | 36,3 dias | 9 | passa |

**O usuário manteve o desenho do plano.** O VC-03 passou a usar o **CI-0040** (~200 dias, demanda −32% a/a), com as mesmas expectativas. A troca está registrada no histórico de ajustes da validação, com o motivo e a alternativa recusada.

**Leitura dos 32 avisos:** parte da diferença não é erro do cadastro, e sim o pico de novembro dentro da janela de 3 meses (a previsão de set–nov é ~12% maior que a média de um trimestre comum). Medindo o cadastro contra as vendas recentes, seriam 9 SKUs. A dica do cartão e este documento dizem isso.

## 3. Efeito na base

**Cobertura e posição na fila:**

| SKU | Cobertura antes (cadastro) | Depois (demanda prevista) | Efeito |
|---|---|---|---|
| CI-0014 | 55,0 dias | **30,5 dias** | aviso de cadastro (×1,81); quantidade sugerida de 400 → 800 |
| CI-0004 | 30,0 dias | **15,0 dias** | entra em ruptura (abaixo do lead time de 21 e do estoque de segurança de 16); posição 28 → **8** |
| CI-0009 | 55,0 dias | **110,1 dias** | **entra na fila** (posição 41) por excesso |
| CI-0040 | 110,0 dias | 200,5 dias | continua excesso (novo VC-03) |
| CI-0044 | 110,0 dias | 84,8 dias | deixa de ser excesso |
| CI-0001 | 18,0 dias | 10,9 dias | **entra na fila** por ruptura |

**Totais** (comparação com o fim da 15.1):

| Indicador | Antes | Depois |
|---|---|---|
| SKUs na fila | 41 | **43** |
| SKUs com sinal de ruptura | 16 | **21** |
| Abaixo do lead time | 15 | 19 |
| Abaixo do estoque de segurança | 13 | 18 |
| Com excesso | 6 | 5 |
| Ações "Produzir" | 13 | 15 |
| "Sem ação necessária" | 29 | 28 |

**Mudanças de ação ou quantidade:**

- CI-0005 e CI-0019: de "sem ação" para produzir 500 e 300.
- CI-0004: produzir 800 → 1.000.
- CI-0018: produzir 500 → 1.000.
- CI-0045: produzir 300 → 600.
- CI-0009: de "sem ação" para "monitorar excesso".
- CI-0032 e CI-0044: de "monitorar excesso" para "sem ação".

**O topo da fila ainda tem 7 "Sem ação necessária"** (CI-0041, CI-0050 e outros). É o G1, corrigido na 15.3 pela projeção semanal datada.

**Casos congelados:** 30 casos; 22 aprovados, 8 pendentes, 0 reprovados. O VC-30 foi liberado e passa (cobertura de 30,5 ≤ 54; aviso presente).

## 4. Telas

- **Dados da planilha:** terceiro cartão na grade de métricas, "Venda média cadastrada · 32 SKUs · distantes da demanda prevista". O "?" explica que a cobertura usa a demanda prevista e lista as 5 maiores diferenças (CI-0004 ×2; CI-0005 ×1,95; CI-0014 ×1,81; CI-0026 ×1,71; CI-0001 ×1,65). Entrou como cartão, não como bloco novo, para respeitar o orçamento de volume da tela (2 blocos), sem afrouxá-lo.
- **Detalhe do SKU, aba Evidências:** quando há divergência, a cobertura aparece como "30 dias · cadastro: 55 dias".
- **Glossário:** "Cobertura" passa a ser "dias que o estoque dura no ritmo de venda previsto (3 próximos meses)".

Verificado no navegador (API própria na porta 8010, bancos copiados no scratchpad): Dados da planilha e detalhe do CI-0014, sem erros no console.

## 5. Testes

- **Python:** 440 aprovados (433 na 15.1). Novos em `tests/test_coverage_demand.py` (7):
  - fonte da previsão (só os 3 primeiros meses);
  - recuo para vendas sem inventar zero;
  - cadastro como último recurso;
  - aviso nos dois sentidos, ordenado;
  - regras com demanda e fonte;
  - estoque de segurança com recuo;
  - API (aviso e cobertura do CI-0014).
- **Frontend:** 359 Vitest (2 novos em `coverage.test.tsx`), 21 node e build OK. A fixture de qualidade ganhou o aviso, então o orçamento de volume e a acessibilidade de `/qualidade` passam a medir o cartão novo.

**Expectativas alteradas:**

| Teste | Antes | Agora | Motivo |
|---|---|---|---|
| `test_rules::test_thresholds_are_loaded_from_configuration` | 2 limiares | 3 (`registered_demand_divergence`) | limiar novo |
| `test_etapa15_protocolo` (pesos novos) | fila com 41 SKUs | sem contagem; só "nenhuma regra nova emitida" | a fila muda de propósito na 15.2 |
| `test_etapa15_protocolo` (pendentes) | 9 pendentes; liberados VC-27/28 | 8; liberados VC-27/28/30 | VC-30 liberado |
| VC-03 (`config/validation_center.json`) | CI-0044 | CI-0040 | decisão do usuário (seção 2) |

## 6. Limitações

- **A janela de 3 meses à frente inclui novembro.** Para SKUs com pico forte, a cobertura fica menor do que pelo ritmo de venda atual. É o comportamento pedido (cobertura olhando para frente), mas um estoque de "85 dias" não é excesso só porque a Black Friday vai consumi-lo.
- **O aviso de divergência mistura erro de cadastro e sazonalidade à frente** (32 SKUs; seriam 9 contra as vendas recentes).
- **A cobertura do campo `Produtos.Cobertura (dias)`** continua exposta como `coverage_days_source`, sem uso nas regras.
- **A quantidade ainda usa só o próximo mês;** a projeção completa é a 15.3.

## 7. Próximo passo

15.3 — projeção semanal de estoque e motor de ação (G1). Ela libera VC-20 a VC-23 e revê o VC-04.

**Commit sugerido:** `fix(etapa-15.2): cobertura pela demanda prevista e alerta de divergência do cadastro`
