import { useCallback, useMemo } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { api } from '../api';
import { Alert, EmptyState, ErrorState, Icon, LoadingState, PageIntro, SectionCard } from '../components';
import { ChallengeBadge } from '../components/ChallengeAction';
import { DirectChannelsTab } from '../components/ChannelViews';
import { CommercialMatrix, monthLabel, opportunityOrderLabels, sortOpportunities } from '../components/CommercialMatrix';
import type { OpportunityOrder } from '../components/CommercialMatrix';
import { useApiResource } from '../hooks/useApiResource';
import { usePageLoadStatus } from '../hooks/usePageLoadStatus';
import { CHALLENGE_NAMES, displayShare } from './shared';

export default function B2BPage({ refreshToken }: { refreshToken: number }) {
  const loader = useCallback((signal: AbortSignal) => api.partners(new URLSearchParams({ limit: '200' }), signal), []);
  const { data, error, loading, loadedAt, refresh } = useApiResource(loader, refreshToken);
  const [params, setParams] = useSearchParams();
  const tab = params.get('aba') === 'parceiros' ? 'parceiros' : params.get('aba') === 'diretos' ? 'diretos' : 'oportunidades';
  const region = params.get('regiao') ?? '', channel = params.get('canal') ?? '', sort = params.get('ordem') ?? 'opportunities', label = params.get('rotulo') ?? '', search = params.get('busca') ?? '';
  // Cada visão tem a sua ordenação; um valor de outra visão cai no padrão.
  const opportunityOrder: OpportunityOrder = sort in opportunityOrderLabels ? sort as OpportunityOrder : 'urgencia';
  const query = search.trim().toLocaleLowerCase('pt-BR');
  const includes = (...texts: string[]) => !query || texts.some(text => text.toLocaleLowerCase('pt-BR').includes(query));
  const opportunitiesLoader = useCallback(async (signal: AbortSignal) => {
    if (tab !== 'oportunidades') return null;
    const query = new URLSearchParams({ action: 'avaliar_reposicao', limit: '200' });
    if (region) query.set('region', region);
    if (channel) query.set('channel', channel);
    return api.commercialRecommendations(query, signal);
  }, [tab, region, channel]);
  const opportunities = useApiResource(opportunitiesLoader, refreshToken);
  const directLoader = useCallback(async (signal: AbortSignal) => tab === 'diretos' ? api.directChannels(signal) : null, [tab]);
  const direct = useApiResource(directLoader, refreshToken);
  usePageLoadStatus(loading || opportunities.loading || direct.loading, error || opportunities.error || direct.error, loadedAt);
  const update = (key: string, value: string) => { const next = new URLSearchParams(params); if (value) next.set(key, value); else next.delete(key); setParams(next, { replace: true }); };
  const regions = useMemo(() => [...new Set((data?.items ?? []).map(p => p.region).filter((x): x is string => !!x))].sort(), [data]);
  const channels = useMemo(() => [...new Set((data?.items ?? []).map(p => p.channel).filter((x): x is string => !!x))].sort(), [data]);
  const filtered = useMemo(() => (data?.items ?? []).filter(p => (!region || p.region === region) && (!channel || p.channel === channel) && (!label || p.challenge_action?.code === label)).sort((a, b) => sort === 'coverage' ? b.coverage - a.coverage || a.name.localeCompare(b.name) : sort === 'name' ? a.name.localeCompare(b.name) : b.action_counts.avaliar_reposicao - a.action_counts.avaliar_reposicao || a.name.localeCompare(b.name)), [data, region, channel, sort, label]);
  const sortedOpportunities = useMemo(() => opportunities.data ? { ...opportunities.data, items: sortOpportunities(opportunities.data.items.filter(row => includes(row.partner_name, row.partner, row.sku, row.product)), opportunityOrder) } : null, [opportunities.data, opportunityOrder, query]); // eslint-disable-line react-hooks/exhaustive-deps
  if (!data) return error ? <ErrorState message={error} onRetry={() => void refresh()} /> : <LoadingState />;
  const opportunityCount = filtered.reduce((sum, p) => sum + p.action_counts.avaliar_reposicao, 0);
  const listed = filtered.filter(p => includes(p.name, p.code));
  const resultCount = tab === 'oportunidades' ? sortedOpportunities?.items.length ?? 0 : listed.length;
  const partnersWithOpportunity = filtered.filter(p => p.action_counts.avaliar_reposicao > 0).length;
  const tabLink = (name: 'oportunidades' | 'parceiros' | 'diretos', label: string) => {
    const next = new URLSearchParams(params); if (name === 'oportunidades') next.delete('aba'); else next.set('aba', name);
    return <Link to={`/parceiros${next.size ? `?${next}` : ''}`} replace className={tab === name ? 'active' : ''} aria-current={tab === name ? 'page' : undefined}>{label}</Link>;
  };
  return <>
    <PageIntro title="Onde há oportunidade de reposição" description={tab === 'diretos' ? `Faturamento observado dos canais diretos. Dados até ${monthLabel(data.reference_month)}.` : `${partnersWithOpportunity} de ${filtered.length} parceiros têm sugestão de reposição (${opportunityCount} no total). Dados até ${monthLabel(data.reference_month)}.`} />
    {error && <Alert title="Falha na atualização" tone="warning" action={<button onClick={() => void refresh()}>Tentar novamente</button>}>{error}</Alert>}
    {tab !== 'diretos' && <div className="filter-bar" role="search" aria-label="Filtrar parceiros"><label className="search-field"><span>Buscar</span><Icon name="search" /><input value={search} onChange={e => update('busca', e.target.value)} placeholder={tab === 'oportunidades' ? 'Parceiro, SKU ou produto' : 'Parceiro'} /></label><label>Região<select value={region} onChange={e => update('regiao', e.target.value)}><option value="">Todas</option>{regions.map(r => <option key={r}>{r}</option>)}</select></label><label>Canal<select value={channel} onChange={e => update('canal', e.target.value)}><option value="">Todos</option>{channels.map(c => <option key={c}>{c}</option>)}</select></label>{tab === 'oportunidades' && <label>Ordenar<select value={opportunityOrder} onChange={e => update('ordem', e.target.value)}>{(Object.keys(opportunityOrderLabels) as OpportunityOrder[]).map(code => <option key={code} value={code}>{opportunityOrderLabels[code]}</option>)}</select></label>}{tab === 'parceiros' && <label>Rótulo<select value={label} onChange={e => update('rotulo', e.target.value)}><option value="">Todos</option><option value="priorizar_parceiro">{CHALLENGE_NAMES.priorizar_parceiro}</option></select></label>}{tab === 'parceiros' && <label>Ordenar<select value={sort} onChange={e => update('ordem', e.target.value)}><option value="opportunities">Sugestões de reposição</option><option value="coverage">Cobertura de dados de sell-out</option><option value="name">Nome</option></select></label>}<div className="filter-count" role="status"><strong>{resultCount}</strong><span>{tab === 'oportunidades' ? 'oportunidades' : 'parceiros'}</span></div>{params.size > 0 && <button className="secondary-button" onClick={() => setParams({}, { replace: true })}>Limpar filtros</button>}</div>}
    <nav className="subnav" aria-label="Visões de parceiros">{tabLink('oportunidades', `Oportunidades (${opportunityCount})`)}{tabLink('parceiros', `Parceiros (${filtered.length})`)}{tabLink('diretos', 'Canais diretos')}</nav>
    {tab !== 'diretos' && data.total > data.items.length && <Alert title="Lista limitada">Exibindo o primeiro lote de {data.items.length} parceiros. A API suporta paginação por limit/offset.</Alert>}
    {tab === 'diretos' ? (direct.data ? <DirectChannelsTab data={direct.data} /> : direct.error ? <ErrorState message={direct.error} onRetry={() => void direct.refresh()} /> : <LoadingState />) : tab === 'oportunidades' ? (sortedOpportunities && opportunities.data ? <>{opportunities.data.total > opportunities.data.items.length && <Alert title="Ordenação do primeiro lote">A lista mostra {opportunities.data.items.length} de {opportunities.data.total} oportunidades e a ordem vale só para esse lote.</Alert>}<CommercialMatrix response={sortedOpportunities} /></> : opportunities.error ? <ErrorState message={opportunities.error} onRetry={() => void opportunities.refresh()} /> : <LoadingState />) : <SectionCard title="Parceiros e canais">
      {!listed.length ? <EmptyState title="Nenhum parceiro neste filtro" description="Ajuste região e canal. Ausência de informação não significa venda zero." /> : <div className="table-shell" tabIndex={0} role="region" aria-label="Parceiros; role horizontalmente para ver todas as colunas"><table className="data-table responsive-table"><thead><tr><th>Parceiro</th><th>Cobertura de dados de sell-out</th><th>Oportunidades</th><th>Sem dados suficientes</th><th><span className="sr-only">Abrir</span></th></tr></thead><tbody>{listed.map(p => <tr key={p.code}>
        <td data-label="Parceiro"><strong>{p.name}</strong><small>{p.region ?? 'Região ausente'} · {p.channel ?? 'Canal ausente'}</small><ChallengeBadge action={p.challenge_action} /></td>
        <td data-label="Cobertura de dados">{displayShare(p.coverage)}</td>
        <td data-label="Oportunidades">{p.action_counts.avaliar_reposicao}</td>
        <td data-label="Sem dados">{p.quality_counts.insufficient}</td>
        <td className="cell-action"><Link className="secondary-button" to={`/parceiros/${encodeURIComponent(p.code)}`} aria-label={`Abrir parceiro ${p.name} e evidências`}>Abrir</Link></td>
      </tr>)}</tbody></table></div>}
    </SectionCard>}
  </>;
}
