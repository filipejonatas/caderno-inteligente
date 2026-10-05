# Decisões técnicas

## 2026-09-28 — Etapa 1

- O arquivo XLSM original é uma fonte somente leitura e não será copiado, salvo ou sobrescrito pelo protótipo.
- As abas têm cabeçalho na linha 3; a ingestão usa `skiprows=2` de forma explícita.
- Ausência de sell-out representa falta de observação, não quantidade vendida igual a zero.
- A validação expõe erros e avisos; não corrige silenciosamente dados ou regras de negócio.
- A normalização, os indicadores e as regras determinísticas permanecem fora desta etapa.

## 2026-09-28 — Etapa 2

- A normalização opera sobre cópias internas: SKU é padronizado em maiúsculas e tipos numéricos e de data são convertidos após a validação.
- A visão de indicadores é uma tabela por SKU; chaves operacionais são agregadas por SKU e capacidade por família.
- Cobertura calculada permanece ao lado da cobertura informada, permitindo auditar divergências; nenhuma delas é substituída silenciosamente.
- `projected_stock_quantity` é um indicador de conciliação de volumes, não uma decisão de produção.
- Capacidade semanal não é alocada a pedidos/OPs nesta etapa, pois a fonte não fornece essa relação.

## 2026-09-28 — Etapa 3

- As regras são sinais determinísticos e auditáveis; não geram ordem de produção nem recomendação autônoma.
- Excesso de cobertura usa limite configurável de 90 dias e conflito de capacidade usa ocupação média familiar acima de 90%.
- A regra de data compara a primeira data prometida e a primeira conclusão prevista do SKU, pois não há vínculo pedido–OP na fonte.
- A ausência de sell-out gera somente um sinal de baixa visibilidade e não altera o volume de vendas.

## 2026-09-28 — Etapa 4

- A priorização é uma soma de pesos por regra, mantidos em configuração e exibidos como evidência.
- A saída é uma ordenação de atenção, não uma solução ótima, recomendação autônoma ou liberação de produção.
- A confiança é baixa sem sell-out observado e média quando há observação, pois a cobertura B2B segue parcial.

## 2026-09-30 — Consolidação da interface

- React/Vite passa a ser a interface principal; Streamlit permanece como ferramenta interna de diagnóstico durante a transição.
- O frontend deve comunicar carregamento, erro, vazio e sucesso explicitamente.
- A navegação móvel usa drawer e não mantém largura fixa de sidebar.
- O detalhe do SKU apresenta evidências, origem e limitações sem transformar o ranking em recomendação autônoma.
- O pipeline da API é cacheado e invalidado por mudanças na fonte ou nas configurações, evitando leituras concorrentes repetidas do XLSM.

## 2026-09-30 — Contexto operacional do ranking

- A prioridade permanece em uma linha por SKU e recebe contexto operacional sem criar alocação por parceiro, canal ou semana.
- A data crítica é a menor data disponível entre a primeira promessa e a primeira conclusão prevista; sua origem é exposta separadamente.
- A lacuna operacional usa `máximo(0, carteira - estoque atual - produção aberta)` e não representa uma ordem recomendada.
- Ausência de sell-in ou sell-out é retornada como `null` e descrita em `missing_data`, nunca convertida silenciosamente em venda zero.

## 2026-09-30 — Impacto do dado do parceiro

- O feedback registra separadamente a ação humana e o efeito declarado dos dados do parceiro.
- Feedbacks antigos são preservados e marcados como `nao_utilizado`; nenhuma influência é inferida retroativamente.
- O indicador de decisões influenciadas soma apenas `aumentou_confianca` e `alterou_decisao`.
- O tempo de análise é opcional, inteiro e não negativo.

## 2026-10-01 — Publicação com Vercel e Supabase

- Frontend e backend são publicados como dois projetos Vercel do mesmo repositório, preservando a separação atual.
- SQLite continua como fallback local; `DATABASE_URL` seleciona PostgreSQL em ambientes publicados.
- Casos e histórico usam a mesma transação para impedir gravações parciais.
- O backend usa o Transaction Pooler do Supabase com prepared statements desabilitados, adequado a Functions de curta duração.
- O frontend conhece apenas `VITE_API_URL`; senhas e connection strings nunca usam o prefixo público `VITE_`.
- O XLSM permanece empacotado e somente leitura. Migração para Storage e autenticação ficam fora do protótipo.

## 2026-10-04 — Previsão de demanda e recomendação operacional

- A previsão mensal compara média móvel de três meses e sazonal ingênuo de doze meses para cada SKU.
- Os três últimos meses são preservados como holdout e o menor WAPE escolhe o modelo; histórico insuficiente não gera previsão zero.
- A tendência compara os três meses recentes com os três anteriores e usa uma faixa de 10% para evitar classificar pequenas oscilações.
- A recomendação usa o maior valor entre previsão do próximo mês e carteira para reduzir dupla contagem.
- Estoque de segurança, estoque atual, produção aberta e lote mínimo permanecem visíveis no cálculo.
- Capacidade por família é apenas um alerta de revisão, pois a fonte não comprova viabilidade por SKU e semana.
- O resultado é aditivo ao detalhe do SKU e não altera regras, score ou ranking oficial.
- Toda recomendação exige revisão humana e não cria ordem de produção.
- Feedbacks são registrados para validação, mas não retreinam o modelo automaticamente no V1.

