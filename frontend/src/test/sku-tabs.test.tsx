import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { SKU_OK, skuDetailOk } from './fixtures';
import { currentLocation, fail, mockApi, renderApp } from './utils';

const selected = () => screen.getAllByRole('tab').filter((tab) => tab.getAttribute('aria-selected') === 'true').map((tab) => tab.textContent);

describe('detalhe do SKU: abas', () => {
  it('abre em Resumo, com a ação e os atalhos acima das abas, e não carrega parceiros nem mostra faturamento', async () => {
    const api = mockApi();
    renderApp(`/skus/${SKU_OK}`);
    const answer = await screen.findByRole('region', { name: 'Ação operacional sugerida' });
    expect(within(answer).getByRole('link', { name: 'Registrar decisão' })).toBeInTheDocument();
    expect(within(answer).getByRole('link', { name: 'Criar caso' })).toBeInTheDocument();
    expect(screen.getAllByRole('tab').map((tab) => tab.textContent)).toEqual(['Resumo', 'Evidências', 'Parceiros', 'Impacto financeiro']);
    expect(selected()).toEqual(['Resumo']);
    expect(screen.getByText(/Evento mais urgente:/)).toBeInTheDocument();
    expect(screen.queryByText('Faturamento estimado', { selector: 'summary' })).not.toBeInTheDocument();
    expect(screen.queryByText('Riscos e evidências')).not.toBeInTheDocument();
    expect(api.gets().some((path) => path.startsWith('/api/commercial-recommendations'))).toBe(false);
  });

  it('a aba escolhida vai para a URL, preserva o retorno à origem e carrega o contexto comercial só quando pedido', async () => {
    const user = userEvent.setup();
    const api = mockApi();
    renderApp('/fila?todos=1');
    await user.click(await screen.findByRole('button', { name: `Ver detalhes de ${SKU_OK}` }));
    await screen.findByRole('region', { name: 'Ação operacional sugerida' });
    await user.click(screen.getByRole('tab', { name: 'Parceiros' }));
    expect(currentLocation()).toBe(`/skus/${SKU_OK}?tab=parceiros`);
    expect(await screen.findByRole('heading', { level: 2, name: 'Parceiros com este SKU' })).toBeInTheDocument();
    expect(api.gets().some((path) => path.startsWith('/api/commercial-recommendations'))).toBe(true);
    await user.click(screen.getByRole('tab', { name: 'Resumo' }));
    expect(currentLocation()).toBe(`/skus/${SKU_OK}`);
    await user.click(screen.getByRole('button', { name: 'Voltar' }));
    await waitFor(() => expect(currentLocation()).toBe('/fila?todos=1'));
  });

  it('cada aba mostra o seu conteúdo: evidências, parceiros e impacto', async () => {
    const user = userEvent.setup();
    mockApi();
    renderApp(`/skus/${SKU_OK}?tab=evidencias`);
    expect(await screen.findByText('Riscos e evidências')).toBeInTheDocument();
    expect(screen.getByText('Dados do SKU')).toBeInTheDocument();
    expect(screen.getByText('Sobre a previsão')).toBeInTheDocument();
    await user.click(screen.getByRole('tab', { name: 'Impacto financeiro' }));
    expect(await screen.findByText('Faturamento estimado', { selector: 'summary' })).toBeInTheDocument();
    expect(screen.queryByText('Riscos e evidências')).not.toBeInTheDocument();
  });

  it('aba inválida cai em Resumo sem erro', async () => {
    mockApi();
    renderApp(`/skus/${SKU_OK}?tab=inexistente`);
    await screen.findByRole('region', { name: 'Ação operacional sugerida' });
    expect(selected()).toEqual(['Resumo']);
  });

  it('"Ver eventos e cenário" no resumo leva às evidências', async () => {
    const user = userEvent.setup();
    mockApi();
    renderApp(`/skus/${SKU_OK}`);
    await user.click(await screen.findByRole('button', { name: 'Ver eventos e cenário' }));
    expect(currentLocation()).toBe(`/skus/${SKU_OK}?tab=evidencias`);
    expect(await screen.findByRole('heading', { level: 4, name: 'Eventos e sazonalidade' })).toBeInTheDocument();
  });

  it('setas, Home e End movem a seleção e o foco; só a aba ativa entra no Tab', async () => {
    const user = userEvent.setup();
    mockApi();
    renderApp(`/skus/${SKU_OK}`);
    const first = await screen.findByRole('tab', { name: 'Resumo' });
    expect(first).toHaveAttribute('tabindex', '0');
    expect(screen.getByRole('tab', { name: 'Parceiros' })).toHaveAttribute('tabindex', '-1');
    first.focus();
    await user.keyboard('{ArrowRight}');
    expect(screen.getByRole('tab', { name: 'Evidências' })).toHaveFocus();
    expect(selected()).toEqual(['Evidências']);
    await user.keyboard('{End}');
    expect(screen.getByRole('tab', { name: 'Impacto financeiro' })).toHaveFocus();
    await user.keyboard('{ArrowRight}');
    expect(screen.getByRole('tab', { name: 'Resumo' })).toHaveFocus();
    await user.keyboard('{ArrowLeft}');
    expect(screen.getByRole('tab', { name: 'Impacto financeiro' })).toHaveFocus();
  });

  it('falha dos dados secundários não bloqueia a ação operacional', async () => {
    mockApi({ commercial: fail(500, 'Comercial fora do ar'), skuDetail: { ...skuDetailOk, revenue_forecast: null, event_alerts: null } });
    renderApp(`/skus/${SKU_OK}?tab=parceiros`);
    expect(await screen.findByText('Comercial fora do ar')).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Ação operacional sugerida' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Registrar decisão' })).toBeInTheDocument();
  });
});
