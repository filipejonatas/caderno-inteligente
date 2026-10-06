import { useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api } from '../api';
import { useApiResource } from '../hooks/useApiResource';
import { usePageLoadStatus } from '../hooks/usePageLoadStatus';
import { MOBILE_LIST_QUERY, useMediaQuery } from '../hooks/useMediaQuery';
import { Alert, Badge, EmptyState, ErrorState, Icon, LoadingState, PageIntro, SectionCard, confidenceTone } from '../components';
import type { ForecastRecommendationSummary, SelectedSku } from '../types';
import { ChallengeBadge } from '../components/ChallengeAction';
import { EventBadge } from '../components/EventAlerts';
import { RevenueSummaryCard } from '../components/RevenueForecast';
import { displayQuantity } from './shared';

type ForecastSort = 'priority' | 'suggested_quantity' | 'forecast_next_month' | 'backtest_wape';

const needsAttention = (item: ForecastRecommendationSummary) => item.forecast.status === 'insufficient_data'
  || item.operational_recommendation.action !== 'sem_acao_necessaria'
  || item.operational_recommendation.capacity_status === 'requires_review';

function recommendationTone(action: ForecastRecommendationSummary['operational_recommendation']['action']) {
  if (action === 'investigar_dados' || action === 'produzir_validar_capacidade') return 'medium';
  if (action === 'produzir') return 'info';
  if (action === 'monitorar_excesso') return 'neutral';
  return 'neutral';
}

