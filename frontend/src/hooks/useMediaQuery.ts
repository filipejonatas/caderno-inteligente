import { useEffect, useState } from 'react';

const matches = (query: string) => typeof window !== 'undefined' && typeof window.matchMedia === 'function' && window.matchMedia(query).matches;

/** Reativo: reavalia a media query quando a janela é redimensionada. */
export function useMediaQuery(query: string) {
  const [value, setValue] = useState(() => matches(query));
  useEffect(() => {
    const media = window.matchMedia(query);
    const change = () => setValue(media.matches);
    change();
    media.addEventListener('change', change);
    return () => media.removeEventListener('change', change);
  }, [query]);
  return value;
}

/** Breakpoints usados pelas páginas; manter alinhados aos @media do CSS. */
export const MOBILE_MENU_QUERY = '(max-width: 820px)';
export const MOBILE_LIST_QUERY = '(max-width: 620px)';
