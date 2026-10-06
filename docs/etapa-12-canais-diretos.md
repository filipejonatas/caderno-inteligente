# Etapa 12 — Visão dos canais diretos

Terceira etapa do [plano de aderência ao desafio](plano-aderencia-desafio.md). Dá visão própria a E-commerce, Marketplace e Loja própria, que concentram a maior parte do faturamento da base e eram tratados só dentro da previsão global por SKU. Camada aditiva e somente leitura: não altera previsão, score, ranking, regras, `/api/data-quality` nem as telas de parceiros B2B.

## Resultado

| Item do plano | Entrega |
|---|---|
| Aba em Parceiros e detalhe do canal | Aba **Canais diretos** em `/parceiros?aba=diretos` e detalhe em `/canais/:canal` |
| Faturamento e unidades de 24 meses, participação e tendência | `src/caderno_inteligente/direct_channels.py`: série mensal, participação no total, tendência (média dos últimos 3 meses × 3 anteriores, mesma regra da previsão) e variação sobre o mesmo período do ano anterior |
| Ranking de SKUs e curva de contribuição | Posição por faturamento, participação no canal, participação acumulada, top 5 e quantos SKUs somam 80% |
| SKUs que cresceram ou caíram | Sinais `GROWING` e `DECLINING` por SKU, com a variação |
| Recorrência e reativação | Meses com venda, primeiro e último mês; `STOPPED` quando o SKU vendeu e ficou 2 meses ou mais sem faturar |
| Mix | `NOT_SOLD`: produto sem nenhum faturamento no canal, exibido como "Sem faturamento no canal", nunca como zero |
| Carteira aberta do canal | Pedidos não encerrados por canal e por SKU, sem alocação de produção |
| Direto × parceiros por SKU | Unidades recentes dos parceiros B2B e participação do canal no SKU, só como contexto |
| Sugestão por SKU | `suggestion` determinística, com motivo e `requires_human_review`: ampliar mix, reativar, investigar queda, monitorar saída de linha, acompanhar crescimento ou sem ação |
| Achados de qualidade | Dois achados entre abas, em **Confiança › Dados da planilha** |

## Contrato (aditivo)

- `GET /api/direct-channels`: totais, resumo dos 3 canais (faturamento, participação, tendência, concentração, carteira, contagem de sinais e sugestões, série mensal), achados, rótulos, `field_nature` e `limitations`.
- `GET /api/direct-channels/{canal}`: o resumo e uma linha por SKU, ordenada por faturamento (SKUs sem faturamento por último). Filtros `signal`, `suggestion` e `search`; 404 para canal inexistente ou parceiro B2B, 422 para sinal ou sugestão inválidos.
- `GET /api/data-quality/channels`: os achados. O `/api/data-quality` **não mudou**.
- `frontend/src/test/contract-keys.json` ganhou os endpoints `directChannels`, `directChannel` e `channelFindings`.
- Limiares em `config/direct_channel_thresholds.json` (janela da tendência, faixa neutra de ±10%, meses de inatividade e participação de concentração), validados no carregamento.

## Achados de qualidade (nada foi reconciliado)

1. **Cobertura dos canais diretos sem Sell_Out.** O cadastro declara cobertura "Completo" e 50 SKUs para os três canais, mas `Sell_Out` não tem nenhuma linha deles. A visão usa o faturamento de `Vendas_24m`, que nesses canais é a venda ao consumidor.
2. **Sell_In difere do faturado nos parceiros.** Nos 600 pares parceiro–SKU–mês em comum, nenhum tem a mesma quantidade; o Sell_In é cerca de 2,79 vezes o faturado (mediana). As abas também cobrem períodos e SKUs diferentes (12 contra 24 meses; 10 contra 50 SKUs por parceiro). A análise comercial dos parceiros segue usando Sell_In e Sell_Out.

## Números na planilha atual (hash `03fa0ed4…`)

| Canal | Faturamento (24 meses) | Participação | Tendência | Carteira aberta |
|---|---|---|---|---|
| E-commerce | R$ 11.606.120 | 28,1% | estável (+1,1%) | 7 pedidos, 2.464 un. |
| Marketplace | R$ 9.110.310 | 22,1% | estável (+1,1%) | 9 pedidos, 3.043 un. |
| Loja própria | R$ 7.447.799 | 18,0% | estável (+1,0%) | 9 pedidos, 4.163 un. |

- Juntos: **68,2% do faturamento** (R$ 28,2 mi de R$ 41,3 mi), contra "parcela menor" no texto do desafio.
- Cada canal vende os 50 SKUs em todos os 24 meses; **não há SKU parado nem lacuna de mix hoje**. Os sinais `STOPPED` e `NOT_SOLD` existem e são testados, mas não disparam nesta base.
- Em cada canal: 4 SKUs em queda (entre −11% e −17%), 4 em crescimento (entre +11% e +15%) e 2 produtos em descontinuação (CI-0047 e CI-0050) ainda vendidos.
- Concentração baixa: os 5 maiores SKUs somam cerca de 27% do canal e são necessários 25 SKUs para chegar a 80%.
- Os três canais têm exatamente a mesma composição de SKUs e a mesma sazonalidade (dado sintético). Por isso o painel não discrimina canais entre si; a diferenciação real virá com dados reais.

