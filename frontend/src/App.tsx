import { useCallback, useEffect, useMemo, useState } from 'react';
import { loadDashboard } from './api';
import { ErrorState, LoadingState, Sidebar, Topbar, navigation } from './components';
import {
  B2BPage,
  CasesPage,
  FeedbackPage,
  GuidePage,
  OverviewPage,
  PrioritiesPage,
  QualityPage,
  RunsPage,
  ScenariosPage,
  SkuDrawer,
} from './pages';
import type { DashboardData, PageId, Priority } from './types';
import './App.css';

function App() {
  const [page, setPage] = useState<PageId>('overview');
  const [data, setData] = useState<DashboardData>();
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [selectedPriority, setSelectedPriority] = useState<Priority | null>(null);

  const refresh = useCallback(async () => {
    setRefreshing(true);
    setError('');
    try {
      setData(await loadDashboard());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Ocorreu um erro inesperado.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);
  useEffect(() => { window.scrollTo({ top: 0 }); }, [page]);

  const navigate = useCallback((nextPage: PageId) => {
    setSelectedPriority(null);
    setPage(nextPage);
  }, []);

  const current = useMemo(() => navigation.find((item) => item.id === page) ?? navigation[0], [page]);
  const shared = data ? { data, onSelect: setSelectedPriority, onRefresh: refresh } : undefined;

  function content() {
    if (page === 'guide') return <GuidePage onNavigate={navigate} />;
    if (loading) return <LoadingState />;
    if (error && !data) return <ErrorState message={error} onRetry={() => void refresh()} />;
    if (!shared) return null;
    switch (page) {
      case 'priorities': return <PrioritiesPage {...shared} />;
      case 'cases': return <CasesPage {...shared} />;
      case 'quality': return <QualityPage {...shared} />;
      case 'b2b': return <B2BPage {...shared} />;
      case 'scenarios': return <ScenariosPage {...shared} />;
      case 'runs': return <RunsPage {...shared} />;
      case 'feedback': return <FeedbackPage {...shared} />;
      default: return <OverviewPage {...shared} />;
    }
  }

  return <div className="app-shell">
    <Sidebar page={page} open={menuOpen} onNavigate={navigate} onClose={() => setMenuOpen(false)} />
    <main className="main-content">
      <Topbar title={current.label} subtitle={current.description} onMenu={() => setMenuOpen(true)} onRefresh={() => void refresh()} refreshing={refreshing} showRefresh={page !== 'guide'} />
      {page !== 'guide' && error && data && <div className="global-warning"><span>!</span>{error}<button onClick={() => void refresh()}>Tentar novamente</button></div>}
      <div className="page-content">{content()}</div>
    </main>
    <SkuDrawer priority={selectedPriority} onClose={() => setSelectedPriority(null)} />
  </div>;
}

export default App;
