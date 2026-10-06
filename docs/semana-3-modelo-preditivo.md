# Semana 3 — Modelo preditivo, arquitetura e dados

## Problema e recorte

O Protótipo V1 apoia o PCP a identificar quais SKUs exigem atenção, compreender os sinais que geraram a prioridade e avaliar uma quantidade de produção para o próximo ciclo.

O recorte não pretende otimizar toda a cadeia. A unidade de análise é o SKU global. Parceiro, canal e capacidade familiar aparecem como contexto e confiança, não como promessa de alocação individual.

## Tarefa executada pelo modelo

O componente preditivo estima a demanda mensal de cada SKU para os próximos três meses usando o histórico de quantidade faturada. Ele também classifica a tendência e mede seu próprio erro em meses que foram separados do ajuste.

O modelo não toma a decisão final. Sua previsão alimenta uma recomendação quantitativa transparente, que precisa ser revisada pelas áreas comercial e operacional.

## Modelos comparados e justificativa

Para cada SKU são comparados:

- média móvel de três meses, sensível ao comportamento recente;
- sazonal ingênuo de doze meses, que representa a repetição do mesmo mês do ano anterior.

Os três últimos meses conhecidos são reservados como holdout. O sistema seleciona o candidato com menor WAPE e, somente depois, recalcula os próximos três meses com todo o histórico.

A escolha favorece modelos simples porque o protótipo possui 24 meses de dados, precisa ser auditável e será avaliado contra uma alternativa clara. Um modelo mais complexo sem volume e validação suficientes produziria uma aparência de precisão sem sustentação.

## Confiança

- WAPE até 20%: confiança alta;
- acima de 20% e até 40%: confiança média;
- acima de 40% ou WAPE indisponível: confiança baixa;
- menos de seis meses: dados insuficientes e nenhuma quantidade prevista.

Confiança representa o desempenho no holdout temporal e não é garantia sobre o futuro. A recomendação também reduz a confiança quando não existe sell-out observado ou quando há pressão de capacidade.

## Recomendação operacional

Para o próximo mês:

```text
demanda a cobrir = máximo(previsão do próximo mês, pedidos em carteira)

estoque de segurança = venda média diária × dias de segurança

necessidade bruta = máximo(
  0,
  demanda a cobrir
  + estoque de segurança
  - estoque atual
  - produção aberta
)
```

A quantidade é arredondada para cima pelo lote mínimo. Previsão e carteira não são somadas para reduzir dupla contagem. Capacidade não limita automaticamente a quantidade, pois a fonte é agregada por família e semana e não relaciona pedidos a ordens individualmente.

## Fluxo de dados

```text
XLSM somente leitura
        ↓
validação e normalização
        ↓
indicadores e histórico mensal por SKU
        ├── regras determinísticas → score e ranking
        └── backtest → modelo selecionado → previsão de 3 meses
                                      ↓
                           recomendação quantitativa
                                      ↓
FastAPI com cache → React/Vite → revisão humana
                                      ↓
Supabase: casos, feedbacks e snapshots auditáveis
```

## Componentes e integrações

- `ingestion.py` e `validation.py`: leitura e qualidade da fonte;
- `indicators.py`: estado operacional por SKU;
- `forecasting.py`: séries mensais, backtest, seleção e previsão;
- `recommendations.py`: quantidade, ação, confiança e limitações;
- `rules.py` e `prioritization.py`: sinais e ranking oficial, preservados;
- FastAPI: contrato e cache por assinatura dos arquivos;
- React/Vite: detalhe do SKU e evidências;
- Supabase PostgreSQL: decisões, casos e execuções;
- Vercel: publicação separada do backend e frontend.

## Retroalimentação

O usuário registra se aceitou, alterou, rejeitou ou decidiu investigar, além do efeito do dado do parceiro e do tempo de análise. Esses registros não retreinam nem alteram automaticamente o modelo no V1.

Essa separação evita aprendizado silencioso a partir de poucas decisões. Em uma evolução, feedbacks revisados poderão orientar recalibração de limiares, análise de aceitação e seleção de modelos.

## Segurança, privacidade e governança

- a planilha é somente leitura;
- a origem e os valores usados ficam visíveis;
- dados ausentes não são convertidos silenciosamente em observação zero, exceto meses sem faturamento dentro de uma série já observada;
- a conexão do Supabase existe somente no backend;
- decisões humanas ficam separadas da fonte;
- snapshots preservam hash, parâmetros, qualidade e ranking;
- o protótipo utiliza dados fictícios e não possui autenticação nesta fase;
- nenhuma recomendação cria ordem de produção automaticamente.

## Limitações conhecidas

- previsão global por SKU, sem parceiro ou região;
- apenas 24 meses de histórico;
- campanhas futuras e eventos não entram como variáveis causais;
- o modelo estatístico prevê unidades; o faturamento é uma estimativa derivada (unidades × preço vigente, [Etapa 10](etapa-10-faturamento-estimado.md)), com as mesmas limitações da previsão e preço constante;
- carteira e forecast podem representar horizontes comerciais diferentes;
- capacidade é agregada por família e não comprova viabilidade individual;
- o histórico disponível é demonstrativo e não substitui validação com especialistas.

## Plano de validação da Semana 4

1. Separar casos representativos que não foram usados para definir regras.
2. Comparar o modelo selecionado com média móvel de três meses.
3. Registrar WAPE por SKU e distribuição da confiança.
4. Revisar SKUs de ruptura, excesso, pressão de capacidade e baixa visibilidade.
5. Medir tempo de análise antes e depois do protótipo.
6. Registrar aceitação, alteração e rejeição das recomendações.
7. Documentar previsões corretas, falhas, limitações e mudanças realizadas.
8. Confirmar que dados insuficientes resultam em investigação, não em quantidade inventada.

## Decisão humana

A saída é uma sugestão para análise. O responsável continua decidindo se produz, quanto produz e quando executa, considerando informações externas, capacidade real e prioridades comerciais não disponíveis no protótipo.
