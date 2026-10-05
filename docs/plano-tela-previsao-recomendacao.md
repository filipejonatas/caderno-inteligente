# Plano de implementação — Tela de previsão e recomendação

## 1. Objetivo

Adicionar uma página responsiva chamada **Previsão e recomendações** para transformar os forecasts já calculados em uma visão operacional consolidada.

A tela deve permitir que PCP, comercial ou planejamento respondam rapidamente:

- quais SKUs têm demanda crescente ou decrescente;
- qual modelo foi selecionado para cada SKU e qual foi seu erro no backtest;
- quais SKUs possuem dados insuficientes ou baixa confiança;
- qual ação operacional é sugerida;
- qual quantidade é sugerida após considerar carteira, estoque, produção aberta, estoque de segurança e lote mínimo;
- quais recomendações precisam de validação de capacidade ou investigação dos dados.

A página continuará sendo um **apoio à decisão**. Ela não deve criar, liberar ou prometer ordens de produção.

## 2. Princípios e restrições

1. Preservar integralmente score, ranking, regras, processamento do Excel e contratos existentes.
2. Não alterar os algoritmos de forecast ou recomendação implementados na V1.
3. Não instalar dependências, criar migration ou persistir previsões no banco nesta etapa.
4. Reutilizar o cache do pipeline; não recalcular forecasts em cada requisição ou interação no frontend.
5. Não buscar o detalhe de cada SKU com dezenas de requisições individuais.
6. Criar somente um endpoint agregado, de leitura e aditivo.
7. Reutilizar o `SkuDrawer` para o aprofundamento, evitando uma segunda tela de detalhe.
8. Manter visíveis os avisos de revisão humana, incerteza e limitação de capacidade.
9. Nunca apresentar a quantidade sugerida como ordem confirmada ou capacidade garantida.

## 3. Escopo funcional do MVP

### 3.1 Entrada no menu

Adicionar **Previsão e recomendações** ao menu lateral, entre **Prioridades** e **Casos**.

Descrição curta no menu:

> Demanda e ação sugerida

O item deve possuir ícone coerente com o design atual, como um gráfico de tendência.

### 3.2 Cabeçalho da página

Usar `PageIntro` com:

- eyebrow: `Planejamento de demanda`;
- título: `Previsão e recomendações`;
- descrição: `Compare a demanda prevista, a confiança do modelo e a ação sugerida antes da validação humana.`

Exibir um aviso permanente próximo ao topo:

> As quantidades são sugestões de apoio à decisão. Revise carteira, capacidade e restrições operacionais antes de agir.

### 3.3 Indicadores resumidos

Exibir quatro cards, calculados no frontend a partir do retorno da nova rota:

1. **SKUs previstos** — quantidade com `forecast.status == "ok"`;
2. **Produção sugerida** — quantidade com ação `produzir` ou `produzir_validar_capacidade`;
3. **Validar capacidade** — quantidade com `capacity_status == "requires_review"`;
4. **Investigar dados** — forecasts insuficientes ou recomendações com ação `investigar_dados`.

Esses cards são contagens informativas e não devem alterar o ranking oficial.

### 3.4 Filtros e ordenação

Adicionar controles locais, sem nova chamada à API a cada alteração:

- busca por SKU ou produto;
- família;
- ação recomendada;
- confiança da previsão;
- tendência;
- opção **Somente itens com atenção**;
- ordenação por prioridade, quantidade sugerida, forecast do próximo mês ou maior WAPE.

Valores iniciais:

- todos os itens;
- ordenação por prioridade oficial;
- itens com dados insuficientes permanecem visíveis.

Adicionar botão **Limpar filtros** quando houver filtro ativo.

### 3.5 Lista operacional

Em desktop, apresentar uma tabela ou lista tabular com as colunas:

| Campo | Conteúdo |
|---|---|
| SKU | Código, produto e família |
| Prioridade | Posição no ranking oficial, quando existir |
| Tendência | Crescente, estável, decrescente ou indeterminada |
| Próximo mês | Forecast em unidades |
| Próximos 3 meses | Soma dos três meses previstos |
| Modelo | Média móvel 3 meses ou sazonal ingênuo 12 meses |
| WAPE | Erro do holdout de três meses |
| Confiança | Alta, média ou baixa |
| Recomendação | Ação sugerida |
| Quantidade | Quantidade sugerida já arredondada pelo lote mínimo |
| Capacidade | Status de validação |

