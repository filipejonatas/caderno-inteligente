import { lazy, Suspense, useCallback, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { matchPath, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { loadDashboard } from './api';
import { ErrorState, LoadingState, Sidebar, Topbar, navigation } from './components';
import type { DashboardData, SelectedSku } from './types';
import './App.css';

const GuidePage = lazy(() => import('./pages/GuidePage'));
const OverviewPage = lazy(() => import('./pages/OverviewPage'));
const PrioritiesPage = lazy(() => import('./pages/PrioritiesPage'));
const ForecastsPage = lazy(() => import('./pages/ForecastsPage'));
const CasesPage = lazy(() => import('./pages/CasesPage'));
const QualityPage = lazy(() => import('./pages/QualityPage'));
const B2BPage = lazy(() => import('./pages/B2BPage'));
const ScenariosPage = lazy(() => import('./pages/ScenariosPage'));
const RunsPage = lazy(() => import('./pages/RunsPage'));
const FeedbackPage = lazy(() => import('./pages/FeedbackPage'));
const SkuDetailPage = lazy(() => import('./pages/SkuDetailPage'));
const NotFoundPage = lazy(() => import('./pages/NotFoundPage'));

function App() {
  const location = useLocation();
  const navigate = useNavigate();
  const [data, setData] = useState<DashboardData>();
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
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

  const requiresDashboard = ['/', '/prioridades', '/casos', '/qualidade', '/parceiros', '/cenarios', '/execucoes', '/decisoes'].includes(location.pathname);

  useEffect(() => {
    if (requiresDashboard && !data) void refresh();
  }, [data, refresh, requiresDashboard]);
  useEffect(() => { window.scrollTo({ top: 0 }); setMenuOpen(false); }, [location.pathname]);

  const current = useMemo(() => {
    if (matchPath('/skus/:sku', location.pathname)) return { label: 'Detalhe do SKU', description: 'Evidências e recomendação' };
    const item = navigation.find((candidate) => matchPath({ path: candidate.path, end: candidate.path === '/' }, location.pathname));
    return item ?? { label: 'Página não encontrada', description: 'Navegação' };
  }, [location.pathname]);

  const selectSku = useCallback((item: SelectedSku) => {
    navigate(`/skus/${encodeURIComponent(item.sku)}`, { state: { from: `${location.pathname}${location.search}` } });
  }, [location.pathname, location.search, navigate]);

  const renderDataPage = (render: (dashboard: DashboardData) => ReactNode) => {
    if (loading) return <LoadingState />;
    if (error && !data) return <ErrorState message={error} onRetry={() => void refresh()} />;
    return data ? render(data) : null;
  };

  const isGuide = location.pathname === '/guia';
  const isSkuDetail = Boolean(matchPath('/skus/:sku', location.pathname));

  return <div className="app-shell">
    <Sidebar open={menuOpen} onClose={() => setMenuOpen(false)} />
    <main className="main-content">
      <Topbar title={current.label} subtitle={current.description} onMenu={() => setMenuOpen(true)} onRefresh={() => void refresh()} refreshing={refreshing} showRefresh={!isGuide && !isSkuDetail} />
      {!isGuide && error && data && <div className="global-warning"><span>!</span>{error}<button onClick={() => void refresh()}>Tentar novamente</button></div>}
      <div className="page-content">
        <Suspense fallback={<LoadingState />}>
          <Routes>
            <Route path="/guia" element={<GuidePage />} />
            <Route path="/" element={renderDataPage((dashboard) => <OverviewPage data={dashboard} onSelect={selectSku} onRefresh={refresh} />)} />
            <Route path="/prioridades" element={renderDataPage((dashboard) => <PrioritiesPage data={dashboard} onSelect={selectSku} onRefresh={refresh} />)} />
            <Route path="/previsoes" element={<ForecastsPage onSelect={selectSku} />} />
            <Route path="/casos" element={renderDataPage((dashboard) => <CasesPage data={dashboard} onSelect={selectSku} onRefresh={refresh} />)} />
            <Route path="/qualidade" element={renderDataPage((dashboard) => <QualityPage data={dashboard} onSelect={selectSku} onRefresh={refresh} />)} />
            <Route path="/parceiros" element={renderDataPage((dashboard) => <B2BPage data={dashboard} onSelect={selectSku} onRefresh={refresh} />)} />
            <Route path="/cenarios" element={renderDataPage((dashboard) => <ScenariosPage data={dashboard} onSelect={selectSku} onRefresh={refresh} />)} />
            <Route path="/execucoes" element={renderDataPage((dashboard) => <RunsPage data={dashboard} onSelect={selectSku} onRefresh={refresh} />)} />
            <Route path="/decisoes" element={renderDataPage((dashboard) => <FeedbackPage data={dashboard} onSelect={selectSku} onRefresh={refresh} />)} />
            <Route path="/skus/:sku" element={<SkuDetailPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </Suspense>
      </div>
    </main>
  </div>;
}

export default App;
