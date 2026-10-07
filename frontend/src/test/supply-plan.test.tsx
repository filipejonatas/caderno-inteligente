import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { forecasts, SKU_OK } from './fixtures';
import { mockApi, renderApp } from './utils';

// Etapa 15.3: a ação vem do plano datado; falta inevitável é urgente e o porquê mostra o plano.
describe('plano datado na fila e no detalhe', () => {
  it('o detalhe do SKU explica a ação com as linhas do plano', async () => {
    mockApi();
    renderApp(`/skus/${encodeURIComponent(SKU_OK)}`);
    expect(await screen.findByText(/Ordem planejada de 500 un\. para chegar em 05\/10/)).toBeInTheDocument();
  });

  it('falta inevitável aparece na fila com o rótulo do plano', async () => {
    const rows = forecasts.map((item, index) => index === 0
      ? { ...item, operational_recommendation: { ...item.operational_recommendation, action: 'atraso_inevitavel' as const, action_label: 'Falta inevitável: renegociar prazos e garantir a OP' } }
      : item);
    mockApi({ forecasts: rows });
    renderApp('/fila');
    expect(await screen.findByText('Falta inevitável: renegociar prazos e garantir a OP')).toBeInTheDocument();
  });
});
