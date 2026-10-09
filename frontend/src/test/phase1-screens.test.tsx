import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { PARTNER, SKU_OK, SKU_SHORT, forecasts, priorities, priority, revenueForecast, revenueOk } from './fixtures';
import { currentLocation, fail, mockApi, renderApp } from './utils';

const many = <T extends { sku: string }>(base: T, count: number) => Array.from({ length: count }, (_, index) => ({ ...base, sku: `GEN-${String(index + 1).padStart(3, '0')}` }));

describe('Início como painel', () => {
  it('mantém o primeiro SKU no topo e monta indicadores, ruptura, oportunidades e faturamento abaixo', async () => {
    mockApi();
    renderApp('/');
    const focus = (await screen.findByText('Primeiro da fila · posição 1')).closest('article') as HTMLElement;
    const indicators = screen.getByLabelText('Indicadores de ruptura');
    // A resposta "o que olho primeiro" vem antes do painel.
    expect(focus.compareDocumentPosition(indicators) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(within(indicators).getByText('Risco de ruptura').nextSibling).toHaveTextContent('2 SKUs');
    expect(within(indicators).getByText('Abaixo do prazo de produção').nextSibling).toHaveTextContent('2');
    expect(within(indicators).getByText('Abaixo do estoque de segurança').nextSibling).toHaveTextContent('1');

    const rupture = screen.getByRole('heading', { level: 3, name: 'SKUs com risco de ruptura' }).closest('section') as HTMLElement;
    expect(within(rupture).getByRole('link', { name: 'Ver na fila' })).toHaveAttribute('href', '/fila?sinal=ruptura');
    expect(within(rupture).getByText(SKU_OK)).toBeInTheDocument();

    // O bloco tem o mesmo título enquanto carrega: espera o link, que só existe com os dados.
    const seeAll = await screen.findByRole('link', { name: 'Ver todas' });
    expect(seeAll).toHaveAttribute('href', '/parceiros');
    const opportunities = seeAll.closest('section') as HTMLElement;
    expect(within(opportunities).getByRole('link', { name: 'Parceiro sintético' })).toHaveAttribute('href', `/parceiros/${encodeURIComponent(PARTNER)}`);

    const toFinance = await screen.findByRole('link', { name: 'Ver o financeiro' });
    expect(toFinance).toHaveAttribute('href', '/faturamento');
    const revenue = toFinance.closest('section') as HTMLElement;
    expect(within(revenue).getByRole('heading', { level: 3, name: 'Faturamento observado e estimado' })).toBeInTheDocument();
    expect(within(revenue).getByRole('img', { name: /observado e estimado/ })).toBeInTheDocument();
  });

  it('a lista de ruptura mostra só SKUs com sinal de ruptura, no máximo cinco', async () => {
    const rows = [...priorities, ...Array.from({ length: 6 }, (_, index) => priority(`RUP-${index + 4}`, index + 4)), priority('SEM-RUPTURA', 10, { reasons: [{ code: 'EXCESS_COVERAGE', description: 'Excesso.', severity: 'média' }] })];
    mockApi({ priorities: rows });
    renderApp('/');
    const rupture = (await screen.findByRole('heading', { level: 3, name: 'SKUs com risco de ruptura' })).closest('section') as HTMLElement;
    expect(within(rupture).getAllByRole('row')).toHaveLength(1 + 5);
    expect(within(rupture).queryByText('SEM-RUPTURA')).not.toBeInTheDocument();
  });

  it('falha do faturamento ou das oportunidades não derruba o restante do Início', async () => {
    const api = mockApi({ revenueForecast: fail(500, 'Erro interno.'), commercial: fail(503, 'Serviço indisponível.') });
    renderApp('/');
    expect(await screen.findByText('Faturamento observado e estimado: indisponível')).toBeInTheDocument();
    expect(await screen.findByText('Onde repor primeiro: indisponível')).toBeInTheDocument();
    expect(screen.getByText('Primeiro da fila · posição 1')).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 3, name: 'SKUs com risco de ruptura' })).toBeInTheDocument();
    expect(screen.queryByText('Não foi possível carregar o painel')).not.toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: 'Tentar novamente' })).toHaveLength(2);
    expect(api.gets().some((path) => path.startsWith('/api/commercial-recommendations?') && path.includes('action=avaliar_reposicao'))).toBe(true);
  });
});

