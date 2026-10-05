import { useState } from 'react';
import type { FormEvent } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api } from '../api';
import { Alert, Badge, EmptyState, PageIntro, SectionCard } from '../components';
import { RunComparisonView } from '../components/RunComparisonView';
import type { PageProps } from './shared';
import { formatDateTime } from './shared';

const parseId = (value: string | null) => value && /^\d+$/.test(value) ? Number(value) : null;

export default function RunsPage({ data, onRefresh }: PageProps<'runs'>) {
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [params, setParams] = useSearchParams();
  const ids = new Set(data.runs.map((run) => run.id));
  const base = parseId(params.get('base'));
  const target = parseId(params.get('alvo'));
  // Defaults: the two most recent runs, older as base (the list is newest first).
  const [draftBase, setDraftBase] = useState(String(base ?? data.runs[1]?.id ?? ''));
  const [draftTarget, setDraftTarget] = useState(String(target ?? data.runs[0]?.id ?? ''));
  const selected = base !== null && target !== null;
  const invalid = selected && (!ids.has(base) || !ids.has(target) || base === target);

  async function snapshot() { setSaving(true); setMessage(''); try { const result = await api.createRun(); await onRefresh(); setMessage(`Execução #${result.id} registrada.`); } catch (error) { setMessage(error instanceof Error ? error.message : 'Falha ao registrar execução.'); } finally { setSaving(false); } }
  function compare(event: FormEvent) { event.preventDefault(); setParams({ base: draftBase, alvo: draftTarget }); }

  return <>
    <PageIntro eyebrow="Auditoria" title="Execuções registradas" description="Snapshots preservam fonte, configuração, ranking, previsão, recomendação e cobertura B2B2C para comparação posterior." action={<button className="primary-button" onClick={snapshot} disabled={saving}>{saving ? 'Registrando…' : 'Registrar execução atual'}</button>} />
    {message && <div className="toast-inline">{message}</div>}
    <SectionCard title="Comparar execuções" subtitle="Escolha a execução base e a execução alvo. O link resultante pode ser compartilhado.">
      {data.runs.length < 2 ? <EmptyState title="São necessárias duas execuções" description="Registre pelo menos duas execuções para comparar mudanças no ranking." /> :
        <form className="run-compare-form" onSubmit={compare}>
          <label>Base<select value={draftBase} onChange={(event) => setDraftBase(event.target.value)}>{data.runs.map((run) => <option key={run.id} value={run.id}>#{run.id} · {formatDateTime(run.created_at)}</option>)}</select></label>
          <label>Alvo<select value={draftTarget} onChange={(event) => setDraftTarget(event.target.value)}>{data.runs.map((run) => <option key={run.id} value={run.id}>#{run.id} · {formatDateTime(run.created_at)}</option>)}</select></label>
          <button className="primary-button" type="submit" disabled={draftBase === draftTarget}>Comparar</button>
          {selected && <button className="secondary-button" type="button" onClick={() => setParams({})}>Fechar comparação</button>}
          {draftBase === draftTarget && <small>Selecione duas execuções diferentes.</small>}
        </form>}
    </SectionCard>
    {invalid && <Alert tone="warning" title="Comparação inválida">{base === target ? 'Base e alvo são a mesma execução.' : 'Uma das execuções do link não existe nesta base.'}</Alert>}
    {selected && !invalid && <RunComparisonView key={`${base}-${target}`} base={base} target={target} refreshToken={0} />}
    <SectionCard title="Histórico" subtitle={`${data.runs.length} snapshots disponíveis.`}>{data.runs.length ? <div className="timeline">{data.runs.map((run) => <article key={run.id}><div className="timeline-dot" /><div><div className="run-title"><strong>Execução #{run.id}</strong><Badge tone="neutral">{run.prioritized_skus} SKUs</Badge><Badge tone={run.comparison_schema_version ? 'good' : 'medium'} title={run.comparison_schema_version ? 'Preserva previsão, recomendação e cobertura B2B2C' : 'Compara apenas o ranking'}>{run.comparison_schema_version ? 'comparação completa' : 'só ranking'}</Badge></div><p>{formatDateTime(run.created_at)}</p><code>{run.source_hash.slice(0, 16)}…</code></div></article>)}</div> : <EmptyState title="Nenhuma execução registrada" description="Crie o primeiro snapshot auditável do ranking." />}</SectionCard>
  </>;
}
