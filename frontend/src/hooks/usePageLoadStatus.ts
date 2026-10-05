import { createContext, useContext, useEffect } from 'react';

export interface PageLoadStatus {
  loading: boolean;
  error: string;
  loadedAt: number | null;
}
export const PageLoadContext = createContext<(status: PageLoadStatus) => void>(() => {});

/** Only the route's primary resource reports status; no business data is global. */
export function usePageLoadStatus(loading: boolean, error: string, loadedAt: number | null) {
  const report = useContext(PageLoadContext);
  useEffect(() => { report({ loading, error, loadedAt }); }, [report, loading, error, loadedAt]);
}