## Decisões de projeto

1. **Canal direto é definido pelo cadastro** (`Parceiros_Canais.Tipo = "Canal direto"`), não por lista fixa no código.
2. **Faturamento ausente é "não vendido", não zero.** SKU sem faturamento no canal tem valores `null`, sinal `NOT_SOLD` e nenhuma tendência.
3. **Sem estoque por canal.** A base só tem o estoque do CD Central; a tela e a API declaram isso (`field_nature.stock = ausente`) e nenhum campo de estoque foi criado.
4. **Sugestões ficam neste módulo como sinais prontos para a Etapa 13.** Os rótulos de ação do desafio serão uma camada derivada que lê esses sinais (por exemplo, "Ampliar mix" a partir de `NOT_SOLD` e "reativação" a partir de `STOPPED`).
5. **Achados no endpoint próprio.** Alterar `/api/data-quality` mudaria uma resposta já consumida e testada; o endpoint novo alimenta o cartão "Achados entre abas".
6. **Orçamento de volume:** o teste não foi afrouxado. As telas novas ganharam entradas próprias em `volume-budget.json`. O cartão de achados cabe no limite de palavras por linha usando títulos curtos e tooltips (o detalhe e o tratamento completo ficam no "?").

## Limitações (declaradas na tela e na API)

- A visibilidade vem do faturamento; os canais diretos não têm Sell_In nem Sell_Out.
- Sem estoque por canal.
- A tendência compara meses recentes com os anteriores e pode refletir sazonalidade.
- A carteira de pedidos é contexto, sem alocação de produção.
- A sugestão é demonstrativa e exige revisão humana.

## Arquivos

### Criados

- `src/caderno_inteligente/direct_channels.py`, `backend/direct_channels.py` e `config/direct_channel_thresholds.json`
- `tests/test_direct_channels.py`
- `frontend/src/types-channels.ts`, `components/ChannelViews.tsx` e `pages/ChannelDetailPage.tsx`
- `frontend/src/test/channels.test.tsx`
- `docs/etapa-12-canais-diretos.md`

### Modificados

- `backend/main.py` (inclusão do roteador)
- `frontend/src/App.tsx` (rota e título), `components.tsx` (grupo Parceiros inclui `/canais`), `api.ts`, `pages/B2BPage.tsx` (aba), `pages/QualityPage.tsx` (achados), `pages/shared.ts` (glossário), `components/RevenueForecast.tsx` (legenda do gráfico só quando há estimativa)
- `frontend/src/test/fixtures.ts`, `utils.tsx`, `contracts.test.ts`, `contract-keys.json`, `a11y.test.tsx`, `volume-budget.json` (duas entradas novas) e `tests/test_frontend_contracts.py`
- `docs/api.md`, `docs/calculations.md`, `README.md` e `docs/plano-aderencia-desafio.md`

## Validação

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider
cd frontend; npm run check
```

- **Python:** 247 testes passando (18 novos em `tests/test_direct_channels.py` e 3 de contrato). Cobrem: canais definidos pelo cadastro, totais com parceiros, tendência e concentração, SKU nunca vendido (nulo, nunca zero), produto em descontinuação, SKU parado, faixa neutra, ranking, ordenação, carteira por canal ignorando pedidos encerrados, contexto dos parceiros, ausência de estoque, os dois achados (com e sem disparo), limiares e a API real.
- **Frontend:** 210 testes do Vitest, 21 do `node --test`, typecheck, build e varredura de segredos passando, inclusive volume e acessibilidade das duas rotas novas.
- **Regressão:** o hash das respostas de `/api/forecasts`, `/api/priorities`, `/api/overview` e `/api/data-quality` é idêntico ao anterior à Etapa 10.
- **Bug encontrado pelos testes:** a carteira por SKU incluía pedidos encerrados; o teste de carteira por canal pegou e foi corrigido antes do fechamento.
- **Navegador:** conferido com a API real em `/parceiros?aba=diretos`, `/canais/Loja própria` e `/qualidade`, sem erros no console.

## Não feito nesta etapa

- Sem deploy, sem alteração de segredos e sem alteração da planilha.
- O `scripts/smoke_test.py` não inclui os endpoints novos, para não mudar a contagem documentada na Etapa 9.
- Sem faturamento previsto por canal: a previsão continua global por SKU.
- Sem estoque, cobertura ou sell-out por canal: a base não tem esses dados para os canais diretos.
