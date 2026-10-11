import { screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { allocationRegions } from './fixtures';
import { fail, mockApi, renderApp } from './utils';

const regions = {
  ...allocationRegions,
  totals: { ...allocationRegions.totals, uncovered_units: 4000, uncovered_value: 300000, orders: 14 },
  regions: [
    { region: 'Nacional', uncovered_units: 1000, uncovered_value: 81200, orders: 7, skus: ['A', 'B'] },
    { region: 'Centro-Oeste', uncovered_units: 1500, uncovered_value: 130400, orders: 4, skus: ['A'] },
    { region: 'Sul', uncovered_units: 1500, uncovered_value: 88400, orders: 3, skus: ['A', 'C', 'D'] },
  ],
};

const card = async () => (await screen.findByRole('list', { name: 'Pedidos sem cobertura por macrorregião' })).closest('section') as HTMLElement;

describe('Início: pedidos sem cobertura por região', () => {
  it('mostra um bloco por macrorregião com valor e pedidos, e o total no subtítulo', async () => {
    mockApi({ allocationRegions: regions });
    renderApp('/');
    const section = await card();
    const list = within(section).getByRole('list', { name: 'Pedidos sem cobertura por macrorregião' });
    const centro = within(list).getByText('Centro-Oeste').closest('li') as HTMLElement;
    expect(centro).toHaveTextContent(/R\$\s*130,4 mil/);
    expect(centro).toHaveTextContent('4 pedidos · 1 SKU');
    expect(section).toHaveTextContent(/R\$\s*300\.000 em 14 pedidos confirmados/);
    expect(within(section).getByRole('link', { name: 'Ver o detalhe por região' })).toHaveAttribute('href', '/parceiros');
  });

  it('região sem pedidos fica como ausência, nunca como zero, e "Nacional" vai para a linha abaixo', async () => {
    mockApi({ allocationRegions: regions });
    renderApp('/');
    const section = await card();
    const norte = within(section).getByText('Norte').closest('li') as HTMLElement;
    expect(norte).toHaveClass('region-empty');
    expect(norte).toHaveTextContent('Sem pedidos');
    expect(norte).not.toHaveTextContent(/R\$/);
    expect(within(section).getByText(/Nacional:/).closest('p')).toHaveTextContent(/R\$\s*81,2 mil em 7 pedidos/);
    expect(within(section).queryByText('Nacional', { selector: 'li strong' })).not.toBeInTheDocument();
  });

  it('sem preço em alguma região, usa as unidades em vez de inventar valor', async () => {
    mockApi();
    renderApp('/');
    const section = await card();
    const sul = within(section).getByText('Sul').closest('li') as HTMLElement;
    expect(sul).toHaveTextContent('300 un.');
    expect(sul).not.toHaveTextContent(/R\$/);
  });

  it('se a leitura falhar, só o mapa e o passo "Atender" ficam indisponíveis', async () => {
    mockApi({ allocationRegions: fail(500, 'Erro interno.') });
    renderApp('/');
    expect(await screen.findByText(/Pedidos sem cobertura por região: indisponível/)).toBeInTheDocument();
    const journey = within(await screen.findByRole('list', { name: 'Caminho do PCP, em cinco passos' }));
    expect(await journey.findAllByText('Indisponível')).toHaveLength(1);
    expect(screen.getByRole('heading', { level: 3, name: 'Decisões de hoje' })).toBeInTheDocument();
  });

  it('"Decisões de hoje" vem depois dos gráficos, na mesma grade', async () => {
    mockApi({ allocationRegions: regions });
    renderApp('/');
    const map = await card();
    const decisions = (await screen.findByRole('heading', { level: 3, name: 'Decisões de hoje' })).closest('section') as HTMLElement;
    expect(map.compareDocumentPosition(decisions) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(decisions.parentElement).toHaveClass('home-mosaic');
  });
});
