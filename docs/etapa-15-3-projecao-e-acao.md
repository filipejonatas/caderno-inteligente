# Etapa 15.3 — Projeção datada de estoque e motor de ação

Quarta subetapa do [plano da Etapa 15](plano-etapa-15-correcao-motor-decisao.md). Corrige o **G1**: a fila mostrava "Sem ação necessária" em 8 dos 10 primeiros SKUs, porque a conta de "próximo mês" descontava toda OP aberta sem olhar a data e ignorava os meses seguintes.

## 1. Como a ação é decidida agora

`src/caderno_inteligente/supply_plan.py` monta, para cada SKU, uma **projeção diária** de 14/09/2026 (data de planejamento, D3) até o fim do horizonte da previsão (28/02/2027). Depois a resume por semana.

**Demanda do dia:**
- pedidos da carteira na data prometida (os vencidos entram em 14/09);
- mais o que a previsão do mês tem além da carteira daquele mês, rateado pelos dias que ainda faltam no mês. É a mesma regra anti-dupla-contagem de antes, agora por mês e por dia.

**Reposição:** OPs abertas na `Conclusão prevista`.

**Estoque projetado:** estoque + reposições − demanda. Pode ficar negativo, e aí é falta.

**Peças do plano:**

| Peça | Regra |
|---|---|
| Chegada mais cedo de algo novo | data de planejamento + lead time do SKU |
| **Pedidos afetados** | carteira com prioridade sobre a previsão. O pedido é afetado se o estoque mais as entradas (OPs e ordens planejadas) só o cobrem depois da data prometida. Informa a data esperada e os dias de atraso |
| **Antecipar OP** | há falta (ou pedido atrasado) antes de uma OP que ainda **não começou** (Planejada/Liberada) e que, iniciada hoje com a mesma duração, chegaria a tempo. OP "Em produção" não é antecipada |
| **Ordem planejada** | na primeira data ≥ chegada mais cedo em que o estoque fica abaixo da segurança. Cobre a falta, a segurança e 4 semanas de demanda, **descontadas as OPs que já chegam nesse período**. Arredondada ao lote; liberação = necessidade − lead time; urgente se a liberação cai na janela de 4 semanas |
| **Reduzir OP (excesso)** | logo após a chegada, o estoque projetado passa de 90 dias de demanda futura + segurança. Reduz em lotes inteiros, sem criar falta nesses 90 dias |
| **Produto em descontinuação** | sem ordem nova e sem previsão: só a carteira confirmada conta. A OP é reduzida ao necessário para a carteira que o estoque não cobre (em lotes) ou cancelada |

**Ação principal** (precedência do plano, mantida pelo usuário):

| Ordem | Ação | Rótulo do PDF |
|---|---|---|
| 1 | Investigar dados (sem previsão) | Investigar |
| 2 | Antecipar OP | Priorizar produção |
| 3 | Falta inevitável: renegociar prazos e garantir a OP | Priorizar produção |
| 4 | Produzir (ordem urgente) | Priorizar produção / Produzir |
| 5 | Rever OP | Investigar |
| 6 | Produzir (ordem fora da janela; o rótulo diz "liberar a partir de dd/mm") | Produzir |
| 7 | Monitorar excesso | Monitorar |
| 8 | Sem ação necessária (só se o estoque fica acima da segurança no horizonte inteiro) | Sem ação necessária |

As outras ações que também valem ficam em `secondary_actions`.

**Regras novas** (pesos gravados na 15.0), emitidas a partir do plano:
- `PROJECTED_SHORTFALL` (9): falta ou pedido atrasado antes da chegada mais cedo;
- `OP_FOR_DISCONTINUED` (6);
- `PROJECTED_EXCESS` (5).

**Quantidade sugerida:** soma das ordens planejadas urgentes. A soma de todas fica em `planned_quantity_horizon`. A cascata (`calculation`) mostra a demanda até a chegada mais cedo + 4 semanas, a segurança, o estoque e as OPs que chegam a tempo.

## 2. Arquivos

