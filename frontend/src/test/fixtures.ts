// Synthetic fixtures typed against the frontend contracts. Never application data: codes start with TEST/KA-T.
import type { AppConfig, B2BVisibility, CaseItem, DataQuality, FeedbackItem, ForecastRecommendationSummary, Overview, Priority, Run, SkuDetail } from '../types';
import type { CommercialPage, CommercialRow, PartnerDetail, PartnerSummary } from '../types-commercial';
import type { RevenueForecast, RevenueItem } from '../types-revenue';
import type { RunComparison } from '../types-runs';
import type { ValidationSummary } from '../types-validation';
import type { SystemInfo } from '../hooks/useSystemInfo';

export const SKU_OK = 'TEST-001';
export const SKU_SHORT = 'TEST / 002'; // Needs URL encoding and has insufficient history.
export const PARTNER = 'KA T1'; // Needs URL encoding.

export function priority(sku: string, position: number, overrides: Partial<Priority> = {}): Priority {
  return {
    priority: position, sku, product: `Produto ${sku}`, family: position % 2 ? 'Família A' : 'Família B', attention_score: 30 - position,
    confidence: position % 2 ? 'média' : 'baixa', confidence_reason: 'Motivo sintético da confiança.',
    critical_date: '2026-09-15', critical_date_reason: 'first_promised_date', operational_gap_quantity: 120, projected_stock_quantity: -20,
    first_promised_date: '2026-09-15', first_production_completion: '2026-09-20', sell_in_quantity: 300, sell_out_quantity: null,
    sell_in_minus_sell_out_quantity: null, forecast_quantity: 200, analysis_scope: 'SKU global', missing_data: ['sell_out_quantity'],
    reasons: [{ code: 'RUP_LEAD_TIME', description: 'Cobertura de estoque abaixo do lead time.', severity: 'alta' }],
    evidence: [{ code: 'RUP_LEAD_TIME', values_used: { coverage_days: 5, lead_time_days: 20 }, data_origin: ['Estoque_Atual.Estoque atual'] }],
    disclaimer: 'Ordenação de atenção; não é decisão automática.', ...overrides,
  };
}

export const priorities: Priority[] = [
  priority(SKU_OK, 1),
  priority(SKU_SHORT, 2, { confidence: 'baixa', family: 'Família B' }),
  priority('TEST-003', 3, { confidence: 'média', family: 'Família A', product: 'Agenda sintética' }),
];

export const overview: Overview = {
  total_skus: 4, prioritized: 3, rupture_sku_count: 2, below_lead_time_count: 2, below_safety_stock_count: 1, rupture_signal_count: 3,
  risk_count: 2, order_without_production: 1, excess_count: 0, low_confidence: 1, decision_count: 0, partner_data_influenced_decision_count: 0,
  risk_distribution: { RUP_LEAD_TIME: 2, RUP_SAFETY_STOCK: 1 }, confidence_distribution: { média: 2, baixa: 1 },
};

export const quality: DataQuality = {
  errors: [], warnings: [],
  sheets: { Produtos: { records: 4, duplicate_keys: 0, missing_columns: [], missing_values: {} } },
  foreign_keys: [{ child_sheet: 'Estoque_Atual', orphan_count: 0 }],
  sell_out_coverage: { observed_pairs: 1, possible_pairs: 4, coverage: 0.25, missing_data_is_not_zero: true },
};

export const config: AppConfig = {
  weights: { RUP_LEAD_TIME: 8, RUP_SAFETY_STOCK: 10, EXCESS_COVERAGE: 3, CAPACITY_CONFLICT: 5 },
  thresholds: { excess_coverage_days: 90, capacity_occupation_threshold: 0.9 },
  actions: ['aceita', 'alterada', 'rejeitada', 'investigar'],
  partner_data_effects: ['nao_utilizado', 'confirmou', 'aumentou_confianca', 'alterou_decisao'],
  case_statuses: ['novo', 'em_investigacao', 'concluido'],
};

