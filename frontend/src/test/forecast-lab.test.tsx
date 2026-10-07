import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { ForecastLabContent, coverageText } from '../components/ForecastLab';
import { SKU_OK, forecastLab } from './fixtures';
import { fail, mockApi, pending, renderApp } from './utils';

async function openModelsTab() {
  const user = userEvent.setup();
  renderApp('/validacao');
  await screen.findByRole('heading', { name: 'Em resumo' });
  await user.click(within(screen.getByRole('tablist', { name: 'Detalhes da validação' })).getByRole('tab', { name: 'Modelos de previsão' }));
  return user;
}

const region = (name: string) => screen.findByRole('region', { name });

describe('laboratório de previsão na Validação', () => {
  it('mostra o laboratório na aba de modelos, avisando que nada foi promovido', async () => {
    const api = mockApi();
    await openModelsTab();

    expect(await screen.findByRole('heading', { name: 'Modelos candidatos (laboratório)' })).toBeInTheDocument();
    expect(screen.getByText(/Nada foi promovido: as previsões oficiais seguem o motor atual/)).toBeInTheDocument();
    expect(api.gets()).toContain('/api/forecast-lab');
  });

  it('compara baseline, motor v1 e motor rolante, com viés assinado', async () => {
    mockApi();
    await openModelsTab();
    const table = await region('Avaliação dos motores em meses já ocorridos');
    const row = (name: string) => within(table).getByText(name).closest('tr') as HTMLElement;

    expect(within(row('Previsão simples (baseline)')).getByText('17,0%')).toBeInTheDocument();
    expect(within(row('Previsão simples (baseline)')).getByText('+8,5%')).toBeInTheDocument();
    expect(within(row('Motor v1')).getByText('9,0%')).toBeInTheDocument();
    expect(within(row('Motor v1')).getByText('-4,3%')).toBeInTheDocument();
    expect(within(row('Motor rolante (candidato)')).getAllByRole('cell')[3]).toHaveTextContent('2');
  });

  it('mostra a avaliação com meses de pico que decidiu a promoção', async () => {
    mockApi();
    await openModelsTab();
    const table = await region('Avaliação dos motores com meses de pico');
    const row = (name: string) => within(table).getByText(name).closest('tr') as HTMLElement;

    expect(within(table).getAllByRole('row')).toHaveLength(5);
    expect(row('Motor v2 (oficial)')).toHaveTextContent('8,0% · 7,9%');
    expect(row('Motor v2 (oficial)')).toHaveTextContent('+0,7%');
    expect(row('Motor v1 (anterior)')).toHaveTextContent('-5,3%');
    expect(screen.getByText(/Critérios de promoção/)).toHaveTextContent('Atendidos');
  });

  it('esconde a faixa de previsão quando ela não está calibrada', () => {
    const data = { ...forecastLab, intervals: { ...forecastLab.intervals, status: 'nao_calibrada' as const, status_note: 'A faixa cobriu 48% dos meses testados contra 80% prometidos; não é mostrada até ser recalibrada.' } };
    render(<MemoryRouter><ForecastLabContent data={data} /></MemoryRouter>);

    expect(screen.getByText(/não é mostrada até ser recalibrada/)).toBeInTheDocument();
    expect(screen.queryByText(/Fora da amostra, a faixa de/)).not.toBeInTheDocument();
    expect(screen.queryByRole('region', { hidden: true, name: 'Faixa de previsão do próximo mês' })).not.toBeInTheDocument();
  });

  it('a grade de sensibilidade marca a linha padrão uma vez e não esconde a combinação que reprova', async () => {
    mockApi();
    await openModelsTab();
    const grid = await region('Grade de sensibilidade da avaliação');
    const rows = within(grid).getAllByRole('row').slice(1);

    expect(rows).toHaveLength(3);
    expect(within(grid).getAllByText('padrão')).toHaveLength(1);
    const defaultRow = within(grid).getByText('padrão').closest('tr') as HTMLElement;
    expect(defaultRow).toHaveTextContent('Treino de 18 e 21 meses');
    expect(defaultRow).toHaveTextContent('+21,6%');
    const failing = rows.find((row) => /Não atendidos/.test(row.textContent ?? '')) as HTMLElement;
    expect(failing).toHaveTextContent('Treino de 15, 18 e 21 meses');
    expect(failing).toHaveTextContent('-26,7%');
    expect(screen.getByText(/Critérios atendidos em/).textContent).toMatch(/2 de 3 combinações.*de -26,7% a \+22,6%/);
    expect(screen.getByText(/a amostra é menor do que parece/)).toBeInTheDocument();
  });

  it('lista os modelos testados e os SKUs que mudariam de modelo', async () => {
    mockApi();
    await openModelsTab();
    const models = await region('Modelos candidatos');

    expect(within(models).getByText('Suavização exponencial simples')).toBeInTheDocument();
    expect(within(models).getAllByRole('row')).toHaveLength(3);
    const changed = screen.getByRole('region', { hidden: true, name: 'SKUs que mudariam de modelo' });
    expect(within(changed).getByRole('link', { name: SKU_OK, hidden: true })).toHaveAttribute('href', `/skus/${encodeURIComponent(SKU_OK)}`);
  });

  it('diz quanto a faixa de previsão acertou fora da amostra, sem esconder que ficou abaixo do esperado', async () => {
    mockApi();
    await openModelsTab();
    await region('Modelos candidatos');

    const note = screen.getByText(/Fora da amostra, a faixa de/);
    expect(note.textContent).toMatch(/80% cobriu 48% dos 150 meses testados/);
    expect(note.textContent).toMatch(/abaixo do esperado: use-a como indicação, não como garantia/);
    expect(note.textContent).toMatch(/1 SKUs ficaram sem faixa/);
    const table = screen.getByRole('region', { hidden: true, name: 'Faixa de previsão do próximo mês' });
    const row = within(table).getByText(SKU_OK, { selector: 'a' }).closest('tr') as HTMLElement;
    expect(row).toHaveTextContent('set/26');
    expect(row).toHaveTextContent('212'); // quantidades a partir de 100 são exibidas como inteiros
    expect(row).toHaveTextContent('198 a 216');
  });

  it('falha do laboratório não derruba a validação e permite nova tentativa', async () => {
    let calls = 0;
    mockApi({ forecastLab: () => (++calls === 1 ? fail(500, 'Erro interno.') : forecastLab) });
    const user = await openModelsTab();

    expect(await screen.findByText(/Laboratório indisponível no momento/)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Em resumo' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Tentar novamente' }));
    expect(await region('Grade de sensibilidade da avaliação')).toBeInTheDocument();
    expect(calls).toBe(2);
  });

  it('enquanto calcula, avisa e o resto da validação continua visível', async () => {
    mockApi({ forecastLab: pending() });
    await openModelsTab();

    expect(await screen.findByText('Calculando a comparação entre motores…')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Falhas conhecidas' })).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole('region', { name: 'Grade de sensibilidade da avaliação' })).not.toBeInTheDocument());
  });
});

