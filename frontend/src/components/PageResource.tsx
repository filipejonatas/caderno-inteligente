import { useCallback } from 'react';
import type { ReactNode } from 'react';
import { loadPageData } from '../api';
import type { DashboardData } from '../types';
import { ErrorState, LoadingState } from '../components';
import { useApiResource } from '../hooks/useApiResource';

export function PageResource<K extends keyof DashboardData>({ fields, refreshToken, children }: {
  fields: readonly K[];
  refreshToken: number;
  children: (data: Pick<DashboardData, K>, refresh: () => Promise<void>) => ReactNode;
}) {
  const loader = useCallback((signal: AbortSignal) => loadPageData(fields, signal), [fields]);
  const { data, error, loading, refresh } = useApiResource(loader, refreshToken);
  if (!data && error) return <ErrorState message={error} onRetry={() => void refresh()} />;
  if (!data) return <LoadingState />;
  return <>
    {error && <div className="global-warning" role="alert">{error}<button onClick={() => void refresh()}>Tentar novamente</button></div>}
    {loading && <p role="status">Atualizando esta página…</p>}
    {children(data, refresh)}
  </>;
}
