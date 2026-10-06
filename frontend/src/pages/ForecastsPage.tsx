import { useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api } from '../api';
import { useApiResource } from '../hooks/useApiResource';
import { usePageLoadStatus } from '../hooks/usePageLoadStatus';
import { Alert, Badge, EmptyState, ErrorState, Hint, Icon, LoadingState, MetricCard, PageIntro, SectionCard, confidenceTone } from '../components';
import type { ForecastRecommendationSummary, SelectedSku } from '../types';
import { displayPercent, displayQuantity } from './shared';

type ForecastSort = 'priority' | 'suggested_quantity' | 'forecast_next_month' | 'backtest_wape';

const needsAttention = (item: ForecastRecommendationSummary) => item.forecast.status === 'insufficient_data'
  || item.operational_recommendation.action !== 'sem_acao_necessaria'
  || item.operational_recommendation.capacity_status === 'requires_review';

function recommendationTone(action: ForecastRecommendationSummary['operational_recommendation']['action']) {
  if (action === 'investigar_dados' || action === 'produzir_validar_capacidade') return 'medium';
  if (action === 'produzir') return 'info';
  if (action === 'monitorar_excesso') return 'neutral';
  return 'good';
}

const isMobile = () => window.matchMedia('(max-width: 620px)').matches;

