import { useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import type { FormEvent } from 'react';
import { api } from '../api';
import { Badge, EmptyState, PageIntro, SectionCard } from '../components';
import { DEFAULT_TEXT_LIMITS, useSystemInfo } from '../hooks/useSystemInfo';
import type { CaseItem } from '../types';
import type { PageProps } from './shared';
import { caseOverdueDays, formatDate, formatDateTime, statusNames } from './shared';

const NO_OWNER = '__sem_responsavel__';
type Draft = { status: string; owner: string; due_date: string };
type Failure = { message: string; retry: () => void };

const isOpen = (item: CaseItem) => item.status !== 'concluido';
const overdueText = (days: number) => `Vencido há ${days} ${days === 1 ? 'dia' : 'dias'}`;

/** Abertos vencidos primeiro, depois abertos por prazo (sem prazo por último), concluídos ao fim. */
function orderCases(items: CaseItem[], today?: string) {
  const rank = (item: CaseItem) => !isOpen(item) ? 2 : caseOverdueDays(item, today) !== null ? 0 : 1;
  return [...items].sort((left, right) => rank(left) - rank(right) || (left.due_date || '9999-12-31').localeCompare(right.due_date || '9999-12-31') || left.id - right.id);
}

export default function CasesPage({ data, onRefresh }: PageProps<'cases' | 'priorities' | 'config'>) {
  const [params, setParams] = useSearchParams();
  const requestedSku = params.get('sku') ?? '';
  const statusFilter = params.get('status') ?? '';
  const ownerFilter = params.get('responsavel') ?? '';
  const skus = data.priorities.map((item) => item.sku);
  const skuOptions = requestedSku && !skus.includes(requestedSku) ? [requestedSku, ...skus] : skus;
  // O SKU só vem preenchido quando o usuário chegou com ?sku= (detalhe do SKU); nunca é escolhido em silêncio.
  const [sku, setSku] = useState(requestedSku);
  const [owner, setOwner] = useState('');
  const [status, setStatus] = useState('novo');
  const [dueDate, setDueDate] = useState('');
  const [createError, setCreateError] = useState('');
  const [notice, setNotice] = useState('');
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<number | null>(null);
  const [draft, setDraft] = useState<Draft>({ status: 'novo', owner: '', due_date: '' });
  const [saving, setSaving] = useState<Set<number>>(new Set());
  const [failures, setFailures] = useState<Record<number, Failure>>({});
  const system = useSystemInfo();
  const limits = system?.text_limits ?? DEFAULT_TEXT_LIMITS;
  const writeDisabled = system?.write_enabled === false;

  const owners = useMemo(() => [...new Set(data.cases.map((item) => item.owner).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'pt-BR')), [data.cases]);
  const ordered = useMemo(() => orderCases(data.cases), [data.cases]);
  const visible = ordered.filter((item) => (!statusFilter || item.status === statusFilter) && (!ownerFilter || (ownerFilter === NO_OWNER ? !item.owner : item.owner === ownerFilter)));
  const overdue = data.cases.filter((item) => caseOverdueDays(item) !== null).length;
  const filtersActive = !!(statusFilter || ownerFilter);

  const setFilter = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value); else next.delete(key);
    setParams(next, { replace: true });
  };

  async function submit(event: FormEvent) {
    event.preventDefault(); setNotice(''); setCreateError('');
    if (!sku) { setCreateError('Escolha o SKU do caso.'); return; }
    setCreating(true);
    try { await api.createCase({ sku, owner, status, due_date: dueDate }); await onRefresh(); setNotice('Caso criado e incluído no acompanhamento.'); }
    catch (error) { setCreateError(error instanceof Error ? error.message : 'Não foi possível criar o caso.'); }
    finally { setCreating(false); }
  }

  /** Atualiza só este caso. Action e note seguem como estão: a API substitui o registro inteiro. */
  async function save(item: CaseItem, changes: Partial<Draft>) {
    const payload = { status: changes.status ?? item.status, owner: changes.owner ?? item.owner, due_date: changes.due_date ?? item.due_date, action: item.action, note: item.note };
    setSaving((current) => new Set(current).add(item.id));
    setFailures((current) => { const { [item.id]: _removed, ...rest } = current; return rest; });
    setNotice('');
    try {
      await api.updateCase(item.id, payload);
      await onRefresh();
      setNotice(`Caso #${item.id} do SKU ${item.sku} atualizado.`);
      setEditing((current) => current === item.id ? null : current);
    } catch (error) {
      setFailures((current) => ({ ...current, [item.id]: { message: error instanceof Error ? error.message : 'Não foi possível atualizar o caso.', retry: () => void save(item, changes) } }));
    } finally {
      setSaving((current) => { const next = new Set(current); next.delete(item.id); return next; });
    }
  }

  const startEditing = (item: CaseItem) => { setEditing(item.id); setDraft({ status: item.status, owner: item.owner, due_date: item.due_date }); setNotice(''); };
  const rowsBlocked = (id: number) => saving.has(id);
  const columns = 5;

  return <>
    <PageIntro title="Casos em acompanhamento" action={requestedSku ? <Link className="secondary-button" to={`/skus/${encodeURIComponent(requestedSku)}`}>Voltar ao SKU {requestedSku}</Link> : undefined} />
    <p className="summary-line"><strong>{data.cases.filter(isOpen).length}</strong> casos abertos · <strong>{overdue}</strong> vencidos · <strong>{data.cases.filter((item) => item.status === 'em_investigacao').length}</strong> em investigação · <strong>{data.cases.filter((item) => !isOpen(item)).length}</strong> concluídos</p>
    <div className="feedback-live" aria-live="polite">{notice && <span className="form-message">{notice}</span>}</div>
    {writeDisabled && <p className="write-disabled-note" role="note">Edição desabilitada nesta publicação (somente leitura).</p>}
    {data.cases.length > 0 && <div className="filter-bar" role="search" aria-label="Filtrar casos">
      <label><span>Status</span><select value={statusFilter} onChange={(event) => setFilter('status', event.target.value)}><option value="">Todos</option>{data.config.case_statuses.map((item) => <option key={item} value={item}>{statusNames[item] ?? item}</option>)}</select></label>
      <label><span>Responsável</span><select value={ownerFilter} onChange={(event) => setFilter('responsavel', event.target.value)}><option value="">Todos</option>{owners.map((item) => <option key={item}>{item}</option>)}<option value={NO_OWNER}>Sem responsável</option></select></label>
      <div className="filter-count" role="status"><strong>{visible.length}</strong><span>de {data.cases.length} casos</span></div>
      {filtersActive && <button className="secondary-button" onClick={() => setParams({}, { replace: true })}>Limpar filtros</button>}
    </div>}
    <SectionCard title="Casos abertos e concluídos">{data.cases.length ? visible.length ? <div className="table-shell case-table" tabIndex={0} role="region" aria-label="Fila de casos; role horizontalmente para ver todas as colunas"><table className="data-table responsive-table">
      <caption className="sr-only">Casos por situação: vencidos primeiro, depois abertos por prazo, depois concluídos</caption>
      <thead><tr><th>SKU</th><th>Status</th><th>Responsável</th><th>Prazo</th><th>Ações</th></tr></thead>
      <tbody>{visible.map((item) => {
        const late = caseOverdueDays(item);
        const busy = rowsBlocked(item.id);
        const failure = failures[item.id];
        return [
          <tr key={item.id} className={late !== null ? 'case-overdue' : undefined} aria-busy={busy || undefined}>
            <td data-label="SKU"><strong>{item.sku}</strong><small>#{item.id} · atualizado {formatDateTime(item.updated_at)}</small></td>
            <td data-label="Status"><Badge tone={item.status === 'concluido' ? 'good' : item.status === 'novo' ? 'neutral' : 'medium'}>{statusNames[item.status] ?? item.status}</Badge></td>
            <td data-label="Responsável">{item.owner || 'Não definido'}</td>
            <td className="cell-stack" data-label="Prazo">{item.due_date ? formatDate(item.due_date) : 'Sem prazo'}{late !== null && <Badge tone="low">{overdueText(late)}</Badge>}</td>
            <td className="cell-action" data-label="Ações"><div className="case-actions">
              <button type="button" className="secondary-button" disabled={writeDisabled || busy} aria-expanded={editing === item.id} aria-label={`Editar caso #${item.id} do SKU ${item.sku}`} onClick={() => editing === item.id ? setEditing(null) : startEditing(item)}>{busy ? 'Salvando…' : 'Editar'}</button>
              {isOpen(item) && <button type="button" className="secondary-button" disabled={writeDisabled || busy} aria-label={`Concluir caso #${item.id} do SKU ${item.sku}`} onClick={() => void save(item, { status: 'concluido' })}>Concluir</button>}
            </div></td>
          </tr>,
          editing === item.id && <tr key={`${item.id}-editor`} className="case-editor-row"><td colSpan={columns}>
            <form className="case-editor" aria-label={`Editar caso #${item.id} do SKU ${item.sku}`} onSubmit={(event) => { event.preventDefault(); void save(item, draft); }}>
              <label>Status do caso<select value={draft.status} onChange={(event) => setDraft({ ...draft, status: event.target.value })}>{[...new Set([...data.config.case_statuses, item.status])].map((value) => <option key={value} value={value}>{statusNames[value] ?? value}</option>)}</select></label>
              <label>Responsável pelo caso<input value={draft.owner} maxLength={limits.owner} onChange={(event) => setDraft({ ...draft, owner: event.target.value })} placeholder="Nome ou área" /></label>
              <label>Prazo do caso<input type="date" value={draft.due_date} onChange={(event) => setDraft({ ...draft, due_date: event.target.value })} /></label>
              <div className="form-actions"><button className="primary-button" disabled={busy || writeDisabled}>{busy ? 'Salvando…' : 'Salvar alterações'}</button><button type="button" className="secondary-button" disabled={busy} onClick={() => setEditing(null)}>Cancelar</button></div>
            </form>
          </td></tr>,
          failure && <tr key={`${item.id}-error`} className="case-error-row"><td colSpan={columns}><div role="alert" className="case-error"><span><strong>Caso #{item.id} não foi atualizado.</strong> {failure.message} Os valores anteriores continuam valendo.</span><button type="button" className="secondary-button" onClick={failure.retry}>Tentar novamente</button></div></td></tr>,
        ];
      })}</tbody></table></div> : <EmptyState title="Nenhum caso neste filtro" description="Ajuste o status ou o responsável, ou limpe os filtros." /> : <EmptyState title="Nenhum caso criado" description="Crie um caso para acompanhar uma prioridade operacional." />}</SectionCard>
    <SectionCard title="Criar caso" className="form-card"><form id="new-case" className="form-layout" onSubmit={submit}>
      <label>SKU<select required value={sku} onChange={(event) => setSku(event.target.value)}><option value="" disabled>Escolha um SKU</option>{skuOptions.map((item) => <option key={item}>{item}</option>)}</select></label>
      <label>Responsável<input value={owner} maxLength={limits.owner} onChange={(event) => setOwner(event.target.value)} placeholder="Nome ou área" /></label>
      <label>Status<select value={status} onChange={(event) => setStatus(event.target.value)}>{data.config.case_statuses.map((item) => <option key={item} value={item}>{statusNames[item] ?? item}</option>)}</select></label>
      <label>Prazo<input type="date" value={dueDate} onChange={(event) => setDueDate(event.target.value)} /></label>
      <div className="form-actions">{createError && <span className="form-message" role="alert">{createError}</span>}{writeDisabled && <p className="write-disabled-note" role="note">Registro desabilitado nesta publicação (somente leitura).</p>}<button className="primary-button" disabled={creating || writeDisabled}>{creating ? 'Salvando…' : 'Criar caso'}</button></div>
    </form></SectionCard>
  </>;
}
