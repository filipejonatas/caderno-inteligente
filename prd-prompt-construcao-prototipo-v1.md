# PRD + Prompt de Construção
## Protótipo V1 — Caderno Inteligente

## Como usar este documento

Envie este arquivo para a IA de desenvolvimento junto com os arquivos de referência listados na seção 2.

A IA deverá primeiro analisar os arquivos, confirmar o entendimento e propor a estrutura técnica. Ela não deve começar a codificar imediatamente.

---

# Parte 1 — PRD do Protótipo V1

## 1. Contexto

O Caderno Inteligente opera em uma cadeia B2B2C e também possui canais diretos de venda.

O PCP precisa decidir:

- o que produzir;
- quanto produzir;
- quando disponibilizar cada SKU;
- para qual canal ou parceiro priorizar a disponibilidade.

Essa decisão é prejudicada pela fragmentação dos dados e pela visibilidade parcial do estoque e do sell-out dos parceiros.

O protótipo deverá apoiar essa decisão usando dados internos e dados de parceiros quando disponíveis.

## 2. Objetivo do protótipo

Construir uma aplicação local que:

1. carregue a base XLSM;
2. valide e padronize os dados;
3. calcule indicadores operacionais;
4. identifique riscos e exceções;
5. priorize SKUs para atenção do PCP;
6. mostre as evidências da prioridade;
7. sinalize a qualidade e as lacunas dos dados;
8. permita registrar a decisão do usuário.

## 3. Problema que o protótipo resolve

> **Ajudar o PCP a identificar quais SKUs precisam de atenção primeiro, por qual motivo e com qual nível de confiança, considerando estoque, pedidos, produção, capacidade, canal e visibilidade do parceiro.**

O protótipo não deve decidir ou liberar automaticamente uma ordem de produção.

## 4. Usuários

### Usuário principal

PCP/Supply Chain/S&OP.

### Usuário secundário

Comercial B2B.

### Necessidades do PCP

- identificar risco de ruptura;
- identificar excesso de estoque;
- encontrar pedidos sem produção adequada;
- encontrar ordens posteriores à data prometida;
- entender pressão de capacidade;
- saber quando a recomendação depende de dados ausentes.

### Necessidades do Comercial

- visualizar cobertura de sell-out;
- identificar parceiros com baixa visibilidade;
- encontrar divergências entre sell-in e sell-out;
- entender quais informações do parceiro alteram a confiança da análise.

## 5. Escopo funcional da V1

### 5.1 Importação da base

Ler o arquivo XLSM sem alterar o arquivo original.

Abas prioritárias:

- `Produtos`;
- `Vendas_24m`;
- `Estoque_Atual`;
- `Carteira_Pedidos`;
- `Ordens_Producao`;
- `Capacidade_Semanal`;
- `Sell_In`;
- `Sell_Out`;
- `Forecast_Comercial`;
- `Calendario_Eventos`;
- `Parceiros_Canais`;
- `Lead_Times`.

As demais abas podem ser carregadas como apoio, se necessário.

### 5.2 Validação dos dados

Validar:

- SKUs válidos;
- datas válidas;
- valores ausentes;
- duplicidades;
- quantidades negativas;
- chaves incompatíveis;
- parceiros inexistentes;
- inconsistências entre sell-in, sell-out e estoque;
- cobertura parcial de sell-out.

O sistema deve exibir erros e alertas de qualidade. Não deve corrigir silenciosamente os dados.

### 5.3 Indicadores determinísticos

Calcular:

- cobertura de estoque;
- diferença entre cobertura e lead time;
- diferença entre cobertura e estoque de segurança;
- pedidos por SKU;
- quantidade em ordens de produção;
- diferença entre pedido e produção;
- atraso potencial da ordem;
- capacidade disponível da família;
- cobertura acima de 90 dias;
- sell-in acumulado;
- sell-out acumulado;
- diferença entre sell-in e sell-out;
- existência de sell-out;
- nível de visibilidade do parceiro.

### 5.4 Regras de risco

Implementar inicialmente as seguintes regras:

```text
Se cobertura < lead time:
    risco de ruptura

Se cobertura < estoque de segurança:
    risco crítico de estoque

Se existe pedido e não existe ordem de produção:
    pedido sem produção correspondente

Se a conclusão da ordem > data prometida:
    risco de atraso

Se cobertura > 90 dias:
    risco de excesso

Se sell-out não existe:
    sinalizar lacuna e reduzir confiança

Se pedidos ou demanda excedem a capacidade da família:
    conflito operacional
```