export const runs: Run[] = [
  { id: 2, created_at: '2026-10-05T12:00:00+00:00', source_hash: 'hash-test-2-0123456789', prioritized_skus: 3, comparison_schema_version: 1 },
  { id: 1, created_at: '2026-10-01T12:00:00+00:00', source_hash: 'hash-test-1-0123456789', prioritized_skus: 3, comparison_schema_version: null },
];

export const cases: CaseItem[] = [{ id: 1, sku: SKU_OK, run_id: null, status: 'em_investigacao', owner: 'PCP', due_date: '2026-10-10', action: '', note: '', created_at: '2026-10-05T12:00:00+00:00', updated_at: '2026-10-05T12:00:00+00:00' }];
export const feedback: FeedbackItem[] = [];

export const b2b: B2BVisibility = {
  reference_month: '2026-08-01', note: 'Cobertura representa observação disponível.', classification_disclaimer: 'Classificação demonstrativa.',
  partners: [{ partner: PARTNER, name: 'Parceiro sintético', observed_skus: 1, total_skus: 4, coverage: 0.25, latest_sell_out_month: '2026-08-01', months_observed: 3, level: 'Essencial', next_level: 'Conectado', next_level_required_skus: 1, next_level_requirement: 'Observar mais 1 SKU.' }],
};

const forecastOk = {
  sku: SKU_OK, reference_month: '2026-08-01', history_months: 24, model: 'moving_average_3' as const, model_label: 'Média móvel de 3 meses',
  forecast_months: ['2026-09-01', '2026-10-01', '2026-11-01'], forecast_values: [100, 110, 120], forecast_next_month: 100, forecast_total_3m: 330,
  trend: 'crescente' as const, trend_change_ratio: 0.12, backtest_wape: 0.08, forecast_confidence: 'alta', status: 'ok' as const, limitation: 'Previsão estatística sintética.',
};
const forecastShort = {
  sku: SKU_SHORT, reference_month: '2026-08-01', history_months: 4, model: null, model_label: 'Não selecionado', forecast_months: [], forecast_values: [],
  forecast_next_month: null, forecast_total_3m: null, trend: 'indeterminada' as const, trend_change_ratio: null, backtest_wape: null,
  forecast_confidence: 'baixa', status: 'insufficient_data' as const, limitation: 'São necessários pelo menos 6 meses de histórico para estimar demanda.',
};

export const forecasts: ForecastRecommendationSummary[] = [
  { sku: SKU_OK, product: `Produto ${SKU_OK}`, family: 'Família A', priority: 1, attention_score: 29, confidence: 'média', confidence_reason: 'Motivo.', forecast: forecastOk,
    operational_recommendation: { action: 'produzir', action_label: 'Produzir', suggested_quantity: 200, minimum_lot: 100, capacity_status: 'family_context_available', confidence: 'alta', confidence_reason: 'Motivo.', requires_human_review: true } },
  { sku: SKU_SHORT, product: `Produto ${SKU_SHORT}`, family: 'Família B', priority: 2, attention_score: 28, confidence: 'baixa', confidence_reason: 'Motivo.', forecast: forecastShort,
    operational_recommendation: { action: 'investigar_dados', action_label: 'Investigar dados', suggested_quantity: null, minimum_lot: 100, capacity_status: 'not_evaluated', confidence: 'baixa', confidence_reason: 'Histórico insuficiente.', requires_human_review: true } },
];

function indicator(sku: string) {
  return {
    SKU: sku, Produto: `Produto ${sku}`, family: 'Família A', current_stock: 50, coverage_days_calculated: 5, lead_time_days: 20, minimum_lot: 100,
    average_sales_per_day: 10, safety_stock_days: 10, backlog_order_quantity: 400, production_order_quantity: 0, projected_stock_quantity: -350,
    operational_gap_quantity: 350, first_promised_date: '2026-09-15', first_production_completion: null, sell_in_quantity: 300, sell_out_quantity: null,
    sell_in_minus_sell_out_quantity: null, sell_out_partner_count: 0, has_sell_out: false, forecast_quantity: null, analysis_scope: 'SKU global' as const,
    missing_data: ['sell_out_quantity', 'first_production_completion'],
  };
}

