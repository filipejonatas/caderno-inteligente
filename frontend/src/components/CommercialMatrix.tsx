import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Badge, EmptyState, Hint, SectionCard } from '../components';
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

/** Evidência de um vínculo parceiro–SKU: o motivo, três números e a origem mensal. */
function Evidence({ row }: { row: CommercialRow }) {
  return <div className="evidence-body">
    <p><strong>Por que esta sugestão:</strong> {localizeText(row.recommendation_reason)}</p>
    <dl className="evidence-figures">
      <div><dt>Enviado (sell-in)</dt><dd>{displayUnits(row.sell_in_recent)}{row.sell_in_months.length === 0 && <small>Não observado</small>}</dd></div>
      <div><dt>Vendido (sell-out)</dt><dd>{displayUnits(row.sell_out_recent)}{row.sell_out_months.length === 0 ? <small>Não observado</small> : <small>{row.sell_out_months.map(monthLabel).join(', ')}</small>}</dd></div>
      <div><dt>Estoque estimado</dt><dd>{displayUnits(row.estimated_stock)}<small>{monthLabel(row.stock_month)} · estimado</small></dd></div>
    </dl>
    <div className="table-shell" tabIndex={0} role="region" aria-label={`Origem mensal de ${row.partner} e ${row.sku}`}><table className="data-table"><caption>Origem: Sell_In e Sell_Out · {row.partner} · {row.sku}</caption><thead><tr><th>Mês</th><th>Enviado</th><th>Vendido</th></tr></thead><tbody>{row.periods.map(period => <tr key={period.month}><td>{monthLabel(period.month)}</td><td>{displayNumber(period.sell_in_quantity)}</td><td>{displayNumber(period.sell_out_quantity)}</td></tr>)}</tbody></table></div>
    {row.orders.length > 0 && <ul className="plain-list">{row.orders.map(order => <li key={order.order}>Pedido {order.order}: {displayUnits(order.quantity)}, prometido para {order.promised_date ? formatDate(order.promised_date) : 'data ausente'} ({order.status}).</li>)}</ul>}
  </div>;
}

export function CommercialMatrix({ response }: { response: CommercialPage<CommercialRow> }) {
  const [open, setOpen] = useState<Set<string>>(new Set());
  const single = response.items.length === 1;
  const toggle = (key: string) => setOpen(current => { const next = new Set(current); if (next.has(key)) next.delete(key); else next.add(key); return next; });
  // Quando todas as linhas têm a mesma ação e dados suficientes (ex.: lista de oportunidades), a coluna não informa nada.
  const uniform = response.items.length > 1 && response.items.every(row => row.action === response.items[0].action && row.data_quality === 'sufficient');
  const columns = uniform ? 5 : 6;
  return <>
    <SectionCard title="Matriz parceiro–SKU">
      {!response.items.length ? <EmptyState title="Nenhum vínculo neste recorte" description="Ajuste os filtros. Não são criadas combinações entre todos os parceiros e todos os SKUs." /> : <div className="table-shell" tabIndex={0} role="region" aria-label="Matriz comercial; role horizontalmente para ver todas as colunas"><table className="data-table commercial-table responsive-table"><thead><tr><th>Parceiro / SKU</th>{!uniform && <th>Ação comercial</th>}<th>Estoque estimado (un.)</th><th>Cobertura (dias)</th><th>Vende por mês (un.) <Hint term="sellout" /></th><th><span className="sr-only">Evidências</span></th></tr></thead><tbody>{response.items.map(row => {
        const key = rowKey(row);
        // Com um único vínculo (ex.: filtro por SKU) a evidência já vem aberta; o botão continua podendo recolher.
        const expanded = single ? !open.has(key) : open.has(key);
        return [
          <tr key={key} className={expanded ? 'is-expanded' : ''}>
            <td data-label="Parceiro / SKU"><Link to={`/parceiros/${encodeURIComponent(row.partner)}`}>{row.partner_name}</Link><br /><Link to={`/skus/${encodeURIComponent(row.sku)}`}>{row.sku}</Link><small>{row.product}</small></td>
            {!uniform && <td className="cell-stack" data-label="Ação comercial"><strong className="commercial-action">{row.action_label}</strong>{row.data_quality !== 'sufficient' && <Badge tone="medium">{qualityLabels[row.data_quality]}</Badge>}</td>}
            <td data-label="Estoque estimado">{displayNumber(row.estimated_stock)}</td>
            <td data-label="Cobertura">{displayDays(row.coverage_days)}</td>
            <td data-label="Vende por mês">{displayNumber(row.average_monthly_sell_out)}</td>
            <td className="cell-action"><button type="button" className="secondary-button evidence-toggle" aria-expanded={expanded} aria-label={`Evidências de ${row.partner} · ${row.sku} — ${row.action_label}`} onClick={() => toggle(key)}>{expanded ? 'Ocultar evidências' : 'Ver evidências'}</button></td>
          </tr>,
          expanded && <tr key={`${key}-evidence`} className="evidence-row"><td colSpan={columns}><Evidence row={row} /></td></tr>,
        ];
      })}</tbody></table></div>}
    </SectionCard>
  </>;
}

/** Método, natureza dos campos e limites configurados: material de auditoria (página Auditoria). */
export function CommercialMethod({ response }: { response: Pick<CommercialPage<unknown>, 'limitation' | 'field_nature' | 'thresholds'> }) {
  return <div>
    <p>{response.limitation}</p>
    <ul>{Object.entries(response.field_nature).map(([name, info]) => <li key={name}><strong>{name.split('_').join(' ')}</strong>: {info.nature}. Origem: {info.origin}.</li>)}</ul>
    <dl className="commercial-thresholds">{Object.entries(response.thresholds).map(([key, value]) => <div key={key}><dt>{thresholdNames[key] ?? key}</dt><dd>{displayNumber(value)}</dd></div>)}</dl>
    <p>Limites demonstrativos, não validados como política comercial pela empresa. Nenhuma recomendação libera reposição ou produção automaticamente.</p>
  </div>;
}
