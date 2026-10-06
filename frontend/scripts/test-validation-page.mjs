// Render-only tests for /validacao with a synthetic fixture (never application data); no new dependency.
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { test } from 'node:test';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import ts from 'typescript';

const dataUrl = code => `data:text/javascript;base64,${Buffer.from(code).toString('base64')}`;
async function compile(file, replacements = {}) {
  const text = await readFile(new URL(file, import.meta.url), 'utf8');
  let code = ts.transpileModule(text, { compilerOptions: { target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.ESNext, jsx: ts.JsxEmit.ReactJSX } }).outputText;
  for (const name of ['react', 'react/jsx-runtime', 'react-router-dom']) {
    code = code.replaceAll(`"${name}"`, JSON.stringify(import.meta.resolve(name))).replaceAll(`'${name}'`, JSON.stringify(import.meta.resolve(name)));
  }
  for (const [name, url] of Object.entries(replacements)) code = code.replaceAll(`'${name}'`, JSON.stringify(url)).replaceAll(`"${name}"`, JSON.stringify(url));
  return dataUrl(code);
}
const sharedUrl = await compile('../src/pages/shared.ts');
const componentsUrl = await compile('../src/components.tsx', { './pages/shared': sharedUrl });
const exportUrl = await compile('../src/validation-export.ts');
const stub = dataUrl('export const api = {}; export function useApiResource() { return {}; } export function usePageLoadStatus() {}');
const { ValidationContent } = await import(await compile('../src/pages/ValidationPage.tsx', {
  '../api': stub, '../hooks/useApiResource': stub, '../hooks/usePageLoadStatus': stub,
  '../components': componentsUrl, './shared': sharedUrl, '../validation-export': exportUrl,
}));
const { validationCsv } = await import(exportUrl);

const originalError = console.error;
console.error = (...args) => { if (!String(args[0]).includes('useLayoutEffect does nothing on the server')) originalError(...args); };

