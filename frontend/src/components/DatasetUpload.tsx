import type { ChangeEvent } from 'react';
import { useId, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, ApiError } from '../api';
import { Badge, SectionCard, Tooltip } from '../components';
import { formatDate, formatMonth } from '../pages/shared';
import type { Session } from '../session';
import type { DatasetApplyResult, DatasetInfo, DatasetIssue, DatasetPreview, DatasetSheetReport } from '../types-dataset';
import { LoginForm } from './SkuRegistry';

type Phase = 'choose' | 'previewing' | 'preview' | 'confirm' | 'applying' | 'done';
type Notice = { tone: 'error' | 'ok'; text: string } | null;

const STEPS: Array<{ label: string; phases: Phase[] }> = [
  { label: 'Escolher arquivo', phases: ['choose', 'previewing'] },
  { label: 'Conferir prévia', phases: ['preview'] },
  { label: 'Aplicar', phases: ['confirm', 'applying', 'done'] },
];

const POLICY_NAMES: Record<DatasetSheetReport['policy'], string> = { serie_mensal: 'acrescenta ou substitui meses', fotografia: 'substitui a aba', cadastro: 'substitui a aba' };
const STATUS_NAMES: Record<DatasetSheetReport['status'], [string, string]> = { mesclada: ['Mesclada', 'info'], substituida: ['Substituída', 'medium'], mantida: ['Mantida', 'neutral'] };
/** Problema por célula, dito em poucas palavras depois do valor ("'abc' não é número"). Sem frase conhecida, vale a mensagem do servidor. */
const CELL_PROBLEMS: Record<string, string> = {
  INVALID_NUMBER: 'não é número', NEGATIVE_VALUE: 'é negativo', INVALID_DATE: 'não é data válida', DUPLICATE_KEY: 'repete uma chave', MISSING_VALUES: 'está vazia',
};

const ptMb = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 });
const ptKb = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 0 });
const megabytes = (bytes: number) => ptMb.format(bytes / 1_048_576);
const fileSize = (bytes: number) => bytes >= 1_048_576 ? `${megabytes(bytes)} MB` : `${ptKb.format(Math.max(1, bytes / 1024))} KB`;
const arrow = (before: string, after: string) => <><span className="diff-before">{before}</span> <span aria-hidden="true">→</span><span className="sr-only">para</span> <strong className="diff-after">{after}</strong></>;
const messageOf = (error: unknown) => error instanceof Error ? error.message : 'A solicitação falhou.';

/** Recusa no navegador com as mesmas mensagens do servidor (upload_safety.check_upload), antes de enviar 4 MB à toa. */
export function checkFile(file: File, info: Pick<DatasetInfo, 'max_upload_bytes' | 'accepted_extensions'>): string | null {
  const extension = file.name.slice(file.name.lastIndexOf('.')).toLowerCase();
  if (!file.name.includes('.') || !info.accepted_extensions.includes(extension)) return `Envie um arquivo ${info.accepted_extensions.join(' ou ')}`;
  if (file.size > info.max_upload_bytes) return `Arquivo maior que o limite de ${megabytes(info.max_upload_bytes)} MB.`;
  return null;
}

/** Uma linha por exemplo: aba, linha do Excel, coluna, valor e o problema; até 5 por código e "mais N iguais". */
export function IssueList({ issues, tone }: { issues: DatasetIssue[]; tone: 'error' | 'warning' }) {
  return <ul className={`issue-lines issue-lines-${tone}`}>{issues.map((issue, index) => {
    const problem = CELL_PROBLEMS[issue.code];
    const lines = problem ? issue.examples.filter((example) => example.row !== null || example.key !== null) : [];
    return <li key={`${issue.code}-${issue.sheet}-${issue.column}-${index}`}>
      {lines.length === 0 ? <span>{issue.message}</span> : <>
        <ul>{lines.map((example, position) => <li key={position}>
          {[issue.sheet, example.row !== null ? `linha ${example.row}` : example.key, issue.column ? `coluna ${issue.column}` : null].filter(Boolean).join(', ')}:{' '}
          {example.value === null ? 'célula' : <q>{example.value}</q>} {problem}
        </li>)}</ul>
        {issue.more > 0 && <small>e mais {issue.more} {issue.more === 1 ? 'igual' : 'iguais'}</small>}
      </>}
    </li>;
  })}</ul>;
}

