# Roteiro de demonstração — 5 minutos

Roteiro da versão com o motor de decisão corrigido (Etapa 15). Ele responde à pergunta norteadora do desafio com quatro casos reais da base:

1. **CI-0041:** promessa sem cobertura → renegociar e priorizar;
2. **KA-02 · CI-0009:** estoque parado no parceiro → não repor e rever a OP-7808;
3. **CI-0050:** OP de produto em descontinuação → cancelar;
4. **Linha Escolar:** Volta às Aulas contra a capacidade → o que não cabe.

Os números são os da planilha de demonstração atual (SHA-256 `03fa0ed4…803f`), com a data de planejamento de 14/09/2026. Se a planilha mudar, confira-os antes de apresentar. O comparativo completo está em [docs/etapa-15/antes-depois.md](etapa-15/antes-depois.md).

## Antes de apresentar (10 minutos antes)

1. Rodar o smoke test contra a publicação. O resultado deve terminar com "verificações aprovadas" e código de saída 0.
   ```powershell
   .\.venv\Scripts\python.exe scripts\smoke_test.py --backend https://API --frontend https://APP --expect-environment production
   ```
2. Abrir as abas na ordem do roteiro e carregar cada uma uma vez, para "aquecer" a API serverless (a primeira leitura da planilha é a mais lenta):
   - `/fila`
   - `/skus/CI-0041?tab=evidencias`
   - `/parceiros/KA-02`
   - `/skus/CI-0009`
   - `/skus/CI-0050`
   - `/capacidade`
   - `/validacao`
3. Se for registrar uma decisão ao vivo, a publicação precisa estar com `WRITE_ENABLED=true`. Depois da apresentação, limpe os dados de teste (veja [Deploy](deploy-vercel-supabase.md)).
4. **Plano B:** se a API cair, o Guia de uso (`/guia`) funciona sem a API e contém o fluxo resumido.

## 0:00–0:45 — O problema em uma frase

**Tela:** `/fila`.

- O Caderno Inteligente vende para parceiros e vê o sell-in, mas só tem sell-out em 20% dos pares parceiro–SKU. O PCP precisa decidir **hoje** o que produzir, quanto e onde há risco.
- A fila ordena 43 SKUs por risco. **Nenhum dos 10 primeiros está "sem ação":** cada linha diz o que fazer e quanto, e o motivo diz quando a falta começa ("Falta a partir de 14/09").
- No total, 21 SKUs têm falta antes que qualquer reposição nova chegue e 22.900 un. precisam ser liberadas nas próximas 4 semanas.

## 0:45–1:45 — Caso 1: CI-0041, promessa sem cobertura

**Tela:** `/skus/CI-0041?tab=evidencias`, bloco "Plano de suprimento".

- **Pedidos sem cobertura:** 1.046 un. prometidas para 13 e 14/09 (PED-041-1 para KA-05 e PED-041-2 para KA-02), contra estoque de 132. A OP-7840 só conclui em 08/10.
- **Por que a falta é inevitável:** nem uma ordem liberada hoje chega antes de 05/10 (lead time de 21 dias). A ação é **renegociar os prazos e garantir a OP**, com uma ordem nova de 800 un. liberada já.
- **Cascata:** demanda até 02/11 de 1.824 + segurança de 202 − estoque de 132 − OPs no prazo de 1.200 = 694, arredondado ao lote de 400 → **800**.
- **A projeção semanal mostra onde falta;** a coluna Capacidade avisa que essa ordem **não cabe** na Linha Escolar.
- **Mensagem:** antes da correção, este SKU era o 1º da fila e aparecia como "Sem ação necessária". A conta olhava o mês inteiro e ignorava a data dos pedidos e da OP.

## 1:45–2:45 — Caso 2: KA-02 · CI-0009, estoque parado no parceiro

**Tela:** `/parceiros/KA-02` → CI-0009 → "Ver evidências"; depois `/skus/CI-0009`.

- **O que os números mostram:** em 6 meses, o KA-02 vendeu **59%** do que recebeu. O estoque estimado foi de **595 para 931 un.**, cerca de 355 dias de giro.
- **Não é erro de dado:** a conta "estoque anterior + recebido − vendido" fecha mês a mês, então é produto parado. Ação comercial: **não repor; acionar sell-out com o parceiro** (rótulo Investigar), com o selo "Estoque acumulando".
- **No SKU:** o CI-0009 entra na fila e a ação é **rever a OP-7808**, de 1.200 para 300 un. O motivo cita o KA-02 e a demanda em queda (cobertura de 110 dias pela previsão).
- **Mensagem:** é exatamente o exemplo do desafio: a venda para o parceiro parecia bom resultado, mas o produto está parado na loja. Só o sinal do parceiro sobe para o SKU; o estoque do CD não é distribuído.

