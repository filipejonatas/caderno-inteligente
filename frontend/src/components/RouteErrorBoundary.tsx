import { Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';

interface State { error: Error | null }

/** Contains render errors and failed lazy chunks to the current route instead of blanking the whole app. */
export class RouteErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('route_render_failed', error, info.componentStack);
  }

  render() {
    if (!this.state.error) return this.props.children;
    const chunk = /dynamically imported module|Loading chunk|Failed to fetch/i.test(this.state.error.message);
    return <div className="state-card error-state error-boundary" role="alert">
      <div className="state-icon">!</div>
      <h2>Esta página não pôde ser exibida</h2>
      <p>{chunk ? 'Uma nova versão do aplicativo pode ter sido publicada. Recarregue para obter a versão atual.' : 'Ocorreu um erro inesperado ao montar a página. Os dados de origem não foram alterados.'}</p>
      <div className="validation-actions">
        <button className="primary-button" onClick={() => window.location.reload()}>Recarregar</button>
        <button className="secondary-button" onClick={() => this.setState({ error: null })}>Tentar novamente</button>
        <a className="secondary-button" href="/">Ir para a visão geral</a>
      </div>
    </div>;
  }
}
