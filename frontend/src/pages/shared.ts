import type { DashboardData, SelectedSku } from '../types';

export interface PageProps {
  data: DashboardData;
  onSelect: (priority: SelectedSku) => void;
  onRefresh: () => Promise<void>;
}

export const reasonNames: Record<string, string> = {
  RUP_LEAD_TIME: 'Cobertura abaixo do lead time',
  RUP_SAFETY_STOCK: 'Abaixo do estoque de segurança',
  ORDER_WITHOUT_PRODUCTION: 'Pedido sem produção',
  PRODUCTION_AFTER_PROMISE: 'Produção após a promessa',
  CAPACITY_CONFLICT: 'Capacidade pressionada',
  EXCESS_COVERAGE: 'Excesso de cobertura',
  LOW_SELLOUT_VISIBILITY: 'Baixa visibilidade de sell-out',
};

export const statusNames: Record<string, string> = {
  novo: 'Novo',
  em_investigacao: 'Em investigação',
  aguardando_comercial: 'Aguardando comercial',
  aguardando_producao: 'Aguardando produção',
  concluido: 'Concluído',
  aceita: 'Aceita',
  alterada: 'Alterada',
  rejeitada: 'Rejeitada',
  investigar: 'Investigar',
};

export const partnerDataEffectNames: Record<string, string> = {
  nao_utilizado: 'Não utilizado',
  confirmou: 'Confirmou a análise',
  aumentou_confianca: 'Aumentou a confiança',
  alterou_decisao: 'Alterou a decisão',
};

export const toUtcDate = (value: string) => new Date(`${value.slice(0, 10)}T00:00:00Z`);
export const formatDate = (value?: string | null) => value ? new Intl.DateTimeFormat('pt-BR', { dateStyle: 'medium', timeZone: 'UTC' }).format(toUtcDate(value)) : 'Não disponível';
export const formatDateTime = (value: string) => new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(value));
export const displayNumber = (value: unknown) => typeof value === 'number' && Number.isFinite(value) ? new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 }).format(value) : '—';
export const displayPercent = (value: number | null) => value === null ? 'Não calculado' : new Intl.NumberFormat('pt-BR', { style: 'percent', maximumFractionDigits: 1 }).format(value);

export const missingDataNames: Record<string, string> = {
  first_promised_date: 'primeira data prometida',
  first_production_completion: 'primeira conclusão prevista',
  sell_in_quantity: 'sell-in',
  sell_out_quantity: 'sell-out',
  forecast_quantity: 'forecast',
};

export function positiveDelayDays(promisedDate: string | null, completionDate: string | null) {
  if (!promisedDate || !completionDate) return null;
  const milliseconds = toUtcDate(completionDate).getTime() - toUtcDate(promisedDate).getTime();
  const days = Math.round(milliseconds / 86_400_000);
  return days > 0 ? days : null;
}

export function partnerLevelTone(level: string) {
  if (level === 'Estratégico') return 'good';
  if (level === 'Sem visibilidade') return 'low';
  if (level === 'Essencial') return 'medium';
  return 'neutral';
}
