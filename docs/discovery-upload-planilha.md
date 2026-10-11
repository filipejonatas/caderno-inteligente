# Discovery: atualizar a base pela tela (anexar planilha)

> Base para uma IA (ou pessoa) implementar a funcionalidade. Escrito em 11/10/2026; a entrega é em 17/10/2026.
> Os números vêm da planilha atual (`data/source/Base de Dados - Caderno Inteligente.xlsm`, sha256 `03fa0ed4…`) e de
> execuções do pipeline em modo somente leitura, com scripts temporários fora do repositório. Nenhum código foi implementado.
> Este documento define **o quê**, **por quê** e **como verificar**. O plano de implementação vem depois das decisões da seção 6.

**Pedido do usuário:** "um botão de anexar planilha com os dados necessários pro motor calcular […] a planilha que temos
tem os dados até o mês 08, mas já estamos no mês 10. Então deve ter um botão onde a pessoa possa anexar a planilha com os
dados do mês 09 e 10 e o motor calcular tudo."

## 0. Como usar este documento

1. Leia a seção 1 antes de qualquer código. O ponto mais perigoso não é o upload em si: são as **datas fixas** (seção 2, P1).
   Com dados novos, o motor continua calculando **sem erro**, mas com números errados.
2. Leve as decisões da seção 6 ao usuário antes de começar. D1, D3 e D4 definem o que a planilha enviada precisa conter.
3. Siga a ordem da seção 7. Cada subetapa tem critérios de aceite verificáveis (seção 5).
4. As regras do projeto continuam valendo (`docs/historico.md`, `docs/discovery-etapa-16.md` §0):
   - dado ausente nunca vira zero;
   - todo campo novo lido pelo frontend entra em `frontend/src/test/contract-keys.json`;
   - toda rota nova entra em `frontend/src/test/volume-budget.json`;
   - a planilha empacotada em `data/source/` **nunca** é alterada. Ela continua sendo a base dos testes e a "base original" da demonstração;
   - o usuário faz o commit.

## 1. Fatos verificados

### 1.1 O que já existe e pode ser reaproveitado

| # | Fato (arquivo:linha) | Reaproveitamento |
|---|---|---|
| E1 | `ingestion.load_workbook` (`src/caderno_inteligente/ingestion.py:12-25`) recebe um **caminho**, exige o sufixo `.xlsm` (`:18`), pula 2 linhas de título (`HEADER_ROW_OFFSET = 2`, `:6`) e lê as 12 abas de `SCHEMAS` mais `Precos_Produtos`, que é opcional (`:7`). | A leitura serve, mas precisa de três ajustes: aceitar bytes (`pd.ExcelFile` aceita `BytesIO`), aceitar `.xlsx` e não exigir todas as abas no modo incremental. |
| E2 | `schemas.py:13-26` define, por aba, as colunas obrigatórias, a chave, as colunas de data e as não negativas. `FOREIGN_KEYS` (`:28-34`) liga as abas a `Produtos` e `Parceiros_Canais`. | É a base da validação do upload. Faltam a **política por aba** (série × fotografia × cadastro, seção 1.3) e a chave de mês de cada série. |
| E3 | `validation.validate_dataset` (`src/caderno_inteligente/validation.py:23-66`) devolve erros só com **contagens** (`DUPLICATE_KEY count`, `INVALID_DATE count`, `ORPHAN_KEY`), sem o número da linha. | Serve como trava. Para a tela de upload, falta o detalhe por linha ("Vendas_24m, linha 9.604: Mês inválido"). |
| E4 | `normalise_dataset` converte números com `pd.to_numeric(errors="raise")` (`transformations.py:27`). A API chama `normalise_dataset` **antes** de `validate_dataset` (`backend/main.py:250-251`), e `scripts/import_workbook.py:52` faz o mesmo. | Uma planilha com texto numa coluna numérica gera **exceção (500)**, e não erro de validação. O upload precisa validar antes de normalizar, ou capturar o erro. |
| E5 | `DatasetStore` (`src/caderno_inteligente/dataset_store.py`) grava uma tabela por aba (linha em JSON) e remonta os mesmos DataFrames. `import_dataset(replace=True)` apaga e regrava tudo numa transação e incrementa `dataset_version` (`:317-334`). | É o núcleo do "aplicar". Com `replace`, o cadastro feito pela tela é perdido e não sobra histórico das bases anteriores. |
| E6 | `dataset_version` + `_dataset_version()` com checagem a cada 5 s (`backend/main.py:180-197`) + `_source_signature()` (`:200-203`) + `_pipeline_signature()` (`:206-208`). | Depois do upload, o cache se invalida sozinho em todas as instâncias da Vercel em até 5 s. Na instância que gravou, basta chamar `invalidate_dataset_version()`. **Isso só vale com `DATA_SOURCE=banco`.** |
| E7 | `DATA_SOURCE=planilha` (padrão) lê o arquivo empacotado (`backend/main.py:211-215`). `banco` lê as tabelas da migração 004 (`supabase/migrations/004_dataset_and_auth.sql`). | Na Vercel, o sistema de arquivos é somente leitura (só `/tmp` aceita escrita, e `/tmp` não sobrevive entre invocações). Por isso **o upload só funciona com `DATA_SOURCE=banco`**. |
| E8 | O cadastro de SKU (`backend/registry.py:112-246`) já faz "prévia em memória → validar → gravar → registrar quem alterou" (`validated_rows` `:180-192`, `apply_sku_rows`, `sku_changes`). As rotas de escrita exigem `WRITE_ENABLED` e `DATA_SOURCE=banco` (`editor`, `:139-143`). O login só é exigido com `AUTH_REQUIRED=true` (`:55-58`, `:123-125`); sem ele, o usuário é anônimo (`OPEN_USER`). | O mesmo padrão serve para o upload: prévia, gravação, trilha, `write_access`, `database_mode` e `current_user`. |
| E9 | `scripts/import_workbook.py` importa a planilha inteira pela linha de comando, com `--replace`. | O endpoint de upload é a versão "pela tela" deste script, mais a prévia, o modo incremental e o histórico de versões. |
| E10 | O middleware rejeita qualquer POST/PUT com `Content-Length` acima de **16 KB** (`backend/security.py:24`, `:163-168`). | Um upload de 420 KB é barrado antes de chegar à rota. A rota de upload precisa de um limite próprio. |
| E11 | `python-multipart` está instalado no `.venv` só porque o `streamlit` depende dele. Não está em `requirements.txt` (lista: pandas, openpyxl, fastapi, uvicorn, psycopg). | `UploadFile`/`Form` do FastAPI quebraria na Vercel. Duas saídas: receber o corpo bruto (`application/octet-stream`), que não precisa de dependência nova, ou acrescentar `python-multipart` ao `requirements.txt`. |
| E12 | A tela "Dados da planilha" (`/qualidade`, `frontend/src/pages/QualityPage.tsx`) está no menu **Bastidores** (`frontend/src/components.tsx:78,83`). O orçamento dela é `fixed 70, numbers 8, blocks 2, columns 5, alerts 0` (`volume-budget.json`). | Os 2 blocos já estão usados, então o botão não cabe dentro de `/qualidade` sem estourar o orçamento. Recomendação: uma rota nova no mesmo menu (seção 4.6). |

