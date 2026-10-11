# Pacote de exemplo: atualização de outubro/2026

> **EXEMPLO FICTÍCIO.** `atualizacao-2026-10.xlsx` não é dado real. Foi gerado por `scripts/build_example_update.py` a partir da base de 14/09/2026,
> por regras fixas e sem sorteio, só para demonstrar o envio de planilha pela tela. A aba `LEIA_ME` do arquivo repete este aviso
> e a prévia do upload o mostra como "arquivo de exemplo fictício".

## O que o arquivo contém

Oito abas, no mesmo layout da planilha de origem (título na linha 1, cabeçalho na linha 3, dados a partir da linha 4), mais o `LEIA_ME`:

| Aba | Conteúdo |
|---|---|
| `Vendas_24m`, `Sell_In`, `Sell_Out` | só **setembro/2026** (meses fechados). O envio acrescenta o mês e preserva os 24 anteriores. |
| `Estoque_Atual`, `Carteira_Pedidos`, `Ordens_Producao`, `Capacidade_Semanal` | fotografias de **12/10/2026** (segunda-feira), que passa a ser a data de planejamento. |
| `Forecast_Comercial` | Nov/26, Dez/26 e Jan/27. |

Cadastros (`Produtos`, `Lead_Times`, `Parceiros_Canais`, `Calendario_Eventos`) não vão no arquivo e ficam como estão (D1).

## Regras de geração

`NEW_REFERENCE = 12/10/2026`, `SHIFT = 28 dias`, `MÊS = 2026-09`. Arredondamento: meio para cima.

- **`Vendas_24m` 2026-09:** para cada par (SKU, Cliente/Canal) de 2026-08, `Q = round(Q[2025-09] × f)`, com
  `f = ΣQ[2026-06..08] / ΣQ[2025-06..08]` do SKU, limitado a [0,5; 2,0] (denominador 0 dá `f = 1`). O preço é o do par em 2026-08 e o valor
  faturado é `Q × preço` com 2 casas.
- **`Sell_In` e `Sell_Out` 2026-09:** só os pares que existem em 2026-08. `Q = round(Q[2026-08] × r)`, com
  `r = vendas do SKU em 2026-09 gerado / vendas do SKU em 2026-08` (1 se o denominador for 0).
  `Estoque estimado cliente = max(0, estoque[2026-08] + sell_in[09] − sell_out[09])`. A `Natureza do dado` é copiada de 2026-08.
- **`Estoque_Atual`:** `estoque = max(0, estoque de 14/09 + Σ quantidade das OPs abertas com conclusão antes de 12/10 − consumo)`, com
  `consumo = round(vendas do SKU em 2026-09 / 30 × 28)`. `Cobertura dias = round(estoque / (consumo / 28))` quando o consumo é maior que 0;
  nos demais casos, e nas outras colunas, o valor é copiado.
- **`Carteira_Pedidos`:** pedidos com data prometida a partir de 12/10 seriam mantidos (na base, nenhum). Cada pedido original é reemitido como
  `PV-EX-0001…`, na ordem original, com data prometida + 28 dias e as demais colunas copiadas.
  *Ajuste em relação ao plano:* um pedido de 13/09 cairia em 11/10, antes da referência; por isso a data nunca fica antes de 12/10.
- **`Ordens_Producao`:** OPs abertas com conclusão antes de 12/10 passam a "Concluída" e ficam para auditoria. As demais são mantidas;
  "Planejada" ou "Liberada" com início antes de 12/10 passam a "Em produção". Cada OP concluída é reemitida como `OP-EX-0001…`, com
  início e conclusão + 28 dias (o início nunca fica antes de 12/10) e status "Planejada".
- **`Capacidade_Semanal`:** as semanas a partir de 12/10 são copiadas. As 4 semanas que faltam (04, 11, 18 e 25/01/2027) repetem, por linha, a
  última semana observada, com `Ordens planejadas = 0`, `Capacidade comprometida = Compromissos base`,
  `Capacidade disponível = máxima − compromissos base` e `Ocupação = compromissos base / máxima`. Resultado: 16 semanas por linha.
- **`Forecast_Comercial`:** "Nov/26" e "Dez/26" são mantidos, "Out/26" sai e "Jan/27" = `round((Nov + Dez) / 2)`, com a origem de "Dez/26".

## Avisos esperados na prévia

- `EXAMPLE_FILE`: o arquivo é fictício.
- `PRODUCT_STOCK_DIVERGENCE`: `Produtos.Estoque atual` (cadastro, não enviado) difere do novo `Estoque_Atual`. O cálculo usa `Estoque_Atual`.

## Como regenerar e conferir

```
python scripts/build_example_update.py            # grava o arquivo
python scripts/build_example_update.py --check    # sai com 0 se o conteúdo gravado bate com as regras
```

`--check` compara o conteúdo das abas (hash do valor das células), não os bytes do ZIP, que podem variar entre execuções.
A planilha de origem em `data/source/` nunca é lida para escrita.
