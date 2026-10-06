import { Badge, Hint, MetricCard, PageIntro, SectionCard } from '../components';
import type { PageProps } from './shared';
import { displayShare } from './shared';

export default function QualityPage({ data }: PageProps<'quality'>) {
  const sheets = Object.entries(data.quality.sheets);
  const totalRecords = sheets.reduce((sum, [, sheet]) => sum + sheet.records, 0);
  const orphanCount = data.quality.foreign_keys.reduce((sum, item) => sum + item.orphan_count, 0);
  const toReview = sheets.filter(([, sheet]) => sheet.duplicate_keys || sheet.missing_columns.length);
  const sound = sheets.length - toReview.length;
  const noErrors = !data.quality.errors.length && !orphanCount;
  const coverage = data.quality.sell_out_coverage;
  return <>
    <PageIntro title="Posso confiar na planilha?" description={noErrors ? 'Sem erros bloqueantes e sem registros sem vínculo. O principal limite é a cobertura de sell-out.' : 'Há itens para revisar antes de decidir.'} />
    <div className="metrics-grid quality-metrics"><MetricCard label="Registros avaliados" value={totalRecords.toLocaleString('pt-BR')} detail={`${sheets.length} abas carregadas`} tone="blue" icon="quality" /><MetricCard label="Situação da base" value={noErrors ? 'Sem erros' : `${data.quality.errors.length + orphanCount} a revisar`} detail={`${data.quality.errors.length} erros bloqueantes · ${orphanCount} registros sem vínculo com o cadastro (chaves órfãs)`} tone={noErrors ? 'green' : 'amber'} icon="quality" /><MetricCard label="Cobertura de sell-out" value={displayShare(coverage.coverage)} detail={`${coverage.observed_pairs} de ${coverage.possible_pairs} combinações parceiro–SKU com venda informada`} tone="slate" icon="b2b" /></div>
    <p className="details-note">Dado ausente de sell-out é falta de observação, não venda igual a zero; o ranking reduz a confiança quando falta essa visibilidade. <Hint term="ausente" /></p>
    <SectionCard title="Abas da planilha" subtitle={`${sound} de ${sheets.length} abas íntegras${toReview.length ? ` · ${toReview.length} para revisar` : ''}.`}>
      <details className="section-details" open={toReview.length > 0}><summary>Ver as {sheets.length} abas</summary>
        <div className="table-shell" tabIndex={0} role="region" aria-label="Abas da planilha; role horizontalmente para ver todas as colunas"><table className="data-table"><thead><tr><th>Aba</th><th>Registros</th><th>Duplicidades</th><th>Colunas ausentes</th><th>Situação</th></tr></thead><tbody>{sheets.map(([name, sheet]) => <tr key={name}><td><strong>{name.split('_').join(' ')}</strong></td><td>{sheet.records.toLocaleString('pt-BR')}</td><td>{sheet.duplicate_keys}</td><td>{sheet.missing_columns.length}</td><td><Badge tone={!sheet.duplicate_keys && !sheet.missing_columns.length ? 'good' : 'medium'}>{!sheet.duplicate_keys && !sheet.missing_columns.length ? 'Íntegra' : 'Revisar'}</Badge></td></tr>)}</tbody></table></div>
      </details>
    </SectionCard>
  </>;
}
