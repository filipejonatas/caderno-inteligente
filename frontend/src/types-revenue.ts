import type { Confidence } from './types';

export type RevenueStatus = 'ok' | 'sem_preco' | 'sem_previsao';

export interface ObservedRevenue { months: string[]; values: Array<number | null> }

export interface CommercialRevenueReference {
  months: string[]; commercial_units: number[]; model_revenue: number | null; commercial_revenue: number | null;
  difference_ratio: number | null; origins: string[]; note: string;
}

export interface RevenueItem {
  sku: string; product: string | null; family: string; status: RevenueStatus; reason: string | null;
  unit_price: number | null; price_source: string | null; price_conflict: boolean;
  model_label: string | null; forecast_confidence: Confidence;
  forecast_months: string[]; forecast_units: number[];
  revenue_values: number[]; revenue_next_month: number | null; revenue_total_3m: number | null;
  commercial_reference: CommercialRevenueReference | null;
  calculation: { formula: string; terms: Array<{ month: string; units: number; unit_price: number; revenue: number }> } | null;
  nature: 'estimado'; observed_revenue: ObservedRevenue;
}

export interface RevenueGroup {
  label: string; skus_total: number; skus_with_estimate: number;
  skus_excluded: Array<{ sku: string; status: RevenueStatus; reason: string | null }>;
  by_month: Array<{ month: string; revenue: number }>; revenue_total_3m: number | null;
  confidence_distribution: Record<Confidence, number>; backtest_wape: number | null;
  observed_revenue: ObservedRevenue; observed_last_3m_same_skus: number | null; change_vs_last_3m: number | null;
  commercial_reference: { months: string[]; skus_compared: number; model_revenue: number | null; commercial_revenue: number | null; difference_ratio: number | null } | null;
}

export interface RevenueForecast {
  reference_month: string | null; nature: 'estimado'; formula: string;
  items: RevenueItem[]; families: RevenueGroup[]; total: RevenueGroup;
  field_nature: Record<string, { nature: string; origin: string }>; limitations: string[];
}
