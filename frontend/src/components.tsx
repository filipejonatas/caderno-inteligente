import type { ReactNode } from 'react';
import { NavLink } from 'react-router-dom';
import type { PageId, Priority } from './types';

type IconName =
  | 'guide'
  | 'overview'
  | 'priorities'
  | 'forecasts'
  | 'cases'
  | 'quality'
  | 'b2b'
  | 'scenarios'
  | 'runs'
  | 'feedback'
  | 'menu'
  | 'close'
  | 'refresh'
  | 'arrow'
  | 'search';

const iconPaths: Record<IconName, ReactNode> = {
  guide: <><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H11v17H6.5A2.5 2.5 0 0 0 4 22V5.5Z"/><path d="M20 5.5A2.5 2.5 0 0 0 17.5 3H13v17h4.5A2.5 2.5 0 0 1 20 22V5.5Z"/></>,
  overview: <><rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/></>,
  priorities: <><path d="M4 6h16M4 12h10M4 18h7"/><path d="m17 15 3 3 3-4"/></>,
  forecasts: <><path d="M4 19V5M4 19h16"/><path d="m7 15 4-4 3 2 5-6"/><path d="M16 7h3v3"/></>,
  cases: <><path d="M9 5h6l1 2h4v13H4V7h4l1-2Z"/><path d="M9 12h6M9 16h4"/></>,
  quality: <><path d="M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6l-8-3Z"/><path d="m9 12 2 2 4-5"/></>,
  b2b: <><circle cx="8" cy="8" r="3"/><circle cx="17" cy="9" r="2.5"/><path d="M3 20c0-4 2-7 5-7s5 3 5 7M14 14c3-1 6 1 7 5"/></>,
  scenarios: <><path d="M5 4v16M5 7h8a3 3 0 0 1 0 6H5M13 13l6 6"/></>,
  runs: <><path d="M12 3a9 9 0 1 1-8 5"/><path d="M3 3v6h6M12 7v5l3 2"/></>,
  feedback: <><path d="M4 4h16v13H9l-5 4V4Z"/><path d="M8 9h8M8 13h5"/></>,
  menu: <path d="M4 7h16M4 12h16M4 17h16"/>,
  close: <path d="m6 6 12 12M18 6 6 18"/>,
  refresh: <><path d="M20 6v5h-5"/><path d="M18 16a8 8 0 1 1 1-9l1 4"/></>,
  arrow: <path d="m9 18 6-6-6-6"/>,
  search: <><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></>,
};

export function Icon({ name, size = 20 }: { name: IconName; size?: number }) {
  return <svg className="icon" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{iconPaths[name]}</svg>;
}

export const navigation: Array<{ id: PageId; path: string; label: string; description: string }> = [
  { id: 'guide', path: '/guia', label: 'Guia de uso', description: 'Comece por aqui' },
  { id: 'overview', path: '/', label: 'Visão geral', description: 'Pulso da operação' },
  { id: 'priorities', path: '/prioridades', label: 'Prioridades', description: 'Fila de atenção' },
  { id: 'forecasts', path: '/previsoes', label: 'Previsão e recomendações', description: 'Demanda e ação sugerida' },
  { id: 'cases', path: '/casos', label: 'Casos', description: 'Acompanhamento' },
  { id: 'quality', path: '/qualidade', label: 'Qualidade', description: 'Confiabilidade dos dados' },
  { id: 'b2b', path: '/parceiros', label: 'Visibilidade B2B2C', description: 'Cobertura dos parceiros' },
  { id: 'scenarios', path: '/cenarios', label: 'Cenários', description: 'Simulações seguras' },
  { id: 'runs', path: '/execucoes', label: 'Execuções', description: 'Snapshots auditáveis' },
  { id: 'feedback', path: '/decisoes', label: 'Decisões', description: 'Feedback do PCP' },
];

export function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  return <>
    <div className={`sidebar-scrim ${open ? 'is-open' : ''}`} onClick={onClose} aria-hidden="true" />
    <aside className={`sidebar ${open ? 'is-open' : ''}`}>
      <div className="brand">
        <div className="brand-mark">CI</div>
        <div><strong>Caderno</strong><span>Inteligente</span></div>
        <button className="icon-button sidebar-close" onClick={onClose} aria-label="Fechar menu"><Icon name="close" /></button>
      </div>
      <nav aria-label="Navegação principal">
        {navigation.map((item) => <NavLink key={item.id} to={item.path} end={item.path === '/'} className={({ isActive }) => isActive ? 'active' : ''} onClick={onClose}>
          <span className="nav-icon"><Icon name={item.id} /></span>
          <span><strong>{item.label}</strong><small>{item.description}</small></span>
        </NavLink>)}
      </nav>
      <div className="sidebar-note"><span className="status-dot" />Sistema de apoio à decisão<strong>Não libera produção automaticamente</strong></div>
    </aside>
  </>;
}

export function Topbar({ title, subtitle, onMenu, onRefresh, refreshing, showRefresh = true }: { title: string; subtitle: string; onMenu: () => void; onRefresh: () => void; refreshing: boolean; showRefresh?: boolean }) {
  return <header className="topbar">
    <div className="topbar-title">
      <button className="icon-button menu-button" onClick={onMenu} aria-label="Abrir menu"><Icon name="menu" /></button>
      <div><p>{subtitle}</p><h1>{title}</h1></div>
    </div>
    {showRefresh && <button className="secondary-button" onClick={onRefresh} disabled={refreshing}><Icon name="refresh" />{refreshing ? 'Atualizando…' : 'Atualizar dados'}</button>}
  </header>;
}

