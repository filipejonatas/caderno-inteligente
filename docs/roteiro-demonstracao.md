# Roteiro de demonstração — 5 minutos

Roteiro para apresentar a V2 seguindo a ordem do plano:

1. problema e linha de base;
2. visão geral;
3. prioridade e recomendação operacional;
4. parceiro e recomendação comercial;
5. validação e comportamento seguro.

Os números citados são os da planilha de demonstração atual (SHA-256 `03fa0ed4…803f`). Se a planilha mudar, confira-os antes de apresentar.

## Antes de apresentar (10 minutos antes)

1. Rodar o smoke test contra a publicação. O resultado deve terminar com "verificações aprovadas" e código de saída 0.
   ```powershell
   .\.venv\Scripts\python.exe scripts\smoke_test.py --backend https://API --frontend https://APP --expect-environment production
   ```
2. Abrir as abas na ordem do roteiro:
   - `/validacao`
   - `/`
   - `/skus/CI-0041`
   - `/skus/CI-0014`
   - `/parceiros/KA-01?sku=CI-0011`
   - `/validacao` (segunda vez, para o fechamento)
3. Abrir cada aba uma vez para "aquecer" a API serverless; a primeira leitura da planilha é a mais lenta.
4. Se for registrar uma decisão ao vivo, a publicação precisa estar com `WRITE_ENABLED=true`. Depois da apresentação, limpe os dados de teste (veja [Deploy](deploy-vercel-supabase.md)).
5. **Plano B:** se a API cair, o Guia de uso (`/guia`) funciona sem a API e contém o fluxo e o roteiro resumido.

## 0:00–1:00 — Problema e linha de base

**Tela:** `/validacao`, aba "Processo atual" (já aberta), bloco "Comparação com o processo atual". O resumo, os 3 números e as falhas conhecidas ficam acima das abas.

- O PCP decide o que, quanto e quando produzir com dados fragmentados. A empresa informa:
  - 22 horas semanais de análise manual;
  - 89% de pedidos no prazo, com meta de 96%;
  - MAPE de 31% no forecast comercial;
  - 78% de aderência ao plano.
- A visibilidade do parceiro é parcial: só 20% dos pares parceiro–SKU têm sell-out registrado (50 de 250). Esse número aparece em `/` ("Detalhes"), em `/qualidade` e em `/parceiros`, não em `/validacao`.
- O protótipo separa o que a empresa **informou**, o que ele **recalculou** e a **meta**. O que a base não permite recalcular aparece como "não disponível", nunca como um número inventado.

## 1:00–2:00 — Visão geral

**Tela:** `/`.

- O primeiro da fila é o **CI-0041** (posição 1, 33 pontos). O motivo principal mostrado é o sinal de maior peso, "Abaixo do estoque de segurança"; os cinco sinais são:
  - abaixo da segurança;
  - abaixo do lead time;
  - produção após a promessa;
  - capacidade pressionada;
  - sem sell-out.
- 16 SKUs têm risco de ruptura (15 abaixo do lead time e 13 abaixo da segurança), há 12 pedidos sem OP e 20 SKUs priorizados têm confiança baixa por falta de sell-out.
- **Mensagem:** é uma **ordem de análise**, com motivos e evidências, não uma ordem de produção. A regra aparece uma vez, na linha amarela sob o título de toda página.

## 2:00–3:00 — Prioridade e recomendação operacional

**Telas:** clicar em "Abrir evidências de CI-0041" (`/skus/CI-0041`) e depois abrir `/skus/CI-0014`. A resposta (ação e quantidade) está no topo da página; o cálculo fica no bloco "Por que esta quantidade" e as evidências em "Riscos e evidências".

