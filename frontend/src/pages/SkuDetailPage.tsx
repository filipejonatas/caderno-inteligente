import { useCallback } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import { api } from '../api';
import { PartnerSkuContext } from '../components/PartnerSkuContext';
import { Alert, Badge, ErrorState, Hint, PageIntro, confidenceTone, severityTone } from '../components';
import { useApiResource } from '../hooks/useApiResource';
import { usePageLoadStatus } from '../hooks/usePageLoadStatus';
import { displayDays, displayNumber, displayPercent, displayQuantity, displayUnits, formatDate, localizeText, missingDataNames, positiveDelayDays, reasonNames } from './shared';

/** Only same-app paths: blocks '//host', backslash tricks and schemes (open-redirect hardening). */
export function isInternalPath(value: string) {
  return value.startsWith('/') && !value.startsWith('//') && !value.includes('\\') && !/[\u0000-\u001f]/.test(value);
}

type EvidenceKind = 'share' | 'days' | 'units' | 'date' | 'text' | 'count';
const evidenceFields: Record<string, [string, EvidenceKind]> = {
  family: ['Família', 'text'],
  average_occupation: ['Ocupação média da família', 'share'],
  available_capacity_average: ['Capacidade disponível média (unidades por semana)', 'units'],
  first_promised_date: ['Primeira data prometida', 'date'],
  first_production_completion: ['Primeira conclusão prevista', 'date'],
  delay_days: ['Atraso entre promessa e conclusão', 'days'],
  coverage_days: ['Cobertura do estoque', 'days'],
  lead_time_days: ['Prazo de produção (lead time)', 'days'],
  safety_stock_days: ['Estoque de segurança', 'days'],
  sell_out_partner_count: ['Parceiros com sell-out', 'count'],
  sell_out_visibility: ['Visibilidade de sell-out', 'text'],
  backlog_order_quantity: ['Carteira de pedidos', 'units'],
  production_order_quantity: ['Produção aberta', 'units'],
  excess_coverage_days: ['Limite de cobertura em excesso', 'days'],
};

function evidenceValue(code: string, key: string, value: unknown) {
  if (value === null || value === undefined) return 'Não disponível';
  const kind: EvidenceKind = code === 'CAPACITY_CONFLICT' && key === 'threshold' ? 'share' : evidenceFields[key]?.[1] ?? 'text';
  if (typeof value === 'number') {
    if (kind === 'share') return displayPercent(value);
    if (kind === 'days') return displayDays(value);
    if (kind === 'units') return displayUnits(value);
    return displayQuantity(value);
  }
  if (kind === 'date' && typeof value === 'string') return formatDate(value);
  return String(value);
}

const evidenceLabel = (code: string, key: string) => code === 'CAPACITY_CONFLICT' && key === 'threshold' ? 'Limite configurado de ocupação'
  : evidenceFields[key]?.[0] ?? key.split('_').join(' ').replace(/^./, (letter) => letter.toUpperCase());

function originLabel(origin: string) {
  if (origin.startsWith('config.')) return `Configuração: ${origin.slice(7).split('.').join(' › ').split('_').join(' ')}`;
  const [sheet, ...column] = origin.split('.');
  return column.length ? `Planilha · aba ${sheet.split('_').join(' ')} · ${column.join('.')}` : origin;
}

