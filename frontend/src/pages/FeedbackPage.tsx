import { useState } from 'react';
import type { FormEvent } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { api } from '../api';
import { Badge, EmptyState, PageIntro, SectionCard } from '../components';
import { DEFAULT_TEXT_LIMITS, useSystemInfo } from '../hooks/useSystemInfo';
import type { PageProps } from './shared';
import { decisionActionNames, formatDateTime, partnerDataEffectNames } from './shared';

export default function FeedbackPage({ data, onRefresh }: PageProps<'feedback' | 'priorities' | 'config'>) {
  const [params] = useSearchParams();
  const requestedSku = params.get('sku') ?? '';
  const skus = data.priorities.map((item) => item.sku);
  // Um SKU que veio do detalhe pode estar fora do ranking: ele continua sendo uma opção.
  const options = requestedSku && !skus.includes(requestedSku) ? [requestedSku, ...skus] : skus;
  const [sku, setSku] = useState(requestedSku || data.priorities[0]?.sku || '');
  const [action, setAction] = useState(data.config.actions[0] ?? 'aceita');
  const [user, setUser] = useState('');
  const [note, setNote] = useState('');
  const [partnerDataEffect, setPartnerDataEffect] = useState('nao_utilizado');
  const [analysisMinutes, setAnalysisMinutes] = useState('');
  const [message, setMessage] = useState('');
  const [saving, setSaving] = useState(false);
  const system = useSystemInfo();
  const limits = system?.text_limits ?? DEFAULT_TEXT_LIMITS;
  const writeDisabled = system?.write_enabled === false;
  async function submit(event: FormEvent) {
    event.preventDefault(); setSaving(true); setMessage('');
    try { await api.createFeedback({ sku, action, user_name: user, note, partner_data_effect: partnerDataEffect, analysis_minutes: analysisMinutes === '' ? null : Number(analysisMinutes) }); setNote(''); setPartnerDataEffect('nao_utilizado'); setAnalysisMinutes(''); await onRefresh(); setMessage('Decisão registrada com sucesso.'); }
    catch (error) { setMessage(error instanceof Error ? error.message : 'Falha ao registrar decisão.'); }
    finally { setSaving(false); }
  }
  return <>
    <PageIntro title="Registrar a decisão" action={requestedSku ? <Link className="secondary-button" to={`/skus/${encodeURIComponent(requestedSku)}`}>Voltar ao SKU {requestedSku}</Link> : undefined} />
    <div className="feedback-layout">
      <SectionCard title="Nova decisão" className="form-card"><form className="stack-form" onSubmit={submit}>
        <label>SKU<select value={sku} onChange={(event) => setSku(event.target.value)}>{options.map((item) => <option key={item}>{item}</option>)}</select></label>
        <label>O que você decidiu?<select value={action} onChange={(event) => setAction(event.target.value)}>{data.config.actions.map((item) => <option key={item} value={item}>{decisionActionNames[item] ?? item}</option>)}</select></label>
        <label>O dado do parceiro ajudou?<select value={partnerDataEffect} onChange={(event) => setPartnerDataEffect(event.target.value)}>{data.config.partner_data_effects.map((item) => <option key={item} value={item}>{partnerDataEffectNames[item] ?? item}</option>)}</select></label>
        <label>Tempo de análise em minutos <span className="optional-label">Opcional</span><input type="number" min="0" max={limits.analysis_minutes} step="1" value={analysisMinutes} onChange={(event) => setAnalysisMinutes(event.target.value)} placeholder="Ex.: 15" /></label>
        <label>Usuário<input value={user} maxLength={limits.user_name} onChange={(event) => setUser(event.target.value)} placeholder="Seu nome" /></label><label>Observação<textarea value={note} maxLength={limits.note} onChange={(event) => setNote(event.target.value)} placeholder="Contexto da decisão" /></label>
        {message && <span className="form-message">{message}</span>}{writeDisabled && <p className="write-disabled-note" role="note">Registro desabilitado nesta publicação (somente leitura).</p>}<button className="primary-button" disabled={saving || writeDisabled}>{saving ? 'Salvando…' : 'Registrar decisão'}</button>
      </form></SectionCard>
      <SectionCard title="Histórico recente">{data.feedback.length ? <div className="feedback-list">{data.feedback.map((item, index) => <article key={`${item.sku}-${item.created_at}-${index}`}><div className="feedback-head"><strong>{item.sku}</strong><Badge tone={item.action === 'aceita' ? 'good' : item.action === 'rejeitada' ? 'low' : 'medium'}>{decisionActionNames[item.action] ?? item.action}</Badge><Badge tone={item.partner_data_effect === 'alterou_decisao' ? 'good' : item.partner_data_effect === 'aumentou_confianca' ? 'medium' : 'neutral'}>{partnerDataEffectNames[item.partner_data_effect] ?? item.partner_data_effect}</Badge></div><p>{item.note || 'Sem observação.'}</p><div className="feedback-meta"><span>{item.analysis_minutes === null ? 'Tempo não informado' : `${item.analysis_minutes} min de análise`}</span><span>{item.user_name || 'Usuário não informado'} · {formatDateTime(item.created_at)}</span></div></article>)}</div> : <EmptyState title="Nenhuma decisão registrada" description="O feedback do PCP aparecerá aqui." />}</SectionCard>
    </div>
  </>;
}
