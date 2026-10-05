import { Badge, EmptyState, PageIntro, ProgressBar } from '../components';
import type { PageProps } from './shared';
import { formatDate, partnerLevelTone } from './shared';

export default function B2BPage({ data }: PageProps<'b2b'>) {
  return <>
    <PageIntro eyebrow="Colaboração comercial" title="Visibilidade B2B2C" description={`Cobertura dos parceiros com referência em ${formatDate(data.b2b.reference_month)}.`} />
    {!data.b2b.partners.length && <EmptyState title="Nenhum parceiro disponível" description="Não foram retornados parceiros neste recorte. Ausência de informação não significa venda zero." />}
    <div className="partners-grid">{data.b2b.partners.map((partner) => <article className="partner-card" key={partner.partner}>
      <div className="partner-head"><div className="partner-avatar">{partner.name.slice(0, 2).toUpperCase()}</div><div><strong>{partner.name}</strong><span>{partner.partner}</span></div><strong className="coverage-value">{Math.round(partner.coverage * 100)}%</strong></div>
      <div className="partner-level"><span>Nível demonstrativo</span><Badge tone={partnerLevelTone(partner.level)}>{partner.level}</Badge></div><ProgressBar value={partner.coverage} tone={partner.coverage < .4 ? 'red' : 'blue'} />
      <div className="partner-stats"><span><strong>{partner.observed_skus}/{partner.total_skus}</strong>SKUs observados</span><span><strong>{partner.months_observed}</strong>meses disponíveis</span></div>
      <div className="partner-recency"><span>Último sell-out</span><strong>{formatDate(partner.latest_sell_out_month)}</strong></div>
      <div className="partner-next"><span>{partner.next_level ? 'Próximo nível' : 'Situação do nível'}</span><strong>{partner.next_level ?? 'Nível máximo demonstrativo'}</strong><p>{partner.next_level_requirement}</p></div>
    </article>)}</div>
    <div className="notice-card"><div className="notice-icon">i</div><div><strong>Classificação demonstrativa</strong><p>{data.b2b.classification_disclaimer}</p><p>{data.b2b.note}</p></div></div>
  </>;
}
