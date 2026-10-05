import { useEffect, useId, useRef, useState } from 'react';
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
  | 'validation'
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
  validation: <><path d="M9 3h6v3H9z"/><path d="M7 4.5H5v16h14v-16h-2"/><path d="m8.5 13 2.5 2.5 4.5-5"/></>,
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
  { id: 'validation', path: '/validacao', label: 'Validação', description: 'Evidência da Semana 4' },
];

export function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [mobile, setMobile] = useState(() => window.matchMedia('(max-width: 820px)').matches);
  const aside = useRef<HTMLElement>(null);
  useEffect(() => {
    const media = window.matchMedia('(max-width: 820px)');
    const change = () => setMobile(media.matches);
    media.addEventListener('change', change);
    return () => media.removeEventListener('change', change);
  }, []);
  useEffect(() => { aside.current?.toggleAttribute('inert', mobile && !open); }, [mobile, open]);
  // Mobile drawer: move focus into the menu when it opens, close with Escape and return focus to the trigger.
  useEffect(() => {
    if (!mobile || !open) return;
    aside.current?.querySelector<HTMLElement>('nav a')?.focus();
    const onKey = (event: KeyboardEvent) => { if (event.key === 'Escape') { onClose(); document.getElementById('menu-button')?.focus(); } };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [mobile, open, onClose]);
  return <>
    <div className={`sidebar-scrim ${open ? 'is-open' : ''}`} onClick={onClose} aria-hidden="true" />
    <aside ref={aside} id="menu-principal" aria-label="Menu" aria-hidden={mobile && !open ? true : undefined} className={`sidebar ${open ? 'is-open' : ''}`}>
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

export function Topbar({ title, subtitle, onMenu, onRefresh, refreshing, showRefresh = true, loadedAt = null, error = '', staticPage = false, menuOpen = false }: { title: string; subtitle: string; onMenu: () => void; onRefresh: () => void; refreshing: boolean; showRefresh?: boolean; loadedAt?: number | null; error?: string; staticPage?: boolean; menuOpen?: boolean }) {
  const timestamp = loadedAt === null ? null : new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'medium', timeZone: 'America/Sao_Paulo' }).format(new Date(loadedAt));
  return <header className="topbar">
    <div className="topbar-title">
      <button id="menu-button" className="icon-button menu-button" onClick={onMenu} aria-label="Abrir menu" aria-expanded={menuOpen} aria-controls="menu-principal"><Icon name="menu" /></button>
      <div><p>{subtitle}</p><h1 id="page-title" tabIndex={-1}>{title}</h1></div>
    </div>
    <div className="topbar-actions">
      <div className="load-status" role="status"><span>{staticPage ? 'Conteúdo de orientação' : refreshing ? 'Carregando dados…' : error ? 'Falha na consulta' : loadedAt === null ? 'Sem dados carregados' : 'Dados carregados'}</span><small title="Última consulta concluída no navegador; não indica atualização da planilha de origem.">{staticPage ? 'Não consulta a API' : timestamp ? `Última carga: ${timestamp} (Brasília)` : 'Ainda sem carga concluída'}</small></div>
      {showRefresh && <button className="secondary-button" onClick={onRefresh} disabled={refreshing} aria-label={refreshing ? 'Atualizando dados' : 'Atualizar dados desta página'}><Icon name="refresh" /><span>{refreshing ? 'Atualizando…' : 'Atualizar'}</span></button>}
    </div>
  </header>;
}

export function Alert({ title, children, tone = 'info', action }: { title: string; children: ReactNode; tone?: 'info' | 'warning' | 'error'; action?: ReactNode }) {
  return <div className={`ui-alert ui-alert-${tone}`} role={tone === 'error' || tone === 'warning' ? 'alert' : 'note'}><div><strong>{title}</strong><div>{children}</div></div>{action}</div>;
}

export function Tooltip({ label, children }: { label: string; children: ReactNode }) {
  const id = useId();
  const [open, setOpen] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  return <span className={`tooltip ${open ? 'is-open' : ''} ${dismissed ? 'is-dismissed' : ''}`} onMouseEnter={() => setDismissed(false)}><button type="button" className="tooltip-trigger" aria-label={label} aria-describedby={id} aria-expanded={open} onFocus={() => setDismissed(false)} onClick={() => { setDismissed(false); setOpen(value => !value); }} onBlur={() => setOpen(false)} onKeyDown={event => { if (event.key === 'Escape') { setOpen(false); setDismissed(true); } }}>?</button><span id={id} role="tooltip" className="tooltip-content">{children}</span></span>;
}

export function SystemBanner({ info }: { info: { demo_mode: boolean; write_enabled: boolean; notice: string | null } | null }) {
  if (!info || (!info.demo_mode && info.write_enabled)) return null;
  return <div className="system-banner" role="note" aria-label="Modo da publicação">
    {info.demo_mode && <span><strong>Demonstração.</strong> {info.notice}</span>}
    {!info.write_enabled && <span><strong>Somente leitura.</strong> Registro de decisões, casos e execuções está desabilitado nesta publicação.</span>}
  </div>;
}

