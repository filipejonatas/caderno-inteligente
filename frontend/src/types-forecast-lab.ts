export interface LabModel {
  model: string;
  label: string;
  description: string;
  complexity: number;
  min_history_months: number;
  official_selected_skus: number;
  rolling_selected_skus: number;
  evaluated_skus: number;
  median_wape: number | null;
}

export interface LabChangedSku {
  sku: string;
  official_model: string | null;
  official_model_label: string | null;
  rolling_model: string;
  rolling_model_label: string;
  rolling_wape: number | null;
}

export interface LabProcedure {
  weighted_wape: number | null;
  weighted_bias: number | null;
  skus_beating_baseline: number;
}

export interface LabCriteria {
  relative_wape_gain: number | null;
  min_relative_wape_gain: number;
  wape_criterion_met: boolean;
  bias_worsening_pp: number | null;
  max_bias_worsening_pp: number;
  bias_criterion_met: boolean;
  skus_beating_baseline_rolling: number;
  skus_beating_baseline_v1: number;
  baseline_criterion_met: boolean;
  all_met: boolean;
}

export interface SensitivityCell {
  outer_windows: number;
  minimum_windows: number;
  is_default: boolean;
  outer_train_lengths: number[];
  skus: number;
  v1_wape: number | null;
  rolling_wape: number | null;
  baseline_wape: number | null;
  v1_bias: number | null;
  rolling_bias: number | null;
  rolling_better_skus: number;
  equal_skus: number;
  rolling_worse_skus: number;
  relative_wape_gain: number | null;
  wape_criterion_met: boolean;
  bias_worsening_pp: number | null;
  bias_criterion_met: boolean;
  skus_beating_baseline_rolling: number;
  skus_beating_baseline_v1: number;
  baseline_criterion_met: boolean;
  all_met: boolean;
}

export interface SensitivitySummary {
  cells: number;
  cells_all_met: number;
  robust: boolean;
  default_all_met: boolean | null;
  min_relative_wape_gain: number | null;
  max_relative_wape_gain: number | null;
}

export interface ForecastLab {
  generated_at: string;
  source: { sha256: string };
  engine: string;
  official_engine_label: string;
  promotion_status: string;
  promotion_note: string;
  baseline: { model: string; label: string };
  selection: { skus: number; skipped_skus: number; changed_skus: number; models: LabModel[]; changed: LabChangedSku[] };
  nested: {
    outer_windows: number;
    outer_train_lengths: number[] | null;
    skus: number;
    aggregate: { v1: LabProcedure; rolling: LabProcedure; baseline: LabProcedure };
    rolling_vs_v1: { rolling_better: number; equal: number; rolling_worse: number };
    criteria: LabCriteria;
  };
  sensitivity: { cells: SensitivityCell[]; summary: SensitivitySummary };
  limitations: string[];
  field_nature: Record<string, { nature: string; origin: string }>;
  requires_human_review: boolean;
}
