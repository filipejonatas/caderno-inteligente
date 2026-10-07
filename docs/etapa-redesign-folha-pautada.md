# Etapa: redesign "folha pautada"

Aplica o plano de design aprovado (A1 a D2). **Só apresentação e navegação:** nenhum cálculo, score, ranking, regra, previsão, recomendação ou contrato da API mudou, e nenhum campo foi criado ou removido da API.

## O que mudou

| Item | Resultado |
|---|---|
| A1 Fundação | `App.css` e `usability.css` (828 linhas, ~20 tamanhos de fonte, 56 cores, 8 raios, 11 `!important`) viraram **um** arquivo, `frontend/src/styles.css`: tokens no topo, 5 tamanhos de texto, 3 raios, 5 espaçamentos, uma paleta, **zero `!important`** |
| A2 Identidade | Folha pautada: fundo papel, tinta, pauta e azul de caneta; títulos em Source Serif 4, interface em Source Sans 3. Sem sombras, gradientes nem ícones decorativos no menu. As fontes são **embutidas no pacote** (`@fontsource`), porque a política de segurança da publicação (`vercel.json`) só aceita fontes do próprio domínio |
| A3 Cor | Cor só para urgência, estado do dado e ação principal. Selos cinza por padrão |
| B1 Fila | Uma linha por SKU: SKU e produto, ação e quantidade à direita, motivo abaixo, exceções em texto cinza. A **margem da linha** carrega a urgência (vermelha, âmbar ou tracejada quando não há previsão). Selos por linha: de 91 na página inteira para 28. A tabela continua semântica (cabeçalhos para leitor de tela) |
| B2 Início | Sem os 3 cartões: uma frase com os números, o primeiro SKU e a fila de 5 |
| B3 SKU | **Já estava feito** (resposta no topo e abas Resumo, Evidências, Parceiros e Impacto financeiro). Nesta etapa só ganhou o visual novo |
| C1 Comercial | 3 páginas, uma por visão: `/parceiros` (Oportunidades), `/carteira` (Parceiros) e `/canais` (Canais diretos). `?aba=parceiros` e `?aba=diretos` continuam abrindo e redirecionam |
| C2 Financeiro | O faturamento saiu de Planejamento e ganhou o grupo Financeiro |
| C3 Confiança e Bastidores | Confiança ficou só com a Validação. Auditoria, Execuções e Dados da planilha foram para Bastidores. Os blocos da Auditoria abrem recolhidos |
| C4 Cenários | Saiu do menu e abre pelo botão "Simular pesos" da fila, com "Voltar à fila" na página. `/cenarios` continua existindo |
| D1 e D2 | Critério de clareza por tela em [criterio-de-clareza.md](criterio-de-clareza.md), com teste automático. O orçamento de volume ficou como rede de segurança |

Menu: Início, Planejamento, Financeiro, Comercial, Acompanhamento, Confiança, Bastidores. Barra superior clara no desktop e gaveta no celular (até 820 px).

## Medição (mesma base, navegador, largura da janela do painel)

| Tela | Selos antes → depois | Palavras antes → depois | Altura (px) antes → depois |
|---|---|---|---|
| Fila (24 linhas) | 91 → 28 | 508 → 543 | 2.607 → 3.134 (ver nota) |
| Início | 14 → 14 | 257 → 251 | 1.437 → 1.381 |
| Detalhe do SKU CI-0014 | 5 → 5 | 148 → 143 | 1.205 → 986 |

Nota: a fila ficou mais alta (3.134 px medidos com a janela em 1000 px; o "antes" foi medido numa largura diferente, então a comparação não é exata). Cada linha ficou maior de propósito, com SKU e quantidade em fonte de leitura; o ganho é em selos e em hierarquia, não em altura. O volume de texto quase não mudou de propósito: o problema não era texto.

## Testes

- `contrast.test.ts` e `legibility.test.ts` agora leem `styles.css`; o primeiro cobre 20 pares de cor da paleta nova e o segundo exige que todo texto use a escala de 5 tamanhos.
- Novo `clarity.test.tsx` (critério D1).
- Atualizados porque o menu e as rotas mudaram de propósito: `navigation`, `routes`, `usability`, `channels`, `opportunities`, `revenue`, `keyboard`, `a11y`, `filters-states` e `volume-budget.json` (`/carteira` e `/canais` no lugar das abas).
- `npm run check`: 22 arquivos de teste passam, 21 testes Node passam, build e verificação de segredos do bundle passam.

## Limitações

- Não conferi 1440 px nem todas as telas no navegador: as capturas do painel saem pequenas. Vi a fila, o Início, o SKU e as Oportunidades em ~1000 px e a fila e o menu em 375 px. As demais telas (Faturamento, Validação, Guia, Auditoria, Casos, Decisões, Execuções) receberam o visual novo pelas mesmas classes e passaram nos testes, mas **não foram revistas visualmente**.
- Na fila, a margem vermelha agora marca só sinal principal crítico; sinal alto vira âmbar (decisão aprovada em 2026-10-07).
- A coluna de quantidade mostra "0" para SKU com ação "Sem ação necessária" (valor real da recomendação, não dado ausente).