Cada item deve oferecer a ação **Ver detalhes**, que abre o `SkuDrawer` existente. O drawer continuará sendo a fonte de explicação completa da fórmula, premissas, limitações e evidências.

Em telas pequenas, transformar cada linha em card. Não depender de rolagem horizontal para acessar as informações principais.

### 3.6 Estados especiais

#### Dados insuficientes

Quando `forecast.status == "insufficient_data"`:

- mostrar `Dados insuficientes` no lugar das quantidades previstas;
- mostrar ação `Investigar dados`;
- não substituir valores ausentes por zero;
- permitir abrir o drawer para ler a limitação.

#### Capacidade

Quando `capacity_status == "requires_review"`:

- usar badge de atenção;
- mostrar `Validar capacidade`;
- não reduzir nem confirmar automaticamente a quantidade sugerida.

#### Erro da API

Mostrar erro apenas dentro da página, com botão **Tentar novamente**. O restante da aplicação deve continuar utilizável.

#### Lista vazia

Se nenhum item corresponder aos filtros, explicar que não há resultados e oferecer **Limpar filtros**.

## 4. Contrato aditivo do backend

### 4.1 Nova rota

Criar:

```text
GET /api/forecasts
```

A rota deve retornar uma lista JSON compacta, com um item por SKU, sem paginação nesta V1. Com o volume atual, isso mantém a implementação simples e permite filtros instantâneos no navegador.

Formato proposto:

```json
[
  {
    "sku": "CI-0002",
    "product": "Produto exemplo",
    "family": "Família exemplo",
    "priority": 6,
    "attention_score": 72.0,
    "forecast": {
      "status": "ok",
      "reference_month": "2026-09-01",
      "history_months": 24,
      "model": "seasonal_naive_12",
      "model_label": "Sazonal ingênuo (12 meses)",
      "forecast_months": ["2026-10-01", "2026-11-01", "2026-12-01"],
      "forecast_values": [203.0, 221.0, 248.0],
      "forecast_next_month": 203.0,
      "forecast_total_3m": 672.0,
      "trend": "estável",
      "trend_change_ratio": 0.02,
      "backtest_wape": 0.0509,
      "forecast_confidence": "alta",
      "limitation": "..."
    },
    "operational_recommendation": {
      "action": "sem_acao_necessaria",
      "action_label": "Sem ação necessária",
      "suggested_quantity": 0.0,
      "minimum_lot": 300.0,
      "capacity_status": "requires_review",
      "confidence": "média",
      "requires_human_review": true
    }
  }
]
```

O endpoint consolidado pode retornar apenas o subconjunto da recomendação necessário à listagem. O contrato completo continuará disponível em `GET /api/priorities/{sku}`.

### 4.2 Regras de montagem

No `backend/main.py`:

1. Obter `indicators`, `issues`, `ranking` e `forecasts` do `pipeline()` já cacheado.
2. Indexar ranking e forecast por SKU.
3. Para cada indicador, chamar `build_operational_recommendation` com os mesmos dados usados pelo detalhe.
4. Reutilizar `_records` para converter `NaN` em `null` e tipos NumPy em tipos JSON.
5. Ordenar primeiro pelos SKUs presentes no ranking oficial e depois pelos demais SKUs em ordem alfabética.
6. Não copiar ou reimplementar a fórmula de recomendação dentro da rota.

O endpoint deve incluir todos os SKUs válidos, mesmo os que não estejam no ranking, para que tendências e excesso também possam ser analisados.

## 5. Alterações no frontend

### `frontend/src/types.ts`

- adicionar `forecasts` ao `PageId`;
- criar `ForecastRecommendationSummary` com o contrato compacto da rota;
- manter `DemandForecast`, `OperationalRecommendation` e `SkuDetail` como fontes dos contratos completos;
- evitar duplicação usando `Pick<>` quando isso mantiver o tipo legível.

### `frontend/src/api.ts`

