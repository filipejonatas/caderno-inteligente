import { Link } from 'react-router-dom';
import { api } from '../api';
import { useApiResource } from '../hooks/useApiResource';
import { Badge, Hint, SectionCard, Tooltip } from '../components';
import { displayCurrency, displayNumber, displayPercent, displayShare } from '../pages/shared';
import type { ChannelFinding, ChannelSkuRow, ChannelSuggestionCode, ChannelSummary, ChannelTrend, DirectChannelsOverview } from '../types-channels';

const TREND_TEXT: Record<ChannelTrend, string> = { crescente: 'Crescente', estável: 'Estável', decrescente: 'Decrescente', indeterminada: 'Indeterminada' };
const TREND_TONE: Record<ChannelTrend, string> = { crescente: 'good', estável: 'neutral', decrescente: 'medium', indeterminada: 'neutral' };
const SUGGESTION_TONE: Record<ChannelSuggestionCode, string> = {
  avaliar_ampliacao_mix: 'info', avaliar_reativacao: 'info', investigar_queda: 'medium', monitorar_saida_de_linha: 'neutral', acompanhar_crescimento: 'good', sem_acao_necessaria: 'neutral',
};

const signed = (ratio: number | null) => ratio === null ? '' : ` (${ratio >= 0 ? '+' : '−'}${displayPercent(Math.abs(ratio))})`;
export const trendLabel = (trend: ChannelTrend, ratio: number | null) => `${TREND_TEXT[trend]}${signed(ratio)}`;

export function TrendBadge({ trend, ratio }: { trend: ChannelTrend; ratio: number | null }) {
  return <Badge tone={TREND_TONE[trend]}>{trendLabel(trend, ratio)}</Badge>;
}

export function backlogText(open: number, quantity: number | null) {
  return open === 0 ? 'Nenhum pedido aberto' : `${open} ${open === 1 ? 'pedido' : 'pedidos'} · ${displayNumber(quantity)} un.`;
}

/** Aba "Canais diretos" de Parceiros. */
export function DirectChannelsTab({ data }: { data: DirectChannelsOverview }) {
  return <SectionCard title="Canais diretos" action={<Hint term="canais_diretos" />}>
    <p className="summary-line">Os canais diretos somam <strong>{displayShare(data.totals.direct_share_of_revenue)}</strong> do faturamento observado nos últimos 24 meses, com visibilidade completa do consumidor pelo faturamento.</p>
    <div className="table-shell" tabIndex={0} role="region" aria-label="Canais diretos; role horizontalmente para ver todas as colunas"><table className="data-table responsive-table"><thead><tr><th>Canal</th><th>Faturamento (24 meses)</th><th>Tendência recente</th><th>Carteira aberta</th><th><span className="sr-only">Abrir</span></th></tr></thead><tbody>{data.channels.map((channel: ChannelSummary) => <tr key={channel.code}>
      <td data-label="Canal"><strong>{channel.name ?? channel.code}</strong><small>{channel.region ?? 'Região ausente'} · {displayShare(channel.share_of_revenue)} do total</small></td>
      <td data-label="Faturamento">{displayCurrency(channel.revenue_24m)} <Badge tone="neutral">Observado</Badge></td>
      <td data-label="Tendência"><TrendBadge trend={channel.trend} ratio={channel.change_ratio} /></td>
      <td data-label="Carteira">{backlogText(channel.backlog.open_orders, channel.backlog.open_quantity)}</td>
      <td className="cell-action"><Link className="secondary-button" to={`/canais/${encodeURIComponent(channel.code)}`} aria-label={`Abrir canal ${channel.name ?? channel.code} e faturamento por SKU`}>Abrir</Link></td>
    </tr>)}</tbody></table></div>
  </SectionCard>;
}

export function SuggestionBadge({ row }: { row: ChannelSkuRow }) {
  const { suggestion } = row;
  return <><Badge tone={SUGGESTION_TONE[suggestion.code]}>{suggestion.label}</Badge><Tooltip label={`Por que: ${suggestion.label} em ${row.sku}`}>{suggestion.reason} Sugestão para revisão humana.</Tooltip></>;
}

function evidenceText(finding: ChannelFinding): string {
  const evidence = finding.evidence;
  if (finding.code === 'DIRECT_COVERAGE_NOT_IN_SELL_OUT' && Array.isArray(evidence)) {
    const rows = evidence.reduce((sum, item) => sum + Number(item.sell_out_rows ?? 0), 0);
    return `Declaram cobertura completa; Sell_Out tem ${rows} linhas.`;
  }
  if (finding.code === 'KA_SELL_IN_DIFFERS_FROM_BILLING' && !Array.isArray(evidence)) {
    return `${evidence.equal_pairs} de ${evidence.overlapping_pairs} pares iguais; Sell_In ≈ ${String(evidence.median_sell_in_over_billing).replace('.', ',')}× o faturado.`;
  }
  return finding.summary;
}

/** Achados entre abas que afetam a leitura dos canais. Camada aditiva: se falhar, a página de qualidade segue completa. */
export function ChannelFindings() {
  const { data, error } = useApiResource(api.channelFindings);
  if (!data) return error ? <p className="fact-line">Achados dos canais indisponíveis no momento.</p> : null;
  if (!data.findings.length) return null;
  return <SectionCard title="Achados entre abas">
    <div className="table-shell" tabIndex={0} role="region" aria-label="Achados entre abas que afetam os canais"><table className="data-table responsive-table"><caption className="sr-only">Inconsistências entre abas da planilha que afetam a leitura dos canais; nada foi reconciliado</caption><thead><tr><th>Achado</th><th>O que a planilha mostra</th><th>Como foi tratado</th></tr></thead><tbody>{data.findings.map((finding) => <tr key={finding.code}>
      <td data-label="Achado"><strong>{finding.title}</strong><Tooltip label={`Detalhe do achado: ${finding.title}`}>{finding.summary} Afeta: {finding.affects.join(', ')}.</Tooltip></td>
      <td data-label="O que mostra">{evidenceText(finding)}</td>
      <td data-label="Tratamento">{finding.treatment_label}<Tooltip label={`Como foi tratado: ${finding.title}`}>{finding.treatment}</Tooltip></td>
    </tr>)}</tbody></table></div>
  </SectionCard>;
}
