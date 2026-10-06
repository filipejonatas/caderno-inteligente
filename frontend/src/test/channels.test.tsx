import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { backlogText, trendLabel } from '../components/ChannelViews';
import { glossary } from '../pages/shared';
import { CHANNEL, channelRows, directChannelDetail } from './fixtures';
import { fail, mockApi, renderApp } from './utils';

const encoded = encodeURIComponent(CHANNEL);

describe('formatos dos canais', () => {
  it('rotula tendência com sinal e carteira sem inventar zero', () => {
    expect(trendLabel('crescente', 0.15)).toBe('Crescente (+15,0%)');
    expect(trendLabel('decrescente', -0.185)).toBe('Decrescente (−18,5%)');
    expect(trendLabel('indeterminada', null)).toBe('Indeterminada');
    expect(backlogText(0, null)).toBe('Nenhum pedido aberto');
    expect(backlogText(1, 100)).toBe('1 pedido · 100 un.');
    expect(backlogText(7, 2464)).toBe('7 pedidos · 2.464 un.');
  });

  it('o "?" avisa que a visão é de faturamento, sem estoque por canal, e que a sugestão é humana', () => {
    expect(glossary.canais_diretos.text).toMatch(/faturamento/);
    expect(glossary.canais_diretos.text).toMatch(/não há estoque por canal/);
    expect(glossary.canais_diretos.text).toMatch(/nunca como venda zero/);
    expect(glossary.canais_diretos.text).toMatch(/revisão humana/);
  });
});

