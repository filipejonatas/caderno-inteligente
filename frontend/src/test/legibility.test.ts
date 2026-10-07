import { describe, expect, it } from 'vitest';
import css from '../styles.css?raw';

// Piso de legibilidade: nenhum texto visível abaixo de 12 px (rótulos só para leitor de tela usam .sr-only e não têm tamanho).
// O texto usa a escala de tokens (--text-*); tamanhos soltos em px fora dela são exceção e ficam visíveis aqui.
describe('legibilidade', () => {
  it('styles.css não declara fontes abaixo de 12px', () => {
    const sizes = [...css.matchAll(/(?:font-size|--text-[a-z]+):\s*([0-9.]+)px/g)].map((match) => Number(match[1]));
    expect(sizes.length).toBeGreaterThanOrEqual(4);
    expect(sizes.filter((size) => size < 12)).toEqual([]);
  });

  it('o texto da interface usa só a escala de cinco tamanhos', () => {
    const declared = [...css.matchAll(/font-size:\s*([^;}]+)/g)].map((match) => match[1].trim());
    const allowed = new Set(['var(--text-meta)', 'var(--text-body)', 'var(--text-lead)', 'var(--text-section)', 'var(--text-page)']);
    expect(declared.filter((value) => !allowed.has(value) && !value.startsWith('--'))).toEqual([]);
  });
});
