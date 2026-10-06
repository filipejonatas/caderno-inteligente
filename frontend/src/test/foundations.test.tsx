import { act, renderHook } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { useMediaQuery } from '../hooks/useMediaQuery';
import { answerToneFor } from '../pages/SkuDetailPage';

describe('useMediaQuery', () => {
  it('reavalia quando a janela muda de breakpoint', () => {
    let current = false;
    const listeners = new Set<() => void>();
    window.matchMedia = ((query: string) => ({
      get matches() { return current; }, media: query,
      addEventListener: (_: string, fn: () => void) => listeners.add(fn),
      removeEventListener: (_: string, fn: () => void) => listeners.delete(fn),
    })) as unknown as typeof window.matchMedia;
    const { result, unmount } = renderHook(() => useMediaQuery('(max-width: 620px)'));
    expect(result.current).toBe(false);
    act(() => { current = true; listeners.forEach((fn) => fn()); });
    expect(result.current).toBe(true);
    unmount();
    expect(listeners.size).toBe(0);
  });
});

describe('answerToneFor', () => {
  it('capacidade a validar nunca usa aparência de sucesso', () => {
    expect(answerToneFor('produzir_validar_capacidade', 'requires_review', 'alta', 'alta', false)).toBe('review');
  });
  it.each([
    ['investigar_dados', 'not_evaluated', 'média', 'média', false],
    ['produzir', 'family_context_available', 'baixa', 'alta', false],
    ['produzir', 'family_context_available', 'alta', 'baixa', false],
    ['produzir', 'not_evaluated', 'alta', 'alta', true],
    ['sem_acao_necessaria', 'requires_review', 'alta', 'alta', false],
  ])('%s exige revisão', (action, capacity, confidence, ranking, insufficient) => {
    expect(answerToneFor(action, capacity, confidence, ranking, insufficient)).toBe('review');
  });
  it('recomendação normal é informativa, não verde', () => {
    expect(answerToneFor('produzir', 'family_context_available', 'alta', 'média', false)).toBe('info');
    expect(answerToneFor('sem_acao_necessaria', 'not_evaluated', 'alta', 'alta', false)).toBe('info');
  });
});
