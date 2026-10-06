import type { ChallengeAction } from './types-actions';

export type ChannelTrend = 'crescente' | 'estável' | 'decrescente' | 'indeterminada';
export type ChannelSignal = 'NOT_SOLD' | 'STOPPED' | 'DECLINING' | 'GROWING' | 'DISCONTINUING_PRODUCT' | 'OPEN_BACKLOG';
export type ChannelSuggestionCode = 'avaliar_ampliacao_mix' | 'avaliar_reativacao' | 'investigar_queda' | 'monitorar_saida_de_linha' | 'acompanhar_crescimento' | 'sem_acao_necessaria';

export interface ChannelSummary {
  code: string; name: string | null; region: string | null; declared_coverage: string | null; declared_skus: number | null; sell_out_rows: number;
  observed_skus: number; catalog_skus: number; revenue_24m: number | null; units_24m: number; share_of_revenue: number | null; share_of_units: number | null;
  revenue_recent: number | null; revenue_previous: number | null; trend: ChannelTrend; change_ratio: number | null; yoy_ratio: number | null;
  monthly: { months: string[]; revenue: Array<number | null>; units: Array<number | null> };
  concentration: { top5_share: number | null; skus_for_target_share: number | null; target_share: number };
  backlog: { open_orders: number; open_quantity: number | null; skus: number };
  signal_counts: Partial<Record<ChannelSignal, number>>; suggestion_counts: Partial<Record<ChannelSuggestionCode, number>>;
}

export interface ChannelSkuRow {
  sku: string; product: string | null; family: string | null; product_status: string | null; months_sold: number; first_month: string | null; last_month: string | null;
  units_24m: number | null; revenue_24m: number | null; share_in_channel: number | null; rank: number | null; cumulative_share: number | null;
  units_recent: number | null; units_previous: number | null; trend: ChannelTrend; change_ratio: number | null; yoy_ratio: number | null;
  partners_units_recent: number | null; direct_share_of_sku_recent: number | null; backlog_open_quantity: number | null; backlog_open_orders: number;
  challenge_action?: ChallengeAction;
  signals: ChannelSignal[]; suggestion: { code: ChannelSuggestionCode; label: string; reason: string; requires_human_review: boolean };
}

export interface ChannelFinding {
  code: string; severity: string; affects: string[]; title: string; summary: string; treatment: string; treatment_label: string;
  evidence: Array<Record<string, unknown>> | Record<string, unknown>;
}

interface ChannelMeta {
  reference_month: string; signal_labels: Record<ChannelSignal, string>; suggestion_labels: Record<ChannelSuggestionCode, string>;
  field_nature: Record<string, { nature: string; origin: string }>; limitations: string[]; settings: Record<string, number>;
}

export interface DirectChannelsOverview extends ChannelMeta {
  totals: { direct_revenue_24m: number | null; total_revenue_24m: number | null; direct_share_of_revenue: number | null; direct_share_of_units: number | null };
  channels: ChannelSummary[]; findings: ChannelFinding[];
}

export interface DirectChannelDetail extends ChannelMeta { channel: ChannelSummary; total: number; items: ChannelSkuRow[]; challenge_labels?: Record<string, string> }
