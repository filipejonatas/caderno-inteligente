import { screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { overview } from './fixtures';
import { fail, mockApi, renderApp } from './utils';

const section = async (title: string) => (await screen.findByRole('heading', { level: 3, name: title })).closest('section') as HTMLElement;

describe('Início: estoque projetado (fase 2)', () => {
  it('mostra falta e segurança projetadas e a produção planejada, abaixo dos indicadores de ruptura', async () => {
    mockApi();
    renderApp('/');
    const projected = await screen.findByLabelText('Estoque projetado');
    const rupture = screen.getByLabelText('Indicadores de ruptura');
    expect(rupture.compareDocumentPosition(projected) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(screen.getByText(/Estoque projetado até 28\/02\/2027/)).toBeInTheDocument();
    const value = (label: string) => within(projected).getByText(label).nextSibling;
    expect(value('Falta sem novas ordens')).toHaveTextContent('2 SKUs a partir da semana de 21/09');
    expect(value('Falta mesmo com o plano')).toHaveTextContent('1 SKU');
    expect(value('Abaixo da segurança com o plano')).toHaveTextContent('2 SKUs');
    expect(value('Produção planejada agora')).toHaveTextContent(/1\.200 un\.\s*liberar até 12\/10/);
    expect(screen.getByRole('link', { name: 'Ver a produção planejada' })).toHaveAttribute('href', '/fila');
  });

  it('sem falta projetada, não inventa semana', async () => {
    const base = overview.projected_stock!;
    mockApi({ overview: { ...overview, projected_stock: { ...base, without_new_orders: { shortfall_sku_count: 0, below_safety_sku_count: 0, first_shortfall_week: null }, shortfall_skus: [] } } });
    renderApp('/');
    const projected = await screen.findByLabelText('Estoque projetado');
    expect(within(projected).getByText('Falta sem novas ordens').nextSibling).toHaveTextContent(/^0 SKUs$/);
  });

  it('falha só na agregação: avisa e mantém os indicadores de ruptura', async () => {
    mockApi({ overview: { ...overview, projected_stock: null } });
    renderApp('/');
    expect(await screen.findByText(/Estoque projetado indisponível agora/)).toBeInTheDocument();
    expect(screen.queryByLabelText('Estoque projetado')).not.toBeInTheDocument();
    expect(within(screen.getByLabelText('Indicadores de ruptura')).getByText('Risco de ruptura').nextSibling).toHaveTextContent('2 SKUs');
    // Sem a agregação, o gráfico semanal também some, sem barras de zero.
    expect(screen.queryByRole('heading', { name: 'SKUs em falta por semana' })).not.toBeInTheDocument();
  });
});

describe('Início: gráficos do painel (fase 4)', () => {
  it('SKUs em falta por semana: duas linhas com eixos, legenda e a frase do pico', async () => {
    mockApi();
    renderApp('/');
    const chart = await section('SKUs em falta por semana');
    const image = within(chart).getByRole('img', { name: /SKUs em falta por semana, sem novas ordens e com o plano/ });
    expect(image.getAttribute('aria-label')).toMatch(/Pico de 2 SKUs em falta na semana de 02\/11 sem novas ordens; com o plano, o pico é de 1 SKU\./);
    expect(within(chart).getByText('Sem novas ordens')).toBeInTheDocument();
    expect(within(chart).getByText('Com o plano')).toBeInTheDocument();
    expect(chart.querySelectorAll('.recharts-line')).toHaveLength(2);
    expect(chart.querySelectorAll('.recharts-xAxis-tick-labels text').length).toBeGreaterThanOrEqual(2);
    expect(chart.querySelectorAll('.recharts-yAxis-tick-labels text').length).toBeGreaterThanOrEqual(2);
    // Vem depois dos indicadores, como o resto do painel.
    expect(screen.getByLabelText('Estoque projetado').compareDocumentPosition(chart) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('sem falta no horizonte, diz isso em vez de desenhar um pico', async () => {
    const base = overview.projected_stock!;
    mockApi({ overview: { ...overview, projected_stock: { ...base, weekly: base.weekly!.map((week) => ({ ...week, shortfall_sku_count: 0, shortfall_with_plan_sku_count: 0 })) } } });
    renderApp('/');
    const chart = await section('SKUs em falta por semana');
    expect(within(chart).getByText('Nenhum SKU em falta no horizonte, com ou sem novas ordens.')).toBeInTheDocument();
  });

  it('resposta antiga sem a série semanal: o gráfico não aparece e os números seguem', async () => {
    const { weekly: _removed, ...base } = overview.projected_stock!;
    mockApi({ overview: { ...overview, projected_stock: base } });
    renderApp('/');
    expect(await screen.findByLabelText('Estoque projetado')).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'SKUs em falta por semana' })).not.toBeInTheDocument();
  });

  it('produção planejada por mês aparece no Início sem repetir os totais dos indicadores', async () => {
    mockApi();
    renderApp('/');
    // O título aparece já no "Calculando…"; espera o gráfico em si.
    const image = await screen.findByRole('img', { name: /Unidades a liberar para produção por mês, Empresa/ });
    const chart = image.closest('section') as HTMLElement;
    expect(chart.textContent).not.toMatch(/para liberar agora/);
    // Os meses além da previsão continuam avisados.
    expect(chart.textContent).toMatch(/jan, fev fora do gráfico/);
  });

  it('falha da produção planejada não derruba o Início', async () => {
    mockApi({ productionPlan: fail(500, 'Erro interno.') });
    renderApp('/');
    expect(await screen.findByText('Produção planejada indisponível')).toBeInTheDocument();
    expect(screen.getByText('Primeiro da fila · posição 1')).toBeInTheDocument();
    expect(await section('SKUs em falta por semana')).toBeInTheDocument();
  });
});