### 1.2 A base atual

| # | Fato verificado | Consequência |
|---|---|---|
| F1 | O arquivo tem 418.622 bytes; descompactado, 3,86 MB em 66 entradas. A maior entrada é `Vendas_24m` (2,58 MB de XML). **Não há `vbaProject.bin`**: apesar da extensão `.xlsm`, não existe macro. | O arquivo cabe com folga no limite de corpo da Vercel (~4,5 MB). Uma base com o dobro de meses continua abaixo de 1 MB compactada. |
| F2 | A pasta tem 18 abas. O motor lê 13. Não são lidas: `Dicionario_Dados`, `Historico_Estoque`, `Capacidade_Producao`, `Indicadores_Atuais` e `LEIA_ME`. | O modelo para download pode trazer só as 13 abas lidas. As outras não afetam o cálculo. |
| F3 | Séries mensais: `Vendas_24m` com 9.600 linhas (8 clientes × 50 SKUs × 24 meses, de 2024-09 a **2026-08**); `Sell_In` e `Sell_Out` com 600 linhas cada (2025-09 a 2026-08). | O "mês 08" do pedido do usuário está confirmado. |
| F4 | Fotografias datadas de meados de setembro: `Carteira_Pedidos` com 53 pedidos, todos "Confirmado", com datas prometidas de 13/09 a 06/10; `Ordens_Producao` com 34 OPs, conclusão prevista de 22/09 a 12/10; `Capacidade_Semanal` com 16 semanas, de **14/09** a 28/12/2026; `Forecast_Comercial` com 150 linhas, de **Out/26 a Dez/26**, no formato "Out/26"; `Parceiros_Canais` com última compra entre 24 e 31/08. | A base é um retrato de **14/09/2026**. A data de planejamento é a primeira semana da capacidade (`docs/decisions.md:146`, decisão D3). |
| F5 | `Precos_Produtos` tem 50 linhas, todas com vigência 01/09/2024. O preço vigente é o último por vigência (`backend/main.py:224-229`). | Preços aceitam acréscimo (nova vigência) sem quebrar nada. |
| F6 | `Produtos` repete `Estoque atual`, `Cobertura (dias)` e `Venda média/dia`, que também estão em `Estoque_Atual`. O indicador usa `Estoque_Atual` para o estoque e `Produtos` para o resto (`indicators.py:123-125`). | Se a pessoa atualizar só `Estoque_Atual`, `Produtos.Estoque atual` fica velho sem efeito no cálculo. Vale um aviso, não um erro. |
| F7 | Tempo medido na máquina local: `load_workbook` leva 3,2 s; `_build_pipeline` completo leva 5,0 s. | Prévia (ler + validar + recalcular) mais aplicação cabem nos 60 s de `maxDuration` (`vercel.json`), mesmo com partida a frio. A gravação no Postgres (~11,7 mil linhas JSON) ainda precisa ser medida (risco R3). |