- **CI-0041:** apesar da prioridade #1, a recomendação é **"Sem ação necessária"**. Estoque e produção aberta já cobrem a demanda do próximo mês. O risco continua exigindo análise, e a tela diz isso explicitamente.
- **CI-0014:** a recomendação é **"Produzir após validar capacidade"**, com **400 unidades**.
  - Demanda a cobrir: 1.327 (o maior valor entre previsão de 1.246 e carteira de 1.327; os dois não são somados).
  - Mais segurança de 434, menos estoque de 1.490 e produção aberta de 0, resulta em necessidade de 271, arredondada ao lote mínimo de 400. A frase "Necessidade: … = 271 un.; arredondada ao lote mínimo" está no cartão de resposta.
  - A família está com capacidade pressionada, então a confiança cai para média e a revisão humana é obrigatória.
- **Mensagem:** cada número mostra fórmula, origem e limitação. Nenhuma sugestão libera uma OP.

## 3:00–4:00 — Parceiro e recomendação comercial

**Tela:** `/parceiros` (aba "Oportunidades": as 12 oportunidades de 5 parceiros em uma lista) → **Papelaria Horizonte (KA-01)** → `/parceiros/KA-01?sku=CI-0011`. Em cada linha, "Ver evidências" abre o detalhe mensal na própria linha.

- A recomendação comercial é por **parceiro e SKU** e usa só dados daquele parceiro.
- **CI-0011 na KA-01: "Avaliar reposição".**
  - Estoque estimado no parceiro: 132 unidades.
  - Sell-out médio: 151 por mês nos últimos 3 meses contínuos.
  - Cobertura de cerca de 26 dias, abaixo dos 30 configurados.
  - Abrir as evidências (a tabela mensal tem 3 colunas: mês, enviado e vendido).
- Nenhum estoque do CD, produção ou forecast global é distribuído entre parceiros. Canais sem sell-out (por exemplo, E-commerce próprio) aparecem como **"dados insuficientes"**, não como venda zero.

## 4:00–5:00 — Validação e auditoria

**Telas:** `/validacao`: resumo e falhas conhecidas no topo e a aba "Modelos de previsão"; depois, o botão "Auditoria completa" (`/auditoria`) para os casos de teste e as verificações de segurança.

- **Previsão:**
  - WAPE ponderado de 6,9% contra 8,0% da baseline ingênua;
  - o modelo **não superou a baseline em 16 de 50 SKUs**, e a tela mostra isso em vez de esconder.
- **Casos:** "8 de 8" no cartão (2 sintéticos, porque a base não tem esses exemplos); o detalhe de cada caso está na Auditoria. Os casos não ajustam pesos nem modelos.
- **Comportamento seguro:** a linha "Verificações de segurança: 7 de 7 passaram" fica em Falhas conhecidas; a lista completa está na Auditoria. As 7 verificações: Sem sell-out, a confiança cai; sem histórico, não há quantidade; capacidade exige revisão; dado ausente não vira zero.
- **Fechamento:** toda decisão é humana e fica registrada em **Decisões**, com o efeito do dado do parceiro e o tempo de análise. É essa medição que vai permitir comparar com as 22 horas semanais.

## Perguntas prováveis

| Pergunta | Resposta curta |
|---|---|
| Por que o primeiro da fila não precisa de produção? | Prioridade ordena a análise de risco; a quantidade vem da recomendação, que considera estoque e produção aberta |
| O WAPE de 6,9% é melhor que o MAPE de 31%? | Não dá para comparar: são métricas e previsões diferentes. A base não permite recalcular o forecast comercial |
| Por que a confiança é baixa em tantos SKUs? | Só 20% dos pares parceiro–SKU têm sell-out. O sistema assume a lacuna em vez de supor venda zero |
| Como explicar uma mudança no ranking? | Em Execuções, comparar duas execuções mostra sinais e pesos que mudaram e a decomposição do score |
| Os dados podem ser alterados por qualquer pessoa? | Em publicação aberta, use `WRITE_ENABLED=false`. Não há login no protótipo |
| O que falta para uso real? | Teste moderado com usuários, integração com dados reais, autenticação e limiares aprovados pela empresa |
