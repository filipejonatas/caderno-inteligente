# Plano de evolução do protótipo

> Para a execução rápida do hackathon, use o recorte timeboxed em `docs/plano-hackathon-para-ia.md`. Este documento permanece como referência de evolução posterior do produto.

## 1. Objetivo

Evoluir o Caderno Inteligente de um ranking explicável por SKU para um protótipo que apoie a análise de:

- qual SKU precisa de atenção;
- para qual canal ou parceiro existe evidência disponível;
- em qual período a necessidade ocorre;
- qual quantidade deve ser analisada;
- quais dados sustentam a análise;
- qual é o nível de confiança;
- como a decisão humana foi registrada;
- se os dados do parceiro alteraram ou reforçaram a decisão.

O protótipo continuará sem liberar ordens de produção, prometer viabilidade individual ou substituir o PCP.

## 2. Princípios de implementação

1. **Não inventar granularidade.** Dados agregados por SKU ou família não serão distribuídos artificialmente entre parceiros, canais ou semanas.
2. **Separar fato, cálculo e decisão.** Dados observados, estimados, previstos e ausentes devem permanecer identificáveis.
3. **Preservar as regras atuais.** As sete regras existentes continuam como linha de base e recebem testes de regressão.
4. **Explicar cada resultado.** Toda prioridade deve apresentar fórmula, valores utilizados, origem, limitação e confiança.
5. **Tratar quantidade como apoio à análise.** A quantidade calculada não será chamada de ordem recomendada ou quantidade ótima.
6. **Instrumentar antes de adicionar IA.** IA só será avaliada após existir histórico de decisões e uma comparação determinística.

## 3. Arquitetura de dados proposta

Evitar uma única tabela cartesiana. O domínio deve ser separado em três visões relacionadas:

### 3.1 Visão global por SKU

- SKU, produto, família e curva ABC;
- estoque no centro de distribuição;
- cobertura, segurança e lead time;
- carteira total e produção aberta;
- forecast e histórico total;
- primeira promessa e primeira conclusão prevista;
- sinais que independem de parceiro.

### 3.2 Visão por SKU e canal ou parceiro

- SKU;
- canal ou parceiro;
- período de referência;
- sell-in observado;
- sell-out observado;
- estoque estimado do parceiro, quando disponível;
- cobertura e atualidade do dado;
- nível de colaboração;
- confiança e campos ausentes.

Quando a fonte não permitir relacionar um pedido ou estoque a um parceiro, o campo permanecerá como `não disponível` e o cálculo continuará no nível global do SKU.

### 3.3 Visão de capacidade por família e semana

- família;
- linha;
- semana;
- capacidade máxima, comprometida e disponível;
- ocupação;
- limitação explícita de que não existe alocação individual por SKU.

### 3.4 Candidato de decisão

Uma camada final reunirá referências para as visões anteriores:

```text
sku
canal_ou_parceiro opcional
periodo
data_de_necessidade
quantidade_para_analise
sinais
score
confianca
evidencias
limitacoes
dados_ausentes
```

## 4. Fases de implementação

### Fase 0 — Correções semânticas e linha de base

**Estimativa:** 1 dia

#### Backend

- Separar `rupture_signal_count` de `rupture_sku_count`.
- Contar SKUs únicos em risco sem somar duas regras do mesmo SKU como dois produtos.
- Expor separadamente:
  - cobertura abaixo do lead time;
  - cobertura abaixo da segurança;
  - SKUs únicos com algum risco de ruptura.
- Registrar no snapshot as métricas atuais para comparação futura.

#### Frontend

- Renomear o card atual para `SKUs com risco de ruptura`.
- Mostrar a decomposição dos sinais no detalhe ou tooltip.
- Revisar todas as métricas para distinguir SKUs, ocorrências e parceiros.

#### Critérios de aceite

- Nenhum indicador visual mistura quantidade de regras com quantidade de SKUs.
- Os valores 15, 13 e o total único podem ser reconciliados com a base.
- Testes cobrem SKUs que acionam as duas regras simultaneamente.

### Fase 1 — Granularidade por canal parceiro e período

**Estimativa:** 4 a 6 dias

#### Núcleo Python

- Criar funções independentes:
  - `build_sku_view`;
  - `build_sku_channel_view`;
  - `build_family_week_capacity_view`;
  - `build_decision_candidates`.
- Preservar as chaves originais e validar unicidade antes de cada agregação.
- Adicionar período de referência explícito a sell-in, sell-out, forecast, capacidade e eventos.
- Classificar cada campo como observado, estimado, previsto ou ausente.
- Gerar relatório de cobertura por parceiro, SKU e período.

#### API

- Criar rotas:
  - `GET /api/decision-candidates`;
  - `GET /api/channels`;
  - `GET /api/partners/{partner}/visibility`;
  - `GET /api/skus/{sku}/timeline`.
- Manter `/api/priorities` temporariamente para compatibilidade.

#### Frontend

- Adicionar filtros de canal, parceiro e período.
- Exibir o nível real da análise: global do SKU ou específico do parceiro.
- Mostrar `não disponível` quando não houver vínculo suportado pela fonte.

