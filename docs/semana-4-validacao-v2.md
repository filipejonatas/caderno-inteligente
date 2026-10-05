# Semana 4 — Validação da V2

Este relatório consolida a evidência de aplicabilidade do Caderno Inteligente V2. A mesma informação aparece, atualizada a cada consulta, na página **`/validacao`** (`GET /api/validation/summary`), que pode ser exportada em CSV ou impressa.

> Os números abaixo foram obtidos em 05/10/2026 sobre a planilha de demonstração com SHA-256 `03fa0ed4…803f`. Se a planilha mudar, a Central de validação indica que os casos congelados precisam ser revisados.

## 1. Pergunta avaliada

O protótipo ajuda o PCP a identificar quais SKUs exigem ação, quanto analisar para produção, quais parceiros apresentam risco ou oportunidade e quais evidências sustentam cada recomendação, sem decidir no lugar das pessoas?

A Semana 4 pede quatro evidências:

1. comparação com o processo atual;
2. avaliação da previsão contra uma referência;
3. casos representativos;
4. comportamento seguro.

## 2. Método

| Evidência | Como foi obtida |
|---|---|
| Processo atual | Linha de base informada pela empresa (Semana 1, Diagnóstico do problema), exibida em coluna separada do valor recalculado e da meta |
| Previsão | Holdout temporal dos 3 últimos meses por SKU para cada modelo candidato, para o modelo selecionado e para uma baseline explícita (último mês observado), que não participa da seleção |
| Casos representativos | Oito casos congelados em `config/validation_center.json`, com hash da planilha, definidos a partir das regras do PRD antes de comparar os resultados. Não ajustam pesos, limiares nem modelos |
| Comportamento seguro | Verificações executadas a cada consulta com entradas controladas, mais testes automatizados do frontend |
| Qualidade técnica | Suítes `pytest` e `npm run check`, acessibilidade com axe-core e smoke test por HTTP |

## 3. Amostra

| Item | Quantidade |
|---|---:|
| SKUs no catálogo | 50 |
| Meses de faturamento | 24 (set/2024 a ago/2026) |
| Meses do holdout | 3 (jun a ago/2026) |
| SKUs elegíveis para previsão (≥ 6 meses) | 50 |
| SKUs com dados insuficientes | 0 |
| Parceiros e canais cadastrados | 8 (5 key accounts e 3 canais diretos) |
| Pares parceiro–SKU com vínculo real | 95 (50 com sell-in/out e 45 só com carteira) |
| Cobertura de sell-out (pares observados / possíveis) | 50 / 250 = 20% |
| Pedidos em carteira / ordens de produção | 53 / 34 |
| Registros de tempo de análise | 0 |

## 4. Resultados

### 4.1 Comparação com o processo atual

| Indicador | Informado pela empresa | Recalculado no protótipo | Meta |
|---|---:|---|---:|
| Tempo de análise | 22 h/semana | Não disponível: 0 decisões com minutos (mínimo 20) | 8 h/semana |
| Erro do forecast | MAPE 31% | WAPE ponderado 6,9% — **métrica diferente, não comparável** | — |
| Pedidos no prazo | 89% | Não recalculável: a base não traz entregas realizadas | 96% |
| Aderência ao plano | 78% | Não recalculável: a base não traz produção realizada | — |

O MAPE de 31% se refere ao forecast comercial da empresa. A base só traz forecast comercial para meses futuros (a partir de outubro de 2026), então ele não pode ser recalculado. O WAPE exibido mede o modelo estatístico do protótipo sobre o faturamento.

### 4.2 Previsão contra baseline

| Modelo | Papel | WAPE mediano | WAPE ponderado | Escolhido em |
|---|---|---:|---:|---:|
| Média móvel de 3 meses | candidato | 7,1% | 7,6% | 34 SKUs |
| Sazonal ingênuo de 12 meses | candidato | 10,2% | 11,7% | 16 SKUs |
| Modelo selecionado por SKU | selecionado | 6,4% | 6,9% | 50 SKUs |
| Último mês observado | baseline | 7,5% | 8,0% | — |

- O modelo selecionado **superou a baseline em 34 dos 50 SKUs** e **não superou em 16**.
- No agregado, a redução de erro é pequena (6,9% contra 8,0%).

### 4.3 Casos congelados

| Caso | Origem | Resultado |
|---|---|---|
| VC-01 Ruptura com carteira e sem produção | sintético¹ | passou |
| VC-02 Produção posterior à promessa (CI-0005) | base | passou |
| VC-03 Excesso de estoque (CI-0044) | base | passou |
| VC-04 Prioridade alta sem produção adicional (CI-0041) | base | passou |
| VC-05 Forecast com dados insuficientes | sintético² | passou |
| VC-06 Reposição sustentada no parceiro (KA-01 / CI-0011) | base | passou |
| VC-07 Parceiro com dado ausente (E-commerce / CI-0009) | base | passou |
| VC-08 Pressão de capacidade (CI-0014) | base | passou |

¹ Nenhum SKU da base tem ruptura, carteira positiva e nenhuma OP ao mesmo tempo. ² Todos os SKUs têm histórico suficiente.

### 4.4 Comportamento seguro

7 de 7 verificações executadas foram aprovadas:

- ausência de sell-out reduz a confiança;
- holdout com demanda zero não gera WAPE;
- forecast insuficiente não vira quantidade;
- capacidade agregada exige revisão;
- as 50 recomendações exigem revisão humana;
- dado ausente não vira zero;
- SKU inexistente retorna 404.

