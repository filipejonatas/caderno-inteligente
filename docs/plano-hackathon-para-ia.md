# Plano rápido de implementação por IA para o hackathon

## 1. Objetivo da rodada

Em uma única rodada de implementação, evoluir o protótipo para demonstrar com clareza:

1. quais SKUs precisam de atenção;
2. por qual motivo;
3. qual é a data crítica conhecida;
4. qual é o déficit operacional calculável;
5. como sell-out e qualidade do dado afetam a confiança;
6. que a decisão final continua sendo humana.

O objetivo não é criar um sistema de produção completo. É produzir uma demonstração coerente, auditável e visualmente convincente.

## 2. Limite de tempo

**Execução esperada pela IA:** uma sessão de aproximadamente 3 a 5 horas, incluindo testes e revisão visual.

Se o tempo estiver acabando, a IA deve concluir e validar o que já começou. Não deve iniciar funcionalidades opcionais com o build ou os testes quebrados.

## 3. Escopo obrigatório

### Entrega 1 — Corrigir a métrica de ruptura

O backend atual soma ocorrências de duas regras e apresenta o total como se fossem SKUs.

Implementar:

- `rupture_sku_count`: quantidade de SKUs únicos com `RUP_LEAD_TIME` ou `RUP_SAFETY_STOCK`;
- `below_lead_time_count`;
- `below_safety_stock_count`;
- manter `rupture_signal_count` apenas se necessário para os gráficos.

No frontend:

- card principal: `SKUs com risco de ruptura`;
- detalhe ou subtítulo: `15 abaixo do lead time · 13 abaixo da segurança`, usando os valores reais da API.

### Entrega 2 — Enriquecer a prioridade sem mudar a granularidade

Não criar agora um novo modelo completo por parceiro, canal e semana. Manter uma linha por SKU e adicionar campos úteis para a demonstração:

```text
critical_date
critical_date_reason
operational_gap_quantity
projected_stock_quantity
first_promised_date
first_production_completion
sell_in_quantity
sell_out_quantity
sell_in_minus_sell_out_quantity
forecast_quantity
analysis_scope = "SKU global"
missing_data
```

Regras dos novos campos:

- `critical_date`: menor data disponível entre a primeira promessa e a primeira conclusão prevista;
- `critical_date_reason`: informar qual data foi utilizada;
- `operational_gap_quantity = max(0, carteira - estoque atual - produção aberta)`;
- o déficit deve ser chamado de `lacuna operacional` ou `quantidade para análise`, nunca de ordem recomendada;
- não distribuir o valor entre parceiros;
- quando uma data ou valor não existir, retornar `null` e explicar em `missing_data`.

### Entrega 3 — Melhorar o detalhe do SKU

Adicionar uma seção visual `Demanda e atendimento` com:

- estoque atual;
- carteira;
- produção aberta;
- estoque projetado;
- lacuna operacional;
- primeira data prometida;
- primeira conclusão prevista;
- atraso em dias, quando aplicável.

Adicionar uma seção `Canal e confiança` com:

- sell-in acumulado;
- sell-out acumulado;
- diferença observada;
- parceiros com sell-out;
- forecast disponível;
- nível de confiança;
- razão da confiança;
- dados ausentes.

Manter a ressalva já existente de que capacidade por família não prova viabilidade individual do SKU.

### Entrega 4 — Tornar a página B2B2C demonstrável

Sem criar integrações reais, enriquecer cada cartão de parceiro com um nível derivado apenas dos dados existentes:

- `Sem visibilidade`: cobertura igual a zero;
- `Essencial`: cobertura maior que zero e menor que 40%;
- `Conectado`: cobertura entre 40% e 79%;
- `Estratégico`: cobertura igual ou superior a 80%.

Mostrar:

- nível atual;
- cobertura de SKUs;
- meses observados;
- última data de sell-out;
- próximo nível e dado necessário para alcançá-lo.

Adicionar uma mensagem explícita:

> O nível é uma classificação demonstrativa baseada em cobertura e atualidade. Não representa acordo comercial firmado.

### Entrega 5 — Registrar impacto do dado na decisão

Ampliar o formulário de feedback com dois campos:

```text
partner_data_effect:
  - nao_utilizado
  - confirmou
  - aumentou_confianca
  - alterou_decisao

analysis_minutes: número inteiro opcional
```

Persistir os campos no SQLite com migração compatível para o banco existente.

Na página de decisões, mostrar:

- ação tomada;
- efeito do dado do parceiro;
- tempo informado;
- observação;
- data e usuário.

Na visão geral, adicionar dois indicadores simples:

- decisões registradas;
- decisões alteradas ou fortalecidas por dado do parceiro.

## 4. Escopo opcional

Executar somente se todas as entregas obrigatórias estiverem funcionando.

### Comparação de cenário

Na tela de cenários, mostrar para os dez primeiros SKUs:

- posição oficial;
- posição simulada;
- variação de posições;
- score oficial e simulado.

### Exportação simples

Adicionar exportação CSV da tabela filtrada de prioridades, incluindo:

- SKU;
- produto;
- família;
- score;
- confiança;
- data crítica;
- lacuna operacional;
- motivos;
- ressalva de uso.

## 5. Fora do escopo

