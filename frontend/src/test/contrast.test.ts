import { describe, expect, it } from 'vitest';
import css from '../App.css?raw';

// WCAG 2.1 AA for normal-size text. Most interface text is 9.5–13px, so the 4.5:1 threshold applies everywhere.
const AA = 4.5;

const root = css.slice(css.indexOf(':root {'), css.indexOf('}', css.indexOf(':root {')));
const tokens = Object.fromEntries([...root.matchAll(/--([\w-]+):\s*(#[0-9a-fA-F]{3,6})/g)].map((match) => [match[1], match[2]]));

function rule(selector: string, property: 'color' | 'background') {
  const block = css.match(new RegExp(`${selector.replace(/[.]/g, '\\.')}[^{]*\\{([^}]*)\\}`))?.[1] ?? '';
  const value = block.match(new RegExp(`(?:^|;)\\s*${property}:\\s*([^;]+)`))?.[1].trim() ?? '';
  return resolve(value);
}

function resolve(value: string): string {
  const token = value.match(/var\(--([\w-]+)\)/)?.[1];
  const color = token ? tokens[token] : value === 'white' ? '#ffffff' : value;
  if (!/^#[0-9a-fA-F]{3,6}$/.test(color ?? '')) throw new Error(`Cor não resolvida: ${value}`);
  return color;
}

function luminance(hex: string) {
  const value = hex.length === 4 ? hex.slice(1).split('').map((c) => c + c).join('') : hex.slice(1);
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(value.slice(i, i + 2), 16) / 255).map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

export function contrast(foreground: string, background: string) {
  const [a, b] = [luminance(foreground), luminance(background)].sort((x, y) => y - x);
  return (a + 0.05) / (b + 0.05);
}

const PAIRS: Array<[string, string, string]> = [
  ['texto secundário sobre branco', resolve('var(--slate-500)'), '#ffffff'],
  ['texto secundário sobre fundo da página', resolve('var(--slate-500)'), resolve('var(--slate-50)')],
  ['texto secundário sobre cabeçalho de tabela', resolve('var(--slate-500)'), '#f9fafc'],
  ['texto padrão sobre branco', resolve('var(--slate-700)'), '#ffffff'],
  ['texto padrão sobre fundo da página', resolve('var(--slate-700)'), resolve('var(--slate-50)')],
  ['título sobre branco', resolve('var(--slate-900)'), '#ffffff'],
  ['link/ação sobre branco', resolve('var(--blue-700)'), '#ffffff'],
  ['link/ação sobre azul claro', resolve('var(--blue-700)'), resolve('var(--blue-50)')],
  ['botão primário', '#ffffff', resolve('var(--blue-700)')],
  ['badge crítico', rule('.badge-critical, .badge-low', 'color'), rule('.badge-critical, .badge-low', 'background')],
  ['badge alto', rule('.badge-high', 'color'), rule('.badge-high', 'background')],
  ['badge médio', rule('.badge-medium', 'color'), rule('.badge-medium', 'background')],
  ['badge bom', rule('.badge-good', 'color'), rule('.badge-good', 'background')],
  ['badge neutro', rule('.badge-neutral', 'color'), rule('.badge-neutral', 'background')],
  ['menu: descrição do item', '#718da3', resolve('var(--navy-900)')],
  ['menu: item', '#a9bdcd', resolve('var(--navy-900)')],
];

describe('contraste de cores (WCAG AA)', () => {
  it.each(PAIRS)('%s', (_name, foreground, background) => {
    expect(contrast(foreground, background)).toBeGreaterThanOrEqual(AA);
  });

  it('calcula razões de referência corretamente', () => {
    expect(contrast('#000000', '#ffffff')).toBeCloseTo(21, 1);
    expect(contrast('#777777', '#ffffff')).toBeCloseTo(4.48, 1);
    // Valor anterior de --slate-500, corrigido nesta etapa por ficar abaixo do AA.
    expect(contrast('#718096', '#ffffff')).toBeLessThan(AA);
  });
});
