import { useRef } from 'react';
import type { KeyboardEvent, ReactNode } from 'react';

export interface TabItem<Id extends string = string> { id: Id; label: string }

const tabId = (prefix: string, id: string) => `${prefix}-tab-${id}`;
const panelId = (prefix: string, id: string) => `${prefix}-panel-${id}`;

/** Abas com setas, Home e End; só a aba ativa entra na ordem de Tab (padrão ARIA de abas com ativação automática). */
export function TabBar<Id extends string>({ tabs, active, onChange, label, prefix, className = '' }: { tabs: ReadonlyArray<TabItem<Id>>; active: Id; onChange: (id: Id) => void; label: string; prefix: string; className?: string }) {
  const refs = useRef<Array<HTMLButtonElement | null>>([]);
  const move = (event: KeyboardEvent, index: number) => {
    const target = event.key === 'ArrowRight' ? (index + 1) % tabs.length
      : event.key === 'ArrowLeft' ? (index - 1 + tabs.length) % tabs.length
      : event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : -1;
    if (target < 0) return;
    event.preventDefault();
    onChange(tabs[target].id);
    refs.current[target]?.focus();
  };
  return <div className={`tab-list ${className}`.trim()} role="tablist" aria-label={label}>{tabs.map((item, index) => <button
    key={item.id} ref={(node) => { refs.current[index] = node; }} id={tabId(prefix, item.id)} role="tab" type="button"
    aria-selected={active === item.id} aria-controls={panelId(prefix, item.id)} tabIndex={active === item.id ? 0 : -1}
    className={active === item.id ? 'active' : ''} onClick={() => onChange(item.id)} onKeyDown={(event) => move(event, index)}>{item.label}</button>)}</div>;
}

/** Painel de uma aba. O conteúdo só é montado quando a aba está ativa, então dados secundários não carregam antes de serem pedidos. */
export function TabPanel({ id, active, prefix, children }: { id: string; active: boolean; prefix: string; children: ReactNode }) {
  return <div role="tabpanel" id={panelId(prefix, id)} aria-labelledby={tabId(prefix, id)} hidden={!active} className="tab-panel" tabIndex={active ? 0 : undefined}>{active ? children : null}</div>;
}
