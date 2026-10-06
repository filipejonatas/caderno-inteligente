// Render-only tests for the run comparison with a synthetic fixture (never application data); no new dependency.
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
const mediaQueryUrl = await compile('../src/hooks/useMediaQuery.ts');
const componentsUrl = await compile('../src/components.tsx', { './pages/shared': sharedUrl, './hooks/useMediaQuery': mediaQueryUrl });
const stub = dataUrl('export const api = {}; export function useApiResource() { return {}; }');
const { RunComparisonContent } = await import(await compile('../src/components/RunComparisonView.tsx', {
  '../api': stub, '../hooks/useApiResource': stub, '../components': componentsUrl, '../pages/shared': sharedUrl,
}));

const originalError = console.error;
console.error = (...args) => { if (!String(args[0]).includes('useLayoutEffect does nothing on the server')) originalError(...args); };

const run = (id, version) => ({ id, created_at: `2026-10-0${id}T12:00:00+00:00`, source_hash: `hash-${id}-0123456789abcdef`, prioritized_skus: 2, comparison_schema_version: version });
const entry = (sku, priority, score, confidence, signals) => ({ sku, product: `Produto ${sku}`, family: 'F', priority, attention_score: score, confidence, signals });
const fixture = {
  base: run(1, null), target: run(2, 1),
  context: { source_changed: true, weights_changes: [{ key: 'LOW_SELLOUT_VISIBILITY', base: 2, target: 12 }], thresholds_changes: [], commercial_thresholds: { available: false, reason: 'Limiares comerciais não preservados.' } },
  comparable: true,
  ranking: {
    available: true,
    entered: [entry('NEW / 1', 1, 20, 'baixa', ['LOW_SELLOUT_VISIBILITY'])],
    exited: [],
    changed: [{
      sku: 'TEST-1', product: 'Produto TEST-1', family: 'F', base: entry('TEST-1', 1, 10, 'média', ['RUP_LEAD_TIME']), target: entry('TEST-1', 3, 22, 'baixa', ['RUP_LEAD_TIME', 'LOW_SELLOUT_VISIBILITY']),
      position_delta: -2, score_delta: 12, confidence_changed: true, signals_added: ['LOW_SELLOUT_VISIBILITY'], signals_removed: [],
      score_breakdown: [{ code: 'LOW_SELLOUT_VISIBILITY', change: 'adicionado', base_weight: null, target_weight: 12, delta: 12 }],
      score_delta_explained: true, explanation: ['Sinal novo LOW_SELLOUT_VISIBILITY (+12).'],
      evidence_changes: [{ code: 'RUP_LEAD_TIME', field: 'coverage_days', base: 5, target: 3 }],
    }],
    unchanged_count: 0,
    summary: { entered: 1, exited: 0, changed: 1, unchanged: 0, moved_up: 0, moved_down: 1, score_changed: 1, confidence_changed: 1, with_new_signals: 1, unexplained: 0 },
  },
  forecasts: { available: false, reason: 'Execução #1 foi registrada antes da comparação ampliada e não preserva previsão e recomendação.' },
  b2b_coverage: { available: true, base_reference_month: '2026-07', target_reference_month: '2026-08', items: [{ partner: 'KA 01', name: 'Parceiro', changes: [{ field: 'partner.coverage', label: 'Cobertura observada', base: 0.5, target: null, delta: null }] }], entered_partners: [], exited_partners: [], summary: { compared_partners: 1, changed_partners: 1 } },
  notes: [], limitations: ['Limitação de teste.'],
};
const render = data => renderToStaticMarkup(React.createElement(MemoryRouter, null, React.createElement(RunComparisonContent, { data })));

test('comparison explains why a priority changed and preserves audit context', () => {
  const html = render(fixture);
  for (const text of ['Execução #1', 'Execução #2', 'hash-1-012345678', 'Planilha diferente', 'Pesos alterados', 'LOW_SELLOUT_VISIBILITY', 'Por que mudou', 'Sinal novo LOW_SELLOUT_VISIBILITY (+12).', 'desceu 2', 'Decomposição do score', 'coverage_days', 'Entraram no ranking (1)']) assert.ok(html.includes(text), text);
  assert.ok(html.includes('href="/skus/NEW%20%2F%201"'));
});

test('incompatible sections are refused with the reason and absent values stay absent', () => {
  const html = render(fixture);
  assert.ok(html.includes('Comparação não disponível nesta seção'));
  assert.ok(html.includes('não preserva previsão e recomendação'));
  assert.ok(html.includes('execução antiga, só com ranking'));
  assert.ok(html.includes('não disponível'));
  assert.ok(html.includes('href="/parceiros/KA%2001"'));
});

test('fully incompatible comparison shows a global warning', () => {
  const html = render({ ...fixture, comparable: false, ranking: { available: false, reason: 'Ranking sem campos.' } });
  assert.ok(html.includes('Execuções sem dados compatíveis'));
  assert.ok(html.includes('Ranking sem campos.'));
});