A IA não deve implementar nesta rodada:

- modelo preditivo;
- Isolation Forest;
- chatbot;
- autenticação;
- integração com parceiros;
- novo banco de dados;
- otimização de capacidade;
- recomendação automática de ordem;
- alocação de quantidade entre parceiros;
- reconstrução completa da arquitetura;
- paginação avançada;
- suíte E2E com nova infraestrutura;
- deploy em nuvem.

## 6. Ordem de execução para a IA

### Bloco A — Inspeção rápida

1. Ler integralmente:
   - `backend/main.py`;
   - `src/caderno_inteligente/indicators.py`;
   - `src/caderno_inteligente/rules.py`;
   - `src/caderno_inteligente/prioritization.py`;
   - `src/caderno_inteligente/feedback.py`;
   - `frontend/src/types.ts`;
   - `frontend/src/api.ts`;
   - `frontend/src/pages.tsx`;
   - testes relacionados.
2. Executar a suíte existente antes de editar.
3. Não alterar fórmulas atuais sem registrar a mudança.

### Bloco B — Núcleo e API

1. Corrigir métricas de ruptura.
2. Enriquecer indicadores por SKU.
3. Levar os campos para a priorização e detalhe.
4. Derivar o nível demonstrativo dos parceiros.
5. Migrar feedback de modo compatível.
6. Criar testes antes de modificar a interface.

### Bloco C — Frontend

1. Atualizar tipos da API.
2. Corrigir os cards da visão geral.
3. Atualizar a tabela de prioridades com data crítica e lacuna operacional.
4. Enriquecer o drawer do SKU.
5. Atualizar a página B2B2C.
6. Atualizar formulário e histórico de decisões.
7. Preservar o design e a responsividade existentes.

### Bloco D — Validação

1. Executar todos os testes Python.
2. Executar `npm run check`.
3. Iniciar backend e frontend.
4. Verificar console do navegador.
5. Inspecionar 1440 x 900 e 390 x 844.
6. Testar manualmente:
   - visão geral;
   - filtro de prioridade;
   - detalhe de um SKU;
   - página B2B2C;
   - registro de uma decisão.
7. Corrigir os problemas encontrados antes de encerrar.

## 7. Testes mínimos obrigatórios

Adicionar testes para:

1. SKU presente nas duas regras de ruptura ser contado uma única vez em `rupture_sku_count`;
2. lacuna operacional nunca ser negativa;
3. ausência de data gerar `critical_date = null`;
4. detalhe do SKU expor data, lacuna, sell-in, sell-out e forecast;
5. nível B2B2C ser calculado nos limites 0%, 20%, 40% e 80%;
6. migração do SQLite preservar feedback já existente;
7. novos campos de decisão serem persistidos e retornados pela API.

## 8. Critérios de aceite da demonstração

Ao final, deve ser possível demonstrar este roteiro:

1. Abrir a visão geral e explicar quantos SKUs únicos têm risco de ruptura.
2. Abrir uma prioridade e explicar o score pelas regras acionadas.
3. Mostrar data prometida, conclusão prevista e lacuna operacional.
4. Mostrar se existe sell-out e como isso afeta a confiança.
5. Abrir um parceiro e explicar seu nível demonstrativo de colaboração.
6. Registrar que o dado do parceiro confirmou, fortaleceu ou alterou a decisão.
7. Mostrar o tempo informado para a análise.
8. Reforçar que o sistema apoia a decisão e não libera produção.

## 9. Prompt pronto para executar com IA

```text
Implemente o plano de hackathon descrito em docs/plano-hackathon-para-ia.md.

Objetivo: melhorar a coerência demonstrável do protótipo em uma única rodada, sem transformar o projeto em um sistema de produção.

Regras obrigatórias:

- preserve o XLSM original;
- não invente alocação por canal, parceiro ou semana;
- mantenha uma linha de prioridade por SKU;
- trate a quantidade calculada como lacuna operacional ou quantidade para análise;
- mantenha a decisão final humana;
- preserve as sete regras existentes e seus testes;
- faça migrações SQLite compatíveis com os bancos atuais;
- não adicione IA preditiva, chatbot, autenticação ou deploy;
- não deixe testes, typecheck ou build quebrados;
- valide a interface em desktop e celular;
- ao final, relate arquivos alterados, testes executados, resultado e limitações restantes.

Execute na ordem:

1. inspeção e testes de linha de base;
2. backend, indicadores e persistência;
3. testes Python;
4. contratos e frontend;
5. typecheck e build;
6. inspeção visual e correções;
7. resumo final.

Se houver ambiguidade de negócio, escolha a alternativa mais conservadora, exponha a limitação na interface e continue. Só interrompa se a escolha puder produzir um número enganoso ou alterar a base original.
```

## 10. Resultado esperado

Este corte não implementa toda a hipótese das Semanas 1 e 2. Ele produz uma demonstração mais coerente ao conectar:

```text
problema identificado
→ regra acionada
→ prioridade do SKU
→ data crítica conhecida
→ lacuna operacional calculável
→ qualidade e confiança
→ efeito do dado do parceiro
→ decisão humana registrada
```

Essa sequência é suficiente para demonstrar valor no hackathon sem alegar capacidades que o protótipo ainda não possui.
