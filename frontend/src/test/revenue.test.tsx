import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { displayCurrency, displayPrice, formatMonth, glossary } from '../pages/shared';
import { SKU_OK, SKU_SHORT, revenueForecast } from './fixtures';
import { currentLocation, fail, mockApi, renderApp } from './utils';

describe('formatos de faturamento', () => {
  it('formata reais e nunca transforma ausência em R$ 0', () => {
    expect(displayCurrency(4125)).toMatch(/R\$\s?4\.125/);
    expect(displayPrice(12.5)).toMatch(/R\$\s?12,50/);
    expect(displayCurrency(null)).toBe('Não disponível');
    expect(displayCurrency(undefined)).toBe('Não disponível');
    expect(displayPrice(null)).toBe('Não disponível');
    expect(displayCurrency(0)).toMatch(/R\$\s?0/);
  });

  it('rotula meses em português sem depender do fuso', () => {
    expect(formatMonth('2026-09-01')).toBe('set/26');
    expect(formatMonth('2027-01-01')).toBe('jan/27');
    expect(formatMonth(null)).toBe('Não disponível');
  });
});

describe('Faturamento previsto: página própria', () => {
  it('mostra o total como estimativa, com selo, erro do teste e gráfico acessível', async () => {
    mockApi();
    renderApp('/faturamento');
    const card = (await screen.findByRole('heading', { level: 3, name: 'Faturamento estimado' })).closest('section') as HTMLElement;
    expect(within(card).getByText('Unidades previstas × preço vigente, próximos três meses.')).toBeInTheDocument();
    expect(within(card).getByText('Estimativa', { selector: '.badge' })).toBeInTheDocument();
    expect(within(card).getByRole('button', { name: 'O que é: Faturamento estimado' })).toBeInTheDocument();
    const table = within(card).getByRole('region', { name: 'Faturamento estimado por família' });
    const total = within(table).getByText('Total da empresa').closest('tr') as HTMLElement;
    expect(within(total).getByText(/R\$\s?4\.125/)).toBeInTheDocument();
    expect(within(total).getByText('+37,5%')).toBeInTheDocument();
    expect(within(total).getByText('8,0%')).toBeInTheDocument();
    expect(within(card).getByRole('img', { name: /observado e estimado/ })).toBeInTheDocument();
    expect(within(card).getByText('Observado')).toBeInTheDocument();
  });

  it('a explicação do "?" traz fórmula e limitações, e o ausente nunca vira R$ 0', () => {
    expect(glossary.faturamento_estimado.text).toMatch(/unidades × preço vigente/);
    expect(glossary.faturamento_estimado.text).toMatch(/Estimativa, não faturamento realizado/);
    expect(glossary.faturamento_estimado.text).toMatch(/nunca vira R\$ 0/);
  });

  it('família sem estimativa mostra "Não disponível", nunca R$ 0, e lista o SKU fora', async () => {
    mockApi();
    renderApp('/faturamento');
    const table = await screen.findByRole('region', { name: 'Faturamento estimado por família' });
    const rowB = within(table).getByText('Família B').closest('tr') as HTMLElement;
    expect(within(rowB).getAllByText('Não disponível').length).toBeGreaterThan(0);
    expect(within(rowB).queryByText(/R\$/)).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'SKUs fora da estimativa em Total da empresa' })).toBeInTheDocument();
    expect(screen.getAllByRole('tooltip', { hidden: true }).some((node) => node.textContent?.includes(`${SKU_SHORT} (sem previsão)`))).toBe(true);
  });

  it('falha da estimativa explica o motivo e oferece nova tentativa', async () => {
    mockApi({ revenueForecast: fail(500, 'Erro interno.') });
    renderApp('/faturamento');
    expect(await screen.findByRole('heading', { level: 2, name: 'Quanto se estima faturar nos próximos três meses' })).toBeInTheDocument();
    expect(await screen.findByText('Faturamento estimado indisponível')).toBeInTheDocument();
    expect(screen.getByText(/Erro interno\./)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Tentar novamente' })).toBeInTheDocument();
  });

  it('a fila operacional não carrega nem exibe faturamento, e a falha dele não a afeta', async () => {
    const api = mockApi({ revenueForecast: fail(500, 'Erro interno.') });
    renderApp('/fila?todos=1');
    const table = await screen.findByRole('region', { name: /Fila operacional; role horizontalmente/ });
    expect(within(table).getByText(SKU_OK)).toBeInTheDocument();
    expect(screen.queryByRole('heading', { level: 3, name: 'Faturamento estimado' })).not.toBeInTheDocument();
    expect(screen.queryByText('Faturamento estimado indisponível')).not.toBeInTheDocument();
    expect(api.gets()).not.toContain('/api/revenue-forecast');
  });

  it('lista os SKUs: sem previsão mostra o motivo e "Não disponível", nunca R$ 0, e leva ao impacto do SKU', async () => {
    mockApi();
    renderApp('/faturamento');
    const table = await screen.findByRole('region', { name: /Faturamento estimado por SKU/ });
    const ok = within(table).getByText(SKU_OK).closest('tr') as HTMLElement;
    expect(within(ok).getByText(/R\$\s?/)).toBeInTheDocument();
    expect(within(ok).getByRole('link', { name: `Ver impacto financeiro de ${SKU_OK}` })).toHaveAttribute('href', `/skus/${SKU_OK}?tab=impacto`);
    const short = within(table).getByText(SKU_SHORT).closest('tr') as HTMLElement;
    expect(within(short).getByText('Sem previsão')).toBeInTheDocument();
    expect(within(short).getAllByText('Não disponível').length).toBeGreaterThan(0);
    expect(within(short).queryByText(/R\$/)).not.toBeInTheDocument();
  });

  it('filtra por família e por busca na URL, e funciona isoladamente por endereço', async () => {
    const user = userEvent.setup();
    mockApi();
    renderApp('/faturamento?familia=Fam%C3%ADlia+B');
    const skus = await screen.findByRole('region', { name: /Faturamento estimado por SKU/ });
    expect(within(skus).getByText(SKU_SHORT)).toBeInTheDocument();
    expect(within(skus).queryByText(SKU_OK)).not.toBeInTheDocument();
    const families = screen.getByRole('region', { name: 'Faturamento estimado por família' });
    expect(within(families).getByText('Família B')).toBeInTheDocument();
    expect(within(families).queryByText('Família A')).not.toBeInTheDocument();
    expect(within(families).getByText('Total da empresa')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Limpar filtros' }));
    expect(currentLocation()).toBe('/faturamento');
    await user.type(screen.getByLabelText('Buscar'), SKU_OK);
    expect(currentLocation()).toBe(`/faturamento?busca=${SKU_OK}`);
    expect(within(screen.getByRole('region', { name: /Faturamento estimado por SKU/ })).queryByText(SKU_SHORT)).not.toBeInTheDocument();
  });

  it('o faturamento tem grupo próprio no menu, separado do Planejamento', async () => {
    mockApi();
    renderApp('/faturamento');
    await screen.findByRole('heading', { level: 2, name: 'Quanto se estima faturar nos próximos três meses' });
    const menu = within(screen.getByRole('navigation', { name: 'Navegação principal' }));
    expect(menu.getByRole('link', { name: 'Financeiro' })).toHaveAttribute('aria-current', 'page');
    expect(menu.getByRole('link', { name: 'Planejamento' })).toHaveAttribute('href', '/fila');
    expect(menu.getByRole('link', { name: 'Planejamento' })).not.toHaveAttribute('aria-current');
  });
});

