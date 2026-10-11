import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { validationSummaryPreviousBase } from './fixtures';
import { mockApi, renderApp } from './utils';

// Upload (D8): casos congelados sobre a base anterior ficam fora da contagem e agrupados.
describe('validação: casos da base anterior', () => {
  it('a contagem exibida exclui os casos da base anterior e informa quantos ficaram de fora', async () => {
    mockApi({ validation: validationSummaryPreviousBase });
    renderApp('/validacao');
    const card = (await screen.findByText('Casos de teste aprovados')).closest('article') as HTMLElement;
    expect(card).toHaveTextContent('1 de 1');
    expect(card).toHaveTextContent('1 da base anterior fora da conta');
  });

  it('sem previous_base a contagem fica como antes', async () => {
    mockApi();
    renderApp('/validacao');
    const card = (await screen.findByText('Casos de teste aprovados')).closest('article') as HTMLElement;
    expect(card).toHaveTextContent('0 de 0');
    expect(card).not.toHaveTextContent('base anterior');
  });

  it('a auditoria agrupa os casos base_anterior num bloco recolhido com o rótulo e a explicação', async () => {
    mockApi({ validation: validationSummaryPreviousBase });
    renderApp('/auditoria');
    const group = (await screen.findByText('Referem-se à base anterior (fora da contagem)')).closest('details') as HTMLElement;
    expect(group).not.toHaveAttribute('open');
    await userEvent.click(within(group).getByText('Referem-se à base anterior (fora da contagem)'));
    expect(group).toHaveTextContent('Refere-se à base anterior (base de 14/09/2026)');
    expect(group).toHaveTextContent('não são avaliados nem contados');
    expect(within(group).getByText('Caso da base anterior')).toBeInTheDocument();
    expect(within(group).queryByText('Caso sintético')).toBeNull();
  });

  it('sem casos da base anterior não há grupo', async () => {
    mockApi();
    renderApp('/auditoria');
    await screen.findByText('Casos de teste congelados');
    expect(screen.queryByText('Referem-se à base anterior (fora da contagem)')).toBeNull();
  });
});
