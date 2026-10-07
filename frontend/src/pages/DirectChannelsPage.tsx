import { useCallback } from 'react';
import { api } from '../api';
import { ErrorState, LoadingState, PageIntro } from '../components';
import { DirectChannelsTab } from '../components/ChannelViews';
import { monthLabel } from '../components/CommercialMatrix';
import { useApiResource } from '../hooks/useApiResource';
import { usePageLoadStatus } from '../hooks/usePageLoadStatus';

/** E-commerce, Marketplace e Loja própria: faturamento observado, sem sell-in nem sell-out. */
export default function DirectChannelsPage({ refreshToken }: { refreshToken: number }) {
  const loader = useCallback((signal: AbortSignal) => api.directChannels(signal), []);
  const { data, error, loading, loadedAt, refresh } = useApiResource(loader, refreshToken);
  usePageLoadStatus(loading, error, loadedAt);
  if (!data) return error ? <ErrorState message={error} onRetry={() => void refresh()} /> : <LoadingState />;
  return <>
    <PageIntro title="Canais diretos: faturamento observado" description={`Dados até ${monthLabel(data.reference_month)}.`} />
    <DirectChannelsTab data={data} />
  </>;
}
