import { Badge, EmptyState, confidenceTone, mainReason, severityTone } from '../components';
import { ChallengeBadge } from './ChallengeAction';
import { EventBadge, mainAlert } from './EventAlerts';
import { displayQuantity, reasonNames } from '../pages/shared';
import type { ForecastRecommendationSummary, Priority } from '../types';
import type { EventItem } from '../types-events';

type Recommendation = ForecastRecommendationSummary['operational_recommendation'];

/** Uma linha da fila: o que cada fonte sabe do SKU. Campo ausente nunca vira zero nem recomendação inventada. */
export interface QueueRow {
  sku: string;
  product: string;
  family: string;
  position: number | null;
  priority?: Priority;
  forecast?: ForecastRecommendationSummary;
}

export type QueueSort = 'priority' | 'suggested_quantity' | 'forecast_next_month' | 'backtest_wape';

/** Junção pelo SKU. A prioridade vem de /priorities; ação e quantidade vêm de /forecasts; SKU em só uma fonte permanece na lista. */
export function joinQueue(priorities: Priority[] | undefined, forecasts: ForecastRecommendationSummary[] | undefined): QueueRow[] {
  const rows = new Map<string, QueueRow>();
  for (const priority of priorities ?? []) rows.set(priority.sku, { sku: priority.sku, product: priority.product, family: priority.family, position: priority.priority, priority });
  for (const forecast of forecasts ?? []) {
    const known = rows.get(forecast.sku);
    rows.set(forecast.sku, known
      ? { ...known, forecast, position: known.position ?? forecast.priority }
      : { sku: forecast.sku, product: forecast.product, family: forecast.family, position: forecast.priority, forecast });
  }
  return [...rows.values()];
}

export const forecastNeedsAttention = (item: ForecastRecommendationSummary) => item.forecast.status === 'insufficient_data'
  || item.operational_recommendation.action !== 'sem_acao_necessaria'
  || item.operational_recommendation.capacity_status === 'requires_review';

/** SKU só no ranking (sem previsão carregada) não pode ser dado como "sem atenção". */
export const rowNeedsAttention = (row: QueueRow) => !row.forecast || forecastNeedsAttention(row.forecast);

const NO_POSITION = Number.MAX_SAFE_INTEGER;

export function sortQueue(rows: QueueRow[], sort: QueueSort) {
  return [...rows].sort((left, right) => {
    if (sort === 'priority') return (left.position ?? NO_POSITION) - (right.position ?? NO_POSITION) || left.sku.localeCompare(right.sku);
    const pick = (row: QueueRow) => sort === 'suggested_quantity' ? row.forecast?.operational_recommendation.suggested_quantity ?? null : row.forecast?.forecast[sort] ?? null;
    const leftValue = pick(left);
    const rightValue = pick(right);
    if (leftValue === null && rightValue === null) return left.sku.localeCompare(right.sku);
    if (leftValue === null) return 1;
    if (rightValue === null) return -1;
    return rightValue - leftValue || left.sku.localeCompare(right.sku);
  });
}

function actionTone(action: Recommendation['action']) {
  if (action === 'investigar_dados' || action === 'produzir_validar_capacidade') return 'medium';
  if (action === 'produzir') return 'info';
  return 'neutral';
}

function Exceptions({ row, event }: { row: QueueRow; event?: EventItem }) {
  const rec = row.forecast?.operational_recommendation;
  const forecastConfidence = row.forecast?.forecast.forecast_confidence;
  const dataConfidence = row.priority?.confidence ?? row.forecast?.confidence;
  const parts = [
    row.forecast?.forecast.status === 'insufficient_data' && <Badge key="insufficient" tone="medium">Dados insuficientes</Badge>,
    rec?.capacity_status === 'requires_review' && <Badge key="capacity" tone="medium">Validar capacidade</Badge>,
    forecastConfidence && forecastConfidence !== 'alta' && row.forecast?.forecast.status === 'ok' && <Badge key="forecast" tone={confidenceTone(forecastConfidence)}>Previsão com confiança {forecastConfidence}</Badge>,
    dataConfidence === 'baixa' && <Badge key="data" tone="low">Dados com confiança baixa</Badge>,
    event && mainAlert(event.alerts) && <EventBadge key="event" item={event} />,
  ].filter(Boolean);
  return <td className="cell-stack" data-label="Exceções">{parts.length ? parts : <span className="queue-none" aria-label="Sem exceções">—</span>}</td>;
}

export function OperationalQueueTable({ rows, onSelect, weights, eventsBySku, forecastsLoaded, prioritiesLoaded }: {
  rows: QueueRow[];
  onSelect: (row: QueueRow) => void;
  weights?: Record<string, number>;
  eventsBySku: Map<string, EventItem>;
  forecastsLoaded: boolean;
  prioritiesLoaded: boolean;
}) {
  if (!rows.length) return <EmptyState title="Nenhum SKU encontrado" description="Ajuste os filtros ou volte à visão completa." />;
  return <div className="table-shell queue-table" tabIndex={0} role="region" aria-label="Fila operacional; role horizontalmente para ver todas as colunas">
    <table className="data-table responsive-table">
      <caption className="sr-only">Fila operacional por posição de atenção; cada sugestão exige revisão humana</caption>
      <thead><tr><th>Posição e SKU</th><th>Ação sugerida</th><th>Quantidade sugerida (un.)</th><th>Motivo principal</th><th>Exceções</th></tr></thead>
      <tbody>{rows.map((row) => {
        const rec = row.forecast?.operational_recommendation;
        const reason = row.priority ? mainReason(row.priority.reasons, weights) : undefined;
        return <tr key={row.sku}>
          <td className="queue-sku" data-label="SKU">
            <span className={`rank ${row.position !== null && row.position <= 3 ? 'top' : ''}`} title="Posição na fila de atenção">{row.position ?? '–'}</span>
            <div><button type="button" className="link-button" onClick={() => onSelect(row)} aria-label={`Ver detalhes de ${row.sku}`}><strong>{row.sku}</strong></button><small>{row.product}</small></div>
          </td>
          <td className="cell-stack" data-label="Ação sugerida">
            {rec ? <><Badge tone={actionTone(rec.action)}>{rec.action_label}</Badge>{row.forecast?.challenge_action?.code === 'priorizar_producao' && <ChallengeBadge action={row.forecast.challenge_action} />}</>
              : <Badge tone="neutral">{forecastsLoaded ? 'Sem previsão para este SKU' : 'Ação indisponível'}</Badge>}
          </td>
          <td data-label="Quantidade"><strong>{displayQuantity(rec?.suggested_quantity)}</strong></td>
          <td className="cell-stack" data-label="Motivo principal">
            {reason ? <Badge tone={severityTone(reason.severity)}>{reasonNames[reason.code] ?? reason.description}</Badge>
              : <span className="queue-none">{prioritiesLoaded ? 'Fora do ranking' : 'Indisponível'}</span>}
          </td>
          <Exceptions row={row} event={eventsBySku.get(row.sku)} />
        </tr>;
      })}</tbody>
    </table>
  </div>;
}

