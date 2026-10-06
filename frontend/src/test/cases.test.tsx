import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { caseOverdueDays } from '../pages/shared';
import type { CaseItem } from '../types';
import { SKU_OK, cases as baseCases, system } from './fixtures';
import { currentLocation, fail, mockApi, renderApp } from './utils';

const item = (id: number, over: Partial<CaseItem> = {}): CaseItem => ({ ...baseCases[0], id, sku: `TEST-00${id}`, status: 'em_investigacao', owner: 'PCP', due_date: '2099-01-01', action: 'Ação anterior', note: 'Nota anterior', ...over });
const CASES = [
  item(1, { due_date: '2099-12-31' }),
  item(2, { status: 'concluido', due_date: '2020-01-01' }),
  item(3, { due_date: '2020-01-01', owner: '' }),
  item(4, { status: 'novo', owner: 'Comercial', due_date: '' }),
];
const rows = () => within(screen.getByRole('region', { name: /Fila de casos/ })).getAllByRole('row').slice(1).filter((row) => within(row).queryAllByRole('cell').length === 5);
const skuOf = (row: HTMLElement) => within(row).getAllByRole('cell')[0].querySelector('strong')?.textContent;

describe('casos: atraso', () => {
  it('só caso aberto com prazo no passado está vencido', () => {
    expect(caseOverdueDays({ status: 'novo', due_date: '2026-10-01' }, '2026-10-06')).toBe(5);
    expect(caseOverdueDays({ status: 'novo', due_date: '2026-10-06' }, '2026-10-06')).toBeNull();
    expect(caseOverdueDays({ status: 'concluido', due_date: '2020-01-01' }, '2026-10-06')).toBeNull();
    expect(caseOverdueDays({ status: 'novo', due_date: '' }, '2026-10-06')).toBeNull();
  });

  it('destaca com texto e ordena vencidos, abertos por prazo e concluídos', async () => {
    mockApi({ cases: CASES });
    renderApp('/casos');
    await screen.findByRole('region', { name: /Fila de casos/ });
    expect(rows().map(skuOf)).toEqual(['TEST-003', 'TEST-001', 'TEST-004', 'TEST-002']);
    expect(within(rows()[0]).getByText(/Vencido há \d+ dias/)).toBeInTheDocument();
    expect(within(rows()[3]).queryByText(/Vencido/)).not.toBeInTheDocument();
    expect(screen.getByText(/vencidos/, { selector: 'p' })).toHaveTextContent('1 vencidos');
  });
});

