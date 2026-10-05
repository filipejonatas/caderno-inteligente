// Render-only regression tests with isolated synthetic fixtures (never application data).
// Uses installed React/TypeScript and Node; no new testing dependency.
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
const componentsUrl = await compile('../src/components.tsx');
const sharedUrl = await compile('../src/pages/shared.ts');
const { Topbar, DecisionBoundary, Alert, Tooltip } = await import(componentsUrl);
const { default: OverviewPage } = await import(await compile('../src/pages/OverviewPage.tsx', { '../components': componentsUrl, './shared': sharedUrl }));
const render = element => renderToStaticMarkup(element);

// Suppress React Router's expected SSR-only useLayoutEffect warning; preserve other warnings.
const originalError = console.error;
console.error = (...args) => { if (!String(args[0]).includes('useLayoutEffect does nothing on the server')) originalError(...args); };
const fixture = {
  overview: { prioritized: 1, total_skus: 1, rupture_sku_count: 1, below_lead_time_count: 1, below_safety_stock_count: 0, order_without_production: 0, low_confidence: 0, decision_count: 0, partner_data_influenced_decision_count: 0, risk_distribution: { RUP_LEAD_TIME: 1 } },
  priorities: [{ sku: 'TEST / SKU', product: 'Produto de teste', family: 'Família de teste', priority: 7, attention_score: 8, confidence: 'média', reasons: [{ code: 'RUP_LEAD_TIME', severity: 'alta', description: 'Sinal de teste' }] }],
  quality: { sell_out_coverage: { coverage: 0.5, observed_pairs: 1, possible_pairs: 2 } },
};
test('overview renders the three blocks, preserves returned priority and links safely', () => {
  const html = render(React.createElement(MemoryRouter, null, React.createElement(OverviewPage, { data: fixture, onSelect() {} })));
  for (const title of ['O que exige atenção', 'Ações sugeridas', 'Qualidade da decisão']) assert.ok(html.includes(title));
  assert.ok(html.includes('prioridade #7'));
  assert.ok(html.includes('href="/previsoes?busca=TEST%20%2F%20SKU"'));
  for (const path of ['/prioridades', '/parceiros', '/qualidade', '/decisoes']) assert.ok(html.includes(`href="${path}"`));
  assert.ok(html.includes('Ausência de sell-out nunca é tratada como venda zero'));
});
test('empty overview does not invent a priority or action quantity', () => {
  const html = render(React.createElement(MemoryRouter, null, React.createElement(OverviewPage, { data: { ...fixture, priorities: [] }, onSelect() {} })));
  assert.ok(html.includes('Nenhum SKU na fila de atenção'));
  assert.ok(!html.includes('Abrir evidências de TEST'));
  assert.ok(html.includes('href="/previsoes"'));
});
test('shared explanation distinguishes analysis priority from production action', () => {
  const html = render(React.createElement(DecisionBoundary));
  assert.ok(html.includes('Prioridade de análise não é ordem de produção'));
  assert.ok(html.includes('prioridade alta e estar sem ação necessária de produção'));
  assert.ok(html.includes('revisão humana'));
});
test('header shows successful load time and never invents a timestamp', () => {
  const props = { title: 'Teste', subtitle: 'Contexto', onMenu() {}, onRefresh() {}, refreshing: false };
  const empty = render(React.createElement(Topbar, props));
  assert.ok(empty.includes('Ainda sem carga concluída'));
  const loaded = render(React.createElement(Topbar, { ...props, loadedAt: Date.UTC(2026, 9, 5, 20, 48) }));
  assert.ok(loaded.includes('05/10/2026, 17:48:00'));
  assert.ok(loaded.includes('não indica atualização da planilha'));
  const loading = render(React.createElement(Topbar, { ...props, refreshing: true }));
  assert.ok(loading.includes('disabled=""'));
  const failed = render(React.createElement(Topbar, { ...props, error: 'Erro de teste' }));
  assert.ok(failed.includes('Falha na consulta'));
});
test('alerts and tooltips expose consistent accessibility semantics', () => {
  assert.ok(render(React.createElement(Alert, { title: 'Erro', tone: 'error' }, 'Teste')).includes('role="alert"'));
  const tooltip = render(React.createElement(Tooltip, { label: 'Explicação de teste' }, 'Texto de ajuda'));
  assert.ok(tooltip.includes('aria-describedby='));
  assert.ok(tooltip.includes('role="tooltip"'));
});