export default function SkuDetailPage({ refreshToken }: { refreshToken: number }) {
  const { sku = '' } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const loader = useCallback((signal: AbortSignal) => api.skuDetail(sku, signal), [sku]);
  const { data: detail, error, loading, loadedAt, refresh: load } = useApiResource(loader, refreshToken);
  usePageLoadStatus(loading, error, loadedAt);
  const backTarget = typeof location.state === 'object' && location.state && 'from' in location.state && typeof location.state.from === 'string' && isInternalPath(location.state.from) ? location.state.from : '/prioridades';

  if (error && !detail) return <div className="sku-detail-page"><PageIntro title={sku || 'SKU não informado'} description="Não foi possível carregar as evidências deste item." action={<button className="secondary-button" onClick={() => navigate(backTarget)}>Voltar</button>} /><ErrorState message={error} onRetry={() => void load()} /></div>;
  if (!detail) return <div className="sku-detail-page"><PageIntro title={sku || 'Detalhe do SKU'} description="Buscando indicadores, previsão, recomendação e evidências." action={<button className="secondary-button" onClick={() => navigate(backTarget)}>Voltar</button>} /><div className="drawer-loading"><span /><span /><span /></div></div>;

  const indicator = detail.indicator;
  const forecast = detail.forecast;
  const recommendation = detail.operational_recommendation;
  const rankedPriority = detail.priority[0];
  const priorityNumber = rankedPriority?.priority ?? null;
  const attentionScore = rankedPriority?.attention_score ?? null;
  const rankingConfidence = rankedPriority?.confidence ?? recommendation.confidence;
  const rankingConfidenceReason = rankedPriority?.confidence_reason ?? recommendation.confidence_reason;
  const delayDays = positiveDelayDays(indicator.first_promised_date, indicator.first_production_completion);
  const insufficient = forecast.status === 'insufficient_data';
  const quantity = recommendation.suggested_quantity;
  const answer = insufficient ? `${recommendation.action_label}: sem histórico suficiente para sugerir quantidade.`
    : `${recommendation.action_label}${quantity && quantity > 0 ? ` · ${displayQuantity(quantity)} un.` : ''}`;
  const contributions = [...detail.score_contributions].sort((a, b) => b.weight - a.weight);

  return <div className="sku-detail-page">
    <PageIntro title={indicator.SKU} description={`${priorityNumber === null ? 'Fora do ranking oficial' : `Posição ${priorityNumber} na fila de atenção`} · ${indicator.Produto} · ${indicator.family}`} action={<button className="secondary-button" onClick={() => navigate(backTarget)}>Voltar</button>} />
    {error && <Alert title="Não foi possível atualizar o SKU" tone="warning" action={<button className="secondary-button" onClick={() => void load()}>Tentar novamente</button>}>{error} A última carga permanece exibida.</Alert>}
    <section className="answer-card" aria-labelledby="answer-title">
      <div className="answer-main">
        <span className="eyebrow" id="answer-title">Ação operacional sugerida</span>
        <p className="answer-sentence">{answer}</p>
        {!insufficient && <p className="answer-why">{localizeText(recommendation.rationale.join(' '))}</p>}
        {insufficient && <p className="answer-why">{forecast.limitation}</p>}
        <div className="answer-badges">{recommendation.capacity_status === 'requires_review' && <Badge tone="medium">Validar capacidade</Badge>}{insufficient ? <><Badge tone="medium">Dados insuficientes</Badge><Badge tone="medium">{recommendation.action_label}</Badge></> : <Badge tone="info">previsto</Badge>}</div>
        <div className="answer-actions">
          <Link className="primary-button" to={`/decisoes?sku=${encodeURIComponent(sku)}`}>Registrar decisão</Link>
          <Link className="secondary-button" to={`/casos?sku=${encodeURIComponent(sku)}`}>Criar caso</Link>
        </div>
      </div>
      <div className="answer-figures">
        {!insufficient && <>
        <div className={quantity && quantity > 0 ? 'metric-recommendation' : ''}><span>Quantidade sugerida</span><strong>{displayQuantity(quantity)}</strong><small>unidades · lote mínimo {displayQuantity(recommendation.minimum_lot)}</small></div>
        <div><span>Previsão do próximo mês</span><strong>{displayQuantity(forecast.forecast_next_month)}</strong><small>unidades previstas pelo modelo</small></div>
        </>}
        <div><span>Confiança na previsão <Hint term="confianca_previsao" /></span><strong><Badge tone={confidenceTone(recommendation.confidence)}>{recommendation.confidence}</Badge></strong><small>{insufficient ? 'sem previsão' : `erro médio de ${displayPercent(forecast.backtest_wape)} nos 3 últimos meses`}</small></div>
        <div><span>Confiança nos dados do SKU <Hint term="confianca_dados" /></span><strong><Badge tone={confidenceTone(rankingConfidence)}>{rankingConfidence}</Badge></strong><small>{rankingConfidenceReason}</small></div>
      </div>
      <div className="human-review"><strong>Revisão humana obrigatória</strong><p>{recommendation.confidence_reason} {insufficient ? 'Nenhuma quantidade é sugerida sem histórico suficiente; ausência de previsão não equivale a demanda zero.' : 'A sugestão não cria nem libera ordem de produção.'}</p></div>
    </section>
    {recommendation.action === 'sem_acao_necessaria' && <Alert title="Sem ação necessária de produção não significa sem risco">A recomendação operacional deste SKU não indica produção adicional neste horizonte. Os sinais da fila de atenção continuam exigindo análise.</Alert>}

    {!insufficient && <details className="detail-block" open>
      <summary>Por que esta quantidade: cálculo e previsão</summary>
      <div className="recommendation-card">
        <div className="calculation-line"><span>Demanda a cobrir</span><strong>{displayUnits(recommendation.calculation.demand_to_cover)}</strong><span>+ Segurança</span><strong>{displayUnits(recommendation.calculation.safety_stock_quantity)}</strong><span>− Estoque</span><strong>{displayUnits(recommendation.calculation.current_stock)}</strong><span>− Produção aberta</span><strong>{displayUnits(recommendation.calculation.open_production_quantity)}</strong></div>
        {recommendation.assumptions.length > 0 && <ul className="plain-list">{recommendation.assumptions.map((item) => <li key={item}>{localizeText(item)}</li>)}</ul>}
      </div>
      <div className="detail-metrics-grid forecast-metrics">
        <div><span>Tendência</span><strong className={`trend-${forecast.trend}`}>{forecast.trend}</strong><small>{forecast.trend_change_ratio === null ? 'Sem comparação percentual' : displayPercent(forecast.trend_change_ratio)}</small></div>
        <div><span>Modelo selecionado</span><strong>{forecast.model_label}</strong><small>{forecast.history_months} meses analisados</small></div>
        <div><span>Erro médio da previsão (WAPE) <Hint term="wape" /></span><strong>{displayPercent(forecast.backtest_wape)}</strong><small>teste nos 3 últimos meses <Hint term="holdout" /></small></div>
        <div><span>Previsão do modelo, próximos 3 meses</span><strong>{displayUnits(forecast.forecast_total_3m)}</strong><small>previsto</small></div>
      </div>
      <div className="forecast-months">{forecast.forecast_months.map((month, index) => <div key={month}><span>{formatDate(month)}</span><strong>{displayQuantity(forecast.forecast_values[index])}</strong><small>unidades previstas</small></div>)}</div>
      <p className="forecast-limitation">{forecast.limitation}</p>
    </details>}

    <details className="detail-block">
      <summary>Demanda e atendimento: estoque, carteira e datas</summary>
      <div className="drawer-section-heading"><div><h3>Demanda e atendimento</h3></div><Badge tone="neutral">{indicator.analysis_scope}</Badge></div>
      <div className="detail-metrics-grid"><div><span>Estoque atual</span><strong>{displayUnits(indicator.current_stock)}</strong></div><div><span>Carteira</span><strong>{displayUnits(indicator.backlog_order_quantity)}</strong></div><div><span>Produção aberta</span><strong>{displayUnits(indicator.production_order_quantity)}</strong></div><div><span>Estoque projetado</span><strong>{displayUnits(indicator.projected_stock_quantity)}</strong></div><div className={indicator.operational_gap_quantity > 0 ? 'metric-alert' : ''}><span>Lacuna operacional</span><strong>{displayUnits(indicator.operational_gap_quantity)}</strong><small>quantidade para análise</small></div><div><span>Cobertura <Hint term="cobertura" /></span><strong>{displayDays(indicator.coverage_days_calculated)}</strong><small>Prazo de produção: {displayDays(indicator.lead_time_days)}</small></div></div>
      <div className="date-comparison"><div><span>Primeira data prometida</span><strong>{formatDate(indicator.first_promised_date)}</strong></div><div><span>Primeira conclusão prevista</span><strong>{formatDate(indicator.first_production_completion)}</strong></div>{delayDays !== null && <div className="delay-callout"><span>Conclusão depois da promessa</span><strong>{delayDays} {delayDays === 1 ? 'dia' : 'dias'}</strong></div>}</div>
      <h3 className="details-heading">Canal e dados ausentes</h3>
      <div className="detail-metrics-grid channel-grid"><div><span>Vendido ao parceiro (sell-in) acumulado</span><strong>{displayUnits(indicator.sell_in_quantity)}</strong></div><div><span>Vendido pelo parceiro (sell-out) acumulado</span><strong>{displayUnits(indicator.sell_out_quantity)}</strong></div><div><span>Diferença observada</span><strong>{displayUnits(indicator.sell_in_minus_sell_out_quantity)}</strong></div><div><span>Parceiros com sell-out</span><strong>{displayNumber(indicator.sell_out_partner_count)}</strong></div><div><span>Previsão comercial (planilha)</span><strong>{displayUnits(indicator.forecast_quantity)}</strong><small>previsto pela área comercial</small></div></div>
      <div className="confidence-explanation"><strong>Por que esta confiança nos dados?</strong><p>{rankingConfidenceReason}</p></div>
      {indicator.missing_data.length > 0 ? <div className="missing-data"><strong>Dados ausentes</strong><ul>{indicator.missing_data.map((field) => <li key={field}>{missingDataNames[field] ?? field.split('_').join(' ')}</li>)}</ul><p>Ausência de dado não é interpretada como valor zero.</p></div> : <div className="data-complete"><span>✓</span><p><strong>Dados principais disponíveis</strong>Não foram identificadas ausências nos campos desta análise.</p></div>}
    </details>

    <details className="detail-block" open>
      <summary>Riscos e evidências: de onde vêm os {attentionScore === null ? '' : `${attentionScore} `}pontos de atenção</summary>
      <p className="score-sum">{attentionScore === null ? 'SKU fora do ranking oficial.' : <>Pontos de atenção <Hint term="score" />: <strong>{attentionScore}</strong>{contributions.length > 0 && <> = {contributions.map((item, index) => <span key={item.code}>{index > 0 && ' + '}<strong>{item.weight}</strong> ({reasonNames[item.code] ?? item.code})</span>)}</>}</>}</p>
      {detail.issues.map((issue) => <article className="issue-card" key={issue.code}><div><Badge tone={severityTone(issue.severity)}>{issue.severity}</Badge><strong>{reasonNames[issue.code] ?? issue.code}</strong></div><p>{issue.description}</p><dl>{Object.entries(issue.values_used).map(([key, value]) => <div key={key}><dt>{evidenceLabel(issue.code, key)}</dt><dd>{evidenceValue(issue.code, key, value)}</dd></div>)}</dl><small>Origem: {issue.data_origin.map(originLabel).join(' · ')}</small></article>)}
      <div className="drawer-note"><strong>Limitação conhecida</strong><p>{detail.limitation}</p></div>
    </details>
    <PartnerSkuContext sku={sku} refreshToken={refreshToken} />
  </div>;
}