describe('Fila: filtro de risco de ruptura', () => {
  it('?sinal=ruptura mostra só os SKUs com sinal de ruptura e limpa com o botão', async () => {
    const user = userEvent.setup();
    mockApi({ priorities: [priorities[0], { ...priorities[1], reasons: [{ code: 'EXCESS_COVERAGE', description: 'Excesso.', severity: 'média' }] }] });
    renderApp('/fila?sinal=ruptura');
    const table = await screen.findByRole('region', { name: /Fila operacional; role horizontalmente/ });
    expect(within(table).getByText(SKU_OK)).toBeInTheDocument();
    expect(within(table).queryByText(SKU_SHORT)).not.toBeInTheDocument();
    expect(screen.getByLabelText('Sinal')).toHaveValue('ruptura');
    await user.click(screen.getByRole('button', { name: 'Limpar filtros' }));
    expect(currentLocation()).toBe('/fila');
  });
});

describe('Financeiro: filtros no topo e 10 SKUs por página', () => {
  it('os filtros vêm antes do cartão de resumo', async () => {
    mockApi();
    renderApp('/faturamento');
    const card = (await screen.findByRole('heading', { level: 3, name: 'Faturamento estimado' })).closest('section') as HTMLElement;
    const filters = screen.getByRole('search', { name: 'Filtrar o faturamento previsto' });
    expect(filters.compareDocumentPosition(card) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('pagina de 10 em 10 e volta à primeira página quando o filtro muda', async () => {
    const user = userEvent.setup();
    mockApi({ revenueForecast: { ...revenueForecast, items: many(revenueOk, 23) } });
    renderApp('/faturamento');
    const table = await screen.findByRole('region', { name: /Faturamento estimado por SKU/ });
    expect(within(table).getAllByRole('row')).toHaveLength(1 + 10);
    const pages = screen.getByRole('navigation', { name: 'Páginas da estimativa por SKU' });
    expect(within(pages).getByText('Página 1 de 3')).toBeInTheDocument();
    expect(within(pages).getByRole('button', { name: 'Anterior' })).toBeDisabled();
    await user.click(within(pages).getByRole('button', { name: 'Próxima' }));
    await user.click(within(pages).getByRole('button', { name: 'Próxima' }));
    expect(within(pages).getByText('Página 3 de 3')).toBeInTheDocument();
    expect(within(screen.getByRole('region', { name: /Faturamento estimado por SKU/ })).getAllByRole('row')).toHaveLength(1 + 3);
    expect(within(pages).getByRole('button', { name: 'Próxima' })).toBeDisabled();
    await user.type(screen.getByLabelText('Buscar'), 'GEN-023');
    await waitFor(() => expect(within(screen.getByRole('region', { name: /Faturamento estimado por SKU/ })).getAllByRole('row')).toHaveLength(1 + 1));
    expect(screen.queryByRole('navigation', { name: 'Páginas da estimativa por SKU' })).not.toBeInTheDocument();
  });
});

describe('Início: setas entre os 3 primeiros da fila', () => {
  it('avança, volta de forma circular, aceita as setas do teclado e abre o SKU mostrado', async () => {
    const user = userEvent.setup();
    mockApi();
    renderApp('/');
    const card = (await screen.findByText('Primeiro da fila · posição 1')).closest('article') as HTMLElement;
    const next = within(card).getByRole('button', { name: 'Próximo SKU da fila' });
    const previous = within(card).getByRole('button', { name: 'SKU anterior da fila' });
    expect(within(card).getByText('1 de 3')).toBeInTheDocument();

    await user.click(next);
    expect(within(card).getByText('Posição 2 da fila')).toBeInTheDocument();
    expect(within(card).getByRole('heading', { level: 3 })).toHaveTextContent(SKU_SHORT);
    expect(within(card).getByRole('status')).toHaveTextContent(`Mostrando 2 de 3: ${SKU_SHORT}`);
    await user.click(next);
    expect(within(card).getByRole('heading', { level: 3 })).toHaveTextContent('TEST-003');
    // Circular: depois do terceiro volta ao primeiro, e do primeiro "anterior" vai ao terceiro.
    await user.click(next);
    expect(within(card).getByText('Primeiro da fila · posição 1')).toBeInTheDocument();
    await user.click(previous);
    expect(within(card).getByText('3 de 3')).toBeInTheDocument();

    // Setas do teclado com o foco na navegação.
    previous.focus();
    await user.keyboard('{ArrowLeft}');
    expect(within(card).getByText('2 de 3')).toBeInTheDocument();
    await user.keyboard('{ArrowRight}');
    expect(within(card).getByText('3 de 3')).toBeInTheDocument();
    await user.keyboard('{ArrowRight}{ArrowRight}');
    expect(within(card).getByText('2 de 3')).toBeInTheDocument();

    // O botão principal abre o SKU que está no cartão.
    await user.click(within(card).getByRole('button', { name: `Abrir evidências de ${SKU_SHORT}` }));
    expect(currentLocation()).toBe(`/skus/${encodeURIComponent(SKU_SHORT)}`);
  });
});

describe('Planejamento: família na barra e 10 SKUs por página', () => {
  it('pagina de 10 em 10 só com troca de página e volta à primeira quando a família muda', async () => {
    const user = userEvent.setup();
    mockApi({ forecasts: [...forecasts, ...many(forecasts[0], 23)] });
    renderApp('/fila?todos=1');
    const queue = () => screen.getByRole('region', { name: /Fila operacional/ });
    await screen.findByRole('region', { name: /Fila operacional/ });
    // 3 SKUs do ranking + 23 gerados = 26: páginas de 10, 10 e 6.
    await waitFor(() => expect(within(queue()).getAllByRole('row')).toHaveLength(1 + 10));
    expect(screen.queryByRole('button', { name: /Ver mais/ })).not.toBeInTheDocument();
    const pages = screen.getByRole('navigation', { name: 'Páginas da fila operacional' });
    expect(within(pages).getByText('Página 1 de 3')).toBeInTheDocument();
    await user.click(within(pages).getByRole('button', { name: 'Próxima' }));
    await user.click(within(pages).getByRole('button', { name: 'Próxima' }));
    expect(within(pages).getByText('Página 3 de 3')).toBeInTheDocument();
    expect(within(queue()).getAllByRole('row')).toHaveLength(1 + 6);

    // Família fica na barra principal, fora de "Mais filtros", e o filtro volta à página 1.
    const family = screen.getByLabelText('Família');
    expect(family.closest('details')).toBeNull();
    await user.selectOptions(family, 'Família B');
    expect(currentLocation()).toBe('/fila?todos=1&familia=Fam%C3%ADlia+B');
    await waitFor(() => expect(within(queue()).getAllByRole('row')).toHaveLength(1 + 1));
    expect(within(queue()).getByText(SKU_SHORT)).toBeInTheDocument();
    expect(screen.queryByRole('navigation', { name: 'Páginas da fila operacional' })).not.toBeInTheDocument();
  });
});

describe('Lista de SKUs no menu', () => {
  it('o menu leva à lista, que abre a página do SKU e mantém o menu ativo', async () => {
    const user = userEvent.setup();
    mockApi();
    renderApp('/');
    const menu = within(screen.getByRole('navigation', { name: 'Navegação principal' }));
    await user.click(menu.getByRole('link', { name: 'SKUs' }));
    expect(await screen.findByRole('heading', { level: 2, name: 'Todos os SKUs' })).toBeInTheDocument();
    expect(menu.getByRole('link', { name: 'SKUs' })).toHaveAttribute('aria-current', 'page');
    const table = screen.getByRole('region', { name: /Lista de SKUs/ });
    expect(within(table).getAllByRole('row')).toHaveLength(1 + forecasts.length);
    await user.click(within(table).getByRole('link', { name: `Abrir ${SKU_OK}` }));
    expect(await screen.findByRole('heading', { level: 2, name: SKU_OK })).toBeInTheDocument();
    expect(currentLocation()).toBe(`/skus/${SKU_OK}`);
    expect(menu.getByRole('link', { name: 'SKUs' })).toHaveAttribute('aria-current', 'page');
  });

  it('busca e família filtram pela URL, e a lista pagina de 10 em 10', async () => {
    const user = userEvent.setup();
    mockApi({ forecasts: [...forecasts, ...many(forecasts[0], 12)] });
    renderApp('/skus?familia=Fam%C3%ADlia+B');
    const filtered = await screen.findByRole('region', { name: /Lista de SKUs/ });
    expect(within(filtered).getByText(SKU_SHORT)).toBeInTheDocument();
    expect(within(filtered).getAllByRole('row')).toHaveLength(1 + 1);
    await user.click(screen.getByRole('button', { name: 'Limpar filtros' }));
    expect(currentLocation()).toBe('/skus');
    const pages = screen.getByRole('navigation', { name: 'Páginas da lista de SKUs' });
    expect(within(pages).getByText('Página 1 de 2')).toBeInTheDocument();
    await user.type(screen.getByLabelText('Buscar'), 'GEN-012');
    expect(currentLocation()).toBe('/skus?busca=GEN-012');
    expect(within(screen.getByRole('region', { name: /Lista de SKUs/ })).getAllByRole('row')).toHaveLength(1 + 1);
  });

  it('falha da API mostra o erro com nova tentativa', async () => {
    mockApi({ forecasts: fail(500, 'Erro interno.') });
    renderApp('/skus');
    expect(await screen.findByText('Erro interno.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Tentar novamente/ })).toBeInTheDocument();
  });
});
