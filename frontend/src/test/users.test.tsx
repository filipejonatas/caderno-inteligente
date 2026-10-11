import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import axe from 'axe-core';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import * as fx from './fixtures';
import { sessionUser } from './fixtures';
import { fail, mockApi, renderApp } from './utils';

const SESSION_KEY = 'caderno-inteligente.sessao';
const users = { items: [{ email: 'ana@exemplo.test', name: 'Ana PCP', active: true, created_at: '2026-10-12 09:30:00' }] };

beforeEach(() => {
  const data = new Map<string, string>();
  Object.defineProperty(window, 'localStorage', {
    configurable: true,
    value: { getItem: (key: string) => data.get(key) ?? null, setItem: (key: string, value: string) => { data.set(key, String(value)); }, removeItem: (key: string) => { data.delete(key); }, clear: () => data.clear() },
  });
});
afterEach(() => window.localStorage.clear());
const signedIn = () => window.localStorage.setItem(SESSION_KEY, JSON.stringify({ token: 'token-salvo', expiresAt: 4_102_444_800, user: sessionUser }));

describe('/usuarios', () => {
  it('sem sessão leva ao login', async () => {
    mockApi({ users });
    renderApp('/usuarios', { signedIn: false });
    expect(await screen.findByRole('heading', { level: 1, name: 'Entrar' })).toBeInTheDocument();
  });

  it('lista, cadastra e recarrega a lista', async () => {
    signedIn();
    const api = mockApi({ users, 'POST users': { email: 'novo@exemplo.test', name: 'Novo' } });
    renderApp('/usuarios');
    expect(await screen.findByText('ana@exemplo.test')).toBeInTheDocument();
    const form = screen.getByRole('form', { name: 'Cadastrar usuário' });
    await userEvent.type(within(form).getByLabelText('E-mail'), 'novo@exemplo.test');
    await userEvent.type(within(form).getByLabelText('Nome'), 'Novo');
    await userEvent.type(within(form).getByLabelText('Senha provisória'), 'senha-forte-123');
    await userEvent.click(within(form).getByRole('button', { name: 'Cadastrar' }));
    expect(await screen.findByText('Usuário novo@exemplo.test cadastrado.')).toBeInTheDocument();
    const post = api.calls.find((call) => call.method === 'POST' && call.path === '/api/users')!;
    expect(post.headers.Authorization).toBe('Bearer token-salvo');
    await waitFor(() => expect(api.calls.filter((call) => call.method === 'GET' && call.path === '/api/users').length).toBeGreaterThan(1));
    expect(within(form).getByLabelText('Senha provisória')).toHaveValue('');
  });

  it('mostra o erro do servidor (e-mail repetido)', async () => {
    signedIn();
    mockApi({ users, 'POST users': fail(409, 'Usuário ana@exemplo.test já existe') });
    renderApp('/usuarios');
    const form = await screen.findByRole('form', { name: 'Cadastrar usuário' });
    await userEvent.type(within(form).getByLabelText('E-mail'), 'ana@exemplo.test');
    await userEvent.type(within(form).getByLabelText('Senha provisória'), 'senha-forte-123');
    await userEvent.click(within(form).getByRole('button', { name: 'Cadastrar' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('já existe');
  });

  it('com a escrita desligada, avisa antes e desabilita o cadastro', async () => {
    signedIn();
    mockApi({ users, system: { ...fx.system, write_enabled: false } });
    renderApp('/usuarios');
    expect(await screen.findByText(/cadastro está desabilitado/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Cadastrar' })).toBeDisabled();
  });

  it('sem violações de acessibilidade', async () => {
    signedIn();
    mockApi({ users });
    const view = renderApp('/usuarios');
    await screen.findByText('ana@exemplo.test');
    const result = await axe.run(view.container, { rules: { 'color-contrast': { enabled: false } }, resultTypes: ['violations'] });
    expect(result.violations.map((item) => item.id)).toEqual([]);
  });
});