describe('ForecastLabContent', () => {
  const renderContent = (data = forecastLab) => render(<MemoryRouter><ForecastLabContent data={data} /></MemoryRouter>);

  it('sem SKUs que mudam de modelo não mostra a lista e ausência continua "Não disponível", nunca zero', () => {
    const data = structuredClone(forecastLab);
    data.selection.changed = [];
    data.selection.changed_skus = 0;
    data.selection.models[1].median_wape = null;
    data.nested.aggregate.v1.weighted_bias = null;
    renderContent(data);

    expect(screen.queryByText(/SKUs que mudariam de modelo/)).not.toBeInTheDocument();
    expect(screen.getAllByText('Não disponível').length).toBeGreaterThanOrEqual(2);
    expect(screen.queryByText('0,0%')).not.toBeInTheDocument();
  });

  it('faixa: sem meses testados não inventa cobertura; com cobertura próxima do nominal não alarma; sem itens não lista', () => {
    const none = structuredClone(forecastLab);
    none.intervals.calibration = { ...none.intervals.calibration, tested_months: 0, hits: 0, coverage: null, median_relative_width: null };
    none.intervals.items = [];
    none.intervals.skus_with_band = 0;
    none.intervals.skus_without_band = 0;
    expect(coverageText(none.intervals)).toBe('Não houve meses suficientes para medir se a faixa acerta.');
    renderContent(none);
    expect(screen.queryByText(/Ver a faixa do próximo mês/)).not.toBeInTheDocument();

    const good = structuredClone(forecastLab);
    good.intervals.calibration = { ...good.intervals.calibration, hits: 120, coverage: 0.8 };
    expect(coverageText(good.intervals)).toBe('Fora da amostra, a faixa de 80% cobriu 80% dos 150 meses testados.');
  });

  it('quando todas as combinações atendem, o resumo diz isso sem alarme', () => {
    const data = structuredClone(forecastLab);
    data.sensitivity.cells = data.sensitivity.cells.map((cell) => ({ ...cell, all_met: true, relative_wape_gain: 0.1 }));
    data.sensitivity.summary = { ...data.sensitivity.summary, cells_all_met: 3, robust: true, min_relative_wape_gain: 0.1, max_relative_wape_gain: 0.1 };
    renderContent(data);

    expect(screen.getByText(/Critérios atendidos em/).textContent).toMatch(/3 de 3 combinações/);
    expect(screen.queryByText('Não atendidos')).not.toBeInTheDocument();
  });
});