#### Critérios de aceite

- Um dado agregado nunca é duplicado pela quantidade de parceiros.
- É possível rastrear cada valor até a linha e a granularidade da fonte.
- A interface distingue claramente análise global e análise por parceiro.

### Fase 2 — Data de necessidade e quantidade para análise

**Estimativa:** 3 a 5 dias

#### Data de necessidade

Calcular candidatos, mantendo a origem de cada data:

- primeira data prometida da carteira;
- data estimada de ruptura pela cobertura;
- início de evento relevante;
- período do forecast;
- primeira conclusão de produção.

A data crítica será a menor data válida aplicável ao contexto. Datas não comparáveis ou sem vínculo permanecerão separadas.

#### Quantidade para análise

Implementar uma fórmula transparente e configurável:

```text
necessidade_bruta = carteira_no_horizonte
                  + forecast_no_horizonte
                  + estoque_de_seguranca_em_unidades

quantidade_para_analise = max(
    0,
    necessidade_bruta
    - estoque_atual
    - producao_aberta_no_horizonte
)
```

Depois, exibir opcionalmente o arredondamento por lote mínimo, sem afirmar viabilidade de capacidade.

#### Regras de segurança

- Não somar forecast e carteira quando representarem a mesma demanda sem uma regra de conciliação aprovada.
- Não distribuir a quantidade entre parceiros sem vínculo na fonte.
- Exibir fórmula, horizonte e parcelas utilizadas.
- Nomear o resultado como `quantidade para análise`, nunca como ordem recomendada.

#### Critérios de aceite

- O PCP consegue entender e reproduzir o cálculo manualmente.
- O sistema identifica quando não há dados suficientes.
- Testes cobrem ausência de forecast, carteira vazia, lote mínimo e sobreposição de demanda.

### Fase 3 — Novos sinais determinísticos

**Estimativa:** 4 a 6 dias

Implementar cada regra atrás de uma configuração e com testes separados.

#### Regras candidatas

1. **Divergência sell-in e sell-out**
   - somente onde ambos são observados em períodos comparáveis;
   - não interpretar automaticamente diferença como excesso.

2. **Risco de cobertura no parceiro**
   - somente onde há estoque estimado e sell-out suficiente;
   - informar idade e qualidade do dado.

3. **Tendência de demanda**
   - comparação determinística entre janelas recentes e anteriores;
   - separar tendência de sazonalidade.

4. **Pressão de evento**
   - evento no horizonte com elevação esperada de demanda;
   - manter impacto como hipótese configurada.

5. **Forecast incompatível com capacidade**
   - comparação por família e período;
   - sinal agregado, não promessa de viabilidade de SKU.

6. **Dado desatualizado ou descontínuo**
   - última atualização acima do limite;
   - períodos ausentes;
   - erros e duplicidades recorrentes.

#### Critérios de aceite

- Cada regra possui código, severidade, valores, origem, período e limitação.
- Regras novas podem ser desligadas individualmente.
- Ausência de dado reduz confiança sem criar venda, estoque ou demanda fictícios.

### Fase 4 — Colaboração Comercial B2B2C

**Estimativa:** 3 a 5 dias

#### Modelo

Criar níveis configuráveis:

- **Essencial:** sell-out periódico por SKU;
- **Conectado:** sell-out frequente e estoque por SKU;
- **Estratégico:** maior cobertura, frequência, consistência e histórico.

#### Indicadores por parceiro

- cobertura de SKU;
- cobertura de períodos;
- latência;
- completude;
- duplicidades e erros;
- continuidade;
- campos disponíveis;
- nível atual e próximo nível possível.

#### Interface

- Evoluir `Visibilidade B2B2C` para uma página de acompanhamento.
- Adicionar detalhe do parceiro com matriz SKU por período.
- Mostrar quais decisões foram afetadas pelos dados do parceiro.
- Tratar benefícios comerciais como hipóteses, não compromissos.

#### Critérios de aceite

- O nível é derivado de critérios explícitos.
- O sistema explica por que o parceiro está em determinado nível.
- É possível identificar qual dado falta para avançar de nível.

### Fase 5 — Métricas de validação do produto

**Estimativa:** 3 a 4 dias

#### Registro de decisão

Ampliar o feedback para registrar:

- decisão antes da análise;
- decisão após a análise;
- aceita, alterada, rejeitada ou investigar;
- se sell-out ou estoque do parceiro alterou a decisão;
- se apenas aumentou a confiança;
- tempo aproximado de análise;
- justificativa e usuário.

#### Métricas

- tempo médio e semanal de análise;
- percentual de prioridades aceitas, alteradas e rejeitadas;
- decisões alteradas por dado de parceiro;
- decisões com confiança aumentada;
- redução de casos de baixa confiança;
- evolução de cobertura B2B2C;
- evolução do ranking entre execuções.

Pedidos no prazo, aderência ao plano e rupturas realizadas só serão medidos quando existir dado realizado suficiente.

#### Critérios de aceite

- A meta de redução de 22 para 8 horas pode ser acompanhada.
- É possível demonstrar se a colaboração B2B2C gerou valor decisório.
- Métricas informadas pela empresa permanecem separadas das recalculadas pelo sistema.

