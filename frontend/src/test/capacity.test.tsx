import { screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { SKU_OK } from './fixtures';
import { mockApi, renderApp } from './utils';

// Etapa 15.4: onde a produção planejada não cabe na capacidade livre de cada linha.
describe('capacidade semanal', () => {
  it('mostra cada família com a situação e explica a falta', async () => {
    const api = mockApi();
    renderApp('/capacidade');
    const table = await screen.findByRole('region', { name: 'Capacidade por linha' });
    const escolar = within(table).getByText('Escolar').closest('tr') as HTMLElement;
    expect(escolar).toHaveTextContent('Não cabe');
    expect(escolar).toHaveTextContent('800');
    expect(within(table).getByText('Refis').closest('tr')).toHaveTextContent('Cabe');
    expect(screen.getByText(new RegExp(`SKUs ${SKU_OK}`))).toHaveTextContent('PED-1 (KA-01)');
    expect(api.gets()).toContain('/api/capacity-plan');
  });

  it('fica em Planejamento e se abre pela fila, como Cenários', async () => {
    mockApi();
    const queue = renderApp('/fila');
    await screen.findByRole('heading', { level: 2, name: 'Qual SKU analisar, o que fazer e quanto' });
    expect(screen.getByRole('link', { name: 'Ver capacidade' })).toHaveAttribute('href', '/capacidade');
    queue.unmount();
    renderApp('/capacidade');
    await screen.findByRole('region', { name: 'Capacidade por linha' });
    expect(within(screen.getByRole('navigation', { name: 'Navegação principal' })).getByRole('link', { name: /Planejamento/ })).toHaveAttribute('aria-current', 'page');
  });
});
