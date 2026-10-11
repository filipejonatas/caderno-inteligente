import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import axe from 'axe-core';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { formatVersionTime } from '../components/DatasetVersions';
import { datasetEnabled, datasetLoginRequired, datasetOriginal, datasetPreviewError, datasetPreviewNoBefore, datasetVersions, sessionUser } from './fixtures';
import { setViewport } from './setup';
import { fail, mockApi, renderApp } from './utils';

const SESSION_KEY = 'caderno-inteligente.sessao';
const signedIn = () => window.localStorage.setItem(SESSION_KEY, JSON.stringify({ token: 'token-salvo', expiresAt: 4_102_444_800, user: sessionUser }));
/** GET /api/dataset responde conforme o login: sem Bearer pede login; com Bearer libera o envio. */
const byLogin = { dataset: (_url: URL, init?: RequestInit) => (init?.headers as Record<string, string> | undefined)?.Authorization ? datasetEnabled : datasetLoginRequired };
const sheet = (name = 'atualizacao-teste.xlsx', size?: number) => {
  const file = new File(['planilha sintética'], name, { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
  if (size !== undefined) Object.defineProperty(file, 'size', { value: size });
  return file;
};
const OPTIONS: axe.RunOptions = { rules: { 'color-contrast': { enabled: false } }, resultTypes: ['violations'] };
const violations = async (container: HTMLElement) => (await axe.run(container, OPTIONS)).violations.map((item) => `${item.id}: ${item.nodes.map((node) => node.target.join(' ')).join(' | ')}`);

// Storage em memória: o `localStorage` experimental do Node recente esconde o do jsdom (mesmo padrão de sku-registry.test).
beforeEach(() => {
  const data = new Map<string, string>();
  Object.defineProperty(window, 'localStorage', {
    configurable: true,
    value: { getItem: (key: string) => data.get(key) ?? null, setItem: (key: string, value: string) => { data.set(key, String(value)); }, removeItem: (key: string) => { data.delete(key); }, clear: () => data.clear() },
  });
});
afterEach(() => window.localStorage.clear());

async function openPage(overrides: Parameters<typeof mockApi>[0] = {}) {
  const api = mockApi(overrides);
  const view = renderApp('/dados/atualizar');
  await screen.findByRole('heading', { level: 2, name: 'Atualizar a base pela planilha' });
  return { api, ...view };
}

async function upload(file = sheet()) {
  await userEvent.upload(screen.getByLabelText(/^Planilha/), file);
}

describe('Bastidores › Atualizar dados (U.2)', () => {
  it('entra no menu Bastidores e mostra a base ativa com o modelo para baixar', async () => {
    await openPage();
    expect(screen.getByRole('heading', { level: 1, name: 'Atualizar dados' })).toBeInTheDocument();
    const tabs = within(screen.getByRole('navigation', { name: 'Seções desta área' }));
    expect(tabs.getByRole('link', { name: 'Atualizar dados' })).toHaveAttribute('aria-current', 'page');
    const active = within(screen.getByRole('heading', { level: 3, name: 'Base ativa' }).closest('section')!);
    expect(active.getByText('14/09/2026')).toBeInTheDocument();
    expect(active.getByText('ago/26')).toBeInTheDocument();
    expect(active.getByText('planilha original')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Baixar modelo (.xlsx)' })).toHaveAttribute('href', '/api/dataset/template');
  });

  it('com a base na planilha, o envio fica desabilitado e mostra o motivo do servidor', async () => {
    const { api } = await openPage();
    expect(screen.getByText(datasetOriginal.upload_disabled_message!)).toHaveAttribute('role', 'note');
    expect(screen.getByLabelText(/^Planilha/)).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Restaurar base original' })).toBeDisabled();
    expect(screen.getByRole('button', { name: /^Voltar para esta versão/ })).toBeDisabled();
    expect(screen.queryByRole('form', { name: 'Entrar para atualizar a base' })).not.toBeInTheDocument();
    expect(api.calls.some((call) => call.method === 'POST')).toBe(false);
  });

  it('com o motivo "login", leva para /login e, depois de entrar, volta com o envio liberado', async () => {
    mockApi(byLogin);
    renderApp('/dados/atualizar');
    expect(await screen.findByRole('heading', { level: 2, name: 'Entrar' })).toBeInTheDocument();
    expect(screen.queryByLabelText(/^Planilha/)).not.toBeInTheDocument();
    const form = screen.getByRole('form');
    await userEvent.type(within(form).getByLabelText('E-mail'), sessionUser.email);
    await userEvent.type(within(form).getByLabelText('Senha'), 'senha-forte-123');
    await userEvent.click(within(form).getByRole('button', { name: 'Entrar' }));
    await screen.findByRole('heading', { level: 2, name: 'Atualizar a base pela planilha' });
    await waitFor(() => expect(screen.getByLabelText(/^Planilha/)).toBeEnabled());
    expect(screen.getByText('Ana PCP')).toBeInTheDocument();
    expect(screen.queryByRole('form')).not.toBeInTheDocument();
  });

  it('oferece o modelo e o exemplo fictício para baixar', async () => {
    await openPage();
    expect(screen.getByRole('link', { name: 'Baixar exemplo fictício' })).toHaveAttribute('href', '/api/dataset/example');
  });

  it('prévia com erro mostra a linha endereçada, "mais N iguais" e não oferece "Aplicar"', async () => {
    signedIn();
    const { api } = await openPage({ ...byLogin, 'POST datasetPreview': fail(422, 'A planilha tem 1 erro que impede a aplicação.', { preview: datasetPreviewError }) });
    await upload(sheet('vendas-com-erro.xlsx'));
    const errors = await screen.findByRole('alert');
    expect(errors).toHaveTextContent('Um erro impede a aplicação');
    expect(within(errors).getAllByRole('listitem').map((item) => item.textContent)).toContain('Vendas_24m, linha 10, coluna Quantidade faturada: abc não é número');
    expect(errors).toHaveTextContent('e mais 1 igual');
    expect(screen.queryByRole('button', { name: 'Aplicar e recalcular' })).not.toBeInTheDocument();
    expect(screen.getByText('Não calculado: a planilha tem erros que bloqueiam a aplicação.')).toBeInTheDocument();
    const preview = api.calls.find((call) => call.path === '/api/dataset/preview')!;
    expect(preview.headers['X-Filename']).toBe('vendas-com-erro.xlsx');
    expect(preview.headers.Authorization).toBe('Bearer token-salvo');
  });

  it('prévia aplicável mostra o efeito estimado; aplicar pede confirmação e envia o sha256 e a versão da prévia', async () => {
    signedIn();
    const { api } = await openPage(byLogin);
    await upload();
    expect(await screen.findByText('Exemplo fictício')).toHaveAttribute('title', expect.stringMatching(/fictícios/));
    expect(screen.getByText('atualizacao-teste.xlsx', { selector: '.dataset-file strong' })).toBeInTheDocument();
    expect(screen.getByText('estimativa')).toBeInTheDocument();
    const facts = screen.getByText('Data de planejamento').closest('dl')!;
    expect(facts).toHaveTextContent(/14\/09\/2026 →para 12\/10\/2026/);
    expect(facts).toHaveTextContent(/2 SKUs →para 3 SKUs/);
    expect(facts).toHaveTextContent(/set\/26 →para out\/26/);
    expect(screen.getByRole('region', { name: /O que muda por aba/ })).toHaveTextContent('Vendas_24m');
    const datasetGets = api.calls.filter((call) => call.method === 'GET' && call.path === '/api/dataset').length;

    await userEvent.click(screen.getByRole('button', { name: 'Aplicar e recalcular' }));
    expect(api.calls.some((call) => call.path === '/api/dataset/apply')).toBe(false);
    await userEvent.click(within(screen.getByRole('group', { name: 'Confirmar aplicação' })).getByRole('button', { name: 'Confirmar e aplicar' }));

    expect(await screen.findByText('Base atualizada: referência 12/10/2026, vendas até set/26.')).toHaveAttribute('role', 'status');
    const apply = api.calls.find((call) => call.path === '/api/dataset/apply')!;
    expect(apply.headers['X-Confirm-Sha256']).toBe('feed01'.repeat(10) + 'feed');
    expect(apply.headers['X-Expected-Version']).toBe('1');
    expect(screen.getByRole('link', { name: 'Ver a fila' })).toHaveAttribute('href', '/fila');
    expect(screen.getByRole('link', { name: 'Ver dados da planilha' })).toHaveAttribute('href', '/qualidade');
    // O refresh do app relê a base ativa (e as outras telas releem a API ao abrir).
    await waitFor(() => expect(api.calls.filter((call) => call.method === 'GET' && call.path === '/api/dataset').length).toBeGreaterThan(datasetGets));
  });

  it('arquivo acima do limite é recusado no navegador com a mensagem do servidor, sem envio', async () => {
    signedIn();
    const { api } = await openPage(byLogin);
    await upload(sheet('grande.xlsx', 5_000_000));
    expect(await screen.findByRole('alert')).toHaveTextContent('Arquivo maior que o limite de 4 MB.');
    expect(api.calls.some((call) => call.path === '/api/dataset/preview')).toBe(false);
  });

  it('arquivo recusado pelo servidor (422 com código) mostra o motivo', async () => {
    signedIn();
    await openPage({ ...byLogin, 'POST datasetPreview': fail(422, 'O arquivo não é uma planilha .xlsx ou .xlsm válida.', { code: 'NOT_XLSX' }) });
    await upload();
    expect(await screen.findByRole('alert')).toHaveTextContent('O arquivo não é uma planilha .xlsx ou .xlsm válida.');
  });

  it('409 na aplicação pede para refazer a prévia', async () => {
    signedIn();
    const { api } = await openPage({ ...byLogin, 'POST datasetApply': fail(409, 'Outra pessoa atualizou a base; refaça a prévia.') });
    await upload();
    await userEvent.click(await screen.findByRole('button', { name: 'Aplicar e recalcular' }));
    await userEvent.click(screen.getByRole('button', { name: 'Confirmar e aplicar' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Outra pessoa atualizou a base; refaça a prévia.');
    await userEvent.click(screen.getByRole('button', { name: 'Refazer a prévia' }));
    await waitFor(() => expect(api.calls.filter((call) => call.path === '/api/dataset/preview')).toHaveLength(2));
  });

  it('sessão vencida (401) na prévia volta ao login', async () => {
    signedIn();
    await openPage({ ...byLogin, 'POST datasetPreview': fail(401, 'Token inválido.') });
    await upload();
    expect(await screen.findByRole('heading', { level: 2, name: 'Entrar' })).toBeInTheDocument();
    expect(screen.getByRole('alert')).toHaveTextContent('Sua sessão expirou. Entre novamente.');
    expect(window.localStorage.getItem(SESSION_KEY)).toBeNull();
  });

  it('histórico: "Voltar para esta versão" pede o segundo clique antes de restaurar', async () => {
    signedIn();
    const { api } = await openPage(byLogin);
    const history = screen.getByRole('region', { name: /Histórico de versões/ });
    expect(within(history).getByText('Ativa')).toBeInTheDocument();
    expect(within(history).getByText('Base original')).toBeInTheDocument();
    await userEvent.click(within(history).getByRole('button', { name: /^Voltar para esta versão/ }));
    expect(api.calls.some((call) => call.path.includes('/restore'))).toBe(false);
    await userEvent.click(within(within(history).getByRole('group')).getByRole('button', { name: 'Confirmar' }));
    expect(await screen.findByText('Base restaurada: referência 12/10/2026, vendas até set/26.')).toBeInTheDocument();
    const call = api.calls.find((item) => item.path === '/api/dataset/versions/1/restore')!;
    expect(call.method).toBe('POST');
    expect(call.headers.Authorization).toBe('Bearer token-salvo');
    expect(call.headers['X-Expected-Version']).toBe('1');
  });

  it('"Restaurar base original" pede confirmação em linha (sem window.confirm) e pode ser cancelado', async () => {
    signedIn();
    const { api } = await openPage(byLogin);
    await userEvent.click(screen.getByRole('button', { name: 'Restaurar base original' }));
    const group = screen.getByRole('group', { name: 'Confirmar restauração da base original' });
    await userEvent.click(within(group).getByRole('button', { name: 'Cancelar' }));
    expect(api.calls.some((call) => call.path === '/api/dataset/restore-original')).toBe(false);
    await userEvent.click(screen.getByRole('button', { name: 'Restaurar base original' }));
    await userEvent.click(within(screen.getByRole('group', { name: 'Confirmar restauração da base original' })).getByRole('button', { name: 'Confirmar' }));
    expect(await screen.findByText('Base restaurada: referência 14/09/2026, vendas até ago/26.')).toBeInTheDocument();
    expect(api.calls.filter((call) => call.path === '/api/dataset/restore-original')).toHaveLength(1);
    expect(api.calls.find((call) => call.path === '/api/dataset/restore-original')!.headers['X-Expected-Version']).toBe('1');
  });

  it('409 ao restaurar mostra a mensagem e recarrega a base', async () => {
    signedIn();
    const { api } = await openPage({ ...byLogin, 'POST datasetVersionRestore': fail(409, 'Outra pessoa atualizou a base; recarregue.') });
    const loads = () => api.calls.filter((call) => call.method === 'GET' && call.path === '/api/dataset').length;
    const before = loads();
    await userEvent.click(screen.getByRole('button', { name: /^Voltar para esta versão/ }));
    await userEvent.click(within(screen.getByRole('group', { name: /^Confirmar volta/ })).getByRole('button', { name: 'Confirmar' }));
    expect(await screen.findByText('Outra pessoa atualizou a base; recarregue.')).toHaveAttribute('role', 'alert');
    await waitFor(() => expect(loads()).toBeGreaterThan(before));
  });

  it('engine.before nulo mostra "Não disponível" nos valores de antes, sem quebrar a prévia', async () => {
    signedIn();
    await openPage({ ...byLogin, 'POST datasetPreview': datasetPreviewNoBefore });
    await upload();
    await screen.findByRole('button', { name: 'Aplicar e recalcular' });
    const facts = screen.getByText('Data de planejamento').closest('dl')!;
    expect(facts).toHaveTextContent(/Não disponível →para 3 SKUs/);
    expect(facts).toHaveTextContent(/Não disponível →para out\/26/);
    const top5 = within(screen.getByRole('region', { name: 'Cinco primeiros da fila antes e depois' }));
    expect(top5.getAllByText('Não disponível').length).toBeGreaterThan(0);
  });

  it('token vencido: com sessão local e GET pedindo login, encerra a sessão e mostra o login', async () => {
    signedIn();
    mockApi({ dataset: datasetLoginRequired });
    renderApp('/dados/atualizar');
    await screen.findByRole('heading', { level: 2, name: 'Entrar' });
    expect(window.localStorage.getItem(SESSION_KEY)).toBeNull();
    expect(screen.getByRole('alert')).toHaveTextContent('Sua sessão expirou. Entre novamente.');
  });

  it('falha de rede numa nova prévia mostra o erro e "Refazer a prévia", e o campo é limpo para reescolher o mesmo arquivo', async () => {
    signedIn();
    const { api } = await openPage({ ...byLogin, 'POST datasetPreview': () => { throw new TypeError('Failed to fetch'); } });
    const field = screen.getByLabelText(/^Planilha/) as HTMLInputElement;
    await upload();
    expect(await screen.findByRole('alert')).toHaveTextContent('Não foi possível conectar ao servidor');
    expect(screen.getByRole('button', { name: 'Refazer a prévia' })).toBeInTheDocument();
    expect(field.value).toBe('');
    await userEvent.click(screen.getByRole('button', { name: 'Refazer a prévia' }));
    await waitFor(() => expect(api.calls.filter((call) => call.path === '/api/dataset/preview')).toHaveLength(2));
  });

  it('e-mail mascarado para anônimos aparece como veio; data sem fuso é UTC e não quebra', async () => {
    const masked = { ...datasetVersions, items: [{ ...datasetVersions.items[0], user_email: 'p***@exemplo.test', created_at: '2026-10-12 09:30:00' }, datasetVersions.items[1]] };
    await openPage({ datasetVersions: masked });
    expect(screen.getByText('p***@exemplo.test')).toBeInTheDocument();
    expect(screen.getAllByText(/12\/10\/2026/).length).toBeGreaterThan(0);
    expect(formatVersionTime('2026-10-12 09:30:00')).toBe(formatVersionTime('2026-10-12T09:30:00Z'));
    expect(formatVersionTime('2026-10-12T09:30:00+00:00')).toBe(formatVersionTime('2026-10-12T09:30:00Z'));
    expect(formatVersionTime('lixo')).toBe('Não disponível');
    expect(formatVersionTime(null)).toBe('Não disponível');
  });
});

describe.each(['desktop', 'mobile'] as const)('acessibilidade de /dados/atualizar (%s)', (viewport) => {
  it('sem violações: desabilitada, com login e com prévia', async () => {
    setViewport(viewport);
    const disabled = await openPage();
    expect(await violations(disabled.container)).toEqual([]);
    disabled.unmount();

    mockApi(byLogin);
    const login = renderApp('/dados/atualizar');
    await screen.findByRole('heading', { level: 2, name: 'Entrar' });
    expect(await violations(login.container)).toEqual([]);
    login.unmount();

    signedIn();
    const withPreview = await openPage(byLogin);
    await upload();
    await screen.findByRole('button', { name: 'Aplicar e recalcular' });
    document.querySelectorAll('details').forEach((details) => { details.open = true; });
    expect(await violations(withPreview.container)).toEqual([]);
    for (const shell of withPreview.container.querySelectorAll('.table-shell')) {
      expect(shell).toHaveAttribute('tabindex', '0');
      expect(shell).toHaveAccessibleName();
    }
  });
});
