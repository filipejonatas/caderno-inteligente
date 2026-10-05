import { Link } from 'react-router-dom';
import { Icon } from '../components';

export default function NotFoundPage() {
  return <div className="state-card"><div className="state-icon">404</div><h2>Página não encontrada</h2><p>O endereço informado não corresponde a uma página do Caderno Inteligente.</p><Link className="primary-button" to="/"><Icon name="arrow" />Voltar para a visão geral</Link></div>;
}