### 1.3 Natureza de cada aba

| Aba | Natureza | Chave | Política no upload incremental | O que precisa vir para "dados até outubro" |
|---|---|---|---|---|
| `Vendas_24m` | Série mensal | Mês + SKU + Cliente/Canal | Acrescentar meses novos; mês já existente é **substituído** por inteiro | Setembro fechado. Outubro só se estiver fechado (D4). |
| `Sell_In` | Série mensal | Mês + Cliente + SKU | Igual | Setembro |
| `Sell_Out` | Série mensal | Mês + Cliente + SKU | Igual | Setembro (se o parceiro informou) |
| `Estoque_Atual` | Fotografia | SKU | Substituir a aba | **Obrigatória**: estoque na nova data de planejamento |
| `Carteira_Pedidos` | Fotografia | Pedido | Substituir | **Obrigatória**: os pedidos de setembro já venceram |
| `Ordens_Producao` | Fotografia | Ordem | Substituir | **Obrigatória**: as OPs com conclusão até 12/10 já terminaram |
| `Capacidade_Semanal` | Fotografia (calendário) | Semana + Linha | Substituir | **Obrigatória**: é dela que sai a nova data de planejamento |
| `Forecast_Comercial` | Fotografia (revisão S&OP) | SKU + Mês | Substituir | Recomendada (Nov/26 em diante) |
| `Produtos` | Cadastro | SKU | Substituir | Só se mudou algo |
| `Lead_Times` | Cadastro | SKU | Substituir | Só se mudou |
| `Parceiros_Canais` | Cadastro | Código | Substituir | Só se mudou |
| `Precos_Produtos` | Cadastro com vigência | SKU (+ vigência) | Substituir | Só se mudou |
| `Calendario_Eventos` | Cadastro | Evento | Substituir | Só se mudou |

Regra resultante: **mandar só as séries não basta.** Para o motor ficar coerente com "outubro", a pessoa precisa mandar
setembro nas séries **e** as quatro fotografias de outubro (estoque, carteira, OPs e capacidade).

## 2. Problemas e causa raiz

### P1. Datas fixas: com dados novos o motor erra em silêncio

**Prova (simulação somente leitura).** Copiamos as vendas de agosto para setembro e outubro e rodamos o pipeline sem
mudar mais nada:

| | Base atual | Vendas até out/26, referência fixa |
|---|---|---|
| Primeiros meses da previsão | 2026-09, 10, 11 | **2026-11, 12, 2027-01** |
| Demanda prevista entre 14/09 e 31/10 (soma dos SKUs) | 41.592 un. | **0 un.** |
| Erros de validação | 0 | 0 |
| Tamanho da fila | 43 | 43 |

**Causa raiz.**
- `config/supply_plan.json:2` e `supply_plan.py:29` fixam `reference_date = 2026-09-14`. A validação exige segunda-feira (`supply_plan.py:72-73`).
- A previsão começa no mês seguinte ao último mês de vendas (`official_forecast.py:102`). `daily_demand` só distribui a previsão a partir da referência (`supply_plan.py:140-148`).
- Resultado: o intervalo entre a referência fixa e o fim do último mês vendido fica **sem demanda prevista**. A projeção de estoque fica otimista, e nada avisa.

**Outros pontos presos à base atual:**

