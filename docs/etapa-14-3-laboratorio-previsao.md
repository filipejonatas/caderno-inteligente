# Etapa 14.3 — API e bloco "Modelos candidatos" na Validação

Quarta subetapa do [plano da Etapa 14](plano-etapa-14-modelos-candidatos.md), depois do [backtest rolante](etapa-14-2-backtest-rolante.md). **Nenhuma saída oficial mudou:** o laboratório só lê o pipeline em cache. Um teste compara `/api/forecasts` antes e depois de chamar o laboratório, e `forecasting.py` continua intocado.

## Entregas

| Camada | Arquivo | Conteúdo |
|---|---|---|
| Biblioteca | [forecast_lab.py](../src/caderno_inteligente/forecast_lab.py) | monta a resposta: seleção, avaliação aninhada, grade de sensibilidade, limitações e natureza dos campos |
| Biblioteca | [rolling_backtest.py](../src/caderno_inteligente/rolling_backtest.py) | `sensitivity_grid`, `summarize_sensitivity` e memória de cálculo (`_run`) |
| Configuração | [config/forecast_engine.json](../config/forecast_engine.json) | chave nova `sensitivity` (`outer_windows` e `minimum_windows`) |
| API | [backend/forecast_lab.py](../backend/forecast_lab.py) | `GET /api/forecast-lab`, com cache e erro 422 para configuração inválida |
| Frontend | [ForecastLab.tsx](../frontend/src/components/ForecastLab.tsx) | bloco na aba "Modelos de previsão" da Validação |
| Contrato | `contract-keys.json`, `fixtures.ts`, `tests/test_frontend_contracts.py` | endpoint `forecastLab` nos dois lados do contrato |

## A resposta (`GET /api/forecast-lab`)

`selection` (modelos testados e SKUs que mudariam), `nested` (avaliação aninhada do padrão), `sensitivity` (`cells[]` e `summary`), `promotion_status = pendente`, `limitations`, `field_nature` e `requires_human_review`. Detalhes em [api.md](api.md).

## O que a tela mostra

Aba **Modelos de previsão** da Validação, abaixo de "Desempenho dos modelos" (que não mudou):

1. **Aviso:** "Nada foi promovido: as previsões oficiais seguem o motor atual" e quantos SKUs mudariam de modelo. O texto vem da API (`promotion_note`), para a tela não afirmar nada que o backend não afirme.
2. **Avaliação em meses já ocorridos:** baseline, motor atual e motor rolante, com erro ponderado (WAPE), viés assinado e SKUs melhores que a baseline.
3. **Grade de sensibilidade:** uma linha por combinação (períodos de teste × janelas mínimas), com a linha padrão marcada, a redução do erro e se os critérios foram atendidos. **A combinação que reprova aparece com o mesmo destaque das demais**, e o resumo diz "critérios atendidos em 5 de 6 combinações" e a faixa da redução (de −26,7% a +22,6%). Uma frase avisa que os períodos testados são os mesmos para todos os SKUs.
4. **Modelos testados:** SKUs escolhidos em cada motor e erro mediano; a descrição de cada modelo fica no "?".
5. Lista recolhida dos SKUs que mudariam de modelo, com link para o SKU.

O bloco busca os próprios dados. Enquanto calcula mostra "Calculando…"; se falhar, mostra "Laboratório indisponível no momento", com botão de nova tentativa, e o resto da Validação segue completo (mesmo padrão dos eventos no Início).

## Decisões de desenho

- **Grade em config:** `sensitivity.outer_windows` (padrão 1, 2, 3) e `sensitivity.minimum_windows` (padrão 1, 2), validados no carregamento. A grade é a que o resultado da 14.2 mostrou ser necessária; se a 14.5 quiser outras combinações, muda-se o JSON.
- **Cache:** o cálculo completo leva cerca de 3 a 4 segundos (6 avaliações aninhadas). Duas camadas reduzem: memória por `(modelo, treino, horizonte)` dentro do cálculo (o mesmo treino reaparece em várias origens e células; a grade caiu de cerca de 6 s para 2,4 s, com resultado idêntico, testado) e cache da resposta até a planilha ou a configuração mudarem. Chamadas simultâneas são serializadas por um lock.
- **Orçamento de volume intocado:** o bloco é feito de tabelas e "?" e coube em `volume-budget.json` sem alterar nenhum limite. O `/guia` não mudou (nenhum termo novo no glossário).
- **Exportação CSV da Validação** não inclui o laboratório (é material de decisão do motor, não da validação do processo). Pode entrar depois, se pedirem.

## Resultado exibido (base atual, hash `03fa0ed4…803f`)

Os números são os da [14.2](etapa-14-2-backtest-rolante.md): no padrão, ganho de 21,6% e critérios atendidos; critérios atendidos em 5 das 6 combinações da grade, com a de 3 períodos de teste e 2 janelas mínimas revertendo o resultado (−26,7%). Observação que a grade deixa à vista: com 1 período de teste, `minimum_windows` 1 e 2 dão o mesmo resultado (a restrição não pesa); e nesse último trimestre a baseline (7,97%) teve erro menor que o motor atual (9,34%).

**Isto continua não sendo veredito de promoção.** Segue valendo o que a 14.2 registrou: amostra efetivamente pequena e escolha de `minimum_windows` feita depois de ver resultados. A decisão é da 14.5, com aprovação.

## Testes e verificação

- `pytest`: 372 testes passam (351 + 21 desta etapa: grade, resumo, memória do cálculo, validação da config nova, API, cache e erro 422).
- `npm run check`: typecheck, 353 testes Vitest (344 + 9), 21 testes `node --test`, build e `check:bundle` passam.
- **API:** o laboratório não muda `/api/forecasts`; contagens por motor somam 50; o bloco aninhado coincide com a célula padrão da grade; sem NaN; cache invalida quando a fonte ou a configuração mudam; configuração inválida devolve 422.
- **Contrato:** `forecastLab` verificado contra a API real (`tests/test_frontend_contracts.py`) e contra a fixture.
- **Tela:** linha padrão marcada uma vez; combinação que reprova visível; viés negativo assinado; ausência continua "Não disponível", nunca zero; falha e carregamento do laboratório não derrubam a validação; nova tentativa funciona.
- **Navegador:** conferido a degradação (API sem a rota → aviso e resto da página intacto) e o caso com dados (resposta real do endpoint injetada no `fetch`, depois "Tentar novamente"): as quatro tabelas renderizam. Não foi possível subir a API e o frontend deste trabalho porque as portas 8000 e 5173 estavam ocupadas por servidores de outra conversa, que não parei.

## Limitações

- Primeira chamada após subir a API (ou após mudar a planilha) leva alguns segundos; em ambiente serverless com limite curto de tempo, convém aquecer a rota ou aumentar o limite. A medir no deploy.
- A grade é informativa: não decide nada, e os critérios continuam fixados em config.
- O erro de seleção por SKU (lista de SKUs que mudariam) é otimista; para comparar motores vale a avaliação aninhada.

## Próximo passo

14.4 (opcional) — faixas de previsão P10–P90; ou, sem ela, direto para a 14.5: decisão de promoção com a grade inteira e aprovação explícita.
