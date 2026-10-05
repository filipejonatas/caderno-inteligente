export type PageId =
  | 'guide'
  | 'overview'
  | 'priorities'
  | 'forecasts'
  | 'cases'
  | 'quality'
  | 'b2b'
  | 'scenarios'
  | 'runs'
  | 'feedback';

export type Severity = 'crítica' | 'alta' | 'média' | 'baixa' | string;
export type Confidence = 'baixa' | 'média' | 'alta' | string;

export interface Reason {
  code: string;
  description: string;
  severity: Severity;
}

export interface Evidence {
  code: string;
  values_used: Record<string, unknown>;
  data_origin: string[];
}

export interface Priority {
  priority: number;
  sku: string;
  product: string;
  family: string;
  attention_score: number;
  confidence: Confidence;
  confidence_reason: string;
  critical_date: string | null;
  critical_date_reason: 'first_promised_date' | 'first_production_completion' | null;
  operational_gap_quantity: number;
  projected_stock_quantity: number;
  first_promised_date: string | null;
  first_production_completion: string | null;
  sell_in_quantity: number | null;
  sell_out_quantity: number | null;
  sell_in_minus_sell_out_quantity: number | null;
  forecast_quantity: number | null;
  analysis_scope: 'SKU global';
  missing_data: string[];
  reasons: Reason[];
  evidence: Evidence[];
  disclaimer: string;
}

export interface SelectedSku {
  sku: string;
  product: string;
  family: string;
  priority: number | null;
  attention_score: number | null;
  confidence: Confidence;
  confidence_reason: string;
}

export interface Overview {
  total_skus: number;
  prioritized: number;
  rupture_sku_count: number;
  below_lead_time_count: number;
  below_safety_stock_count: number;
  rupture_signal_count: number;
  /** @deprecated Use rupture_sku_count. */
  risk_count: number;
  order_without_production: number;
  excess_count: number;
  low_confidence: number;
  decision_count: number;
  partner_data_influenced_decision_count: number;
  risk_distribution: Record<string, number>;
  confidence_distribution: Record<string, number>;
}

export interface Run {
  id: number;
  created_at: string;
  source_hash: string;
  prioritized_skus: number;
}

export interface CaseItem {
  id: number;
  sku: string;
  run_id: number | null;
  status: string;
  owner: string;
  due_date: string;
  action: string;
  note: string;
  created_at: string;
  updated_at: string;
}

export interface PartnerVisibility {
  partner: string;
  name: string;
  observed_skus: number;
  total_skus: number;
  coverage: number;
  latest_sell_out_month: string | null;
  months_observed: number;
  level: 'Sem visibilidade' | 'Essencial' | 'Conectado' | 'Estratégico';
  next_level: 'Essencial' | 'Conectado' | 'Estratégico' | null;
  next_level_required_skus: number;
  next_level_requirement: string;
}

export interface B2BVisibility {
  reference_month: string;
  partners: PartnerVisibility[];
  note: string;
  classification_disclaimer: string;
}

export interface AppConfig {
  weights: Record<string, number>;
  thresholds: Record<string, number>;
  actions: string[];
  partner_data_effects: string[];
  case_statuses: string[];
}

export interface FeedbackItem {
  sku: string;
  action: string;
  note: string;
  user_name: string;
  partner_data_effect: 'nao_utilizado' | 'confirmou' | 'aumentou_confianca' | 'alterou_decisao';
  analysis_minutes: number | null;
  created_at: string;
}

export interface SheetQuality {
  records: number;
  duplicate_keys: number;
  missing_columns: string[];
  missing_values: Record<string, number>;
}

export interface DataQuality {
  errors: Array<Record<string, unknown>>;
  warnings: Array<Record<string, unknown>>;
  sheets: Record<string, SheetQuality>;
  foreign_keys: Array<{ child_sheet: string; orphan_count: number }>;
  sell_out_coverage: {
    observed_pairs: number;
    possible_pairs: number;
    coverage: number;
    missing_data_is_not_zero: boolean;
  };
}

export interface DashboardData {
  overview: Overview;
  priorities: Priority[];
  runs: Run[];
  cases: CaseItem[];
  b2b: B2BVisibility;
  config: AppConfig;
  feedback: FeedbackItem[];
  quality: DataQuality;
}

export interface SkuIssue extends Reason {
  sku: string;
  product: string;
  family: string;
  values_used: Record<string, unknown>;
  data_origin: string[];
}

export interface SkuIndicator {
  SKU: string;
  Produto: string;
  family: string;
  current_stock: number;
  coverage_days_calculated: number;
  lead_time_days: number;
  minimum_lot: number;
  average_sales_per_day: number;
  safety_stock_days: number;
  backlog_order_quantity: number;
  production_order_quantity: number;
  projected_stock_quantity: number;
  operational_gap_quantity: number;
  first_promised_date: string | null;
  first_production_completion: string | null;
  sell_in_quantity: number | null;
  sell_out_quantity: number | null;
  sell_in_minus_sell_out_quantity: number | null;
  sell_out_partner_count: number;
  has_sell_out: boolean;
  forecast_quantity: number | null;
  analysis_scope: 'SKU global';
  missing_data: string[];
}

export interface DemandForecast {
  sku: string;
  reference_month: string | null;
  history_months: number;
  model: 'moving_average_3' | 'seasonal_naive_12' | null;
  model_label: string;
  forecast_months: string[];
  forecast_values: number[];
  forecast_next_month: number | null;
  forecast_total_3m: number | null;
  trend: 'crescente' | 'estável' | 'decrescente' | 'indeterminada';
  trend_change_ratio: number | null;
  backtest_wape: number | null;
  forecast_confidence: Confidence;
  status: 'ok' | 'insufficient_data';
  limitation: string;
}

export interface OperationalRecommendation {
  action: 'investigar_dados' | 'produzir_validar_capacidade' | 'produzir' | 'monitorar_excesso' | 'sem_acao_necessaria';
  action_label: string;
  horizon: string;
  suggested_quantity: number | null;
  raw_quantity: number | null;
  minimum_lot: number;
  forecast_next_month: number | null;
  backlog_quantity: number;
  safety_stock_quantity: number | null;
  current_stock: number;
  open_production_quantity: number;
  capacity_status: 'not_evaluated' | 'requires_review' | 'family_context_available';
  confidence: Confidence;
  confidence_reason: string;
  rationale: string[];
  calculation: Record<string, number>;
  assumptions: string[];
  limitations: string[];
  requires_human_review: boolean;
}

export interface ForecastRecommendationSummary {
  sku: string;
  product: string;
  family: string;
  priority: number | null;
  attention_score: number | null;
  confidence: Confidence;
  confidence_reason: string;
  forecast: DemandForecast;
  operational_recommendation: Pick<
    OperationalRecommendation,
    | 'action'
    | 'action_label'
    | 'suggested_quantity'
    | 'minimum_lot'
    | 'capacity_status'
    | 'confidence'
    | 'confidence_reason'
    | 'requires_human_review'
  >;
}

export interface SkuDetail {
  indicator: SkuIndicator;
  issues: SkuIssue[];
  priority: Priority[];
  score_contributions: Array<{ code: string; weight: number; description: string }>;
  forecast: DemandForecast;
  operational_recommendation: OperationalRecommendation;
  limitation: string;
}

export interface ScenarioResult {
  is_simulation: boolean;
  warning: string;
  weights: Record<string, number>;
  thresholds: Record<string, number>;
  ranking: Priority[];
}
