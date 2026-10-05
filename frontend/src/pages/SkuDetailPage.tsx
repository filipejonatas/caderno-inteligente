import { useCallback, useEffect, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { api } from '../api';
import { Badge, ErrorState, PageIntro, confidenceTone, severityTone } from '../components';
import type { SkuDetail } from '../types';
import { displayNumber, displayPercent, formatDate, missingDataNames, positiveDelayDays, reasonNames } from './shared';

export default function SkuDetailPage() {
  const { sku = '' } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const [detail, setDetail] = useState<SkuDetail>();
  const [error, setError] = useState('');
  const backTarget = typeof location.state === 'object' && location.state && 'from' in location.state && typeof location.state.from === 'string' && location.state.from.startsWith('/') ? location.state.from : '/prioridades';

  const load = useCallback(async () => {
    setDetail(undefined); setError('');
    try { setDetail(await api.skuDetail(sku)); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Falha ao carregar detalhe.'); }
  }, [sku]);

  useEffect(() => { void load(); }, [load]);

  if (error) return <div className="sku-detail-page"><PageIntro eyebrow="Detalhe compartilhável" title={sku || 'SKU não informado'} description="Não foi possível carregar as evidências deste item." action={<button className="secondary-button" onClick={() => navigate(backTarget)}>Voltar</button>} /><ErrorState message={error} onRetry={() => void load()} /></div>;
  if (!detail) return <div className="sku-detail-page"><PageIntro eyebrow="Carregando análise" title={sku || 'Detalhe do SKU'} description="Buscando indicadores, previsão, recomendação e evidências." action={<button className="secondary-button" onClick={() => navigate(backTarget)}>Voltar</button>} /><div className="drawer-loading"><span /><span /><span /></div></div>;

  const indicator = detail.indicator;
  const forecast = detail.forecast;
  const recommendation = detail.operational_recommendation;
  const rankedPriority = detail.priority[0];
  const priorityNumber = rankedPriority?.priority ?? null;
  const attentionScore = rankedPriority?.attention_score ?? null;
  const rankingConfidence = rankedPriority?.confidence ?? recommendation.confidence;
  const rankingConfidenceReason = rankedPriority?.confidence_reason ?? recommendation.confidence_reason;
  const delayDays = positiveDelayDays(indicator.first_promised_date, indicator.first_production_completion);

  return <div className="sku-detail-page">
    <PageIntro eyebrow={priorityNumber === null ? 'SKU fora do ranking oficial' : `Prioridade #${priorityNumber}`} title={indicator.SKU} description={`${indicator.Produto} · ${indicator.family}`} action={<button className="secondary-button" onClick={() => navigate(backTarget)}>Voltar</button>} />
    <div className="drawer-body">
      <div className="drawer-summary"><div><span>Score</span><strong>{displayNumber(attentionScore)}</strong></div><div><span>Confiança</span><Badge tone={confidenceTone(rankingConfidence)}>{rankingConfidence}</Badge></div><div><span>Família</span><strong>{indicator.family}</strong></div></div>
      <section className="drawer-section detail-section">
        <div className="drawer-section-heading"><div><span>Contexto operacional</span><h3>Demanda e atendimento</h3></div><Badge tone="neutral">{indicator.analysis_scope}</Badge></div>
        <div className="detail-metrics-grid"><div><span>Estoque atual</span><strong>{displayNumber(indicator.current_stock)}</strong></div><div><span>Carteira</span><strong>{displayNumber(indicator.backlog_order_quantity)}</strong></div><div><span>Produção aberta</span><strong>{displayNumber(indicator.production_order_quantity)}</strong></div><div><span>Estoque projetado</span><strong>{displayNumber(indicator.projected_stock_quantity)}</strong></div><div className={indicator.operational_gap_quantity > 0 ? 'metric-alert' : ''}><span>Lacuna operacional</span><strong>{displayNumber(indicator.operational_gap_quantity)}</strong><small>Quantidade para análise</small></div><div><span>Cobertura</span><strong>{displayNumber(indicator.coverage_days_calculated)} dias</strong><small>Lead time: {displayNumber(indicator.lead_time_days)} dias</small></div></div>
        <div className="date-comparison"><div><span>Primeira data prometida</span><strong>{formatDate(indicator.first_promised_date)}</strong></div><div><span>Primeira conclusão prevista</span><strong>{formatDate(indicator.first_production_completion)}</strong></div>{delayDays !== null && <div className="delay-callout"><span>Atraso identificado</span><strong>{delayDays} {delayDays === 1 ? 'dia' : 'dias'}</strong></div>}</div>
      </section>
      <section className="drawer-section detail-section">
        <div className="drawer-section-heading"><div><span>Qualidade da análise</span><h3>Canal e confiança</h3></div><Badge tone={confidenceTone(rankingConfidence)}>{rankingConfidence}</Badge></div>
        <div className="detail-metrics-grid channel-grid"><div><span>Sell-in acumulado</span><strong>{displayNumber(indicator.sell_in_quantity)}</strong></div><div><span>Sell-out acumulado</span><strong>{displayNumber(indicator.sell_out_quantity)}</strong></div><div><span>Diferença observada</span><strong>{displayNumber(indicator.sell_in_minus_sell_out_quantity)}</strong></div><div><span>Parceiros com sell-out</span><strong>{displayNumber(indicator.sell_out_partner_count)}</strong></div><div><span>Forecast disponível</span><strong>{displayNumber(indicator.forecast_quantity)}</strong></div></div>
        <div className="confidence-explanation"><strong>Por que esta confiança?</strong><p>{rankingConfidenceReason}</p></div>
        {indicator.missing_data.length > 0 ? <div className="missing-data"><strong>Dados ausentes</strong><ul>{indicator.missing_data.map((field) => <li key={field}>{missingDataNames[field] ?? field.split('_').join(' ')}</li>)}</ul><p>Ausência de dado não é interpretada como valor zero.</p></div> : <div className="data-complete"><span>✓</span><p><strong>Dados principais disponíveis</strong>Não foram identificadas ausências nos campos desta análise.</p></div>}
      </section>
      <section className="drawer-section detail-section forecast-section">
        <div className="drawer-section-heading"><div><span>Modelo preditivo</span><h3>Previsão e recomendação</h3></div><Badge tone={confidenceTone(recommendation.confidence)}>{recommendation.confidence}</Badge></div>
        {forecast.status === 'insufficient_data' ? <div className="forecast-empty"><strong>Dados insuficientes</strong><p>{forecast.limitation}</p><Badge tone="medium">{recommendation.action_label}</Badge></div> : <>
          <div className="detail-metrics-grid forecast-metrics"><div><span>Tendência</span><strong className={`trend-${forecast.trend}`}>{forecast.trend}</strong><small>{forecast.trend_change_ratio === null ? 'Sem comparação percentual' : displayPercent(forecast.trend_change_ratio)}</small></div><div><span>Modelo selecionado</span><strong>{forecast.model_label}</strong><small>{forecast.history_months} meses analisados</small></div><div><span>Erro no backtest</span><strong>{displayPercent(forecast.backtest_wape)}</strong><small>WAPE nos 3 meses reservados</small></div><div><span>Próximo mês</span><strong>{displayNumber(forecast.forecast_next_month)}</strong><small>unidades previstas</small></div><div><span>Próximos 3 meses</span><strong>{displayNumber(forecast.forecast_total_3m)}</strong><small>unidades previstas</small></div><div className={recommendation.suggested_quantity && recommendation.suggested_quantity > 0 ? 'metric-recommendation' : ''}><span>Quantidade sugerida</span><strong>{displayNumber(recommendation.suggested_quantity)}</strong><small>{recommendation.horizon}</small></div></div>
          <div className="forecast-months">{forecast.forecast_months.map((month, index) => <div key={month}><span>{formatDate(month)}</span><strong>{displayNumber(forecast.forecast_values[index])}</strong><small>unidades</small></div>)}</div>
          <div className="recommendation-card"><div><span>Ação sugerida</span><strong>{recommendation.action_label}</strong><Badge tone={recommendation.capacity_status === 'requires_review' ? 'medium' : 'good'}>{recommendation.capacity_status === 'requires_review' ? 'Validar capacidade' : 'Contexto familiar disponível'}</Badge></div><p>{recommendation.rationale.join(' ')}</p><div className="calculation-line"><span>Demanda a cobrir</span><strong>{displayNumber(recommendation.calculation.demand_to_cover)}</strong><span>+ Segurança</span><strong>{displayNumber(recommendation.calculation.safety_stock_quantity)}</strong><span>− Estoque</span><strong>{displayNumber(recommendation.calculation.current_stock)}</strong><span>− Produção aberta</span><strong>{displayNumber(recommendation.calculation.open_production_quantity)}</strong></div></div>
          <div className="human-review"><strong>Revisão humana obrigatória</strong><p>{recommendation.confidence_reason} A sugestão não cria nem libera ordem de produção.</p></div>
        </>}
        <p className="forecast-limitation">{forecast.limitation}</p>
      </section>
      <div className="drawer-section"><h3>Riscos e evidências</h3>{detail.issues.map((issue) => <article className="issue-card" key={issue.code}><div><Badge tone={severityTone(issue.severity)}>{issue.severity}</Badge><strong>{reasonNames[issue.code] ?? issue.code}</strong></div><p>{issue.description}</p><dl>{Object.entries(issue.values_used).map(([key, value]) => <div key={key}><dt>{key.split('_').join(' ')}</dt><dd>{String(value)}</dd></div>)}</dl><small>Origem: {issue.data_origin.join(' · ')}</small></article>)}</div>
      <div className="drawer-note"><strong>Limitação conhecida</strong><p>{detail.limitation}</p></div>
    </div>
  </div>;
}
