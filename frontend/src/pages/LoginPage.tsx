import { useEffect } from 'react';
import { api } from '../api';
import { LoginForm } from '../components/SkuRegistry';
import { saveSession } from '../session';
import type { Session } from '../session';

/** Primeira tela do sistema: nada mais carrega até a pessoa entrar. Depois do login o app abre a tela inicial. */
export default function LoginPage({ expired, onSignedIn }: { expired: boolean; onSignedIn: (session: Session) => void }) {
  useEffect(() => { document.title = 'Entrar · Caderno Inteligente'; }, []);
  const signIn = async (email: string, password: string) => onSignedIn(saveSession(await api.login(email, password)));

  return <main className="login-screen" id="conteudo">
    <div className="login-card">
      <p className="login-brand">Caderno Inteligente</p>
      <h1 id="page-title">Entrar</h1>
      <p className="dataset-muted">Entre com seu usuário para ver as recomendações e atualizar a base.</p>
      {expired && <p className="inline-error" role="alert">Sua sessão expirou. Entre novamente.</p>}
      <LoginForm onSubmit={signIn} disabled={false} label="Entrar" />
    </div>
  </main>;
}
