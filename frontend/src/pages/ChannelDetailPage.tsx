import { useCallback, useState } from 'react';
import { Link, useLocation, useParams, useSearchParams } from 'react-router-dom';
import { api } from '../api';
import { Alert, Badge, EmptyState, ErrorState, Hint, LoadingState, PageIntro, SectionCard } from '../components';
import { SuggestionBadge, TrendBadge, backlogText } from '../components/ChannelViews';
import { RevenueTrend } from '../components/RevenueForecast';
import { useApiResource } from '../hooks/useApiResource';
import { usePageLoadStatus } from '../hooks/usePageLoadStatus';
import type { ChannelSignal } from '../types-channels';
import { displayCurrency, displayNumber, displayPercent, displayShare, formatMonth } from './shared';

const PAGE = 25;

export default function ChannelDetailPage({ refreshToken }: { refreshToken: number }) {
  const { canal = '' } = useParams();
  const location = useLocation();
  const [params, setParams] = useSearchParams();
  const [extra, setExtra] = useState(0);
  const signal = params.get('sinal') ?? '', search = params.get('busca') ?? '';
  const loader = useCallback((abort: AbortSignal) => {
    const query = new URLSearchParams();
    if (signal) query.set('signal', signal);
    if (search.trim()) query.set('search', search.trim());
    return api.directChannel(canal, query, abort);
  }, [canal, signal, search]);
  const { data, error, loading, loadedAt, refresh } = useApiResource(loader, refreshToken);
  usePageLoadStatus(loading, error, loadedAt);
  const update = (key: string, value: string) => { const next = new URLSearchParams(params); if (value) next.set(key, value); else next.delete(key); setParams(next, { replace: true }); setExtra(0); };
  if (!data) return error ? <ErrorState message={error} onRetry={() => void refresh()} /> : <LoadingState />;
  const channel = data.channel;
  const visible = data.items.slice(0, PAGE + extra);
  const signals = (Object.keys(data.signal_labels) as ChannelSignal[]).filter((code) => (channel.signal_counts[code] ?? 0) > 0);
  const from = `${location.pathname}${location.search}`;
  return <>
    <PageIntro title={channel.name ?? channel.code} description={`${channel.code} · ${channel.region ?? 'Região ausente'} · dados até ${formatMonth(data.reference_month)}`} action={<Link className="secondary-button" to="/parceiros?aba=diretos">Voltar aos canais</Link>} />
    {error && <Alert title="Falha na atualização" tone="warning" action={<button className="secondary-button" onClick={() => void refresh()}>Tentar novamente</button>}>{error}</Alert>}
    <p className="summary-line">Faturamento <strong>{displayCurrency(channel.revenue_24m)}</strong> em 24 meses <Badge tone="neutral">Observado</Badge> · {displayShare(channel.share_of_revenue)} do total · <TrendBadge trend={channel.trend} ratio={channel.change_ratio} /> · {channel.observed_skus} de {channel.catalog_skus} SKUs com faturamento · {backlogText(channel.backlog.open_orders, channel.backlog.open_quantity).toLocaleLowerCase('pt-BR')} <Hint term="canais_diretos" /></p>
    <RevenueTrend observed={{ months: channel.monthly.months, values: channel.monthly.revenue }} months={[]} values={[]} label={`Faturamento mensal observado de ${channel.name ?? channel.code}`} />
    <div className="filter-bar" role="search" aria-label="Filtrar SKUs do canal">
      <label>Buscar<input value={search} onChange={(event) => update('busca', event.target.value)} placeholder="SKU ou produto" /></label>
      <label>Sinal<select value={signal} onChange={(event) => update('sinal', event.target.value)}><option value="">Todos</option>{signals.map((code) => <option key={code} value={code}>{data.signal_labels[code]} ({channel.signal_counts[code]})</option>)}</select></label>
      {params.size > 0 && <button className="secondary-button" onClick={() => { setParams({}, { replace: true }); setExtra(0); }}>Limpar filtros</button>}
    </div>
    <SectionCard title={`Faturamento por SKU (${data.total})`}>
      {!data.items.length ? <EmptyState title="Nenhum SKU neste filtro" description="Ajuste a busca ou o sinal. SKU sem faturamento no canal aparece como não vendido, nunca como zero." /> : <>
        <div className="table-shell" tabIndex={0} role="region" aria-label="SKUs do canal; role horizontalmente para ver todas as colunas"><table className="data-table responsive-table"><thead><tr><th>SKU / Produto</th><th>Faturamento (24 meses)</th><th>Tendência recente</th><th>Carteira aberta</th><th>Sugestão</th></tr></thead><tbody>{visible.map((row) => <tr key={row.sku}>
          <td data-label="SKU"><Link className="link-button" to={`/skus/${encodeURIComponent(row.sku)}`} state={{ from }}><strong>{row.sku}</strong></Link><small>{row.product}{row.product_status && row.product_status !== 'Ativo' ? ` · ${row.product_status}` : ''}</small></td>
          <td data-label="Faturamento">{row.revenue_24m === null ? <Badge tone="medium">Sem faturamento no canal</Badge> : <>{displayCurrency(row.revenue_24m)}<small>#{row.rank} · {displayPercent(row.share_in_channel)}</small></>}</td>
          <td data-label="Tendência">{row.units_24m === null ? 'Não disponível' : <TrendBadge trend={row.trend} ratio={row.change_ratio} />}</td>
          <td data-label="Carteira">{row.backlog_open_orders ? `${displayNumber(row.backlog_open_quantity)} un.` : '—'}</td>
          <td data-label="Sugestão" className="cell-stack"><SuggestionBadge row={row} /></td>
        </tr>)}</tbody></table></div>
        {data.items.length > visible.length && <div className="show-more"><button className="secondary-button" onClick={() => setExtra((value) => value + PAGE)}>Ver mais ({data.items.length - visible.length} restantes)</button></div>}
      </>}
    </SectionCard>
  </>;
}
