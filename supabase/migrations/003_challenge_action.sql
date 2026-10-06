-- Etapa 13: rótulo de ação do desafio registrado junto com a decisão humana.
-- Aditiva: decisões anteriores permanecem com challenge_action = null; a API detecta a coluna e funciona antes da migração.
alter table public.feedback add column if not exists challenge_action text;

comment on column public.feedback.challenge_action is 'Código do rótulo de ação do desafio mostrado ao usuário no momento da decisão (ex.: priorizar_producao); null em decisões anteriores.';
