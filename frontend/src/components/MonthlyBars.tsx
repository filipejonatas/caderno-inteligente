import { formatMonth } from '../pages/shared';

const CHART = { width: 560, height: 112, top: 6, bottom: 20, gap: 4 };

/** Uma barra por mês: parte cheia embaixo e tracejada em cima. `null` = parte sem valor (não desenhada); um número, mesmo zero, desenha ao menos 1 px. */
export interface MonthBar { month: string; solid: number | null; dashed: number | null }
export interface BarKey { label: string; dashed: boolean }

/** Barras mensais (cheias × tracejadas), usadas no faturamento e na produção planejada. Os rótulos e a legenda evitam depender só da cor. */
export function MonthlyBars({ bars, keys, label }: { bars: MonthBar[]; keys: BarKey[]; label: string }) {
  const max = Math.max(1, ...bars.map((bar) => (bar.solid ?? 0) + (bar.dashed ?? 0)));
  const slot = CHART.width / Math.max(1, bars.length);
  const plot = CHART.height - CHART.top - CHART.bottom;
  const scale = (value: number) => Math.max(1, (value / max) * plot);
  return <figure className="revenue-trend">
    <svg viewBox={`0 0 ${CHART.width} ${CHART.height}`} role="img" aria-label={label} preserveAspectRatio="xMidYMid meet">
      {bars.map((bar, index) => {
        const x = index * slot + CHART.gap / 2;
        const width = slot - CHART.gap;
        const solid = bar.solid === null ? 0 : scale(bar.solid);
        const dashed = bar.dashed === null ? 0 : scale(bar.dashed);
        const base = CHART.top + plot;
        return <g key={`${index}-${bar.month}`}>
          {solid > 0 && <rect className="revenue-bar" x={x} y={base - solid} width={width} height={solid} rx="2"></rect>}
          {dashed > 0 && <rect className="revenue-bar revenue-bar-estimated" x={x} y={base - solid - dashed} width={width} height={dashed} rx="2"></rect>}
          <text className="revenue-axis" x={x + width / 2} y={CHART.height - 6} textAnchor="middle">{formatMonth(bar.month).split('/')[0]}</text>
        </g>;
      })}
    </svg>
    <figcaption>{keys.map((key) => <span key={key.label}><i className={key.dashed ? 'revenue-key revenue-key-estimated' : 'revenue-key'} /> {key.label}</span>)}</figcaption>
  </figure>;
}
