import { useCallback, useEffect, useRef, useState } from 'react';

/** Route-local lifecycle; aborted/stale requests cannot overwrite current state. */
export function useApiResource<T>(loader: (signal: AbortSignal) => Promise<T>, refreshToken = 0) {
  const [data, setData] = useState<T>();
  const [error, setError] = useState('');
  const [loadedAt, setLoadedAt] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const active = useRef<AbortController>();
  const refresh = useCallback(async () => {
    active.current?.abort();
    const controller = new AbortController();
    active.current = controller;
    setLoading(true); setError('');
    try {
      const result = await loader(controller.signal);
      if (!controller.signal.aborted) { setData(result); setLoadedAt(Date.now()); }
    } catch (reason) {
      if (!controller.signal.aborted) {
        setError(reason instanceof Error ? reason.message : 'Falha ao carregar esta seção.');
        controller.abort(); // Stop remaining parallel reads when one fails.
      }
    } finally {
      if (active.current === controller) setLoading(false);
    }
  }, [loader]);
  useEffect(() => { setData(undefined); setLoadedAt(null); }, [loader]);
  useEffect(() => {
    void refresh();
    return () => { active.current?.abort(); active.current = undefined; };
  }, [refresh, refreshToken]);
  return { data, error, loading, loadedAt, refresh };
}
