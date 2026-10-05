import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { PARTNER, SKU_OK, SKU_SHORT } from './fixtures';
import { setViewport } from './setup';
import { currentLocation, mockApi, renderApp } from './utils';

const ROUTES: Array<[string, string, string]> = [
  ['/', 'Visão geral', 'Da atenção à decisão humana'],
  ['/guia', 'Guia de uso', 'Entenda o Caderno Inteligente em poucos minutos'],
  ['/prioridades', 'Prioridades', 'Prioridades explicáveis'],
  ['/previsoes', 'Previsão e recomendações', 'Previsão e recomendações'],
  ['/casos', 'Casos', 'Casos operacionais'],
  ['/qualidade', 'Qualidade', 'Qualidade dos dados'],
  ['/parceiros', 'Visibilidade B2B2C', 'Parceiros e canais'],
  ['/cenarios', 'Cenários', 'Simulação de cenários'],
  ['/execucoes', 'Execuções', 'Execuções registradas'],
  ['/decisoes', 'Decisões', 'Feedback do PCP'],
  ['/validacao', 'Validação', 'Central de validação'],
];

describe.each(['desktop', 'mobile'] as const)('rotas em %s', (viewport) => {
  it.each(ROUTES)('%s resolve título, conteúdo e título da aba', async (path, label, intro) => {
    setViewport(viewport);
    mockApi();
    renderApp(path);
    expect(screen.getByRole('heading', { level: 1, name: label })).toBeInTheDocument();
    expect(await screen.findByRole('heading', { level: 2, name: intro })).toBeInTheDocument();
    expect(document.title).toBe(`${label} · Caderno Inteligente`);
    expect(screen.getByRole('main')).toBeInTheDocument();
  });
});

describe('deep links', () => {
  it('abre o detalhe de SKU com código codificado e sem carregar o dashboard', async () => {
    const api = mockApi();
    renderApp(`/skus/${encodeURIComponent(SKU_SHORT)}`);
    expect(await screen.findByRole('heading', { level: 2, name: SKU_SHORT })).toBeInTheDocument();
    expect(api.gets()).toContain(`/api/priorities/${encodeURIComponent(SKU_SHORT)}`);
    expect(api.gets().some((path) => path === '/api/overview' || path === '/api/priorities')).toBe(false);
    expect(screen.getByRole('heading', { level: 1, name: 'Detalhe do SKU' })).toBeInTheDocument();
  });

  it('abre o detalhe do parceiro com código codificado', async () => {
    const api = mockApi();
    renderApp(`/parceiros/${encodeURIComponent(PARTNER)}`);
    expect(await screen.findByRole('heading', { level: 2, name: 'Parceiro sintético' })).toBeInTheDocument();
    expect(api.gets()).toContain(`/api/partners/${encodeURIComponent(PARTNER)}`);
    expect(api.gets().some((path) => path.startsWith(`/api/partners/${encodeURIComponent(PARTNER)}/skus?`))).toBe(true);
    expect(screen.getByRole('link', { name: /Visibilidade B2B2C/ })).toHaveAttribute('aria-current', 'page');
  });

  it('abre a comparação de execuções pela URL', async () => {
    const api = mockApi();
    renderApp('/execucoes?base=1&alvo=2');
    expect(await screen.findByText('Execução #1', { selector: 'strong' })).toBeInTheDocument();
    expect(api.gets()).toContain('/api/run-comparisons?base=1&target=2');
  });

  it('abre a página do SKU a partir de uma prioridade e preserva o retorno', async () => {
    const user = userEvent.setup();
    mockApi();
    renderApp('/prioridades?familia=Fam%C3%ADlia+A');
    await user.click(await screen.findByRole('button', { name: `Abrir evidências de ${SKU_OK}` }));
    expect(await screen.findByRole('heading', { level: 2, name: SKU_OK })).toBeInTheDocument();
    expect(currentLocation()).toBe(`/skus/${SKU_OK}`);
    await user.click(screen.getByRole('button', { name: 'Voltar' }));
    await waitFor(() => expect(currentLocation()).toBe('/prioridades?familia=Fam%C3%ADlia+A'));
  });
});

describe('404 e guia offline', () => {
  it('rota desconhecida mostra 404 sem consultar a API', async () => {
    const api = mockApi();
    renderApp('/rota-inexistente');
    expect(await screen.findByRole('heading', { level: 2, name: 'Página não encontrada' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Voltar para a visão geral/ })).toHaveAttribute('href', '/');
    expect(api.calls).toHaveLength(0);
  });

  it('o guia funciona com a API fora do ar', async () => {
    const api = mockApi();
    api.fetchMock.mockRejectedValue(new TypeError('Failed to fetch'));
    renderApp('/guia');
    expect(await screen.findByRole('heading', { level: 2, name: 'Entenda o Caderno Inteligente em poucos minutos' })).toBeInTheDocument();
    expect(screen.getByText('Não consulta a API')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Atualizar/ })).not.toBeInTheDocument();
    expect(api.fetchMock).not.toHaveBeenCalled();
    const pages = screen.getAllByRole('link', { name: /Abrir página/ });
    expect(pages.length).toBeGreaterThanOrEqual(ROUTES.length - 1);
  });
});

describe('menu', () => {
  it('marca apenas o link ativo e move o foco para o título ao navegar', async () => {
    const user = userEvent.setup();
    mockApi();
    renderApp('/prioridades');
    const nav = screen.getByRole('navigation', { name: 'Navegação principal' });
    expect(within(nav).getByRole('link', { name: /Prioridades/ })).toHaveAttribute('aria-current', 'page');
    expect(within(nav).getByRole('link', { name: /Visão geral/ })).not.toHaveAttribute('aria-current');
    await user.click(within(nav).getByRole('link', { name: /Validação/ }));
    expect(await screen.findByRole('heading', { level: 1, name: 'Validação' })).toHaveFocus();
    expect(within(nav).getByRole('link', { name: /Validação/ })).toHaveAttribute('aria-current', 'page');
    expect(document.title).toBe('Validação · Caderno Inteligente');
  });
});
