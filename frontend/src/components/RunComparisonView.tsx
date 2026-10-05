import { useCallback } from 'react';
import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import { Alert, Badge, EmptyState, ErrorState, LoadingState, MetricCard, SectionCard, confidenceTone } from '../components';
import { useApiResource } from '../hooks/useApiResource';
import { displayNumber, formatDateTime, reasonNames } from '../pages/shared';
import type { FieldChange, KeyChange, RankingEntry, RunComparison, RunMeta, Unavailable } from '../types-runs';

const isUnavailable = (section: { available: boolean }): section is Unavailable => !section.available;
const value = (input: unknown) => input === null || input === undefined ? 'não disponível'
  : typeof input === 'number' ? displayNumber(input) : typeof input === 'object' ? JSON.stringify(input) : String(input);
const signed = (delta: number | null) => delta === null ? '' : `${delta > 0 ? '+' : delta < 0 ? '−' : '±'}${displayNumber(Math.abs(delta))}`;
const signal = (code: string) => <Badge key={code} tone="neutral" title={code}>{reasonNames[code] ?? code}</Badge>;

function Refused({ section }: { section: Unavailable }) {
  return <Alert tone="warning" title="Comparação não disponível nesta seção">{section.reason}</Alert>;
}

function RunCard({ label, run }: { label: string; run: RunMeta }) {
  return <div className="run-compare-meta"><span className="eyebrow">{label}</span><strong>Execução #{run.id}</strong><small>{formatDateTime(run.created_at)}</small><code title={run.source_hash}>{run.source_hash.slice(0, 16)}…</code><small>{run.prioritized_skus} SKUs no ranking · {run.comparison_schema_version ? `snapshot ampliado v${run.comparison_schema_version}` : 'snapshot anterior à Etapa 6'}</small></div>;
}

function Changes({ title, changes }: { title: string; changes: KeyChange[] }) {
  return <div className="run-compare-config"><h5>{title}</h5>{changes.length ? <ul>{changes.map((change) => <li key={change.key}><code>{change.key}</code>: {value(change.base)} → <strong>{value(change.target)}</strong></li>)}</ul> : <p className="validation-muted">Sem alteração.</p>}</div>;
}

function FieldChanges({ changes }: { changes: FieldChange[] }) {
  return <ul className="run-compare-fields">{changes.map((change) => <li key={change.field}><span>{change.label}</span><span>{value(change.base)} → <strong>{value(change.target)}</strong>{change.delta !== null && <small> ({signed(change.delta)})</small>}</span></li>)}</ul>;
}