- adicionar `api.forecasts()` para `GET /forecasts`;
- não incluir a rota em `loadDashboard`, evitando aumentar o carregamento inicial das demais páginas;
- carregar os dados somente ao abrir a nova página;
- permitir nova tentativa após erro.

### `frontend/src/components.tsx`

- adicionar o ícone `forecasts`;
- adicionar a página ao catálogo `navigation`;
- manter o item visível e acessível no menu mobile.

### `frontend/src/App.tsx`

- importar e renderizar `ForecastsPage`;
- passar `onSelect={setSelectedPriority}` para reutilizar o drawer;
- quando um SKU não estiver no ranking, construir uma referência mínima ou adaptar a seleção do drawer para receber `sku`, `product` e `family` sem alterar a aparência pública;
- manter o comportamento global de voltar ao topo ao navegar.

Preferência de implementação: alterar o estado de seleção para um tipo mínimo, por exemplo `SelectedSku`, aceito tanto por prioridades quanto pela nova página. Isso evita fabricar um objeto `Priority` incompleto.

### `frontend/src/pages.tsx`

- criar `ForecastsPage`;
- buscar a lista uma vez ao montar a página;
- implementar filtros, ordenação, KPIs, estados de erro/vazio e lista responsiva;
- reutilizar `PageIntro`, `SectionCard`, `Badge`, `LoadingState`, `ErrorState` e formatadores existentes;
- manter a explicação detalhada somente no `SkuDrawer`;
- adicionar a nova página ao mapa estático exibido em `GuidePage`.

### `frontend/src/App.css`

- criar estilos específicos com prefixo `forecast-page-` para reduzir colisões;
- reutilizar tokens, cores, sombras, espaçamentos e breakpoints atuais;
- manter badges consistentes para tendência, confiança, ação e capacidade;
- em até `760px`, substituir a grade tabular por cards empilhados;
- garantir foco visível, botões com área confortável e ausência de rolagem horizontal em `390 x 844`.

## 6. Fluxo de dados

```text
Excel / PostgreSQL
        ↓
pipeline() cacheado
        ↓
indicadores + regras + ranking + forecasts
        ↓
build_operational_recommendation()
        ↓
GET /api/forecasts
        ↓
ForecastsPage — KPIs, filtros e lista
        ↓
GET /api/priorities/{sku}
        ↓
SkuDrawer — explicação completa
```

## 7. Ordem de implementação para a IA

### Etapa 1 — Contrato agregado

1. Criar `GET /api/forecasts` usando o pipeline cacheado.
2. Reutilizar a função atual de recomendação.
3. Criar teste de contrato da nova rota.
4. Confirmar que os contratos das rotas existentes não mudaram.

### Etapa 2 — Tipos e navegação

1. Adicionar o novo `PageId` e o tipo de resumo.
2. Adicionar ícone e item no menu.
3. Ajustar o estado de SKU selecionado para servir às duas páginas.
4. Adicionar a página ao Guia de uso.

### Etapa 3 — Página e interação

1. Criar `ForecastsPage` com carregamento sob demanda.
2. Implementar aviso, KPIs, filtros e ordenação.
3. Implementar tabela desktop e cards mobile.
4. Ligar **Ver detalhes** ao drawer existente.
5. Implementar estados de erro, lista vazia e dados insuficientes.

### Etapa 4 — Estilo e acessibilidade

1. Aplicar o design system existente.
2. Validar navegação por teclado e foco.
3. Conferir contraste e textos de confiança/limitação.
4. Validar desktop e mobile.

### Etapa 5 — Testes e documentação

1. Executar a suíte Python completa.
2. Executar `npm run check`.
3. Atualizar `docs/api.md` com a nova rota.
4. Atualizar `docs/architecture.md` com o fluxo consolidado.
5. Registrar a decisão em `docs/decisions.md`.

Estimativa para execução por IA: **1h30 a 2h30**, incluindo testes e ajustes visuais.

## 8. Testes necessários

### Backend

Adicionar testes para confirmar:

