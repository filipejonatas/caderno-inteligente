import { Link } from 'react-router-dom';
import { api } from '../api';
import { Badge, LoadingState, PageIntro, SectionCard, Tooltip } from '../components';
import { useApiResource } from '../hooks/useApiResource';
import { usePageLoadStatus } from '../hooks/usePageLoadStatus';
import type { CapacityFamily, CapacityStatus } from '../types';
import { displayQuantity, formatDate } from './shared';

const STATUS_TONE: Record<CapacityStatus, string> = { ok: 'good', pre_producao: 'info', a_confirmar: 'neutral', insuficiente: 'critical' };
const STATUS_TEXT: Record<CapacityStatus, string> = { ok: 'Cabe', pre_producao: 'Cabe com pré-produção', a_confirmar: 'Cabe no calendário; depois, a confirmar', insuficiente: 'Não cabe' };
const MONTHS = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];

function shortfallLine(family: CapacityFamily) {
  const orders = family.affected_orders.slice(0, 3).map((order) => `${order.order} (${order.client})`).join(', ');
  return <p key={family.family} className="fact-line"><strong>{family.family}:</strong> {displayQuantity(family.unscheduled_quantity)} un. sem programação, a primeira para {formatDate(family.first_shortfall_due)}; SKUs {family.skus_short.join(', ')}{orders && `; pedidos em carteira desses SKUs: ${orders}${family.affected_orders.length > 3 ? '…' : ''}`}.</p>;
}

/** Etapa 15.4: onde a produção planejada não cabe na capacidade livre de cada linha, semana a semana. */
export default function CapacityPage({ refreshToken }: { refreshToken: number }) {
  const { data, error, loading, loadedAt } = useApiResource(api.capacityPlan, refreshToken);
  usePageLoadStatus(loading, data ? '' : error, loadedAt);
  if (!data && loading) return <LoadingState />;
  if (!data) return <p className="fact-line">Plano de capacidade indisponível no momento.</p>;
  const short = data.families.filter((family) => family.status === 'insuficiente');
  const calendarEnd = data.families[0]?.calendar_end;
  const peakMonths = (data.families[0]?.peak_months ?? []).map((month) => MONTHS[month - 1]).join(', ');

  return <div className="revenue-page">
    <PageIntro title="Onde a produção planejada não cabe" description={`Ordens planejadas encaixadas na capacidade livre de cada linha até ${formatDate(calendarEnd)}. Simulação: nada é reservado.`} />
    <SectionCard title="Por linha" action={<Tooltip label="Premissas do encaixe">{data.assumptions.join(' ')}</Tooltip>}>
      <div className="table-shell" tabIndex={0} role="region" aria-label="Capacidade por linha"><table className="data-table">
        <thead><tr><th>Família</th><th>Livre no calendário</th><th>Encaixado</th><th>Sem programação</th><th>Situação</th></tr></thead>
        <tbody>{data.families.map((family) => <tr key={family.family}>
          <td><strong>{family.family}</strong></td>
          <td>{displayQuantity(family.available_until_calendar_end)}</td>
          <td>{displayQuantity(family.planned_in_calendar)}</td>
          <td>{displayQuantity(family.unscheduled_quantity)}</td>
          <td><Badge tone={STATUS_TONE[family.status]}>{STATUS_TEXT[family.status]}</Badge></td>
        </tr>)}</tbody>
      </table></div>
      {short.length ? short.map(shortfallLine) : <p className="fact-line">Todas as ordens planejadas cabem até o fim do calendário.</p>}
      <p className="fact-line">Picos ({peakMonths}): {data.families.filter((family) => family.peak_status).map((family) => `${family.family} ${STATUS_TEXT[family.peak_status as CapacityStatus].toLowerCase()}`).join(' · ')}. Ordens que começariam depois do calendário ficam a confirmar.</p>
    </SectionCard>
    {data.families.map((family) => <details key={family.family} className="validation-details"><summary>Semanas da {family.line || family.family}</summary>
      <div className="table-shell" tabIndex={0} role="region" aria-label={`Semanas da ${family.line || family.family}`}><table className="data-table">
        <thead><tr><th>Semana</th><th>Livre</th><th>Encaixado</th><th>Sobra</th></tr></thead>
        <tbody>{family.weeks.map((week) => <tr key={week.week_start}><td>{formatDate(week.week_start)}</td><td>{displayQuantity(week.available)}</td><td>{displayQuantity(week.allocated)}</td><td>{displayQuantity(week.remaining)}</td></tr>)}</tbody>
      </table></div>
    </details>)}
    <p className="fact-line"><Link to="/fila">Voltar à fila</Link> para ver a ação de cada SKU.</p>
  </div>;
}
