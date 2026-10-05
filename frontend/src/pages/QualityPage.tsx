import { Badge, MetricCard, PageIntro, SectionCard } from '../components';
import type { PageProps } from './shared';

export default function QualityPage({ data }: PageProps<'quality'>) {
  const sheets = Object.entries(data.quality.sheets);
  const totalRecords = sheets.reduce((sum, [, sheet]) => sum + sheet.records, 0);
  const orphanCount = data.quality.foreign_keys.reduce((sum, item) => sum + item.orphan_count, 0);
  return <>
    <PageIntro eyebrow="Confiabilidade" title="Qualidade dos dados" description="Transparência sobre cobertura, integridade e lacunas antes de qualquer decisão." />
    <div className="metrics-grid quality-metrics"><MetricCard label="Registros avaliados" value={totalRecords.toLocaleString('pt-BR')} detail={`${sheets.length} abas carregadas`} tone="blue" icon="quality" /><MetricCard label="Erros bloqueantes" value={data.quality.errors.length} detail="validações da fonte" tone={data.quality.errors.length ? 'red' : 'green'} icon="quality" /><MetricCard label="Chaves órfãs" value={orphanCount} detail="integridade referencial" tone={orphanCount ? 'amber' : 'green'} icon="quality" /><MetricCard label="Cobertura sell-out" value={`${Math.round(data.quality.sell_out_coverage.coverage * 100)}%`} detail={`${data.quality.sell_out_coverage.observed_pairs} de ${data.quality.sell_out_coverage.possible_pairs} pares`} tone="slate" icon="b2b" /></div>
    <SectionCard title="Cobertura da fonte" subtitle="Volume e duplicidades por aba."><div className="table-shell" tabIndex={0} role="region" aria-label="Cobertura da fonte; role horizontalmente para ver todas as colunas"><table className="data-table"><thead><tr><th>Aba</th><th>Registros</th><th>Duplicidades</th><th>Colunas ausentes</th><th>Situação</th></tr></thead><tbody>{sheets.map(([name, sheet]) => <tr key={name}><td><strong>{name.split('_').join(' ')}</strong></td><td>{sheet.records.toLocaleString('pt-BR')}</td><td>{sheet.duplicate_keys}</td><td>{sheet.missing_columns.length}</td><td><Badge tone={!sheet.duplicate_keys && !sheet.missing_columns.length ? 'good' : 'medium'}>{!sheet.duplicate_keys && !sheet.missing_columns.length ? 'Íntegra' : 'Revisar'}</Badge></td></tr>)}</tbody></table></div></SectionCard>
    <div className="notice-card"><div className="notice-icon">i</div><div><strong>Como interpretar a cobertura</strong><p>Dado ausente de sell-out representa falta de observação, não venda igual a zero. O ranking reduz a confiança quando essa visibilidade não existe.</p></div></div>
  </>;
}
