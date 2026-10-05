export interface RunMeta {
  id: number;
  created_at: string;
  source_hash: string;
  prioritized_skus: number;
  comparison_schema_version: number | null;
}

export interface KeyChange {
  key: string;
  base: unknown;
  target: unknown;
}

export interface RankingEntry {
  sku: string;
  product: string | null;
  family: string | null;
  priority: number;
  attention_score: number;
  confidence: string;
  signals: string[];
}

export interface ScoreBreakdown {
  code: string;
  change: 'adicionado' | 'removido' | 'peso alterado';
  base_weight: number | null;
  target_weight: number | null;
  delta: number | null;
}

export interface RankingChange {
  sku: string;
  product: string | null;
  family: string | null;
  base: RankingEntry;
  target: RankingEntry;
  position_delta: number;
  score_delta: number | null;
  confidence_changed: boolean;
  signals_added: string[];
  signals_removed: string[];
  score_breakdown: ScoreBreakdown[];
  score_delta_explained: boolean;
  explanation: string[];
  evidence_changes: Array<{ code: string; field: string; base: unknown; target: unknown }>;
}

export interface Unavailable {
  available: false;
  reason: string;
}

export interface RankingComparison {
  available: true;
  entered: RankingEntry[];
  exited: RankingEntry[];
  changed: RankingChange[];
  unchanged_count: number;
  summary: Record<'entered' | 'exited' | 'changed' | 'unchanged' | 'moved_up' | 'moved_down' | 'score_changed' | 'confidence_changed' | 'with_new_signals' | 'unexplained', number>;
}

export interface FieldChange {
  field: string;
  label: string;
  base: unknown;
  target: unknown;
  delta: number | null;
}

export interface ForecastComparison {
  available: true;
  items: Array<{ sku: string; changes: FieldChange[] }>;
  only_in_base: string[];
  only_in_target: string[];
  summary: Record<'compared_skus' | 'changed_skus' | 'action_changes' | 'quantity_changes' | 'model_changes' | 'forecast_changes', number>;
}

export interface B2BComparison {
  available: true;
  base_reference_month: string | null;
  target_reference_month: string | null;
  items: Array<{ partner: string; name: string | null; changes: FieldChange[] }>;
  entered_partners: string[];
  exited_partners: string[];
  summary: Record<'compared_partners' | 'changed_partners', number>;
}

export interface RunComparison {
  base: RunMeta;
  target: RunMeta;
  context: {
    source_changed: boolean;
    weights_changes: KeyChange[];
    thresholds_changes: KeyChange[];
    commercial_thresholds: { available: true; changes: KeyChange[] } | Unavailable;
  };
  comparable: boolean;
  ranking: RankingComparison | Unavailable;
  forecasts: ForecastComparison | Unavailable;
  b2b_coverage: B2BComparison | Unavailable;
  notes: string[];
  limitations: string[];
}
