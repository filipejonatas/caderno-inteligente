import { Link } from 'react-router-dom';
import { api } from '../api';
import { useApiResource } from '../hooks/useApiResource';
import { usePageLoadStatus } from '../hooks/usePageLoadStatus';
import { Alert, Badge, ErrorState, LoadingState, MetricCard, PageIntro, SectionCard, Tooltip } from '../components';
import type { CaseCheck, FrozenCase, MeasuredValue, SafeBehaviorCheck, ValidationSummary } from '../types-validation';
import { validationCsv } from '../validation-export';
import { displayNumber, displayPercent, formatDate } from './shared';

const fieldNames: Record<string, string> = {
  signals: 'Sinais', action: 'Ação', suggested_quantity: 'Quantidade sugerida', requires_human_review: 'Revisão humana',
  ranked: 'No ranking', priority: 'Prioridade', capacity_status: 'Capacidade', confidence: 'Confiança',
  forecast_status: 'Status da previsão', data_quality: 'Qualidade do dado', missing_months: 'Meses ausentes',
  estimated_stock: 'Estoque estimado', coverage_days: 'Cobertura (dias)',
};
const inputNames: Record<string, string> = {
  current_stock: 'Estoque atual', coverage_days_calculated: 'Cobertura calculada (dias)', lead_time_days: 'Lead time (dias)',
  safety_stock_days: 'Segurança (dias)', backlog_order_quantity: 'Carteira', production_order_quantity: 'Produção aberta',
  first_promised_date: 'Primeira promessa', first_production_completion: 'Primeira conclusão prevista',
  capacity_occupation_average: 'Ocupação média da família', has_sell_out: 'Sell-out observado', forecast_status: 'Status da previsão',
  forecast_next_month: 'Previsão do próximo mês', sell_out_months: 'Meses com sell-out', missing_months: 'Meses ausentes',
  estimated_stock: 'Estoque estimado do parceiro', average_monthly_sell_out: 'Sell-out médio mensal', coverage_days: 'Cobertura no parceiro (dias)',
  age_months: 'Idade do dado (meses)', backlog_quantity: 'Carteira do par',
};
const resultLabel: Record<FrozenCase['result'], string> = { passou: 'Passou', falhou: 'Falhou', nao_encontrado: 'Não encontrado' };
const resultTone: Record<FrozenCase['result'], string> = { passou: 'good', falhou: 'critical', nao_encontrado: 'medium' };
const safeLabel: Record<SafeBehaviorCheck['status'], string> = { aprovado: 'Aprovado', reprovado: 'Reprovado', coberto_por_teste: 'Coberto por teste' };
const safeTone: Record<SafeBehaviorCheck['status'], string> = { aprovado: 'good', reprovado: 'critical', coberto_por_teste: 'neutral' };
const roleTone: Record<string, string> = { candidato: 'neutral', selecionado: 'good', baseline: 'medium' };

const isRatio = (unit: string | null) => !!unit && (unit === 'percentual' || unit === 'MAPE' || unit.startsWith('WAPE'));
function measured(value: MeasuredValue | null) {
  if (!value || value.value === null) return <span className="validation-muted">Não disponível</span>;
  return <><strong>{isRatio(value.unit) ? displayPercent(value.value) : `${displayNumber(value.value)} ${value.unit ?? ''}`}</strong>{isRatio(value.unit) && <small>{value.unit === 'percentual' ? '' : value.unit}</small>}</>;
}

function plain(value: unknown): string {
  if (value === null || value === undefined) return 'não disponível';
  if (Array.isArray(value)) return value.length ? value.join(', ') : 'vazio';
  if (typeof value === 'boolean') return value ? 'sim' : 'não';
  if (typeof value === 'number') return displayNumber(value);
  return String(value);
}

function CheckList({ checks }: { checks: CaseCheck[] }) {
  return <ul className="validation-checks">{checks.map((check) => <li key={check.field} className={check.passed ? 'is-passed' : 'is-failed'}>
    <span aria-hidden="true">{check.passed ? '✓' : '✗'}</span>
    <span><strong>{fieldNames[check.field] ?? check.field}</strong> — esperado: {plain(check.expected)} · obtido: {plain(check.obtained)}<span className="sr-only">{check.passed ? ' (atendido)' : ' (não atendido)'}</span></span>
  </li>)}</ul>;
}

