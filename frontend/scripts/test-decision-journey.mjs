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
const sharedUrl = await compile('../src/pages/shared.ts');
const componentsUrl = await compile('../src/components.tsx', { './pages/shared': sharedUrl });
const { Topbar, RuleLine, Alert, Tooltip } = await import(componentsUrl);
// A faixa de eventos busca a API sozinha (coberta pelo Vitest); aqui só se renderiza o conteúdo próprio da página.
const eventAlertsStub = dataUrl('export const UpcomingEvents = () => null;');
const { default: OverviewPage } = await import(await compile('../src/pages/OverviewPage.tsx', { '../components': componentsUrl, './shared': sharedUrl, '../components/EventAlerts': eventAlertsStub }));
const render = element => renderToStaticMarkup(element);

// Suppress React Router's expected SSR-only useLayoutEffect warning; preserve other warnings.
const originalError = console.error;
console.error = (...args) => { if (!String(args[0]).includes('useLayoutEffect does nothing on the server')) originalError(...args); };
const fixture = {
  overview: { prioritized: 1, total_skus: 1, rupture_sku_count: 1, below_lead_time_count: 1, below_safety_stock_count: 0, order_without_production: 0, low_confidence: 0, decision_count: 0, partner_data_influenced_decision_count: 0, risk_distribution: { RUP_LEAD_TIME: 1 } },
  priorities: [{ sku: 'TEST / SKU', product: 'Produto de teste', family: 'Família de teste', priority: 7, attention_score: 8, confidence: 'média', reasons: [{ code: 'RUP_LEAD_TIME', severity: 'alta', description: 'Sinal de teste' }] }],
  quality: { sell_out_coverage: { coverage: 0.5, observed_pairs: 1, possible_pairs: 2 } },
  config: { weights: { RUP_LEAD_TIME: 8 } },
};
test('overview renders the three blocks, preserves returned priority and links safely', () => {
  const html = render(React.createElement(MemoryRouter, null, React.createElement(OverviewPage, { data: fixture, onSelect() {} })));
  for (const title of ['O que olhar primeiro', 'Fila de atenção (1 de 1)']) assert.ok(html.includes(title));
  assert.ok(html.includes('posição 7'));
  assert.ok(!html.includes('href="/previsoes?busca='), 'o cartão tem uma única ação: abrir as evidências do SKU');
  assert.ok(html.includes('href="/prioridades"'));
  assert.ok(!html.includes('Detalhes: qualidade da evidência'), 'a seção de detalhes foi removida da tela de decisão');
});
test('empty overview does not invent a priority or action quantity', () => {
  const html = render(React.createElement(MemoryRouter, null, React.createElement(OverviewPage, { data: { ...fixture, priorities: [] }, onSelect() {} })));
  assert.ok(html.includes('Nenhum SKU na fila de atenção'));
  assert.ok(!html.includes('Abrir evidências de TEST'));
  assert.ok(html.includes('href="/previsoes"'));
});
test('the single rule line says once that suggestions need human review and are not production orders', () => {
  const html = render(React.createElement(MemoryRouter, null, React.createElement(RuleLine)));
  assert.ok(html.includes('toda sugestão exige revisão humana'));
  assert.ok(html.includes('não é ordem de produção'));
});
test('header shows successful load time and never invents a timestamp', () => {
  const props = { title: 'Teste', onMenu() {}, onRefresh() {}, refreshing: false };
  const render = element => renderToStaticMarkup(React.createElement(MemoryRouter, null, element));
  const empty = render(React.createElement(Topbar, props));
  assert.ok(empty.includes('Ainda sem carga concluída'));
  const loaded = render(React.createElement(Topbar, { ...props, loadedAt: Date.UTC(2026, 9, 5, 20, 48) }));
  assert.ok(loaded.includes('Atualizado às 17:48'));
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

// O selo de rótulo é coberto pelo Vitest; aqui só se renderiza o conteúdo próprio da matriz.
const challengeBadgeStub = dataUrl('export const ChallengeBadge = () => null;');
const { CommercialMatrix } = await import(await compile('../src/components/CommercialMatrix.tsx', { '../components': componentsUrl, '../pages/shared': sharedUrl, './ChallengeAction': challengeBadgeStub }));
test('commercial view keeps null separate from observed zero and names its real key', () => {
  const row = {
    partner: 'Loja própria', partner_name: 'Teste comercial', sku: 'TEST / SKU', product: 'Teste', region: 'Sul', channel: 'Loja',
    sell_in_recent: null, sell_out_recent: 0, comparable_difference: null, sell_in_months: [], sell_out_months: ['2026-08'], comparable_months: [],
    estimated_stock: null, stock_month: null, coverage_days: null, backlog_quantity: 10, backlog_order_count: 1,
    data_quality: 'insufficient', action_label: 'Sem recomendação por dados insuficientes', age_months: 0, missing_months: [],
    data_nature: null, comparable_sell_in: null, comparable_sell_out: null, average_monthly_sell_out: 0, signals: [], orders: [],
    recommendation_reason: 'Teste isolado', periods: [{ month: '2026-08', sell_in_quantity: null, sell_out_quantity: 0, estimated_stock: null, data_nature: null }],
  };
  const response = { items: [row], total: 1, reference_month: '2026-08', limitation: 'Estoque do parceiro não é estoque do CD.', field_nature: {}, thresholds: {} };
  const html = render(React.createElement(MemoryRouter, null, React.createElement(CommercialMatrix, { response })));
  assert.ok(html.includes('Estoque estimado'), 'o estoque do parceiro continua rotulado como estimado');
  assert.ok(!html.includes('Recomendação comercial, não operacional'), 'o alerta repetido saiu da matriz');
  assert.ok(html.includes('Sem recomendação por dados insuficientes'));
  assert.ok(html.includes('0 un.<small>08/2026'));
  assert.ok(html.includes('Não observado'));
  assert.ok(html.includes('/parceiros/Loja%20pr%C3%B3pria'));
  assert.ok(html.includes('/skus/TEST%20%2F%20SKU'));
});
test('commercial matrix has an explicit empty state without synthesizing links', () => {
  const response = { items: [], total: 0, reference_month: null, limitation: 'Teste', field_nature: {}, thresholds: {} };
  const html = render(React.createElement(MemoryRouter, null, React.createElement(CommercialMatrix, { response })));
  assert.ok(html.includes('Nenhum vínculo neste recorte'));
  assert.ok(!html.includes('href="/skus/'));
});
