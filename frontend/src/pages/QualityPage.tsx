import { Badge, Hint, MetricCard, PageIntro, SectionCard } from '../components';
import { ChannelFindings } from '../components/ChannelViews';
import type { PageProps } from './shared';
import { displayShare } from './shared';

export default function QualityPage({ data }: PageProps<'quality'>) {
  const sheets = Object.entries(data.quality.sheets);
  const orphanCount = data.quality.foreign_keys.reduce((sum, item) => sum + item.orphan_count, 0);
  const toReview = sheets.filter(([, sheet]) => sheet.duplicate_keys || sheet.missing_columns.length);
  const noErrors = !data.quality.errors.length && !orphanCount;
  const coverage = data.quality.sell_out_coverage;
  return <>
    <PageIntro title="Posso confiar na planilha?" description={noErrors ? `Sem erros bloqueantes e sem registros sem vínculo. O principal limite é a cobertura de sell-out: ${displayShare(coverage.coverage)}.` : 'Há itens para revisar antes de decidir.'} />
    <div className="metrics-grid quality-metrics">
      <MetricCard label="Situação da base" value={noErrors ? 'Sem erros' : `${data.quality.errors.length + orphanCount} a revisar`} detail={`${sheets.length - toReview.length} de ${sheets.length} abas íntegras`} tone={noErrors ? 'green' : 'amber'} icon="quality" />
      <MetricCard label={<>Cobertura de sell-out <Hint term="ausente" /></>} value={displayShare(coverage.coverage)} detail={`${coverage.observed_pairs} de ${coverage.possible_pairs} combinações parceiro–SKU com venda informada`} tone="slate" icon="b2b" />
    </div>
    <ChannelFindings />
    {toReview.length > 0 && <SectionCard title="Abas para revisar">
      <div className="table-shell" tabIndex={0} role="region" aria-label="Abas da planilha; role horizontalmente para ver todas as colunas"><table className="data-table"><thead><tr><th>Aba</th><th>Registros</th><th>Duplicidades</th><th>Colunas ausentes</th><th>Situação</th></tr></thead><tbody>{toReview.map(([name, sheet]) => <tr key={name}><td><strong>{name.split('_').join(' ')}</strong></td><td>{sheet.records.toLocaleString('pt-BR')}</td><td>{sheet.duplicate_keys}</td><td>{sheet.missing_columns.length}</td><td><Badge tone="medium">Revisar</Badge></td></tr>)}</tbody></table></div>
    </SectionCard>}
  </>;
}
