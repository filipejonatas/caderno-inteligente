import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { ChallengeBadge } from '../components/ChallengeAction';
import { CHALLENGE_DEFINITIONS, CHALLENGE_NAMES } from '../pages/shared';
import { PARTNER, SKU_OK, SKU_SHORT, challengeInvestigate, challengeUrgent } from './fixtures';
import { mockApi, renderApp } from './utils';

describe('selo do rótulo de ação', () => {
  it('mostra o rótulo e explica no "?" o porquê, as evidências, a limitação e a revisão humana', () => {
    render(<ChallengeBadge action={challengeUrgent} />);
    expect(screen.getByText('Priorizar produção', { selector: '.badge' })).toBeInTheDocument();
    const tip = screen.getByRole('tooltip', { hidden: true }).textContent ?? '';
    expect(tip).toContain('posição 3 na fila de atenção');
    expect(tip).toContain('Posição na fila de atenção: 3');
    expect(tip).not.toContain('Sem valor');            // evidência nula não é exibida como zero
    expect(tip).toContain('a quantidade oficial não muda');
    expect(tip).toContain('Revisão humana obrigatória');
  });

  it('sem rótulo (resposta antiga) não renderiza nada', () => {
    const { container } = render(<><ChallengeBadge action={undefined} /><ChallengeBadge action={null} /></>);
    expect(container).toBeEmptyDOMElement();
  });

  it('nomes e definições cobrem os dez rótulos', () => {
    expect(Object.keys(CHALLENGE_NAMES)).toHaveLength(10);
    expect(Object.keys(CHALLENGE_DEFINITIONS).sort()).toEqual(Object.keys(CHALLENGE_NAMES).sort());
  });
});

describe('Previsão: rótulo por SKU', () => {
  it('destaca só "Priorizar produção" na lista e mantém a ação operacional', async () => {
    mockApi();
    renderApp('/previsoes?todos=1');
    const table = await screen.findByRole('region', { name: /Previsões; role horizontalmente/ });
    const row = within(table).getByText(SKU_OK).closest('tr') as HTMLElement;
    expect(within(row).getByText('Priorizar produção', { selector: '.badge' })).toBeInTheDocument();
    expect(within(row).getByText('Produzir')).toBeInTheDocument();
    const short = within(table).getByText(SKU_SHORT).closest('tr') as HTMLElement;
    expect(within(short).queryByText('Priorizar produção')).not.toBeInTheDocument();
    expect(within(short).getByText('Investigar dados')).toBeInTheDocument();
  });

  it('o filtro por rótulo lê e grava a URL e filtra a lista', async () => {
    const user = userEvent.setup();
    mockApi();
    renderApp('/previsoes?rotulo=investigar');
    const select = await screen.findByLabelText('Rótulo');
    expect(select).toHaveValue('investigar');
    const table = screen.getByRole('region', { name: /Previsões; role horizontalmente/ });
    expect(within(table).getByText(SKU_SHORT)).toBeInTheDocument();
    expect(within(table).queryByText(SKU_OK)).not.toBeInTheDocument();
    await user.selectOptions(select, 'priorizar_producao');
    await waitFor(() => expect(within(screen.getByRole('region', { name: /Previsões; role horizontalmente/ })).getByText(SKU_OK)).toBeInTheDocument());
    expect(within(screen.getByRole('region', { name: /Previsões; role horizontalmente/ })).queryByText(SKU_SHORT)).not.toBeInTheDocument();
  });

  it('resposta antiga sem rótulo não mostra o filtro nem quebra a lista', async () => {
    const { forecasts } = await import('./fixtures');
    mockApi({ forecasts: forecasts.map(({ challenge_action: _removed, ...item }) => item) });
    renderApp('/previsoes?todos=1');
    const table = await screen.findByRole('region', { name: /Previsões; role horizontalmente/ });
    expect(within(table).getByText(SKU_OK)).toBeInTheDocument();
    expect(screen.queryByLabelText('Rótulo')).not.toBeInTheDocument();
  });
});

