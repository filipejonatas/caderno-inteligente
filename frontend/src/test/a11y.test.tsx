import { screen } from '@testing-library/react';
import axe from 'axe-core';
import { describe, expect, it } from 'vitest';
import { PARTNER, SKU_SHORT } from './fixtures';
import { setViewport } from './setup';
import { mockApi, renderApp } from './utils';

// jsdom has no layout engine: color contrast is checked separately in contrast.test.ts.
const OPTIONS: axe.RunOptions = { rules: { 'color-contrast': { enabled: false } }, resultTypes: ['violations'] };

const PAGES: Array<[string, string]> = [
  ['/', 'O que olhar primeiro'],
  ['/guia', 'Entenda o Caderno Inteligente em poucos minutos'],
  ['/prioridades', 'Em que ordem analisar os SKUs'],
  ['/previsoes', 'Preciso produzir? Quanto?'],
  [`/skus/${encodeURIComponent(SKU_SHORT)}`, SKU_SHORT],
  ['/casos', 'Casos em acompanhamento'],
  ['/qualidade', 'Posso confiar na planilha?'],
  ['/parceiros', 'Onde há oportunidade de reposição'],
  [`/parceiros/${encodeURIComponent(PARTNER)}`, 'Parceiro sintético'],
  ['/cenarios', 'E se o peso de um sinal mudar?'],
  ['/execucoes?base=1&alvo=2', 'O que mudou entre duas execuções'],
  ['/decisoes', 'Registrar a decisão'],
  ['/validacao', 'Quanto confiar nas recomendações'],
  ['/rota-inexistente', 'Página não encontrada'],
];

function describeViolations(violations: axe.Result[]) {
  return violations.map((violation) => `${violation.impact} ${violation.id}: ${violation.help} → ${violation.nodes.slice(0, 3).map((node) => node.target.join(' ')).join(' | ')}`);
}

describe.each(['desktop', 'mobile'] as const)('acessibilidade automatizada (%s)', (viewport) => {
  it.each(PAGES)('%s não tem violações de acessibilidade', async (path, heading) => {
    setViewport(viewport);
    mockApi();
    const { container } = renderApp(path);
    await screen.findByRole('heading', { level: 2, name: heading });
    if (path.startsWith('/execucoes')) await screen.findByText('Fonte e configuração');
    const results = await axe.run(container, OPTIONS);
    // Every impact level (critical, serious, moderate, minor) must be clean in the main flow.
    expect(describeViolations(results.violations)).toEqual([]);
    // jsdom cannot detect overflow, so enforce the pattern axe checks in real browsers (scrollable-region-focusable).
    for (const shell of container.querySelectorAll('.table-shell')) {
      expect(shell).toHaveAttribute('tabindex', '0');
      expect(shell).toHaveAccessibleName();
    }
  });
});
