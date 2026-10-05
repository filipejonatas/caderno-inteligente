import { useState } from 'react';
import { api } from '../api';
import { Badge, EmptyState, PageIntro, SectionCard } from '../components';
import type { PageProps } from './shared';
import { formatDateTime } from './shared';

export default function RunsPage({ data, onRefresh }: PageProps) {
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  async function snapshot() { setSaving(true); setMessage(''); try { const result = await api.createRun(); await onRefresh(); setMessage(`Execução #${result.id} registrada.`); } catch (error) { setMessage(error instanceof Error ? error.message : 'Falha ao registrar execução.'); } finally { setSaving(false); } }
  return <>
    <PageIntro eyebrow="Auditoria" title="Execuções registradas" description="Snapshots preservam fonte, configuração e ranking para consulta posterior." action={<button className="primary-button" onClick={snapshot} disabled={saving}>{saving ? 'Registrando…' : 'Registrar execução atual'}</button>} />
    {message && <div className="toast-inline">{message}</div>}
    <SectionCard title="Histórico" subtitle={`${data.runs.length} snapshots disponíveis.`}>{data.runs.length ? <div className="timeline">{data.runs.map((run) => <article key={run.id}><div className="timeline-dot" /><div><div className="run-title"><strong>Execução #{run.id}</strong><Badge tone="neutral">{run.prioritized_skus} SKUs</Badge></div><p>{formatDateTime(run.created_at)}</p><code>{run.source_hash.slice(0, 16)}…</code></div></article>)}</div> : <EmptyState title="Nenhuma execução registrada" description="Crie o primeiro snapshot auditável do ranking." />}</SectionCard>
  </>;
}