1. `GET /api/forecasts` retorna HTTP 200 e uma lista;
2. há um item por SKU válido;
3. cada item possui identificação, forecast e recomendação compacta;
4. forecasts válidos possuem exatamente três meses e três valores;
5. dados insuficientes permanecem `null`, nunca zero artificial;
6. toda recomendação possui `requires_human_review == true`;
7. quantidades positivas respeitam o lote mínimo;
8. previsão e carteira continuam sendo conciliadas por `max`, não por soma;
9. a ordenação inicial preserva a prioridade oficial;
10. score e ranking permanecem idênticos aos produzidos pelo pipeline atual.

### Frontend

Sem adicionar biblioteca de testes:

1. TypeScript compila sem erros;
2. build de produção termina com sucesso;
3. filtros não alteram os dados de origem;
4. valores `null` são mostrados como indisponíveis, não como zero;
5. botão **Ver detalhes** abre o SKU correto;
6. falha na nova rota não derruba as outras páginas.

### Validação manual

Validar em `1440 x 900`, `1366 x 768` e `390 x 844`:

1. navegação pelo menu;
2. leitura dos KPIs;
3. combinação de busca e filtros;
4. ordenações;
5. SKUs com baixa confiança ou dados insuficientes;
6. badge de validação de capacidade;
7. abertura e fechamento do drawer;
8. navegação apenas por teclado;
9. ausência de erros no console;
10. ausência de rolagem horizontal no mobile.

## 9. Critérios de aceite

- Existe uma página dedicada acessível pelo menu lateral.
- A página exibe todos os SKUs retornados pelo pipeline, inclusive os não priorizados.
- Forecast, tendência, WAPE, confiança, ação e quantidade são compreensíveis sem abrir o detalhe.
- Dados insuficientes são sinalizados de forma explícita e não viram zero.
- A recomendação continua transparente e sempre exige revisão humana.
- Capacidade é apresentada como validação pendente, não como garantia.
- O ranking exibido é o ranking oficial já existente.
- O drawer atual abre a explicação completa do SKU selecionado.
- Nenhuma chamada individual por SKU é feita para montar a listagem.
- Nenhuma dependência, migration ou persistência adicional é criada.
- Todas as rotas existentes mantêm seus contratos.
- A suíte Python e `npm run check` passam integralmente.

## 10. Fora do escopo

- gráficos avançados ou biblioteca de visualização;
- edição manual do forecast;
- aprovação ou emissão de ordem de produção;
- otimização matemática de capacidade;
- previsão probabilística ou intervalos estatísticos;
- comparação interativa de novos modelos;
- paginação no backend;
- persistência ou versionamento das previsões;
- alertas por e-mail, Slack ou WhatsApp;
- atualização em tempo real;
- mudanças no score, ranking, regras ou Excel.

## 11. Riscos e mitigação

| Risco | Mitigação |
|---|---|
| A página parecer prescritiva | Aviso permanente e revisão humana explícita |
| Duplicação da fórmula no endpoint | Chamar `build_operational_recommendation` existente |
| Muitas chamadas serverless | Uma rota agregada e cacheada |
| Confusão entre prioridade e quantidade | Colunas separadas e textos distintos |
| Capacidade interpretada como confirmada | Badge `Validar capacidade` e nenhuma limitação automática |
| `null` interpretado como demanda zero | Estado textual `Dados insuficientes` |
| Tela excessivamente densa no celular | Cards responsivos com informações progressivas |

## 12. Prompt sugerido para implementação

> Implemente integralmente `docs/plano-tela-previsao-recomendacao.md`. Preserve os contratos existentes, score, ranking, regras, processamento do Excel e os algoritmos atuais de previsão e recomendação. Não adicione dependências, migrations ou persistência. Crie a página responsiva “Previsão e recomendações”, acessível pelo menu lateral, e o endpoint aditivo `GET /api/forecasts`, montado sobre o pipeline cacheado. A tela deve carregar os dados sob demanda, apresentar KPIs, busca, filtros, ordenação e todos os SKUs, reutilizando o `SkuDrawer` para o detalhe. Dados insuficientes não podem aparecer como zero; capacidade não pode ser apresentada como garantia; toda recomendação deve exigir revisão humana. Atualize o Guia de uso e a documentação técnica, crie testes de contrato e execute toda a suíte Python e `npm run check`. Não altere segredos nem faça deploy. Ao final, informe arquivos modificados, resultados dos testes, limitações e passos de deploy.
