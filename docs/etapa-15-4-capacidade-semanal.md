# Etapa 15.4 — Capacidade semanal finita

Quinta subetapa do [plano da Etapa 15](plano-etapa-15-correcao-motor-decisao.md). Corrige o **G4**: a capacidade era só um selo de ocupação média acima de 90%, presente nas 6 famílias de Escolar sem dizer o que não cabia. Agora responde à pergunta do PDF "onde uma oportunidade não pode ser executada por restrição operacional", com quantidades, semanas, SKUs e pedidos.

## 1. Como funciona

`src/caderno_inteligente/capacity_plan.py` encaixa as **ordens planejadas da 15.3** na `Capacidade disponível` de `Capacidade_Semanal`, por família (linha) e semana:

1. **Ordem de atendimento:** data de necessidade; empate por curva ABC e depois por SKU.
2. **Semana de liberação primeiro:** a ordem consome capacidade na semana de liberação (início), como a coluna "Ordens planejadas" da base.
3. **Pré-produção:** se faltar capacidade na semana de liberação, a ordem antecipa semana a semana até a data de planejamento.
4. **Situação de cada ordem:**
   - `ok`: cabe na própria semana;
   - `pre_producao`: precisou antecipar;
   - `insuficiente`: sobra quantidade sem programação, e nunca é jogada para depois da necessidade;
   - `a_confirmar`: começaria depois do fim do calendário (28/12/2026 + 6 dias), onde não há capacidade informada.

**Premissas declaradas na tela** (o "?" de "Por linha"):
- `Capacidade disponível` já desconta compromissos base e OPs existentes;
- unidades homogêneas por família;
- "compromissos base" não foram validados com a empresa;
- não há calendário depois de dezembro;
- antecipar ou reduzir OP não libera nem consome capacidade nesta conta (conservador).

**Regra nova (decisão D4):**
- `CAPACITY_SHORTFALL` (peso 7, gravado na 15.0) entra quando alguma ordem planejada do SKU fica `insuficiente`.
- `CAPACITY_CONFLICT` (ocupação média) saiu, com seu peso e o limiar `capacity_occupation_threshold`. A ocupação média continua nos indicadores como contexto.

**Efeito na recomendação:**
- `capacity_status = requires_review` quando há `CAPACITY_SHORTFALL`;
- "Produzir" vira "Produzir após validar capacidade";
- a confiança "alta" cai para "média";
- o porquê ganha a linha "Capacidade: a linha X não comporta N un. para dd/mm…";
- o campo `capacity` traz o status de cada ordem.

## 2. Arquivos

- **Novos:**
  - `src/caderno_inteligente/capacity_plan.py`;
  - `frontend/src/pages/CapacityPage.tsx`;
  - `tests/test_capacity_plan.py`;
  - `frontend/src/test/capacity.test.tsx`.
- **`backend/main.py`:**
  - capacidade calculada no pipeline, no mesmo cache (`capacity_plan()`);
  - `GET /api/capacity-plan` (novo);
  - `/api/capacity/{family}` ganhou `allocated` e `remaining` por semana;
  - limite de cenários sem o limiar de ocupação;
  - texto de limitação do detalhe do SKU atualizado.
- **`rules.py`, `recommendations.py` e `validation_center.py`:**
  - regra nova e efeito na recomendação;
  - caso do tipo `capacity_family`, verificação `in` e checagem "falta de capacidade exige revisão".
- **Configuração:** `prioritization_weights.json` sem `CAPACITY_CONFLICT`; `rule_thresholds.json` sem `capacity_occupation_threshold`.
- **Frontend:**
  - rota `/capacidade` no grupo Planejamento, aberta pelo botão **"Ver capacidade"** da fila, como "Simular pesos";
  - Cenários simula "Não cabe na capacidade", e o título conta os pesos dinamicamente ("2 dos 11");
  - nomes das regras novas da 15.3/15.4 nos motivos;
  - tipos, cliente da API, fixture, contrato e orçamento de volume da rota nova.

**Desvio de implementação:** a primeira versão deu ao Planejamento abas "Fila | Capacidade". Um teste da navegação congela que a fila não tem abas (decisão do redesign), então troquei por um botão, sem mexer nessa decisão.

**Orçamento de volume `/capacidade`** (D6): palavras 120, palavras por linha 8, números 10, blocos 5, colunas 5, avisos 0. Medido com a fixture: 69 palavras, 2 por linha, 1 número, 4 blocos e 5 colunas.

## 3. Efeito na base

