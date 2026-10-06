# Etapa 11 — Sazonalidade e eventos (alerta e fator explícito)

Segunda etapa do [plano de aderência ao desafio](plano-aderencia-desafio.md). Passa a usar o `Calendario_Eventos` — que até aqui só era validado — como **alerta** e como **cenário explícito**, sem alterar o modelo de previsão, a previsão em unidades, o score, o ranking, as regras nem a quantidade oficial sugerida.

## Resultado

| Item do plano | Entrega |
|---|---|
| Alerta por SKU | `src/caderno_inteligente/events.py`: eventos que cobrem a família do SKU e exigem decisão no horizonte ou antes dele. Cada alerta traz período, impacto, dias até o início, **data de decisão** (início − lead time do SKU), se está no horizonte e a evidência histórica |
| Fator sazonal por evidência | Fator por família e mês: mês do evento ÷ média dos meses sem evento num raio de 6 meses (acompanha a tendência), média das ocorrências anteriores. Limitado por `config/event_factors.json` (0,5 a 3,0) com registro de corte (`capped`) |
| Cenário com evento | `previsão base × fator do mês`, em coluna separada, com selo **Estimativa**, fórmula, faturamento no cenário (preço da Etapa 10) e quantidade oficial ao lado da quantidade com cenário |
| Sem dupla contagem | SKU cujo modelo é `seasonal_naive_12` (já repete o ano anterior) recebe só alerta, com a explicação na tela |
| Evento sem histórico | "Novos SKUs sem histórico direto" (Primavera) gera alerta e nenhum fator. A regra é por marcador configurável na observação |
| Famílias sem evidência | Histórico curto, sem linha de base ou sem ocorrência anterior: só alerta, com o motivo |
| Telas | Início: faixa "Eventos que pedem decisão". Previsão: selo `Evento: …` por SKU. Detalhe do SKU: alertas e cenário dentro de "Sobre a previsão" |

## Contrato (aditivo)

- `GET /api/events`: `events[]` (período, impacto, `has_history`, `in_horizon`, `past`, `decision_date_earliest`, `skus_alerted`, evidência por família), `items[]` (um por SKU, com `alerts[]`, `scenario`, `scenario_applicable` e `scenario_note`), `family_factors[]` (fator por família e mês, com as ocorrências usadas), `settings`, `ignored_events[]`, `field_nature` e `limitations`.
- `GET /api/priorities/{sku}`: campos opcionais `event_alerts` e `event_scenario` (`null` se a análise falhar, sem afetar o restante).
- `GET /api/forecasts`, `/api/priorities` e os demais endpoints **não ganharam campos**.
- `frontend/src/test/contract-keys.json` ganhou o endpoint `events` e os campos novos de `skuDetail`.

## Como o fator é calculado

1. Para cada família, os meses do ano cobertos por eventos que a afetam são excluídos da linha de base. Eventos sem histórico direto também são excluídos, por prudência, mas não geram fator.
2. Para cada ocorrência histórica do mês do evento, `lift = unidades do mês ÷ média dos meses sem evento` no raio de 6 meses, com no mínimo 3 meses de base.
3. O fator do mês é a média dos lifts (mínimo de 1 ocorrência e 12 meses de histórico da família). O fator do evento é a média dos meses que ele cobre.
4. A evidência é classificada em `aumento`, `sem_alteracao` (±10%), `queda`, `sem_evidencia` ou `sem_historico_direto`. Quando o calendário aponta impacto e a história não mostra variação, a tela diz isso.
5. No cenário, cada mês do horizonte recebe o fator do mês se houver evento cobrindo-o; os demais ficam com fator 1.

## Números na planilha atual (hash `03fa0ed4…`)

| Evento | Famílias | Fator | Leitura |
|---|---|---|---|
| Black Friday (20 a 30/11/2026) | todas | ×1,29 a ×1,52 (2 ocorrências) | no horizonte; 50 SKUs; decidir até 24/10 |
| Natal (01 a 23/12/2026) | Planner | ×1,61 | fora do horizonte, mas a decisão cai dentro dele |
| Natal | Executivo, Acessórios | ×0,99 | o calendário indica impacto médio, o histórico não mostra aumento |
| Volta às Aulas (05/01 a 20/02/2027) | Escolar | ×2,41 (4 ocorrências) | decidir até 14/12 |
| Volta às Aulas | Clássico, Refis | ×1,00 | o calendário indica impacto alto, o histórico não mostra aumento |
| Lançamento Coleção Primavera (15 a 31/10/2026) | Clássico, Acessórios | — | sem histórico direto: só alerta (26 SKUs) |
| Dia das Mães (2027) | Planner, Executivo | ×0,90 a ×1,03 | a decisão só cai depois do horizonte: nenhum SKU alertado |

