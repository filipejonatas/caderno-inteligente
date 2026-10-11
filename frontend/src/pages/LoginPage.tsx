import { useNavigate, useSearchParams } from 'react-router-dom';
import { api } from '../api';
import { PageIntro, SectionCard } from '../components';
import { LoginForm } from '../components/SkuRegistry';
import { readSession, saveSession } from '../session';

/** Só caminhos internos: evita redirecionar para outro site por um `?next=` forjado. */
export const safeNext = (value: string | null) => value && value.startsWith('/') && !value.startsWith('//') && !value.startsWith('/login') ? value : '/dados/atualizar';

/** Tela de entrada: guarda a sessão no navegador e volta para onde a pessoa estava (`?next=`). */
export default function LoginPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const next = safeNext(params.get('next'));
  const expired = params.get('motivo') === 'expirou';
  const signedIn = readSession();

  const signIn = async (email: string, password: string) => {
    saveSession(await api.login(email, password));
    navigate(next, { replace: true });
  };

  return <>
    <PageIntro title="Entrar" description="Entre com seu usuário para atualizar a base pela planilha." />
    <SectionCard title="Acesso">
      {expired && <p className="inline-error" role="alert">Sua sessão expirou. Entre novamente.</p>}
      {signedIn && <p className="dataset-muted" role="status">Você já está conectado como {signedIn.user.name || signedIn.user.email}. <button type="button" className="link-button" onClick={() => navigate(next)}>Continuar</button></p>}
      <LoginForm onSubmit={signIn} disabled={false} label="Entrar" />
    </SectionCard>
  </>;
}
