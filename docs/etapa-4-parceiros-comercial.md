# Etapa 4 — Visão parceiro–SKU e recomendação comercial

## Resultado

Implementado núcleo comercial separado, cinco sinais configuráveis, quatro APIs aditivas, lista/detalhe de parceiros e contexto comercial no detalhe do SKU.

Nenhuma alteração em score, ranking oficial, sete regras operacionais, ingestão/normalização do Excel, previsão por SKU, recomendação operacional ou persistência. Os dados globais de estoque do CD, produção, capacidade e forecast não são distribuídos aos parceiros. Não foram instaladas dependências, alterados segredos ou realizados deploys.

## Dados verificados

- 8 parceiros/canais cadastrados, incluindo canais diretos.
- 50 pares parceiro–SKU com sell-in/out mensal, 12 meses e 600 chaves mensais reais após união por chave.
- 95 vínculos reais na união de sell-in/out e carteira; 45 possuem somente carteira, sem imputação de sell-out ou estoque.
- Os 53 pedidos permanecem rastreáveis por código, parceiro, SKU, quantidade, data prometida e status.
- Referência da base: agosto/2026; janela recente padrão: junho–agosto/2026.

Sugestões na base, usando os limites demonstrativos atuais:

| Ação | Pares |
|---|---:|
| Avaliar reposição | 12 |
| Investigar divergência | 1 |
| Monitorar estoque do parceiro | 37 |
| Sem recomendação por dados insuficientes | 45 |

Um dos pares apresenta sinal de possível excesso. Monitoramento dos demais não afirma excesso. Esses resultados não são decisões comerciais aprovadas.

O hash SHA-256 do XLSM foi preservado:

`03fa0ed400aa3f8e14de8f8232cd12727a54c85089a36672f009cae37b78803f`.

## Núcleo e APIs

`partner_insights.py` une exclusivamente chaves existentes. Comparações de sell-in/out usam a interseção dos meses com ambas as quantidades observadas. Estoque é o estimado do último registro de sell-out, nunca soma histórica ou estoque do CD.

A cobertura aproxima dias por `estoque estimado / (média mensal observada / 30)`. Giro zero ou ausente produz cobertura nula, sem infinito. A reposição exige giro positivo, estoque estimado, natureza declarada, amostra mínima e continuidade recente.

Cinco sinais: `REPOSITION_OPPORTUNITY`, `PARTNER_EXCESS_RISK`, `SELLIN_SELLOUT_DIVERGENCE`, `STALE_PARTNER_DATA`, `INSUFFICIENT_PARTNER_DATA`.

APIs novas:

- `GET /api/partners`
- `GET /api/partners/{codigo}`
- `GET /api/partners/{codigo}/skus`
- `GET /api/commercial-recommendations`

Listas filtráveis por parceiro, SKU, região, canal, ação e qualidade do dado; envelopes com paginação `limit`/`offset`, referência, limiares, natureza dos campos e limitações. Métodos e fórmulas estão em `docs/commercial-rules.md`; contrato em `docs/api.md`.

## Interface

- `/parceiros`: KPIs, filtros por região/canal, ordenação e links para todos os canais cadastrados. A cobertura é medida a partir dos registros, não copiada da declaração cadastral de cobertura completa.
- `/parceiros/:codigo`: resumo, cobertura, referência, matriz de SKUs, filtro de SKU exato/ação/qualidade, paginação e evidências expansíveis.
- Evidências mostram histórico mensal com quantidades, estoque estimado, natureza declarada, períodos comparáveis e pedidos identificados.
- `/skus/:sku`: seção Contexto dos parceiros, com consulta independente. Uma falha comercial não impede o detalhe operacional de abrir.
- Recomendação comercial é rotulada separadamente da operacional; nenhuma quantidade é autorizada.

## Arquivos

### Modificados

- `backend/main.py`: somente registro do router aditivo.
- `frontend/src/App.tsx`: rota do parceiro e carregamento próprio da lista.
- `frontend/src/api.ts`: quatro métodos comerciais aditivos.
- `frontend/src/App.css`: matriz, evidências, filtros e responsividade.
- `frontend/src/pages/B2BPage.tsx`: nova lista comercial de parceiros.
- `frontend/src/pages/SkuDetailPage.tsx`: contexto comercial separado.
- `frontend/scripts/test-decision-journey.mjs`: dois testes comerciais de renderização.
- `docs/api.md`: contrato dos endpoints novos.

### Criados