- **34 SKUs** com cenário (média móvel) e **16** só com alerta (previsão sazonal).
- No cenário, +6.004 unidades em 3 meses e **+R$ 425 mil** (+12,8%) sobre a base de R$ 3,33 mi desses SKUs, quase tudo da Black Friday em novembro.
- Nenhum fator foi limitado pelo teto de 3,0 (o maior é ×2,41).
- A quantidade oficial **não muda em nenhum SKU**: ela cobre só o próximo mês (setembro) e os eventos caem depois. O que o evento muda é a **data de decisão**, que é o que a tela mostra.

## Decisões de projeto

1. **Teto do fator em 3,0 e não em 2,0.** O plano sugeria 2,0 como exemplo; o histórico mostra Volta às Aulas em ×2,41 para Escolar, e limitar a 2,0 subestimaria o pico e aumentaria o risco de ruptura. É configurável em `config/event_factors.json`.
2. **Fator por evidência, não por tabela.** Foi a recomendação padrão do plano. Uma tabela fixa por impacto ("Alta = ×1,2") contradiria os dados em vários casos (Clássico na Volta às Aulas, Natal para Executivo).
3. **Data de decisão = início do evento − lead time do SKU**, e o alerta vale até `lead time + 30 dias` de antecedência além do horizonte. É isso que faz Natal e Volta às Aulas aparecerem hoje.
4. **Eventos dentro de "Sobre a previsão".** O orçamento de volume do detalhe do SKU admite 6 blocos; um bloco novo estouraria o teste, então alertas e cenário ficam dentro do bloco da previsão. Observações longas ficam em tooltip, e o "?" traz a definição do cenário. O teste de volume não foi afrouxado.
5. **Fonte da `has_history`:** marcador de texto na observação (`config/event_factors.json`). É frágil se o texto da planilha mudar, e por isso é configurável.

## Limitações (declaradas na tela e na API)

- Cenário indicativo: poucas ocorrências por evento (de 1 a 4) e nenhum efeito de campanhas futuras.
- Fator em mês calendário: Black Friday (11 dias) recebe o fator de novembro inteiro, que no histórico já inclui o mesmo evento.
- A previsão sazonal de 12 meses já embute o padrão do ano anterior; para esses SKUs não há cenário.
- Dia de referência é o mês de referência da base (agosto de 2026), não a data de hoje.
- A previsão base, o ranking e a quantidade oficial não são alterados.

## Arquivos

### Criados

- `src/caderno_inteligente/events.py`
- `config/event_factors.json`
- `tests/test_events.py`
- `frontend/src/types-events.ts`
- `frontend/src/components/EventAlerts.tsx`
- `frontend/src/test/events.test.tsx`
- `docs/etapa-11-eventos-sazonalidade.md`

### Modificados

- `backend/main.py` (endpoint, cache com a configuração e campos no detalhe do SKU)
- `frontend/src/api.ts`, `types.ts`, `pages/shared.ts` (glossário), `pages/OverviewPage.tsx`, `pages/ForecastsPage.tsx`, `pages/SkuDetailPage.tsx`, `usability.css`
- `frontend/src/test/fixtures.ts`, `utils.tsx`, `contracts.test.ts`, `contract-keys.json`, `frontend/scripts/test-decision-journey.mjs` (a faixa de eventos busca a API sozinha e é coberta pelo Vitest; o teste de renderização estática a substitui por um stub) e `tests/test_frontend_contracts.py`
- `docs/api.md`, `docs/calculations.md`, `docs/semana-3-modelo-preditivo.md`, `README.md` e `docs/plano-aderencia-desafio.md`

## Validação

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider
cd frontend; npm run check
```

- **Python:** 226 testes passando (16 novos em `tests/test_events.py`, mais 1 de contrato: configuração, calendário com linhas inválidas, fator por evidência, teto registrado, histórico curto, evento sem histórico, impacto sem aumento histórico, modelo sazonal sem cenário, janela de alerta com lead time, inalterabilidade da previsão e contrato da API).
- **Frontend:** 189 testes do Vitest, 21 do `node --test`, typecheck, build e varredura de segredos passando, inclusive volume e acessibilidade.
- **Regressão:** o hash das respostas de `/api/forecasts`, `/api/priorities`, `/api/overview` e `/api/data-quality` é idêntico ao anterior à Etapa 10.
- **Navegador:** conferido com a API real em `/`, `/previsoes` e `/skus/CI-0001`. O único ruído no console são falhas do WebSocket de HMR do Vite no painel.

## Não feito nesta etapa

- Sem deploy, sem alteração de segredos e sem alteração da planilha.
- O `scripts/smoke_test.py` não inclui o endpoint novo, para não mudar a contagem documentada na Etapa 9.
- Não há fator por evento em campanhas futuras nem por parceiro ou região: a base só sustenta histórico por família.