export default function ForecastsPage({ onSelect, refreshToken }: { onSelect: (item: SelectedSku) => void; refreshToken: number }) {
  const { data: items, error, loading, loadedAt, refresh: load } = useApiResource(api.forecasts, refreshToken);
  usePageLoadStatus(loading, error, loadedAt);
  const [params, setParams] = useSearchParams();
  const [extra, setExtra] = useState(0);
  const search = params.get('busca') ?? '';
  const family = params.get('familia') ?? '';
  const action = params.get('acao') ?? '';
  const confidence = params.get('confianca') ?? '';
  const trend = params.get('tendencia') ?? '';
  const attentionOnly = params.get('atencao') === '1';
  const sort = (params.get('ordem') ?? 'priority') as ForecastSort;

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
      && (!confidence || item.forecast.forecast_confidence === confidence)
      && (!trend || item.forecast.trend === trend)
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
  }, [action, attentionOnly, confidence, family, items, search, sort, trend]);

  const filtersActive = params.size > 0;
  if (!items && !error) return <LoadingState />;
  if (!items && error) return <ErrorState message={error} onRetry={() => void load()} />;

  const source = items ?? [];
  const production = source.filter((item) => ['produzir', 'produzir_validar_capacidade'].includes(item.operational_recommendation.action)).length;
  const produceOnly = source.filter((item) => item.operational_recommendation.action === 'produzir').length;
  const capacity = source.filter((item) => item.operational_recommendation.capacity_status === 'requires_review').length;
  const investigate = source.filter((item) => item.forecast.status === 'insufficient_data' || item.operational_recommendation.action === 'investigar_dados').length;
  const pageSize = (isMobile() ? 10 : 25) + extra;
  const visible = filtered.slice(0, pageSize);
  const moreFilters = !!(family || confidence || trend || sort !== 'priority');

  return <div className="forecast-page">
    <PageIntro title="Preciso produzir? Quanto?" description="Ação e quantidade sugeridas para cada SKU. Abra o SKU para ver o cálculo e as evidências." />
    {error && <Alert tone="warning" title="Falha ao atualizar previsões" action={<button className="secondary-button" onClick={() => void load()}>Tentar novamente</button>}>{error} A última carga permanece exibida.</Alert>}
    <div className="metrics-grid forecast-page-metrics">
      <MetricCard label="Produção sugerida" value={production} detail={`de ${source.length} SKUs: ${produceOnly} produzir e ${production - produceOnly} produzir após validar capacidade`} tone="green" icon="forecasts" />
      <MetricCard label="Validar capacidade" value={capacity} detail="SKUs de famílias com capacidade pressionada, mesmo os sem ação de produção" tone="amber" icon="quality" />
      {investigate > 0 && <MetricCard label="Investigar dados" value={investigate} detail="sem previsão confiável" tone="red" icon="search" />}
    </div>
    <div className="forecast-page-filters" role="search" aria-label="Filtrar previsões">
      <label className="search-field"><span>Buscar</span><Icon name="search" /><input value={search} onChange={(event) => update('busca', event.target.value)} placeholder="SKU ou produto" /></label>
      <label><span>Ação</span><select value={action} onChange={(event) => update('acao', event.target.value)}><option value="">Todas</option><option value="produzir">Produzir</option><option value="produzir_validar_capacidade">Produzir e validar capacidade</option><option value="monitorar_excesso">Monitorar excesso</option><option value="investigar_dados">Investigar dados</option><option value="sem_acao_necessaria">Sem ação necessária</option></select></label>
      <label className="forecast-page-check"><input type="checkbox" checked={attentionOnly} onChange={(event) => update('atencao', event.target.checked ? '1' : '')} /><span>Somente itens com atenção</span></label>
      <div className="forecast-page-filter-result"><strong>{filtered.length}</strong><span>de {source.length} SKUs</span>{filtersActive && <button onClick={() => { setParams({}, { replace: true }); setExtra(0); }}>Limpar filtros</button>}</div>
      <details className="more-filters" open={moreFilters}><summary>Mais filtros</summary>
        <div className="more-filters-grid">
          <label><span>Família</span><select value={family} onChange={(event) => update('familia', event.target.value)}><option value="">Todas</option>{families.map((item) => <option key={item}>{item}</option>)}</select></label>
          <label><span>Confiança</span><select value={confidence} onChange={(event) => update('confianca', event.target.value)}><option value="">Todas</option><option value="alta">Alta</option><option value="média">Média</option><option value="baixa">Baixa</option></select></label>
          <label><span>Tendência</span><select value={trend} onChange={(event) => update('tendencia', event.target.value)}><option value="">Todas</option><option value="crescente">Crescente</option><option value="estável">Estável</option><option value="decrescente">Decrescente</option><option value="indeterminada">Indeterminada</option></select></label>
          <label><span>Ordenar por</span><select value={sort} onChange={(event) => update('ordem', event.target.value)}><option value="priority">Posição na fila de atenção</option><option value="suggested_quantity">Maior quantidade sugerida</option><option value="forecast_next_month">Maior previsão do próximo mês</option><option value="backtest_wape">Maior erro da previsão</option></select></label>
        </div>
      </details>
    </div>
    <SectionCard title="Ação e quantidade por SKU" subtitle="A fila de atenção continua separada da quantidade sugerida.">
      {filtered.length ? <>
        <div className="table-shell forecast-page-table" tabIndex={0} role="region" aria-label="Previsões; role horizontalmente para ver todas as colunas"><table className="data-table responsive-table"><thead><tr><th>SKU</th><th>Ação operacional sugerida</th><th>Quantidade sugerida</th><th>Próximo mês</th><th>Confiança na previsão <Hint term="confianca_previsao" /></th><th>Fila de atenção</th><th><span className="sr-only">Detalhes</span></th></tr></thead><tbody>{visible.map((item) => {
          const rec = item.operational_recommendation;
          return <tr key={item.sku}>
            <td data-label="SKU"><strong>{item.sku}</strong><small>{item.product} · {item.family}</small></td>
            <td className="cell-stack" data-label="Ação sugerida"><Badge tone={recommendationTone(rec.action)}>{rec.action_label}</Badge>{rec.capacity_status === 'requires_review' && <Badge tone="medium">Validar capacidade</Badge>}
              <details className="row-more"><summary>Ver previsão e modelo</summary>
                <dl className="row-more-body"><div><dt>Tendência</dt><dd className={`trend-${item.forecast.trend}`}>{item.forecast.trend}</dd></div><div><dt>Próximos 3 meses</dt><dd>{item.forecast.status === 'ok' ? `${displayQuantity(item.forecast.forecast_total_3m)} un.` : 'Não disponível'}</dd></div><div><dt>Modelo</dt><dd>{item.forecast.model_label}</dd></div><div><dt>Erro médio da previsão (WAPE) <Hint term="wape" /></dt><dd>{displayPercent(item.forecast.backtest_wape)}</dd></div><div><dt>Capacidade</dt><dd>{rec.capacity_status === 'requires_review' ? 'Validar capacidade' : 'Contexto da família disponível; sem garantia por SKU'}</dd></div></dl>
              </details></td>
            <td data-label="Quantidade"><strong>{displayQuantity(rec.suggested_quantity)}</strong><small>Lote mínimo: {displayQuantity(rec.minimum_lot)}</small></td>
            <td data-label="Próximo mês">{item.forecast.status === 'ok' ? <>{displayQuantity(item.forecast.forecast_next_month)}<small>unidades previstas</small></> : <Badge tone="medium">Dados insuficientes</Badge>}</td>
            <td data-label="Confiança na previsão"><Badge tone={confidenceTone(item.forecast.forecast_confidence)}>{item.forecast.forecast_confidence}</Badge></td>
            <td data-label="Fila de atenção">{item.priority === null ? <span className="forecast-page-muted">Fora do ranking</span> : <span className={`rank ${item.priority <= 3 ? 'top' : ''}`}>#{item.priority}</span>}</td>
            <td className="cell-action"><button className="forecast-page-detail-button" onClick={() => onSelect(item)} aria-label={`Ver detalhes de ${item.sku}`}>Ver detalhes</button></td>
          </tr>;
        })}</tbody></table></div>
        {filtered.length > visible.length && <div className="show-more"><button className="secondary-button" onClick={() => setExtra(value => value + 25)}>Ver mais ({filtered.length - visible.length} restantes)</button></div>}
      </> : <div className="forecast-page-empty"><EmptyState title="Nenhum SKU encontrado" description="Ajuste os filtros ou volte à visão completa." />{filtersActive && <button className="secondary-button" onClick={() => setParams({}, { replace: true })}>Limpar filtros</button>}</div>}
    </SectionCard>
  </div>;
}