describe('casos: filtros', () => {
  it('status e responsável vêm da URL, filtram e podem ser limpos', async () => {
    const user = userEvent.setup();
    mockApi({ cases: CASES });
    renderApp('/casos?status=novo');
    await screen.findByRole('region', { name: /Fila de casos/ });
    expect(rows().map(skuOf)).toEqual(['TEST-004']);
    await user.click(screen.getByRole('button', { name: 'Limpar filtros' }));
    expect(currentLocation()).toBe('/casos');
    await user.selectOptions(screen.getByLabelText('Responsável', { selector: 'select' }), 'Sem responsável');
    expect(currentLocation()).toBe('/casos?responsavel=__sem_responsavel__');
    expect(rows().map(skuOf)).toEqual(['TEST-003']);
  });

  it('filtro sem resultado explica e oferece limpeza', async () => {
    mockApi({ cases: CASES });
    renderApp('/casos?status=aguardando_comercial');
    expect(await screen.findByText('Nenhum caso neste filtro')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Limpar filtros' })).toBeInTheDocument();
  });
});

describe('casos: atualizar', () => {
  it('edita status, responsável e prazo, preserva ação e nota e anuncia o sucesso', async () => {
    const user = userEvent.setup();
    const api = mockApi({ cases: CASES });
    renderApp('/casos');
    await user.click(await screen.findByRole('button', { name: 'Editar caso #1 do SKU TEST-001' }));
    const form = screen.getByRole('form', { name: 'Editar caso #1 do SKU TEST-001' });
    await user.selectOptions(within(form).getByLabelText('Status do caso'), 'concluido');
    await user.clear(within(form).getByLabelText('Responsável pelo caso'));
    await user.type(within(form).getByLabelText('Responsável pelo caso'), 'Logística');
    await user.click(within(form).getByRole('button', { name: 'Salvar alterações' }));
    const put = await waitFor(() => { const call = api.calls.find((entry) => entry.method === 'PUT'); expect(call).toBeTruthy(); return call!; });
    expect(put.path).toBe('/api/cases/1');
    expect(put.body).toEqual({ status: 'concluido', owner: 'Logística', due_date: '2099-12-31', action: 'Ação anterior', note: 'Nota anterior' });
    expect(await screen.findByText('Caso #1 do SKU TEST-001 atualizado.')).toBeInTheDocument();
    expect(screen.getByText('Caso #1 do SKU TEST-001 atualizado.').closest('[aria-live]')).toHaveAttribute('aria-live', 'polite');
    expect(screen.queryByRole('form', { name: /Editar caso/ })).not.toBeInTheDocument();
  });

  it('"Concluir" fecha o caso em um clique e só existe para casos abertos', async () => {
    const user = userEvent.setup();
    const api = mockApi({ cases: CASES });
    renderApp('/casos');
    await screen.findByRole('region', { name: /Fila de casos/ });
    expect(screen.queryByRole('button', { name: 'Concluir caso #2 do SKU TEST-002' })).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Concluir caso #4 do SKU TEST-004' }));
    await waitFor(() => expect(api.calls.find((entry) => entry.method === 'PUT')?.body).toMatchObject({ status: 'concluido', owner: 'Comercial' }));
  });

  it('erro do servidor mantém a lista e os valores digitados, avisa com role="alert" e permite tentar de novo', async () => {
    const user = userEvent.setup();
    let attempts = 0;
    const api = mockApi({ cases: CASES, 'PUT case': () => (++attempts === 1 ? fail(422, 'Prazo inválido') : { status: 'updated' }) });
    renderApp('/casos');
    await user.click(await screen.findByRole('button', { name: 'Editar caso #1 do SKU TEST-001' }));
    const form = screen.getByRole('form', { name: 'Editar caso #1 do SKU TEST-001' });
    await user.clear(within(form).getByLabelText('Responsável pelo caso'));
    await user.type(within(form).getByLabelText('Responsável pelo caso'), 'Logística');
    await user.click(within(form).getByRole('button', { name: 'Salvar alterações' }));
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Prazo inválido');
    expect(alert).toHaveTextContent('Os valores anteriores continuam valendo');
    expect(rows()).toHaveLength(4);
    expect(within(screen.getByRole('form', { name: /Editar caso #1/ })).getByLabelText('Responsável pelo caso')).toHaveValue('Logística');
    await user.click(within(alert).getByRole('button', { name: 'Tentar novamente' }));
    expect(await screen.findByText('Caso #1 do SKU TEST-001 atualizado.')).toBeInTheDocument();
    expect(api.calls.filter((entry) => entry.method === 'PUT')).toHaveLength(2);
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('salvar um caso não bloqueia os demais', async () => {
    const user = userEvent.setup();
    let release: (value: unknown) => void = () => {};
    const gate = new Promise((resolve) => { release = resolve; });
    mockApi({ cases: CASES, 'PUT case': (url: URL) => (url.pathname.endsWith('/1') ? gate.then(() => ({ status: 'updated' })) : { status: 'updated' }) });
    renderApp('/casos');
    await user.click(await screen.findByRole('button', { name: 'Concluir caso #1 do SKU TEST-001' }));
    expect(screen.getByRole('button', { name: 'Editar caso #1 do SKU TEST-001' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Editar caso #3 do SKU TEST-003' })).toBeEnabled();
    expect(screen.getByRole('button', { name: 'Concluir caso #4 do SKU TEST-004' })).toBeEnabled();
    release(null);
    await screen.findByText('Caso #1 do SKU TEST-001 atualizado.');
  });

  it('somente leitura desabilita a edição com explicação', async () => {
    mockApi({ cases: CASES, system: { ...system, write_enabled: false } });
    renderApp('/casos');
    await waitFor(() => expect(screen.getByRole('button', { name: 'Editar caso #1 do SKU TEST-001' })).toBeDisabled());
    expect(screen.getByRole('button', { name: 'Concluir caso #1 do SKU TEST-001' })).toBeDisabled();
    expect(screen.getAllByRole('note').some((note) => /Edição desabilitada/.test(note.textContent ?? ''))).toBe(true);
  });
});

describe('Acompanhamento: entrada e SKU explícito', () => {
  it('o grupo do menu abre em Casos e lista Casos antes do histórico', async () => {
    mockApi();
    renderApp('/decisoes');
    await screen.findByRole('heading', { level: 2, name: 'Histórico de decisões' });
    const menu = within(screen.getByRole('navigation', { name: 'Navegação principal' })).getByRole('link', { name: /Acompanhamento/ });
    expect(menu).toHaveAttribute('href', '/casos');
    expect(menu).toHaveAttribute('aria-current', 'page');
    const tabs = within(screen.getByRole('navigation', { name: 'Seções desta área' })).getAllByRole('link').map((link) => link.textContent);
    expect(tabs).toEqual(['Casos', 'Histórico de decisões']);
  });

  it('decisão sem SKU na URL não escolhe um SKU em silêncio e exige escolha', async () => {
    const user = userEvent.setup();
    const api = mockApi();
    renderApp('/decisoes');
    const sku = await screen.findByLabelText('SKU');
    expect(sku).toHaveValue('');
    await user.click(screen.getByRole('button', { name: 'Registrar decisão' }));
    expect(api.calls.some((call) => call.method === 'POST')).toBe(false);
    await user.selectOptions(sku, SKU_OK);
    await user.click(screen.getByRole('button', { name: 'Registrar decisão' }));
    expect(await screen.findByText('Decisão registrada com sucesso.')).toBeInTheDocument();
    expect(api.calls.find((call) => call.method === 'POST')?.body).toMatchObject({ sku: SKU_OK });
  });

  it('com ?sku= o SKU vem do detalhe e fica visível para confirmação', async () => {
    mockApi();
    renderApp(`/decisoes?sku=${SKU_OK}`);
    expect(await screen.findByLabelText('SKU')).toHaveValue(SKU_OK);
  });

  it('criar caso também exige a escolha do SKU', async () => {
    const user = userEvent.setup();
    const api = mockApi();
    renderApp('/casos');
    const sku = await screen.findByLabelText('SKU');
    expect(sku).toHaveValue('');
    await user.click(screen.getByRole('button', { name: 'Criar caso' }));
    expect(api.calls.some((call) => call.method === 'POST')).toBe(false);
  });

  it('erro ao registrar decisão é anunciado com role="alert" e o formulário mantém os dados', async () => {
    const user = userEvent.setup();
    mockApi({ 'POST feedback': fail(500, 'Servidor indisponível') });
    renderApp(`/decisoes?sku=${SKU_OK}`);
    await user.type(await screen.findByLabelText('Observação'), 'Texto digitado');
    await user.click(screen.getByRole('button', { name: 'Registrar decisão' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Servidor indisponível');
    expect(screen.getByLabelText('Observação')).toHaveValue('Texto digitado');
  });
});
