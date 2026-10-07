import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { SKU_OK } from './fixtures';
import { mockApi, renderApp } from './utils';

// Etapa 15.2: a cobertura usa a demanda prevista; o cadastro divergente vira aviso de qualidade.
describe('cobertura pela demanda prevista', () => {
  it('Dados da planilha mostra quantos SKUs têm venda média cadastrada distante da prevista', async () => {
    mockApi();
    renderApp('/qualidade');
    expect(await screen.findByText('2 SKUs')).toBeInTheDocument();
    expect(screen.getByText('distantes da demanda prevista')).toBeInTheDocument();
  });

  it('o detalhe do SKU mostra a cobertura pela demanda e a do cadastro quando divergem', async () => {
    mockApi();
    renderApp(`/skus/${encodeURIComponent(SKU_OK)}?tab=evidencias`);
    expect(await screen.findByText(/cadastro: 9 dias/)).toBeInTheDocument();
  });
});
