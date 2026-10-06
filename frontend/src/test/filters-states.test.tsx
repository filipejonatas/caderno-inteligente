import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { PARTNER, SKU_OK, SKU_SHORT, priorities } from './fixtures';
import { currentLocation, fail, mockApi, pending, renderApp } from './utils';

const rows = () => screen.getAllByRole('row').slice(1).map((row) => within(row).getAllByRole('cell')[1].querySelector('strong')?.textContent);

describe('filtros sincronizados com a URL', () => {
  it('prioridades: lê a URL inicial e grava busca, confiança e limpeza', async () => {
    const user = userEvent.setup();
    mockApi();
    renderApp('/prioridades?familia=Fam%C3%ADlia+A');
    await screen.findByRole('heading', { level: 2, name: 'Em que ordem analisar os SKUs' });
    expect(screen.getByLabelText('Família')).toHaveValue('Família A');
    expect(rows()).toEqual(['TEST-001', 'TEST-003']);

    await user.type(screen.getByLabelText('Buscar'), 'agenda');
    expect(rows()).toEqual(['TEST-003']);
    expect(new URLSearchParams(currentLocation().split('?')[1]).get('busca')).toBe('agenda');

    await user.click(screen.getByRole('button', { name: 'Limpar filtros' }));
    expect(currentLocation()).toBe('/prioridades');
    await user.selectOptions(screen.getByLabelText('Confiança'), 'baixa');
    expect(currentLocation()).toBe('/prioridades?confianca=baixa');
    expect(rows()).toEqual([SKU_SHORT]);
  });

  it('previsões: filtro de ação vindo da URL e checkbox de atenção', async () => {
    const user = userEvent.setup();
    mockApi();
    renderApp('/previsoes?acao=investigar_dados');
    expect(await screen.findByText('de 2 SKUs')).toBeInTheDocument();
    expect(screen.getByLabelText('Ação')).toHaveValue('investigar_dados');
    const table = screen.getByRole('region', { name: /Previsões/ });
    expect(within(table).getByText(SKU_SHORT)).toBeInTheDocument();
    expect(within(table).queryByText(SKU_OK)).not.toBeInTheDocument();
    await user.click(screen.getByLabelText('Somente itens com atenção'));
    expect(currentLocation()).toContain('atencao=1');
  });

  it('parceiro: filtro de qualidade vai para a URL e para a consulta da API', async () => {
    const user = userEvent.setup();
    const api = mockApi();
    renderApp(`/parceiros/${encodeURIComponent(PARTNER)}`);
    await user.selectOptions(await screen.findByLabelText('Qualidade'), 'insufficient');
    expect(currentLocation()).toBe(`/parceiros/${encodeURIComponent(PARTNER)}?qualidade=insufficient`);
    await waitFor(() => expect(api.gets().some((path) => path.includes('/skus?') && path.includes('data_quality=insufficient'))).toBe(true));
  });
});

describe('estados de carregamento, erro, vazio e sucesso', () => {
  it('carregando: mostra estado acessível e status no topo', async () => {
    mockApi({ priorities: () => pending() });
    renderApp('/prioridades');
    expect(screen.getByRole('status', { name: 'Carregando dados' })).toBeInTheDocument();
    expect(screen.getByText('Carregando dados…')).toBeInTheDocument();
  });

  it('erro: mostra a mensagem da API e recupera com "Tentar novamente"', async () => {
    const user = userEvent.setup();
    let attempts = 0;
    mockApi({ priorities: () => (++attempts === 1 ? fail(503, 'Serviço de prioridades indisponível') : priorities) });
    renderApp('/prioridades');
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
    mockApi({ priorities: [] });
    renderApp('/prioridades');
    expect(await screen.findByText('Nenhuma prioridade encontrada')).toBeInTheDocument();
  });

  it('vazio: comparação exige duas execuções', async () => {
    mockApi({ runs: [] });
    renderApp('/execucoes');
    expect(await screen.findByText('São necessárias duas execuções')).toBeInTheDocument();
    expect(screen.getByText('Nenhuma execução registrada')).toBeInTheDocument();
  });

  it('vazio: filtros sem resultado nas previsões oferecem limpeza', async () => {
    mockApi();
    renderApp('/previsoes?busca=nao-existe');
    expect(await screen.findByText('Nenhum SKU encontrado')).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: 'Limpar filtros' }).length).toBeGreaterThan(0);
  });

  it('falha só do contexto comercial não impede o detalhe operacional do SKU', async () => {
    mockApi({ commercial: fail(500, 'Análise comercial indisponível') });
    renderApp(`/skus/${SKU_OK}`);
    expect(await screen.findByRole('heading', { level: 2, name: SKU_OK })).toBeInTheDocument();
    expect(await screen.findByText('Análise comercial indisponível')).toBeInTheDocument();
    expect(screen.getByText('Demanda e atendimento')).toBeInTheDocument();
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
    renderApp('/previsoes');
    const table = await screen.findByRole('region', { name: /Previsões/ });
    const row = within(table).getByText(SKU_SHORT).closest('tr')!;
    expect(within(row).getByText('Dados insuficientes')).toBeInTheDocument();
    expect(within(row).getByText('Investigar dados')).toBeInTheDocument();
    expect(within(row).queryByText('0')).not.toBeInTheDocument();
  });
});
