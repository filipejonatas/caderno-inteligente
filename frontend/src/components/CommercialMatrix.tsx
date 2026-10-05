import { Link } from 'react-router-dom';
import { Alert, Badge, EmptyState, SectionCard } from '../components';
import type { CommercialPage, CommercialRow } from '../types-commercial';
import { displayNumber } from '../pages/shared';

export const qualityLabels = { sufficient: 'Suficiente no recorte', stale: 'Antigo/descontínuo', insufficient: 'Insuficiente' };
export const commercialActions = { avaliar_reposicao: 'Avaliar reposição', monitorar_estoque: 'Monitorar estoque do parceiro', investigar_divergencia: 'Investigar divergência', solicitar_atualizacao: 'Solicitar atualização dos dados', dados_insuficientes: 'Sem recomendação por dados insuficientes' };
export const monthLabel = (value: string | null) => value ? value.split('-').reverse().join('/') : 'Não disponível';

export function CommercialMatrix({ response }: { response: CommercialPage<CommercialRow> }) {
  return <>
    <Alert title="Recomendação comercial, não operacional">{response.limitation} Os totais recentes podem ter meses diferentes; a diferença abaixo usa somente os meses comparáveis. Referência: {monthLabel(response.reference_month)}.</Alert>
    <SectionCard title="Matriz parceiro–SKU" subtitle={`${response.items.length} de ${response.total} vínculos neste filtro. Somente vínculos existentes em sell-in/out ou carteira.`}>
      {!response.items.length ? <EmptyState title="Nenhum vínculo neste recorte" description="Ajuste os filtros. Não são criadas combinações entre todos os parceiros e todos os SKUs." /> : <div className="table-shell" tabIndex={0} role="region" aria-label="Matriz comercial; role horizontalmente para ver todas as colunas"><table className="data-table commercial-table"><thead><tr><th>Parceiro / SKU</th><th>Sell-in recente</th><th>Sell-out recente</th><th>Diferença comparável</th><th>Estoque estimado</th><th>Cobertura estimada</th><th>Carteira</th><th>Qualidade / ação comercial</th></tr></thead><tbody>{response.items.map(row => <tr key={`${row.partner}-${row.sku}`}>
        <td><Link to={`/parceiros/${encodeURIComponent(row.partner)}`}>{row.partner_name}</Link><br /><Link to={`/skus/${encodeURIComponent(row.sku)}`}>{row.sku}</Link><small>{row.product}</small></td>
        <td>{displayNumber(row.sell_in_recent)}<small>{row.sell_in_months.map(monthLabel).join(', ') || 'Não observado'}</small></td>
        <td>{displayNumber(row.sell_out_recent)}<small>{row.sell_out_months.map(monthLabel).join(', ') || 'Não observado'}</small></td>
        <td>{displayNumber(row.comparable_difference)}<small>{row.comparable_months.map(monthLabel).join(', ') || 'Sem período comparável'}</small></td>
        <td>{displayNumber(row.estimated_stock)}<small>{monthLabel(row.stock_month)} · estimado</small></td><td>{displayNumber(row.coverage_days)} dias</td><td>{displayNumber(row.backlog_quantity)}<small>{row.backlog_order_count} pedidos</small></td>
        <td><Badge tone={row.data_quality === 'sufficient' ? 'neutral' : 'medium'}>{qualityLabels[row.data_quality]}</Badge><strong className="commercial-action">{row.action_label}</strong></td>
      </tr>)}</tbody></table></div>}
    </SectionCard>
    {response.items.map(row => <details className="commercial-evidence" key={`${row.partner}-${row.sku}`}><summary>Evidências de {row.partner} · {row.sku} — {row.action_label}</summary><div>
      <p><strong>Escopo:</strong> {row.partner_name} · {row.sku}. Região: {row.region ?? 'Não disponível'} · Canal: {row.channel ?? 'Não disponível'}.</p>
      <p><strong>Sinais:</strong> {row.signals.map(signal => signal.label).join('; ') || 'Sem sinal comercial de exceção neste recorte; monitoramento não afirma excesso.'}</p>
      <p><strong>Atualidade:</strong> {row.age_months === null ? 'Não calculável' : `${row.age_months} meses em relação à referência da base`}. Meses recentes sem sell-out: {row.missing_months.map(monthLabel).join(', ') || 'Nenhum'}.</p>
      <p><strong>Natureza do sell-out:</strong> {row.data_nature ?? 'Não declarada'}. Estoque estimado na fonte, não auditado.</p>
      <p><strong>Comparação:</strong> sell-in {displayNumber(row.comparable_sell_in)} − sell-out {displayNumber(row.comparable_sell_out)} = {displayNumber(row.comparable_difference)}. Meses: {row.comparable_months.map(monthLabel).join(', ') || 'Nenhum'}.</p>
      <p><strong>Cobertura:</strong> estoque estimado {displayNumber(row.estimated_stock)} / (média mensal observada {displayNumber(row.average_monthly_sell_out)} / 30). Sem giro ou dado suficiente, não há cobertura calculável nem recomendação de reposição.</p>
      <p>{row.recommendation_reason}</p>
      <div className="table-shell" tabIndex={0} role="region" aria-label={`Origem mensal de ${row.partner} e ${row.sku}`}><table className="data-table"><caption>Origem: Sell_In e Sell_Out · {row.partner} · {row.sku}</caption><thead><tr><th>Mês</th><th>Enviado</th><th>Vendido</th><th>Estoque estimado</th><th>Natureza declarada</th></tr></thead><tbody>{row.periods.map(period => <tr key={period.month}><td>{monthLabel(period.month)}</td><td>{displayNumber(period.sell_in_quantity)}</td><td>{displayNumber(period.sell_out_quantity)}</td><td>{displayNumber(period.estimated_stock)}</td><td>{period.data_nature ?? 'Não declarada'}</td></tr>)}</tbody></table></div>
      {row.orders.length > 0 && <ul>{row.orders.map(order => <li key={order.order}>Carteira_Pedidos: {order.order} · {displayNumber(order.quantity)} unidades · promessa {order.promised_date ?? 'ausente'} · {order.status}</li>)}</ul>}
      <p>Carteira não é venda realizada nem produção alocada. Não foi somada ao giro observado.</p>
    </div></details>)}
    <details className="commercial-evidence"><summary>Método, natureza dos campos e limites configurados</summary><div><ul>{Object.entries(response.field_nature).map(([name, info]) => <li key={name}><strong>{name}</strong>: {info.nature}. Origem: {info.origin}.</li>)}</ul><dl className="commercial-thresholds">{Object.entries(response.thresholds).map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{displayNumber(value)}</dd></div>)}</dl><p>Limites demonstrativos, não validados como política comercial pela empresa. Nenhuma recomendação libera reposição ou produção automaticamente.</p></div></details>
  </>;
}
