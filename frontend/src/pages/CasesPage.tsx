import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import type { FormEvent } from 'react';
import { api } from '../api';
import { Badge, EmptyState, PageIntro, SectionCard } from '../components';
import { DEFAULT_TEXT_LIMITS, useSystemInfo } from '../hooks/useSystemInfo';
import type { PageProps } from './shared';
import { formatDate, formatDateTime, statusNames } from './shared';

export default function CasesPage({ data, onRefresh }: PageProps<'cases' | 'priorities' | 'config'>) {
  const [params] = useSearchParams();
  const requestedSku = params.get('sku') ?? '';
  const skus = data.priorities.map((item) => item.sku);
  const skuOptions = requestedSku && !skus.includes(requestedSku) ? [requestedSku, ...skus] : skus;
  const [sku, setSku] = useState(requestedSku || data.priorities[0]?.sku || '');
  const [owner, setOwner] = useState('');
  const [status, setStatus] = useState('novo');
  const [dueDate, setDueDate] = useState('');
  const [message, setMessage] = useState('');
  const [saving, setSaving] = useState(false);
  const system = useSystemInfo();
  const limits = system?.text_limits ?? DEFAULT_TEXT_LIMITS;
  const writeDisabled = system?.write_enabled === false;
  async function submit(event: FormEvent) {
    event.preventDefault(); setSaving(true); setMessage('');
    try { await api.createCase({ sku, owner, status, due_date: dueDate }); await onRefresh(); setMessage('Caso criado e incluído no acompanhamento.'); }
    catch (error) { setMessage(error instanceof Error ? error.message : 'Não foi possível criar o caso.'); }
    finally { setSaving(false); }
  }
  return <>
    <PageIntro title="Casos em acompanhamento" action={requestedSku ? <Link className="secondary-button" to={`/skus/${encodeURIComponent(requestedSku)}`}>Voltar ao SKU {requestedSku}</Link> : undefined} />
    <p className="summary-line"><strong>{data.cases.filter((item) => item.status !== 'concluido').length}</strong> casos abertos · <strong>{data.cases.filter((item) => item.status === 'em_investigacao').length}</strong> em investigação · <strong>{data.cases.filter((item) => item.status === 'concluido').length}</strong> concluídos</p>
    <SectionCard title="Casos abertos e concluídos">{data.cases.length ? <div className="table-shell" tabIndex={0} role="region" aria-label="Fila de casos; role horizontalmente para ver todas as colunas"><table className="data-table"><thead><tr><th>SKU</th><th>Status</th><th>Responsável</th><th>Prazo</th><th>Atualizado</th></tr></thead><tbody>{data.cases.map((item) => <tr key={item.id}><td><strong>{item.sku}</strong><small>#{item.id}</small></td><td><Badge tone={item.status === 'concluido' ? 'good' : item.status === 'novo' ? 'neutral' : 'medium'}>{statusNames[item.status] ?? item.status}</Badge></td><td>{item.owner || 'Não definido'}</td><td>{formatDate(item.due_date)}</td><td>{formatDateTime(item.updated_at)}</td></tr>)}</tbody></table></div> : <EmptyState title="Nenhum caso criado" description="Crie um caso para acompanhar uma prioridade operacional." />}</SectionCard>
    <SectionCard title="Criar caso" className="form-card"><form id="new-case" className="form-layout" onSubmit={submit}><label>SKU<select required value={sku} onChange={(event) => setSku(event.target.value)}>{skuOptions.map((item) => <option key={item}>{item}</option>)}</select></label><label>Responsável<input value={owner} maxLength={limits.owner} onChange={(event) => setOwner(event.target.value)} placeholder="Nome ou área" /></label><label>Status<select value={status} onChange={(event) => setStatus(event.target.value)}>{data.config.case_statuses.map((item) => <option key={item} value={item}>{statusNames[item] ?? item}</option>)}</select></label><label>Prazo<input type="date" value={dueDate} onChange={(event) => setDueDate(event.target.value)} /></label><div className="form-actions">{message && <span className="form-message">{message}</span>}{writeDisabled && <p className="write-disabled-note" role="note">Registro desabilitado nesta publicação (somente leitura).</p>}<button className="primary-button" disabled={saving || writeDisabled}>{saving ? 'Salvando…' : 'Criar caso'}</button></div></form></SectionCard>
  </>;
}
