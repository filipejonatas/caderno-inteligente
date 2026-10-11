# Atualizar a base pela tela: resumo

Especificação: [discovery-upload-planilha.md](discovery-upload-planilha.md). Decisões D1–D11 e R1: [decisions.md](decisions.md). Rotas: [api.md](api.md). Publicação: [deploy-vercel-supabase.md](deploy-vercel-supabase.md), seção 7.

## O que mudou

- **Envio de planilha pela tela** (`/dados/atualizar`): prévia sem gravação, aplicação em duas etapas e histórico das 20 últimas versões, com "Voltar para esta versão" e "Restaurar base original".
- **Uma regra só (D1):** cada aba enviada substitui a atual; nas abas mensais (`Vendas_24m`, `Sell_In`, `Sell_Out`), só os meses enviados entram ou são trocados. Aba ausente fica como está.
- **Data de planejamento derivada (D3):** `reference_date = "auto"` é a primeira semana de `Capacidade_Semanal`, a mesma em todo o motor. O envio é bloqueado se as vendas avançarem e a data não; quando ela avança, estoque, carteira, OPs e capacidade vão juntos (D5).
- **Casos congelados (D8):** com a base diferente da congelada, os 20 casos de origem `base` aparecem como "base anterior" e saem da contagem.
- **Segurança:** só com `DATA_SOURCE=banco`, `WRITE_ENABLED=true` e login (sempre, mesmo com `AUTH_REQUIRED=false`); até 4 MB; ZIP e XML verificados.
- **Correções no caminho:** referência única também nos eventos (R1) e OPs concluídas e pedidos encerrados não contam como abertos.

## Como usar

1. Publicação: migração `005`, `DATA_SOURCE=banco`, `WRITE_ENABLED=true`, `AUTH_SECRET`, `scripts/import_workbook.py` e `scripts/create_user.py` ([deploy](deploy-vercel-supabase.md), seção 7).
2. Entre em Bastidores › Atualizar dados com o usuário de demonstração.
3. Escolha o arquivo e leia a prévia (erros e avisos por célula, nova data de planejamento, efeito na fila). Para testar, use o [pacote de exemplo fictício](exemplos/README.md), `docs/exemplos/atualizacao-2026-10.xlsx`.
4. "Aplicar e recalcular" e "Confirmar e aplicar".
5. **Ao final de qualquer teste, "Restaurar base original".** O envio vale para todos os usuários.

Pela API: `POST /api/dataset/preview` e `/api/dataset/apply` com o arquivo no corpo bruto ([api.md](api.md)).

## Números reais, antes e depois

Conferidos no app real com `DATA_SOURCE=banco` (SQLite local) e o pacote de exemplo.

| Medida | Base original | Depois de aplicar o exemplo |
|---|---|---|
| Data de planejamento | 14/09/2026 | 12/10/2026 |
| Vendas até | 2026-08 | 2026-09 |
| Primeiro mês da previsão | 2026-09 | 2026-10 |
| Demanda além da carteira, 12 a 31/10 (semanas do plano) | — | 7.980 un. |
| Demanda total (carteira + previsão), mesmo período | — | 17.042 un. |
| Cinco primeiros da fila | CI-0004, CI-0041, CI-0011, CI-0017, CI-0025 | CI-0014, CI-0004, CI-0042, CI-0036, CI-0041 |
| SKUs em risco de ruptura (Início) | 21 | 15 |
| SKUs com falta projetada sem novas ordens (prévia) | 44 | 43 |
| Decisões de hoje | 26 (até 21/09) | 26 (até 19/10) |
| Casos congelados contados | 34 de 34 | 14 de 34 (20 "base anterior") |
| Prévia / aplicação (SQLite local) | — | cerca de 3,4 s / 4,4 s |

Depois de "Restaurar base original": referência, fila, hash e 34 de 34 voltam aos valores da primeira coluna.

Efeitos de R1 na **base original** (referência única nos eventos), medidos sobre os 43 SKUs da fila:

| Rótulo | Antes | Depois |
|---|---|---|
| Priorizar produção | 10 (23,3%) | 16 (37,2%) |
| Teto de 40% (sobre a fila) | atendido | atendido |

O top 10 da fila não mudou. Sobre os 50 SKUs, Priorizar produção vai de 12 para 22.

Os 7.980 un. são só a demanda além da carteira nas semanas do plano de 12/10 a 31/10; somada à carteira, a demanda total (carteira + previsão) no mesmo período é de 17.042 un. (`daily_demand`).

## Limitações

- **Só meses fechados:** as abas mensais aceitam apenas meses anteriores ao da data de planejamento.
- **Mês substituído vai para o fim da aba:** a ordem das linhas muda, o conteúdo é o mesmo.
- **Tempo no Supabase não medido:** os 3,4 s e 4,4 s são do SQLite local. Meça na primeira vez na Vercel.
- **Janelas fixas da previsão (D11):** `forecast_engine.json` e `partner_projection.json` não acompanham o mês novo; os erros exibidos continuam os da janela configurada.
- **Sobrescreve o cadastro da tela (D10):** a prévia avisa quais SKUs.
- **Só com banco:** com a planilha empacotada, o botão aparece desabilitado com o motivo.
- **O exemplo é fictício:** não é dado real, e a prévia o marca como tal.
- **"n/a" em célula numérica:** é lido como vazio (aviso `MISSING_VALUES`, não erro); dado ausente nunca vira zero.
- **Colunas completas:** a planilha precisa trazer todas as colunas da aba atual.
- Toda saída continua exigindo revisão humana; o envio não decide nada sozinho.

## Commits sugeridos

| Subetapa | Mensagem |
|---|---|
| U.0 | `feat(upload.0): data de referência derivada dos dados e validação com endereço` |
| U.1 | `feat(upload.1): leitura segura de planilha enviada, mescla por aba e versões (migração 005)` e `feat(upload.1): prévia e aplicação de planilha com versões` |
| U.2 | `feat(upload.2): tela de atualização da base` |
| U.3 | `feat(upload.3): pacote de exemplo fictício de outubro e gerador`, `feat(upload.3): hash da base ativa e casos da base anterior`, `test(upload.3): ponta a ponta com o pacote de exemplo` e `docs(upload.3): API, banco, decisões e roteiro da atualização pela tela` |
