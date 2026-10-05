import type { ValidationSummary } from './types-validation';

// Dependency-free CSV export; `;` separator and BOM so Excel pt-BR opens accents and columns correctly.
const cell = (value: unknown) => {
  const text = value === null || value === undefined ? '' : typeof value === 'object' ? JSON.stringify(value) : String(value);
  return /[";\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
};
const line = (values: unknown[]) => values.map(cell).join(';');

export function validationCsv(summary: ValidationSummary): string {
  const rows: string[] = [];
  rows.push(line(['Seção', 'Item', 'Natureza', 'Valor', 'Unidade', 'Observação']));
  for (const row of summary.process_comparison) {
    rows.push(line(['Processo atual', row.label, 'informado', row.informed.value, row.informed.unit, row.informed.source]));
    rows.push(line(['Processo atual', row.label, 'recalculado', row.recalculated.value, row.recalculated.unit, row.recalculated.reason]));
    if (row.target) rows.push(line(['Processo atual', row.label, 'meta', row.target.value, row.target.unit, '']));
  }
  const time = summary.analysis_time;
  rows.push(line(['Tempo de análise', 'Registros com minutos', 'recalculado', time.records_with_minutes, 'registros', time.note]));
  rows.push(line(['Tempo de análise', 'Minutos registrados', 'recalculado', time.total_minutes, 'minutos', '']));
  const forecast = summary.forecast_evaluation;
  rows.push(line(['Previsão', 'SKUs elegíveis', 'recalculado', forecast.eligible_skus, 'SKUs', `${forecast.insufficient_skus} com dados insuficientes`]));
  rows.push(line(['Previsão', 'Não superou a baseline', 'recalculado', forecast.did_not_beat_baseline_skus, 'SKUs', forecast.baseline.label]));
  for (const model of forecast.models) {
    rows.push(line(['Previsão', model.label, model.role, model.weighted_wape, 'WAPE ponderado', `mediana ${model.median_wape ?? ''}; ${model.wape_defined_skus} SKUs`]));
  }
  rows.push('');
  rows.push(line(['Caso', 'Título', 'Origem', 'Entrada', 'Esperado', 'Obtido', 'Resultado', 'Limitação', 'Ajuste']));
  for (const item of summary.frozen_cases.items) {
    rows.push(line([item.id, item.title, item.origin === 'synthetic' ? 'sintético' : 'base', item.input, item.expected, item.obtained, item.result, item.limitation, item.adjustment]));
  }
  rows.push('');
  rows.push(line(['Comportamento seguro', 'Status', 'Método', 'Evidência']));
  for (const check of summary.safe_behavior) rows.push(line([check.label, check.status, check.method, check.evidence]));
  rows.push('');
  rows.push(line(['Falha conhecida', 'Área']));
  for (const failure of summary.known_failures) rows.push(line([failure.description, failure.area]));
  rows.push('');
  rows.push(line(['Data', 'Ajuste', 'Motivo', 'Evidência', 'Alterou pesos ou modelos']));
  for (const entry of summary.adjustments) rows.push(line([entry.date, entry.change, entry.reason, entry.evidence, entry.changed_weights_or_models ? 'sim' : 'não']));
  return `﻿${rows.join('\r\n')}\r\n`;
}
