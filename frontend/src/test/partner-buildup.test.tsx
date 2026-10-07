import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { CommercialMatrix } from '../components/CommercialMatrix';
import { commercialRow, partnerRows } from './fixtures';

// Etapa 15.5: estoque acumulando no parceiro aparece como risco, com sell-through e estoque inicial → final.
const buildup = {
  ...commercialRow, action: 'conter_reposicao' as const, action_label: 'Não repor; acionar sell-out com o parceiro', data_quality: 'sufficient' as const,
  estimated_stock: 931, stock_start: 595, sell_through_window: 0.59, buildup_window_months: 6, stock_identity_consistent: true, coverage_days: 355,
  average_monthly_sell_out: 79, recommendation_reason: 'O parceiro recebe mais do que vende.',
  signals: [{ code: 'PARTNER_STOCK_BUILDUP', label: 'Estoque acumulando no parceiro' }],
  periods: [{ month: '2026-08', sell_in_quantity: 150, sell_out_quantity: 70, estimated_stock: 931, data_nature: 'Observado pelo parceiro' }],
};

describe('estoque acumulando no parceiro', () => {
  it('marca o vínculo e mostra o sell-through e a evolução do estoque', () => {
    render(<MemoryRouter><CommercialMatrix response={{ ...partnerRows, items: [buildup] }} /></MemoryRouter>);
    expect(screen.getAllByText('Estoque acumulando').length).toBeGreaterThan(0);
    expect(screen.getByText('Vendido ÷ enviado')).toBeInTheDocument();
    expect(screen.getByText(/6 meses · estoque 595 → 931/)).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'Estoque estimado' })).toBeInTheDocument();
  });
});
