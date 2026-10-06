export type ChallengeCode =
  | 'produzir' | 'repor' | 'priorizar_producao' | 'priorizar_parceiro' | 'ampliar_mix'
  | 'recomendar_recompra' | 'reativar' | 'monitorar' | 'investigar' | 'sem_acao_necessaria';

export interface ChallengeEvidence { label: string; value: string | number | null; origin: string }

/** Rótulo de ação do desafio: camada derivada dos sinais existentes; nunca substitui a ação operacional ou comercial. */
export interface ChallengeAction {
  code: ChallengeCode; label: string; source: 'operational' | 'commercial' | 'partner' | 'channel'; origin_action: string | null;
  reason: string; signals_used: string[]; evidence: ChallengeEvidence[]; limitations: string[]; requires_human_review: boolean;
}
