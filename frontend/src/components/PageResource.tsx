import { useCallback } from 'react';
import type { ReactNode } from 'react';
import { loadPageData } from '../api';
import type { DashboardData } from '../types';
import { Alert, ErrorState, LoadingState } from '../components';
import { useApiResource } from '../hooks/useApiResource';
import { usePageLoadStatus } from '../hooks/usePageLoadStatus';

export function PageResource<K extends keyof DashboardData>({ fields, refreshToken, children }: {
  fields: readonly K[];
  refreshToken: number;
  children: (data: Pick<DashboardData, K>, refresh: () => Promise<void>) => ReactNode;
}) {
  const loader = useCallback((signal: AbortSignal) => loadPageData(fields, signal), [fields]);
  const { data, error, loading, loadedAt, refresh } = useApiResource(loader, refreshToken);
  usePageLoadStatus(loading, error, loadedAt);
  if (!data && error) return <ErrorState message={error} onRetry={() => void refresh()} />;
  if (!data) return <LoadingState />;
  return <>
    {error && <Alert tone="warning" title="Não foi possível atualizar" action={<button className="secondary-button" onClick={() => void refresh()}>Tentar novamente</button>}>{error} Os dados exibidos são da última carga bem-sucedida.</Alert>}
    {loading && <p role="status">Atualizando esta página…</p>}
    {children(data, refresh)}
  </>;
}