### Fase 6 — Experiência e comparação histórica

**Estimativa:** 3 a 5 dias

- Atualizar a tabela principal para SKU, contexto, período, data crítica, quantidade para análise, score e confiança.
- Adicionar timeline do SKU.
- Criar comparação entre execução atual e anterior:
  - entrada e saída do ranking;
  - mudança de score;
  - mudança de confiança;
  - nova evidência disponível.
- Permitir exportação da visão filtrada com ressalvas e metadados.
- Implementar paginação ou virtualização caso a base cresça.

#### Critérios de aceite

- O usuário explica por que a prioridade mudou entre duas execuções.
- A exportação preserva fonte, período, confiança e limitações.
- Fluxos principais funcionam em desktop e celular.

### Fase 7 — Avaliação de IA opcional

**Estimativa:** 4 a 7 dias, somente após histórico suficiente

#### Portão de entrada

A fase só começa quando houver:

- histórico temporal suficiente;
- definição da tarefa e variável alvo;
- conjunto de validação;
- baseline determinística;
- métrica de utilidade para o PCP.

#### Primeiro experimento recomendado

Detecção de anomalias separada do ranking oficial:

- produzir apenas sinal e intensidade;
- explicar variáveis utilizadas;
- comparar contra limites determinísticos;
- permitir desligamento completo;
- não alterar pesos ou decisões automaticamente.

#### Critério de continuidade

A IA só permanece se superar a baseline simples e gerar alertas considerados úteis pelo PCP.

## 5. Ordem recomendada

| Ordem | Entrega | Resultado principal |
|---:|---|---|
| 1 | Correção semântica | Métricas confiáveis |
| 2 | Nova granularidade | SKU, contexto e período sem duplicação |
| 3 | Data e quantidade | Apoio a quando e quanto analisar |
| 4 | Novos sinais | Uso efetivo de forecast, sell-in, sell-out e eventos |
| 5 | Colaboração B2B2C | Qualidade e nível por parceiro |
| 6 | Métricas de produto | Evidência de valor e redução de esforço |
| 7 | Histórico e exportação | Auditabilidade longitudinal |
| 8 | IA opcional | Experimento controlado e comparável |

## 6. Plano de sprints

### Sprint 1 — Fundamentos

- Fase 0;
- estrutura das três visões da Fase 1;
- contratos e testes de granularidade.

### Sprint 2 — Decisão operacional

- concluir Fase 1;
- Fase 2;
- filtros e detalhe por contexto.

### Sprint 3 — Dados comerciais e novas regras

- Fase 3;
- Fase 4;
- matriz de cobertura do parceiro.

### Sprint 4 — Validação do valor

- Fase 5;
- Fase 6;
- testes end-to-end e documentação.

### Sprint posterior opcional

- Fase 7, condicionada aos dados e aos resultados das quatro primeiras sprints.

## 7. Estratégia de testes

### Núcleo

- unidade para cada indicador e regra;
- regressão das sete regras atuais;
- testes contra duplicação em joins;
- testes de ausência e granularidade incompatível;
- testes de fórmulas e arredondamento por lote.

### API

- contratos de resposta;
- filtros combinados;
- invalidação do cache;
- criação e comparação de snapshots;
- validação de entradas de feedback.

### Frontend

- loading, erro, vazio e sucesso;
- filtros de SKU, canal, parceiro e período;
- detalhe e timeline;
- fluxo de decisão;
- acessibilidade por teclado;
- responsividade em 390, 768, 1024 e 1440 pixels.

### Aceitação do produto

Demonstrar pelo menos:

1. SKU com risco global sem vínculo de parceiro;
2. SKU com dado específico de parceiro;
3. caso em que sell-out altera a confiança;
4. caso em que os dados são insuficientes;
5. cálculo reproduzível de data e quantidade para análise;
6. mudança entre duas execuções;
7. decisão humana registrada com tempo e justificativa.

## 8. Riscos e decisões necessárias

Antes da Fase 2, o grupo deve aprovar:

- horizonte da carteira e do forecast;
- regra para evitar dupla contagem entre carteira e forecast;
- conversão do estoque de segurança de dias para unidades;
- uso e arredondamento por lote mínimo;
- definição de data crítica;
- limites das novas regras;
- critérios objetivos dos níveis de colaboração;
- quais métricas podem ser recalculadas e quais permanecem apenas informadas.

Sem essas decisões, o sistema deve expor os componentes separadamente e não calcular uma falsa precisão.

## 9. Definição de conclusão

O protótipo evoluído estará coerente com a hipótese completa quando:

- priorizar no nível máximo suportado pela fonte;
- distinguir SKU global de SKU por parceiro;
- apresentar período e data de necessidade;
- calcular quantidade para análise com fórmula auditável;
- usar dados comerciais e operacionais sem dupla contagem;
- medir qualidade e colaboração por parceiro;
- registrar se o dado alterou a decisão;
- acompanhar as métricas principais;
- manter a decisão final humana;
- recusar cálculos quando os dados forem insuficientes.
