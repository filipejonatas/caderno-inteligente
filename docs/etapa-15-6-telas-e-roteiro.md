# Etapa 15.6 — Telas, validação, documentação e roteiro

Última subetapa do [plano da Etapa 15](plano-etapa-15-correcao-motor-decisao.md). Fecha a correção do motor de decisão (G1–G5): o plano datado aparece nas telas, a comparação antes × depois fica registrada e a documentação e o roteiro de demonstração passam a descrever o motor novo.

## 1. Telas

**Detalhe do SKU › Evidências › "Plano de suprimento"** (`frontend/src/components/SupplyPlan.tsx`):
- **cascata:** "Até 02/11: demanda 1.824 + segurança 202 − estoque 132 − OPs no prazo 1.200 = 694 un." e a data em que uma reposição nova pode chegar;
- **pedidos afetados:** cliente, quantidade, data prometida e quando o pedido é atendido;
- **ajustes de OP:** antecipar (com a nova data), reduzir ou cancelar (de → para);
- **ordens planejadas:** liberar até, chegada, quantidade e situação na capacidade (cabe, pré-produção, a confirmar, não cabe);
- **projeção semanal:** 8 semanas visíveis e "Ver as demais N semanas". A marca "falta" segue a projeção exibida (com as ordens planejadas). O campo `shortfall_with_plan` foi criado para isso; o `shortfall`, sem as ordens, continua sendo o usado pelas regras e verificações.
- **link para `/capacidade`** quando alguma ordem não cabe.

**Detalhe do SKU › Resumo:** a linha de capacidade diz quantas unidades não cabem e leva a "Ver capacidade". Uma linha aponta o plano em Evidências.

**Fila:**
- o motivo principal vira "Falta a partir de dd/mm" quando a ação é falta inevitável ou antecipar OP (vem da projeção, não da regra de cobertura);
- a quantidade mostra no `title` o total planejado no horizonte.

**Guia:** a pergunta "Um SKU com prioridade alta precisa ser produzido?" agora diz que a ação vem do plano datado. A primeira versão do texto passou o orçamento da tela (510 palavras para 500); a resposta foi encurtada, sem mexer no orçamento.

**Já entregues nas subetapas anteriores:** `/capacidade` (15.4), selo "Estoque acumulando" na matriz (15.5), manchete normal × pico na Validação (15.1), cartão de cadastro divergente em Dados da planilha (15.2).

## 2. Antes × depois

`scripts/snapshot_decisions.py` ganhou:
- `--comparar ANTES DEPOIS`, que gera o resumo em Markdown;
- o campo `capacity` no snapshot.

| Arquivo | O que é |
|---|---|
| [docs/etapa-15/antes.json](etapa-15/antes.json) | estado no início da 15.0 |
| [docs/etapa-15/depois.json](etapa-15/depois.json) | estado no fim da 15.6 |
| [docs/etapa-15/antes-depois.md](etapa-15/antes-depois.md) | comparação gerada (há teste que confere que o arquivo bate com os dois JSON) |

**Destaques:**

| | Antes | Depois |
|---|---|---|
| "Sem ação necessária" | 30 SKUs (8 no top 10) | 0 |
| Falta inevitável / antecipar OP / rever OP | — | 21 / 1 / 5 |
| Previsão de nov/26 | 29.235 un. | 36.203 un. |
| Quantidade a liberar agora | 7.700 un. | 22.900 un. |
| CI-0041 (1º da fila) | sem ação | falta inevitável; PED-041-1/2 atrasam 22–24 dias; ordem de 800 un. |
| CI-0050 | sem ação | rever OP: cancelar a OP-7849 (1.600 un.) |
| CI-0009 | fora da fila | 29º; rever a OP-7808 (1.200 → 300); acúmulo no KA-02 |
| KA-02 · CI-0009 | investigar divergência | não repor; acionar sell-out |
| Linha Escolar | selo de ocupação | 8.720 un. não cabem; pico de 20.800 un. não cabe |
| Casos congelados | 20 aprovados, 10 pendentes | 30 de 30 aprovados |

## 3. Documentação

- **`calculations.md`:**
  - demanda de referência e cobertura;
  - previsão v2 e o protocolo de pico;
  - faturamento em 3 e 6 meses;
  - eventos sem dupla contagem;
  - plano de suprimento e a precedência das ações;
  - capacidade semanal;
  - janela de acúmulo;
  - validação rolante e casos pendentes.
- **`rules.md`:** regras dos indicadores e as 5 regras do plano; `CAPACITY_CONFLICT` registrada como substituída; limites e cenários atualizados.
- **`prioritization.md`:** os 11 pesos e o exemplo do CI-0041 (antes "sem ação", agora falta inevitável).
- **`commercial-rules.md`:** janela de acúmulo, conta de estoque, sinais e as 7 ações; `low_monthly_sell_out` registrado como removido.
- **`decisions.md`:** registro da Etapa 15 (D1–D6, protocolo e as duas decisões tomadas durante a execução).
- **`api.md`:** `/api/capacity-plan`, campos novos de `/api/forecasts` e `/api/priorities/{sku}`, ações possíveis.
- **`README.md`:** perguntas que o protótipo responde (quando produzir, onde não cabe, estoque parado), rota `/capacidade`, configurações e índice da Etapa 15.
- **`roteiro-demonstracao.md`:** reescrito em 5 minutos, em torno dos quatro casos:
  1. CI-0041 (promessa sem cobertura);
  2. KA-02 · CI-0009 (estoque parado);
  3. CI-0050 (OP de produto saindo de linha);
  4. Linha Escolar (Volta às Aulas × capacidade);
  
  e o bloco "por que confiar".

## 4. Testes

- **Python:** 473 aprovados (472 na 15.5); novo teste confere que `antes-depois.md` é a comparação de `antes.json` e `depois.json`.
- **Frontend:** 368 Vitest (2 novos em `supply-plan.test.tsx`: bloco do plano e motivo da fila), 21 node e build OK; orçamento de volume do detalhe do SKU e do Guia respeitado.

**Verificado no navegador** (API própria na porta 8010, bancos copiados):
- bloco "Plano de suprimento" do CI-0041 (cascata, pedidos, ordens com capacidade, projeção);
- fila com "Falta a partir de dd/mm".

Sem erros no console.

## 5. Pendências fora do código

- **Deploy e smoke test** com o motor novo (`scripts/smoke_test.py`); o roteiro lista as abas para aquecer a API.
- **Teste moderado com usuários** (protocolo no relatório da Semana 4), ainda não realizado.
- **Migração 003 do Supabase:** confirmar que foi aplicada; a Etapa 15 não exigiu migração nova (`action` é texto livre).
- **Fora da Etapa 15:**
  - tendência ano contra ano;
  - alocação de produto escasso entre parceiros e regiões;
  - reconciliação Sell_In × Vendas_24m;
  - recalibração das faixas P10–P90;
  - capacidade além de dezembro;
  - vínculo pedido–OP (depende de dados da empresa).

**Commit sugerido:** `feat(etapa-15.6): telas, validação e roteiro com o motor de decisão corrigido`