## 2026-10-04 — Visão consolidada de previsão e recomendação

- A visão consolidada possui uma rota aditiva própria e somente leitura, sem ampliar o contrato do carregamento inicial do dashboard.
- O endpoint usa o pipeline cacheado e a função existente de recomendação; fórmulas não são duplicadas no frontend ou na rota.
- Todos os SKUs são exibidos, inclusive os não presentes no ranking, sem fabricar posição ou score.
- Busca, filtros e ordenação acontecem no navegador devido ao pequeno volume atual; paginação permanece fora do MVP.
- O detalhe continua centralizado no drawer e é carregado apenas quando solicitado.
- Quantidade sugerida permanece separada da prioridade oficial, capacidade não é tratada como garantia e revisão humana continua obrigatória.

## 2026-10-05 — Rotas e modularização da V2

- Cada página existente recebe uma rota real com `react-router-dom`, sem alterar contratos ou cálculos do backend.
- O detalhe do SKU passa do drawer para `/skus/:sku`, preservando as mesmas evidências, previsão, recomendação e revisão humana.
- Filtros relevantes usam query parameters para permitir compartilhamento e navegação pelo histórico.
- O Guia de uso permanece estático e não depende do carregamento da API.
- As páginas são separadas em módulos e carregadas sob demanda; o carregamento específico por rota das demais áreas fica para a Etapa 2.
- O frontend usa rewrite de SPA na Vercel para que deep links sejam atualizáveis e compartilháveis.
- Detalhe de parceiro e Validação continuam reservados às etapas que possuem dados e critérios próprios; nenhuma granularidade é criada apenas para preencher uma rota.

## 2026-10-05 — Central de validação da Semana 4

- A validação é uma rota aditiva e somente leitura; não altera pesos, limiares, modelos, ranking, regras ou a planilha.
- Linha de base da empresa (22 h/semana, MAPE 31%, 89% no prazo com meta de 96%, 78% de aderência) e meta de 8 h/semana aparecem separadas do que o protótipo recalcula.
- Pedidos no prazo e aderência ao plano ficam como não recalculáveis: a base não traz entregas nem produção realizada. O forecast comercial da base cobre somente meses futuros, por isso o MAPE informado também não é recalculado; o WAPE do protótipo é exibido como métrica diferente, não comparável diretamente.
- A baseline explícita da previsão é o último mês observado repetido no holdout. Ela não participa da seleção do modelo; empate conta como não superou.
- Os oito casos representativos são congelados em `config/validation_center.json` com o hash da planilha. Seis usam SKUs ou pares reais; dois são sintéticos porque a base não contém exemplo, e isso é exibido como lacuna.
- O tempo de análise registrado não é comparado com a linha de base antes de 20 registros com minutos.
- Exportação em CSV e impressão são feitas no navegador, sem dependência nova.

## 2026-10-05 — Comparação entre execuções

- Os snapshots passam a gravar um payload versionado com previsão e recomendação por SKU e cobertura por parceiro cadastrado, exatamente como calculados. Nenhum valor global é distribuído entre parceiros.
- A comparação só lê o que cada snapshot preservou. Execuções antigas são comparáveis apenas no ranking; as demais seções são recusadas com explicação, nunca recalculadas retroativamente.
- A diferença de score é decomposta em sinais adicionados, removidos e pesos alterados, usando os pesos gravados em cada execução. Quando a soma não fecha, o item é marcado como não explicado em vez de ocultado.
- A coluna `runs.comparison` é opcional. No PostgreSQL, o adaptador detecta a migração 002 e mantém o registro funcionando antes dela, sem o payload ampliado.
- A rota de comparação é `/api/run-comparisons`, porque `/api/runs/compare` seria capturada pela rota existente `/api/runs/{run_id}`.

## 2026-10-05 — Testes do frontend, acessibilidade e robustez

- Vitest 3.2 foi escolhido por ser compatível com o Vite 6.0.11 já fixado; o Vitest 5 exigiria atualizar o Vite, o que ficou fora do escopo. Testing Library, jsdom e axe-core são dependências apenas de desenvolvimento e não entram no bundle.
- `npm run check` executa typecheck, testes Vitest, testes `node --test` existentes, build e verificação de segredos no `dist/`. O build da Vercel continua sendo `npm run build`, sem executar testes.
- Os testes usam somente fixtures sintéticas tipadas pelos contratos do frontend. Um arquivo de campos compartilhado é validado nas duas pontas: fixtures no Vitest e API real no pytest.
- A acessibilidade é verificada com axe-core em todas as rotas, em viewport móvel e desktop, exigindo zero violações de qualquer gravidade. Como o jsdom não calcula cores nem layout, o contraste é testado a partir dos tokens do CSS e foi conferido com axe no Chromium real.
- `--slate-500` mudou de `#718096` (4,0:1 sobre branco) para `#5b6b7f` (≥ 5:1), cumprindo WCAG AA para texto pequeno. Nenhuma outra cor foi alterada.
- Cada rota fica dentro de um error boundary: resposta malformada ou chunk indisponível após um deploy não apagam a aplicação inteira.
