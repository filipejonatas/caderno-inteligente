# Etapa 15.5 — Estoque acumulando no parceiro

Sexta subetapa do [plano da Etapa 15](plano-etapa-15-correcao-motor-decisao.md). Corrige o **G2**: o caso que abre o PDF ("uma venda para um parceiro pode parecer um bom resultado comercial, mas o produto pode estar parado no estoque da loja") não era detectado. KA-02 · CI-0009 aparecia como "investigar divergência", como se fosse erro de registro. A regra de excesso exigia giro ≤ 30 un./mês e não pegava nenhum caso real.

## 1. O que mudou

### Janela de acúmulo por par parceiro–SKU (`partner_insights.py`)

Os últimos 6 meses (`buildup_months`, gravado na 15.0) dão:
- `sell_in_window` e `sell_out_window`;
- `sell_through_window` = vendido ÷ enviado;
- `stock_start` (estoque no mês anterior à janela) e `stock_growth`;
- `stock_identity_consistent`: a conta estoque(t) = estoque(t−1) + sell-in(t) − sell-out(t) fecha em todos os meses, com tolerância de 1 un.

### Sinais

| Sinal | Quando | Ação comercial | Rótulo do PDF (D5) |
|---|---|---|---|
| `PARTNER_STOCK_BUILDUP` | dados suficientes e atuais; estoque ≥ 100 e cobertura ≥ 90 dias (ou sem giro); sell-through ≤ 0,90; estoque cresceu ≥ 30% | **Não repor; acionar sell-out com o parceiro** (`conter_reposicao`) | Investigar |
| `PARTNER_EXCESS_RISK` | estoque alto como acima, **sem** acúmulo. A trava "giro ≤ 30 un./mês" saiu | **Monitorar estoque alto no parceiro** (`monitorar_excesso_parceiro`) | Monitorar |
| `SELLIN_SELLOUT_DIVERGENCE` | o critério de antes, **só quando a conta de estoque não fecha** (ou não pode ser conferida) | Investigar divergência | Investigar |

**Precedência comercial:** dado antigo > dado insuficiente > divergência > **acúmulo** > reposição > **excesso estável** > monitorar.

O limiar `low_monthly_sell_out` saiu da configuração, do validador e do bloco "Método" da tela.

### Ligação com o SKU e a OP

- `supply_plan.attach_partner_buildup`: o SKU com acúmulo em algum parceiro ganha o sinal `PARTNER_STOCK_BUILDUP` (regra SKU, peso 6 gravado na 15.0) e o campo `partner_buildup` (parceiro, sell-through, estoque inicial → final, cobertura).
- Se o SKU tem OP a reduzir, o motivo do ajuste cita o parceiro.
- O estoque do CD **nunca** é distribuído entre parceiros: só o sinal do parceiro sobe para o SKU.
- As percepções comerciais passam a ser calculadas também no pipeline (antes só nas rotas comerciais), sem mudar as rotas.

### Validação, tela e textos

- **Validação:** os casos comerciais expõem `challenge_code`. VC-24, VC-25 e VC-26 foram liberados.
- **Matriz parceiro–SKU:**
  - selo **"Estoque acumulando"** na linha (tabela e cartão);
  - a evidência mostra "Vendido ÷ enviado: 59% · 6 meses · estoque 595 → 931";
  - a origem mensal ganhou a coluna **Estoque estimado**;
  - "Não repor" entra entre as linhas que pedem ação no detalhe do parceiro.
- **Textos polidos após a verificação no navegador:**
  - a evidência do rótulo mostrava "0,6" e "true"; agora mostra "59%" e "sim";
  - os motivos de ajuste de OP e de antecipação usavam datas ISO; agora usam dd/mm (os campos estruturados continuam ISO).

## 2. Efeito na base

**Pares parceiro–SKU (95):**

| Ação | Antes (15.4) | Depois |
|---|---|---|
| Avaliar reposição | 12 | 12 |
| Monitorar estoque | 37 | 27 |
| **Monitorar estoque alto** | — | **10** |
| **Não repor; acionar sell-out** | — | **1** (KA-02 · CI-0009) |
| Investigar divergência | 1 (KA-02 · CI-0009) | 0 |
| Dados insuficientes | 45 | 45 |

