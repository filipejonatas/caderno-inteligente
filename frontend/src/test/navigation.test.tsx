import { screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { menuGroups, navigation, subNavigation } from '../components';
import { SKU_OK } from './fixtures';
import { mockApi, renderApp } from './utils';

const mainMenu = () => within(screen.getByRole('navigation', { name: 'Navegação principal' }));

describe('arquitetura de navegação final', () => {
  it('o menu tem Início, Planejamento, Comercial, Acompanhamento e Confiança, sem "Avançado"', async () => {
    mockApi();
    renderApp('/');
    await screen.findByRole('heading', { level: 2, name: 'O que olhar primeiro' });
    expect(mainMenu().getAllByRole('link').map((link) => link.querySelector('strong')?.textContent)).toEqual(['Início', 'Planejamento', 'Comercial', 'Acompanhamento', 'Confiança']);
    expect(screen.queryByText('Avançado')).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Ajuda: abrir o guia de uso' })).toHaveAttribute('href', '/guia');
    expect(menuGroups.map((group) => group.label)).not.toContain('Avançado');
  });

  it('Cenários fica em Planejamento e Execuções em Confiança, com abas e menu ativo corretos', async () => {
    mockApi();
    const { unmount } = renderApp('/cenarios');
    await screen.findByRole('heading', { level: 2, name: 'E se o peso de um sinal mudar?' });
    expect(mainMenu().getByRole('link', { name: /Planejamento/ })).toHaveAttribute('aria-current', 'page');
    const planTabs = within(screen.getByRole('navigation', { name: 'Seções desta área' }));
    expect(planTabs.getAllByRole('link').map((link) => link.textContent)).toEqual(['Fila operacional', 'Faturamento previsto', 'Cenários']);
    expect(planTabs.getByRole('link', { name: 'Cenários' })).toHaveAttribute('aria-current', 'page');
    unmount();

    renderApp('/execucoes');
    await screen.findByRole('heading', { level: 2, name: 'O que mudou entre duas execuções' });
    expect(mainMenu().getByRole('link', { name: /Confiança/ })).toHaveAttribute('aria-current', 'page');
    const trustTabs = within(screen.getByRole('navigation', { name: 'Seções desta área' }));
    expect(trustTabs.getAllByRole('link').map((link) => link.textContent)).toEqual(['Validação', 'Dados da planilha', 'Auditoria', 'Execuções']);
    expect(trustTabs.getByRole('link', { name: 'Execuções' })).toHaveAttribute('aria-current', 'page');
  });

  it('toda rota de página pertence a exatamente um grupo do menu', () => {
    const owners = (path: string) => menuGroups.filter((group) => group.paths.some((item) => item === path || (item !== '/' && path.startsWith(`${item}/`)))).map((group) => group.id);
    for (const item of navigation.filter((entry) => entry.path !== '/guia')) expect(owners(item.path), item.path).toHaveLength(1);
    for (const tabs of Object.values(subNavigation)) for (const tab of tabs) expect(navigation.some((entry) => entry.path === tab.to), tab.to).toBe(true);
  });
});

describe('endereços antigos continuam abrindo', () => {
  it.each([
    '/prioridades', '/prioridades?familia=Fam%C3%ADlia+A', '/previsoes', '/previsoes?acao=investigar_dados&ordem=suggested_quantity',
    '/fila', '/faturamento', '/cenarios', '/execucoes', '/execucoes?base=1&alvo=2', '/casos', '/casos?sku=TEST-001', '/decisoes', '/decisoes?sku=TEST-001',
    '/qualidade', '/validacao', '/auditoria', '/parceiros', '/parceiros?aba=parceiros', '/parceiros?aba=diretos', '/guia', `/skus/${SKU_OK}`, `/skus/${SKU_OK}?tab=impacto`,
  ])('%s não resulta em 404', async (path) => {
    mockApi();
    renderApp(path);
    await screen.findByRole('heading', { level: 2 });
    expect(screen.queryByText('Página não encontrada')).not.toBeInTheDocument();
    expect(document.title).not.toMatch(/Página não encontrada/);
  });
});
