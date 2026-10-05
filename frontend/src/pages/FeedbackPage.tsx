import { useState } from 'react';
import type { FormEvent } from 'react';
import { api } from '../api';
import { Badge, EmptyState, PageIntro, SectionCard } from '../components';
import type { PageProps } from './shared';
import { formatDateTime, partnerDataEffectNames, statusNames } from './shared';

export default function FeedbackPage({ data, onRefresh }: PageProps) {
  const [sku, setSku] = useState(data.priorities[0]?.sku ?? '');
  const [action, setAction] = useState(data.config.actions[0] ?? 'aceita');
  const [user, setUser] = useState('');
  const [note, setNote] = useState('');
  const [partnerDataEffect, setPartnerDataEffect] = useState('nao_utilizado');
  const [analysisMinutes, setAnalysisMinutes] = useState('');
  const [message, setMessage] = useState('');
  const [saving, setSaving] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault(); setSaving(true); setMessage('');
    try { await api.createFeedback({ sku, action, user_name: user, note, partner_data_effect: partnerDataEffect, analysis_minutes: analysisMinutes === '' ? null : Number(analysisMinutes) }); setNote(''); setPartnerDataEffect('nao_utilizado'); setAnalysisMinutes(''); await onRefresh(); setMessage('Decisão registrada com sucesso.'); }
    catch (error) { setMessage(error instanceof Error ? error.message : 'Falha ao registrar decisão.'); }
    finally { setSaving(false); }
  }
  return <>
    <PageIntro eyebrow="Decisão humana" title="Feedback do PCP" description="Registre aceitação, alteração ou rejeição sem mudar automaticamente as regras." />
    <div className="feedback-layout">
      <SectionCard title="Registrar decisão" subtitle="O histórico fica separado da planilha de origem." className="form-card"><form className="stack-form" onSubmit={submit}>
        <label>SKU<select value={sku} onChange={(event) => setSku(event.target.value)}>{data.priorities.map((item) => <option key={item.sku}>{item.sku}</option>)}</select></label>
        <label>Ação tomada<select value={action} onChange={(event) => setAction(event.target.value)}>{data.config.actions.map((item) => <option key={item} value={item}>{statusNames[item] ?? item}</option>)}</select></label>
        <label>Efeito do dado do parceiro<select value={partnerDataEffect} onChange={(event) => setPartnerDataEffect(event.target.value)}>{data.config.partner_data_effects.map((item) => <option key={item} value={item}>{partnerDataEffectNames[item] ?? item}</option>)}</select></label>
        <label>Tempo de análise em minutos <span className="optional-label">Opcional</span><input type="number" min="0" step="1" value={analysisMinutes} onChange={(event) => setAnalysisMinutes(event.target.value)} placeholder="Ex.: 15" /></label>
        <label>Usuário<input value={user} onChange={(event) => setUser(event.target.value)} placeholder="Seu nome" /></label><label>Observação<textarea value={note} onChange={(event) => setNote(event.target.value)} placeholder="Contexto da decisão" /></label>
        {message && <span className="form-message">{message}</span>}<button className="primary-button" disabled={saving}>{saving ? 'Salvando…' : 'Registrar decisão'}</button>
      </form></SectionCard>
      <SectionCard title="Histórico recente" subtitle="Ação, influência dos dados e tempo de análise.">{data.feedback.length ? <div className="feedback-list">{data.feedback.map((item, index) => <article key={`${item.sku}-${item.created_at}-${index}`}><div className="feedback-head"><strong>{item.sku}</strong><Badge tone={item.action === 'aceita' ? 'good' : item.action === 'rejeitada' ? 'low' : 'medium'}>{statusNames[item.action] ?? item.action}</Badge><Badge tone={item.partner_data_effect === 'alterou_decisao' ? 'good' : item.partner_data_effect === 'aumentou_confianca' ? 'medium' : 'neutral'}>{partnerDataEffectNames[item.partner_data_effect] ?? item.partner_data_effect}</Badge></div><p>{item.note || 'Sem observação.'}</p><div className="feedback-meta"><span>{item.analysis_minutes === null ? 'Tempo não informado' : `${item.analysis_minutes} min de análise`}</span><span>{item.user_name || 'Usuário não informado'} · {formatDateTime(item.created_at)}</span></div></article>)}</div> : <EmptyState title="Nenhuma decisão registrada" description="O feedback do PCP aparecerá aqui." />}</SectionCard>
    </div>
  </>;
}
