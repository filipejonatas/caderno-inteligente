import { screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { overview } from './fixtures';
import { mockApi, renderApp } from './utils';

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
  });
});