Cada regra deverá gerar:

- código do risco;
- descrição;
- severidade;
- valor utilizado no cálculo;
- origem do dado.

### 5.5 Priorização

Criar um ranking de exceções por SKU.

A primeira versão pode utilizar uma pontuação transparente, por exemplo:

- risco abaixo do lead time;
- risco abaixo do estoque de segurança;
- pedido sem ordem;
- ordem posterior à data prometida;
- capacidade pressionada;
- excesso de cobertura;
- divergência sell-in/sell-out;
- baixa visibilidade do parceiro.

Os pesos devem ficar em configuração separada, não codificados de forma espalhada.

A pontuação não deve ser apresentada como uma decisão ótima. Ela deve ser apresentada como uma ordenação de atenção.

### 5.6 Interface

Criar uma aplicação local, preferencialmente em Streamlit, contendo:

#### Página ou seção de visão geral

- total de SKUs;
- SKUs em risco de ruptura;
- SKUs em excesso;
- pedidos potencialmente atrasados;
- famílias com capacidade pressionada;
- percentual de sell-out disponível;
- quantidade de casos com baixa confiança.

#### Página ou seção de prioridades

Tabela com:

- prioridade;
- SKU;
- produto;
- família;
- canal/parceiro;
- tipo de risco;
- cobertura;
- lead time;
- pedido;
- produção;
- capacidade;
- confiança;
- evidências.

#### Filtros

- família;
- SKU;
- canal;
- parceiro;
- tipo de risco;
- prioridade;
- confiança;
- existência de sell-out.

#### Página ou seção de qualidade dos dados

- abas carregadas;
- registros por aba;
- campos ausentes;
- duplicidades;
- cobertura de sell-out;
- última data disponível;
- dados observados, estimados e previstos;
- alertas de consistência.

#### Página ou seção de detalhe do SKU

Ao selecionar um SKU, mostrar:

- dados cadastrais;
- estoque e cobertura;
- pedidos;
- produção;
- capacidade;
- forecast;
- sell-in;
- sell-out;
- riscos detectados;
- evidências;
- confiança;
- decisão registrada pelo usuário.

### 5.7 Feedback do usuário

Permitir registrar:

- prioridade aceita;
- prioridade alterada;
- prioridade rejeitada;
- investigar;
- observação;
- usuário;
- data/hora.

O feedback deve ser salvo em SQLite ou CSV separado da base original.

A V1 não deve alterar automaticamente as regras com base no feedback.

## 6. IA do produto

A V1 não terá IA conversacional.

Também não é necessário implementar um modelo preditivo na primeira etapa.

O protótipo deve funcionar corretamente com regras determinísticas.

Se houver tempo e dados suficientes, poderá ser adicionado um componente opcional de detecção de anomalias usando Isolation Forest, desde que:

- o modelo seja separado do motor de regras;
- o resultado seja apenas um sinal adicional;
- o modelo não altere sozinho a prioridade final;
- seja possível comparar IA e regras;
- o modelo seja executado localmente;
- a funcionalidade possa ser desligada sem quebrar a aplicação.

## 7. Fora do escopo

Não implementar nesta V1:

- chatbot;
- IA conversacional;
- decisão autônoma de produção;
- emissão de ordem de produção;
- integração real com ERP;
- integração real com parceiros;
- API obrigatória;
- previsão universal;
- otimização matemática completa da fábrica;
- contratos ou benefícios comerciais;
- autenticação complexa;
- infraestrutura de produção;
- fine-tuning;
- agentes autônomos.

## 8. Critérios de sucesso

### Funcionais

- o XLSM é carregado sem alteração;
- os dados são validados;
- os principais riscos são calculados;
- a prioridade é ordenada;
- cada prioridade apresenta evidências;
- a ausência de sell-out é explicitada;
- o usuário consegue filtrar e consultar um SKU;
- o usuário consegue registrar feedback.

### Qualidade

- os mesmos dados produzem o mesmo resultado;
- nenhuma recomendação aparece sem evidência;
- nenhum sell-out ausente é convertido em zero;
- regras possuem testes automatizados;
- erros de leitura são informados;
- o modelo opcional pode ser comparado com regras simples.

