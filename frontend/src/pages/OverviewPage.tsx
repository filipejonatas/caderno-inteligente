import { Link } from 'react-router-dom';
import { Badge, EmptyState, Hint, Icon, MetricCard, PageIntro, PriorityTable, SectionCard, confidenceTone, mainReason, severityTone } from '../components';
import type { PageProps } from './shared';
import { displayShare, formatDate, positiveDelayDays, reasonNames, sortReasons } from './shared';

export default function OverviewPage({ data, onSelect }: PageProps<'overview' | 'priorities' | 'quality' | 'config'>) {
  const first = data.priorities[0];
  const weights = data.config.weights;
  const maxRisk = Math.max(...Object.values(data.overview.risk_distribution), 1);
  const coverage = data.quality.sell_out_coverage;
  const main = first ? mainReason(first.reasons, weights) : undefined;
  const delay = first ? positiveDelayDays(first.first_promised_date, first.first_production_completion) : null;
  return <div className="decision-journey">
    <PageIntro title="O que olhar primeiro" description="O primeiro SKU da fila, o porquê e os números que dão contexto." />
    {first ? <article className="attention-focus">
      <div>
        <span className="eyebrow">Primeiro da fila · posição {first.priority}</span>
        <h3>{first.sku} <span>{first.product}</span></h3>
        <p className="answer-line"><strong>{reasonNames[main?.code ?? ''] ?? main?.description ?? 'Sem motivo registrado'}.</strong> {main?.description}{delay !== null && ` A produção está prevista para ${formatDate(first.first_production_completion)}, ${delay} ${delay === 1 ? 'dia' : 'dias'} depois da data prometida.`}</p>
        <div className="focus-badges">{sortReasons(first.reasons, weights).map(reason => <Badge key={reason.code} tone={severityTone(reason.severity)}>{reasonNames[reason.code] ?? reason.description}</Badge>)}<Badge tone={confidenceTone(first.confidence)}>Confiança nos dados: {first.confidence}</Badge></div>
      </div>
      <div className="focus-actions">
        <button className="primary-button" onClick={() => onSelect(first)}>Abrir evidências de {first.sku}<Icon name="arrow" /></button>
        <Link className="secondary-button" to={`/previsoes?busca=${encodeURIComponent(first.sku)}`}>Ver previsão e ação</Link>
      </div>
    </article> : <><EmptyState title="Nenhum SKU na fila de atenção" description="Não foram retornadas prioridades. Isso não substitui a avaliação da qualidade dos dados." /><Link className="secondary-button" to="/previsoes">Ver previsão e ação</Link></>}
    <div className="metrics-grid">
      <MetricCard label="SKUs na fila de atenção" value={data.overview.prioritized} detail={`de ${data.overview.total_skus} SKUs monitorados`} icon="priorities" />
      <MetricCard label="SKUs com risco de ruptura" value={data.overview.rupture_sku_count} detail={`${data.overview.below_lead_time_count} abaixo do prazo de produção e ${data.overview.below_safety_stock_count} abaixo da segurança (alguns estão nos dois)`} tone="red" icon="quality" />
      <MetricCard label="Pedidos sem ordem de produção" value={data.overview.order_without_production} detail="pedidos em carteira sem OP: validar o atendimento" tone="amber" icon="cases" />
      <MetricCard label="Com confiança baixa" value={data.overview.low_confidence} detail={`de ${data.overview.prioritized} SKUs na fila: sem sell-out observado`} tone="slate" icon="b2b" />
    </div>
    <SectionCard title="Fila de atenção" subtitle="Abra um SKU para consultar motivos, valores e origem da evidência." action={<Link className="secondary-button" to="/prioridades">Ver a fila completa</Link>}><PriorityTable rows={data.priorities.slice(0, 5)} onSelect={onSelect} compact weights={weights} /></SectionCard>
    <details className="section-details">
      <summary>Detalhes: qualidade da evidência, decisões e sinais</summary>
      <div className="quality-summary-grid">
        <MetricCard label="Cobertura de sell-out" value={displayShare(coverage.coverage)} detail={`${coverage.observed_pairs} de ${coverage.possible_pairs} combinações parceiro–SKU com venda informada. Ausência de sell-out nunca é tratada como venda zero.`} tone="slate" icon="b2b" />
        <MetricCard label="Decisões registradas" value={data.overview.decision_count} detail={`${data.overview.partner_data_influenced_decision_count} influenciadas por dado de parceiro`} icon="feedback" />
      </div>
      <h3 className="details-heading">Sinais que compõem a análise <Hint term="score" /></h3>
      <p className="details-note">Ocorrências por regra; um SKU pode ter mais de um sinal.</p>
      <div className="risk-bars">{Object.entries(data.overview.risk_distribution).sort((a, b) => b[1] - a[1]).map(([code, value]) => <div className="risk-bar" key={code}><div><span>{reasonNames[code] ?? code}</span><strong>{value}</strong></div><div className="bar-track"><span style={{ width: `${(value / maxRisk) * 100}%` }} /></div></div>)}</div>
    </details>
  </div>;
}