## 2:45–3:30 — Caso 3: CI-0050, OP de produto saindo de linha

**Tela:** `/skus/CI-0050`.

- **A situação:** o produto está em descontinuação e tem a OP-7849 de **1.600 un.** liberada. O estoque (118) já cobre o único pedido em carteira (85).
- **Ação: Rever OP**, com a sugestão de cancelar a OP-7849. Produto saindo de linha não recebe ordem nova nem previsão; só a carteira confirmada conta.
- Há também o CI-0047 (2º da fila): a OP-7846 deve cair de 400 para 200 un. e o pedido PED-047-1 atrasa 7 dias.

## 3:30–4:15 — Caso 4: Linha Escolar e a Volta às Aulas

**Tela:** `/capacidade` (botão "Ver capacidade" na fila).

- **O que não cabe:** a previsão sazonal pede **20.800 un.** de Escolar nos picos, e a linha tem **12.960 un.** livres até o fim do calendário (03/01). **8.720 un. não cabem**, a primeira para 05/10.
- **Quem é afetado:** CI-0014, CI-0025 e CI-0041, com pedidos de KA-02, KA-05 e Marketplace.
- **O que decidir:** antecipar a produção, terceirizar ou repriorizar clientes. As premissas estão no "?" (capacidade livre já desconta compromissos e OPs existentes; sem calendário depois de dezembro).
- Clássico (540 un.) e Planner (1.520 un.) também têm faltas pequenas em outubro.

## 4:15–5:00 — Por que confiar

**Tela:** `/validacao`; aba "Modelos de previsão"; depois "Auditoria completa".

- **Previsão:**
  - erro médio de **8,0%**, contra 18,9% de repetir o último mês;
  - nos meses de pico, **7,9%** contra 26,8%;
  - o motor sazonal foi promovido porque atendeu aos quatro critérios fixados antes do teste;
  - novembro de 2026 previsto em 36,2 mil un. (o motor anterior previa 29,2 mil para um mês que vendeu 34,3 mil em 2025).
- **Casos de teste:** 30 de 30 aprovados. Os casos-alvo da correção (CI-0041, CI-0050, CI-0047, CI-0048, CI-0009, KA-02 · CI-0009, Escolar) foram gravados **antes** do código. As revisões de casos antigos estão no histórico de ajustes, com o motivo.
- **Comportamento seguro:** 9 verificações executadas, entre elas:
  - nenhuma falta projetada aparece como "sem ação";
  - toda ordem planejada respeita o lote mínimo;
  - dado ausente não vira zero.
- **Fechamento:** toda sugestão exige revisão humana. Nada cria, antecipa ou reduz OP sozinho, e a decisão fica registrada em Decisões.

## Perguntas prováveis

| Pergunta | Resposta curta |
|---|---|
| Por que tantas "faltas inevitáveis" (21)? | Na base, o estoque costuma durar menos que o lead time. A falta é projetada dia a dia; quando há pedido afetado, ele aparece com a data esperada |
| Por que nenhum SKU está "sem ação"? | O horizonte vai até fevereiro, e todo SKU precisa de alguma ordem até lá. As que não são para agora aparecem como "Produzir (liberar a partir de dd/mm)" |
| O WAPE de 8,0% é melhor que o MAPE de 31%? | Não dá para comparar: são métricas e previsões diferentes. A base não tem o realizado do forecast comercial |
| O pico de novembro foi testado? | Não diretamente: o modelo exige 15 meses de histórico, então o teste rolante cobre os picos de janeiro e fevereiro. Novembro é conferido por um caso congelado contra o realizado de 2025 |
| A falta de capacidade é exata? | Não: é um encaixe em ordem de necessidade, sem otimização, e não há capacidade informada depois de dezembro. Serve para decidir onde agir |
| O estoque do parceiro é real? | É estimado na planilha. A conta fechar mostra coerência entre as abas, não inventário físico; por isso o rótulo é "Investigar" |
| O que falta para uso real? | Teste com usuários, dados reais (vínculo pedido–OP, capacidade além de dezembro), autenticação e limiares aprovados pela empresa |