export function DecisionBoundary() {
  return <Alert title="Prioridade de análise não é ordem de produção">O score indica o que investigar primeiro. A recomendação considera demanda, estoque e produção aberta. Um SKU pode ter prioridade alta e estar sem ação necessária de produção. Isso não elimina seus riscos nem dispensa revisão humana.</Alert>;
}

export function PageIntro({ eyebrow, title, description, action }: { eyebrow: string; title: string; description: string; action?: ReactNode }) {
  return <div className="page-intro"><div><span className="eyebrow">{eyebrow}</span><h2>{title}</h2><p>{description}</p></div>{action}</div>;
}

export function Badge({ children, tone = 'neutral', title }: { children: ReactNode; tone?: string; title?: string }) {
  return <span className={`badge badge-${tone}`} title={title}>{children}</span>;
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
  return <div className="table-shell" tabIndex={0} role="region" aria-label="Prioridades; role horizontalmente para ver todas as colunas"><table className={`data-table priority-table ${compact ? 'is-compact' : ''}`}><caption>Prioridade de análise · não é autorização de produção</caption><thead><tr><th>Prioridade</th><th>SKU / Produto</th><th>Família</th><th>Motivo principal</th>{!compact && <><th>Data crítica</th><th>Lacuna operacional</th></>}<th>Score <Tooltip label="O que significa o score?">Soma dos pesos dos sinais. Ordena a atenção, não a quantidade a produzir.</Tooltip></th><th>Confiança <Tooltip label="O que significa a confiança?">Qualidade da evidência para análise; não é garantia de atendimento ou previsão.</Tooltip></th><th><span className="sr-only">Abrir</span></th></tr></thead><tbody>{rows.map((row) => <tr key={row.sku} onClick={() => onSelect(row)} tabIndex={0} onKeyDown={(event) => { if (event.key === 'Enter' && event.target === event.currentTarget) onSelect(row); }}>
    <td><span className={`rank ${row.priority <= 3 ? 'top' : ''}`}>{row.priority}</span></td>
    <td><strong>{row.sku}</strong><small>{row.product}</small></td>
    <td>{row.family}</td>
    <td><Badge tone={severityTone(row.reasons[0]?.severity)}>{shortReason[row.reasons[0]?.code] ?? row.reasons[0]?.description ?? 'Sem motivo'}</Badge>{!compact && row.reasons.length > 1 && <small className="more-reasons">+{row.reasons.length - 1} sinais</small>}</td>
    {!compact && <><td><strong>{formatDate(row.critical_date)}</strong><small>{row.critical_date_reason === 'first_promised_date' ? 'Data prometida' : row.critical_date_reason === 'first_production_completion' ? 'Conclusão prevista' : 'Sem data operacional'}</small></td><td><strong>{formatQuantity(row.operational_gap_quantity)}</strong><small>Quantidade para análise</small></td></>}
    <td><strong className="score">{row.attention_score}</strong></td>
    <td><Badge tone={confidenceTone(row.confidence)}>{row.confidence}</Badge></td>
    <td><button className="icon-button table-detail-button" aria-label={`Abrir evidências de ${row.sku}`} onClick={event => { event.stopPropagation(); onSelect(row); }}><Icon name="arrow" size={17} /></button></td>
  </tr>)}</tbody></table></div>;
}

export function LoadingState() {
  return <div className="loading-grid" role="status" aria-label="Carregando dados"><div className="skeleton hero-skeleton" />{[1, 2, 3, 4].map((item) => <div className="skeleton card-skeleton" key={item} />)}<div className="skeleton table-skeleton" /></div>;
}

export function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return <div className="state-card error-state" role="alert"><div className="state-icon">!</div><h2>Não foi possível carregar o painel</h2><p>{message}</p><button className="primary-button" onClick={onRetry}><Icon name="refresh" />Tentar novamente</button></div>;
}

export function EmptyState({ title, description }: { title: string; description: string }) {
  return <div className="empty-state" role="status"><span>○</span><strong>{title}</strong><p>{description}</p></div>;
}

export function SectionCard({ title, subtitle, action, children, className = '' }: { title: string; subtitle?: string; action?: ReactNode; children: ReactNode; className?: string }) {
  return <section className={`section-card ${className}`}><div className="section-heading"><div><h3>{title}</h3>{subtitle && <p>{subtitle}</p>}</div>{action}</div>{children}</section>;
}

export function ProgressBar({ value, tone = 'blue', label = 'Cobertura observada' }: { value: number; tone?: string; label?: string }) {
  const percent = Math.max(0, Math.min(100, value * 100));
  return <div className="progress" role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(percent)} aria-valuetext={`${Math.round(percent)}%`}><span className={`progress-${tone}`} style={{ width: `${percent}%` }} /></div>;
}