- **`supply_plan.py`:** projeção, pedidos afetados, antecipação, excesso, descontinuação, ordens planejadas, resumo semanal e `decide`.
- **`recommendations.py`:** com plano, a ação, os rótulos, o porquê (`rationale`) e os campos do plano (`planned_orders`, `op_adjustments`, `affected_orders`, `projection`, `secondary_actions`…). Sem plano (casos sintéticos da validação), vale a conta antiga.
- **`rules.py`:** `evaluate_rules(indicators, thresholds, plans)`.
- **`action_labels.py`:** rótulos de `atraso_inevitavel`, `antecipar_op` e `rever_op`.
- **`backend/main.py`:**
  - planos calculados no pipeline, no mesmo cache (`supply_plans()`);
  - recomendação, cenários de pesos e validação usam o plano;
  - `/api/forecasts` ganhou `secondary_actions`, `planned_quantity_horizon` e `first_shortfall_date`;
  - o detalhe do SKU traz o plano completo.
- **`validation_center.py` e `backend/validation.py`:**
  - casos da base avaliados com o plano;
  - campos `affected_order_ids`, `op_adjusted_orders`, `op_anticipated_orders`, `challenge_code` e `secondary_actions`;
  - invariantes novas: falta projetada nunca "sem ação"; ordem planejada em lote inteiro.
- **Frontend:**
  - tipos das ações novas;
  - na fila, falta inevitável e antecipação marcam a linha como urgente e rever OP como revisar; filtro de ação ampliado;
  - no detalhe do SKU, o porquê lista as linhas do plano.

O bloco visual completo do plano (tabela semanal, ordens, ajustes) é da 15.6.

## 3. Decisões tomadas durante a subetapa

Pelo protocolo, os casos que falharam foram levados ao usuário, sem ajustar código nem expectativa para passar:

| Caso | O que aconteceu | Decisão do usuário |
|---|---|---|
| VC-03 (CI-0040, excesso) | Há excesso hoje (~200 dias), mas a projeção pede uma ordem em 14/01. Pela precedência, a principal é "Produzir (liberar a partir de 14/01)" | **Manter a precedência.** O VC-03 passou a verificar o excesso como sinal e como ação secundária |
| VC-22 (CI-0047, descontinuado) | O PED-047-1 atrasa 7 dias e a OP-7846 deve cair de 400 para 200. A principal é "Falta inevitável"; esperava-se "Rever OP" | **Manter a falta como principal.** O VC-22 espera falta, com "Rever OP" como secundária e a OP ajustada |
| VC-08 (CI-0014, capacidade) | Falta de 1 dia antes da reposição; esperava-se "Produzir após validar capacidade" | Mesma decisão. O VC-08 verifica "Produzir" como secundária e a capacidade em revisão |
| VC-04 (CI-0041) | Revisão prevista no plano | Passou a exigir ação ≠ "Sem ação necessária" |

**Ajustes de lógica feitos ao ver o primeiro resultado** (antes de rodar os casos), todos registrados aqui:

1. A ordem planejada passou a descontar as OPs que chegam na janela de cobertura. Antes, o CI-0048 recebia 1.000 un. novas para chegar 3 dias antes de uma OP de 2.000.
2. A antecipação passou a valer também para falta depois do lead time, quando uma OP existente pode chegar a tempo (CI-0033: pedido 2 dias antes da OP liberada).
3. Os pedidos afetados passaram a mostrar a data esperada já com as ordens planejadas.

## 4. Efeito na base

**Ações (50 SKUs):**

| Ação | 15.0 (início) | 15.2 | **15.3** |
|---|---|---|---|
| Sem ação necessária | 30 | 28 | **0** |
| Falta inevitável | — | — | 21 |
| Antecipar OP | — | — | 1 (CI-0033) |
| Produzir / validar capacidade | 14 | 17 | 23 |
| Rever OP | — | — | 5 (CI-0050, CI-0048, CI-0021, CI-0009, CI-0031) |
| Monitorar excesso | 6 | 5 | 0 (como secundária em CI-0038, CI-0040, CI-0022) |

**Top 10 da fila**, todos com ação:

| # | SKU | Ação | Sugerido agora |
|---|---|---|---|
| 1 | CI-0047 | Falta inevitável (+ rever OP-7846 de 400 para 200) | 0 |
| 2 | CI-0041 | Falta inevitável: PED-041-1 e PED-041-2 atrasam 22–24 dias | 800 |
| 3 | CI-0025 | Falta inevitável (PED-025-2, 4 dias) | 0 |
| 4 | CI-0050 | Rever OP: cancelar a OP-7849 (1.600), o estoque cobre a carteira | 0 |
| 5 | CI-0037 | Falta inevitável | 0 |
| 6 | CI-0049 | Falta inevitável | 600 |
| 7 | CI-0004 | Falta inevitável | 1.600 |
| 8 | CI-0002 | Falta inevitável (PED-002-1, 11 dias) | 0 |
| 9 | CI-0015 | Falta inevitável | 200 |
| 10 | CI-0017 | Falta inevitável | 200 |