| Família (linha) | Livre até 03/01 | Encaixado | Sem programação | Situação | Pico (nov, jan, fev) |
|---|---|---|---|---|---|
| **Escolar** | 12.960 | 11.680 | **8.720** | **Não cabe** (primeira falta: 05/10) | **20.800 un. necessárias; não cabe** |
| Clássico | 39.240 | 24.060 | 540 | Não cabe (02/10) | cabe no calendário; depois, a confirmar |
| Planner | 22.560 | 13.680 | 1.520 | Não cabe (06/10) | cabe no calendário; depois, a confirmar |
| Acessórios | 122.000 | 27.300 | 0 | cabe no calendário; depois, a confirmar | idem |
| Executivo | 23.940 | 2.800 | 0 | idem | idem |
| Refis | 136.500 | 18.500 | 0 | idem | idem |

- **Escolar:** CI-0014, CI-0025 e CI-0041 não cabem. As ordens de 05/10 (liberação em 14/09) e as de janeiro (Volta às Aulas) ficam sem programação, porque as semanas de novembro e dezembro já foram usadas pelas necessidades anteriores. Pedidos afetados: PED-014-1/2 (KA-02), PED-025-1/2 (Marketplace), PED-041-1/2 (KA-05, KA-02).
- **Clássico:** CI-0036 (PED-036-1 KA-02, PED-036-2 E-commerce).
- **Planner:** CI-0017 (PED-017-1 KA-05) e CI-0042 (PED-042-1 KA-04).

**Na fila:**
- `CAPACITY_SHORTFALL` em 6 SKUs (CI-0041, CI-0025, CI-0014, CI-0017, CI-0042, CI-0036), em vez dos 6 de Escolar marcados pela ocupação média (que incluíam CI-0050, CI-0016 e CI-0039 sem falta real).
- Ações: CI-0042 e CI-0036 passam a "Produzir após validar capacidade"; CI-0039 volta a "Produzir".
- Topo da fila: CI-0041 em 1º, seguido de CI-0047, CI-0017, CI-0025…; todos com ação.

**Casos congelados:** 30 casos; **27 aprovados**, 3 pendentes (VC-24 a VC-26, da 15.5), 0 reprovados.
- **VC-29 liberado e aprovado:** pico de Escolar "insuficiente", 20.800 un. necessárias, 12.960 livres.
- **VC-08 revisto (D4):** espera `CAPACITY_SHORTFALL` e não `CAPACITY_CONFLICT`. Registrado no histórico de ajustes com `changed_weights_or_models: true`.

## 4. Testes

- **Python:** 466 aprovados (457 na 15.3). Novos em `tests/test_capacity_plan.py` (8):
  - cabe na semana;
  - pré-produção;
  - sem programação, nunca depois da necessidade;
  - fora do calendário fica a confirmar;
  - necessidade mais cedo primeiro e alocado ≤ disponível;
  - resumo da família (SKUs, pedidos, pico);
  - na base: Escolar não absorve a Volta às Aulas;
  - a regra nova substitui a antiga.
- **Frontend:** 365 Vitest (2 novos: página e acesso pela fila), 21 node e build OK. `/capacidade` passa no orçamento de volume e no teste de rotas.

**Expectativas alteradas:**

| Teste | Antes | Agora | Motivo |
|---|---|---|---|
| `test_rules::test_applies_all_*` | 7 regras com `CAPACITY_CONFLICT` | 6 regras dos indicadores; capacidade vem do plano | D4 |
| `test_rules::test_thresholds_*` | com `capacity_occupation_threshold` | sem | D4 |
| `test_etapa15_protocolo` (regras/pendentes) | 4 pendentes; capacidade não emitida | 3; `CAPACITY_SHORTFALL` emitida e `CAPACITY_CONFLICT` não | 15.4 |
| `test_frontend_contracts` | sem `/api/capacity-plan` | com | endpoint novo |
| VC-08 | `CAPACITY_CONFLICT` | `CAPACITY_SHORTFALL` | D4 |

**Verificado no navegador** (API própria na porta 8010, bancos copiados): `/capacidade` com as 6 famílias, as faltas e as semanas por linha, menu Planejamento ativo; botão "Ver capacidade" na fila; sem erros no console.

## 5. Limitações

- **Sem calendário depois de 28/12:** as ordens de janeiro e fevereiro que começam depois ficam "a confirmar". O conflito de Escolar aparece porque parte da Volta às Aulas precisa começar em dezembro.
- **Alocação gulosa por data de necessidade,** sem otimização: pode haver outra ordem de encaixe que programe mais. A falta mostrada é um alerta, não um limite exato.
- **Antecipar e reduzir OP não mexem na capacidade:** reduzir as OPs de CI-0009 e CI-0048 liberaria capacidade em Acessórios e Refis, que não têm falta.
- **A quantidade sugerida não é cortada pela capacidade:** o que não cabe aparece como "sem programação" e exige decisão (antecipar, terceirizar, repriorizar clientes). Priorizar parceiros para o produto escasso (G8) fica fora da Etapa 15.

## 6. Próximo passo

15.5 — estoque acumulando no parceiro (G2). Ela libera VC-24 a VC-26.

**Commit sugerido:** `feat(etapa-15.4): plano de capacidade semanal finita e viabilidade por família`