- **KA-02 · CI-0009:** vendeu 59% do que recebeu em 6 meses, estoque de 595 → 931 un. (355 dias de giro). A conta de estoque fecha em todos os meses (como nos 50 pares com sell-out da base): é produto parado, não erro de registro.
- **KA-03 · CI-0001:** cobertura de ~297 dias, mas o estoque cresceu só 12% em 6 meses. Fica como **estoque alto estável** (VC-26 aceita qualquer dos dois sinais).
- **Outros 9 pares com estoque alto estável:**
  - KA-01: CI-0002, CI-0005, CI-0020;
  - KA-02: CI-0018;
  - KA-03: CI-0004, CI-0016;
  - KA-04: CI-0002;
  - KA-05: CI-0003, CI-0018.
- **CI-0009 na fila:** sobe da posição 39 para a **29**, com `PARTNER_STOCK_BUILDUP` + `PROJECTED_EXCESS` e ação "Rever OP". A OP-7808 cai de 1.200 para 300, e o motivo cita o KA-02.
- **Casos congelados: 30 de 30 aprovados, nenhum pendente.** A Etapa 15 não tem mais casos esperando código.

## 3. Testes

- **Python:** 472 aprovados (466 na 15.4). `tests/test_partner_buildup.py` (6):
  - acúmulo não é divergência quando a conta fecha;
  - divergência quando a conta não fecha;
  - excesso estável sem a trava de giro;
  - reposição saudável intacta;
  - ligação com o SKU e o motivo da OP;
  - KA-02 · CI-0009 e CI-0009 na base real.
- **Frontend:** 366 Vitest (1 novo em `partner-buildup.test.tsx`: selo, evidência e coluna de estoque), 21 node e build OK. Uma rodada intermediária teve uma falha intermitente em `routes.test` (comparação de execuções); isolado e na rodada seguinte, passou.

**Expectativas alteradas:**

| Teste | Antes | Agora | Motivo |
|---|---|---|---|
| `test_partner_insights::test_excess_signal_for_low_or_zero_turnover` | ação `monitorar_estoque` | `monitorar_excesso_parceiro` | o excesso ganhou ação própria |
| `test_etapa15_protocolo` (regras) | `PARTNER_STOCK_BUILDUP` não emitida | emitida | 15.5 |
| `test_etapa15_protocolo` (pendentes) | 3 pendentes na base | 0 na base; o comportamento de "pendente" passa a ser testado com um caso marcado em memória | fim dos pendentes |

**Verificado no navegador** (API própria na porta 8010, bancos copiados):
- matriz do KA-02 com "Não repor; acionar sell-out", selo "Estoque acumulando" e rótulo Investigar;
- evidência com 59%, estoque 595 → 931 e a coluna de estoque mês a mês;
- detalhe do CI-0009 em 29º, com "Rever OP" e o motivo citando o KA-02.

Sem erros no console.

## 4. Limitações

- **O estoque do parceiro é estimado na fonte.** A conta fechar mostra coerência entre as abas, não confirma o estoque físico; o rótulo é "Investigar".
- **Visibilidade de 20% dos pares:** só 10 SKUs por parceiro têm sell-out. Nos outros 45 pares com carteira, nada é inferido.
- **Os limiares de acúmulo** (sell-through ≤ 0,90, crescimento ≥ 30%) foram gravados antes do código, mas são demonstrativos: não foram validados com a empresa.
- **O sinal do parceiro pesa no ranking do SKU,** mas não muda a quantidade planejada: a redução da OP vem do excesso projetado (15.3); o parceiro entra como evidência.

## 5. Próximo passo

15.6 — telas, validação, documentação e roteiro (bloco "Plano" no detalhe do SKU, comparação antes × depois em `docs/etapa-15/`, atualização de `calculations.md`, `rules.md`, `commercial-rules.md`, `decisions.md`, README e roteiro de demonstração).

**Commit sugerido:** `feat(etapa-15.5): estoque acumulando no parceiro e ligação com a OP do SKU`
