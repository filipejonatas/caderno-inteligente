# Etapa 5 — Central de validação da Semana 4

## Resultado

Foi criada a página `/validacao` e a API aditiva `GET /api/validation/summary`. A página reúne a evidência de aplicabilidade em um só lugar: comparação com o processo atual, avaliação da previsão contra uma baseline explícita, oito casos representativos congelados, comportamento seguro, falhas conhecidas e histórico de ajustes. O resumo pode ser exportado em CSV ou impresso, sem dependência nova.

Nada foi alterado em score, ranking oficial, sete regras operacionais, pesos, limiares, ingestão/normalização do Excel, previsão por SKU, recomendação operacional, sinais comerciais ou persistência. Nenhum dado global é distribuído por parceiro. Não houve deploy, alteração de segredos, nova variável de ambiente nem migração de banco.

O hash SHA-256 do XLSM foi preservado:

`03fa0ed400aa3f8e14de8f8232cd12727a54c85089a36672f009cae37b78803f`.

## Resultados na base atual

### Comparação com o processo atual

| Indicador | Informado pela empresa | Recalculado no protótipo | Meta |
|---|---:|---|---:|
| Tempo de análise | 22 h/semana | Não disponível: 0 registros com minutos (mínimo 20) | 8 h/semana |
| Erro do forecast | MAPE 31% | WAPE ponderado 6,9% — **métrica diferente, não comparável** | — |
| Pedidos no prazo | 89% | Não recalculável: sem histórico de entregas | 96% |
| Aderência ao plano | 78% | Não recalculável: sem produção realizada | — |

O forecast comercial da base cobre somente outubro/2026 em diante, então o MAPE informado não pode ser recalculado. O WAPE exibido mede o modelo estatístico do protótipo sobre faturamento.

### Previsão contra baseline

Holdout dos três últimos meses (junho a agosto de 2026), 50 SKUs elegíveis e 0 com dados insuficientes.

| Modelo | Papel | WAPE mediano | WAPE ponderado | Escolhido em |
|---|---|---:|---:|---:|
| Média móvel de 3 meses | candidato | 7,1% | 7,6% | 34 SKUs |
| Sazonal ingênuo de 12 meses | candidato | 10,2% | 11,7% | 16 SKUs |
| Modelo selecionado por SKU | selecionado | 6,4% | 6,9% | — |
| Último mês observado | baseline | 7,5% | 8,0% | — |

**Falha visível:** o modelo selecionado não superou a baseline em 16 dos 50 SKUs. A página lista esses SKUs.

### Casos congelados

8 de 8 passaram. Seis usam SKUs ou pares reais: CI-0005, CI-0044, CI-0041, KA-01/CI-0011, E-commerce/CI-0009 e CI-0014. Dois são sintéticos porque a base não contém exemplo:

- **VC-01:** nenhum SKU da base tem, ao mesmo tempo, ruptura, carteira positiva e nenhuma OP;
- **VC-05:** todos os SKUs da base possuem histórico suficiente para a previsão.

Os casos sintéticos passam pelas mesmas funções de regras, previsão e recomendação. A página os marca como entrada sintética e os lista como lacuna de cobertura.

### Comportamento seguro

7 de 7 verificações executadas foram aprovadas:

- ausência de sell-out reduz a confiança;
- holdout com demanda zero não gera WAPE;
- forecast insuficiente não vira quantidade;
- capacidade agregada exige revisão e não é tratada como garantia;
- todas as 50 recomendações exigem revisão humana;
- dado ausente não vira zero nem cobertura inventada;
- SKU inexistente retorna 404.

O erro de API é coberto por teste automatizado do frontend e aparece como "coberto por teste", não como executado.

## Método

- **Baseline:** repete o último mês antes do holdout e não participa da seleção do modelo. Empate conta como "não superou".
- **WAPE ponderado:** soma dos erros absolutos dividida pela soma da demanda real, considerando apenas SKUs com demanda no holdout. A mediana é calculada sobre os SKUs com WAPE definido.
- **Consistência com a previsão:** o WAPE do modelo selecionado é idêntico ao `backtest_wape` de `/api/forecasts`, o que está garantido por teste.
- **Congelamento dos casos:** os casos ficam em `config/validation_center.json`, com data e hash da planilha. Se a planilha mudar, a página avisa que os casos precisam ser revisados. Os casos não alimentam pesos, limiares nem modelos.
- **Tempo de análise:** vem dos minutos opcionais do registro de decisões. Antes de 20 registros, nenhum ganho é afirmado.

