-- Etapa 6: snapshot ampliado para comparação entre execuções.
-- Aditiva: execuções anteriores permanecem com comparison = null e continuam comparáveis apenas no ranking.
alter table public.runs add column if not exists comparison jsonb;

comment on column public.runs.comparison is 'Previsão, recomendação por SKU e cobertura B2B2C por parceiro preservadas para comparação; null em execuções anteriores.';
