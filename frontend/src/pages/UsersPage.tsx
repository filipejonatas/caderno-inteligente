import type { FormEvent } from 'react';
import { useCallback, useState } from 'react';
import { api } from '../api';
import { ErrorState, LoadingState, PageIntro, SectionCard } from '../components';
import { useApiResource } from '../hooks/useApiResource';
import { readSession } from '../session';
import { formatVersionTime } from '../components/DatasetVersions';

const MIN_PASSWORD = 10;
const messageOf = (error: unknown) => error instanceof Error ? error.message : 'A solicitação falhou.';

/** Cadastro de usuários: quem já entrou cadastra os próximos. Não há cadastro público; o servidor confere o login a cada chamada. */
export default function UsersPage() {
  const token = readSession()?.token ?? '';
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<{ tone: 'error' | 'ok'; text: string } | null>(null);

  const loader = useCallback((signal: AbortSignal) => api.users(token, signal), [token]);
  const { data, error, refresh } = useApiResource(loader, 0);

  if (!data && error) return <ErrorState message={error} onRetry={() => void refresh()} />;
  if (!data) return <LoadingState />;

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true); setNotice(null);
    try {
      const created = await api.createUser(token, { email, name, password });
      setNotice({ tone: 'ok', text: `Usuário ${created.email} cadastrado.` });
      setEmail(''); setName(''); setPassword('');
      void refresh();
    } catch (caught) {
      setNotice({ tone: 'error', text: messageOf(caught) });
      setPassword('');
    } finally { setBusy(false); }
  };

  return <>
    <PageIntro title="Usuários" description="Quem pode entrar para atualizar a base. Qualquer usuário cadastrado pode cadastrar outros." />

    <SectionCard title="Cadastrar usuário">
      <form className="form-layout login-form" aria-label="Cadastrar usuário" onSubmit={(event) => void submit(event)}>
        <label>Nome<input type="text" autoComplete="off" maxLength={80} value={name} onChange={(event) => setName(event.target.value)} /></label>
        <label>E-mail<input type="email" autoComplete="off" required value={email} onChange={(event) => setEmail(event.target.value)} /></label>
        <label>Senha provisória<input type="password" autoComplete="new-password" required minLength={MIN_PASSWORD} value={password} onChange={(event) => setPassword(event.target.value)} /></label>
        <div className="form-actions">
          {notice && <span className={`form-message ${notice.tone === 'error' ? 'form-error' : ''}`} role={notice.tone === 'error' ? 'alert' : 'status'}>{notice.text}</span>}
          <button className="primary-button" disabled={busy}>{busy ? 'Cadastrando…' : 'Cadastrar'}</button>
        </div>
      </form>
      <p className="dataset-muted">A senha precisa ter pelo menos {MIN_PASSWORD} caracteres. Combine a troca da senha provisória com a pessoa por um canal seguro.</p>
    </SectionCard>

    <SectionCard title={`Usuários cadastrados (${data.items.length})`}>
      <div className="table-shell" tabIndex={0} role="region" aria-label="Usuários cadastrados">
        <table className="data-table responsive-table"><caption className="sr-only">Usuários com login</caption>
          <thead><tr><th>Nome</th><th>E-mail</th><th>Situação</th><th>Cadastrado em</th></tr></thead>
          <tbody>{data.items.map((user) => <tr key={user.email}>
            <td data-label="Nome">{user.name || '–'}</td><td data-label="E-mail">{user.email}</td>
            <td data-label="Situação">{user.active ? 'Ativo' : 'Inativo'}</td><td data-label="Cadastrado em">{formatVersionTime(user.created_at)}</td>
          </tr>)}</tbody>
        </table>
      </div>
    </SectionCard>
  </>;
}
