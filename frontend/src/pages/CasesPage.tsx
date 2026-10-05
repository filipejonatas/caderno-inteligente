import { useState } from 'react';
import type { FormEvent } from 'react';
import { api } from '../api';
import { Badge, EmptyState, PageIntro, SectionCard } from '../components';
import type { PageProps } from './shared';
import { formatDate, formatDateTime, statusNames } from './shared';

export default function CasesPage({ data, onRefresh }: PageProps<'cases' | 'priorities' | 'config'>) {
  const [sku, setSku] = useState(data.priorities[0]?.sku ?? '');
  const [owner, setOwner] = useState('');
  const [status, setStatus] = useState('novo');
  const [dueDate, setDueDate] = useState('');
  const [message, setMessage] = useState('');
  const [saving, setSaving] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault(); setSaving(true); setMessage('');
    try { await api.createCase({ sku, owner, status, due_date: dueDate }); await onRefresh(); setMessage('Caso criado e incluído no acompanhamento.'); }
    catch (error) { setMessage(error instanceof Error ? error.message : 'Não foi possível criar o caso.'); }
    finally { setSaving(false); }
  }
  return <>
    <PageIntro eyebrow="Acompanhamento" title="Casos operacionais" description="Transforme um sinal em responsabilidade, prazo e acompanhamento visível." action={<button className="primary-button" onClick={() => document.getElementById('new-case')?.scrollIntoView({ behavior: 'smooth' })}>+ Novo caso</button>} />
    <div className="case-summary"><div><strong>{data.cases.filter((item) => item.status !== 'concluido').length}</strong><span>casos abertos</span></div><div><strong>{data.cases.filter((item) => item.status === 'em_investigacao').length}</strong><span>em investigação</span></div><div><strong>{data.cases.filter((item) => item.status === 'concluido').length}</strong><span>concluídos</span></div></div>
    <SectionCard title="Fila de casos" subtitle="Últimas atualizações primeiro.">{data.cases.length ? <div className="table-shell"><table className="data-table"><thead><tr><th>SKU</th><th>Status</th><th>Responsável</th><th>Prazo</th><th>Atualizado</th></tr></thead><tbody>{data.cases.map((item) => <tr key={item.id}><td><strong>{item.sku}</strong><small>#{item.id}</small></td><td><Badge tone={item.status === 'concluido' ? 'good' : item.status === 'novo' ? 'neutral' : 'medium'}>{statusNames[item.status] ?? item.status}</Badge></td><td>{item.owner || 'Não definido'}</td><td>{formatDate(item.due_date)}</td><td>{formatDateTime(item.updated_at)}</td></tr>)}</tbody></table></div> : <EmptyState title="Nenhum caso criado" description="Crie um caso para acompanhar uma prioridade operacional." />}</SectionCard>
    <SectionCard title="Criar caso" subtitle="Vincule um SKU priorizado a um responsável e prazo." className="form-card"><form id="new-case" className="form-layout" onSubmit={submit}><label>SKU<select required value={sku} onChange={(event) => setSku(event.target.value)}>{data.priorities.map((item) => <option key={item.sku}>{item.sku}</option>)}</select></label><label>Responsável<input value={owner} onChange={(event) => setOwner(event.target.value)} placeholder="Nome ou área" /></label><label>Status<select value={status} onChange={(event) => setStatus(event.target.value)}>{data.config.case_statuses.map((item) => <option key={item} value={item}>{statusNames[item] ?? item}</option>)}</select></label><label>Prazo<input type="date" value={dueDate} onChange={(event) => setDueDate(event.target.value)} /></label><div className="form-actions">{message && <span className="form-message">{message}</span>}<button className="primary-button" disabled={saving}>{saving ? 'Salvando…' : 'Criar caso'}</button></div></form></SectionCard>
  </>;
}
