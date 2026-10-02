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
