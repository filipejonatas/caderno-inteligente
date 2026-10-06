import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { PARTNER, SKU_OK, SKU_SHORT, forecasts, partnerRows, priorities } from './fixtures';
import { currentLocation, fail, mockApi, pending, renderApp } from './utils';

const rows = () => within(screen.getByRole('region', { name: /Fila operacional/ })).getAllByRole('row').slice(1).map((row) => within(row).getAllByRole('cell')[0].querySelector('strong')?.textContent);

describe('filtros sincronizados com a URL', () => {
  it('fila: lê a URL inicial e grava busca, confiança e limpeza', async () => {
    const user = userEvent.setup();
    mockApi();
    renderApp('/fila?familia=Fam%C3%ADlia+A&todos=1');
    await screen.findByRole('heading', { level: 2, name: 'Qual SKU analisar, o que fazer e quanto' });
    expect(screen.getByLabelText('Família')).toHaveValue('Família A');
    expect(rows()).toEqual(['TEST-001', 'TEST-003']);

    await user.type(screen.getByLabelText('Buscar'), 'agenda');
    expect(rows()).toEqual(['TEST-003']);
    expect(new URLSearchParams(currentLocation().split('?')[1]).get('busca')).toBe('agenda');

    await user.click(screen.getByRole('button', { name: 'Limpar filtros' }));
    expect(currentLocation()).toBe('/fila');
    await user.selectOptions(screen.getByLabelText('Confiança nos dados'), 'baixa');
    expect(currentLocation()).toBe('/fila?confianca=baixa');
    expect(rows()).toEqual([SKU_SHORT]);
  });

  it('fila: filtro de ação vindo da URL', async () => {
    const user = userEvent.setup();
    mockApi();
    renderApp('/fila?acao=investigar_dados');
    expect(await screen.findByText('de 3 SKUs')).toBeInTheDocument();
    expect(screen.getByLabelText('Ação')).toHaveValue('investigar_dados');
    const table = screen.getByRole('region', { name: /Fila operacional/ });
    expect(within(table).getByText(SKU_SHORT)).toBeInTheDocument();
    expect(within(table).queryByText(SKU_OK)).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Limpar filtros' }));
    expect(currentLocation()).toBe('/fila');
  });

  it('fila: por padrão mostra só o que pede atenção e o botão mostra todos', async () => {
    const user = userEvent.setup();
    mockApi();
    renderApp('/fila');
    // As três linhas do fixture pedem atenção (uma só tem prioridade, sem previsão); a contagem "N de M" fica sempre visível.
    expect(await screen.findByRole('heading', { name: 'SKUs que pedem atenção (3 de 3)' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Ver os 3 SKUs' }));
    expect(currentLocation()).toBe('/fila?todos=1');
    expect(screen.getByRole('button', { name: 'Só os que pedem atenção' })).toBeInTheDocument();
  });

  it('parceiro: com poucos vínculos não há filtro; com muitos, a ação vai para a URL e para a consulta da API', async () => {
    const user = userEvent.setup();
    mockApi();
    const { unmount } = renderApp(`/parceiros/${encodeURIComponent(PARTNER)}`);
    await screen.findByRole('region', { name: /Matriz comercial/ });
    expect(screen.queryByLabelText('Ação comercial')).not.toBeInTheDocument();
    unmount();
    const api = mockApi({ partnerSkus: { ...partnerRows, total: 30 } });
    renderApp(`/parceiros/${encodeURIComponent(PARTNER)}`);
    await user.selectOptions(await screen.findByLabelText('Ação comercial'), 'avaliar_reposicao');
    expect(currentLocation()).toBe(`/parceiros/${encodeURIComponent(PARTNER)}?acao=avaliar_reposicao`);
    await waitFor(() => expect(api.gets().some((path) => path.includes('/skus?') && path.includes('action=avaliar_reposicao'))).toBe(true));
  });
});

describe('estados de carregamento, erro, vazio e sucesso', () => {
  it('carregando: mostra estado acessível e status no topo', async () => {
    mockApi({ priorities: () => pending() });
    renderApp('/fila');
    expect(screen.getByRole('status', { name: 'Carregando dados' })).toBeInTheDocument();
    expect(screen.getByText('Carregando dados…')).toBeInTheDocument();
  });

  it('erro: mostra a mensagem da API e recupera com "Tentar novamente"', async () => {
    const user = userEvent.setup();
    let attempts = 0;
    mockApi({ priorities: () => (++attempts === 1 ? fail(503, 'Serviço de prioridades indisponível') : priorities), forecasts: () => (attempts <= 1 ? fail(503, 'Serviço de prioridades indisponível') : forecasts) });
    renderApp('/fila');
    expect(await screen.findByRole('heading', { name: 'Não foi possível carregar o painel' })).toBeInTheDocument();
    expect(screen.getByText('Serviço de prioridades indisponível')).toBeInTheDocument();
    expect(screen.getByText('Falha na consulta')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Tentar novamente' }));
    expect(await screen.findByText('TEST-003')).toBeInTheDocument();
    expect(screen.getByText('Dados carregados')).toBeInTheDocument();
  });

  it('erro de rede usa mensagem compreensível', async () => {
    const api = mockApi();
    api.fetchMock.mockRejectedValue(new TypeError('Failed to fetch'));
    renderApp('/validacao');
    expect(await screen.findByText(/Não foi possível conectar ao servidor/)).toBeInTheDocument();
  });

  it('vazio: prioridades e execuções explicam a ausência sem inventar dados', async () => {
    mockApi({ priorities: [], forecasts: [] });
    renderApp('/fila');
    expect(await screen.findByText('Nenhum SKU encontrado')).toBeInTheDocument();
  });

  it('vazio: comparação exige duas execuções', async () => {
    mockApi({ runs: [] });
    renderApp('/execucoes');
    expect(await screen.findByText('São necessárias duas execuções')).toBeInTheDocument();
    expect(screen.getByText('Nenhuma execução registrada')).toBeInTheDocument();
  });

  it('vazio: filtros sem resultado nas previsões oferecem limpeza', async () => {
    mockApi();
    renderApp('/fila?busca=nao-existe');
    expect(await screen.findByText('Nenhum SKU encontrado')).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: 'Limpar filtros' }).length).toBeGreaterThan(0);
  });

  it('falha só do contexto comercial não impede o detalhe operacional do SKU', async () => {
    mockApi({ commercial: fail(500, 'Análise comercial indisponível') });
    renderApp(`/skus/${SKU_OK}?tab=parceiros`);
    expect(await screen.findByRole('heading', { level: 2, name: SKU_OK })).toBeInTheDocument();
    expect(await screen.findByText('Análise comercial indisponível')).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Ação operacional sugerida' })).toBeInTheDocument();
  });

  it('SKU inexistente mostra erro com retorno', async () => {
    mockApi({ skuDetail: fail(404, 'SKU não encontrado') });
    renderApp('/skus/NAO-EXISTE');
    expect(await screen.findByText('SKU não encontrado')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Voltar' })).toBeInTheDocument();
  });
});

describe('recomendação com dados insuficientes', () => {
  it('detalhe não sugere quantidade, não mostra zero e mantém revisão humana', async () => {
    mockApi();
    renderApp(`/skus/${encodeURIComponent(SKU_SHORT)}`);
    expect(await screen.findByText('Dados insuficientes')).toBeInTheDocument();
    expect(screen.getAllByText('Investigar dados').length).toBeGreaterThan(0);
    expect(screen.getAllByText('São necessários pelo menos 6 meses de histórico para estimar demanda.').length).toBeGreaterThan(0);
    expect(screen.queryByText('Quantidade sugerida')).not.toBeInTheDocument();
    expect(screen.getByText('Revisão humana obrigatória')).toBeInTheDocument();
    expect(screen.getByText(/ausência de previsão não equivale a demanda zero/)).toBeInTheDocument();
  });

  it('lista de previsões marca dados insuficientes em vez de quantidade', async () => {
    mockApi();
    renderApp('/fila');
    const table = await screen.findByRole('region', { name: /Fila operacional/ });
    const row = within(table).getByText(SKU_SHORT).closest('tr')!;
    expect(within(row).getByText('Dados insuficientes')).toBeInTheDocument();
    expect(within(row).getByText('Investigar dados')).toBeInTheDocument();
    expect(within(row).queryByText('0')).not.toBeInTheDocument();
  });
});
