import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Alert, Badge, EmptyState, SectionCard } from '../components';
import type { CommercialPage, CommercialRow } from '../types-commercial';
import { displayDays, displayNumber, displayUnits, formatDate, localizeText } from '../pages/shared';

export const qualityLabels = { sufficient: 'Suficiente no recorte', stale: 'Antigo/descontínuo', insufficient: 'Insuficiente' };
export const commercialActions = { avaliar_reposicao: 'Avaliar reposição', monitorar_estoque: 'Monitorar estoque do parceiro', investigar_divergencia: 'Investigar divergência', solicitar_atualizacao: 'Solicitar atualização dos dados', dados_insuficientes: 'Sem recomendação por dados insuficientes' };
export const monthLabel = (value: string | null) => value ? value.split('-').reverse().join('/') : 'Não disponível';

const thresholdNames: Record<string, string> = {
  recent_months: 'Meses recentes considerados',
  minimum_sell_out_months: 'Mínimo de meses com sell-out',
  maximum_age_months: 'Idade máxima do dado (meses)',
  reposition_coverage_days: 'Cobertura que sugere reposição (dias)',
  excess_coverage_days: 'Cobertura que indica excesso (dias)',
  low_monthly_sell_out: 'Giro mensal considerado baixo (unidades)',
  minimum_excess_stock: 'Estoque mínimo para apontar excesso (unidades)',
  divergence_ratio: 'Divergência sell-in × sell-out (proporção)',
  minimum_divergence_quantity: 'Divergência mínima (unidades)',
};

const rowKey = (row: CommercialRow) => `${row.partner}-${row.sku}`;

function Evidence({ row }: { row: CommercialRow }) {
  return <div className="evidence-body">
    <dl className="evidence-figures">
      <div><dt>Vendido ao parceiro (sell-in)</dt><dd>{displayUnits(row.sell_in_recent)}<small>{row.sell_in_months.map(monthLabel).join(', ') || 'Não observado'}</small></dd></div>
      <div><dt>Vendido pelo parceiro (sell-out)</dt><dd>{displayUnits(row.sell_out_recent)}<small>{row.sell_out_months.map(monthLabel).join(', ') || 'Não observado'}</small></dd></div>
      <div><dt>Diferença comparável</dt><dd>{displayNumber(row.comparable_difference)}<small>{row.comparable_months.map(monthLabel).join(', ') || 'Sem período comparável'}</small></dd></div>
      <div><dt>Carteira</dt><dd>{displayUnits(row.backlog_quantity)}<small>{row.backlog_order_count} pedidos</small></dd></div>
      <div><dt>Qualidade do dado</dt><dd>{qualityLabels[row.data_quality]}</dd></div>
    </dl>
    <p><strong>Por que esta sugestão:</strong> {localizeText(row.recommendation_reason)}</p>
    <p><strong>Escopo:</strong> {row.partner_name} · {row.sku}. Região: {row.region ?? 'Não disponível'} · Canal: {row.channel ?? 'Não disponível'}.</p>
    <p><strong>Sinais:</strong> {row.signals.map(signal => signal.label).join('; ') || 'Sem sinal comercial de exceção neste recorte; monitoramento não afirma excesso.'}</p>
    <p><strong>Atualidade:</strong> {row.age_months === null ? 'Não calculável' : `${row.age_months} meses em relação à referência da base`}. Meses recentes sem sell-out: {row.missing_months.map(monthLabel).join(', ') || 'Nenhum'}.</p>
    <p><strong>Natureza do sell-out:</strong> {row.data_nature ?? 'Não declarada'}. Estoque estimado na fonte, não auditado.</p>
    <p><strong>Comparação:</strong> sell-in {displayNumber(row.comparable_sell_in)} − sell-out {displayNumber(row.comparable_sell_out)} = {displayNumber(row.comparable_difference)}. Meses: {row.comparable_months.map(monthLabel).join(', ') || 'Nenhum'}.</p>
    <p><strong>Cobertura:</strong> estoque estimado {displayNumber(row.estimated_stock)} / (média mensal observada {displayNumber(row.average_monthly_sell_out)} / 30). Sem giro ou dado suficiente, não há cobertura calculável nem recomendação de reposição.</p>
    <div className="table-shell" tabIndex={0} role="region" aria-label={`Origem mensal de ${row.partner} e ${row.sku}`}><table className="data-table"><caption>Origem: Sell_In e Sell_Out · {row.partner} · {row.sku}</caption><thead><tr><th>Mês</th><th>Enviado</th><th>Vendido</th><th>Estoque estimado</th><th>Natureza declarada</th></tr></thead><tbody>{row.periods.map(period => <tr key={period.month}><td>{monthLabel(period.month)}</td><td>{displayNumber(period.sell_in_quantity)}</td><td>{displayNumber(period.sell_out_quantity)}</td><td>{displayNumber(period.estimated_stock)}</td><td>{period.data_nature ?? 'Não declarada'}</td></tr>)}</tbody></table></div>
    {row.orders.length > 0 && <ul>{row.orders.map(order => <li key={order.order}>Carteira_Pedidos: {order.order} · {displayUnits(order.quantity)} · promessa {order.promised_date ? formatDate(order.promised_date) : 'ausente'} · {order.status}</li>)}</ul>}
    <p>Carteira não é venda realizada nem produção alocada. Não foi somada ao giro observado.</p>
  </div>;
}

