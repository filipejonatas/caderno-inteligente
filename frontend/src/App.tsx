import { lazy, Suspense, useCallback, useEffect, useMemo, useState } from 'react';
import { matchPath, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { PageResource } from './components/PageResource';
import { LoadingState, Sidebar, Topbar, navigation } from './components';
import type { SelectedSku } from './types';
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

const PAGE_FIELDS = {
  OverviewPage: ['overview', 'priorities', 'quality'],
  PrioritiesPage: ['priorities'],
  CasesPage: ['cases', 'priorities', 'config'],
  QualityPage: ['quality'],
  B2BPage: ['b2b'],
  ScenariosPage: ['config'],
  RunsPage: ['runs'],
  FeedbackPage: ['feedback', 'priorities', 'config'],
} as const;

function App() {
  const location = useLocation();
  const navigate = useNavigate();
  const [refreshToken, setRefreshToken] = useState(0);
  const [menuOpen, setMenuOpen] = useState(false);
  const refresh = () => setRefreshToken(token => token + 1);

  useEffect(() => { window.scrollTo({ top: 0 }); setMenuOpen(false); }, [location.pathname]);

  const current = useMemo(() => {
    if (matchPath('/skus/:sku', location.pathname)) return { label: 'Detalhe do SKU', description: 'Evidências e recomendação' };
    const item = navigation.find((candidate) => matchPath({ path: candidate.path, end: candidate.path === '/' }, location.pathname));
    return item ?? { label: 'Página não encontrada', description: 'Navegação' };
  }, [location.pathname]);

  const selectSku = useCallback((item: SelectedSku) => {
    navigate(`/skus/${encodeURIComponent(item.sku)}`, { state: { from: `${location.pathname}${location.search}` } });
  }, [location.pathname, location.search, navigate]);

  const isGuide = location.pathname === '/guia';
  const isSkuDetail = Boolean(matchPath('/skus/:sku', location.pathname));

  return <div className="app-shell">
    <Sidebar open={menuOpen} onClose={() => setMenuOpen(false)} />
    <main className="main-content">
      <Topbar title={current.label} subtitle={current.description} onMenu={() => setMenuOpen(true)} onRefresh={() => void refresh()} refreshing={false} showRefresh={!isGuide && !isSkuDetail && current.label !== 'Página não encontrada'} />
      <div className="page-content">
        <Suspense fallback={<LoadingState />}>
          <Routes>
            <Route path="/guia" element={<GuidePage />} />
            <Route path="/" element={<PageResource key="OverviewPage" fields={PAGE_FIELDS.OverviewPage} refreshToken={refreshToken}>{(dashboard, reload) => <OverviewPage data={dashboard} onSelect={selectSku} onRefresh={reload} />}</PageResource>} />
            <Route path="/prioridades" element={<PageResource key="PrioritiesPage" fields={PAGE_FIELDS.PrioritiesPage} refreshToken={refreshToken}>{(dashboard, reload) => <PrioritiesPage data={dashboard} onSelect={selectSku} onRefresh={reload} />}</PageResource>} />
            <Route path="/previsoes" element={<ForecastsPage onSelect={selectSku} refreshToken={refreshToken} />} />
            <Route path="/casos" element={<PageResource key="CasesPage" fields={PAGE_FIELDS.CasesPage} refreshToken={refreshToken}>{(dashboard, reload) => <CasesPage data={dashboard} onSelect={selectSku} onRefresh={reload} />}</PageResource>} />
            <Route path="/qualidade" element={<PageResource key="QualityPage" fields={PAGE_FIELDS.QualityPage} refreshToken={refreshToken}>{(dashboard, reload) => <QualityPage data={dashboard} onSelect={selectSku} onRefresh={reload} />}</PageResource>} />
            <Route path="/parceiros" element={<PageResource key="B2BPage" fields={PAGE_FIELDS.B2BPage} refreshToken={refreshToken}>{(dashboard, reload) => <B2BPage data={dashboard} onSelect={selectSku} onRefresh={reload} />}</PageResource>} />
            <Route path="/cenarios" element={<PageResource key="ScenariosPage" fields={PAGE_FIELDS.ScenariosPage} refreshToken={refreshToken}>{(dashboard, reload) => <ScenariosPage data={dashboard} onSelect={selectSku} onRefresh={reload} />}</PageResource>} />
            <Route path="/execucoes" element={<PageResource key="RunsPage" fields={PAGE_FIELDS.RunsPage} refreshToken={refreshToken}>{(dashboard, reload) => <RunsPage data={dashboard} onSelect={selectSku} onRefresh={reload} />}</PageResource>} />
            <Route path="/decisoes" element={<PageResource key="FeedbackPage" fields={PAGE_FIELDS.FeedbackPage} refreshToken={refreshToken}>{(dashboard, reload) => <FeedbackPage data={dashboard} onSelect={selectSku} onRefresh={reload} />}</PageResource>} />
            <Route path="/skus/:sku" element={<SkuDetailPage key={location.pathname} />} />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </Suspense>
      </div>
    </main>
  </div>;
}

export default App;