## 9. Casos de demonstração obrigatórios

O protótipo deverá demonstrar pelo menos:

1. um SKU com risco de ruptura;
2. um SKU com pedido e sem produção adequada;
3. um SKU com ordem posterior à data prometida;
4. um SKU com excesso de cobertura;
5. um caso com sell-in e sell-out disponíveis;
6. um caso sem sell-out, exibindo baixa confiança;
7. uma família com capacidade pressionada;
8. um registro de feedback do usuário.

## 10. Segurança e privacidade

Mesmo com dados fictícios:

- não alterar a base original;
- não armazenar credenciais no código;
- usar variáveis de ambiente para segredos;
- não enviar o XLSM completo para serviços externos;
- não enviar dados pessoais de consumidores;
- separar feedback da base original;
- registrar logs básicos de execução;
- não expor dados de um parceiro para outro;
- manter o protótipo local nesta etapa.

---

# Parte 2 — Especificação técnica inicial

## Stack recomendada

- Python 3.11+;
- pandas;
- openpyxl;
- Streamlit;
- SQLite;
- pytest;
- scikit-learn somente se o componente de anomalias for implementado;
- Plotly ou Altair para gráficos, se necessário.

## Estrutura esperada

```text
project/
├── app.py
├── README.md
├── requirements.txt
├── data/
│   └── README.md
├── src/
│   ├── ingestion.py
│   ├── validation.py
│   ├── transformations.py
│   ├── rules.py
│   ├── prioritization.py
│   ├── anomalies.py
│   ├── feedback.py
│   └── config.py
├── tests/
│   ├── test_ingestion.py
│   ├── test_validation.py
│   ├── test_rules.py
│   └── test_prioritization.py
└── docs/
    └── decisions.md
```

A estrutura pode ser alterada se houver justificativa técnica, mas a IA deve explicar a mudança antes de implementá-la.

## Regras de implementação

- Não misturar leitura de arquivos com regras de negócio.
- Não colocar pesos diretamente na interface.
- Não esconder erros de validação.
- Não usar valores mágicos sem configuração.
- Não alterar a planilha de origem.
- Não adicionar dependências sem necessidade.
- Escrever testes para cada regra.
- Manter as funções pequenas e verificáveis.
- Usar nomes de campos em português ou documentar claramente a tradução.
- Registrar decisões técnicas no README ou em `docs/decisions.md`.

---

# Parte 3 — Prompt para a IA de desenvolvimento

Copie o texto abaixo e envie junto com os arquivos de referência.