- `src/caderno_inteligente/partner_insights.py`
- `backend/partners.py`
- `config/commercial_thresholds.json`
- `frontend/src/types-commercial.ts`
- `frontend/src/components/CommercialMatrix.tsx`
- `frontend/src/components/PartnerSkuContext.tsx`
- `frontend/src/pages/PartnerDetailPage.tsx`
- `tests/test_partner_insights.py`
- `tests/test_partners_api.py`
- `docs/commercial-rules.md`
- `docs/etapa-4-parceiros-comercial.md`

## Validação

```powershell
# Raiz
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider
# 90 passed: 61 anteriores + 29 novos

cd frontend
node --test scripts/test-page-data.mjs scripts/test-decision-journey.mjs
# 12 passed
npm run check
# Typecheck + build aprovados

cd ..
git diff --check
# Aprovado
```

Testes incluem: proteção contra produto cartesiano, origem real, imutabilidade dos DataFrames e fonte, ausência versus zero, interseção de períodos, estoque/giro insuficientes, continuidade/idade, excesso, divergência, configuração, órfãos/duplicatas/valores inválidos, filtros, paginação, códigos com acento, 404/422 e preservação dos contratos operacionais.

A execução conjunta inicialmente atingiu o timeout da ferramenta após concluir os testes; `npm run check` foi executado separadamente e aprovado. A suíte Python completa também foi reexecutada e aprovada após os ajustes finais de justificativa.

### Navegador local

20 verificações: cinco recortes em 390, 768, 1024 e 1440 pixels. Recortes: lista; KA-01; Loja própria com código codificado; KA-01 filtrado por dados insuficientes; contexto de CI-0041. Nenhum erro de carga ou overflow horizontal do documento foi encontrado. Rolagem horizontal de tabelas é intencional e restrita à sua região.

Como a janela interna não permite menos de 700 pixels, as larguras exatas foram medidas em iframes de mesma origem com a aplicação e API reais. Isso verifica DOM/geometria, não substitui revisão visual e interação com usuários. Não foi gerado screenshot nem executado teste completo de interação nativa nesta etapa.

## Limitações importantes

1. **Decisões por parceiro não são atribuíveis.** O feedback atual possui SKU e efeito genérico do dado do parceiro, sem código de parceiro. A API e a tela mostram indisponibilidade; não associam decisões a todos os parceiros do SKU. Essa parte do escopo permanece limitada até existir vínculo explícito no modelo, cuja migração não foi realizada.
2. **Atualidade é relativa à referência da base.** Agosto/2026 não é outubro/2026. O sistema não afirma atualização até a data atual; os sinais identificam atraso/descontinuidade dentro da referência observada.
3. Estoque do parceiro é estimado, não auditado. Cobertura usa mês aproximado de 30 dias. Limiares são hipóteses demonstrativas sem aprovação da empresa.
4. Cadastro de cobertura completa de canais diretos não substitui registros ausentes. Esses canais podem aparecer sem sell-out observado e com carteira vinculada.
5. Carteira representa quantidade registrada, sem inferir saldo de entrega parcial nem alocar produção. Pedido não é sell-out.
6. Todas as sugestões exigem revisão humana. Monitoramento sem exceção não equivale a risco de excesso; reposição não contém quantidade autorizada.
7. Lista de parceiros e contexto no SKU carregam lote máximo de 200 e informam eventual truncamento; detalhe do parceiro pagina 50 vínculos. A API permite até 500 por chamada.
8. O núcleo comercial é recalculado em cada leitura a partir do dataset já cacheado. Não houve cache comercial novo, autenticação ou integração real.

## Deploy manual — não executado

Esta etapa requer **backend e frontend**, diferentemente da etapa 3.

1. Revisar os arquivos e executar as validações acima.
2. Incluir no backend `backend/partners.py`, o módulo Python e `config/commercial_thresholds.json`. A configuração atual de empacotamento já contempla `config/**` e `src/caderno_inteligente/**`; o router é importado por `backend/main.py`.
3. Publicar o backend conforme `docs/deploy-vercel-supabase.md`, mantendo as variáveis existentes. Não há nova variável, segredo ou migração de banco.
4. Validar health, `/api/partners` (8 registros na base atual), parceiro KA-01, matriz e filtros; confirmar acesso aos endpoints antigos.
5. Publicar o frontend: Root Directory `frontend`, build `npm run build`, saída `dist`. Manter `VITE_API_URL` e o rewrite SPA existentes.
6. Validar `/parceiros`, deep link de KA-01 e Loja própria, SKU CI-0041, filtros, paginação, estados vazios/erro e evidências mensais.

Nenhum deploy ou alteração de segredos foi feito.