| Ponto | Onde | Com dados novos |
|---|---|---|
| OP com conclusão antes da referência entra como recebimento **no dia da referência** | `supply_plan.py:206` (`max(op["finish"], reference)`) | Se a referência avança e a aba de OPs não é atualizada, OPs já concluídas são somadas de novo a um estoque que já as contém (**dupla contagem**). |
| Pedido com data prometida anterior à referência vira "falta" na referência | `supply_plan.affected_orders`; `decide_by` limitado à referência (`docs/decisions.md:213`) | Uma carteira velha com referência nova gera "atrasos" falsos para todos os 53 pedidos. |
| A referência dos eventos é o fim do último mês de vendas, não a data de planejamento | `events.py:240-243` | Com vendas até setembro e capacidade a partir de 12/10, os eventos usariam 30/09 e o plano 12/10: duas "datas de hoje" na mesma tela. |
| `reference_month` de parceiros e canais = último mês faturado | `partner_insights.py:196,270`; `direct_channels.py:317` | Já deriva dos dados: funciona. |
| Janela de avaliação da previsão fixa (2025-11 a 2026-05) | `config/forecast_engine.json:29-31`; `official_forecast.py:59` | Não quebra: as origens continuam dentro da série. Mas o protocolo deixa de usar os meses novos. |
| Janela de avaliação da projeção no parceiro fixa (2026-02 a 2026-05) | `config/partner_projection.json:6-9` | Igual: não quebra, fica desatualizada. |
| Backtest rolante | `rolling_backtest.py:71-78` (origens contadas a partir do fim da série) | Já deriva dos dados: funciona com 26 meses. |
| Nome `Vendas_24m` | `schemas.py:15`; tabela `sheet_vendas_24m` | Só nome. Nenhum código limita a 24 meses; a previsão usa a série inteira e os indicadores, os últimos 3 meses (`indicators.py:14,64`). **Recomendação:** manter o nome da aba (é o contrato da planilha) e não cortar a série; aceitar 26 meses ou mais. |
| Calendário de capacidade de 16 semanas | `Capacidade_Semanal` | A extensão estimada (Etapa 16.5, `config/capacity_extension.json`) cobre além do calendário. A capacidade enviada precisa começar na nova referência. |
| `docs/etapa-16/antes.json`, `depois.json` e `antes-depois.md` | `scripts/snapshot_decisions.py:201-202` (nov/26, jan/27 fixos) | São registros históricos da base de 14/09 e não devem ser recalculados. O roteiro de demonstração (`docs/roteiro-demonstracao.md`) cita números dessa base. |

**Como a data de referência deve ser derivada.** A regra já está aprovada em `docs/decisions.md:146`: *a data de
planejamento é a primeira semana de `Capacidade_Semanal`*. Proposta:
1. `reference_date = min(Capacidade_Semanal["Semana inicial"])`, que precisa ser segunda-feira.
2. `config/supply_plan.json` passa a aceitar `"reference_date": "auto"` (novo padrão). Uma data explícita continua valendo como sobrescrita, para testes e para reproduzir a base congelada.
3. Uma única referência para todo o pipeline: eventos, alocação, capacidade, `decide_by` e "Decisões de hoje" recebem a mesma data. O fim do último mês de vendas fica só como `sales_reference_month`.
4. Regras de coerência que **bloqueiam** a aplicação:
   - o último mês de cada série precisa ser **anterior** ao mês da referência (só meses fechados; veja D4);
   - se o último mês de vendas avançou, a referência precisa ter avançado também (ou seja, `Capacidade_Semanal` nova);
   - nenhuma OP com status diferente de concluída pode ter conclusão prevista anterior à referência.
5. Avisos que **não bloqueiam**:
   - pedido confirmado com data prometida anterior à referência ("pedido vencido: confirme se já foi entregue");
   - mais de um mês entre o último mês de vendas e a referência;
   - `Produtos.Estoque atual` diferente de `Estoque_Atual`.

### P2. Os hashes de "qual base foi usada" ignoram o banco

**Sintoma.** Com `DATA_SOURCE=banco`, depois de um upload a Central de validação continuaria dizendo que a base é a
congelada (`source_matches_frozen: true`). A execução gravaria o hash do arquivo empacotado, e o benchmark não ficaria
marcado como desatualizado.

**Causa raiz.** Todos fazem o hash do arquivo `SOURCE`, não dos dados ativos: `backend/validation.py:52`,
`backend/forecast_lab.py:33-38`, `backend/model_benchmark.py:42-65`, `postgres_persistence.py:150` e
`backend/main.py:1010`. A limitação já está documentada (`docs/fase-3-banco-e-cadastro.md:94`), mas com o upload deixa
de ser detalhe.

**Solução.** Calcular um `content_sha256` do conjunto de dados ativo (hash do JSON canônico das abas, ou o sha256 do
arquivo enviado, guardado na versão) e expor uma função `active_source_hash()` usada por esses cinco pontos.

### P3. Os casos congelados descrevem a base de 14/09

`config/validation_center.json` tem 34 casos: 20 de origem `base` (por exemplo VC-04, VC-20 e VC-33 sobre CI-0041) e 14
sintéticos. O congelamento compara o hash (`validation_center.py:650-655`) e já mostra a nota "A planilha mudou desde o
congelamento". Com uma base nova, os 20 casos de base vão falhar ou não ser encontrados, e **isso é o esperado**. Os 14
sintéticos continuam valendo.

**Solução.** Quando `source_matches_frozen` for falso, a Central mostra os casos de base como "referem-se à base de
14/09/2026", fora da contagem de aprovados e falhos. Os sintéticos continuam contando. **Não** recongelar os casos
automaticamente (D8).

### P4. Validação sem endereço

Os erros dizem "INVALID_DATE em Vendas_24m, 3 ocorrências" (`validation.py:48`), sem dizer **onde**. Para quem corrige a
planilha no Excel, isso não basta. A prévia precisa listar até N exemplos por erro, com a aba, a linha do Excel (índice
+ 4, porque o cabeçalho fica na linha 3), a coluna e o valor recebido.

