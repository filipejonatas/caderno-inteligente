import { useCallback } from 'react';
import { api } from '../api';
import { ErrorState, LoadingState } from '../components';
import { CommercialMethod } from '../components/CommercialMatrix';
import { useApiResource } from '../hooks/useApiResource';
import { usePageLoadStatus } from '../hooks/usePageLoadStatus';
import { AuditoriaContent } from './ValidationPage';

export default function AuditoriaPage({ refreshToken }: { refreshToken: number }) {
  const loader = useCallback(async (signal: AbortSignal) => {
    const [summary, partners] = await Promise.all([api.validationSummary(signal), api.partners(new URLSearchParams({ limit: '1' }), signal)]);
    return { summary, partners };
  }, []);
  const { data, error, loading, loadedAt, refresh } = useApiResource(loader, refreshToken);
  usePageLoadStatus(loading, error, loadedAt);
  if (!data && error) return <ErrorState message={error} onRetry={() => void refresh()} />;
  if (!data) return <LoadingState />;
  return <AuditoriaContent data={data.summary} method={<CommercialMethod response={data.partners} />} />;
}