function EntryList({ title, items, empty }: { title: string; items: RankingEntry[]; empty: string }) {
  return <div className="run-compare-list"><h5>{title} ({items.length})</h5>{items.length ? <ul>{items.map((item) => <li key={item.sku}><Link to={`/skus/${encodeURIComponent(item.sku)}`}><strong>{item.sku}</strong></Link> #{item.priority} · score {item.attention_score} · <Badge tone={confidenceTone(item.confidence)}>{item.confidence}</Badge><div className="run-compare-signals">{item.signals.map(signal)}</div></li>)}</ul> : <p className="validation-muted">{empty}</p>}</div>;
}

function Section({ title, subtitle, children }: { title: string; subtitle: string; children: ReactNode }) {
  return <SectionCard title={title} subtitle={subtitle}>{children}</SectionCard>;
}

/** Pure rendering of a loaded comparison; testable without the API. */
export function RunComparisonContent({ data }: { data: RunComparison }) {
  const { ranking, forecasts, b2b_coverage: b2b, context } = data;
  return <div className="run-compare">
    {!data.comparable && <Alert tone="warning" title="Execuções sem dados compatíveis">Nenhuma seção pôde ser comparada. Os motivos aparecem abaixo.</Alert>}
    <Section title="Fonte e configuração" subtitle="Hash da planilha, data e configuração preservados em cada snapshot.">
      <div className="run-compare-pair"><RunCard label="Base" run={data.base} /><span aria-hidden="true">→</span><RunCard label="Alvo" run={data.target} /></div>
      <div className="run-compare-badges"><Badge tone={context.source_changed ? 'medium' : 'good'}>{context.source_changed ? 'Planilha diferente' : 'Mesma planilha'}</Badge><Badge tone={context.weights_changes.length ? 'medium' : 'good'}>{context.weights_changes.length ? 'Pesos alterados' : 'Mesmos pesos'}</Badge><Badge tone={context.thresholds_changes.length ? 'medium' : 'good'}>{context.thresholds_changes.length ? 'Limiares alterados' : 'Mesmos limiares'}</Badge></div>
      <div className="run-compare-config-grid">
        <Changes title="Pesos" changes={context.weights_changes} />
        <Changes title="Limiares das regras" changes={context.thresholds_changes} />
        {isUnavailable(context.commercial_thresholds) ? <div className="run-compare-config"><h5>Limiares comerciais</h5><p className="validation-muted">{context.commercial_thresholds.reason}</p></div> : <Changes title="Limiares comerciais" changes={context.commercial_thresholds.changes} />}
      </div>
      {data.notes.map((note) => <p key={note} className="validation-note">{note}</p>)}
    </Section>

    <Section title="Ranking oficial" subtitle="Entradas, saídas, posição, score, confiança e sinais, com a decomposição da diferença de score.">
      {isUnavailable(ranking) ? <Refused section={ranking} /> : <>
        <div className="metrics-grid">
          <MetricCard label="Entraram / saíram" value={`${ranking.summary.entered} / ${ranking.summary.exited}`} detail="SKUs no ranking" icon="priorities" />
          <MetricCard label="Mudaram" value={ranking.summary.changed} detail={`${ranking.summary.moved_up} subiram · ${ranking.summary.moved_down} desceram · ${ranking.summary.unchanged} iguais`} icon="runs" />
          <MetricCard label="Score ou confiança" value={`${ranking.summary.score_changed} / ${ranking.summary.confidence_changed}`} detail={`${ranking.summary.with_new_signals} com sinal novo`} tone="amber" icon="quality" />
          <MetricCard label="Sem explicação" value={ranking.summary.unexplained} detail="diferença de score não decomposta" tone={ranking.summary.unexplained ? 'red' : 'green'} icon="search" />
        </div>
        <div className="run-compare-columns"><EntryList title="Entraram no ranking" items={ranking.entered} empty="Nenhum SKU entrou." /><EntryList title="Saíram do ranking" items={ranking.exited} empty="Nenhum SKU saiu." /></div>
        {ranking.changed.length ? <div className="run-compare-changes">{ranking.changed.map((item) => <details key={item.sku} className="run-compare-change">
          <summary>
            <span><Link to={`/skus/${encodeURIComponent(item.sku)}`}><strong>{item.sku}</strong></Link><small>{item.product}</small></span>
            <span>#{item.base.priority} → <strong>#{item.target.priority}</strong> <Badge tone={item.position_delta > 0 ? 'high' : item.position_delta < 0 ? 'good' : 'neutral'}>{item.position_delta > 0 ? `subiu ${item.position_delta}` : item.position_delta < 0 ? `desceu ${-item.position_delta}` : 'mesma posição'}</Badge></span>
            <span>score {item.base.attention_score} → <strong>{item.target.attention_score}</strong> {item.score_delta ? <small>({signed(item.score_delta)})</small> : null}</span>
            <span>{item.confidence_changed ? <><Badge tone={confidenceTone(item.base.confidence)}>{item.base.confidence}</Badge> → <Badge tone={confidenceTone(item.target.confidence)}>{item.target.confidence}</Badge></> : <Badge tone={confidenceTone(item.target.confidence)}>{item.target.confidence}</Badge>}</span>
            {!item.score_delta_explained && !!item.score_delta && <Badge tone="critical">Não explicado</Badge>}
          </summary>
          <div className="run-compare-change-body">
            <div><h5>Por que mudou</h5><ul className="validation-list">{item.explanation.length ? item.explanation.map((line) => <li key={line}>{line}</li>) : <li>Somente valores de evidência mudaram; sinais, score e posição permaneceram.</li>}</ul></div>
            {(item.signals_added.length > 0 || item.signals_removed.length > 0) && <div><h5>Sinais</h5>{item.signals_added.length > 0 && <p>Novos: {item.signals_added.map(signal)}</p>}{item.signals_removed.length > 0 && <p>Removidos: {item.signals_removed.map(signal)}</p>}</div>}
            {item.score_breakdown.length > 0 && <div><h5>Decomposição do score</h5><ul className="run-compare-fields">{item.score_breakdown.map((entry) => <li key={`${entry.code}-${entry.change}`}><span>{reasonNames[entry.code] ?? entry.code} · {entry.change}</span><span>{value(entry.base_weight)} → {value(entry.target_weight)} <strong>{signed(entry.delta)}</strong></span></li>)}</ul></div>}
            {item.evidence_changes.length > 0 && <div><h5>Valores de evidência</h5><ul className="run-compare-fields">{item.evidence_changes.map((change) => <li key={`${change.code}-${change.field}`}><span>{reasonNames[change.code] ?? change.code} · {change.field}</span><span>{value(change.base)} → <strong>{value(change.target)}</strong></span></li>)}</ul></div>}
          </div>
        </details>)}</div> : <EmptyState title="Nenhum SKU mudou" description="Posição, score, confiança, sinais e evidências são iguais nas duas execuções." />}
      </>}
    </Section>

    <Section title="Previsão e recomendação operacional" subtitle="Valores preservados por SKU em cada snapshot; nada é recalculado.">
      {isUnavailable(forecasts) ? <Refused section={forecasts} /> : <>
        <p className="validation-note">{forecasts.summary.compared_skus} SKUs comparados · {forecasts.summary.changed_skus} com mudança · {forecasts.summary.action_changes} de ação · {forecasts.summary.quantity_changes} de quantidade · {forecasts.summary.model_changes} de modelo{forecasts.only_in_base.length + forecasts.only_in_target.length > 0 && ` · presentes em só uma execução: ${[...forecasts.only_in_base, ...forecasts.only_in_target].join(', ')}`}</p>
        {forecasts.items.length ? <div className="run-compare-cards">{forecasts.items.map((item) => <article key={item.sku}><Link to={`/skus/${encodeURIComponent(item.sku)}`}><strong>{item.sku}</strong></Link><FieldChanges changes={item.changes} /></article>)}</div> : <EmptyState title="Sem mudanças" description="Previsão e recomendação iguais em todos os SKUs comparados." />}
      </>}
    </Section>

    <Section title="Cobertura B2B2C" subtitle="Comparada por parceiro cadastrado; dados globais não são distribuídos entre parceiros.">
      {isUnavailable(b2b) ? <Refused section={b2b} /> : <>
        <p className="validation-note">Referência: {b2b.base_reference_month ?? '—'} → {b2b.target_reference_month ?? '—'} · {b2b.summary.compared_partners} parceiros comparados · {b2b.summary.changed_partners} com mudança{b2b.entered_partners.length > 0 && ` · novos: ${b2b.entered_partners.join(', ')}`}{b2b.exited_partners.length > 0 && ` · removidos: ${b2b.exited_partners.join(', ')}`}</p>
        {b2b.items.length ? <div className="run-compare-cards">{b2b.items.map((item) => <article key={item.partner}><Link to={`/parceiros/${encodeURIComponent(item.partner)}`}><strong>{item.name ?? item.partner}</strong></Link><FieldChanges changes={item.changes} /></article>)}</div> : <EmptyState title="Sem mudanças" description="Cobertura, SKUs observados e último sell-out iguais para todos os parceiros." />}
      </>}
    </Section>
    <ul className="validation-list">{data.limitations.map((item) => <li key={item}>{item}</li>)}</ul>
  </div>;
}

export function RunComparisonView({ base, target, refreshToken }: { base: number; target: number; refreshToken: number }) {
  const loader = useCallback((signal: AbortSignal) => api.runComparison(base, target, signal), [base, target]);
  const { data, error, refresh } = useApiResource(loader, refreshToken);
  if (!data && error) return <ErrorState message={error} onRetry={() => void refresh()} />;
  if (!data) return <LoadingState />;
  return <RunComparisonContent data={data} />;
}
