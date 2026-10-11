import { Link } from 'react-router-dom';
import { NEXT_STEPS } from '../journey';

/** Rodapé das páginas da jornada: diz o que falta fazer e leva à etapa seguinte. */
export function NextStep({ pathname }: { pathname: string }) {
  const step = NEXT_STEPS[pathname];
  if (!step) return null;
  return <nav className="next-step" aria-label="Próximo passo"><p>{step.text}</p><Link className="secondary-button" to={step.to}>{step.label}</Link></nav>;
}
