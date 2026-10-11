import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { JOURNEY, NEXT_STEPS } from '../journey';
import { fail, mockApi, renderApp } from './utils';

const strip = async () => within(await screen.findByRole('list', { name: 'Caminho do PCP, em cinco passos' }));
const step = (list: ReturnType<typeof within>, verb: string) => list.getByText(verb, { exact: false, selector: '.journey-verb' }).closest('a') as HTMLElement;

describe('Início: o caminho em cinco passos', () => {
  it('mostra as cinco etapas na ordem, cada uma com a pergunta, o número da API e o link', async () => {
    mockApi();
    renderApp('/');
    const list = await strip();
    expect(list.getAllByRole('link').map((link) => link.getAttribute('href'))).toEqual(JOURNEY.map((item) => item.to));
    expect(within(step(list, 'Ver')).getByText('O que arde agora?')).toBeInTheDocument();
    expect(within(step(list, 'Ver')).getByText(/2\s*$/)).toBeInTheDocument();
    expect(await within(step(list, 'Caber')).findByText('1 de 2')).toBeInTheDocument();
    expect(await within(step(list, 'Atender')).findByText(/300 un\./)).toBeInTheDocument();
    expect(within(step(list, 'Confiar')).getByText(/de 3 SKUs com confiança baixa/)).toBeInTheDocument();
  });

  it('valor sem preço mostra as unidades e avisa, nunca R$ 0', async () => {
    mockApi();
    renderApp('/');
    const atender = step(await strip(), 'Atender');
    expect(await within(atender).findByText(/valor indisponível \(sem preço\)/)).toBeInTheDocument();
    expect(atender).not.toHaveTextContent(/R\$\s0/);
  });

  it('uma etapa que falha diz indisponível sem derrubar as outras nem virar zero', async () => {
    mockApi({ capacityPlan: fail(500, 'Erro interno.') });
    renderApp('/');
    const list = await strip();
    expect(await within(step(list, 'Caber')).findByText('Indisponível')).toBeInTheDocument();
    expect(step(list, 'Caber')).not.toHaveTextContent(/0 de/);
    expect(await within(step(list, 'Atender')).findByText(/300 un\./)).toBeInTheDocument();
    expect(within(step(list, 'Ver')).getByText(/risco de ruptura/)).toBeInTheDocument();
  });
});

describe('Próximo passo', () => {
  it.each(Object.entries(NEXT_STEPS))('%s tem um rodapé que leva a %s', async (path, next) => {
    mockApi();
    renderApp(path);
    const footer = await screen.findByRole('navigation', { name: 'Próximo passo' });
    expect(within(footer).getByRole('link', { name: next.label })).toHaveAttribute('href', next.to);
  });

  it('seguindo só os rodapés, do Início chega-se à Validação e volta ao Início', async () => {
    mockApi();
    renderApp('/fila');
    let path = '/fila';
    const visited = [path];
    while (NEXT_STEPS[path]) {
      const footer = await screen.findByRole('navigation', { name: 'Próximo passo' });
      await userEvent.click(within(footer).getByRole('link'));
      path = NEXT_STEPS[path].to;
      visited.push(path);
      if (path === '/') break;
    }
    expect(visited).toEqual(['/fila', '/capacidade', '/parceiros', '/faturamento', '/validacao', '/']);
    expect(await screen.findByRole('heading', { level: 2, name: 'O que olho primeiro?' })).toBeInTheDocument();
  });

  it('páginas fora da jornada não mostram o rodapé', async () => {
    mockApi();
    renderApp('/skus');
    await screen.findByRole('heading', { level: 2 });
    expect(screen.queryByRole('navigation', { name: 'Próximo passo' })).not.toBeInTheDocument();
  });
});