const recommendationBase = {
  horizon: 'próximo mês', minimum_lot: 100, backlog_quantity: 400, current_stock: 50, open_production_quantity: 0,
  assumptions: ['Premissa sintética.'], limitations: ['A recomendação não cria nem libera ordem de produção.'], requires_human_review: true,
};

const observedMonths = ['2025-09-01', '2025-10-01', '2025-11-01', '2025-12-01', '2026-01-01', '2026-02-01', '2026-03-01', '2026-04-01', '2026-05-01', '2026-06-01', '2026-07-01', '2026-08-01'];
export const revenueOk: RevenueItem = {
  sku: SKU_OK, product: `Produto ${SKU_OK}`, family: 'Família A', status: 'ok', reason: null, unit_price: 12.5, price_source: 'Precos_Produtos', price_conflict: false,
  model_label: 'Média móvel de 3 meses', forecast_confidence: 'alta', forecast_months: ['2026-09-01', '2026-10-01', '2026-11-01'], forecast_units: [100, 110, 120],
  revenue_values: [1250, 1375, 1500], revenue_next_month: 1250, revenue_total_3m: 4125,
  commercial_reference: { months: ['2026-10-01', '2026-11-01'], commercial_units: [100, 100], model_revenue: 2875, commercial_revenue: 2500, difference_ratio: 0.15, origins: ['Consenso S&OP'], note: 'Comparação, não erro: o consenso comercial não substitui a previsão estatística.' },
  calculation: { formula: 'Faturamento estimado = previsão em unidades × preço unitário vigente', terms: [
    { month: '2026-09-01', units: 100, unit_price: 12.5, revenue: 1250 }, { month: '2026-10-01', units: 110, unit_price: 12.5, revenue: 1375 }, { month: '2026-11-01', units: 120, unit_price: 12.5, revenue: 1500 },
  ] },
  nature: 'estimado', observed_revenue: { months: observedMonths, values: observedMonths.map(() => 1000) },
};
export const revenueShort: RevenueItem = {
  sku: SKU_SHORT, product: `Produto ${SKU_SHORT}`, family: 'Família B', status: 'sem_previsao', reason: 'Sem previsão de unidades; não há como estimar faturamento.',
  unit_price: 20, price_source: 'Precos_Produtos', price_conflict: false, model_label: 'Não selecionado', forecast_confidence: 'baixa', forecast_months: [], forecast_units: [],
  revenue_values: [], revenue_next_month: null, revenue_total_3m: null, commercial_reference: null, calculation: null, nature: 'estimado',
  observed_revenue: { months: observedMonths, values: observedMonths.map(() => null) },
};
const revenueGroup = (label: string, total: number | null, withEstimate: number, size: number) => ({
  label, skus_total: size, skus_with_estimate: withEstimate,
  skus_excluded: withEstimate < size ? [{ sku: SKU_SHORT, status: 'sem_previsao' as const, reason: revenueShort.reason }] : [],
  by_month: total === null ? [] : [{ month: '2026-09-01', revenue: 1250 }, { month: '2026-10-01', revenue: 1375 }, { month: '2026-11-01', revenue: 1500 }], revenue_total_3m: total,
  confidence_distribution: { alta: withEstimate, média: 0, baixa: 0 }, backtest_wape: total === null ? null : 0.08,
  observed_revenue: { months: observedMonths, values: observedMonths.map(() => 1000) }, observed_last_3m_same_skus: total === null ? null : 3000, change_vs_last_3m: total === null ? null : 0.375,
  commercial_reference: total === null ? null : { months: ['2026-10-01', '2026-11-01'], skus_compared: 1, model_revenue: 2875, commercial_revenue: 2500, difference_ratio: 0.15 },
});
export const revenueForecast: RevenueForecast = {
  reference_month: '2026-08-01', nature: 'estimado', formula: 'Faturamento estimado = previsão em unidades × preço unitário vigente',
  items: [revenueOk, revenueShort], families: [revenueGroup('Família A', 4125, 1, 1), revenueGroup('Família B', null, 0, 1)], total: revenueGroup('Total da empresa', 4125, 1, 2),
  field_nature: { revenue_values: { nature: 'estimado', origin: 'calculado' } }, limitations: ['Estimativa, não faturamento realizado.', 'O preço é mantido constante.'],
};