### P5. Leitura frágil quanto ao layout

`HEADER_ROW_OFFSET = 2` (`ingestion.py:6`) supõe o título nas linhas 1 e 2 e o cabeçalho na 3. Uma planilha "limpa", com
o cabeçalho na linha 1, vira `MISSING_COLUMNS` em todas as abas. **Solução:** detectar a linha do cabeçalho (a primeira
das 5 primeiras linhas que contém as colunas obrigatórias) e dizer na prévia qual linha foi usada.

## 3. Opções de produto

| | (A) Substituir a base inteira | (B) Incremental (merge) | (C) Uma regra só: a planilha traz as abas que quiser |
|---|---|---|---|
| O que a pessoa envia | A pasta completa, com as 13 abas e todo o histórico | Só os meses novos e as fotografias atualizadas | Qualquer subconjunto das 13 abas. Séries: os meses enviados entram ou substituem os existentes. Fotografias e cadastros: a aba enviada substitui a atual. Aba ausente: fica como está. |
| Atende ao exemplo "meses 09 e 10" | Só se a pessoa montar a base completa | Sim | Sim |
| Atende a "recebi a base nova inteira" | Sim | Não diretamente | Sim: a pasta completa é só o caso "todas as abas presentes" |
| Complexidade | Baixa: `import_dataset(replace=True)` já existe | Média: regras por aba e chave de mês | Média: igual a B, porque A sai de graça |
| Risco de erro do usuário | Esquecer meses antigos apaga histórico (pego pela validação só se ficar com menos de 13 meses) | Mandar só vendas e esquecer as fotografias (pego pela regra de coerência de P1) | Os dois riscos, os dois cobertos pelas regras de P1 e pela prévia |
| Prévia útil | "Tudo muda" | Mostra exatamente meses novos, abas substituídas e SKUs novos | Igual a B |

**Recomendação: (C).** Custa o mesmo que (B), cobre o pedido literal ("anexar os meses 09 e 10") e também a base
completa, com uma única regra que se explica numa frase: *"cada aba enviada substitui a atual; nas abas mensais, só os
meses enviados são substituídos"*.

**Versionamento (vale para qualquer opção).** Cada aplicação grava uma versão com: quem enviou, quando, nome do arquivo,
sha256, tamanho, resumo da prévia, data de referência resultante e um **snapshot completo do conjunto resultante**
(JSON das abas comprimido com gzip, estimado em menos de 1 MB). Voltar para uma versão reimporta esse snapshot. Não é
preciso reaplicar a sequência de uploads. "Restaurar a base original" reimporta o arquivo empacotado.

**Prévia antes de aplicar (dry-run).** O mesmo endpoint, sem confirmação, devolve:
- por aba: política aplicada, linhas atuais → resultantes, meses acrescentados, meses substituídos, SKUs ou pedidos novos e removidos;
- erros que bloqueiam e avisos, com linha e coluna;
- data de referência atual → nova;
- efeito resumido no motor: tamanho da fila, os 5 primeiros SKUs antes e depois, número de SKUs com falta.

## 4. Recomendação de desenho

### 4.1 Fluxo

1. A pessoa entra em **Bastidores › Atualizar dados** (rota nova) e vê a base ativa: versão, data de referência, último mês de vendas, quem enviou e quando.
2. Baixa o **modelo** (opcional): um `.xlsx` gerado da base ativa, com as 13 abas, título nas linhas 1 e 2 e cabeçalho na linha 3.
3. Anexa o arquivo (`.xlsx` ou `.xlsm`, até 4 MB). A tela mostra a **prévia** (passo 3 da seção 3).
4. Se houver erro, a tela mostra a lista por aba e linha, sem botão de aplicar. Se só houver avisos, a pessoa confirma com "Aplicar e recalcular".
5. Depois de aplicar, a API grava a versão, invalida o cache e a tela mostra "Base atualizada: referência 12/10/2026, vendas até set/26", com links para a fila e para "Dados da planilha".
6. O histórico lista as versões, cada uma com "Voltar para esta versão", e há um botão "Restaurar base original".

### 4.2 API (sem estado entre chamadas, compatível com a Vercel)

| Método e rota | Função |
|---|---|
| `GET /api/dataset` | Versão ativa, `reference_date`, `sales_last_month`, `content_sha256`, origem (`original` ou `upload`), quem e quando, e `upload_enabled` com o motivo quando falso (`planilha`, `WRITE_ENABLED=false`, sem login) |
| `GET /api/dataset/template` | Modelo `.xlsx` gerado da base ativa |
| `POST /api/dataset/preview` | Corpo bruto `application/octet-stream` e cabeçalho `X-Filename`. Devolve a prévia e o `sha256` do arquivo. Nada é gravado. |
| `POST /api/dataset/apply` | Mesmo corpo, com o cabeçalho `X-Confirm-Sha256` igual ao da prévia. Revalida tudo, grava e devolve a nova versão. Reenviar o arquivo evita guardar estado pendente entre invocações. |
| `GET /api/dataset/versions` | Histórico (sem o conteúdo) |
| `POST /api/dataset/versions/{id}/restore` e `POST /api/dataset/restore-original` | Reversão |

