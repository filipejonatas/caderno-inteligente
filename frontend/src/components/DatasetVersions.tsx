import { useState } from 'react';
import { api, ApiError } from '../api';
import { Badge, SectionCard } from '../components';
import { formatDate, formatMonth } from '../pages/shared';
import type { DatasetVersionRow, DatasetVersions } from '../types-dataset';

type Pending = number | 'original' | null;
type Notice = { tone: 'error' | 'ok'; text: string } | null;

const messageOf = (error: unknown) => error instanceof Error ? error.message : 'A solicitação falhou.';
const dateTime = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' });
/** Data e hora do backend: sem fuso (ex. "2026-10-12 09:30:00") vale UTC, e o espaço vira "T" (Safari não lê o formato com espaço). */
export function formatVersionTime(value: string | null | undefined): string {
  if (!value) return 'Não disponível';
  const iso = /\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}(:?\d{2})?)$/i.test(value) ? value.replace(' ', 'T') : `${value.replace(' ', 'T')}Z`;
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? 'Não disponível' : dateTime.format(date);
}
/** "script" é a importação inicial (scripts/import_workbook.py), não uma pessoa. */
const who = (email: string) => email === 'script' ? 'importação' : email;

function source(row: DatasetVersionRow) {
  if (row.action === 'original') return 'Base original';
  if (row.action === 'restore') return row.restored_from === null ? 'Volta à original' : `Volta à versão ${row.restored_from}`;
  return row.filename ?? 'Arquivo sem nome';
}

/** Bloco 3: histórico (as 20 últimas versões) com "Voltar para esta versão" e "Restaurar base original"; os dois pedem um segundo clique. */
export function DatasetVersionsPanel({ versions, enabled, token, version, onExpired, onRestored }: {
  versions: DatasetVersions | null; enabled: boolean; token: string; version: number | null; onExpired: (caught: unknown) => boolean; onRestored: () => void;
}) {
  const [pending, setPending] = useState<Pending>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<Notice>(null);
  const items = versions?.items ?? [];

  const restore = async (target: Exclude<Pending, null>) => {
    if (version === null) return;
    setBusy(true); setNotice(null);
    try {
      const result = target === 'original' ? await api.restoreOriginalDataset(token, version) : await api.restoreDatasetVersion(token, target, version);
      setNotice({ tone: 'ok', text: `Base restaurada: referência ${formatDate(result.reference_date)}, vendas até ${formatMonth(result.sales_last_month)}.` });
      onRestored();
    } catch (caught) {
      setNotice({ tone: 'error', text: onExpired(caught) ? 'Sua sessão expirou. Entre novamente.' : messageOf(caught) });
      if (caught instanceof ApiError && caught.status === 409) onRestored(); // a base mudou: recarrega a versão e o histórico
    } finally {
      setBusy(false); setPending(null);
    }
  };

  const confirm = (target: Exclude<Pending, null>, label: string) => <span className="dataset-confirm" role="group" aria-label={label}>
    <button type="button" className="secondary-button" disabled={busy} onClick={() => setPending(null)}>Cancelar</button>
    <button type="button" className="primary-button" disabled={busy} onClick={() => void restore(target)}>{busy ? 'Restaurando…' : 'Confirmar'}</button>
  </span>;

  const original = pending === 'original'
    ? confirm('original', 'Confirmar restauração da base original')
    : <button type="button" className="secondary-button danger-button" disabled={!enabled || busy} onClick={() => setPending('original')}>Restaurar base original</button>;

  return <SectionCard title="Histórico de versões" className="dataset-history" action={original}>
    {notice && <p className={notice.tone === 'error' ? 'inline-error' : 'toast-inline'} role={notice.tone === 'error' ? 'alert' : 'status'}>{notice.text}</p>}
    {items.length === 0 ? <p className="dataset-muted">Sem versões guardadas: a base ainda não foi atualizada pela tela.</p>
      : <div className="table-shell" tabIndex={0} role="region" aria-label="Histórico de versões; role horizontalmente para ver todas as colunas">
        <table className="data-table responsive-table dataset-versions"><caption className="sr-only">Versões guardadas da base, da mais recente para a mais antiga</caption>
          <thead><tr><th>Quando</th><th>Quem</th><th>Arquivo</th><th>Referência</th><th>Ação</th></tr></thead>
          <tbody>{items.map((row) => {
            const when = formatVersionTime(row.created_at);
            return <tr key={row.id} className={row.active ? 'is-active' : ''}>
              <td data-label="Quando">{when}</td>
              <td data-label="Quem">{who(row.user_email)}</td>
              <td data-label="Arquivo"><strong>{source(row)}</strong></td>
              <td data-label="Referência">{formatDate(row.reference_date)}<small>vendas {formatMonth(row.sales_last_month)}</small></td>
              <td data-label="Ação" className="cell-action">{row.active ? <Badge tone="good">Ativa</Badge>
                : pending === row.id ? confirm(row.id, `Confirmar volta para a versão de ${when}`)
                  : <button type="button" className="secondary-button evidence-toggle" disabled={!enabled || busy} aria-label={`Voltar para esta versão (${when})`} onClick={() => setPending(row.id)}>Voltar para esta versão</button>}</td>
            </tr>;
          })}</tbody>
        </table>
      </div>}
  </SectionCard>;
}