export const skuDetailOk: SkuDetail = {
  indicator: indicator(SKU_OK),
  issues: [{ sku: SKU_OK, product: `Produto ${SKU_OK}`, family: 'Família A', code: 'RUP_LEAD_TIME', description: 'Cobertura de estoque abaixo do lead time.', severity: 'alta', values_used: { coverage_days: 5 }, data_origin: ['Estoque_Atual.Estoque atual'] }],
  priority: [priorities[0]],
  score_contributions: [{ code: 'RUP_LEAD_TIME', weight: 8, description: 'Cobertura abaixo do lead time.' }],
  forecast: forecastOk,
  revenue_forecast: revenueOk,
  operational_recommendation: { ...recommendationBase, action: 'produzir', action_label: 'Produzir', suggested_quantity: 500, raw_quantity: 450, forecast_next_month: 100, safety_stock_quantity: 100, capacity_status: 'family_context_available', confidence: 'baixa', confidence_reason: 'Sell-out não observado.', rationale: ['Demanda a cobrir sintética.'], calculation: { demand_to_cover: 400, safety_stock_quantity: 100, current_stock: 50, open_production_quantity: 0 } },
  limitation: 'A base não vincula pedidos a OPs por semana.',
};

export const skuDetailShort: SkuDetail = {
  ...skuDetailOk,
  indicator: indicator(SKU_SHORT),
  priority: [priorities[1]],
  forecast: forecastShort,
  revenue_forecast: revenueShort,
  operational_recommendation: { ...recommendationBase, action: 'investigar_dados', action_label: 'Investigar dados', suggested_quantity: null, raw_quantity: null, forecast_next_month: null, safety_stock_quantity: null, capacity_status: 'not_evaluated', confidence: 'baixa', confidence_reason: 'Histórico insuficiente para produzir uma previsão quantitativa.', rationale: ['Investigar e completar o histórico antes de sugerir produção.'], calculation: {} },
};

const metadata = { reference_month: '2026-08', limitation: 'Recomendação comercial demonstrativa.', thresholds: { recent_months: 3 }, field_nature: { estimated_stock: { nature: 'estimado na fonte', origin: 'Sell_Out' } } };

export const partnerSummary: PartnerSummary = {
  code: PARTNER, name: 'Parceiro sintético', type: 'Key account', region: 'Sudeste', channel: 'Varejo', state: 'SP', city: 'Cidade', observed_skus: 1,
  linked_skus: 2, total_catalog_skus: 4, coverage: 0.25, latest_sell_out_month: '2026-08', backlog_quantity: 120,
  action_counts: { avaliar_reposicao: 1, monitorar_estoque: 0, investigar_divergencia: 0, solicitar_atualizacao: 0, dados_insuficientes: 1 },
  quality_counts: { sufficient: 1, stale: 0, insufficient: 1 },
};

export const commercialRow: CommercialRow = {
  partner: PARTNER, partner_name: 'Parceiro sintético', sku: SKU_OK, product: `Produto ${SKU_OK}`, region: 'Sudeste', channel: 'Varejo', reference_month: '2026-08',
  window_months: ['2026-06', '2026-07', '2026-08'], sell_in_recent: 90, sell_out_recent: 0, sell_in_months: ['2026-06', '2026-07', '2026-08'],
  sell_out_months: ['2026-06', '2026-07', '2026-08'], comparable_months: ['2026-06', '2026-07', '2026-08'], comparable_sell_in: 90, comparable_sell_out: 0,
  comparable_difference: 90, divergence_ratio: null, estimated_stock: null, stock_month: null, data_nature: 'Real', average_monthly_sell_out: 0,
  coverage_days: null, age_months: 0, missing_months: [], data_quality: 'insufficient', backlog_quantity: 120, backlog_order_count: 1,
  orders: [{ order: 'PED-T1', quantity: 120, promised_date: '2026-10-01', status: 'Confirmado' }],
  signals: [{ code: 'INSUFFICIENT_PARTNER_DATA', label: 'Dados insuficientes para recomendar' }], action: 'dados_insuficientes',
  action_label: 'Sem recomendação por dados insuficientes', requires_human_review: true, recommendation_reason: 'Sem estoque estimado.',
  periods: [{ month: '2026-08', sell_in_quantity: 30, sell_out_quantity: 0, estimated_stock: null, data_nature: 'Real' }],
};

