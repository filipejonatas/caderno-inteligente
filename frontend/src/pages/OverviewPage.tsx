import { Link } from 'react-router-dom';
import { UpcomingEvents } from '../components/EventAlerts';
import { PANEL_ROWS, RevenueOverview, TopOpportunities } from '../components/OverviewPanel';
import { Badge, EmptyState, Icon, PageIntro, PriorityTable, SectionCard, confidenceTone, hasRuptureRisk, mainReason, severityTone } from '../components';
import type { PageProps } from './shared';
import { formatDate, positiveDelayDays, reasonNames, sortReasons } from './shared';

/**
 * Início como painel. A resposta "o que olho primeiro" continua no topo (critério de clareza);
 * o painel vem logo abaixo. Faturamento e oportunidades carregam e falham cada um por si.
 */
export default function OverviewPage({ data, onSelect, refreshToken }: PageProps<'overview' | 'priorities' | 'config'> & { refreshToken: number }) {
  const first = data.priorities[0];
  const weights = data.config.weights;
  const main = first ? mainReason(first.reasons, weights) : undefined;
  const delay = first ? positiveDelayDays(first.first_promised_date, first.first_production_completion) : null;
  const { overview } = data;
  const rupture = data.priorities.filter((row) => hasRuptureRisk(row.reasons));
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
    <dl className="panel-indicators" aria-label="Indicadores de ruptura">
      <div><dt>Risco de ruptura</dt><dd>{overview.rupture_sku_count} SKUs</dd></div>
      <div><dt>Abaixo do prazo de produção</dt><dd>{overview.below_lead_time_count}</dd></div>
      <div><dt>Abaixo do estoque de segurança</dt><dd>{overview.below_safety_stock_count}</dd></div>
      <div><dt>Pedidos sem ordem de produção</dt><dd>{overview.order_without_production}</dd></div>
      <div><dt>Confiança baixa</dt><dd>{overview.low_confidence} de {overview.prioritized}</dd></div>
    </dl>
    <UpcomingEvents />
    <SectionCard title="SKUs com risco de ruptura" subtitle="Na ordem da fila de atenção." action={<Link className="secondary-button" to="/fila?sinal=ruptura">Ver na fila</Link>}>
      {rupture.length ? <PriorityTable rows={rupture.slice(0, PANEL_ROWS)} onSelect={onSelect} weights={weights} /> : <EmptyState title="Nenhum SKU com risco de ruptura" description="Nenhum SKU está abaixo do prazo de produção ou do estoque de segurança." />}
    </SectionCard>
    <TopOpportunities refreshToken={refreshToken} />
    <RevenueOverview refreshToken={refreshToken} />
  </div>;
}
