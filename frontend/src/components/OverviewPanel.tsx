import { Link } from 'react-router-dom';
import { api } from '../api';
import { useApiResource } from '../hooks/useApiResource';
import { Alert, EmptyState, SectionCard, Tooltip } from '../components';
import type { ProjectedStockSummary } from '../types';
import { sortOpportunities } from './CommercialMatrix';
import { ProductionPlanChart } from './ProductionPlanChart';
import { RevenueTrend } from './RevenueForecast';
import { displayCurrency, displayDays, displayNumber, displayUnits, formatDate } from '../pages/shared';

/** Quantas linhas cada bloco do painel mostra; a lista completa fica na página de origem. */
export const PANEL_ROWS = 5;

// Loaders fora do componente: identidade estável para o useApiResource.
const loadOpportunities = (signal: AbortSignal) => api.commercialRecommendations(new URLSearchParams({ action: 'avaliar_reposicao', limit: '200' }), signal);

function BlockLoading({ title }: { title: string }) {
  return <SectionCard title={title} subtitle="Carregando…"><div className="drawer-loading"><span /><span /></div></SectionCard>;
}

/** Bloco que falhou: explica e permite nova tentativa sem derrubar o restante do Início. */
function BlockError({ title, error, retry }: { title: string; error: string; retry: () => Promise<void> }) {
  return <Alert tone="warning" title={`${title}: indisponível`} action={<button className="secondary-button" onClick={() => void retry()}>Tentar novamente</button>}>{error || 'Não foi possível carregar este bloco.'} O restante do Início segue válido.</Alert>;
}

const skuCount = (count: number) => `${count} ${count === 1 ? 'SKU' : 'SKUs'}`;
const shortDate = (value: string | null) => value ? formatDate(value).slice(0, 5) : null;

/**
 * Estoque projetado no horizonte da previsão (fase 2): agrega o plano de suprimento que a API já calcula.
 * Vem junto do /api/overview; `null` quando só essa agregação falhou, sem afetar os indicadores de ruptura.
 */
export function ProjectedStockIndicators({ summary }: { summary: ProjectedStockSummary | null }) {
  if (!summary || !summary.horizon_end) return <p className="panel-note">Estoque projetado indisponível agora. Os indicadores de ruptura seguem válidos.</p>;
  const { without_new_orders: base, with_planned_orders: planned, planned_production: production } = summary;
  const firstWeek = shortDate(base.first_shortfall_week);
  const releaseBy = shortDate(production.urgent_window_end);
  return <div className="panel-projected">
    <p className="panel-subhead">Estoque projetado até {formatDate(summary.horizon_end)} <Tooltip label="Como o estoque projetado é calculado">Estoque atual + OPs abertas − demanda (carteira e previsão), dia a dia. “Sem novas ordens” usa só as OPs abertas; “com o plano” soma as ordens planejadas, que exigem revisão humana. Abaixo da segurança inclui os SKUs com falta.</Tooltip></p>
    <dl className="panel-indicators" aria-label="Estoque projetado">
      <div><dt>Falta sem novas ordens</dt><dd>{skuCount(base.shortfall_sku_count)}{firstWeek && <small> a partir da semana de {firstWeek}</small>}</dd></div>
      <div><dt>Falta mesmo com o plano</dt><dd>{skuCount(planned.shortfall_sku_count)}</dd></div>
      <div><dt>Abaixo da segurança com o plano</dt><dd>{skuCount(planned.below_safety_sku_count)}</dd></div>
      <div><dt>Produção planejada agora</dt><dd>{displayUnits(production.urgent_total)}{releaseBy && <small> liberar até {releaseBy}</small>}</dd></div>
    </dl>
    <Link className="secondary-button" to="/fila">Ver a produção planejada</Link>
  </div>;
}

/** O gráfico de produção planejada da fila, sem alterações (empresa toda). Carrega e falha à parte, como os demais blocos. */
export function PlannedProductionOverview({ refreshToken }: { refreshToken: number }) {
  const { data, error, loading, refresh } = useApiResource(api.productionPlan, refreshToken);
  return <ProductionPlanChart data={data} error={error} loading={loading} refresh={refresh} totals={false} />;
}

/** Resumo das oportunidades de reposição (página Comercial): as de menor cobertura de estoque no parceiro. */
export function TopOpportunities({ refreshToken }: { refreshToken: number }) {
  const { data, error, loading, refresh } = useApiResource(loadOpportunities, refreshToken);
  const title = 'Onde repor primeiro';
  if (!data && loading) return <BlockLoading title={title} />;
  if (!data) return <BlockError title={title} error={error} retry={refresh} />;
  const rows = sortOpportunities(data.items, 'urgencia').slice(0, PANEL_ROWS);
  return <SectionCard title={title} subtitle="Menor cobertura de estoque no parceiro primeiro." action={<Link className="secondary-button" to="/parceiros">Ver todas</Link>}>
    {!rows.length ? <EmptyState title="Nenhuma oportunidade de reposição" description="Nenhum parceiro tem sugestão de reposição agora." />
      : <div className="table-shell" tabIndex={0} role="region" aria-label="Principais oportunidades de reposição"><table className="data-table responsive-table"><thead><tr><th>Parceiro / SKU</th><th>Cobertura de estoque (dias)</th><th>Vende por mês (un.)</th></tr></thead><tbody>{rows.map((row) => <tr key={`${row.partner}-${row.sku}`}>
        <td data-label="Parceiro / SKU"><Link to={`/parceiros/${encodeURIComponent(row.partner)}`}>{row.partner_name}</Link><br /><Link to={`/skus/${encodeURIComponent(row.sku)}`}>{row.sku}</Link><small>{row.product}</small></td>
        <td data-label="Cobertura de estoque">{displayDays(row.coverage_days)}</td>
        <td data-label="Vende por mês">{displayNumber(row.average_monthly_sell_out)}</td>
      </tr>)}</tbody></table></div>}
  </SectionCard>;
}

/** O gráfico do Financeiro (observado × estimado, em R$), sem alterações; a análise completa fica em /faturamento. */
export function RevenueOverview({ refreshToken }: { refreshToken: number }) {
  const { data, error, loading, refresh } = useApiResource(api.revenueForecast, refreshToken);
  const title = 'Faturamento observado e estimado';
  if (!data && loading) return <BlockLoading title={title} />;
  if (!data) return <BlockError title={title} error={error} retry={refresh} />;
  const { total } = data;
  return <SectionCard className="revenue-card" title={title} subtitle={`Estimativa de ${displayCurrency(total.revenue_total_3m)} nos próximos três meses.`} action={<Link className="secondary-button" to="/faturamento">Ver o financeiro</Link>}>
    <RevenueTrend observed={total.observed_revenue} months={total.by_month.map((row) => row.month)} values={total.by_month.map((row) => row.revenue)} label={`Faturamento mensal observado e estimado da empresa. Estimativa de ${displayCurrency(total.revenue_total_3m)} em três meses.`} />
  </SectionCard>;
}
