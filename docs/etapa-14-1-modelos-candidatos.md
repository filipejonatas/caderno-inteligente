# Etapa 14.1 — Modelos candidatos

Segunda subetapa do [plano da Etapa 14](plano-etapa-14-modelos-candidatos.md), depois da [linha de base](etapa-14-0-linha-de-base.md). **Nenhuma saída oficial mudou:** `forecasting.py` não foi editado, não há endpoint novo e nada novo é chamado pelo pipeline. Os candidatos existem como biblioteca testada, à espera do backtest rolante (14.2).

## Entregas

| Arquivo | Conteúdo |
|---|---|
| [forecast_candidates.py](../src/caderno_inteligente/forecast_candidates.py) | os 6 candidatos, registro (`CANDIDATES`), ordem de simplicidade, `run_candidate` e `applicable_candidates` |
| [forecast_engine_config.py](../src/caderno_inteligente/forecast_engine_config.py) | carregador e validação de `config/forecast_engine.json` (campos desconhecidos são rejeitados) |
| [config/forecast_engine.json](../config/forecast_engine.json) | candidatos habilitados, parâmetros do backtest rolante, margem de parcimônia e critérios de promoção |
| `tests/test_forecast_candidates.py`, `tests/test_forecast_engine_config.py` | 38 testes novos |

## Os candidatos

Todos recebem a série mensal contínua e os meses-alvo, devolvem previsões ≥ 0 ou `None` quando faltam dados (nunca zero inventado) e estimam parâmetros só com a série recebida, em grades fixas e determinísticas.

| Ordem | Código | Em uma frase | Histórico mínimo |
|---|---|---|---|
| 1 | `moving_average_3` | média dos últimos 3 meses (atual, reaproveitado) | 3 |
| 2 | `seasonal_naive_12` | repete o mesmo mês do ano anterior (atual, reaproveitado) | 12 |
| 3 | `ses` | nível que pesa mais o recente; α ∈ {0,1 … 0,9} escolhido pelo menor erro de 1 mês à frente no treino | 6 |
| 4 | `combo_ma_sn` | média simples dos dois primeiros | 12 |
| 5 | `seasonal_level` | mês do ano anterior × crescimento do nível (média dos 3 últimos meses ÷ a dos mesmos 3 meses há um ano); razão limitada a 0,5–2,0 | 15 |
| 6 | `holt_damped` | nível + tendência amortecida; α, β, φ em grade de 45 combinações pelo menor erro de 1 passo | 9 |

Detalhes que valem registro:

- **Mínimos por modelo vêm da matemática de cada um.** O de `seasonal_level` (15) é o treino da primeira janela rolante em 24 meses, então os 50 SKUs da base atual são elegíveis a todos os candidatos nas 3 janelas.
- **Desempate dentro de `ses` e `holt_damped`:** vence o primeiro da grade (menor α, depois menor β, depois menor φ) em caso de SSE igual. Isso torna o resultado reprodutível.
- **Holt:** inicialização com nível = 1º mês e tendência = (4º − 1º)/3; previsão do passo h = nível + (φ + φ² + … + φʰ) × tendência.
- **`SIMPLICITY_ORDER`** (a coluna "Ordem") é a regra de desempate e de parcimônia da 14.2.
- **`SEASONAL_CODES`** (`seasonal_naive_12`, `combo_ma_sn`, `seasonal_level`) marca os candidatos que já repetem o padrão do ano anterior. A 14.5 usa isso para estender a regra de não contar evento duas vezes, hoje restrita a `seasonal_naive_12` em `events.py`.
- **Croston/SBA ficou fora** por decisão da 14.0 (nenhum mês zerado na base).

## Configuração (`config/forecast_engine.json`)

- `engine`: só `"v1"` é aceito por enquanto. O motor rolante só passa a existir se a 14.5 aprovar a promoção; uma chave que não faz nada seria um risco silencioso, então qualquer outro valor é rejeitado.
- `candidates`: precisa conter os dois modelos atuais (sem eles não há comparação com o v1), sem repetidos e sem códigos desconhecidos.
- `rolling` (janelas, passo, horizonte, treino mínimo ≥ 6), `parsimony_margin` (0,05) e `promotion` (ganho relativo mínimo de WAPE 0,05; piora máxima de viés 2 p.p.) já estão fixados aqui, antes de qualquer resultado, e só serão lidos pela 14.2 e pela 14.5.
- O arquivo vai no deploy sem mudança (`vercel.json` já inclui `config/**`).

## Testes e verificação

- **Respostas calculadas à mão:** SES com empate de α (nível 11), SES com degrau (19,99), razão sazonal (44, 48, 60), teto da razão (80), piso (20) e combinação (15; 15,67; 16,22).
- **Propriedades:** série constante não gera tendência; Holt cresce mas amortecido e nunca fica negativo; mínimo de histórico respeitado sem inventar valor; determinismo; a série de entrada não é alterada.
- **Base real:** todos os candidatos aplicáveis produzem 3 valores finitos ≥ 0 para os 50 SKUs.
- **Regressão:** a previsão oficial é idêntica, byte a byte, ao `snapshot-previsao-v1.json` da 14.0.
- **Validação de configuração:** 15 casos inválidos rejeitados com mensagem; o arquivo versionado carrega com os valores do plano.
- `pytest`: 312 testes passaram (274 da linha de base + 38 novos).

## Limitações

- Não se mediu ainda se algum candidato é melhor que os atuais: isso é a 14.2. Nada aqui autoriza afirmar ganho.
- `seasonal_level` assume que o crescimento do nível de 3 meses se mantém nos 3 meses seguintes, e a razão sazonal vem de uma única observação do ano anterior. Por isso há o teto e o piso, e por isso ele só vence se superar os mais simples por margem.
- Holt amortecido usa grade fixa e inicialização simples; em séries muito curtas (9 meses) a tendência inicial é ruidosa. A parcimônia da 14.2 limita o efeito.

## Próximo passo

14.2 — `rolling_backtest.py`: origens rolantes, seleção por WAPE agrupado com parcimônia, viés e avaliação aninhada.
