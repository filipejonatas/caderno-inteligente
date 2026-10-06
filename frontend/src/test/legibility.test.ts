import { describe, expect, it } from 'vitest';
import appCss from '../App.css?raw';
import usabilityCss from '../usability.css?raw';

// Piso de legibilidade: nenhum texto visível abaixo de 12 px (rótulos só para leitor de tela usam .sr-only e não têm tamanho).
describe('legibilidade', () => {
  for (const [file, css] of [['App.css', appCss], ['usability.css', usabilityCss]] as const) {
    it(`${file} não declara fontes abaixo de 12px`, () => {
      const sizes = [...css.matchAll(/font-size:\s*([0-9.]+)px/g)].map((match) => Number(match[1]));
      expect(sizes.length).toBeGreaterThanOrEqual(file === 'App.css' ? 1 : 0);
      expect(sizes.filter((size) => size < 12)).toEqual([]);
    });
  }
});
