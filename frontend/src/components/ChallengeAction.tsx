import { Badge, Tooltip } from '../components';
import { displayNumber } from '../pages/shared';
import type { ChallengeAction, ChallengeCode } from '../types-actions';

const TONE: Record<ChallengeCode, string> = {
  priorizar_producao: 'high', priorizar_parceiro: 'high', produzir: 'info', repor: 'info', ampliar_mix: 'info', recomendar_recompra: 'info',
  reativar: 'info', monitorar: 'neutral', investigar: 'medium', sem_acao_necessaria: 'neutral',
};

const evidenceValue = (value: string | number) => typeof value === 'number' ? displayNumber(value) : value;

/** Selo do rótulo com o porquê, as evidências e a ressalva de revisão humana no "?". Sem rótulo, não renderiza nada. */
export function ChallengeBadge({ action }: { action?: ChallengeAction | null }) {
  if (!action) return null;
  const evidence = action.evidence.filter((item) => item.value !== null).map((item) => `${item.label}: ${evidenceValue(item.value as string | number)}`).join('; ');
  return <><Badge tone={TONE[action.code] ?? 'neutral'}>{action.label}</Badge><Tooltip label={`Por que: ${action.label}`}>{action.reason}{evidence ? ` Evidências: ${evidence}.` : ''} {action.limitations[0]} Revisão humana obrigatória.</Tooltip></>;
}