```text
Você é um engenheiro de software responsável por construir o Protótipo V1 do projeto Caderno Inteligente.

Leia integralmente:

1. o PRD e a especificação técnica deste documento;
2. o arquivo da base XLSM;
3. o diagnóstico da Semana 1;
4. a entrega da Semana 2;
5. qualquer notebook ou script de análise anexado.

Contexto do produto:

O protótipo deve apoiar o PCP a identificar quais SKUs precisam de atenção primeiro, por qual motivo e com qual nível de confiança, conectando dados de estoque, pedidos, produção, capacidade, canal e visibilidade parcial dos parceiros.

A solução possui duas frentes integradas:

- Colaboração Comercial B2B2C;
- Priorização de PCP.

Objetivo da primeira etapa:

Implementar somente a ingestão, validação, normalização e exploração inicial dos dados.

Antes de escrever qualquer código:

1. confirme quais arquivos foram recebidos;
2. faça um inventário das abas e colunas da base;
3. identifique chaves e relacionamentos;
4. identifique campos ausentes, duplicidades e inconsistências;
5. proponha a estrutura de pastas;
6. liste as dependências necessárias;
7. descreva as decisões técnicas;
8. apresente dúvidas e riscos;
9. proponha os primeiros testes;
10. aguarde aprovação antes de implementar a próxima etapa.

Restrições obrigatórias:

- não implementar chatbot;
- não implementar IA conversacional;
- não enviar a planilha completa para uma API externa;
- não usar IA para decidir ou liberar produção;
- não alterar o arquivo XLSM original;
- não inventar dados;
- não tratar ausência de sell-out como venda zero;
- não criar integração real com parceiros nesta primeira etapa;
- não criar funcionalidades fora do PRD;
- não instalar dependências sem explicar o motivo;
- não modificar regras de negócio sem registrar a alteração.

Stack preferencial:

- Python;
- pandas;
- openpyxl;
- Streamlit;
- SQLite para feedback;
- pytest;
- scikit-learn somente se o componente opcional de anomalias for aprovado.

Ordem obrigatória de implementação:

ETAPA 1 — Ingestão e validação

- carregar as abas necessárias;
- preservar a base original;
- validar colunas, chaves, datas, duplicidades e valores ausentes;
- gerar relatório de qualidade;
- criar testes.

ETAPA 2 — Normalização e indicadores

- padronizar SKU, datas e tipos;
- criar tabelas internas consistentes;
- calcular cobertura, lead time, segurança, pedidos, produção e capacidade;
- documentar os cálculos;
- criar testes.

ETAPA 3 — Regras determinísticas

Implementar:

- risco abaixo do lead time;
- risco abaixo do estoque de segurança;
- pedido sem ordem;
- ordem posterior à data prometida;
- excesso de cobertura;
- conflito de capacidade;
- baixa visibilidade de sell-out.

Cada regra deve retornar código, descrição, severidade, valores utilizados e origem dos dados.

ETAPA 4 — Priorização

- criar um ranking transparente de exceções;
- manter pesos em configuração;
- exibir os motivos da prioridade;
- indicar nível de confiança;
- não afirmar que o ranking é uma solução ótima.

ETAPA 5 — Interface

Criar uma aplicação Streamlit com:

- visão geral;
- lista de prioridades;
- filtros;
- detalhe do SKU;
- qualidade dos dados;
- registro de feedback.

ETAPA 6 — IA opcional

Somente depois de validar as regras, avaliar Isolation Forest para detecção de anomalias.

Se implementado:

- manter o modelo separado das regras;
- executar localmente;
- não alterar a prioridade sozinho;
- retornar somente sinal de anomalia e intensidade;
- comparar com uma abordagem determinística;
- criar testes e documentar limitações.

Formato de trabalho:

Ao concluir cada etapa, retorne:

1. arquivos criados ou alterados;
2. comandos executados;
3. testes executados;
4. resultados dos testes;
5. problemas encontrados;
6. decisões que precisam de aprovação;
7. próximo passo recomendado.

Não avance automaticamente para a etapa seguinte se houver erro de dados, ambiguidade de regra ou teste quebrado.
```

---

# Parte 4 — Arquivos que devem ser fornecidos à IA

## Obrigatórios

1. **Base de dados XLSM**
   - fonte operacional do desafio;
   - arquivo original, sem alterações.

2. **Entrega da Semana 1**
   - diagnóstico do problema;
   - evidências;
   - escopo;
   - limitações.

3. **Entrega da Semana 2**
   - hipótese de solução;
   - duas frentes;
   - papel da IA;
   - métricas;
   - dados e qualidade.

4. **Este PRD/prompt**
   - requisitos funcionais;
   - arquitetura inicial;
   - etapas;
   - restrições;
   - critérios de aceitação.

## Recomendados

5. **Notebook ou scripts usados para análise**
   - fórmulas dos indicadores;
   - critérios de cálculo;
   - listas de SKUs de exemplo;
   - validações já realizadas.

6. **Dicionário de dados**
   - caso exista fora da aba `Dicionario_Dados`.

7. **Regras definidas pelo grupo**
   - pesos de prioridade;
   - nomes dos riscos;
   - níveis de confiança;
   - critérios de sucesso.

## Não fornecer no primeiro momento

- credenciais;
- chaves de API;
- dados reais de parceiros;
- dados pessoais de consumidores;
- contratos comerciais;
- integrações de produção;
- arquivos modificados sem controle de versão.

---

# Parte 5 — Decisão inicial recomendada

Começar sem IA de produto.

A primeira entrega técnica deve provar:

1. que a base é lida corretamente;
2. que os indicadores são calculados corretamente;
3. que as regras de risco funcionam;
4. que a prioridade é explicável;
5. que a qualidade dos dados aparece na interface;
6. que o feedback é registrado.

Somente depois disso decidir se o Isolation Forest agrega valor.

> **A IA de desenvolvimento pode ajudar a construir o protótipo desde o início. A IA do produto só entra depois que o fluxo determinístico estiver funcionando e validado.**