- Limite de corpo próprio de **4 MB** para `preview` e `apply`, com exceção explícita no middleware de 16 KB (`security.py:163-168`).
- Corpo bruto em vez de `multipart/form-data`: não depende de `python-multipart` (E11).

### 4.3 Armazenamento (migração `005_dataset_uploads.sql`)

- Tabela `dataset_versions`: `id`, `created_at`, `user_email`, `action` (`upload`, `restore` ou `original`), `filename`, `file_sha256`, `size_bytes`, `content_sha256`, `reference_date`, `sales_last_month`, `summary jsonb` (a prévia), `snapshot bytea` (gzip). RLS ligado, como nas tabelas da 004.
- `dataset_version` ganha `active_version_id`.
- Guardar o snapshot no Postgres, e não no Supabase Storage: o Storage exigiria chave de serviço e um cliente novo. Com cerca de 1 MB por versão, os 500 MB do plano gratuito comportam centenas de versões. Opcional: guardar só as 20 últimas.
- O SQLite local ganha a mesma tabela em `_SQLITE_SCHEMA` (`dataset_store.py:220-228`).
- A gravação reutiliza `import_dataset(replace=True)` com o conjunto **já mesclado em memória**, na mesma transação que a versão.

### 4.4 Segurança

| Ameaça | Medida |
|---|---|
| Macro | O openpyxl não executa VBA e só preserva o `vbaProject` com `keep_vba=True`. A base atual nem tem macro (F1). Nunca devolver o arquivo enviado para download; o modelo é gerado como `.xlsx`. |
| Zip bomb | Antes do openpyxl, abrir com `zipfile` e recusar: mais de 300 entradas, mais de 50 MB descompactados (a base atual tem 3,86 MB) ou razão de compressão acima de 100 numa entrada. |
| XML malicioso (entity expansion) | `openpyxl.xml.DEFUSEDXML` é **False** no `.venv`. Acrescentar `defusedxml` ao `requirements.txt`: o openpyxl passa a usá-lo sozinho. |
| Tipo falso | Conferir a assinatura ZIP (`PK\x03\x04`) e a presença de `xl/workbook.xml`. Recusar `.xls`, `.csv` e o resto. |
| Tamanho | Até 4 MB no corpo (abaixo dos ~4,5 MB da Vercel); até 50 mil linhas por aba. |
| Quem envia | Exigir `WRITE_ENABLED` (403), `DATA_SOURCE=banco` (409) e **login sempre**, mesmo com `AUTH_REQUIRED=false` (D6). Trocar a base muda todas as recomendações; é mais sensível que editar um SKU. |
| Auditoria | `dataset_versions.user_email`, mais log `dataset_upload action=... version=... sha=...` sem conteúdo. |
| Base quebrada | Validação completa, mais a execução do pipeline na prévia. Se o pipeline falhar na prévia, a aplicação é bloqueada. A reversão fica sempre disponível. |
| Concorrência | `apply` confere se a versão ativa ainda é a da prévia (`expected_version`). Se não for, devolve 409 "outra pessoa atualizou a base; refaça a prévia". |

### 4.5 Ajustes no motor (independentes do botão)

1. A referência sai dos dados (P1, regra 1 a 3), com as regras de coerência (P1, regras 4 e 5) dentro de `validate_dataset` ou num `validate_coherence` novo.
2. Validar antes de normalizar, ou capturar o `to_numeric(errors="raise")` (E4).
3. Erros com endereço (P4) e cabeçalho detectado (P5).
4. `active_source_hash()` (P2) e casos de base fora da contagem quando a base mudou (P3).

### 4.6 Experiência

- **Onde:** rota nova `/dados/atualizar`, no menu Bastidores (`components.tsx:83`), ao lado de "Dados da planilha". Ela ganha a própria entrada no `volume-budget.json` (sugestão: `fixed 90, numbers 10, blocks 3, columns 5, alerts 1`). Em `/qualidade`, só a linha de intenção muda para citar a referência ("Base de 12/10/2026"), dentro do orçamento atual.
- **Sem permissão:** o botão aparece desabilitado com o motivo, vindo de `upload_enabled`: "Publicação somente leitura", "Lendo a planilha empacotada (DATA_SOURCE=planilha)" ou "Entre com seu usuário".
- **Mensagens de erro:** uma linha por erro, com a aba, a linha do Excel, a coluna, o problema e o valor. Até 5 exemplos por código e "mais 37 iguais".
- **Depois de aplicar:** um aviso fixo de uma linha no topo das telas por 24 h ("Base atualizada em 11/10 por fulano; referência 12/10/2026"), que cabe no `alerts: 1` das rotas principais.
- **Pacote de exemplo:** sem um arquivo de outubro, ninguém consegue testar o botão. Veja D9.

