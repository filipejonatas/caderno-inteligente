import { useCallback, useMemo } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { api } from '../api';
import { Alert, EmptyState, ErrorState, Hint, LoadingState, MetricCard, PageIntro, ProgressBar, SectionCard } from '../components';
import { CommercialMatrix, monthLabel } from '../components/CommercialMatrix';
import { useApiResource } from '../hooks/useApiResource';
import { usePageLoadStatus } from '../hooks/usePageLoadStatus';
import { displayShare } from './shared';

export default function B2BPage({ refreshToken }: { refreshToken: number }) {
  const loader = useCallback((signal: AbortSignal) => api.partners(new URLSearchParams({ limit: '200' }), signal), []);
  const { data, error, loading, loadedAt, refresh } = useApiResource(loader, refreshToken);
  const [params, setParams] = useSearchParams();
  const tab = params.get('aba') === 'parceiros' ? 'parceiros' : 'oportunidades';
  const region = params.get('regiao') ?? '', channel = params.get('canal') ?? '', sort = params.get('ordem') ?? 'opportunities';
  const opportunitiesLoader = useCallback(async (signal: AbortSignal) => {
    if (tab !== 'oportunidades') return null;
    const query = new URLSearchParams({ action: 'avaliar_reposicao', limit: '200' });
    if (region) query.set('region', region);
    if (channel) query.set('channel', channel);
    return api.commercialRecommendations(query, signal);
  }, [tab, region, channel]);
  const opportunities = useApiResource(opportunitiesLoader, refreshToken);
  usePageLoadStatus(loading || opportunities.loading, error || opportunities.error, loadedAt);
  const update = (key: string, value: string) => { const next = new URLSearchParams(params); if (value) next.set(key, value); else next.delete(key); setParams(next, { replace: true }); };
  const regions = useMemo(() => [...new Set((data?.items ?? []).map(p => p.region).filter((x): x is string => !!x))].sort(), [data]);
  const channels = useMemo(() => [...new Set((data?.items ?? []).map(p => p.channel).filter((x): x is string => !!x))].sort(), [data]);
  const filtered = useMemo(() => (data?.items ?? []).filter(p => (!region || p.region === region) && (!channel || p.channel === channel)).sort((a, b) => sort === 'coverage' ? b.coverage - a.coverage || a.name.localeCompare(b.name) : sort === 'name' ? a.name.localeCompare(b.name) : b.action_counts.avaliar_reposicao - a.action_counts.avaliar_reposicao || a.name.localeCompare(b.name)), [data, region, channel, sort]);
  if (!data) return error ? <ErrorState message={error} onRetry={() => void refresh()} /> : <LoadingState />;
  const opportunityCount = filtered.reduce((sum, p) => sum + p.action_counts.avaliar_reposicao, 0);
  const partnersWithOpportunity = filtered.filter(p => p.action_counts.avaliar_reposicao > 0).length;
  const insufficient = filtered.reduce((sum, p) => sum + p.quality_counts.insufficient, 0);
  const observedPairs = filtered.reduce((sum, p) => sum + p.observed_skus, 0);
  const tabLink = (name: 'oportunidades' | 'parceiros', label: string) => {
    const next = new URLSearchParams(params); if (name === 'oportunidades') next.delete('aba'); else next.set('aba', name);
    return <Link to={`/parceiros${next.size ? `?${next}` : ''}`} replace className={tab === name ? 'active' : ''} aria-current={tab === name ? 'page' : undefined}>{label}</Link>;
  };
  return <>
    <PageIntro title="Onde há oportunidade de reposição" description={`${partnersWithOpportunity} de ${filtered.length} parceiros têm sugestão de reposição (${opportunityCount} no total). Referência mensal da base: ${monthLabel(data.reference_month)}.`} />
    {error && <Alert title="Falha na atualização" tone="warning" action={<button onClick={() => void refresh()}>Tentar novamente</button>}>{error}</Alert>}
    <div className="metrics-grid">
      <MetricCard label="Oportunidades de reposição" value={opportunityCount} detail={`em ${partnersWithOpportunity} de ${filtered.length} parceiros; sugestão para revisão humana`} icon="feedback" />
      <MetricCard label="Combinações com venda informada" value={observedPairs} detail="parceiro–SKU com sell-out registrado" icon="quality" />
      <MetricCard label="Vínculos sem base para recomendar" value={insufficient} detail="dados insuficientes: não significa venda zero" tone="amber" icon="quality" />
    </div>
    <p className="details-note">A cobertura usa só o sell-out realmente registrado, mesmo quando o cadastro declara cobertura completa; não é benefício comercial firmado nem desempenho de vendas. <Hint term="sellout" /></p>
    <div className="filter-bar" role="search" aria-label="Filtrar parceiros"><label>Região<select value={region} onChange={e => update('regiao', e.target.value)}><option value="">Todas</option>{regions.map(r => <option key={r}>{r}</option>)}</select></label><label>Canal<select value={channel} onChange={e => update('canal', e.target.value)}><option value="">Todos</option>{channels.map(c => <option key={c}>{c}</option>)}</select></label>{tab === 'parceiros' && <label>Ordenar<select value={sort} onChange={e => update('ordem', e.target.value)}><option value="opportunities">Sugestões de reposição</option><option value="coverage">Cobertura observada</option><option value="name">Nome</option></select></label>}{params.size > 0 && <button className="secondary-button" onClick={() => setParams({}, { replace: true })}>Limpar filtros</button>}</div>
    <nav className="subnav" aria-label="Visões de parceiros">{tabLink('oportunidades', `Oportunidades (${opportunityCount})`)}{tabLink('parceiros', `Parceiros (${filtered.length})`)}</nav>
    {data.total > data.items.length && <Alert title="Lista limitada">Exibindo o primeiro lote de {data.items.length} parceiros. A API suporta paginação por limit/offset.</Alert>}
    {tab === 'oportunidades' ? (opportunities.data ? <CommercialMatrix response={opportunities.data} /> : opportunities.error ? <ErrorState message={opportunities.error} onRetry={() => void opportunities.refresh()} /> : <LoadingState />) : <SectionCard title="Parceiros e canais" subtitle="Cobertura medida pelo sell-out registrado.">
      {!filtered.length ? <EmptyState title="Nenhum parceiro neste filtro" description="Ajuste região e canal. Ausência de informação não significa venda zero." /> : <div className="table-shell" tabIndex={0} role="region" aria-label="Parceiros; role horizontalmente para ver todas as colunas"><table className="data-table responsive-table"><thead><tr><th>Parceiro</th><th>Região · Canal</th><th>Cobertura de sell-out</th><th>Oportunidades</th><th>Sem dados suficientes</th><th><span className="sr-only">Abrir</span></th></tr></thead><tbody>{filtered.map(p => <tr key={p.code}>
        <td data-label="Parceiro"><strong>{p.name}</strong><small>{p.code} · {p.type}</small></td>
        <td data-label="Região · Canal">{p.region ?? 'Região ausente'} · {p.channel ?? 'Canal ausente'}</td>
        <td data-label="Cobertura"><strong>{displayShare(p.coverage)}</strong><small>{p.observed_skus} de {p.total_catalog_skus} SKUs · último sell-out {monthLabel(p.latest_sell_out_month)}</small><ProgressBar value={p.coverage} label={`Cobertura observada de ${p.name}`} /></td>
        <td data-label="Oportunidades">{p.action_counts.avaliar_reposicao}</td>
        <td data-label="Sem dados">{p.quality_counts.insufficient}{p.quality_counts.stale > 0 && <small>{p.quality_counts.stale} antigos/descontínuos</small>}</td>
        <td className="cell-action"><Link className="secondary-button" to={`/parceiros/${encodeURIComponent(p.code)}`} aria-label={`Abrir parceiro ${p.name} e evidências`}>Abrir</Link></td>
      </tr>)}</tbody></table></div>}
    </SectionCard>}
  </>;
}