describe('Detalhe do SKU: faturamento estimado', () => {
  it('exibe o cálculo unidades × preço e o selo de estimativa', async () => {
    mockApi();
    renderApp(`/skus/${SKU_OK}?tab=impacto`);
    const block = (await screen.findByText('Faturamento estimado', { selector: 'summary' })).closest('details') as HTMLElement;
    expect(within(block).getAllByText('Estimativa').length).toBeGreaterThan(0);
    expect(within(block).getByText(/Precos_Produtos/)).toBeInTheDocument();
    const calc = within(block).getByRole('region', { name: 'Cálculo do faturamento estimado' });
    expect(within(calc).getAllByRole('row')).toHaveLength(1 + revenueForecast.items[0].calculation!.terms.length);
    expect(within(calc).getByText(/previsão em unidades × preço unitário vigente/)).toBeInTheDocument();
  });

  it('SKU sem previsão: não mostra valor em reais e explica o motivo', async () => {
    mockApi();
    renderApp(`/skus/${encodeURIComponent(SKU_SHORT)}?tab=impacto`);
    const block = (await screen.findByText('Faturamento estimado', { selector: 'summary' })).closest('details') as HTMLElement;
    expect(within(block).getByText('Sem previsão')).toBeInTheDocument();
    expect(within(block).getByText(/ausência não é faturamento zero/)).toBeInTheDocument();
    expect(within(block).queryByText(/R\$/)).not.toBeInTheDocument();
  });

  it('resposta antiga sem o campo não quebra o detalhe', async () => {
    const detail = { ...(await import('./fixtures')).skuDetailOk } as Record<string, unknown>;
    delete detail.revenue_forecast;
    mockApi({ skuDetail: detail });
    renderApp(`/skus/${SKU_OK}?tab=impacto`);
    expect(await screen.findByRole('tab', { name: 'Impacto financeiro', selected: true })).toBeInTheDocument();
    expect(screen.queryByText('Faturamento estimado', { selector: 'summary' })).not.toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Ação operacional sugerida' })).toBeInTheDocument();
  });

  it('estimativa indisponível (null) mantém a previsão em unidades visível', async () => {
    const { skuDetailOk } = await import('./fixtures');
    mockApi({ skuDetail: { ...skuDetailOk, revenue_forecast: null } });
    renderApp(`/skus/${SKU_OK}?tab=impacto`);
    expect(await screen.findByText(/Estimativa de faturamento indisponível no momento/)).toBeInTheDocument();
    await userEvent.setup().click(screen.getByRole('tab', { name: 'Evidências' }));
    expect(await screen.findByText('Sobre a previsão')).toBeInTheDocument();
  });
});