O erro de API é coberto por teste automatizado do frontend.

### 4.5 Qualidade técnica

| Verificação | Resultado |
|---|---|
| `pytest` (núcleo, API, persistência, segurança, contratos e smoke test) | 193 testes aprovados |
| `npm run check` (typecheck, Vitest, `node --test`, build e segredos no bundle) | 131 + 20 testes aprovados; build e varredura ok |
| Acessibilidade (axe-core) | 0 violações em 14 páginas × 2 viewports no jsdom; 0 violações no Chromium real, com contraste, a 375 e 1440 px |
| Smoke test por HTTP com cabeçalhos da Vercel | 47/47 em configuração equivalente à publicação (produção, demonstração, somente leitura) |

## 5. Falhas e limitações encontradas

Estas falhas são mostradas na Central de validação, não ocultadas:

1. **Previsão:** o modelo selecionado não superou a baseline ingênua em 16 de 50 SKUs. O ganho agregado é pequeno.
2. **Otimismo do holdout:** o mesmo holdout escolhe e avalia o modelo. Por isso todos os 50 SKUs ficaram com confiança de previsão "alta" (WAPE ≤ 20%). O resultado não garante a precisão futura.
3. **Cobertura dos casos:** dois casos são sintéticos porque a base não contém esses exemplos.
4. **Indicadores não recalculáveis:** pedidos no prazo e aderência ao plano. O ganho de tempo de análise ainda não pode ser afirmado (0 registros com minutos).
5. **Atribuição por parceiro:** decisões não são atribuíveis a parceiros, porque o feedback não registra o código do parceiro.
6. **Visibilidade:** a cobertura de sell-out é de apenas 20% dos pares parceiro–SKU. Nenhum ranking recebe confiança "alta", e 20 dos 41 SKUs priorizados têm confiança baixa.
7. **Limiares:** os limiares de regras e de sinais comerciais são demonstrativos e não foram aprovados pela empresa.
8. **Teste com usuários:** o teste moderado previsto no plano (PCP, Comercial e uma pessoa sem contexto) **ainda não foi realizado**. O protocolo está na seção 7.

## 6. Mudanças da V1 para a V2

| Etapa | Mudança | Efeito para o usuário |
|---|---|---|
| 1 | Rotas reais e modularização | Links compartilháveis, histórico do navegador e 404 |
| 2 | Carregamento por página | Cada tela consulta só o que exibe; falhas ficam isoladas |
| 3 | Jornada visual de decisão | Visão geral em blocos: atenção → ação → qualidade da decisão |
| 4 | Visão parceiro–SKU e recomendação comercial | Repor, monitorar, investigar ou pedir dados por parceiro, sem distribuir dados globais |
| 5 | Central de validação | Linha de base, baseline de previsão, casos congelados e comportamento seguro |
| 6 | Comparação entre execuções | Explica por que uma prioridade mudou (sinais e pesos) |
| 7 | Testes do frontend e acessibilidade | Contraste AA, foco visível, teclado no menu, error boundary e contrato frontend↔API |
| 8 | Segurança e modo demonstração | Somente leitura, aviso de demonstração, CORS restrito, validação de entrada e erros sem detalhes internos |
| 9 | Documentação e demonstração | Guia atualizado, roteiro de 5 minutos e smoke test das URLs publicadas |

Ajustes feitos após testes e revisões, registrados também na Central de validação; nenhum alterou pesos ou modelos:

- **Métrica de ruptura:** passou a contar SKUs únicos.
- **Histórico insuficiente:** não gera mais previsão zero.
- **Rótulo de datas:** o intervalo entre promessa e conclusão passou a se chamar intervalo de risco.
- **Cobertura comercial:** passou a ser medida pelos registros, não pelo cadastro.
- **Feedback:** separa a ação humana do efeito do dado do parceiro.

Correções vindas dos testes da V2:

- contraste do texto secundário;
- foco invisível em linhas da tabela;
- tabelas roláveis sem acesso por teclado;
- histórico órfão ao atualizar caso inexistente;
- aviso de revisão humana ausente no SKU sem previsão.

## 7. Protocolo do teste moderado (pendente)

- **Participantes:** pelo menos três pessoas — uma do PCP, uma do Comercial e uma sem contexto prévio.
- **Duração:** cerca de 20 minutos por pessoa.
- **Ambiente:** publicação com `DEMO_MODE=true`.
- **Registro:** para cada tarefa, anotar tempo, se concluiu, erro, dúvida e sugestão.

| # | Tarefa | Critério de sucesso |
|---|---|---|
| 1 | "Qual SKU você analisaria primeiro e por quê?" | Cita o primeiro da fila e ao menos um sinal |
| 2 | "Esse SKU precisa de produção agora? Quanto?" | Distingue prioridade de ação e lê a quantidade ou "sem ação necessária" |
| 3 | "Existe algum parceiro com oportunidade de reposição?" | Encontra uma sugestão "Avaliar reposição" e a evidência mensal |
| 4 | "Quanto você confia na previsão desse SKU?" | Localiza WAPE/confiança e a comparação com a baseline |
| 5 | "Registre sua decisão" | Registra a decisão com o efeito do dado do parceiro |

| Participante | Perfil | Tarefa | Tempo | Concluiu | Erro | Dúvida | Sugestão |
|---|---|---|---|---|---|---|---|
| | | | | | | | |

Os minutos de análise registrados nas decisões alimentam a Central de validação. Somente com 20 ou mais registros o tempo pode ser comparado à linha de base de 22 h semanais.
