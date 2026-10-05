import { useCallback, useMemo } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { api } from '../api';
import { Alert, Badge, EmptyState, ErrorState, LoadingState, MetricCard, PageIntro, ProgressBar } from '../components';
import { monthLabel } from '../components/CommercialMatrix';
import { useApiResource } from '../hooks/useApiResource';
import { usePageLoadStatus } from '../hooks/usePageLoadStatus';

export default function B2BPage({ refreshToken }: { refreshToken: number }) {
  const loader = useCallback((signal: AbortSignal) => api.partners(new URLSearchParams({ limit: '200' }), signal), []);
  const { data, error, loading, loadedAt, refresh } = useApiResource(loader, refreshToken);
  usePageLoadStatus(loading, error, loadedAt);
  const [params, setParams] = useSearchParams();
  const region = params.get('regiao') ?? '', channel = params.get('canal') ?? '', sort = params.get('ordem') ?? 'name';
  const update = (key: string, value: string) => { const next = new URLSearchParams(params); if (value) next.set(key, value); else next.delete(key); setParams(next, { replace: true }); };
  const regions = useMemo(() => [...new Set((data?.items ?? []).map(p => p.region).filter((x): x is string => !!x))].sort(), [data]);
  const channels = useMemo(() => [...new Set((data?.items ?? []).map(p => p.channel).filter((x): x is string => !!x))].sort(), [data]);
  const filtered = useMemo(() => (data?.items ?? []).filter(p => (!region || p.region === region) && (!channel || p.channel === channel)).sort((a, b) => sort === 'coverage' ? b.coverage - a.coverage || a.name.localeCompare(b.name) : sort === 'opportunities' ? b.action_counts.avaliar_reposicao - a.action_counts.avaliar_reposicao || a.name.localeCompare(b.name) : a.name.localeCompare(b.name)), [data, region, channel, sort]);
  if (!data) return error ? <ErrorState message={error} onRetry={() => void refresh()} /> : <LoadingState />;
  return <>
    <PageIntro eyebrow="Colaboração comercial" title="Parceiros e canais" description={`Vínculos observados e carteira por parceiro. Referência mensal da base: ${monthLabel(data.reference_month)}.`} />
    {error && <Alert title="Falha na atualização" tone="warning" action={<button onClick={() => void refresh()}>Tentar novamente</button>}>{error}</Alert>}
    <Alert title="Visibilidade medida, não presumida">Inclui todos os canais cadastrados. A cobertura usa sell-out realmente registrado, mesmo quando o cadastro declara cobertura completa. Não é benefício comercial firmado nem desempenho de vendas.</Alert>
    <div className="metrics-grid"><MetricCard label="Parceiros neste filtro" value={filtered.length} detail={`de ${data.total} cadastrados`} icon="b2b" /><MetricCard label="Pares com sell-out" value={filtered.reduce((sum, p) => sum + p.observed_skus, 0)} detail="pares observados, não SKUs distintos" icon="quality" /><MetricCard label="Avaliar reposição" value={filtered.reduce((sum, p) => sum + p.action_counts.avaliar_reposicao, 0)} detail="sugestões comerciais, revisão humana" icon="feedback" /><MetricCard label="Dados insuficientes" value={filtered.reduce((sum, p) => sum + p.quality_counts.insufficient, 0)} detail="vínculos sem base para recomendar" tone="amber" icon="quality" /></div>
    <div className="filter-bar" role="search" aria-label="Filtrar parceiros"><label>Região<select value={region} onChange={e => update('regiao', e.target.value)}><option value="">Todas</option>{regions.map(r => <option key={r}>{r}</option>)}</select></label><label>Canal<select value={channel} onChange={e => update('canal', e.target.value)}><option value="">Todos</option>{channels.map(c => <option key={c}>{c}</option>)}</select></label><label>Ordenar<select value={sort} onChange={e => update('ordem', e.target.value)}><option value="name">Nome</option><option value="coverage">Cobertura observada</option><option value="opportunities">Sugestões de reposição</option></select></label>{params.size > 0 && <button className="secondary-button" onClick={() => setParams({}, { replace: true })}>Limpar filtros</button>}</div>
    {data.total > data.items.length && <Alert title="Lista limitada">Exibindo o primeiro lote de {data.items.length} parceiros. A API suporta paginação por limit/offset.</Alert>}
    {!filtered.length && <EmptyState title="Nenhum parceiro neste filtro" description="Ajuste região e canal. Ausência de informação não significa venda zero." />}
    <div className="partners-grid">{filtered.map(p => <article className="partner-card" key={p.code}><div className="partner-head"><div><strong>{p.name}</strong><span>{p.code} · {p.type}</span></div><Badge>{Math.round(p.coverage * 100)}% observado</Badge></div><p>{p.region ?? 'Região ausente'} · {p.channel ?? 'Canal ausente'}</p><ProgressBar value={p.coverage} label={`Cobertura observada de ${p.name}`} /><div className="partner-stats"><span><strong>{p.observed_skus}/{p.total_catalog_skus}</strong>SKUs do catálogo observados</span><span><strong>{p.linked_skus}</strong>vínculos reais com SKU</span></div><p>Último sell-out: {monthLabel(p.latest_sell_out_month)}</p><p>{p.action_counts.avaliar_reposicao} sugestões de reposição · {p.quality_counts.stale} dados antigos/descontínuos</p><Link className="secondary-button" to={`/parceiros/${encodeURIComponent(p.code)}`}>Abrir parceiro e evidências</Link></article>)}</div>
  </>;
}
