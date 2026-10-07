import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import { useApiResource } from '../hooks/useApiResource';
import { Badge, SectionCard, Tooltip } from '../components';
import { displayPercent, displayQuantity, displayShare, formatMonth } from '../pages/shared';
import type { ForecastLab, LabIntervals, SensitivityCell } from '../types-forecast-lab';

const NA = 'Não disponível';
const signed = (value: number | null) => value === null ? NA : `${value > 0 ? '+' : ''}${displayPercent(value)}`;
const months = (values: number[]) => values.length > 1 ? `${values.slice(0, -1).join(', ')} e ${values[values.length - 1]}` : values.join('');
const trainText = (cell: SensitivityCell) => `Treino de ${months(cell.outer_train_lengths)} meses`;

/** Cobertura fora da amostra, dita sem enfeite: abaixo do nível nominal a faixa é só uma indicação. */
export function coverageText(intervals: LabIntervals) {
  const { coverage, tested_months: tested } = intervals.calibration;
  if (coverage === null) return 'Não houve meses suficientes para medir se a faixa acerta.';
  const base = `Fora da amostra, a faixa de ${displayShare(intervals.level)} cobriu ${displayShare(coverage)} dos ${tested} meses testados.`;
  return coverage < intervals.level - 0.05 ? `${base} Ficou abaixo do esperado: use-a como indicação, não como garantia.` : base;
}

function Table({ label, children }: { label: string; children: ReactNode }) {
  return <div className="table-shell" tabIndex={0} role="region" aria-label={label}><table className="data-table validation-table">{children}</table></div>;
}

/**
 * Laboratório de previsão (Etapa 14.3): motor atual × motor rolante, avaliados só em meses já ocorridos, e a grade que
 * mostra o quanto o veredito muda com as escolhas de desenho. Camada aditiva: sem ela, a validação segue completa.
 */
export function ForecastLabSection({ refreshToken = 0 }: { refreshToken?: number }) {
  const { data, error, refresh } = useApiResource(api.forecastLab, refreshToken);
  if (!data) {
    return <SectionCard title="Modelos candidatos (laboratório)">
      {error
        ? <p className="fact-line">Laboratório indisponível no momento. O restante da validação segue válido. <button type="button" className="secondary-button" onClick={() => void refresh()}>Tentar novamente</button></p>
        : <p className="fact-line" role="status">Calculando a comparação entre motores…</p>}
    </SectionCard>;
  }
  return <ForecastLabContent data={data} />;
}

const PEAK_ROWS = [
  { key: 'v2', label: 'Motor v2 (oficial)' },
  { key: 'v1', label: 'Motor v1 (anterior)' },
  { key: 'v2_ratio_2', label: 'Motor v2 com teto 2,0' },
  { key: 'baseline', label: 'Previsão simples (baseline)' },
] as const;