describe('Parceiros: aba Canais diretos', () => {
  it('lista os canais com faturamento observado, tendência, carteira e link para o detalhe', async () => {
    const api = mockApi();
    renderApp('/parceiros?aba=diretos');
    const table = await screen.findByRole('region', { name: /Canais diretos; role horizontalmente/ });
    const row = within(table).getByText('E-commerce próprio').closest('tr') as HTMLElement;
    expect(within(row).getByText(/R\$\s?11\.606\.120/)).toBeInTheDocument();
    expect(within(row).getByText('Observado')).toBeInTheDocument();
    expect(within(row).getByText('Estável (+1,1%)')).toBeInTheDocument();
    expect(within(row).getByText('7 pedidos · 2.464 un.')).toBeInTheDocument();
    expect(within(row).getByRole('link', { name: /Abrir canal E-commerce próprio/ })).toHaveAttribute('href', '/canais/E-commerce');
    expect(screen.getByText(/somam/).textContent).toContain('68%');
    const tabs = screen.getByRole('navigation', { name: 'Visões de parceiros' });
    expect(within(tabs).getByRole('link', { name: 'Canais diretos' })).toHaveAttribute('aria-current', 'page');
    expect(screen.queryByRole('search', { name: 'Filtrar parceiros' })).not.toBeInTheDocument();
    expect(api.gets().some((path) => path.startsWith('/api/commercial-recommendations'))).toBe(false);
    expect(api.gets()).toContain('/api/direct-channels');
  });

  it('a aba padrão não busca os canais diretos', async () => {
    const api = mockApi();
    renderApp('/parceiros');
    await screen.findByRole('heading', { level: 2, name: 'Onde há oportunidade de reposição' });
    await waitFor(() => expect(api.gets().some((path) => path.startsWith('/api/commercial-recommendations'))).toBe(true));
    expect(api.gets()).not.toContain('/api/direct-channels');
  });

  it('falha da análise mostra erro com nova tentativa', async () => {
    mockApi({ directChannels: fail(500, 'Erro interno.') });
    renderApp('/parceiros?aba=diretos');
    expect(await screen.findByText('Erro interno.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Tentar novamente/ })).toBeInTheDocument();
  });
});

describe('Detalhe do canal', () => {
  it('mostra o canal, o gráfico observado e uma linha por SKU com valor ausente tratado como "não vendido"', async () => {
    mockApi();
    renderApp(`/canais/${encoded}`);
    expect(await screen.findByRole('heading', { level: 2, name: 'Loja própria' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 1, name: 'Detalhe do canal' })).toBeInTheDocument();
    expect(screen.getByRole('img', { name: /Faturamento mensal observado de Loja própria/ })).toBeInTheDocument();
    expect(screen.queryByText('Estimativa')).not.toBeInTheDocument();
    const table = screen.getByRole('region', { name: /SKUs do canal; role horizontalmente/ });
    expect(within(table).getAllByRole('row')).toHaveLength(1 + channelRows.length);
    const missing = within(table).getByText('CH-003').closest('tr') as HTMLElement;
    expect(within(missing).getByText('Sem faturamento no canal')).toBeInTheDocument();
    expect(within(missing).queryByText(/R\$/)).not.toBeInTheDocument();
    expect(within(missing).getByText('Ampliar mix')).toBeInTheDocument();
    const growing = within(table).getByText('CH-002').closest('tr') as HTMLElement;
    expect(within(growing).getByText('Crescente (+15,0%)')).toBeInTheDocument();
    expect(within(growing).getByText('300 un.')).toBeInTheDocument();
    expect(within(growing).getByRole('link', { name: 'CH-002' })).toHaveAttribute('href', '/skus/CH-002');
  });

  it('a sugestão explica o motivo no tooltip e exige revisão humana', async () => {
    mockApi();
    renderApp(`/canais/${encoded}`);
    const table = await screen.findByRole('region', { name: /SKUs do canal; role horizontalmente/ });
    const tips = within(table).getAllByRole('tooltip', { hidden: true }).map((node) => node.textContent ?? '');
    expect(tips.some((text) => text.includes('Produto ativo sem nenhum faturamento neste canal') && text.includes('Revisão humana obrigatória'))).toBe(true);
  });

  it('o filtro de sinal vai para a URL e para a API', async () => {
    const user = userEvent.setup();
    const api = mockApi({ directChannel: directChannelDetail });
    renderApp(`/canais/${encoded}`);
    const select = await screen.findByLabelText('Sinal');
    await user.selectOptions(select, 'NOT_SOLD');
    await waitFor(() => expect(api.gets().some((path) => path.includes('signal=NOT_SOLD'))).toBe(true));
    expect(select).toHaveValue('NOT_SOLD');
  });

  it('canal inexistente mostra o erro e permite tentar de novo', async () => {
    mockApi({ directChannel: fail(404, 'Canal direto não encontrado') });
    renderApp('/canais/Inexistente');
    expect(await screen.findByText('Canal direto não encontrado')).toBeInTheDocument();
  });

  it('mantém o menu Parceiros ativo e oferece o caminho de volta', async () => {
    mockApi();
    renderApp(`/canais/${encoded}`);
    await screen.findByRole('heading', { level: 2, name: 'Loja própria' });
    expect(within(screen.getByRole('navigation', { name: 'Navegação principal' })).getByRole('link', { name: /Parceiros/ })).toHaveAttribute('aria-current', 'page');
    expect(screen.getByRole('link', { name: 'Voltar aos canais' })).toHaveAttribute('href', '/parceiros?aba=diretos');
  });
});

describe('Dados da planilha: achados entre abas', () => {
  it('mostra os dois achados com evidência numérica e tratamento', async () => {
    mockApi();
    renderApp('/qualidade');
    const table = await screen.findByRole('region', { name: 'Achados entre abas que afetam os canais' });
    expect(within(table).getByText('Cobertura dos canais diretos sem Sell_Out')).toBeInTheDocument();
    expect(within(table).getByText('Declaram cobertura completa; Sell_Out tem 0 linhas.')).toBeInTheDocument();
    expect(within(table).getByText('0 de 600 pares iguais; Sell_In ≈ 2,79× o faturado.')).toBeInTheDocument();
    expect(within(table).getAllByText('Não reconciliado', { exact: false }).length).toBeGreaterThan(0);
    expect(within(table).getAllByRole('tooltip', { hidden: true }).some((node) => node.textContent?.includes('Não reconciliado.'))).toBe(true);
  });

  it('falha dos achados não afeta o restante da página de qualidade', async () => {
    mockApi({ channelFindings: fail(500, 'Erro interno.') });
    renderApp('/qualidade');
    expect(await screen.findByRole('heading', { level: 2, name: 'Posso confiar na planilha?' })).toBeInTheDocument();
    expect(await screen.findByText('Achados dos canais indisponíveis no momento.')).toBeInTheDocument();
    expect(screen.getByText('Situação da base')).toBeInTheDocument();
  });
});
