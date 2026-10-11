import { screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { quality } from './fixtures';
import { mockApi, renderApp } from './utils';

// Upload (U.2): a linha de intenção de /qualidade diz de que base são os números.
describe('qualidade: data de referência da base', () => {
  it('mostra a base de dd/mm/aaaa, o último mês de vendas e o link para atualizar', async () => {
    mockApi();
    renderApp('/qualidade');
    const title = await screen.findByRole('heading', { level: 2, name: 'Posso confiar na planilha?' });
    const intro = title.closest('.page-intro') as HTMLElement;
    expect(intro).toHaveTextContent('Base de 14/09/2026 · vendas até ago/26');
    expect(within(intro).getByRole('link', { name: 'Atualizar dados' })).toHaveAttribute('href', '/dados/atualizar');
  });

  it('sem reference mantém o texto de antes e não oferece o link', async () => {
    const { reference: _omit, ...legacy } = quality;
    mockApi({ quality: legacy });
    renderApp('/qualidade');
    const title = await screen.findByRole('heading', { level: 2, name: 'Posso confiar na planilha?' });
    const intro = title.closest('.page-intro') as HTMLElement;
    expect(intro).not.toHaveTextContent('Base de');
    expect(intro).toHaveTextContent('O principal limite é a cobertura de sell-out');
    expect(within(intro).queryByRole('link')).toBeNull();
  });

  it('sem vendas informadas mostra só a data da base', async () => {
    mockApi({ quality: { ...quality, reference: { ...quality.reference!, sales_last_month: null } } });
    renderApp('/qualidade');
    const title = await screen.findByRole('heading', { level: 2, name: 'Posso confiar na planilha?' });
    expect((title.closest('.page-intro') as HTMLElement).textContent).toMatch(/Base de 14\/09\/2026\. /);
  });
});