export function ForecastLabContent({ data }: { data: ForecastLab }) {
  const { selection, nested, sensitivity } = data;
  const peak = data.peak_evaluation;
  const hideBand = data.intervals.status === 'nao_calibrada';
  const { aggregate } = nested;
  const summary = sensitivity.summary;
  const procedures = [
    { key: 'baseline', label: 'Previsão simples (baseline)', value: aggregate.baseline },
    { key: 'v1', label: 'Motor v1', value: aggregate.v1 },
    { key: 'rolling', label: 'Motor rolante (candidato)', value: aggregate.rolling },
  ] as const;

  return <SectionCard title="Modelos candidatos (laboratório)">
    <p className="fact-line">{data.promotion_note} O motor rolante escolheria outro modelo em <strong>{selection.changed_skus}</strong> de {selection.skus} SKUs.</p>

    {peak && <>
      <h4 className="lab-heading">Avaliação com meses de pico <Tooltip label="Como a promoção foi decidida">Cada motor prevê os {peak.horizon_months} meses seguintes a {peak.origins.length} datas passadas ({peak.origins[0]} a {peak.origins[peak.origins.length - 1]}), só com os dados de até então. Erro total e erro só nos meses de pico. Critérios fixados antes do teste: erro 5% menor que o v1, viés no pico de até {displayPercent(peak.criteria.max_abs_peak_bias)}, viés sem piorar e mais SKUs melhores que a baseline.</Tooltip></h4>
      <Table label="Avaliação dos motores com meses de pico">
        <thead><tr><th>Motor</th><th>Erro total · no pico</th><th>Viés no pico</th><th>SKUs melhores que a baseline</th></tr></thead>
        <tbody>{PEAK_ROWS.map((row) => { const value = peak.procedures[row.key]; return <tr key={row.key}>
          <td><strong>{row.label}</strong></td>
          <td>{displayPercent(value.weighted_wape)} · {displayPercent(value.peak_wape)}</td>
          <td>{signed(value.peak_bias)}</td>
          <td>{row.key === 'baseline' ? '—' : value.skus_beating_baseline}</td>
        </tr>; })}</tbody>
      </Table>
      <p className="fact-line">Critérios de promoção: <Badge tone={peak.criteria.all_met ? 'good' : 'critical'}>{peak.criteria.all_met ? 'Atendidos' : 'Não atendidos'}</Badge></p>
    </>}

    <h4 className="lab-heading">Motor rolante (Etapa 14) em meses já ocorridos <Tooltip label="Como a avaliação é feita">Cada motor escolhe o modelo só com os dados anteriores ao período testado e é medido nos 3 meses seguintes. Assim o erro não é medido no mesmo teste em que o modelo foi escolhido. Viés negativo significa que a previsão ficou abaixo do vendido.</Tooltip></h4>
    <Table label="Avaliação dos motores em meses já ocorridos">
      <thead><tr><th>Procedimento</th><th>Erro ponderado (WAPE)</th><th>Viés</th><th>SKUs melhores que a baseline</th></tr></thead>
      <tbody>{procedures.map((row) => <tr key={row.key}>
        <td><strong>{row.label}</strong></td>
        <td>{displayPercent(row.value.weighted_wape)}</td>
        <td>{signed(row.value.weighted_bias)}</td>
        <td>{row.key === 'baseline' ? '—' : row.value.skus_beating_baseline}</td>
      </tr>)}</tbody>
    </Table>

    <h4 className="lab-heading">E se a avaliação fosse feita de outro jeito? <Tooltip label="O que a grade mostra">Cada linha refaz a avaliação com outro número de períodos de teste (os mais recentes) e outra exigência mínima de janelas de seleção. Os critérios de promoção combinados são: erro pelo menos 5% menor, viés sem piorar mais de 2 pontos e mais SKUs melhores que a baseline. A linha marcada como padrão é a que a tabela acima usa.</Tooltip></h4>
    <Table label="Grade de sensibilidade da avaliação">
      <thead><tr><th>Períodos de teste</th><th>Janelas mínimas</th><th>Redução do erro</th><th>Critérios</th></tr></thead>
      <tbody>{sensitivity.cells.map((cell) => <tr key={`${cell.outer_windows}-${cell.minimum_windows}`}>
        <td>{trainText(cell)} {cell.is_default && <Badge tone="neutral">padrão</Badge>}</td>
        <td>{cell.minimum_windows}</td>
        <td>{signed(cell.relative_wape_gain)}</td>
        <td><Badge tone={cell.all_met ? 'good' : 'critical'}>{cell.all_met ? 'Atendidos' : 'Não atendidos'}</Badge></td>
      </tr>)}</tbody>
    </Table>
    <p className="fact-line">Critérios atendidos em <strong>{summary.cells_all_met} de {summary.cells}</strong> combinações; a redução do erro vai de {signed(summary.min_relative_wape_gain)} a {signed(summary.max_relative_wape_gain)}. Os períodos testados são os mesmos para todos os SKUs: a amostra é menor do que parece.</p>

    <h4 className="lab-heading">Modelos testados</h4>
    <Table label="Modelos candidatos">
      <thead><tr><th>Modelo</th><th>Motor oficial (SKUs)</th><th>Motor rolante (SKUs)</th><th>Erro mediano (WAPE)</th></tr></thead>
      <tbody>{selection.models.map((model) => <tr key={model.model}>
        <td><strong>{model.label}</strong> <Tooltip label={`Sobre: ${model.label}`}>{model.description} Histórico mínimo: {model.min_history_months} meses.</Tooltip></td>
        <td>{model.official_selected_skus}</td>
        <td>{model.rolling_selected_skus}</td>
        <td>{displayPercent(model.median_wape)}</td>
      </tr>)}</tbody>
    </Table>

    <h4 className="lab-heading">Faixa de previsão <Tooltip label="Como a faixa é calculada">Faixa empírica entre o 10º e o 90º percentil dos erros relativos do motor rolante nos meses de teste, aplicada à previsão. Exige pelo menos {data.intervals.minimum_residuals} erros por SKU; sem isso o SKU fica sem faixa. Nunca é negativa, sempre contém a previsão pontual e não entra no ranking nem no score.</Tooltip></h4>
    {hideBand
      ? <p className="fact-line">{data.intervals.status_note}</p>
      : <p className="fact-line">{coverageText(data.intervals)}{data.intervals.skus_without_band > 0 && ` ${data.intervals.skus_without_band} SKUs ficaram sem faixa por falta de erros para estimá-la.`}</p>}
    {!hideBand && data.intervals.items.length > 0 && <details className="validation-details"><summary>Ver a faixa do próximo mês de {data.intervals.items.length} SKUs</summary>
      <Table label="Faixa de previsão do próximo mês">
        <thead><tr><th>SKU</th><th>Mês</th><th>Previsão</th><th>Faixa estimada</th></tr></thead>
        <tbody>{data.intervals.items.map((item) => <tr key={item.sku}>
          <td><Link to={`/skus/${encodeURIComponent(item.sku)}`}>{item.sku}</Link></td>
          <td>{formatMonth(item.month)}</td>
          <td>{displayQuantity(item.point)}</td>
          <td>{displayQuantity(item.lower)} a {displayQuantity(item.upper)}</td>
        </tr>)}</tbody>
      </Table>
    </details>}

    {selection.changed.length > 0 && <details className="validation-details"><summary>Ver os {selection.changed.length} SKUs que mudariam de modelo</summary>
      <Table label="SKUs que mudariam de modelo">
        <thead><tr><th>SKU</th><th>Motor oficial</th><th>Motor rolante</th><th>Erro na seleção (WAPE)</th></tr></thead>
        <tbody>{selection.changed.map((item) => <tr key={item.sku}>
          <td><Link to={`/skus/${encodeURIComponent(item.sku)}`}>{item.sku}</Link></td>
          <td>{item.official_model_label ?? NA}</td>
          <td>{item.rolling_model_label}</td>
          <td>{displayPercent(item.rolling_wape)}</td>
        </tr>)}</tbody>
      </Table>
    </details>}
  </SectionCard>;
}
