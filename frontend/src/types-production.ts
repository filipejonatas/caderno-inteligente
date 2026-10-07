/** Produção planejada por mês de liberação (GET /api/production-plan). Plano sugerido, não ordem liberada. */
export interface ProductionMonth { month: string; urgent: number; later: number }
export interface ProductionBlock { months: ProductionMonth[]; urgent_total: number; horizon_total: number }
export interface ProductionFamily extends ProductionBlock { family: string }
export interface ProductionPlan {
  reference_date: string | null;
  horizon_end: string | null;
  urgent_window_end: string | null;
  max_lead_time_days: number | null;
  total: ProductionBlock;
  families: ProductionFamily[];
  excluded_skus: Array<{ sku: string; reason: 'sem_previsao' }>;
  omitted_months: string[];
  field_nature: Record<string, { nature: string; origin: string }>;
  limitations: string[];
  requires_human_review: boolean;
}