describe('Detalhe do SKU: rótulo e registro da decisão', () => {
  it('mostra o rótulo no cartão da ação e leva o rótulo para o registro', async () => {
    mockApi();
    renderApp(`/skus/${SKU_OK}`);
    const answer = (await screen.findByText('Ação operacional sugerida')).closest('section') as HTMLElement;
    expect(within(answer).getByText('Priorizar produção', { selector: '.badge' })).toBeInTheDocument();
    expect(within(answer).getByRole('link', { name: 'Registrar decisão' })).toHaveAttribute('href', `/decisoes?sku=${SKU_OK}&rotulo=priorizar_producao`);
  });

  it('o registro mostra o rótulo e o envia com a decisão', async () => {
    const user = userEvent.setup();
    const api = mockApi();
    renderApp(`/decisoes?sku=${SKU_OK}&rotulo=priorizar_producao`);
    expect(await screen.findByText('Rótulo registrado com a decisão:')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Registrar decisão' }));
    await waitFor(() => expect(api.calls.find((call) => call.method === 'POST')).toBeTruthy());
    expect(api.calls.find((call) => call.method === 'POST')?.body).toMatchObject({ sku: SKU_OK, challenge_action: 'priorizar_producao' });
  });

  it('trocar de SKU descarta o rótulo; rótulo desconhecido na URL é ignorado', async () => {
    const user = userEvent.setup();
    const api = mockApi();
    const { unmount } = renderApp(`/decisoes?sku=${SKU_OK}&rotulo=priorizar_producao`);
    await user.selectOptions(await screen.findByLabelText('SKU'), SKU_SHORT);
    expect(screen.queryByText('Rótulo registrado com a decisão:')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Registrar decisão' }));
    await waitFor(() => expect(api.calls.find((call) => call.method === 'POST')).toBeTruthy());
    expect(api.calls.find((call) => call.method === 'POST')?.body).not.toHaveProperty('challenge_action');
    unmount();
    renderApp(`/decisoes?sku=${SKU_OK}&rotulo=inventado`);
    await screen.findByLabelText('SKU');
    expect(screen.queryByText('Rótulo registrado com a decisão:')).not.toBeInTheDocument();
  });
});

describe('Parceiros e canais: rótulos', () => {
  it('lista de parceiros mostra "Priorizar parceiro" e o filtro vai para a URL', async () => {
    const user = userEvent.setup();
    mockApi();
    renderApp('/parceiros?aba=parceiros');
    const table = await screen.findByRole('region', { name: /Parceiros; role horizontalmente/ });
    expect(within(table).getByText('Priorizar parceiro', { selector: '.badge' })).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText('Rótulo'), 'priorizar_parceiro');
    expect(within(screen.getByRole('region', { name: /Parceiros; role horizontalmente/ })).getByText('Parceiro sintético')).toBeInTheDocument();
    expect(await screen.findByLabelText('Rótulo')).toHaveValue('priorizar_parceiro');
  });

  it('a matriz parceiro–SKU mostra o rótulo da linha e o detalhe filtra pela API', async () => {
    const user = userEvent.setup();
    const api = mockApi();
    renderApp(`/parceiros/${encodeURIComponent(PARTNER)}?qualidade=sufficient`); // a barra de filtros só aparece com muitos SKUs ou com filtro ativo
    const matrix = await screen.findByRole('region', { name: /Matriz comercial/ });
    expect(within(matrix).getByText('Repor', { selector: '.badge' })).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText('Rótulo'), 'repor');
    await waitFor(() => expect(api.gets().some((path) => path.includes('challenge_action=repor'))).toBe(true));
  });

  it('o detalhe do canal mostra o rótulo do desafio e filtra pela API', async () => {
    const user = userEvent.setup();
    const api = mockApi();
    renderApp('/canais/Loja%20pr%C3%B3pria');
    const table = await screen.findByRole('region', { name: /SKUs do canal; role horizontalmente/ });
    expect(within(table).getByText('Monitorar', { selector: '.badge' })).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText('Rótulo'), 'ampliar_mix');
    await waitFor(() => expect(api.gets().some((path) => path.includes('challenge_action=ampliar_mix'))).toBe(true));
  });
});

describe('Guia: legenda dos rótulos', () => {
  it('traz o nome e a definição de cada rótulo', async () => {
    mockApi();
    renderApp('/guia');
    await screen.findByRole('heading', { level: 2, name: 'Entenda o Caderno Inteligente em poucos minutos' });
    for (const [code, name] of Object.entries(CHALLENGE_NAMES)) {
      expect(screen.getByText(`Rótulo: ${name}`)).toBeInTheDocument();
      expect(screen.getByText(CHALLENGE_DEFINITIONS[code])).toBeInTheDocument();
    }
  });
});