function SheetTable({ sheets }: { sheets: DatasetSheetReport[] }) {
  return <div className="table-shell" tabIndex={0} role="region" aria-label="O que muda por aba; role horizontalmente para ver todas as colunas">
    <table className="data-table responsive-table dataset-sheets"><caption className="sr-only">O que muda em cada aba enviada</caption>
      <thead><tr><th>Aba</th><th>Regra</th><th>Linhas</th><th>Meses</th><th>Situação</th></tr></thead>
      <tbody>{sheets.map((sheet) => {
        const [status, tone] = STATUS_NAMES[sheet.status];
        const months = [...sheet.months_added.map((month) => `+${formatMonth(month)}`), ...sheet.months_replaced.map((month) => `${formatMonth(month)} substituído`)];
        return <tr key={sheet.sheet}>
          <td data-label="Aba"><strong>{sheet.sheet}</strong></td>
          <td data-label="Regra">{POLICY_NAMES[sheet.policy]}</td>
          <td data-label="Linhas">{sheet.rows_before === null || sheet.rows_after === null ? 'Não disponível' : arrow(ptKb.format(sheet.rows_before), ptKb.format(sheet.rows_after))}</td>
          <td data-label="Meses">{months.length ? months.join(', ') : '–'}</td>
          <td data-label="Situação"><Badge tone={tone}>{status}</Badge></td>
        </tr>;
      })}</tbody>
    </table>
  </div>;
}

/** Prévia: o que muda por aba, erros endereçados, data de planejamento e efeito estimado no motor. Nada foi gravado. */
export function PreviewReport({ preview }: { preview: DatasetPreview }) {
  const changed = preview.sheets.filter((sheet) => sheet.status !== 'mantida');
  const kept = preview.sheets.filter((sheet) => sheet.status === 'mantida').map((sheet) => sheet.sheet);
  const { before, after } = preview.engine;
  const none = 'Não disponível';
  const hasOverrideWarning = preview.warnings.some((issue) => issue.code === 'REGISTRY_OVERRIDE');
  return <div className="dataset-preview">
    <p className="dataset-file">
      <strong>{preview.file.filename}</strong> <span>{fileSize(preview.file.size_bytes)}</span>
      {preview.file.example && <Badge tone="medium-estimated" title="Arquivo de exemplo: os números são fictícios e não servem para decidir.">Exemplo fictício</Badge>}
      {preview.file.has_macro && <Badge tone="neutral" title="Macros não são executadas nem guardadas.">Macro ignorada</Badge>}
    </p>

    {preview.errors.length > 0 && <div className="inline-error dataset-errors" role="alert">
      <strong>{preview.errors.length === 1 ? 'Um erro impede a aplicação' : `${preview.errors.length} erros impedem a aplicação`}</strong>
      <IssueList issues={preview.errors} tone="error" />
    </div>}

    <dl className="dataset-facts dataset-diff">
      <div><dt>Data de planejamento</dt><dd>{preview.reference.after ? arrow(formatDate(preview.reference.before), formatDate(preview.reference.after)) : <>{formatDate(preview.reference.before)} <small>nova data não calculada</small></>}</dd></div>
      <div><dt>Vendas até</dt><dd>{preview.reference.sales_last_month_after ? arrow(formatMonth(preview.reference.sales_last_month_before), formatMonth(preview.reference.sales_last_month_after)) : formatMonth(preview.reference.sales_last_month_before)}</dd></div>
      {after && <>
        <div><dt>Fila <Badge tone="neutral" title="Estimativa: o motor foi recalculado só na prévia.">estimativa</Badge></dt><dd>{arrow(before ? `${before.queue_size} SKUs` : none, `${after.queue_size} SKUs`)}</dd></div>
        <div><dt>Previsão começa em</dt><dd>{arrow(before ? formatMonth(before.forecast_first_month) : none, formatMonth(after.forecast_first_month))}</dd></div>
      </>}
    </dl>
    {!after && preview.engine.error && <p className="dataset-muted">{preview.engine.error}</p>}

    {changed.length > 0 && <SheetTable sheets={changed} />}
    {(kept.length > 0 || preview.ignored_sheets.length > 0) && <p className="dataset-muted">
      {kept.length > 0 && <>Sem mudança: {kept.join(', ')}. </>}
      {preview.ignored_sheets.length > 0 && <>Abas ignoradas: {preview.ignored_sheets.join(', ')}.</>}
    </p>}

    {after && <details className="dataset-details"><summary>Cinco primeiros da fila, antes e depois</summary>
      <div className="table-shell" tabIndex={0} role="region" aria-label="Cinco primeiros da fila antes e depois">
        <table className="data-table"><caption className="sr-only">Estimativa: posição na fila antes e depois da atualização</caption>
          <thead><tr><th>Posição</th><th>Antes</th><th>Depois</th></tr></thead>
          <tbody>{Array.from({ length: Math.max(before?.top5.length ?? 0, after.top5.length) }, (_, index) => <tr key={index}>
            <td>{index + 1}</td>
            <td>{!before ? none : before.top5[index] ? <><strong>{before.top5[index].sku}</strong><small>{before.top5[index].product}</small></> : '–'}</td>
            <td>{after.top5[index] ? <><strong>{after.top5[index].sku}</strong><small>{after.top5[index].product}</small></> : '–'}</td>
          </tr>)}</tbody>
        </table>
      </div>
    </details>}

    {preview.warnings.length > 0 && <details className="dataset-details"><summary>Avisos ({preview.warnings.length})</summary><IssueList issues={preview.warnings} tone="warning" /></details>}
    {preview.registry_overrides.count > 0 && !hasOverrideWarning && <p className="dataset-muted">Sobrescreve o cadastro feito pela tela em {preview.registry_overrides.skus.join(', ')}.</p>}
    {preview.limitations.length > 0 && <details className="dataset-details"><summary>Limitações</summary><ul className="plain-list">{preview.limitations.map((item) => <li key={item}>{item}</li>)}</ul></details>}
  </div>;
}

