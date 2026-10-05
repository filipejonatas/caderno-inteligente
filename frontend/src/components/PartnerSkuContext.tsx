import { useCallback } from 'react';
import { api } from '../api';
import { Alert, ErrorState, LoadingState } from '../components';
import { useApiResource } from '../hooks/useApiResource';
import { CommercialMatrix } from './CommercialMatrix';

export function PartnerSkuContext({ sku, refreshToken }: { sku: string; refreshToken: number }) {
  const loader = useCallback((signal: AbortSignal) => api.commercialRecommendations(new URLSearchParams({ sku, limit: '200' }), signal), [sku]);
  const { data, error, refresh } = useApiResource(loader, refreshToken);
  return <section className="partner-sku-context" aria-labelledby="partner-context-title"><h2 id="partner-context-title">Contexto dos parceiros</h2><p>Visão comercial separada. Nenhum estoque estimado abaixo foi somado ao estoque global do CD.</p>
    {!data ? error ? <ErrorState message={error} onRetry={() => void refresh()} /> : <LoadingState /> : <>
      {error && <Alert title="Contexto comercial não atualizado" tone="warning" action={<button onClick={() => void refresh()}>Tentar novamente</button>}>{error}</Alert>}
      {data.total > data.items.length && <Alert title="Recorte limitado">Exibindo {data.items.length} de {data.total} vínculos. A API oferece paginação.</Alert>}
      <CommercialMatrix response={data} />
    </>}
  </section>;
}
