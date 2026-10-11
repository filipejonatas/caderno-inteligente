/** Atualização da base pela tela (upload): GET /api/dataset, prévia, aplicação e versões (contrato C6). */

export type DatasetOrigin = 'original' | 'upload' | 'restore' | 'desconhecida';
/** Motivo do botão desabilitado; `null` quando o envio está liberado. */
export type DatasetUploadDisabledReason = 'planilha' | 'somente_leitura' | 'login' | 'login_indisponivel';
export type DatasetVersionAction = 'upload' | 'restore' | 'original';

/** GET /api/dataset: a base ativa e se este usuário pode enviar uma planilha (o Bearer é opcional). */
export interface DatasetInfo {
  data_source: 'planilha' | 'banco';
  /** `null` com DATA_SOURCE=planilha (sem versão no banco). */
  version: number | null;
  active_version_id: number | null;
  origin: DatasetOrigin;
  /** AAAA-MM-DD: a primeira semana de Capacidade_Semanal (referência "auto") ou a data do config. */
  reference_date: string;
  reference_source: 'auto' | 'config';
  /** AAAA-MM; `null` sem vendas. */
  sales_last_month: string | null;
  content_sha256: string;
  source_sha256: string;
  matches_original: boolean;
  uploaded_by: string | null;
  uploaded_at: string | null;
  filename: string | null;
  upload_enabled: boolean;
  upload_disabled_reason: DatasetUploadDisabledReason | null;
  upload_disabled_message: string | null;
  max_upload_bytes: number;
  accepted_extensions: string[];
  max_versions: number;
  policy: string;
}

/** Problema com endereço (C2). `row`/`cell`/`value` repetem o primeiro exemplo; ausentes ficam `null`. */
export interface DatasetIssueExample {
  row: number | null;
  cell: string | null;
  key: string | null;
  value: string | null;
}

export interface DatasetIssue {
  code: string;
  severity: 'error' | 'warning';
  sheet: string | null;
  column: string | null;
  message: string;
  count: number;
  examples: DatasetIssueExample[];
  /** Quantos iguais além dos exemplos ("mais N iguais"). */
  more: number;
  row: number | null;
  cell: string | null;
  value: string | null;
}

/** Uma linha por aba da base: o que a mescla faria (C4). Aba ausente no envio fica "mantida", com `rows_received: null`. */
export interface DatasetSheetReport {
  sheet: string;
  policy: 'serie_mensal' | 'fotografia' | 'cadastro';
  status: 'mesclada' | 'substituida' | 'mantida';
  header_row: number | null;
  rows_before: number | null;
  rows_received: number | null;
  rows_after: number | null;
  months_added: string[];
  months_replaced: string[];
  keys_added: number;
  keys_removed: number;
  keys_added_examples: string[];
  keys_removed_examples: string[];
}

/** Resumo do motor para comparar antes × depois na prévia. */
export interface EngineSummary {
  reference_date: string | null;
  sales_last_month: string | null;
  queue_size: number;
  top5: Array<{ sku: string; product: string; urgency_label: string | null }>;
  shortfall_skus: number;
  forecast_first_month: string | null;
}

export interface DatasetPreview {
  file: { filename: string; size_bytes: number; sha256: string; extension: string; has_macro: boolean; example: boolean };
  /** Versão da base vista na prévia; vai em X-Expected-Version na aplicação. */
  expected_version: number;
  can_apply: boolean;
  policy: string;
  sheets: DatasetSheetReport[];
  ignored_sheets: string[];
  errors: DatasetIssue[];
  warnings: DatasetIssue[];
  /** `after`/`sales_last_month_after` ficam `null` quando a planilha tem erro que impede calcular. */
  reference: { before: string | null; after: string | null; advanced: boolean; sales_last_month_before: string | null; sales_last_month_after: string | null };
  /** D10: SKUs cadastrados pela tela que o envio sobrescreve. */
  registry_overrides: { count: number; skus: string[] };
  /** `after: null` + `error` quando o motor não foi recalculado (planilha com erro). */
  /** `before: null` quando o motor não conseguiu resumir a base atual. */
  engine: { before: EngineSummary | null; after: EngineSummary | null; error: string | null };
  requires_human_review: true;
  limitations: string[];
}

/** Resposta de apply, restaurar versão e restaurar original. */
export interface DatasetApplyResult {
  version: number;
  version_id: number;
  reference_date: string | null;
  sales_last_month: string | null;
  content_sha256: string;
  pruned_versions: number;
  /** Só em restaurações: a versão de origem (`null` em restore-original). */
  restored_from?: number | null;
  preview: DatasetPreview;
}

export interface DatasetVersionRow {
  id: number;
  created_at: string;
  user_email: string;
  action: DatasetVersionAction;
  filename: string | null;
  file_sha256: string | null;
  size_bytes: number | null;
  content_sha256: string;
  reference_date: string | null;
  sales_last_month: string | null;
  restored_from: number | null;
  active: boolean;
}

/** GET /api/dataset/versions; com DATA_SOURCE=planilha, `items: []`. */
export interface DatasetVersions {
  data_source: 'planilha' | 'banco';
  active_version_id: number | null;
  max_versions: number;
  items: DatasetVersionRow[];
}

/** Prévia e aplicação resolvem tanto no 200 quanto no 422 com `preview` (erro de dado); `detail` vem só no 422. */
export interface DatasetPreviewOutcome {
  status: number;
  preview: DatasetPreview;
  detail: string | null;
}

export interface DatasetApplyOutcome extends DatasetPreviewOutcome {
  /** `null` no 422: nada foi aplicado. */
  result: DatasetApplyResult | null;
}