function InputList({ input }: { input: Record<string, unknown> | null }) {
  if (!input) return <span className="validation-muted">Caso não encontrado na base atual.</span>;
  return <dl className="validation-input">{Object.entries(input).map(([key, value]) => <div key={key}><dt>{inputNames[key] ?? key}</dt><dd>{plain(value)}</dd></div>)}</dl>;
}

function download(summary: ValidationSummary) {
  const blob = new Blob([validationCsv(summary)], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = `validacao-caderno-inteligente-${summary.generated_at.slice(0, 10)}.csv`;
  anchor.click();
  URL.revokeObjectURL(url);
}

export default function ValidationPage({ refreshToken }: { refreshToken: number }) {
  const { data, error, loading, loadedAt, refresh } = useApiResource(api.validationSummary, refreshToken);
  usePageLoadStatus(loading, error, loadedAt);
  if (!data && error) return <ErrorState message={error} onRetry={() => void refresh()} />;
  if (!data) return <LoadingState />;
  return <ValidationContent data={data} error={error} onRetry={() => void refresh()} />;
}

/** Pure rendering of a loaded summary; kept separate so it can be tested without the API. */
export function ValidationContent({ data, error = '', onRetry }: { data: ValidationSummary; error?: string; onRetry: () => void }) {
  const { forecast_evaluation: forecast, frozen_cases: cases, analysis_time: time } = data;
  const selected = forecast.models.find((model) => model.role === 'selecionado');
  const baseline = forecast.models.find((model) => model.role === 'baseline');
  const safeExecuted = data.safe_behavior.filter((check) => check.status !== 'coberto_por_teste');
  const safeFailed = safeExecuted.filter((check) => check.status === 'reprovado').length;
  const notBeating = forecast.items.filter((item) => item.outcome !== 'superou');

  return <div className="validation-page">
    <PageIntro eyebrow="Semana 4 · Aplicabilidade" title="Central de validação" description="Compare o protótipo com o processo atual, avalie a previsão contra uma baseline explícita e confira casos representativos, comportamento seguro e falhas conhecidas." action={<div className="validation-actions"><button className="secondary-button" onClick={() => download(data)}>Exportar CSV</button><button className="secondary-button" onClick={() => window.print()}>Imprimir resumo</button></div>} />
    {error && <Alert tone="warning" title="Falha ao atualizar a validação" action={<button className="secondary-button" onClick={onRetry}>Tentar novamente</button>}>{error} A última carga permanece exibida.</Alert>}
    <Alert title="Evidência, não promessa de ganho">Indicadores informados pela empresa, valores recalculados pelo protótipo e metas aparecem em colunas separadas. Os casos congelados não ajustam pesos, limiares ou modelos, e toda recomendação continua exigindo revisão humana.</Alert>
    {!cases.source_matches_frozen && <Alert tone="warning" title="Base alterada desde o congelamento">{cases.source_note}</Alert>}

    <div className="metrics-grid">
      <MetricCard label="Casos aprovados" value={`${cases.passed}/${cases.total}`} detail={`${cases.failed} falha(s) · ${cases.not_found} não encontrado(s) · ${cases.synthetic} sintético(s)`} tone={cases.passed === cases.total ? 'green' : 'red'} icon="validation" />
      <MetricCard label="WAPE ponderado" value={displayPercent(selected?.weighted_wape ?? null)} detail={`baseline: ${displayPercent(baseline?.weighted_wape ?? null)} · ${forecast.eligible_skus} SKUs`} tone="blue" icon="forecasts" />
      <MetricCard label="Não superou a baseline" value={forecast.did_not_beat_baseline_skus} detail={`de ${forecast.eligible_skus} SKUs elegíveis · ${forecast.not_comparable_skus} não comparável(is)`} tone={forecast.did_not_beat_baseline_skus ? 'amber' : 'green'} icon="forecasts" />
      <MetricCard label="Comportamento seguro" value={`${safeExecuted.length - safeFailed}/${safeExecuted.length}`} detail={`${safeFailed ? `${safeFailed} reprovada(s)` : 'executadas, nenhuma reprovada'} · ${data.safe_behavior.length - safeExecuted.length} coberta(s) por teste`} tone={safeFailed ? 'red' : 'green'} icon="quality" />
    </div>

    <SectionCard title="Comparação com o processo atual" subtitle="Linha de base informada pela empresa, valor recalculado com a base e meta, sem misturar as naturezas.">
      <div className="table-shell" tabIndex={0} role="region" aria-label="Comparação com o processo atual; role horizontalmente para ver todas as colunas"><table className="data-table validation-table validation-comparison">
        <thead><tr><th>Indicador</th><th>Informado pela empresa</th><th>Recalculado no protótipo</th><th>Meta</th><th>Observação</th></tr></thead>
        <tbody>{data.process_comparison.map((row) => <tr key={row.id}>
          <td><strong>{row.label}</strong></td>
          <td><div className="validation-value"><Badge tone="neutral">informado</Badge>{measured(row.informed)}</div></td>
          <td><div className="validation-value"><Badge tone="medium">recalculado</Badge>{measured(row.recalculated)}{row.recalculated.value !== null && !row.recalculated.comparable && <small>não comparável diretamente</small>}</div></td>
          <td>{row.target ? <div className="validation-value"><Badge tone="good">meta</Badge>{measured(row.target)}</div> : <span className="validation-muted">Sem meta informada</span>}</td>
          <td><small>{row.recalculated.reason}</small></td>
        </tr>)}</tbody>
      </table></div>
      <p className="validation-source">Fonte da linha de base: {data.process_comparison[0]?.informed.source}.</p>
    </SectionCard>

    <SectionCard title="Tempo de análise registrado" subtitle="Minutos informados no registro de decisões. Não substitui a medição da jornada semanal completa." action={<Link className="secondary-button" to="/decisoes">Registrar decisão</Link>}>
      <div className="validation-time">
        <div><span>Decisões registradas</span><strong>{time.feedback_count}</strong></div>
        <div><span>Com tempo de análise</span><strong>{time.records_with_minutes}</strong></div>
        <div><span>Minutos somados</span><strong>{displayNumber(time.total_minutes)}</strong></div>
        <div><span>Média por decisão</span><strong>{time.average_minutes_per_decision === null ? '—' : `${displayNumber(time.average_minutes_per_decision)} min`}</strong></div>
        <div><span>Amostra</span><strong><Badge tone={time.comparison_allowed ? 'good' : 'medium'}>{time.sample_status}</Badge></strong><small>mínimo {time.minimum_sample}</small></div>
      </div>
      <p className="validation-note">{time.note}</p>
    </SectionCard>

    <SectionCard title="Desempenho dos modelos" subtitle={`Holdout temporal dos últimos ${forecast.holdout_months} meses. ${forecast.baseline.description}`}>
      <div className="table-shell" tabIndex={0} role="region" aria-label="Desempenho dos modelos; role horizontalmente para ver todas as colunas"><table className="data-table validation-table">
        <thead><tr><th>Modelo</th><th>Papel</th><th>SKUs avaliados</th><th>WAPE mediano</th><th>WAPE ponderado <Tooltip label="O que é WAPE ponderado?">Soma dos erros absolutos dividida pela soma da demanda real de todos os SKUs com demanda no holdout.</Tooltip></th><th>Escolhido em</th></tr></thead>
        <tbody>{forecast.models.map((model) => <tr key={model.model}>
          <td><strong>{model.label}</strong></td><td><Badge tone={roleTone[model.role]}>{model.role}</Badge></td>
          <td>{model.wape_defined_skus} de {model.evaluated_skus}</td><td>{displayPercent(model.median_wape)}</td><td>{displayPercent(model.weighted_wape)}</td>
          <td>{model.role === 'candidato' ? `${model.selected_skus} SKU(s)` : '—'}</td>
        </tr>)}</tbody>
      </table></div>
      <div className="validation-sample">
        <span><strong>{forecast.eligible_skus}</strong> SKUs elegíveis</span>
        <span><strong>{forecast.insufficient_skus}</strong> com dados insuficientes</span>
        <span><strong>{forecast.beat_baseline_skus}</strong> superaram a baseline</span>
        <span><strong>{forecast.did_not_beat_baseline_skus}</strong> não superaram</span>
        <span><strong>{forecast.zero_demand_holdout_skus}</strong> com holdout sem demanda</span>
      </div>
      {notBeating.length > 0 && <details className="validation-details"><summary>Ver os {notBeating.length} SKU(s) em que o modelo não superou a baseline</summary>
        <div className="table-shell" tabIndex={0} role="region" aria-label="SKUs sem ganho sobre a baseline"><table className="data-table validation-table"><thead><tr><th>SKU</th><th>Modelo selecionado</th><th>WAPE selecionado</th><th>WAPE baseline</th><th>Resultado</th></tr></thead>
          <tbody>{notBeating.map((item) => <tr key={item.sku}><td><Link to={`/skus/${encodeURIComponent(item.sku)}`}>{item.sku}</Link></td><td>{item.selected_model_label}</td><td>{displayPercent(item.selected_wape)}</td><td>{displayPercent(item.baseline_wape)}</td><td><Badge tone="medium">{item.outcome === 'nao_superou' ? 'Não superou' : 'Não comparável'}</Badge></td></tr>)}</tbody></table></div>
      </details>}
      <ul className="validation-list">{forecast.limitations.map((item) => <li key={item}>{item}</li>)}</ul>
    </SectionCard>

    <SectionCard title="Casos representativos congelados" subtitle={`Congelados em ${formatDate(cases.frozen_at)}. ${cases.policy}`}>
      <div className="validation-cases">{cases.items.map((item) => <article key={item.id} className={`validation-case is-${item.result}`}>
        <header><div><span className="eyebrow">{item.id} · {item.kind === 'commercial' ? 'comercial' : 'operacional'}</span><h4>{item.title}</h4>
          <p>{item.origin === 'synthetic' ? <><Badge tone="medium">entrada sintética</Badge> {item.origin_reason}</> : <><Badge tone="neutral">base real</Badge> {item.partner ? `${item.partner} · ` : ''}{item.sku && <Link to={`/skus/${encodeURIComponent(item.sku)}`}>{item.sku}</Link>}</>}</p></div>
          <Badge tone={resultTone[item.result]}>{resultLabel[item.result]}</Badge></header>
        <div className="validation-case-body">
          <div><h5>Entrada</h5><InputList input={item.input} /></div>
          <div><h5>Esperado × obtido</h5>{item.checks.length ? <CheckList checks={item.checks} /> : <span className="validation-muted">Sem saída obtida.</span>}</div>
        </div>
        <footer><p><strong>Limitação:</strong> {item.limitation}</p><p><strong>Ajuste realizado:</strong> {item.adjustment}</p></footer>
      </article>)}</div>
    </SectionCard>

    <SectionCard title="Comportamento seguro" subtitle="Verificações executadas a cada consulta com entradas controladas, além das cobertas por testes automatizados.">
      <ul className="validation-safe">{data.safe_behavior.map((check) => <li key={check.id}><Badge tone={safeTone[check.status]}>{safeLabel[check.status]}</Badge><div><strong>{check.label}</strong><small>{check.evidence}</small></div></li>)}</ul>
    </SectionCard>

    <div className="validation-two-columns">
      <SectionCard title="Falhas conhecidas" subtitle="Mostradas como estão; não são ocultadas nem compensadas.">
        {data.known_failures.length ? <ul className="validation-list">{data.known_failures.map((item) => <li key={item.description}><Badge tone="medium">{item.area}</Badge> {item.description}</li>)}</ul> : <p className="validation-muted">Nenhuma falha detectada nesta consulta.</p>}
        <h4>Limitações permanentes</h4>
        <ul className="validation-list">{data.known_limitations.map((item) => <li key={item}>{item}</li>)}</ul>
      </SectionCard>
      <SectionCard title="Histórico de ajustes" subtitle="Mudanças feitas após testes e revisões. Nenhuma alterou pesos ou modelos.">
        <ol className="validation-timeline">{data.adjustments.map((entry) => <li key={`${entry.date}-${entry.change}`}><time>{formatDate(entry.date)}</time><strong>{entry.change}</strong><small>{entry.reason}</small><small>Evidência: {entry.evidence} · {entry.changed_weights_or_models ? 'alterou pesos/modelos' : 'não alterou pesos nem modelos'}</small></li>)}</ol>
      </SectionCard>
    </div>
    <p className="validation-source">Planilha SHA-256 {data.source.sha256.slice(0, 12)}… · Referência de vendas: {formatDate(data.source.sales_reference_month)} · Gerado em {new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short', timeZone: 'America/Sao_Paulo' }).format(new Date(data.generated_at))} (Brasília)</p>
  </div>;
}
