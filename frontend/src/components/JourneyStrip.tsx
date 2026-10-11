import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import { useApiResource } from '../hooks/useApiResource';
import { JOURNEY } from '../journey';
import type { CapacityFamilyStatus, Overview } from '../types';
import type { AllocationRegions } from '../types-allocation';
import type { Resource } from './OverviewPanel';
import { displayCurrency, displayNumber, displayUnits, formatDate } from '../pages/shared';

type Tone = 'urgent' | 'review' | 'neutral';
interface Reading { value: string; detail: ReactNode; tone: Tone }

const isShort = (status: CapacityFamilyStatus) => status === 'insuficiente' || status === 'insuficiente_estimado';
const pending: Reading = { value: 'Carregando…', detail: null, tone: 'neutral' };
const unavailable: Reading = { value: 'Indisponível', detail: 'Não foi possível ler agora', tone: 'neutral' };
const tone = (count: number, level: Tone): Tone => count > 0 ? level : 'neutral';

/**
 * Cinco etapas do trabalho do PCP, cada uma com a pergunta, um número e o caminho.
 * Ver, decidir e confiar saem do `overview`; atender usa a leitura de regiões que o Início também mostra no mapa; caber carrega à parte e, se falharem, só aquela etapa diz "indisponível".
 * A Validação não é chamada aqui: ela recalcula a cada leitura (2 a 4 s), então "confiar" usa a contagem de confiança baixa do `overview`.
 */
export function JourneyStrip({ overview, allocation, refreshToken }: { overview: Overview; allocation: Resource<AllocationRegions>; refreshToken: number }) {
  const capacity = useApiResource(api.capacityPlan, refreshToken);

  const decisions = overview.decisions_today;
  const short = capacity.data?.families.filter((family) => isShort(family.status)) ?? [];
  const unscheduled = short.reduce((sum, family) => sum + family.unscheduled_quantity, 0);
  const totals = allocation.data?.totals;

  const readings: Record<string, Reading> = {
    ver: { value: displayNumber(overview.rupture_sku_count), detail: `SKUs com risco de ruptura · ${overview.below_lead_time_count} abaixo do prazo de produção`, tone: tone(overview.rupture_sku_count, 'urgent') },
    decidir: decisions
      ? { value: displayNumber(decisions.count), detail: `decisões com prazo até ${formatDate(decisions.window_end)}`, tone: tone(decisions.count, 'review') }
      : unavailable,
    caber: !capacity.data ? (capacity.loading ? pending : unavailable)
      : { value: `${short.length} de ${capacity.data.families.length}`, detail: short.length ? `famílias não cabem · ${displayUnits(unscheduled)} sem programação` : 'famílias: toda a produção planejada cabe', tone: tone(short.length, 'urgent') },
    atender: !totals ? (allocation.loading ? pending : unavailable)
      : { value: totals.uncovered_value === null ? displayUnits(totals.uncovered_units) : displayCurrency(totals.uncovered_value),
          detail: `sem cobertura na data prometida · ${totals.orders} pedidos de ${totals.skus} SKUs${totals.uncovered_value === null ? ' · valor indisponível (sem preço)' : ''}`, tone: tone(totals.uncovered_units, 'review') },
    confiar: { value: displayNumber(overview.low_confidence), detail: `de ${overview.prioritized} SKUs com confiança baixa`, tone: 'neutral' },
  };

  return <ol className="journey" aria-label="Caminho do PCP, em cinco passos">
    {JOURNEY.map((step, index) => {
      const reading = readings[step.id];
      return <li key={step.id}><Link className={`journey-step journey-${reading.tone}`} to={step.to}>
        <span className="journey-verb"><span aria-hidden="true">{index + 1}. </span>{step.verb}</span>
        <span className="journey-question">{step.question}</span>
        <strong className="journey-value">{reading.value}</strong>
        {reading.detail && <span className="journey-detail">{reading.detail}</span>}
      </Link></li>;
    })}
  </ol>;
}
