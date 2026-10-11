import { useCallback, useState } from 'react';
import { api, ApiError, DATASET_EXAMPLE_PATH, DATASET_TEMPLATE_PATH, downloadFile } from '../api';
import { ErrorState, LoadingState, PageIntro, SectionCard } from '../components';
import { DatasetUpload } from '../components/DatasetUpload';
import { DatasetVersionsPanel, formatVersionTime } from '../components/DatasetVersions';
import { useApiResource } from '../hooks/useApiResource';
import { usePageLoadStatus } from '../hooks/usePageLoadStatus';
import { readSession } from '../session';
import type { DatasetInfo } from '../types-dataset';
import { formatDate, formatMonth } from './shared';

const ORIGIN_NAMES: Record<DatasetInfo['origin'], string> = { original: 'planilha original', upload: 'planilha enviada', restore: 'versão restaurada', desconhecida: 'não identificada' };

/** Bastidores › Atualizar dados (U.2): base ativa, envio em passos com prévia e histórico de versões. Nada muda sem prévia e confirmação. */
export default function DatasetUpdatePage({ refreshToken, onChanged }: { refreshToken: number; onChanged: () => void }) {
  const token = readSession()?.token ?? '';
  const [downloadError, setDownloadError] = useState('');

  const loader = useCallback(async (signal: AbortSignal) => {
    const info = await api.dataset(token || undefined, signal);
    // O histórico é um bloco a mais: se falhar, a base ativa e o envio continuam disponíveis.
    const versions = await api.datasetVersions(signal).catch(() => null);
    return { info, versions };
  }, [token]);
  const { data, error, loading, loadedAt, refresh } = useApiResource(loader, refreshToken);
  usePageLoadStatus(loading, error, loadedAt);

  const download = (path: string, name: string) => { setDownloadError(''); downloadFile(path, name).catch((caught: unknown) => setDownloadError(caught instanceof Error ? caught.message : 'Não foi possível baixar o arquivo.')); };
  /** 401 em qualquer gravação: o app já encerrou a sessão e voltou para o login. */
  const handleExpired = (caught: unknown) => caught instanceof ApiError && caught.status === 401;

  if (!data && error) return <ErrorState message={error} onRetry={() => void refresh()} />;
  if (!data) return <LoadingState />;
  const { info, versions } = data;
  // O servidor decide (banco, gravação ligada e login): upload_enabled já reflete o token enviado.
  const canWrite = info.upload_enabled;

  return <>
    <PageIntro title="Atualizar a base pela planilha" description="Envie a planilha, confira a prévia e só então aplique." />

    <SectionCard title="Base ativa" className="dataset-active" action={<span className="form-actions">
      <button type="button" className="secondary-button" onClick={() => download(DATASET_TEMPLATE_PATH, 'modelo-caderno-inteligente.xlsx')}>Baixar modelo (.xlsx)</button>
      <button type="button" className="secondary-button" title="Planilha preenchida com números fictícios, só para treinar o envio." onClick={() => download(DATASET_EXAMPLE_PATH, 'atualizacao-exemplo.xlsx')}>Baixar exemplo fictício</button>
    </span>}>
      <dl className="dataset-facts">
        <div><dt>Referência</dt><dd>{formatDate(info.reference_date)}</dd></div>
        <div><dt>Vendas até</dt><dd>{formatMonth(info.sales_last_month)}</dd></div>
        <div><dt>Origem</dt><dd>{ORIGIN_NAMES[info.origin]}</dd></div>
        <div><dt>Versão</dt><dd>{info.version ?? 'Não disponível'}</dd></div>
        {info.uploaded_by && <div><dt>Enviada por</dt><dd>{info.uploaded_by}{info.uploaded_at && <small>{formatVersionTime(info.uploaded_at)}</small>}</dd></div>}
      </dl>
    </SectionCard>

    {downloadError && <p className="inline-error" role="alert">{downloadError}</p>}
    <DatasetUpload info={info} token={token} onExpired={handleExpired} onApplied={onChanged} />

    <DatasetVersionsPanel versions={versions} enabled={canWrite} token={token} version={info.version} onExpired={handleExpired} onRestored={onChanged} />
  </>;
}
