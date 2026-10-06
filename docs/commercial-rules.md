# Regras comerciais — Etapa 4

Estas regras são demonstrativas e independentes das sete regras operacionais. Não alteram score, ranking, previsão ou recomendação de produção. Os limites não foram validados pela empresa.

## Granularidade e origem

- Chave mensal: `Cliente + SKU + Mês` em Sell_In/Sell_Out, normalizada para mês civil.
- Join externo `one_to_one` apenas nas chaves reais. Chaves duplicadas, valores negativos/não finitos e vínculos órfãos bloqueiam a análise comercial.
- O universo de pares é a união dos vínculos de Sell_In, Sell_Out e Carteira_Pedidos. Não existe produto cartesiano de parceiros e produtos.
- Produtos fornece somente SKU/nome; Parceiros_Canais fornece cadastro/região/canal. Não há leitura de quantidades de estoque global, previsão global ou capacidade para distribuir por parceiro.
- Cada par expõe histórico mensal, natureza declarada do sell-out, estoque estimado e pedidos identificados por código/data/status.
- Quantidade de carteira representa pedidos registrados não encerrados, sem inferir saldo após entregas parciais. Status cancelado, concluído, entregue e faturado são excluídos. Na fonte atual, todos os 53 pedidos estão Confirmados.
- Ausência em sell-in/out/estoque permanece `null`; zero observado permanece zero. Carteira zero significa ausência de pedido no recorte de documentos carregado, não ausência de vendas.

## Referência e cálculos

A referência reproduzível é o maior mês de Sell_In/Sell_Out. **Não é a data atual.** Na base atual, é agosto/2026. A atualidade mede diferenças contra esse mês; não afirma que o dado esteja atualizado em outubro/2026.

A janela recente padrão é junho–agosto/2026. Totais de sell-in e sell-out apresentam seus próprios meses observados. A diferença comparável usa somente a interseção de meses com ambas as quantidades não nulas:

`diferença = soma(sell-in nos meses comparáveis) − soma(sell-out nos mesmos meses)`.

Não se subtraem totais de períodos distintos. A proporção usa `abs(diferença) / sell-out comparável`. Se sell-out comparável for zero, a proporção é nula, sem infinito; divergência exige diferença absoluta mínima.

O estoque estimado é o valor do último registro com sell-out, não a soma dos estoques mensais. Sua data é exposta separadamente. Se o estoque desse registro estiver ausente, não se substitui silenciosamente pelo de um mês anterior.

`cobertura estimada em dias = estoque estimado / (média mensal de sell-out observado / 30)`.

O mês de 30 dias é uma aproximação explícita, não uma previsão. Média zero ou ausente deixa cobertura nula. Zero observado entra na média. Nunca se usa estoque do CD, giro global ou forecast global nesse cálculo.

## Configuração

Arquivo independente: `config/commercial_thresholds.json`. Lido em cada consulta comercial; não precisa invalidar o cache do pipeline operacional.

| Parâmetro | Padrão | Significado |
|---|---:|---|
| recent_months | 3 | Meses da janela de análise |
| minimum_sell_out_months | 3 | Mínimo de meses observados para recomendar |
| maximum_age_months | 1 | Idade tolerada contra a referência da base |
| reposition_coverage_days | 30 | Cobertura máxima para avaliar reposição |
| excess_coverage_days | 90 | Cobertura mínima do sinal de excesso |
| low_monthly_sell_out | 30 | Giro mensal máximo para sinal de excesso |
| minimum_excess_stock | 100 | Estoque estimado mínimo para excesso |
| divergence_ratio | 0,5 | Proporção mínima de divergência |
| minimum_divergence_quantity | 50 | Diferença absoluta mínima de divergência |

## Sinais e ações

- `INSUFFICIENT_PARTNER_DATA`: menos meses recentes que o mínimo, estoque ausente ou natureza não declarada. Não recomenda reposição.
- `STALE_PARTNER_DATA`: último sell-out antigo contra a referência, ou mês sem observação na janela recente. Solicita atualização; bloqueia reposição.
- `SELLIN_SELLOUT_DIVERGENCE`: amostra comparável mínima e diferença absoluta/proporcional relevante. É investigação, não prova de erro ou previsão de vendas.
- `REPOSITION_OPPORTUNITY`: amostra suficiente, sem descontinuidade, giro positivo e cobertura estimada até o limite. Ação: avaliar reposição; não há quantidade autorizada.
- `PARTNER_EXCESS_RISK`: estoque estimado mínimo, giro baixo e cobertura alta ou giro zero observado. Ação: monitorar estoque.

Precedência da ação: atualizar dado antigo/descontínuo → dados insuficientes → investigar divergência → avaliar reposição → monitorar estoque.

Monitoramento também é a ação de acompanhamento quando há dados suficientes e nenhuma exceção. Nesse caso, a justificativa diz explicitamente que monitorar não afirma excesso.

As cinco ações possíveis são: Avaliar reposição; Monitorar estoque do parceiro; Investigar divergência; Solicitar atualização dos dados; Sem recomendação por dados insuficientes. Todas exigem revisão humana.

## Rótulos de ação do desafio

As cinco ações acima continuam sendo a fonte. Um segundo campo, `challenge_action`, traduz cada par para o vocabulário do desafio sem alterá-las: `avaliar_reposicao` → **Repor**; `monitorar_estoque` → **Monitorar** (ou **Recomendar recompra** quando o par vende mas está sem sell-in acima do próprio ritmo); `investigar_divergencia`, `solicitar_atualizacao` e `dados_insuficientes` → **Investigar**. No nível do parceiro, **Priorizar parceiro** exige 2 ou mais pares **Repor**, com pelo menos um SKU entre os 10 primeiros da fila de atenção. Parceiro sem sell-out suficiente nunca recebe oportunidade inferida. Detalhes e limiares em [Etapa 13](etapa-13-rotulos-de-acao.md).

## Decisões por parceiro

O feedback existente possui SKU e efeito genérico do dado de parceiros, mas não código do parceiro. A API retorna atribuição indisponível e itens nulos. Não associa feedback a todos os parceiros que compartilham o SKU. Não foi criada migração ou alteração no contrato de feedback.
