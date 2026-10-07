import type { ChallengeAction } from './types-actions';

export type CommercialAction = 'avaliar_reposicao' | 'monitorar_estoque' | 'investigar_divergencia' | 'solicitar_atualizacao' | 'dados_insuficientes'
  | 'conter_reposicao' | 'monitorar_excesso_parceiro';
export type CommercialQuality = 'sufficient' | 'stale' | 'insufficient';
export interface PartnerSummary {
  code: string; name: string; type: string; region: string | null; channel: string | null;
  state: string | null; city: string | null; observed_skus: number; linked_skus: number;
  challenge_action?: ChallengeAction | null;
  total_catalog_skus: number; coverage: number; latest_sell_out_month: string | null;
  backlog_quantity: number; action_counts: Record<CommercialAction, number>; quality_counts: Record<CommercialQuality, number>;
}
export interface CommercialRow {
  partner: string; partner_name: string; sku: string; product: string; region: string | null; channel: string | null;
  reference_month: string | null; window_months: string[]; sell_in_recent: number | null; sell_out_recent: number | null;
  sell_in_months: string[]; sell_out_months: string[]; comparable_months: string[];
  comparable_sell_in: number | null; comparable_sell_out: number | null; comparable_difference: number | null;
  divergence_ratio: number | null; estimated_stock: number | null; stock_month: string | null; data_nature: string | null;
  average_monthly_sell_out: number | null; coverage_days: number | null; age_months: number | null; missing_months: string[];
  data_quality: CommercialQuality; backlog_quantity: number; backlog_order_count: number;
  orders: Array<{ order: string; quantity: number; promised_date: string | null; status: string }>;
  signals: Array<{ code: string; label: string }>;
  action: CommercialAction; action_label: string; requires_human_review: boolean; recommendation_reason: string;
  challenge_action?: ChallengeAction;
  /** Etapa 15.5: janela de acúmulo no parceiro. */
  buildup_window_months?: number; sell_through_window?: number | null; stock_start?: number | null; stock_growth?: number | null;
  stock_identity_consistent?: boolean | null;
  periods: Array<{ month: string; sell_in_quantity: number | null; sell_out_quantity: number | null; estimated_stock: number | null; data_nature: string | null }>;
}
export interface CommercialMetadata {
  reference_month: string | null; limitation: string; thresholds: Record<string, number>;
  field_nature: Record<string, { nature: string; origin: string }>;
  challenge_labels?: Record<string, string>;
}
export interface CommercialPage<T> extends CommercialMetadata { items: T[]; total: number; offset: number; limit: number }
export interface PartnerDetail extends CommercialMetadata {
  partner: PartnerSummary;
  decisions: { attribution_available: boolean; items: null; reason: string };
}
