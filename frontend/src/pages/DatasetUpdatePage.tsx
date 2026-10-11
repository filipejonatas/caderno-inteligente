import { useCallback, useEffect, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { api, ApiError, DATASET_EXAMPLE_URL, DATASET_TEMPLATE_URL } from '../api';
import { ErrorState, LoadingState, PageIntro, SectionCard } from '../components';
import { DatasetUpload } from '../components/DatasetUpload';
import { DatasetVersionsPanel, formatVersionTime } from '../components/DatasetVersions';
import { useApiResource } from '../hooks/useApiResource';
import { usePageLoadStatus } from '../hooks/usePageLoadStatus';
import { clearSession, readSession } from '../session';
import type { Session } from '../session';
import type { DatasetInfo } from '../types-dataset';
import { formatDate, formatMonth } from './shared';

const ORIGIN_NAMES: Record<DatasetInfo['origin'], string> = { original: 'planilha original', upload: 'planilha enviada', restore: 'versão restaurada', desconhecida: 'não identificada' };

/** Bastidores › Atualizar dados (U.2): base ativa, envio em passos com prévia e histórico de versões. Nada muda sem prévia e confirmação. */
export default function DatasetUpdatePage({ refreshToken, onChanged }: { refreshToken: number; onChanged: () => void }) {
  const [session, setSession] = useState<Session | null>(() => readSession());
  const [expired, setExpired] = useState(false);
  const location = useLocation();
  const token = session?.token ?? '';

  const loader = useCallback(async (signal: AbortSignal) => {
    // Token vencido no GET: a base ativa continua visível, sem login (o motivo volta a ser "login").
    let stale = false;
    const info = await api.dataset(token || undefined, signal).catch((caught: unknown) => {
      if (!token || !(caught instanceof ApiError) || caught.status !== 401) throw caught;
      stale = true;
      return api.dataset(undefined, signal);
    });
    // O histórico é um bloco a mais: se falhar, a base ativa e o envio continuam disponíveis.
    const versions = await api.datasetVersions(signal).catch(() => null);
    // Token guardado, mas o servidor ainda pede login: a sessão local venceu.
    if (token && info.upload_disabled_reason === 'login') stale = true;
    return { info, versions, stale };
  }, [token]);
  const { data, error, loading, loadedAt, refresh } = useApiResource(loader, refreshToken);
  usePageLoadStatus(loading, error, loadedAt);

  const expire = useCallback(() => { clearSession(); setSession(null); setExpired(true); }, []);
  useEffect(() => { if (data?.stale) expire(); }, [data?.stale, expire]);

  const signOut = () => { clearSession(); setSession(null); };
  /** 401 em qualquer gravação encerra a sessão local e volta ao login. */
  const handleExpired = (caught: unknown) => {
    if (!(caught instanceof ApiError) || caught.status !== 401) return false;
    expire();
    return true;
  };

  if (!data && error) return <ErrorState message={error} onRetry={() => void refresh()} />;
  if (!data) return <LoadingState />;
  const { info, versions } = data;
  // O login mora em /login; o servidor decide quando ele é preciso (motivo "login") e a pessoa volta para cá depois de entrar.
  if (!session && info.upload_disabled_reason === 'login') {
    const next = encodeURIComponent(`${location.pathname}${location.search}`);
    return <Navigate to={`/login?next=${next}${expired ? '&motivo=expirou' : ''}`} replace />;
  }
  // O servidor decide (banco, gravação ligada e login): upload_enabled já reflete o token enviado.
  const canWrite = info.upload_enabled;

  return <>
    <PageIntro title="Atualizar a base pela planilha" description="Envie a planilha, confira a prévia e só então aplique." />

    <SectionCard title="Base ativa" className="dataset-active" action={<span className="form-actions"><a className="secondary-button" href={DATASET_TEMPLATE_URL} download>Baixar modelo (.xlsx)</a><a className="secondary-button" href={DATASET_EXAMPLE_URL} download title="Planilha preenchida com números fictícios, só para treinar o envio.">Baixar exemplo fictício</a></span>}>
      <dl className="dataset-facts">
        <div><dt>Referência</dt><dd>{formatDate(info.reference_date)}</dd></div>
        <div><dt>Vendas até</dt><dd>{formatMonth(info.sales_last_month)}</dd></div>
        <div><dt>Origem</dt><dd>{ORIGIN_NAMES[info.origin]}</dd></div>
        <div><dt>Versão</dt><dd>{info.version ?? 'Não disponível'}</dd></div>
        {info.uploaded_by && <div><dt>Enviada por</dt><dd>{info.uploaded_by}{info.uploaded_at && <small>{formatVersionTime(info.uploaded_at)}</small>}</dd></div>}
      </dl>
    </SectionCard>

    <DatasetUpload info={info} session={session} token={token} onSignOut={signOut} onExpired={handleExpired} onApplied={onChanged} />

    <DatasetVersionsPanel versions={versions} enabled={canWrite} token={token} version={info.version} onExpired={handleExpired} onRestored={onChanged} />
  </>;
}
