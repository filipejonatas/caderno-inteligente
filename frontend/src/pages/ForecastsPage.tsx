import { useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api } from '../api';
import { useApiResource } from '../hooks/useApiResource';
import { Badge, EmptyState, ErrorState, Icon, LoadingState, MetricCard, PageIntro, SectionCard, confidenceTone } from '../components';
import type { ForecastRecommendationSummary, SelectedSku } from '../types';
import { displayNumber, displayPercent } from './shared';

type ForecastSort = 'priority' | 'suggested_quantity' | 'forecast_next_month' | 'backtest_wape';

const needsAttention = (item: ForecastRecommendationSummary) => item.forecast.status === 'insufficient_data'
  || item.operational_recommendation.action !== 'sem_acao_necessaria'
  || item.operational_recommendation.capacity_status === 'requires_review';

function recommendationTone(action: ForecastRecommendationSummary['operational_recommendation']['action']) {
  if (action === 'investigar_dados' || action === 'produzir_validar_capacidade') return 'medium';
  if (action === 'produzir') return 'high';
  if (action === 'monitorar_excesso') return 'neutral';
  return 'good';
}

export default function ForecastsPage({ onSelect, refreshToken }: { onSelect: (item: SelectedSku) => void; refreshToken: number }) {
  const { data: items, error, refresh: load } = useApiResource(api.forecasts, refreshToken);
  const [params, setParams] = useSearchParams();
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
  const predicted = source.filter((item) => item.forecast.status === 'ok').length;
  const production = source.filter((item) => ['produzir', 'produzir_validar_capacidade'].includes(item.operational_recommendation.action)).length;
  const capacity = source.filter((item) => item.operational_recommendation.capacity_status === 'requires_review').length;
  const investigate = source.filter((item) => item.forecast.status === 'insufficient_data' || item.operational_recommendation.action === 'investigar_dados').length;

  return <div className="forecast-page">
    <PageIntro eyebrow="Planejamento de demanda" title="Previsão e recomendações" description="Compare a demanda prevista, a confiança do modelo e a ação sugerida antes da validação humana." />
    {error && <div className="global-warning"><span>!</span>{error}<button onClick={() => void load()}>Tentar novamente</button></div>}
    <div className="forecast-page-warning"><div className="notice-icon">!</div><div><strong>Revisão humana obrigatória</strong><p>As quantidades são sugestões de apoio à decisão. Revise carteira, capacidade e restrições operacionais antes de agir.</p></div></div>
    <div className="metrics-grid forecast-page-metrics">
      <MetricCard label="SKUs previstos" value={predicted} detail={`${source.length} SKUs analisados`} tone="blue" icon="forecasts" />
      <MetricCard label="Produção sugerida" value={production} detail="itens que pedem avaliação" tone="green" icon="forecasts" />
      <MetricCard label="Validar capacidade" value={capacity} detail="contexto familiar pressionado" tone="amber" icon="quality" />
      <MetricCard label="Investigar dados" value={investigate} detail="sem previsão confiável" tone={investigate ? 'red' : 'slate'} icon="search" />
    </div>
    <div className="forecast-page-filters">
      <label className="search-field"><span>Buscar</span><Icon name="search" /><input value={search} onChange={(event) => update('busca', event.target.value)} placeholder="SKU ou produto" /></label>
      <label><span>Família</span><select value={family} onChange={(event) => update('familia', event.target.value)}><option value="">Todas</option>{families.map((item) => <option key={item}>{item}</option>)}</select></label>
      <label><span>Ação</span><select value={action} onChange={(event) => update('acao', event.target.value)}><option value="">Todas</option><option value="produzir">Produzir</option><option value="produzir_validar_capacidade">Produzir e validar capacidade</option><option value="monitorar_excesso">Monitorar excesso</option><option value="investigar_dados">Investigar dados</option><option value="sem_acao_necessaria">Sem ação necessária</option></select></label>
      <label><span>Confiança</span><select value={confidence} onChange={(event) => update('confianca', event.target.value)}><option value="">Todas</option><option value="alta">Alta</option><option value="média">Média</option><option value="baixa">Baixa</option></select></label>
      <label><span>Tendência</span><select value={trend} onChange={(event) => update('tendencia', event.target.value)}><option value="">Todas</option><option value="crescente">Crescente</option><option value="estável">Estável</option><option value="decrescente">Decrescente</option><option value="indeterminada">Indeterminada</option></select></label>
      <label><span>Ordenar por</span><select value={sort} onChange={(event) => update('ordem', event.target.value)}><option value="priority">Prioridade oficial</option><option value="suggested_quantity">Maior quantidade sugerida</option><option value="forecast_next_month">Maior previsão do próximo mês</option><option value="backtest_wape">Maior WAPE</option></select></label>
      <label className="forecast-page-check"><input type="checkbox" checked={attentionOnly} onChange={(event) => update('atencao', event.target.checked ? '1' : '')} /><span>Somente itens com atenção</span></label>
      <div className="forecast-page-filter-result"><strong>{filtered.length}</strong><span>de {source.length} SKUs</span>{filtersActive && <button onClick={() => setParams({}, { replace: true })}>Limpar filtros</button>}</div>
    </div>
    <SectionCard title="Visão operacional consolidada" subtitle="O ranking oficial permanece separado da quantidade sugerida." action={<span className="live-label"><span />Pipeline cacheado</span>}>
      {filtered.length ? <>
        <div className="table-shell forecast-page-table"><table className="data-table"><thead><tr><th>SKU</th><th>Prioridade</th><th>Tendência</th><th>Próximo mês</th><th>3 meses</th><th>Modelo / WAPE</th><th>Confiança</th><th>Recomendação</th><th>Quantidade</th><th>Capacidade</th><th></th></tr></thead><tbody>{filtered.map((item) => <tr key={item.sku}>
          <td><strong>{item.sku}</strong><small>{item.product} · {item.family}</small></td><td>{item.priority === null ? <span className="forecast-page-muted">Fora do ranking</span> : <span className={`rank ${item.priority <= 3 ? 'top' : ''}`}>#{item.priority}</span>}</td><td><strong className={`trend-${item.forecast.trend}`}>{item.forecast.trend}</strong></td><td>{item.forecast.status === 'ok' ? displayNumber(item.forecast.forecast_next_month) : <Badge tone="medium">Dados insuficientes</Badge>}</td><td>{item.forecast.status === 'ok' ? displayNumber(item.forecast.forecast_total_3m) : '—'}</td><td><strong>{item.forecast.model_label}</strong><small>{displayPercent(item.forecast.backtest_wape)}</small></td><td><Badge tone={confidenceTone(item.forecast.forecast_confidence)}>{item.forecast.forecast_confidence}</Badge></td><td><Badge tone={recommendationTone(item.operational_recommendation.action)}>{item.operational_recommendation.action_label}</Badge></td><td><strong>{displayNumber(item.operational_recommendation.suggested_quantity)}</strong><small>Lote: {displayNumber(item.operational_recommendation.minimum_lot)}</small></td><td><Badge tone={item.operational_recommendation.capacity_status === 'requires_review' ? 'medium' : 'neutral'}>{item.operational_recommendation.capacity_status === 'requires_review' ? 'Validar capacidade' : 'Sem garantia individual'}</Badge></td><td><button className="forecast-page-detail-button" onClick={() => onSelect(item)}>Ver detalhes</button></td>
        </tr>)}</tbody></table></div>
        <div className="forecast-page-cards">{filtered.map((item) => <article key={item.sku} className="forecast-page-card"><div className="forecast-page-card-head"><div><strong>{item.sku}</strong><span>{item.product}</span><small>{item.family}</small></div>{item.priority === null ? <Badge tone="neutral">Fora do ranking</Badge> : <span className={`rank ${item.priority <= 3 ? 'top' : ''}`}>#{item.priority}</span>}</div><div className="forecast-page-card-badges"><Badge tone={confidenceTone(item.forecast.forecast_confidence)}>{item.forecast.forecast_confidence}</Badge><Badge tone={recommendationTone(item.operational_recommendation.action)}>{item.operational_recommendation.action_label}</Badge>{item.operational_recommendation.capacity_status === 'requires_review' && <Badge tone="medium">Validar capacidade</Badge>}</div><dl><div><dt>Tendência</dt><dd className={`trend-${item.forecast.trend}`}>{item.forecast.trend}</dd></div><div><dt>Próximo mês</dt><dd>{item.forecast.status === 'ok' ? displayNumber(item.forecast.forecast_next_month) : 'Dados insuficientes'}</dd></div><div><dt>Próximos 3 meses</dt><dd>{displayNumber(item.forecast.forecast_total_3m)}</dd></div><div><dt>Quantidade sugerida</dt><dd>{displayNumber(item.operational_recommendation.suggested_quantity)}</dd></div><div><dt>Modelo</dt><dd>{item.forecast.model_label}</dd></div><div><dt>WAPE</dt><dd>{displayPercent(item.forecast.backtest_wape)}</dd></div></dl><button className="secondary-button" onClick={() => onSelect(item)}>Ver detalhes</button></article>)}</div>
      </> : <div className="forecast-page-empty"><EmptyState title="Nenhum SKU encontrado" description="Ajuste os filtros ou volte à visão completa." />{filtersActive && <button className="secondary-button" onClick={() => setParams({}, { replace: true })}>Limpar filtros</button>}</div>}
    </SectionCard>
  </div>;
}