## 5. Critérios de aceite verificáveis

1. **Referência derivada:** com `reference_date: "auto"`, a base original continua com referência 14/09/2026 e os snapshots de `scripts/snapshot_decisions.py` ficam idênticos a `docs/etapa-16/depois.json`, sem regressão.
2. **Regra de coerência:** a planilha de teste com vendas até out/26 e capacidade a partir de 14/09 é **bloqueada** com a mensagem "Vendas vão até out/26, mas a data de planejamento é 14/09/2026; envie Capacidade_Semanal, Estoque_Atual, Carteira_Pedidos e Ordens_Producao atualizadas". Hoje ela passa com 0 erro e 0 unidade prevista no intervalo (P1).
3. **Pacote coerente:** com o pacote de exemplo de outubro (setembro nas séries + 4 fotografias a partir de 12/10), a previsão começa em 2026-10, a demanda prevista entre a referência e 31/10 é maior que 0 para todo SKU ativo com histórico, e nenhuma OP aparece como recebida antes da referência.
4. **Incremental:** enviar só `Vendas_24m` com 2026-09 (e as fotografias) resulta em 25 meses, com 2024-09 a 2026-08 iguais ao original, byte a byte por linha.
5. **Substituição de mês:** reenviar 2026-09 com valores diferentes substitui o mês, sem duplicar a chave.
6. **Prévia sem efeito:** `POST /api/dataset/preview` não altera `dataset_version` (teste).
7. **Erro com endereço:** uma planilha com "abc" em `Vendas_24m!D10` devolve 422 com `{sheet: "Vendas_24m", row: 10, column: "Quantidade faturada", value: "abc"}`, e não 500.
8. **Segurança:** arquivo com mais de 4 MB → 413; ZIP com 60 MB descompactados → 422; `.csv` renomeado para `.xlsx` → 422; `WRITE_ENABLED=false` → 403; `DATA_SOURCE=planilha` → 409; sem token → 401.
9. **Reversão:** aplicar, voltar para a versão anterior e restaurar a original devolvem `content_sha256` iguais aos de antes (teste de ida e volta).
10. **Cache:** depois de `apply`, `GET /api/priorities` reflete a base nova na mesma instância. Em outra instância, reflete em até 5 s (teste com `_version_seen` zerado).
11. **Hash:** depois de um upload, `/api/validation/summary` devolve `source_matches_frozen: false` e mostra os casos de base fora da contagem; `POST /api/runs` grava o `content_sha256` ativo.
12. **Tela:** `npm run check` passa, com a rota nova no `volume-budget.json` e os campos novos no `contract-keys.json`.
13. **Testes atuais:** todos continuam lendo `data/source/…xlsm` e passando. Nenhum teste depende do banco ter recebido upload.

## 6. Decisões que o usuário precisa tomar

| ID | Decisão | Recomendação |
|---|---|---|
| D1 | Modo de envio: (A) só base completa, (B) só incremental ou (C) uma regra para os dois. | **(C)**: cada aba enviada substitui a atual; nas abas mensais, só os meses enviados são substituídos. |
| D2 | O upload exige `DATA_SOURCE=banco` na publicação. | **Sim.** É a única forma de persistir na Vercel. Com `planilha`, o botão aparece desabilitado com o motivo. É preciso confirmar se a publicação já roda com `banco`, o que não foi verificado aqui. |
| D3 | Data de referência = primeira semana de `Capacidade_Semanal` (`"auto"`), única para todo o motor, com bloqueio quando as vendas avançam e a referência não. | **Aprovar.** Reaproveita a decisão D3 já registrada em `docs/decisions.md:146`. |
| D4 | Mês corrente parcial (outubro, em 11/10) nas séries. | **Não aceitar:** séries só com meses fechados (anteriores ao mês da referência). No exemplo do usuário: setembro nas séries e as **fotografias de outubro**. Outubro entra quando fechar. |
| D5 | As quatro fotografias (estoque, carteira, OPs e capacidade) são obrigatórias quando a referência avança. | **Sim, obrigatórias.** Sem elas há dupla contagem de OPs e falsos atrasos (P1). |
| D6 | Quem pode enviar. | **Login sempre** para o upload (independente de `AUTH_REQUIRED`), mais `WRITE_ENABLED=true`. Criar um usuário de demonstração para os avaliadores com `scripts/create_user.py`. |
| D7 | Versionamento e reversão. | **Sim:** snapshot por versão, "Voltar para esta versão" e "Restaurar base original". Guardar as 20 últimas. |
| D8 | O que fazer com os casos congelados (VC-*) quando a base muda. | **Não recongelar.** Casos de base aparecem como "referem-se à base de 14/09" e saem da contagem; os 14 sintéticos continuam valendo. |
| D9 | Pacote de exemplo para testar o botão (setembro + fotografias de outubro). A base é fictícia e não existe dado real de setembro. | **Gerar** `docs/exemplos/atualizacao-2026-10.xlsx`, marcado como fictício no `LEIA_ME` e no nome. A regra "não criar dados sintéticos na base real" continua valendo: o exemplo **não** substitui `data/source/`. Quem gera os números (você ou o script, com regra documentada) precisa ser decidido. |
| D10 | Upload sobrescreve o cadastro de SKU feito pela tela. | **Sim, com aviso na prévia** ("3 SKUs editados pela tela serão substituídos pela planilha"). As exclusões lógicas (`active=false`) são mantidas para SKUs que continuam na planilha. |
| D11 | Janelas de avaliação fixas da previsão e da projeção no parceiro (`first_origin`/`last_origin`). | **Não mexer até 17/10.** Elas não quebram com dados novos. Fica registrado como limitação. |

