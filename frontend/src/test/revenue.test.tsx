import { screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { displayCurrency, displayPrice, formatMonth, glossary } from '../pages/shared';
import { SKU_OK, SKU_SHORT, revenueForecast } from './fixtures';
import { fail, mockApi, renderApp } from './utils';

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

describe('Previsão: faturamento estimado', () => {
  it('mostra o total como estimativa, com selo, erro do teste e gráfico acessível', async () => {
    mockApi();
    renderApp('/previsoes');
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
    renderApp('/previsoes');
    const table = await screen.findByRole('region', { name: 'Faturamento estimado por família' });
    const rowB = within(table).getByText('Família B').closest('tr') as HTMLElement;
    expect(within(rowB).getAllByText('Não disponível').length).toBeGreaterThan(0);
    expect(within(rowB).queryByText(/R\$/)).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'SKUs fora da estimativa em Total da empresa' })).toBeInTheDocument();
    expect(screen.getAllByRole('tooltip', { hidden: true }).some((node) => node.textContent?.includes(`${SKU_SHORT} (sem previsão)`))).toBe(true);
  });

  it('falha da estimativa não bloqueia a tela operacional e oferece nova tentativa', async () => {
    mockApi({ revenueForecast: fail(500, 'Erro interno.') });
    renderApp('/previsoes?todos=1');
    expect(await screen.findByRole('heading', { level: 2, name: 'Preciso produzir? Quanto?' })).toBeInTheDocument();
    expect(await screen.findByText('Faturamento estimado indisponível')).toBeInTheDocument();
    expect(screen.getByText(/A previsão em unidades e as ações seguem válidas/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Tentar novamente' })).toBeInTheDocument();
    expect(screen.getAllByText(SKU_OK).length).toBeGreaterThan(0);
    expect(screen.getAllByText('Não disponível').length).toBeGreaterThan(0);
  });

  it('não altera as colunas e a ação operacional existentes', async () => {
    mockApi();
    renderApp('/previsoes?todos=1');
    const table = await screen.findByRole('region', { name: /Previsões; role horizontalmente/ });
    for (const header of ['SKU / Produto', 'Ação operacional sugerida', 'Quantidade sugerida (un.)', 'Próximo mês (un.)']) {
      expect(within(table).getByRole('columnheader', { name: header })).toBeInTheDocument();
    }
  });
});

describe('Detalhe do SKU: faturamento estimado', () => {
  it('exibe o cálculo unidades × preço e o selo de estimativa', async () => {
    mockApi();
    renderApp(`/skus/${SKU_OK}`);
    const block = (await screen.findByText('Faturamento estimado', { selector: 'summary' })).closest('details') as HTMLElement;
    expect(within(block).getAllByText('Estimativa').length).toBeGreaterThan(0);
    expect(within(block).getByText(/Precos_Produtos/)).toBeInTheDocument();
    const calc = within(block).getByRole('region', { name: 'Cálculo do faturamento estimado' });
    expect(within(calc).getAllByRole('row')).toHaveLength(1 + revenueForecast.items[0].calculation!.terms.length);
    expect(within(calc).getByText(/previsão em unidades × preço unitário vigente/)).toBeInTheDocument();
  });

  it('SKU sem previsão: não mostra valor em reais e explica o motivo', async () => {
    mockApi();
    renderApp(`/skus/${encodeURIComponent(SKU_SHORT)}`);
    const block = (await screen.findByText('Faturamento estimado', { selector: 'summary' })).closest('details') as HTMLElement;
    expect(within(block).getByText('Sem previsão')).toBeInTheDocument();
    expect(within(block).getByText(/ausência não é faturamento zero/)).toBeInTheDocument();
    expect(within(block).queryByText(/R\$/)).not.toBeInTheDocument();
  });

  it('resposta antiga sem o campo não quebra o detalhe', async () => {
    const detail = { ...(await import('./fixtures')).skuDetailOk } as Record<string, unknown>;
    delete detail.revenue_forecast;
    mockApi({ skuDetail: detail });
    renderApp(`/skus/${SKU_OK}`);
    expect(await screen.findByText('Riscos e evidências')).toBeInTheDocument();
    expect(screen.queryByText('Faturamento estimado', { selector: 'summary' })).not.toBeInTheDocument();
  });

  it('estimativa indisponível (null) mantém a previsão em unidades visível', async () => {
    const { skuDetailOk } = await import('./fixtures');
    mockApi({ skuDetail: { ...skuDetailOk, revenue_forecast: null } });
    renderApp(`/skus/${SKU_OK}`);
    expect(await screen.findByText(/Estimativa de faturamento indisponível no momento/)).toBeInTheDocument();
    expect(screen.getByText('Sobre a previsão')).toBeInTheDocument();
  });
});