const fixture = {
  generated_at: '2026-10-05T12:00:00+00:00',
  source: { sha256: 'abc123abc123abc123', sales_reference_month: '2026-08-01' },
  process_comparison: [
    { id: 'analysis_time', label: 'Tempo de análise do PCP', informed: { value: 22, unit: 'horas/semana', nature: 'informado', source: 'Fonte de teste' }, recalculated: { value: null, unit: 'horas/semana', nature: 'recalculado', comparable: false, reason: 'Amostra insuficiente; nenhum ganho é afirmado.' }, target: { value: 8, unit: 'horas/semana', nature: 'meta' } },
    { id: 'on_time_orders', label: 'Pedidos no prazo', informed: { value: 0.89, unit: 'percentual', nature: 'informado', source: 'Fonte de teste' }, recalculated: { value: null, unit: 'percentual', nature: 'recalculado', comparable: false, reason: 'Sem histórico de entregas.' }, target: { value: 0.96, unit: 'percentual', nature: 'meta' } },
  ],
  analysis_time: { feedback_count: 1, records_with_minutes: 0, total_minutes: null, average_minutes_per_decision: null, median_minutes_per_decision: null, minimum_sample: 20, sample_status: 'insuficiente', comparison_allowed: false, note: 'Somente 0 registro(s).' },
  forecast_evaluation: {
    holdout_months: 3, total_skus: 2, eligible_skus: 2, insufficient_skus: 0, insufficient_sku_list: [], zero_demand_holdout_skus: 0,
    baseline: { model: 'naive_last', label: 'Baseline de teste', description: 'Descrição da baseline.' },
    models: [
      { model: 'selected', label: 'Modelo selecionado por SKU', role: 'selecionado', selected_skus: 2, evaluated_skus: 2, wape_defined_skus: 2, median_wape: 0.1, weighted_wape: 0.12 },
      { model: 'naive_last', label: 'Baseline de teste', role: 'baseline', selected_skus: 0, evaluated_skus: 2, wape_defined_skus: 2, median_wape: 0.11, weighted_wape: 0.1 },
    ],
    beat_baseline_skus: 1, did_not_beat_baseline_skus: 1, not_comparable_skus: 0,
    items: [{ sku: 'TEST / 1', selected_model: 'moving_average_3', selected_model_label: 'Média móvel', selected_wape: 0.2, baseline_wape: 0.1, candidate_wapes: {}, outcome: 'nao_superou', holdout_actual_total: 30 }],
    limitations: ['Holdout otimista.'],
  },
  frozen_cases: {
    frozen_at: '2026-10-05', frozen_source_sha256: 'outro', source_matches_frozen: false, source_note: 'A planilha mudou desde o congelamento.', policy: 'Política de teste.',
    total: 2, passed: 1, failed: 1, not_found: 0, synthetic: 1,
    items: [
      { id: 'VC-T1', title: 'Caso aprovado', kind: 'operational', origin: 'synthetic', origin_reason: 'Sem exemplo na base.', sku: 'SINT', partner: null, limitation: 'Limitação A', input: { current_stock: 50 }, expected: { action: 'produzir' }, obtained: { action: 'produzir' }, checks: [{ field: 'action', expected: 'produzir', obtained: 'produzir', passed: true }], result: 'passou', adjustment: 'Nenhum ajuste.' },
      { id: 'VC-T2', title: 'Caso reprovado', kind: 'commercial', origin: 'base', origin_reason: null, sku: 'TEST / 2', partner: 'KA-T', limitation: 'Limitação B', input: { estimated_stock: null }, expected: { coverage_days: { is_null: true } }, obtained: { coverage_days: 0 }, checks: [{ field: 'coverage_days', expected: 'nulo (não disponível)', obtained: 0, passed: false }], result: 'falhou', adjustment: 'Nenhum ajuste.' },
    ],
  },
  safe_behavior: [
    { id: 'a', label: 'Verificação aprovada', status: 'aprovado', method: 'executado', evidence: 'ok' },
    { id: 'b', label: 'Verificação por teste', status: 'coberto_por_teste', method: 'teste automatizado', evidence: 'arquivo' },
  ],
  known_failures: [{ area: 'previsão', description: 'Não superou a baseline em 1 de 2.' }],
  known_limitations: ['Limitação permanente de teste.'],
  adjustments: [{ date: '2026-10-01', change: 'Ajuste de teste; com aspas "x"', reason: 'Motivo', evidence: 'docs/x.md', changed_weights_or_models: false }],
  requires_human_review: true,
};
const render = () => renderToStaticMarkup(React.createElement(MemoryRouter, null, React.createElement(ValidationContent, { data: fixture, onRetry() {} })));

test('validation page separates informed, recalculated and target values', () => {
  const html = render();
  for (const text of ['Comparação com o processo atual', 'informado', 'recalculado', 'meta', 'Não disponível', 'Sem histórico de entregas.']) assert.ok(html.includes(text), text);
  assert.ok(html.includes('89%') && html.includes('96%'));
});

test('validation page shows failures, synthetic origin, source change and baseline gaps instead of hiding them', () => {
  const html = render();
  for (const text of ['Falhou', 'Passou', 'entrada sintética', 'Base alterada desde o congelamento', 'Não superou a baseline em 1 de 2.', 'Coberto por teste', 'Exportar CSV', 'Imprimir resumo']) assert.ok(html.includes(text), text);
  assert.ok(html.includes('href="/skus/TEST%20%2F%201"'));
  assert.ok(html.includes('obtido: 0'));
});

test('CSV export keeps sections, natures and escapes separators without inventing zero', () => {
  const csv = validationCsv(fixture);
  assert.ok(csv.startsWith('﻿'));
  assert.ok(csv.includes('Processo atual;Tempo de análise do PCP;informado;22;horas/semana;Fonte de teste'));
  assert.ok(csv.includes('Processo atual;Tempo de análise do PCP;recalculado;;horas/semana;'));
  assert.ok(csv.includes('Processo atual;Tempo de análise do PCP;meta;8;horas/semana;'));
  assert.ok(csv.includes('"Ajuste de teste; com aspas ""x"""'));
  assert.ok(csv.includes('VC-T2;Caso reprovado;base;'));
  assert.ok(csv.includes(';falhou;'));
});
