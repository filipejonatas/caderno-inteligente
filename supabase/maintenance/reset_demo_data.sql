-- Limpeza de dados de demonstração no Supabase (SQL Editor).
-- ATENÇÃO: apaga TODAS as decisões, casos, históricos de casos e execuções registradas.
-- Não altera a estrutura das tabelas nem a planilha de origem (que fica no deploy do backend).
-- Antes de executar, exporte as tabelas pelo Table Editor (Export to CSV) se precisar de backup.
-- Alternativa com backup automático em JSON: python scripts/reset_demo_data.py --postgres --confirm

begin;
select 'feedback' as tabela, count(*) from public.feedback
union all select 'cases', count(*) from public.cases
union all select 'case_history', count(*) from public.case_history
union all select 'runs', count(*) from public.runs;

truncate table public.case_history, public.cases, public.feedback, public.runs restart identity;
commit;
