import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { isInternalPath } from '../pages/SkuDetailPage';
import { system } from './fixtures';
import { fail, mockApi, renderApp } from './utils';

const readOnly = { ...system, write_enabled: false };
const demo = { ...system, demo_mode: true, notice: 'Publicação de demonstração: os dados são fictícios.' };

describe('modo da publicação', () => {
  it('modo normal não mostra aviso e mantém registros habilitados', async () => {
    mockApi();
    renderApp('/decisoes');
    expect(await screen.findByRole('button', { name: 'Registrar decisão' })).toBeEnabled();
    expect(screen.queryByRole('note', { name: 'Modo da publicação' })).not.toBeInTheDocument();
  });

  it('modo demonstração exibe aviso em páginas com dados', async () => {
    mockApi({ system: demo });
    renderApp('/');
    expect(await screen.findByRole('note', { name: 'Modo da publicação' })).toHaveTextContent('Publicação de demonstração: os dados são fictícios.');
  });

  it('somente leitura desabilita decisões, casos e execuções com explicação', async () => {
    mockApi({ system: readOnly });
    const { unmount } = renderApp('/decisoes');
    await waitFor(() => expect(screen.getByRole('button', { name: 'Registrar decisão' })).toBeDisabled());
    expect(screen.getByText('Registro desabilitado nesta publicação (somente leitura).')).toBeInTheDocument();
    expect(screen.getByRole('note', { name: 'Modo da publicação' })).toHaveTextContent('Somente leitura.');
    unmount();

    renderApp('/casos');
    await waitFor(() => expect(screen.getByRole('button', { name: 'Criar caso' })).toBeDisabled());
    expect(screen.queryByRole('button', { name: '+ Novo caso' })).not.toBeInTheDocument();
  });

  it('somente leitura também bloqueia o registro de execução', async () => {
    mockApi({ system: readOnly });
    renderApp('/execucoes');
    await waitFor(() => expect(screen.getByRole('button', { name: 'Registrar execução atual' })).toBeDisabled());
  });

  it('páginas estáticas não consultam o modo, preservando o guia offline', async () => {
    const api = mockApi({ system: demo });
    renderApp('/guia');
    await screen.findByRole('heading', { level: 2, name: 'Entenda o Caderno Inteligente em poucos minutos' });
    expect(api.calls).toHaveLength(0);
    expect(screen.queryByRole('note', { name: 'Modo da publicação' })).not.toBeInTheDocument();
  });

  it('falha ao consultar o modo não impede a página', async () => {
    mockApi({ system: fail(500, 'indisponível') });
    renderApp('/decisoes');
    expect(await screen.findByRole('button', { name: 'Registrar decisão' })).toBeEnabled();
  });

  it('403 do servidor é exibido mesmo se a interface não souber do modo', async () => {
    const user = userEvent.setup();
    mockApi({ system: fail(500, 'indisponível'), 'POST feedback': fail(403, 'Registro desabilitado nesta publicação (modo somente leitura).') });
    renderApp('/decisoes');
    await user.click(await screen.findByRole('button', { name: 'Registrar decisão' }));
    expect(await screen.findByText('Registro desabilitado nesta publicação (modo somente leitura).')).toBeInTheDocument();
  });
});

describe('validação de entrada', () => {
  it('campos de texto têm limites alinhados ao servidor', async () => {
    mockApi();
    renderApp('/decisoes');
    expect(await screen.findByLabelText('Observação')).toHaveAttribute('maxlength', '2000');
    expect(screen.getByLabelText('Usuário')).toHaveAttribute('maxlength', '80');
    expect(screen.getByLabelText(/Tempo de análise/)).toHaveAttribute('max', '1440');
  });

  it('erros de validação em lista viram mensagem legível', async () => {
    const user = userEvent.setup();
    mockApi({ 'POST feedback': () => ({ __failure: true, status: 422, detail: [{ loc: ['body', 'note'], msg: 'String should have at most 2000 characters' }] }) });
    renderApp('/decisoes');
    await user.click(await screen.findByRole('button', { name: 'Registrar decisão' }));
    expect(await screen.findByText('Dados inválidos: observação — String should have at most 2000 characters')).toBeInTheDocument();
  });
});

describe('redirecionamento interno', () => {
  it.each([
    ['/prioridades?familia=A', true],
    ['/skus/CI-0001', true],
    ['//evil.example', false],
    ['/\\evil.example', false],
    ['https://evil.example', false],
    ['javascript:alert(1)', false],
    ['/ok\nheader', false],
  ])('%s → %s', (path, expected) => {
    expect(isInternalPath(path)).toBe(expected);
  });
});