## 7. Plano de subetapas sugerido e corte mínimo

| Subetapa | Conteúdo | Dias | Commit sugerido |
|---|---|---|---|
| U.0 | Referência `"auto"`, referência única no pipeline, regras de coerência, validar antes de normalizar, erros com linha, cabeçalho detectado. Testes com fixtures derivadas da base. | 1 | `feat(upload.0): data de referência derivada dos dados e validação com endereço` |
| U.1 | Leitura de bytes (`.xlsx`/`.xlsm`), checagens de ZIP, `defusedxml`, mescla por política de aba, `preview`/`apply`, limite de 4 MB, migração 005 e versões. | 1,5 | `feat(upload.1): prévia e aplicação de planilha com versões` |
| U.2 | Tela `/dados/atualizar` (estado da base, anexar, prévia, aplicar, histórico, restaurar), orçamento, contratos. | 1 | `feat(upload.2): tela de atualização da base` |
| U.3 | `active_source_hash`, casos de base fora da contagem, pacote de exemplo, docs (`api.md`, `fase-3`, `roteiro-demonstracao.md`) e smoke test na Vercel. | 0,5 | `feat(upload.3): hash da base ativa, exemplo e roteiro` |

São cerca de 4 dias. Começando em 12/10, termina em 15/10 e sobra 16/10 de folga.

**Corte mínimo viável (se o prazo apertar), nesta ordem de sacrifício:**
1. Tirar da prévia o "efeito no motor" (top 5 antes e depois). Ficam as contagens por aba e a referência.
2. Tirar o histórico completo. Ficam só "Voltar para a anterior" e "Restaurar base original".
3. Tirar o modelo gerado. O "modelo" passa a ser o download da planilha original empacotada.
4. **Nunca cortar:** U.0 (referência derivada e coerência), validação com bloqueio, login, restaurar original e as checagens de ZIP e tamanho. Sem U.0, o botão produz recomendações erradas sem avisar (P1).

## 8. Riscos

| # | Risco | Mitigação |
|---|---|---|
| R1 | A publicação não está com `DATA_SOURCE=banco`, ou a migração 004 não foi rodada no Supabase. | Verificar no primeiro dia; o passo a passo está em `docs/fase-3-banco-e-cadastro.md:74-90`. |
| R2 | Demonstração em 17/10 com uma base enviada durante os testes: os números do roteiro (CI-0041, R$ 64 mil etc.) mudam. | "Restaurar base original" antes da apresentação; o roteiro passa a ter esse passo. |
| R3 | A gravação de ~11,7 mil linhas JSON no Supabase a partir da Vercel pode ser lenta (`executemany` linha a linha, `dataset_store.py:330-331`). | Medir em U.1. Se passar de 15 s, usar `COPY` ou inserção em lote (`insert … select from jsonb_array_elements`). |
| R4 | Partida a frio, prévia e pipeline juntos podem passar dos 60 s. | Prévia sem o "efeito no motor" (corte 1). Medir na Vercel. |
| R5 | O pacote de exemplo parecer dado real. | Nome, `LEIA_ME` e aviso na prévia ("arquivo de exemplo fictício"). |
| R6 | Os 20 casos de base "falham" depois de um upload e passam a impressão de regressão. | D8: fora da contagem, com texto explícito. |
| R7 | Escopo: a Etapa 16 ainda pode ter correções pendentes do revisor. | U.0 vale sozinha (corrige um defeito real). U.2 e U.3 encolhem primeiro. |

## 9. Fora de escopo

- Editar células pela tela (só o cadastro de SKU já existente).
- Integração automática com ERP ou leitura agendada.
- Recongelar os casos de validação ou recalcular `docs/etapa-16/*`.
- Mudar o motor de previsão ou as janelas de avaliação (D11).
- Upload com `DATA_SOURCE=planilha` (gravar em `/tmp` não persiste na Vercel).