## Arquivos

### Criados

- `src/caderno_inteligente/validation_center.py`
- `backend/validation.py`
- `config/validation_center.json`
- `frontend/src/pages/ValidationPage.tsx`
- `frontend/src/types-validation.ts`
- `frontend/src/validation-export.ts`
- `frontend/scripts/test-validation-page.mjs`
- `tests/test_validation_center.py`
- `tests/test_validation_api.py`
- `docs/etapa-5-validacao.md`

### Modificados

- `backend/main.py`: somente o registro do router aditivo.
- `frontend/src/App.tsx`: rota `/validacao`.
- `frontend/src/api.ts`: método `validationSummary`.
- `frontend/src/components.tsx`: item de navegação e ícone.
- `frontend/src/types.ts`: `PageId` `validation`.
- `frontend/src/pages/GuidePage.tsx`: descrição da página no guia.
- `frontend/src/App.css`: estilos da página e regras de impressão.
- `frontend/scripts/test-page-data.mjs`: leitura dedicada da validação.
- `README.md`, `docs/api.md`, `docs/architecture.md` e `docs/decisions.md`.

## Validação

```powershell
# Raiz
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider
# 106 passed: 90 anteriores + 16 novos

cd frontend
node --test scripts/test-validation-page.mjs scripts/test-page-data.mjs scripts/test-decision-journey.mjs
# 16 passed
npm run check
# Typecheck + build aprovados
```

Na sessão de desenvolvimento, o sandbox bloqueava a pasta temporária padrão do pytest. Por isso a suíte foi executada com `--basetemp` apontando para uma pasta gravável. Sem essa opção, os testes que usam `tmp_path` falham com `PermissionError` antes de executar, por causa do ambiente e não do código.

Navegador local, com a API e o frontend reais:

- em 375, 1024 e 1440 pixels, não houve overflow horizontal do documento nem texto truncado;
- o console não registrou erros;
- a exportação CSV foi testada por teste unitário, mas o download não foi acionado no navegador.

## Limitações

1. Pedidos no prazo e aderência ao plano não são recalculáveis com a base atual.
2. O WAPE do protótipo e o MAPE da empresa medem coisas diferentes. A página não os compara diretamente.
3. O mesmo holdout escolhe e avalia o modelo, então o WAPE selecionado tende a ser otimista. Três meses por SKU formam uma amostra pequena.
4. Dois dos oito casos são sintéticos. Eles provam o comportamento das regras, não a ocorrência na operação.
5. Os casos verificam coerência com a especificação, não ganho de negócio. As saídas esperadas foram escritas a partir das regras do PRD, pela mesma equipe que implementou as regras.
6. O tempo de análise depende de registros manuais. Hoje a amostra é insuficiente e nenhum ganho é afirmado.
7. Decisões continuam não atribuíveis a parceiros específicos, porque o feedback não registra o código do parceiro.
8. O histórico de ajustes é mantido manualmente na configuração, com referência aos documentos de origem.

## Deploy manual — não executado

1. Revisar os arquivos e executar as validações acima.
2. **Backend:** publicar com a configuração atual. `vercel.json` já inclui `config/**` e `src/caderno_inteligente/**`, e `backend/validation.py` é importado por `backend/main.py`. Não há variável, segredo ou migração nova.
3. Validar `https://URL-DO-BACKEND/api/health` e `https://URL-DO-BACKEND/api/validation/summary`. Na base atual, a rota deve mostrar 8/8 casos, `source_matches_frozen=true` e 16 SKUs sem ganho sobre a baseline. Confirmar também os endpoints antigos.
4. **Frontend:** Root Directory `frontend`, build `npm run build`, saída `dist`. Manter `VITE_API_URL` e o rewrite SPA.
5. Validar o deep link `/validacao`, a atualização da página, a exportação CSV, a impressão e os estados de carregamento e erro.
6. Em produção, o tempo de análise vem do Supabase. Enquanto houver menos de 20 decisões com minutos, a página mostra a amostra como insuficiente.
