import { useCallback, useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { api } from '../api';
import { Alert, ErrorState, LoadingState, MetricCard, PageIntro } from '../components';
import { CommercialMatrix, commercialActions, monthLabel, qualityLabels } from '../components/CommercialMatrix';
import { useApiResource } from '../hooks/useApiResource';
import { usePageLoadStatus } from '../hooks/usePageLoadStatus';

export default function PartnerDetailPage({ refreshToken }: { refreshToken: number }) {
  const { codigo = '' } = useParams();
  const [params, setParams] = useSearchParams();
  const sku = params.get('sku') ?? '', action = params.get('acao') ?? '', quality = params.get('qualidade') ?? '';
  const [draftSku, setDraftSku] = useState(sku);
  useEffect(() => setDraftSku(sku), [sku]);
  const offset = Math.max(0, Number(params.get('offset')) || 0);
  const loader = useCallback(async (signal: AbortSignal) => {
    const query = new URLSearchParams({ limit: '50', offset: String(offset) });
    if (sku) query.set('sku', sku); if (action) query.set('action', action); if (quality) query.set('data_quality', quality);
    const [detail, rows] = await Promise.all([api.partnerDetail(codigo, signal), api.partnerSkus(codigo, query, signal)]);
    return { detail, rows };
  }, [codigo, sku, action, quality, offset]);
  const { data, error, loading, loadedAt, refresh } = useApiResource(loader, refreshToken);
  usePageLoadStatus(loading, error, loadedAt);
  const update = (key: string, value: string) => { const next = new URLSearchParams(params); next.delete('offset'); if (value) next.set(key, value); else next.delete(key); setParams(next, { replace: true }); };
  if (!data) return error ? <ErrorState message={error} onRetry={() => void refresh()} /> : <LoadingState />;
  const p = data.detail.partner;
  return <>
    <PageIntro title={p.name} description={`${p.code} · ${p.region ?? 'Região ausente'} · ${p.channel ?? 'Canal ausente'}`} action={<Link className="secondary-button" to="/parceiros">Voltar aos parceiros</Link>} />
    {error && <Alert title="Falha na atualização" tone="warning" action={<button className="secondary-button" onClick={() => void refresh()}>Tentar novamente</button>}>{error}</Alert>}
    <div className="metrics-grid"><MetricCard label="Cobertura observada" value={`${Math.round(p.coverage * 100)}%`} detail={`${p.observed_skus} de ${p.total_catalog_skus} SKUs do catálogo`} icon="b2b" /><MetricCard label="Último sell-out" value={monthLabel(p.latest_sell_out_month)} detail={`referência: ${monthLabel(data.detail.reference_month)}`} icon="quality" /><MetricCard label="Oportunidades de reposição" value={p.action_counts.avaliar_reposicao} detail={`de ${p.linked_skus} vínculos reais com SKU`} icon="feedback" /><MetricCard label="Dados antigos/descontínuos" value={p.quality_counts.stale} detail="em relação à referência da base" tone="amber" icon="quality" /></div>
    <div className="filter-bar" role="search" aria-label="Filtrar SKUs do parceiro"><form className="commercial-sku-filter" onSubmit={e => { e.preventDefault(); update('sku', draftSku.trim().toUpperCase()); }}><label>SKU exato<input value={draftSku} onChange={e => setDraftSku(e.target.value)} placeholder="CI-0001" /></label><button className="secondary-button">Filtrar SKU</button></form><label>Ação comercial<select value={action} onChange={e => update('acao', e.target.value)}><option value="">Todas</option>{Object.entries(commercialActions).map(([code, name]) => <option key={code} value={code}>{name}</option>)}</select></label><label>Qualidade<select value={quality} onChange={e => update('qualidade', e.target.value)}><option value="">Todas</option>{Object.entries(qualityLabels).map(([code, name]) => <option key={code} value={code}>{name}</option>)}</select></label>{params.size > 0 && <button className="secondary-button" onClick={() => setParams({}, { replace: true })}>Limpar filtros</button>}</div>
    <CommercialMatrix response={data.rows} />
    <div className="commercial-pagination"><button className="secondary-button" disabled={offset === 0} onClick={() => update('offset', String(Math.max(0, offset - 50)))}>Anterior</button><span>{data.rows.items.length ? data.rows.offset + 1 : 0}–{data.rows.offset + data.rows.items.length} de {data.rows.total}</span><button className="secondary-button" disabled={offset + 50 >= data.rows.total} onClick={() => update('offset', String(offset + 50))}>Próxima</button></div>
    <details className="commercial-evidence"><summary>Limitações</summary><div><p><strong>Decisões influenciadas por este parceiro:</strong> atribuição indisponível. {data.detail.decisions.reason} Nenhuma associação foi inferida ou criada.</p></div></details>
  </>;
}
