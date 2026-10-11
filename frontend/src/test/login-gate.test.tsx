import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import axe from 'axe-core';
import { describe, expect, it } from 'vitest';
import { sessionUser } from './fixtures';
import { fail, mockApi, renderApp } from './utils';

const SESSION_KEY = 'caderno-inteligente.sessao';

async function signIn(password = 'senha-forte-123') {
  const form = screen.getByRole('form', { name: 'Entrar' });
  await userEvent.type(within(form).getByLabelText('E-mail'), sessionUser.email);
  await userEvent.type(within(form).getByLabelText('Senha'), password);
  await userEvent.click(within(form).getByRole('button', { name: 'Entrar' }));
}

describe('login antes de tudo: login > tela inicial > demais telas', () => {
  it.each(['/', '/fila', '/skus', '/dados/atualizar', '/usuarios', '/guia', '/rota-inexistente'])('sem sessão, %s mostra só o login e não chama a API', async (path) => {
    const api = mockApi();
    renderApp(path, { signedIn: false });
    expect(await screen.findByRole('heading', { level: 1, name: 'Entrar' })).toBeInTheDocument();
    expect(screen.queryByRole('navigation')).not.toBeInTheDocument();
    expect(screen.queryByRole('banner')).not.toBeInTheDocument();
    expect(api.calls).toEqual([]);
  });

  it('depois de entrar abre a tela inicial e as chamadas levam o token', async () => {
    const api = mockApi();
    renderApp('/fila', { signedIn: false });
    await screen.findByRole('heading', { level: 1, name: 'Entrar' });
    await signIn();
    await waitFor(() => expect(screen.getByRole('heading', { level: 1, name: 'Início' })).toBeInTheDocument());
    expect(JSON.parse(window.localStorage.getItem(SESSION_KEY) ?? '{}').user.email).toBe(sessionUser.email);
    const data = api.calls.filter((call) => call.path === '/api/overview');
    expect(data.length).toBeGreaterThan(0);
    expect(data.every((call) => call.headers.Authorization === 'Bearer token-sintetico')).toBe(true);
  });

  it('senha errada mostra o motivo e não guarda sessão', async () => {
    mockApi({ 'POST login': fail(401, 'E-mail ou senha incorretos.') });
    renderApp('/', { signedIn: false });
    await screen.findByRole('heading', { level: 1, name: 'Entrar' });
    await signIn('errada-errada');
    expect(await screen.findByRole('alert')).toHaveTextContent('E-mail ou senha incorretos.');
    expect(window.localStorage.getItem(SESSION_KEY)).toBeNull();
    expect(screen.queryByRole('navigation')).not.toBeInTheDocument();
  });

  it('401 em qualquer chamada encerra a sessão e volta ao login', async () => {
    mockApi({ overview: fail(401, 'Sessão inválida ou expirada. Entre novamente.') });
    renderApp('/');
    expect(await screen.findByRole('heading', { level: 1, name: 'Entrar' })).toBeInTheDocument();
    expect(screen.getByRole('alert')).toHaveTextContent('Sua sessão expirou. Entre novamente.');
    expect(window.localStorage.getItem(SESSION_KEY)).toBeNull();
  });

  it('"Sair" encerra a sessão e mostra o login', async () => {
    mockApi();
    renderApp('/');
    await userEvent.click(await screen.findByRole('button', { name: sessionUser.name || sessionUser.email }));
    await userEvent.click(screen.getByRole('button', { name: 'Sair' }));
    expect(await screen.findByRole('heading', { level: 1, name: 'Entrar' })).toBeInTheDocument();
    expect(window.localStorage.getItem(SESSION_KEY)).toBeNull();
  });

  it('a tela de login não tem violações de acessibilidade', async () => {
    mockApi();
    const view = renderApp('/', { signedIn: false });
    await screen.findByRole('heading', { level: 1, name: 'Entrar' });
    const result = await axe.run(view.container, { rules: { 'color-contrast': { enabled: false } }, resultTypes: ['violations'] });
    expect(result.violations.map((item) => item.id)).toEqual([]);
  });
});