export default function ForecastsPage({ onSelect, refreshToken }: { onSelect: (item: SelectedSku) => void; refreshToken: number }) {
  const { data: items, error, loading, loadedAt, refresh: load } = useApiResource(api.forecasts, refreshToken);
  // Camada aditiva: a estimativa de faturamento carrega à parte e nunca bloqueia a tela operacional.
  const { data: events } = useApiResource(api.events, refreshToken);
  const eventsBySku = useMemo(() => new Map((events?.items ?? []).map((item) => [item.sku, item])), [events]);
  const { data: revenue, error: revenueError, loading: revenueLoading, refresh: loadRevenue } = useApiResource(api.revenueForecast, refreshToken);
  usePageLoadStatus(loading, error, loadedAt);
  const [params, setParams] = useSearchParams();
  const [extra, setExtra] = useState(0);
  const mobile = useMediaQuery(MOBILE_LIST_QUERY);
  const search = params.get('busca') ?? '';
  const family = params.get('familia') ?? '';
  const action = params.get('acao') ?? '';
  const label = params.get('rotulo') ?? '';
  const showAll = params.get('todos') === '1';
  const sort = (params.get('ordem') ?? 'priority') as ForecastSort;
  // Padrão da tela: só o que pede atenção. Buscar um SKU ou escolher uma ação mostra tudo o que combina.
  const attentionOnly = !showAll && !action && !label && !search.trim();

  const update = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value && value !== 'priority') next.set(key, value); else next.delete(key);
    setParams(next, { replace: true });
    setExtra(0);
  };

  const families = useMemo(() => [...new Set((items ?? []).map((item) => item.family))].sort(), [items]);
  const filtered = useMemo(() => {
    const query = search.trim().toLocaleLowerCase('pt-BR');
    const result = (items ?? []).filter((item) => (!query || item.sku.toLocaleLowerCase('pt-BR').includes(query) || item.product.toLocaleLowerCase('pt-BR').includes(query))
      && (!family || item.family === family)
      && (!action || item.operational_recommendation.action === action)
      && (!label || item.challenge_action?.code === label)
      && (!attentionOnly || needsAttention(item)));
    return [...result].sort((left, right) => {
      if (sort === 'priority') return (left.priority ?? Number.MAX_SAFE_INTEGER) - (right.priority ?? Number.MAX_SAFE_INTEGER) || left.sku.localeCompare(right.sku);
      const leftValue = sort === 'suggested_quantity' ? left.operational_recommendation.suggested_quantity : left.forecast[sort];
      const rightValue = sort === 'suggested_quantity' ? right.operational_recommendation.suggested_quantity : right.forecast[sort];
      if (leftValue === null && rightValue === null) return left.sku.localeCompare(right.sku);
      if (leftValue === null) return 1;
      if (rightValue === null) return -1;
      return rightValue - leftValue || left.sku.localeCompare(right.sku);
    });
  }, [action, attentionOnly, family, items, label, search, sort]);
  const labels = useMemo(() => [...new Map((items ?? []).filter((item) => item.challenge_action).map((item) => [item.challenge_action!.code, item.challenge_action!.label])).entries()].sort((a, b) => a[1].localeCompare(b[1], 'pt-BR')), [items]);

  const filtersActive = params.size > 0;
  if (!items && !error) return <LoadingState />;
  if (!items && error) return <ErrorState message={error} onRetry={() => void load()} />;

  const source = items ?? [];
  const production = source.filter((item) => ['produzir', 'produzir_validar_capacidade'].includes(item.operational_recommendation.action)).length;
  const capacity = source.filter((item) => item.operational_recommendation.capacity_status === 'requires_review').length;
  const investigate = source.filter((item) => item.forecast.status === 'insufficient_data' || item.operational_recommendation.action === 'investigar_dados').length;
  const pageSize = (mobile ? 10 : 25) + extra;
  const visible = filtered.slice(0, pageSize);
  const noFilters = !action && !label && !search.trim();

  return <div className="forecast-page">
    <PageIntro title="Preciso produzir? Quanto?" description={`${production} SKUs para produzir · ${capacity} com capacidade a validar${investigate > 0 ? ` · ${investigate} para investigar dados` : ''}`} />
    {error && <Alert tone="warning" title="Falha ao atualizar previsões" action={<button className="secondary-button" onClick={() => void load()}>Tentar novamente</button>}>{error} A última carga permanece exibida.</Alert>}
    <RevenueSummaryCard data={revenue} error={revenueError} loading={revenueLoading} refresh={loadRevenue} />
    <div className="forecast-page-filters" role="search" aria-label="Filtrar previsões">
      <label className="search-field"><span>Buscar</span><Icon name="search" /><input value={search} onChange={(event) => update('busca', event.target.value)} placeholder="SKU ou produto" /></label>
      <label><span>Ação</span><select value={action} onChange={(event) => update('acao', event.target.value)}><option value="">Todas</option><option value="produzir">Produzir</option><option value="produzir_validar_capacidade">Produzir e validar capacidade</option><option value="monitorar_excesso">Monitorar excesso</option><option value="investigar_dados">Investigar dados</option><option value="sem_acao_necessaria">Sem ação necessária</option></select></label>
      {labels.length > 0 && <label><span>Rótulo</span><select value={label} onChange={(event) => update('rotulo', event.target.value)}><option value="">Todos</option>{labels.map(([code, name]) => <option key={code} value={code}>{name}</option>)}</select></label>}
      <label><span>Família</span><select value={family} onChange={(event) => update('familia', event.target.value)}><option value="">Todas</option>{families.map((item) => <option key={item}>{item}</option>)}</select></label>
      <label><span>Ordenar por</span><select value={sort} onChange={(event) => update('ordem', event.target.value)}><option value="priority">Posição na fila de atenção</option><option value="suggested_quantity">Maior quantidade sugerida</option><option value="forecast_next_month">Maior previsão do próximo mês</option><option value="backtest_wape">Maior erro da previsão</option></select></label>
      <div className="forecast-page-filter-result"><strong>{filtered.length}</strong><span>de {source.length} SKUs</span>{filtersActive && <button onClick={() => { setParams({}, { replace: true }); setExtra(0); }}>Limpar filtros</button>}</div>
    </div>
    <SectionCard title={attentionOnly ? `SKUs que pedem atenção (${filtered.length} de ${source.length})` : 'Ação e quantidade por SKU'} action={attentionOnly ? <button className="secondary-button" onClick={() => update('todos', '1')}>Ver os {source.length} SKUs</button> : showAll && noFilters ? <button className="secondary-button" onClick={() => update('todos', '')}>Só os que pedem atenção</button> : undefined}>
      {filtered.length ? <>
        <div className="table-shell forecast-page-table" tabIndex={0} role="region" aria-label="Previsões; role horizontalmente para ver todas as colunas"><table className="data-table responsive-table"><thead><tr><th>SKU / Produto</th><th>Ação operacional sugerida</th><th>Quantidade sugerida (un.)</th><th>Próximo mês (un.)</th></tr></thead><tbody>{visible.map((item) => {
          const rec = item.operational_recommendation;
          return <tr key={item.sku}>
            <td data-label="SKU"><button type="button" className="link-button" onClick={() => onSelect(item)} aria-label={`Ver detalhes de ${item.sku}`}><strong>{item.sku}</strong></button><small>{item.product}</small></td>
            <td className="cell-stack" data-label="Ação sugerida"><Badge tone={recommendationTone(rec.action)}>{rec.action_label}</Badge>{rec.capacity_status === 'requires_review' && <Badge tone="medium">Validar capacidade</Badge>}{item.forecast.forecast_confidence !== 'alta' && <Badge tone={confidenceTone(item.forecast.forecast_confidence)}>Previsão com confiança {item.forecast.forecast_confidence}</Badge>}{item.challenge_action?.code === 'priorizar_producao' && <ChallengeBadge action={item.challenge_action} />}<EventBadge item={eventsBySku.get(item.sku)} /></td>
            <td data-label="Quantidade"><strong>{displayQuantity(rec.suggested_quantity)}</strong></td>
            <td data-label="Próximo mês">{item.forecast.status === 'ok' ? displayQuantity(item.forecast.forecast_next_month) : <Badge tone="medium">Dados insuficientes</Badge>}</td>
          </tr>;
        })}</tbody></table></div>
        {filtered.length > visible.length && <div className="show-more"><button className="secondary-button" onClick={() => setExtra(value => value + 25)}>Ver mais ({filtered.length - visible.length} restantes)</button></div>}
      </> : <div className="forecast-page-empty"><EmptyState title="Nenhum SKU encontrado" description="Ajuste os filtros ou volte à visão completa." />{filtersActive && <button className="secondary-button" onClick={() => setParams({}, { replace: true })}>Limpar filtros</button>}</div>}
    </SectionCard>
  </div>;
}
