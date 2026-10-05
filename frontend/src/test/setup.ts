import '@testing-library/jest-dom/vitest';
import { cleanup, configure } from '@testing-library/react';
import { afterEach, beforeEach, vi } from 'vitest';

// Lazy route chunks load slower when every test file runs in parallel; the 1s default caused flaky waits.
configure({ asyncUtilTimeout: 5000 });

/** Tests switch the emulated viewport with setViewport('mobile' | 'desktop'). */
let mobile = false;
export function setViewport(kind: 'mobile' | 'desktop') { mobile = kind === 'mobile'; }

beforeEach(() => {
  mobile = false;
  window.matchMedia = ((query: string) => ({
    matches: query.includes('max-width') ? mobile : false,
    media: query, onchange: null,
    addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {}, dispatchEvent: () => false,
  })) as unknown as typeof window.matchMedia;
  window.scrollTo = vi.fn() as unknown as typeof window.scrollTo;
  Element.prototype.scrollIntoView = vi.fn();
  // jsdom has no canvas; axe-core probes it for icon-font detection. Returning null is the documented fallback.
  HTMLCanvasElement.prototype.getContext = (() => null) as unknown as typeof HTMLCanvasElement.prototype.getContext;
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});
