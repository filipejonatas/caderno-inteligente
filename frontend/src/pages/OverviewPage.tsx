import { Badge, Icon, MetricCard, PageIntro, PriorityTable, SectionCard } from '../components';
import type { PageProps } from './shared';
import { reasonNames } from './shared';

export default function OverviewPage({ data, onSelect }: PageProps) {
  const maxRisk = Math.max(...Object.values(data.overview.risk_distribution), 1);
  return <>
    <PageIntro eyebrow="Centro de decisão" title="O que exige atenção hoje" description="Riscos, lacunas de dados e prioridades reunidos para orientar a análise do PCP." />
    <div className="metrics-grid">
      <MetricCard label="SKUs priorizados" value={data.overview.prioritized} detail={`de ${data.overview.total_skus} SKUs monitorados`} tone="blue" icon="priorities" />
      <MetricCard label="SKUs com risco de ruptura" value={data.overview.rupture_sku_count} detail={`${data.overview.below_lead_time_count} abaixo do lead time · ${data.overview.below_safety_stock_count} abaixo da segurança`} tone="red" icon="quality" />
      <MetricCard label="Pedidos sem OP" value={data.overview.order_without_production} detail="requerem validação operacional" tone="amber" icon="cases" />
      <MetricCard label="Baixa confiança" value={data.overview.low_confidence} detail="sell-out não observado" tone="slate" icon="b2b" />
    </div>
    <div className="decision-metrics"><MetricCard label="Decisões registradas" value={data.overview.decision_count} detail="feedbacks salvos pelo PCP" tone="blue" icon="feedback" /><MetricCard label="Influenciadas por dado parceiro" value={data.overview.partner_data_influenced_decision_count} detail="decisões alteradas ou fortalecidas" tone="green" icon="b2b" /></div>
    <div className="dashboard-grid">
      <SectionCard className="priorities-card" title="Prioridades mais urgentes" subtitle="Selecione um SKU para ver as evidências completas." action={<span className="live-label"><span />Ranking oficial</span>}><PriorityTable rows={data.priorities.slice(0, 7)} onSelect={onSelect} compact /></SectionCard>
      <SectionCard title="Distribuição dos sinais" subtitle="Quantidade de ocorrências por regra."><div className="risk-bars">{Object.entries(data.overview.risk_distribution).sort((a, b) => b[1] - a[1]).map(([code, value]) => <div className="risk-bar" key={code}><div><span>{reasonNames[code] ?? code}</span><strong>{value}</strong></div><div className="bar-track"><span style={{ width: `${(value / maxRisk) * 100}%` }} /></div></div>)}</div></SectionCard>
    </div>
    <div className="insight-strip"><div className="insight-icon"><Icon name="b2b" /></div><div><strong>Visibilidade do canal ainda é parcial</strong><p>{Math.round(data.quality.sell_out_coverage.coverage * 100)}% dos pares parceiro–SKU possuem sell-out observado. Ausência de dado nunca é tratada como venda zero.</p></div><Badge tone="low">Atenção à confiança</Badge></div>
  </>;
}