export const partnersPage: CommercialPage<PartnerSummary> = { ...metadata, items: [partnerSummary], total: 1, offset: 0, limit: 200 };
export const partnerRows: CommercialPage<CommercialRow> = { ...metadata, items: [commercialRow], total: 1, offset: 0, limit: 50 };
export const partnerDetail: PartnerDetail = { ...metadata, partner: partnerSummary, decisions: { attribution_available: false, items: null, reason: 'O feedback não registra o código do parceiro.' } };

export const validationSummary: ValidationSummary = {
  generated_at: '2026-10-05T12:00:00+00:00',
  source: { sha256: 'abc123abc123abc123', sales_reference_month: '2026-08-01' },
  process_comparison: [{ id: 'analysis_time', label: 'Tempo de análise do PCP', informed: { value: 22, unit: 'horas/semana', nature: 'informado', source: 'Fonte sintética' }, recalculated: { value: null, unit: 'horas/semana', nature: 'recalculado', comparable: false, reason: 'Amostra insuficiente.' }, target: { value: 8, unit: 'horas/semana', nature: 'meta' } }],
  analysis_time: { feedback_count: 0, records_with_minutes: 0, total_minutes: null, average_minutes_per_decision: null, median_minutes_per_decision: null, minimum_sample: 20, sample_status: 'insuficiente', comparison_allowed: false, note: 'Amostra insuficiente.' },
  forecast_evaluation: {
    holdout_months: 3, total_skus: 2, eligible_skus: 1, insufficient_skus: 1, insufficient_sku_list: [SKU_SHORT], zero_demand_holdout_skus: 0,
    baseline: { model: 'naive_last', label: 'Baseline', description: 'Último mês.' },
    models: [{ model: 'selected', label: 'Selecionado', role: 'selecionado', selected_skus: 1, evaluated_skus: 1, wape_defined_skus: 1, median_wape: 0.1, weighted_wape: 0.1 }],
    beat_baseline_skus: 1, did_not_beat_baseline_skus: 0, not_comparable_skus: 0, items: [], limitations: ['Holdout otimista.'],
  },
  frozen_cases: { frozen_at: '2026-10-05', frozen_source_sha256: 'abc', source_matches_frozen: true, source_note: null, policy: 'Política.', total: 0, passed: 0, failed: 0, not_found: 0, synthetic: 0, items: [] },
  safe_behavior: [{ id: 'a', label: 'Verificação', status: 'aprovado', method: 'executado', evidence: 'ok' }],
  known_failures: [], known_limitations: ['Limitação.'], adjustments: [], requires_human_review: true,
};

export const runComparison: RunComparison = {
  base: { ...runs[1], comparison_schema_version: null }, target: { ...runs[0], comparison_schema_version: 1 },
  context: { source_changed: false, weights_changes: [], thresholds_changes: [], commercial_thresholds: { available: false, reason: 'Não preservado.' } },
  comparable: true,
  ranking: { available: true, entered: [], exited: [], changed: [], unchanged_count: 3, summary: { entered: 0, exited: 0, changed: 0, unchanged: 3, moved_up: 0, moved_down: 0, score_changed: 0, confidence_changed: 0, with_new_signals: 0, unexplained: 0 } },
  forecasts: { available: false, reason: 'Execução #1 foi registrada antes da comparação ampliada.' },
  b2b_coverage: { available: false, reason: 'Execução #1 foi registrada antes da comparação ampliada.' },
  notes: [], limitations: ['Limitação.'],
};

export const system: SystemInfo = {
  environment: 'development', demo_mode: false, write_enabled: true, notice: null,
  text_limits: { note: 2000, user_name: 80, owner: 80, case_action: 200, analysis_minutes: 1440 },
};
