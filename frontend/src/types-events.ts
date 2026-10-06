export type EvidenceStatus = 'aumento' | 'queda' | 'sem_alteracao' | 'sem_evidencia' | 'sem_historico_direto';

export interface EventEvidence {
  family: string; factor: number | null; factor_raw: number | null; capped: boolean; occurrences: number;
  months_used: string[]; evidence_status: EvidenceStatus; note: string | null;
}

export interface EventAlert {
  event_id: string; event: string; start: string; end: string; impact: string | null; observation: string | null;
  days_to_start: number; decision_date: string | null; in_horizon: boolean; evidence: EventEvidence;
}

export interface EventScenario {
  months: string[]; base_units: number[]; factors: Array<number | null>; events: Array<string | null>; scenario_units: number[];
  base_total_3m: number; scenario_total_3m: number; incremental_units_3m: number;
  unit_price: number | null; scenario_revenue_total_3m: number | null; base_revenue_total_3m: number | null;
  next_month_affected: boolean; nature: 'estimado'; formula: string;
  quantity?: { official: number | null; with_event: number | null; differs: boolean; note: string };
}

export interface SkuEventScenario { applicable: boolean; note: string | null; scenario: EventScenario | null }

export interface EventItem {
  sku: string; family: string | null; model: string | null; lead_time_days: number | null;
  scenario_applicable: boolean; scenario_note: string | null; alerts: EventAlert[]; scenario: EventScenario | null;
}

export interface EventRow {
  id: string; name: string; start: string; end: string; impact: string | null; observation: string | null;
  all_families: boolean; families: EventEvidence[]; unknown_families: string[]; has_history: boolean;
  days_to_start: number; in_horizon: boolean; past: boolean; decision_date_earliest: string | null; skus_alerted: number;
}

export interface EventAnalysis {
  reference_month: string; reference_date: string; horizon_end: string; settings: Record<string, unknown>;
  events: EventRow[]; ignored_events: Array<{ event: string; reason: string }>; items: EventItem[];
  family_factors: Array<{ family: string; month: number; month_name: string; factor_raw: number | null; factor: number | null; capped: boolean }>;
  field_nature: Record<string, { nature: string; origin: string }>; limitations: string[];
}