/** Bloco 2: escolher o arquivo → prévia → aplicar com confirmação. O 422 com prévia lista os erros; arquivo recusado, 401, 403 e 409 viram mensagem. */
export function DatasetUpload({ info, session, expired, token, onSignIn, onSignOut, onExpired, onApplied }: {
  info: DatasetInfo; session: Session | null; expired: boolean; token: string;
  onSignIn: (email: string, password: string) => Promise<void>; onSignOut: () => void; onExpired: (caught: unknown) => boolean; onApplied: () => void;
}) {
  const inputId = useId();
  const input = useRef<HTMLInputElement>(null);
  const [phase, setPhase] = useState<Phase>('choose');
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<DatasetPreview | null>(null);
  const [result, setResult] = useState<DatasetApplyResult | null>(null);
  const [notice, setNotice] = useState<Notice>(null);
  const busy = phase === 'previewing' || phase === 'applying';
  const needsLogin = info.upload_disabled_reason === 'login';
  const enabled = info.upload_enabled;

  const reset = () => {
    setPhase('choose'); setFile(null); setPreview(null); setResult(null); setNotice(null);
    if (input.current) input.current.value = '';
  };

  /** `fallback` é a fase de volta, decidida por quem chama (a closure de `preview` pode estar velha). */
  const fail = (caught: unknown, fallback: Phase) => {
    if (onExpired(caught)) { reset(); setNotice({ tone: 'error', text: 'Sua sessão expirou. Entre novamente.' }); return; }
    // 409 de versão: a prévia ficou velha; o arquivo continua escolhido para refazer.
    if (caught instanceof ApiError && caught.status === 409) { setPreview(null); setPhase('choose'); }
    else setPhase(fallback);
    setNotice({ tone: 'error', text: messageOf(caught) });
  };

  const runPreview = async (chosen: File) => {
    setPhase('previewing'); setPreview(null); setResult(null); setNotice(null);
    try {
      const outcome = await api.previewDataset(token, chosen);
      setPreview(outcome.preview);
      setPhase('preview');
    } catch (caught) {
      fail(caught, 'choose'); // a prévia anterior já foi descartada; o botão "Refazer a prévia" reaparece
    }
  };

  const choose = (event: ChangeEvent<HTMLInputElement>) => {
    const chosen = event.target.files?.[0] ?? null;
    if (!chosen) return;
    const refused = checkFile(chosen, info);
    setFile(refused ? null : chosen);
    if (refused) { setPreview(null); setPhase('choose'); setNotice({ tone: 'error', text: refused }); event.target.value = ''; return; }
    event.target.value = ''; // permite escolher o mesmo arquivo de novo (o File já está guardado)
    void runPreview(chosen);
  };

  const apply = async () => {
    if (!file || !preview) return;
    setPhase('applying'); setNotice(null);
    try {
      const outcome = await api.applyDataset(token, file, preview.file.sha256, preview.expected_version);
      if (!outcome.result) { setPreview(outcome.preview); setPhase('preview'); setNotice({ tone: 'error', text: outcome.detail ?? 'A planilha tem erros; nada foi aplicado.' }); return; }
      setResult(outcome.result);
      setPhase('done');
      onApplied();
    } catch (caught) {
      fail(caught, 'preview');
    }
  };

  const canApply = preview !== null && preview.can_apply && preview.errors.length === 0;
  const currentStep = STEPS.findIndex((step) => step.phases.includes(phase));
  const action = session ? <div className="registry-user"><span>{session.user.name || session.user.email}</span><button type="button" className="secondary-button" onClick={onSignOut}>Sair</button></div> : undefined;

  return <SectionCard title="Atualizar" className="dataset-upload" action={action}>
    <ol className="dataset-steps" aria-label="Passos">{STEPS.map((step, index) => <li key={step.label} className={index === currentStep ? 'is-current' : index < currentStep ? 'is-done' : ''} aria-current={index === currentStep ? 'step' : undefined}>{step.label}</li>)}</ol>

    <div className="dataset-flow" aria-busy={busy}>
      {notice && <p className={notice.tone === 'error' ? 'inline-error' : 'toast-inline'} role={notice.tone === 'error' ? 'alert' : 'status'}>{notice.text}</p>}
      {expired && !session && !notice && <p className="inline-error" role="alert">Sua sessão expirou. Entre novamente.</p>}

      {!enabled && info.upload_disabled_message && <p className="write-disabled-note" role="note">{info.upload_disabled_message}</p>}
      {needsLogin && !session && <LoginForm onSubmit={onSignIn} disabled={false} label="Entrar para atualizar a base" />}

      {phase !== 'done' && <div className={`dataset-drop ${enabled ? '' : 'is-disabled'}`}>
        <label htmlFor={inputId}>Planilha {info.accepted_extensions.join(' ou ')}</label>
        <input ref={input} id={inputId} type="file" accept={info.accepted_extensions.join(',')} disabled={!enabled || busy} onChange={choose} />
        <Tooltip label="Formato aceito">Até {megabytes(info.max_upload_bytes)} MB. Abas enviadas substituem as atuais; nas abas mensais, só os meses enviados. Aba ausente fica como está.</Tooltip>
      </div>}

      {busy && <p role="status" className="dataset-muted">{phase === 'previewing' ? 'Conferindo a planilha…' : 'Aplicando e recalculando…'}</p>}
      {!preview && file && phase === 'choose' && enabled && <button type="button" className="secondary-button" onClick={() => void runPreview(file)}>Refazer a prévia</button>}

      {preview && phase !== 'done' && <>
        <PreviewReport preview={preview} />
        <p className="human-review-line">Revisão humana: confira a fila depois de aplicar; a troca vale para todos os usuários.</p>
        <div className="form-actions dataset-actions">
          <button type="button" className="secondary-button" disabled={busy} onClick={reset}>Escolher outro arquivo</button>
          {canApply && phase === 'preview' && <button type="button" className="primary-button" onClick={() => setPhase('confirm')}>Aplicar e recalcular</button>}
          {canApply && (phase === 'confirm' || phase === 'applying') && <span className="dataset-confirm" role="group" aria-label="Confirmar aplicação">
            <span>Substituir a base ativa?</span>
            <button type="button" className="secondary-button" disabled={busy} onClick={() => setPhase('preview')}>Cancelar</button>
            <button type="button" className="primary-button" disabled={busy} onClick={() => void apply()}>{phase === 'applying' ? 'Aplicando…' : 'Confirmar e aplicar'}</button>
          </span>}
        </div>
      </>}

      {phase === 'done' && result && <div className="dataset-done">
        <p className="toast-inline" role="status">Base atualizada: referência {formatDate(result.reference_date)}, vendas até {formatMonth(result.sales_last_month)}.</p>
        <div className="form-actions dataset-actions">
          <Link className="secondary-button" to="/fila">Ver a fila</Link>
          <Link className="secondary-button" to="/qualidade">Ver dados da planilha</Link>
          <button type="button" className="link-button" onClick={reset}>Enviar outra planilha</button>
        </div>
      </div>}
    </div>
  </SectionCard>;
}