export function PageIntro({ eyebrow, title, description, action }: { eyebrow: string; title: string; description: string; action?: ReactNode }) {
  return <div className="page-intro"><div><span className="eyebrow">{eyebrow}</span><h2>{title}</h2><p>{description}</p></div>{action}</div>;
}

export function Badge({ children, tone = 'neutral' }: { children: ReactNode; tone?: string }) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}

export function severityTone(severity: string) {
  if (severity === 'crítica') return 'critical';
  if (severity === 'alta') return 'high';
  if (severity === 'média') return 'medium';
  return 'neutral';
}

export function confidenceTone(confidence: string) {
  return confidence === 'baixa' ? 'low' : confidence === 'alta' ? 'good' : 'medium';
}

const shortReason: Record<string, string> = {
  RUP_LEAD_TIME: 'Cobertura abaixo do lead time',
  RUP_SAFETY_STOCK: 'Abaixo do estoque de segurança',
  ORDER_WITHOUT_PRODUCTION: 'Pedido sem produção',
  PRODUCTION_AFTER_PROMISE: 'Produção após a promessa',
  CAPACITY_CONFLICT: 'Capacidade pressionada',
  EXCESS_COVERAGE: 'Excesso de cobertura',
  LOW_SELLOUT_VISIBILITY: 'Baixa visibilidade de sell-out',
};

export function MetricCard({ label, value, detail, tone = 'blue', icon }: { label: string; value: ReactNode; detail: string; tone?: string; icon: IconName }) {
  return <article className={`metric-card metric-${tone}`}><div className="metric-icon"><Icon name={icon} /></div><div><span>{label}</span><strong>{value}</strong><small>{detail}</small></div></article>;
}

const formatDate = (value: string | null) => value
  ? new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeZone: 'UTC' }).format(new Date(value))
  : 'Não disponível';

const formatQuantity = (value: number | null) => value === null
  ? 'Não disponível'
  : new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 }).format(value);

export function PriorityTable({ rows, onSelect, compact = false }: { rows: Priority[]; onSelect: (row: Priority) => void; compact?: boolean }) {
  if (!rows.length) return <EmptyState title="Nenhuma prioridade encontrada" description="Ajuste os filtros ou atualize os dados." />;
  return <div className="table-shell"><table className={`data-table priority-table ${compact ? 'is-compact' : ''}`}><thead><tr><th>Prioridade</th><th>SKU / Produto</th><th>Família</th><th>Motivo principal</th>{!compact && <><th>Data crítica</th><th>Lacuna operacional</th></>}<th>Score</th><th>Confiança</th><th><span className="sr-only">Abrir</span></th></tr></thead><tbody>{rows.map((row) => <tr key={row.sku} onClick={() => onSelect(row)} tabIndex={0} onKeyDown={(event) => { if (event.key === 'Enter') onSelect(row); }}>
    <td><span className={`rank ${row.priority <= 3 ? 'top' : ''}`}>{row.priority}</span></td>
    <td><strong>{row.sku}</strong><small>{row.product}</small></td>
    <td>{row.family}</td>
    <td><Badge tone={severityTone(row.reasons[0]?.severity)}>{shortReason[row.reasons[0]?.code] ?? row.reasons[0]?.description ?? 'Sem motivo'}</Badge>{!compact && row.reasons.length > 1 && <small className="more-reasons">+{row.reasons.length - 1} sinais</small>}</td>
    {!compact && <><td><strong>{formatDate(row.critical_date)}</strong><small>{row.critical_date_reason === 'first_promised_date' ? 'Data prometida' : row.critical_date_reason === 'first_production_completion' ? 'Conclusão prevista' : 'Sem data operacional'}</small></td><td><strong>{formatQuantity(row.operational_gap_quantity)}</strong><small>Quantidade para análise</small></td></>}
    <td><strong className="score">{row.attention_score}</strong></td>
    <td><Badge tone={confidenceTone(row.confidence)}>{row.confidence}</Badge></td>
    <td><Icon name="arrow" size={17} /></td>
  </tr>)}</tbody></table></div>;
}

export function LoadingState() {
  return <div className="loading-grid" aria-label="Carregando dados"><div className="skeleton hero-skeleton" />{[1, 2, 3, 4].map((item) => <div className="skeleton card-skeleton" key={item} />)}<div className="skeleton table-skeleton" /></div>;
}

export function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return <div className="state-card error-state"><div className="state-icon">!</div><h2>Não foi possível carregar o painel</h2><p>{message}</p><button className="primary-button" onClick={onRetry}><Icon name="refresh" />Tentar novamente</button></div>;
}

export function EmptyState({ title, description }: { title: string; description: string }) {
  return <div className="empty-state"><span>○</span><strong>{title}</strong><p>{description}</p></div>;
}

export function SectionCard({ title, subtitle, action, children, className = '' }: { title: string; subtitle?: string; action?: ReactNode; children: ReactNode; className?: string }) {
  return <section className={`section-card ${className}`}><div className="section-heading"><div><h3>{title}</h3>{subtitle && <p>{subtitle}</p>}</div>{action}</div>{children}</section>;
}

export function ProgressBar({ value, tone = 'blue' }: { value: number; tone?: string }) {
  const percent = Math.max(0, Math.min(100, value * 100));
  return <div className="progress" aria-label={`${Math.round(percent)}%`}><span className={`progress-${tone}`} style={{ width: `${percent}%` }} /></div>;
}