export function CommercialMatrix({ response }: { response: CommercialPage<CommercialRow> }) {
  const [open, setOpen] = useState<Set<string>>(new Set());
  const single = response.items.length === 1;
  const toggle = (key: string) => setOpen(current => { const next = new Set(current); if (next.has(key)) next.delete(key); else next.add(key); return next; });
  return <>
    <Alert title="Recomendação comercial, não operacional">O estoque do parceiro é estimado e não é o estoque do CD. Ausência de informação não é venda zero. A atualidade é relativa ao mês de referência da base ({monthLabel(response.reference_month)}), não à data atual. Nenhuma sugestão libera reposição ou produção.</Alert>
    <SectionCard title="Matriz parceiro–SKU" subtitle={`${response.items.length} de ${response.total} vínculos neste filtro. Somente vínculos existentes em sell-in/out ou carteira.`}>
      {!response.items.length ? <EmptyState title="Nenhum vínculo neste recorte" description="Ajuste os filtros. Não são criadas combinações entre todos os parceiros e todos os SKUs." /> : <div className="table-shell" tabIndex={0} role="region" aria-label="Matriz comercial; role horizontalmente para ver todas as colunas"><table className="data-table commercial-table responsive-table"><thead><tr><th>Parceiro / SKU</th><th>Ação comercial</th><th>Estoque estimado</th><th>Cobertura estimada</th><th>Giro mensal (sell-out)</th><th><span className="sr-only">Evidências</span></th></tr></thead><tbody>{response.items.map(row => {
        const key = rowKey(row);
        // Com um único vínculo (ex.: filtro por SKU) a evidência já vem aberta; o botão continua podendo recolher.
        const expanded = single ? !open.has(key) : open.has(key);
        return [
          <tr key={key} className={expanded ? 'is-expanded' : ''}>
            <td data-label="Parceiro / SKU"><Link to={`/parceiros/${encodeURIComponent(row.partner)}`}>{row.partner_name}</Link><br /><Link to={`/skus/${encodeURIComponent(row.sku)}`}>{row.sku}</Link><small>{row.product}</small></td>
            <td className="cell-stack" data-label="Ação comercial"><strong className="commercial-action">{row.action_label}</strong><Badge tone={row.data_quality === 'sufficient' ? 'neutral' : 'medium'}>{qualityLabels[row.data_quality]}</Badge></td>
            <td data-label="Estoque estimado">{displayNumber(row.estimated_stock)}<small>{monthLabel(row.stock_month)} · estimado</small></td>
            <td data-label="Cobertura">{displayDays(row.coverage_days)}</td>
            <td data-label="Giro mensal">{displayUnits(row.average_monthly_sell_out)}</td>
            <td className="cell-action"><button type="button" className="secondary-button evidence-toggle" aria-expanded={expanded} aria-label={`Evidências de ${row.partner} · ${row.sku} — ${row.action_label}`} onClick={() => toggle(key)}>{expanded ? 'Ocultar evidências' : 'Ver evidências'}</button></td>
          </tr>,
          expanded && <tr key={`${key}-evidence`} className="evidence-row"><td colSpan={6}><Evidence row={row} /></td></tr>,
        ];
      })}</tbody></table></div>}
    </SectionCard>
    <details className="commercial-evidence"><summary>Método, natureza dos campos e limites configurados</summary><div><p>{response.limitation}</p><ul>{Object.entries(response.field_nature).map(([name, info]) => <li key={name}><strong>{name.split('_').join(' ')}</strong>: {info.nature}. Origem: {info.origin}.</li>)}</ul><dl className="commercial-thresholds">{Object.entries(response.thresholds).map(([key, value]) => <div key={key}><dt>{thresholdNames[key] ?? key}</dt><dd>{displayNumber(value)}</dd></div>)}</dl><p>Limites demonstrativos, não validados como política comercial pela empresa. Nenhuma recomendação libera reposição ou produção automaticamente.</p></div></details>
  </>;
}
