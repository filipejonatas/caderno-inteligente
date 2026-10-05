import { Link } from 'react-router-dom';
import { Alert, Badge, DecisionBoundary, EmptyState, Icon, MetricCard, PageIntro, PriorityTable, SectionCard, confidenceTone, severityTone } from '../components';
import type { PageProps } from './shared';
import { reasonNames } from './shared';

export default function OverviewPage({ data, onSelect }: PageProps<'overview' | 'priorities' | 'quality'>) {
  const first = data.priorities[0];
  const maxRisk = Math.max(...Object.values(data.overview.risk_distribution), 1);
  const coverage = Math.round(data.quality.sell_out_coverage.coverage * 100);
  return <div className="decision-journey">
    <PageIntro eyebrow="Centro de decisão" title="Da atenção à decisão humana" description="Identifique o sinal, confira a ação sugerida e valide a qualidade da evidência antes de agir." />
    <section aria-labelledby="attention-title">
      <div className="journey-heading"><span>01</span><div><h2 id="attention-title">O que exige atenção</h2><p>Ranking oficial de análise, sem autorização automática de produção.</p></div><Link to="/prioridades" className="secondary-button">Ver prioridades</Link></div>
      {first ? <article className="attention-focus">
        <div><span className="eyebrow">Primeiro da fila · prioridade #{first.priority}</span><h3>{first.sku} <span>{first.product}</span></h3><div className="focus-badges">{first.reasons.map(reason => <Badge key={reason.code} tone={severityTone(reason.severity)}>{reasonNames[reason.code] ?? reason.description}</Badge>)}<Badge tone={confidenceTone(first.confidence)}>Confiança {first.confidence}</Badge></div><p>{first.reasons[0]?.description ?? 'Abra o detalhe para consultar a análise.'}</p></div>
        <button className="primary-button" onClick={() => onSelect(first)}>Abrir evidências de {first.sku}<Icon name="arrow" /></button>
      </article> : <EmptyState title="Nenhum SKU na fila de atenção" description="Não foram retornadas prioridades. Isso não substitui a avaliação da qualidade dos dados." />}
      <div className="metrics-grid">
        <MetricCard label="SKUs priorizados" value={data.overview.prioritized} detail={`de ${data.overview.total_skus} SKUs monitorados`} icon="priorities" />
        <MetricCard label="SKUs com risco de ruptura" value={data.overview.rupture_sku_count} detail={`${data.overview.below_lead_time_count} abaixo do lead time · ${data.overview.below_safety_stock_count} abaixo da segurança`} tone="red" icon="quality" />
        <MetricCard label="Pedidos sem OP" value={data.overview.order_without_production} detail="validar o atendimento operacional" tone="amber" icon="cases" />
        <MetricCard label="Baixa confiança" value={data.overview.low_confidence} detail="sell-out não observado" tone="slate" icon="b2b" />
      </div>
      <SectionCard title="Fila de atenção" subtitle="Abra um SKU para consultar motivos, valores e origem da evidência." action={<Badge>Ranking oficial</Badge>}><PriorityTable rows={data.priorities.slice(0, 5)} onSelect={onSelect} compact /></SectionCard>
    </section>
    <section aria-labelledby="actions-title">
      <div className="journey-heading"><span>02</span><div><h2 id="actions-title">Ações sugeridas</h2><p>Próximos passos de análise. As recomendações operacionais são calculadas no backend.</p></div></div>
      <DecisionBoundary />
      <div className="journey-shortcuts">
        <Link to={first ? `/previsoes?busca=${encodeURIComponent(first.sku)}` : '/previsoes'}><Icon name="forecasts" /><strong>Consultar previsão e ação</strong><span>{first ? `Conferir a recomendação de ${first.sku}` : 'Consultar as recomendações disponíveis'}</span><small>Demanda, quantidade sugerida e capacidade</small></Link>
        <Link to="/parceiros"><Icon name="b2b" /><strong>Verificar parceiros</strong><span>Entender a cobertura de sell-out</span><small>Ausência de informação não significa venda zero</small></Link>
        <Link to="/qualidade"><Icon name="quality" /><strong>Validar os dados</strong><span>Conferir lacunas e integridade</span><small>Integridade e ausências na fonte disponível</small></Link>
        <Link to="/decisoes"><Icon name="feedback" /><strong>Registrar decisão humana</strong><span>Documentar o que foi decidido</span><small>Sem alterar automaticamente regras ou produção</small></Link>
      </div>
    </section>
    <section aria-labelledby="decision-quality-title">
      <div className="journey-heading"><span>03</span><div><h2 id="decision-quality-title">Qualidade da decisão</h2><p>Visibilidade, evidência e decisões registradas no recorte disponível.</p></div></div>
      <div className="quality-summary-grid">
        <MetricCard label="Cobertura de sell-out" value={`${coverage}%`} detail={`${data.quality.sell_out_coverage.observed_pairs} de ${data.quality.sell_out_coverage.possible_pairs} pares observados`} tone="slate" icon="b2b" />
        <MetricCard label="Decisões registradas" value={data.overview.decision_count} detail="feedbacks salvos pelo PCP" icon="feedback" />
        <MetricCard label="Influenciadas por dado parceiro" value={data.overview.partner_data_influenced_decision_count} detail="decisões alteradas ou fortalecidas" tone="slate" icon="feedback" />
      </div>
      <Alert title="Limite da evidência observada" tone={coverage < 100 ? 'warning' : 'info'}>A cobertura mede pares parceiro–SKU com informação, não o desempenho comercial dos parceiros. Ausência de sell-out nunca é tratada como venda zero.</Alert>
      <SectionCard title="Sinais que compõem a análise" subtitle="Ocorrências por regra; um SKU pode apresentar mais de um sinal."><div className="risk-bars">{Object.entries(data.overview.risk_distribution).sort((a, b) => b[1] - a[1]).map(([code, value]) => <div className="risk-bar" key={code}><div><span>{reasonNames[code] ?? code}</span><strong>{value}</strong></div><div className="bar-track"><span style={{ width: `${(value / maxRisk) * 100}%` }} /></div></div>)}</div></SectionCard>
    </section>
  </div>;
}
