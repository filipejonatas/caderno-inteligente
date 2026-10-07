import { Link } from 'react-router-dom';
import { UpcomingEvents } from '../components/EventAlerts';
import { Badge, EmptyState, Icon, PageIntro, PriorityTable, SectionCard, confidenceTone, mainReason, severityTone } from '../components';
import type { PageProps } from './shared';
import { formatDate, positiveDelayDays, reasonNames, sortReasons } from './shared';

export default function OverviewPage({ data, onSelect }: PageProps<'overview' | 'priorities' | 'config'>) {
  const first = data.priorities[0];
  const weights = data.config.weights;
  const main = first ? mainReason(first.reasons, weights) : undefined;
  const delay = first ? positiveDelayDays(first.first_promised_date, first.first_production_completion) : null;
  return <div className="decision-journey">
    <PageIntro title="O que olhar primeiro" />
    {first ? <article className="attention-focus">
      <div>
        <span className="eyebrow">Primeiro da fila · posição {first.priority}</span>
        <h3>{first.sku} <span>{first.product}</span></h3>
        <p className="answer-line"><strong>{reasonNames[main?.code ?? ''] ?? main?.description ?? 'Sem motivo registrado'}.</strong>{delay !== null && ` Produção prevista para ${formatDate(first.first_production_completion)}, ${delay} ${delay === 1 ? 'dia' : 'dias'} depois da data prometida.`}</p>
        <div className="focus-badges">{sortReasons(first.reasons, weights).slice(0, 3).map(reason => <Badge key={reason.code} tone={severityTone(reason.severity)}>{reasonNames[reason.code] ?? reason.description}</Badge>)}<Badge tone={confidenceTone(first.confidence)}>Confiança nos dados: {first.confidence}</Badge></div>
      </div>
      <div className="focus-actions">
        <button className="primary-button" onClick={() => onSelect(first)}>Abrir evidências de {first.sku}<Icon name="arrow" /></button>
      </div>
    </article> : <><EmptyState title="Nenhum SKU na fila de atenção" description="Não foram retornadas prioridades. Isso não substitui a avaliação da qualidade dos dados." /><Link className="secondary-button" to="/fila">Ver a fila operacional</Link></>}
    <p className="summary-line">{data.overview.rupture_sku_count} SKUs com risco de ruptura ({data.overview.below_lead_time_count} abaixo do prazo de produção, {data.overview.below_safety_stock_count} abaixo da segurança), {data.overview.order_without_production} pedidos sem ordem de produção e {data.overview.low_confidence} de {data.overview.prioritized} SKUs com confiança baixa.</p>
    <UpcomingEvents />
    <SectionCard title={`Fila de atenção (${data.overview.prioritized} de ${data.overview.total_skus})`} action={<Link className="secondary-button" to="/fila?todos=1">Ver a fila completa</Link>}><PriorityTable rows={data.priorities.slice(0, 5)} onSelect={onSelect} weights={weights} /></SectionCard>
  </div>;
}