**Quantidades e casos:**

- **Quantidade sugerida agora** (ordens urgentes): de 7.700 para **22.900 un.** O plano completo até fevereiro tem 175 ordens.
- **Ajustes de OP:** OP-7808 (CI-0009) 1.200 → 300; OP-7847 (CI-0048) 2.000 → 1.500; OP-7820 (CI-0021) → 300; OP-7830 (CI-0031) → 500.
- **Casos congelados:** 30 casos; **26 aprovados**, 4 pendentes (VC-24 a VC-26 na 15.5, VC-29 na 15.4), 0 reprovados. VC-20 a VC-23 liberados e aprovados.
- **Verificações de comportamento seguro:** 44 SKUs têm falta projetada no horizonte, e nenhum aparece como "Sem ação"; as 175 ordens planejadas estão em lote inteiro.

## 5. Testes

- **Python:** 457 aprovados (440 na 15.2). `tests/test_supply_plan.py` (17):
  - demanda sem dupla contagem e vencidos no primeiro dia;
  - pedidos afetados;
  - falta inevitável;
  - antecipação de OP não iniciada, e não de OP em produção;
  - descontinuado (cancelar e reduzir ao lote);
  - redução por excesso sem criar falta;
  - ordem que desconta OP na janela;
  - ordem futura não urgente com lote;
  - "sem ação" só com projeção acima da segurança;
  - contrato da recomendação;
  - previsão insuficiente;
  - regras do plano;
  - na base: topo sem "Sem ação", CI-0041 e as OPs de CI-0050/0047/0048/0009.
- **Frontend:** 361 Vitest (2 novos em `supply-plan.test.tsx`), 21 node e build OK.

**Expectativas alteradas:**

| Teste | Antes | Agora | Motivo |
|---|---|---|---|
| `test_action_labels` (vocabulário) | definição "próximo mês" | "ordem planejada no horizonte" | definição de Produzir mudou |
| `test_etapa15_protocolo` (pesos) | nenhuma regra nova | 3 regras do plano emitidas; capacidade e parceiro ainda não | 15.3 |
| `test_etapa15_protocolo` (pendentes) | 8 | 4 | VC-20 a VC-23 liberados |
| VC-03, VC-04, VC-08, VC-22 | ver seção 3 | ver seção 3 | precedência do plano |

**Verificado no navegador** (API própria na porta 8010, bancos copiados): fila com o topo urgente e sem "Sem ação"; detalhe do CI-0041 (falta, pedidos, ordem) e do CI-0050 (cancelar OP). Uma primeira carga da fila mostrou "Ação indisponível" porque o pedido foi abortado enquanto o servidor ainda subia; recarregada, respondeu em 50 ms. O pipeline frio leva 1,8 s e o plano, 0,1 s.

## 6. Limitações

- **Muitas faltas inevitáveis (21 SKUs).** Na base, o estoque costuma cobrir menos dias que o lead time, e parte da falta é de demanda prevista, sem pedido. O rótulo fala em renegociar prazos; quando não há pedido afetado, a ação real é priorizar a OP e a reposição.
- **Nenhum SKU fica "Sem ação".** Com 6 meses de horizonte, todo SKU precisa de alguma ordem até fevereiro. As que liberam fora da janela aparecem como "Produzir (liberar a partir de dd/mm)".
- **Pedido e OP não são vinculados na base.** A leitura de atraso dá prioridade à carteira sobre a previsão, mas não sabe a qual OP cada pedido pertence.
- **A data da falta é estimativa,** porque a previsão mensal é rateada por dia.
- **Capacidade ainda não limita nada:** "Validar capacidade" segue a regra de ocupação média até a 15.4.
- **Cenários de pesos** recalculam o ranking com o mesmo plano; o texto "2 dos 7 pesos" segue desatualizado até a 15.4.

## 7. Próximo passo

15.4 — capacidade semanal finita (G4). Ela libera o VC-29 e substitui `CAPACITY_CONFLICT` por `CAPACITY_SHORTFALL` (D4).

**Commit sugerido:** `feat(etapa-15.3): projeção semanal de estoque e ações coerentes com a fila`
