import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react';
import { api } from './api';
import {
  Badge,
  EmptyState,
  ErrorState,
  Icon,
  LoadingState,
  MetricCard,
  PageIntro,
  PriorityTable,
  ProgressBar,
  SectionCard,
  confidenceTone,
  severityTone,
} from './components';
import type { DashboardData, ForecastRecommendationSummary, PageId, ScenarioResult, SelectedSku, SkuDetail } from './types';

const reasonNames: Record<string, string> = {
  RUP_LEAD_TIME: 'Cobertura abaixo do lead time',
  RUP_SAFETY_STOCK: 'Abaixo do estoque de segurança',
  ORDER_WITHOUT_PRODUCTION: 'Pedido sem produção',
  PRODUCTION_AFTER_PROMISE: 'Produção após a promessa',
  CAPACITY_CONFLICT: 'Capacidade pressionada',
  EXCESS_COVERAGE: 'Excesso de cobertura',
  LOW_SELLOUT_VISIBILITY: 'Baixa visibilidade de sell-out',
};

const statusNames: Record<string, string> = {
  novo: 'Novo',
  em_investigacao: 'Em investigação',
  aguardando_comercial: 'Aguardando comercial',
  aguardando_producao: 'Aguardando produção',
  concluido: 'Concluído',
  aceita: 'Aceita',
  alterada: 'Alterada',
  rejeitada: 'Rejeitada',
  investigar: 'Investigar',
};

const partnerDataEffectNames: Record<string, string> = {
  nao_utilizado: 'Não utilizado',
  confirmou: 'Confirmou a análise',
  aumentou_confianca: 'Aumentou a confiança',
  alterou_decisao: 'Alterou a decisão',
};

const toUtcDate = (value: string) => new Date(`${value.slice(0, 10)}T00:00:00Z`);
const formatDate = (value?: string | null) => value ? new Intl.DateTimeFormat('pt-BR', { dateStyle: 'medium', timeZone: 'UTC' }).format(toUtcDate(value)) : 'Não disponível';
const formatDateTime = (value: string) => new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(value));
const displayNumber = (value: unknown) => typeof value === 'number' && Number.isFinite(value) ? new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 }).format(value) : '—';
const displayPercent = (value: number | null) => value === null ? 'Não calculado' : new Intl.NumberFormat('pt-BR', { style: 'percent', maximumFractionDigits: 1 }).format(value);
const missingDataNames: Record<string, string> = {
  first_promised_date: 'primeira data prometida',
  first_production_completion: 'primeira conclusão prevista',
  sell_in_quantity: 'sell-in',
  sell_out_quantity: 'sell-out',
  forecast_quantity: 'forecast',
};

function positiveDelayDays(promisedDate: string | null, completionDate: string | null) {
  if (!promisedDate || !completionDate) return null;
  const milliseconds = toUtcDate(completionDate).getTime() - toUtcDate(promisedDate).getTime();
  const days = Math.round(milliseconds / 86_400_000);
  return days > 0 ? days : null;
}

function partnerLevelTone(level: string) {
  if (level === 'Estratégico') return 'good';
  if (level === 'Sem visibilidade') return 'low';
  if (level === 'Essencial') return 'medium';
  return 'neutral';
}

interface PageProps { data: DashboardData; onSelect: (priority: SelectedSku) => void; onRefresh: () => Promise<void>; }

const guidePages: Array<{ id: Exclude<PageId, 'guide'>; title: string; eyebrow: string; description: string }> = [
  { id: 'overview', title: 'Visão geral', eyebrow: 'Comece aqui', description: 'Veja o pulso da operação, os principais riscos e o que exige atenção hoje.' },
  { id: 'priorities', title: 'Prioridades', eyebrow: 'Ordene a análise', description: 'Consulte os SKUs ordenados por urgência e abra as evidências de cada sinal.' },
  { id: 'forecasts', title: 'Previsão e recomendações', eyebrow: 'Planeje a demanda', description: 'Compare forecast, confiança e ação sugerida antes da validação humana.' },
  { id: 'cases', title: 'Casos', eyebrow: 'Acompanhe ações', description: 'Transforme um alerta em responsável, prazo e acompanhamento operacional.' },
  { id: 'quality', title: 'Qualidade', eyebrow: 'Valide a base', description: 'Entenda cobertura, integridade e lacunas antes de tomar uma decisão.' },
  { id: 'b2b', title: 'Visibilidade B2B2C', eyebrow: 'Observe o canal', description: 'Compare a cobertura de sell-out e o nível demonstrativo dos parceiros.' },
  { id: 'scenarios', title: 'Cenários', eyebrow: 'Teste hipóteses', description: 'Altere pesos em uma simulação segura, sem modificar o ranking oficial.' },
  { id: 'runs', title: 'Execuções', eyebrow: 'Preserve o histórico', description: 'Registre snapshots auditáveis da fonte, configuração e ranking.' },
  { id: 'feedback', title: 'Decisões', eyebrow: 'Feche o ciclo', description: 'Registre a decisão humana e como os dados do parceiro influenciaram a análise.' },
];

const guideGlossary = [
  { term: 'Pontuação de atenção', description: 'Soma transparente dos pesos dos sinais encontrados. Quanto maior o score, mais cedo o item deve ser analisado — não significa decisão automática.' },
  { term: 'Confiança', description: 'Indica a qualidade e a cobertura dos dados usados. Confiança baixa pede validação humana antes de agir.' },
  { term: 'Data crítica', description: 'Primeira referência operacional relevante, como a data prometida ao cliente ou a conclusão prevista da produção.' },
  { term: 'Estoque projetado', description: 'Estimativa do saldo após considerar estoque, carteira e produção disponível na análise.' },
  { term: 'Lacuna operacional', description: 'Quantidade ainda sem cobertura suficiente e que precisa ser investigada pelo time.' },
  { term: 'Dado ausente', description: 'Informação que não foi observada na fonte. Ausência nunca é interpretada automaticamente como valor zero.' },
  { term: 'Nível B2B2C', description: 'Classificação demonstrativa da visibilidade de cada parceiro, baseada na cobertura e na recorrência dos dados compartilhados.' },
];

const guideFaq = [
  { question: 'Como os dados são atualizados?', answer: 'O botão “Atualizar dados” recarrega as informações disponibilizadas pelo backend. A página Execuções permite registrar um snapshot do momento para auditoria.' },
  { question: 'O que significa confiança baixa?', answer: 'Significa que informações relevantes estão ausentes ou têm cobertura limitada. Use o ranking como sinal de investigação e valide as evidências antes de decidir.' },
  { question: 'O que fazer quando o sell-out ou outro dado está zerado?', answer: 'Primeiro confirme se o zero foi realmente informado. Campo ausente e valor zero têm significados diferentes; o sistema sinaliza dados ausentes para evitar essa confusão.' },
  { question: 'Uma simulação altera os dados reais?', answer: 'Não. Cenários são temporários, não persistem os pesos testados e não alteram o ranking oficial nem as decisões já registradas.' },
  { question: 'O sistema emite uma ordem de produção automaticamente?', answer: 'Não. O protótipo organiza sinais e evidências para apoiar o PCP, mas toda decisão e execução continuam sob responsabilidade humana.' },
];

export function GuidePage({ onNavigate }: { onNavigate: (page: PageId) => void }) {
  return <div className="guide-page">
    <PageIntro
      eyebrow="Onboarding do protótipo"
      title="Entenda o Caderno Inteligente em poucos minutos"
      description="Siga o fluxo recomendado, conheça cada área e use os indicadores como apoio para uma decisão humana mais rápida e explicável."
      action={<button className="primary-button" onClick={() => onNavigate('overview')}>Começar pela visão geral <Icon name="arrow" size={17} /></button>}
    />

    <section className="guide-start" aria-labelledby="guide-start-title">
      <div className="guide-start-copy"><Badge tone="good">Fluxo recomendado</Badge><h3 id="guide-start-title">Do sinal à decisão, em cinco passos</h3><p>Uma sequência simples para explorar o protótipo sem se perder entre as telas.</p></div>
      <ol className="guide-steps">
        <li><span>1</span><div><strong>Confira o panorama</strong><p>Abra a Visão geral e identifique os principais riscos do dia.</p></div></li>
        <li><span>2</span><div><strong>Escolha uma prioridade</strong><p>Use o ranking e abra as evidências do SKU que exige atenção.</p></div></li>
        <li><span>3</span><div><strong>Valide o contexto</strong><p>Confira qualidade, datas, canal e dados ausentes antes de agir.</p></div></li>
        <li><span>4</span><div><strong>Teste uma hipótese</strong><p>Compare pesos em Cenários sem alterar a configuração oficial.</p></div></li>
        <li><span>5</span><div><strong>Registre a decisão</strong><p>Crie o acompanhamento necessário e guarde o feedback do PCP.</p></div></li>
      </ol>
    </section>

    <SectionCard title="O que há em cada página" subtitle="Use os atalhos para ir direto ao ponto.">
      <div className="guide-pages-grid">{guidePages.map((item) => <article className="guide-page-card" key={item.id}>
        <div className="guide-page-icon"><Icon name={item.id} /></div>
        <div className="guide-page-copy"><span>{item.eyebrow}</span><h4>{item.title}</h4><p>{item.description}</p></div>
        <button className="guide-link" onClick={() => onNavigate(item.id)}>Abrir página <Icon name="arrow" size={15} /></button>
      </article>)}</div>
    </SectionCard>

    <SectionCard title="Entenda os indicadores" subtitle="Conceitos essenciais em linguagem simples.">
      <dl className="guide-glossary">{guideGlossary.map((item) => <div key={item.term}><dt>{item.term}</dt><dd>{item.description}</dd></div>)}</dl>
    </SectionCard>

    <div className="guide-two-columns">
      <section className="guide-limitations" aria-labelledby="guide-limitations-title">
        <span className="guide-section-label">Transparência</span><h3 id="guide-limitations-title">O que este protótipo não faz</h3>
        <ul><li>Não executa decisões ou libera produção automaticamente.</li><li>Pode utilizar dados simulados para demonstrar o conceito.</li><li>Não substitui a validação manual quando há baixa confiança ou dados ausentes.</li><li>Uma simulação não equivale a uma ordem real de produção ou compra.</li></ul>
      </section>
      <section className="guide-demo" aria-labelledby="guide-demo-title">
        <span className="guide-section-label">Apresentação</span><h3 id="guide-demo-title">Roteiro de demonstração</h3><p className="guide-demo-time">2–3 minutos</p>
        <ol><li><strong>30s</strong><span>Mostre o problema na Visão geral.</span></li><li><strong>45s</strong><span>Abra uma prioridade e explique as evidências.</span></li><li><strong>30s</strong><span>Destaque a qualidade e a visibilidade do parceiro.</span></li><li><strong>45s</strong><span>Simule um cenário e registre a decisão humana.</span></li></ol>
      </section>
    </div>

    <SectionCard title="Dúvidas frequentes" subtitle="Respostas rápidas para usar o protótipo com segurança.">
      <div className="guide-faq">{guideFaq.map((item) => <details key={item.question}><summary>{item.question}<span aria-hidden="true">+</span></summary><p>{item.answer}</p></details>)}</div>
    </SectionCard>

    <div className="guide-footer-cta"><div><span>Pronto para explorar?</span><strong>Comece pelo panorama e siga os sinais.</strong></div><button className="primary-button" onClick={() => onNavigate('overview')}>Abrir visão geral <Icon name="arrow" size={17} /></button></div>
  </div>;
}

export function OverviewPage({ data, onSelect }: PageProps) {
  const maxRisk = Math.max(...Object.values(data.overview.risk_distribution), 1);
  return <>
    <PageIntro eyebrow="Centro de decisão" title="O que exige atenção hoje" description="Riscos, lacunas de dados e prioridades reunidos para orientar a análise do PCP." />
    <div className="metrics-grid">
      <MetricCard label="SKUs priorizados" value={data.overview.prioritized} detail={`de ${data.overview.total_skus} SKUs monitorados`} tone="blue" icon="priorities" />
      <MetricCard
        label="SKUs com risco de ruptura"
        value={data.overview.rupture_sku_count}
        detail={`${data.overview.below_lead_time_count} abaixo do lead time · ${data.overview.below_safety_stock_count} abaixo da segurança`}
        tone="red"
        icon="quality"
      />
      <MetricCard label="Pedidos sem OP" value={data.overview.order_without_production} detail="requerem validação operacional" tone="amber" icon="cases" />
      <MetricCard label="Baixa confiança" value={data.overview.low_confidence} detail="sell-out não observado" tone="slate" icon="b2b" />
    </div>
    <div className="decision-metrics">
      <MetricCard label="Decisões registradas" value={data.overview.decision_count} detail="feedbacks salvos pelo PCP" tone="blue" icon="feedback" />
      <MetricCard label="Influenciadas por dado parceiro" value={data.overview.partner_data_influenced_decision_count} detail="decisões alteradas ou fortalecidas" tone="green" icon="b2b" />
    </div>
    <div className="dashboard-grid">
      <SectionCard className="priorities-card" title="Prioridades mais urgentes" subtitle="Selecione um SKU para ver as evidências completas." action={<span className="live-label"><span />Ranking oficial</span>}>
        <PriorityTable rows={data.priorities.slice(0, 7)} onSelect={onSelect} compact />
      </SectionCard>
      <SectionCard title="Distribuição dos sinais" subtitle="Quantidade de ocorrências por regra.">
        <div className="risk-bars">{Object.entries(data.overview.risk_distribution).sort((a, b) => b[1] - a[1]).map(([code, value]) => <div className="risk-bar" key={code}><div><span>{reasonNames[code] ?? code}</span><strong>{value}</strong></div><div className="bar-track"><span style={{ width: `${(value / maxRisk) * 100}%` }} /></div></div>)}</div>
      </SectionCard>
    </div>
    <div className="insight-strip"><div className="insight-icon"><Icon name="b2b" /></div><div><strong>Visibilidade do canal ainda é parcial</strong><p>{Math.round(data.quality.sell_out_coverage.coverage * 100)}% dos pares parceiro–SKU possuem sell-out observado. Ausência de dado nunca é tratada como venda zero.</p></div><Badge tone="low">Atenção à confiança</Badge></div>
  </>;
}

export function PrioritiesPage({ data, onSelect }: PageProps) {
  const [search, setSearch] = useState('');
  const [family, setFamily] = useState('');
  const [confidence, setConfidence] = useState('');
  const families = useMemo(() => [...new Set(data.priorities.map((item) => item.family))].sort(), [data.priorities]);
  const filtered = useMemo(() => data.priorities.filter((item) => {
    const query = search.trim().toLocaleLowerCase('pt-BR');
    return (!query || item.sku.toLocaleLowerCase('pt-BR').includes(query) || item.product.toLocaleLowerCase('pt-BR').includes(query))
      && (!family || item.family === family)
      && (!confidence || item.confidence === confidence);
  }), [confidence, data.priorities, family, search]);

  return <>
    <PageIntro eyebrow="Fila de atenção" title="Prioridades explicáveis" description="A pontuação ordena a análise; a decisão continua sendo humana e apoiada pelas evidências." />
    <div className="filter-bar">
      <label className="search-field"><span className="sr-only">Buscar</span><Icon name="search" /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Buscar SKU ou produto" /></label>
      <label><span>Família</span><select value={family} onChange={(event) => setFamily(event.target.value)}><option value="">Todas</option>{families.map((item) => <option key={item}>{item}</option>)}</select></label>
      <label><span>Confiança</span><select value={confidence} onChange={(event) => setConfidence(event.target.value)}><option value="">Todas</option><option value="baixa">Baixa</option><option value="média">Média</option></select></label>
      <div className="filter-count"><strong>{filtered.length}</strong><span>resultados</span></div>
    </div>
    <SectionCard title="Ranking oficial" subtitle="Ordenado pela soma transparente dos pesos de cada sinal."><PriorityTable rows={filtered} onSelect={onSelect} /></SectionCard>
  </>;
}

type ForecastSort = 'priority' | 'suggested_quantity' | 'forecast_next_month' | 'backtest_wape';

const needsForecastAttention = (item: ForecastRecommendationSummary) =>
  item.forecast.status === 'insufficient_data'
  || item.operational_recommendation.action !== 'sem_acao_necessaria'
  || item.operational_recommendation.capacity_status === 'requires_review';

function recommendationTone(action: ForecastRecommendationSummary['operational_recommendation']['action']) {
  if (action === 'investigar_dados' || action === 'produzir_validar_capacidade') return 'medium';
  if (action === 'produzir') return 'high';
  if (action === 'monitorar_excesso') return 'neutral';
  return 'good';
}

export function ForecastsPage({ onSelect }: { onSelect: (item: SelectedSku) => void }) {
  const [items, setItems] = useState<ForecastRecommendationSummary[]>();
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [family, setFamily] = useState('');
  const [action, setAction] = useState('');
  const [confidence, setConfidence] = useState('');
  const [trend, setTrend] = useState('');
  const [attentionOnly, setAttentionOnly] = useState(false);
  const [sort, setSort] = useState<ForecastSort>('priority');

  const load = useCallback(async () => {
    setError('');
    try { setItems(await api.forecasts()); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Falha ao carregar previsões.'); }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const families = useMemo(() => [...new Set((items ?? []).map((item) => item.family))].sort(), [items]);
  const filtered = useMemo(() => {
    const query = search.trim().toLocaleLowerCase('pt-BR');
    const result = (items ?? []).filter((item) => (
      (!query || item.sku.toLocaleLowerCase('pt-BR').includes(query) || item.product.toLocaleLowerCase('pt-BR').includes(query))
      && (!family || item.family === family)
      && (!action || item.operational_recommendation.action === action)
      && (!confidence || item.forecast.forecast_confidence === confidence)
      && (!trend || item.forecast.trend === trend)
      && (!attentionOnly || needsForecastAttention(item))
    ));
    return [...result].sort((left, right) => {
      if (sort === 'priority') return (left.priority ?? Number.MAX_SAFE_INTEGER) - (right.priority ?? Number.MAX_SAFE_INTEGER) || left.sku.localeCompare(right.sku);
      const leftValue = sort === 'suggested_quantity' ? left.operational_recommendation.suggested_quantity : left.forecast[sort];
      const rightValue = sort === 'suggested_quantity' ? right.operational_recommendation.suggested_quantity : right.forecast[sort];
      if (leftValue === null && rightValue === null) return left.sku.localeCompare(right.sku);
      if (leftValue === null) return 1;
      if (rightValue === null) return -1;
      return rightValue - leftValue || left.sku.localeCompare(right.sku);
    });
  }, [action, attentionOnly, confidence, family, items, search, sort, trend]);

  const filtersActive = Boolean(search || family || action || confidence || trend || attentionOnly || sort !== 'priority');
  const clearFilters = () => { setSearch(''); setFamily(''); setAction(''); setConfidence(''); setTrend(''); setAttentionOnly(false); setSort('priority'); };

  if (!items && !error) return <LoadingState />;
  if (!items && error) return <ErrorState message={error} onRetry={() => void load()} />;

  const source = items ?? [];
  const predicted = source.filter((item) => item.forecast.status === 'ok').length;
  const production = source.filter((item) => ['produzir', 'produzir_validar_capacidade'].includes(item.operational_recommendation.action)).length;
  const capacity = source.filter((item) => item.operational_recommendation.capacity_status === 'requires_review').length;
  const investigate = source.filter((item) => item.forecast.status === 'insufficient_data' || item.operational_recommendation.action === 'investigar_dados').length;

  return <div className="forecast-page">
    <PageIntro eyebrow="Planejamento de demanda" title="Previsão e recomendações" description="Compare a demanda prevista, a confiança do modelo e a ação sugerida antes da validação humana." />
    {error && <div className="global-warning"><span>!</span>{error}<button onClick={() => void load()}>Tentar novamente</button></div>}
    <div className="forecast-page-warning"><div className="notice-icon">!</div><div><strong>Revisão humana obrigatória</strong><p>As quantidades são sugestões de apoio à decisão. Revise carteira, capacidade e restrições operacionais antes de agir.</p></div></div>
    <div className="metrics-grid forecast-page-metrics">
      <MetricCard label="SKUs previstos" value={predicted} detail={`${source.length} SKUs analisados`} tone="blue" icon="forecasts" />
      <MetricCard label="Produção sugerida" value={production} detail="itens que pedem avaliação" tone="green" icon="forecasts" />
      <MetricCard label="Validar capacidade" value={capacity} detail="contexto familiar pressionado" tone="amber" icon="quality" />
      <MetricCard label="Investigar dados" value={investigate} detail="sem previsão confiável" tone={investigate ? 'red' : 'slate'} icon="search" />
    </div>
    <div className="forecast-page-filters">
      <label className="search-field"><span>Buscar</span><Icon name="search" /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="SKU ou produto" /></label>
      <label><span>Família</span><select value={family} onChange={(event) => setFamily(event.target.value)}><option value="">Todas</option>{families.map((item) => <option key={item}>{item}</option>)}</select></label>
      <label><span>Ação</span><select value={action} onChange={(event) => setAction(event.target.value)}><option value="">Todas</option><option value="produzir">Produzir</option><option value="produzir_validar_capacidade">Produzir e validar capacidade</option><option value="monitorar_excesso">Monitorar excesso</option><option value="investigar_dados">Investigar dados</option><option value="sem_acao_necessaria">Sem ação necessária</option></select></label>
      <label><span>Confiança</span><select value={confidence} onChange={(event) => setConfidence(event.target.value)}><option value="">Todas</option><option value="alta">Alta</option><option value="média">Média</option><option value="baixa">Baixa</option></select></label>
      <label><span>Tendência</span><select value={trend} onChange={(event) => setTrend(event.target.value)}><option value="">Todas</option><option value="crescente">Crescente</option><option value="estável">Estável</option><option value="decrescente">Decrescente</option><option value="indeterminada">Indeterminada</option></select></label>
      <label><span>Ordenar por</span><select value={sort} onChange={(event) => setSort(event.target.value as ForecastSort)}><option value="priority">Prioridade oficial</option><option value="suggested_quantity">Maior quantidade sugerida</option><option value="forecast_next_month">Maior previsão do próximo mês</option><option value="backtest_wape">Maior WAPE</option></select></label>
      <label className="forecast-page-check"><input type="checkbox" checked={attentionOnly} onChange={(event) => setAttentionOnly(event.target.checked)} /><span>Somente itens com atenção</span></label>
      <div className="forecast-page-filter-result"><strong>{filtered.length}</strong><span>de {source.length} SKUs</span>{filtersActive && <button onClick={clearFilters}>Limpar filtros</button>}</div>
    </div>
    <SectionCard title="Visão operacional consolidada" subtitle="O ranking oficial permanece separado da quantidade sugerida." action={<span className="live-label"><span />Pipeline cacheado</span>}>
      {filtered.length ? <>
        <div className="table-shell forecast-page-table"><table className="data-table"><thead><tr><th>SKU</th><th>Prioridade</th><th>Tendência</th><th>Próximo mês</th><th>3 meses</th><th>Modelo / WAPE</th><th>Confiança</th><th>Recomendação</th><th>Quantidade</th><th>Capacidade</th><th></th></tr></thead><tbody>{filtered.map((item) => <tr key={item.sku}>
          <td><strong>{item.sku}</strong><small>{item.product} · {item.family}</small></td>
          <td>{item.priority === null ? <span className="forecast-page-muted">Fora do ranking</span> : <span className={`rank ${item.priority <= 3 ? 'top' : ''}`}>#{item.priority}</span>}</td>
          <td><strong className={`trend-${item.forecast.trend}`}>{item.forecast.trend}</strong></td>
          <td>{item.forecast.status === 'ok' ? displayNumber(item.forecast.forecast_next_month) : <Badge tone="medium">Dados insuficientes</Badge>}</td>
          <td>{item.forecast.status === 'ok' ? displayNumber(item.forecast.forecast_total_3m) : '—'}</td>
          <td><strong>{item.forecast.model_label}</strong><small>{displayPercent(item.forecast.backtest_wape)}</small></td>
          <td><Badge tone={confidenceTone(item.forecast.forecast_confidence)}>{item.forecast.forecast_confidence}</Badge></td>
          <td><Badge tone={recommendationTone(item.operational_recommendation.action)}>{item.operational_recommendation.action_label}</Badge></td>
          <td><strong>{displayNumber(item.operational_recommendation.suggested_quantity)}</strong><small>Lote: {displayNumber(item.operational_recommendation.minimum_lot)}</small></td>
          <td><Badge tone={item.operational_recommendation.capacity_status === 'requires_review' ? 'medium' : 'neutral'}>{item.operational_recommendation.capacity_status === 'requires_review' ? 'Validar capacidade' : 'Sem garantia individual'}</Badge></td>
          <td><button className="forecast-page-detail-button" onClick={() => onSelect(item)}>Ver detalhes</button></td>
        </tr>)}</tbody></table></div>
        <div className="forecast-page-cards">{filtered.map((item) => <article key={item.sku} className="forecast-page-card">
          <div className="forecast-page-card-head"><div><strong>{item.sku}</strong><span>{item.product}</span><small>{item.family}</small></div>{item.priority === null ? <Badge tone="neutral">Fora do ranking</Badge> : <span className={`rank ${item.priority <= 3 ? 'top' : ''}`}>#{item.priority}</span>}</div>
          <div className="forecast-page-card-badges"><Badge tone={confidenceTone(item.forecast.forecast_confidence)}>{item.forecast.forecast_confidence}</Badge><Badge tone={recommendationTone(item.operational_recommendation.action)}>{item.operational_recommendation.action_label}</Badge>{item.operational_recommendation.capacity_status === 'requires_review' && <Badge tone="medium">Validar capacidade</Badge>}</div>
          <dl><div><dt>Tendência</dt><dd className={`trend-${item.forecast.trend}`}>{item.forecast.trend}</dd></div><div><dt>Próximo mês</dt><dd>{item.forecast.status === 'ok' ? displayNumber(item.forecast.forecast_next_month) : 'Dados insuficientes'}</dd></div><div><dt>Próximos 3 meses</dt><dd>{displayNumber(item.forecast.forecast_total_3m)}</dd></div><div><dt>Quantidade sugerida</dt><dd>{displayNumber(item.operational_recommendation.suggested_quantity)}</dd></div><div><dt>Modelo</dt><dd>{item.forecast.model_label}</dd></div><div><dt>WAPE</dt><dd>{displayPercent(item.forecast.backtest_wape)}</dd></div></dl>
          <button className="secondary-button" onClick={() => onSelect(item)}>Ver detalhes</button>
        </article>)}</div>
      </> : <div className="forecast-page-empty"><EmptyState title="Nenhum SKU encontrado" description="Ajuste os filtros ou volte à visão completa." />{filtersActive && <button className="secondary-button" onClick={clearFilters}>Limpar filtros</button>}</div>}
    </SectionCard>
  </div>;
}

export function CasesPage({ data, onRefresh }: PageProps) {
  const [sku, setSku] = useState(data.priorities[0]?.sku ?? '');
  const [owner, setOwner] = useState('');
  const [status, setStatus] = useState('novo');
  const [dueDate, setDueDate] = useState('');
  const [message, setMessage] = useState('');
  const [saving, setSaving] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault(); setSaving(true); setMessage('');
    try { await api.createCase({ sku, owner, status, due_date: dueDate }); await onRefresh(); setMessage('Caso criado e incluído no acompanhamento.'); }
    catch (error) { setMessage(error instanceof Error ? error.message : 'Não foi possível criar o caso.'); }
    finally { setSaving(false); }
  }

  return <>
    <PageIntro eyebrow="Acompanhamento" title="Casos operacionais" description="Transforme um sinal em responsabilidade, prazo e acompanhamento visível." action={<button className="primary-button" onClick={() => document.getElementById('new-case')?.scrollIntoView({ behavior: 'smooth' })}>+ Novo caso</button>} />
    <div className="case-summary"><div><strong>{data.cases.filter((item) => item.status !== 'concluido').length}</strong><span>casos abertos</span></div><div><strong>{data.cases.filter((item) => item.status === 'em_investigacao').length}</strong><span>em investigação</span></div><div><strong>{data.cases.filter((item) => item.status === 'concluido').length}</strong><span>concluídos</span></div></div>
    <SectionCard title="Fila de casos" subtitle="Últimas atualizações primeiro.">
      {data.cases.length ? <div className="table-shell"><table className="data-table"><thead><tr><th>SKU</th><th>Status</th><th>Responsável</th><th>Prazo</th><th>Atualizado</th></tr></thead><tbody>{data.cases.map((item) => <tr key={item.id}><td><strong>{item.sku}</strong><small>#{item.id}</small></td><td><Badge tone={item.status === 'concluido' ? 'good' : item.status === 'novo' ? 'neutral' : 'medium'}>{statusNames[item.status] ?? item.status}</Badge></td><td>{item.owner || 'Não definido'}</td><td>{formatDate(item.due_date)}</td><td>{formatDateTime(item.updated_at)}</td></tr>)}</tbody></table></div> : <EmptyState title="Nenhum caso criado" description="Crie um caso para acompanhar uma prioridade operacional." />}
    </SectionCard>
    <SectionCard title="Criar caso" subtitle="Vincule um SKU priorizado a um responsável e prazo." className="form-card"><form id="new-case" className="form-layout" onSubmit={submit}><label>SKU<select required value={sku} onChange={(event) => setSku(event.target.value)}>{data.priorities.map((item) => <option key={item.sku}>{item.sku}</option>)}</select></label><label>Responsável<input value={owner} onChange={(event) => setOwner(event.target.value)} placeholder="Nome ou área" /></label><label>Status<select value={status} onChange={(event) => setStatus(event.target.value)}>{data.config.case_statuses.map((item) => <option key={item} value={item}>{statusNames[item] ?? item}</option>)}</select></label><label>Prazo<input type="date" value={dueDate} onChange={(event) => setDueDate(event.target.value)} /></label><div className="form-actions">{message && <span className="form-message">{message}</span>}<button className="primary-button" disabled={saving}>{saving ? 'Salvando…' : 'Criar caso'}</button></div></form></SectionCard>
  </>;
}

export function QualityPage({ data }: PageProps) {
  const sheets = Object.entries(data.quality.sheets);
  const totalRecords = sheets.reduce((sum, [, sheet]) => sum + sheet.records, 0);
  const orphanCount = data.quality.foreign_keys.reduce((sum, item) => sum + item.orphan_count, 0);
  return <>
    <PageIntro eyebrow="Confiabilidade" title="Qualidade dos dados" description="Transparência sobre cobertura, integridade e lacunas antes de qualquer decisão." />
    <div className="metrics-grid quality-metrics"><MetricCard label="Registros avaliados" value={totalRecords.toLocaleString('pt-BR')} detail={`${sheets.length} abas carregadas`} tone="blue" icon="quality" /><MetricCard label="Erros bloqueantes" value={data.quality.errors.length} detail="validações da fonte" tone={data.quality.errors.length ? 'red' : 'green'} icon="quality" /><MetricCard label="Chaves órfãs" value={orphanCount} detail="integridade referencial" tone={orphanCount ? 'amber' : 'green'} icon="quality" /><MetricCard label="Cobertura sell-out" value={`${Math.round(data.quality.sell_out_coverage.coverage * 100)}%`} detail={`${data.quality.sell_out_coverage.observed_pairs} de ${data.quality.sell_out_coverage.possible_pairs} pares`} tone="slate" icon="b2b" /></div>
    <SectionCard title="Cobertura da fonte" subtitle="Volume e duplicidades por aba."><div className="table-shell"><table className="data-table"><thead><tr><th>Aba</th><th>Registros</th><th>Duplicidades</th><th>Colunas ausentes</th><th>Situação</th></tr></thead><tbody>{sheets.map(([name, sheet]) => <tr key={name}><td><strong>{name.split('_').join(' ')}</strong></td><td>{sheet.records.toLocaleString('pt-BR')}</td><td>{sheet.duplicate_keys}</td><td>{sheet.missing_columns.length}</td><td><Badge tone={!sheet.duplicate_keys && !sheet.missing_columns.length ? 'good' : 'medium'}>{!sheet.duplicate_keys && !sheet.missing_columns.length ? 'Íntegra' : 'Revisar'}</Badge></td></tr>)}</tbody></table></div></SectionCard>
    <div className="notice-card"><div className="notice-icon">i</div><div><strong>Como interpretar a cobertura</strong><p>Dado ausente de sell-out representa falta de observação, não venda igual a zero. O ranking reduz a confiança quando essa visibilidade não existe.</p></div></div>
  </>;
}

export function B2BPage({ data }: PageProps) {
  return <>
    <PageIntro eyebrow="Colaboração comercial" title="Visibilidade B2B2C" description={`Cobertura dos parceiros com referência em ${formatDate(data.b2b.reference_month)}.`} />
    <div className="partners-grid">{data.b2b.partners.map((partner) => <article className="partner-card" key={partner.partner}>
      <div className="partner-head"><div className="partner-avatar">{partner.name.slice(0, 2).toUpperCase()}</div><div><strong>{partner.name}</strong><span>{partner.partner}</span></div><strong className="coverage-value">{Math.round(partner.coverage * 100)}%</strong></div>
      <div className="partner-level"><span>Nível demonstrativo</span><Badge tone={partnerLevelTone(partner.level)}>{partner.level}</Badge></div>
      <ProgressBar value={partner.coverage} tone={partner.coverage < .4 ? 'red' : 'blue'} />
      <div className="partner-stats"><span><strong>{partner.observed_skus}/{partner.total_skus}</strong>SKUs observados</span><span><strong>{partner.months_observed}</strong>meses disponíveis</span></div>
      <div className="partner-recency"><span>Último sell-out</span><strong>{formatDate(partner.latest_sell_out_month)}</strong></div>
      <div className="partner-next"><span>{partner.next_level ? 'Próximo nível' : 'Situação do nível'}</span><strong>{partner.next_level ?? 'Nível máximo demonstrativo'}</strong><p>{partner.next_level_requirement}</p></div>
    </article>)}</div>
    <div className="notice-card"><div className="notice-icon">i</div><div><strong>Classificação demonstrativa</strong><p>{data.b2b.classification_disclaimer}</p><p>{data.b2b.note}</p></div></div>
  </>;
}

export function ScenariosPage({ data, onSelect }: PageProps) {
  const [excess, setExcess] = useState(data.config.weights.EXCESS_COVERAGE ?? 3);
  const [capacity, setCapacity] = useState(data.config.weights.CAPACITY_CONFLICT ?? 5);
  const [result, setResult] = useState<ScenarioResult>();
  const [running, setRunning] = useState(false);
  const [error, setError] = useState('');
  async function simulate() { setRunning(true); setError(''); try { setResult(await api.scenario({ weights: { EXCESS_COVERAGE: excess, CAPACITY_CONFLICT: capacity } })); } catch (reason) { setError(reason instanceof Error ? reason.message : 'Falha ao simular.'); } finally { setRunning(false); } }
  return <>
    <PageIntro eyebrow="Ambiente seguro" title="Simulação de cenários" description="Teste pesos sem alterar configurações ou o ranking oficial." />
    <div className="scenario-layout"><SectionCard title="Parâmetros da simulação" subtitle="Somente esta visualização será recalculada."><div className="slider-field"><div><label htmlFor="excess">Excesso de cobertura</label><output>{excess}</output></div><input id="excess" type="range" min="0" max="20" value={excess} onChange={(event) => setExcess(Number(event.target.value))} /><small>Oficial: {data.config.weights.EXCESS_COVERAGE}</small></div><div className="slider-field"><div><label htmlFor="capacity">Conflito de capacidade</label><output>{capacity}</output></div><input id="capacity" type="range" min="0" max="20" value={capacity} onChange={(event) => setCapacity(Number(event.target.value))} /><small>Oficial: {data.config.weights.CAPACITY_CONFLICT}</small></div>{error && <p className="inline-error">{error}</p>}<button className="primary-button full-button" onClick={simulate} disabled={running}>{running ? 'Simulando…' : 'Executar simulação'}</button></SectionCard><div className="scenario-explainer"><span>SIMULAÇÃO</span><h3>Nenhuma alteração é persistida</h3><p>Os pesos oficiais e as decisões registradas permanecem intactos. Use o resultado apenas para comparar sensibilidade.</p></div></div>
    {result && <SectionCard title="Resultado simulado" subtitle={result.warning} action={<Badge tone="medium">Cenário hipotético</Badge>}><PriorityTable rows={result.ranking.slice(0, 10)} onSelect={onSelect} /></SectionCard>}
  </>;
}

export function RunsPage({ data, onRefresh }: PageProps) {
  const [saving, setSaving] = useState(false); const [message, setMessage] = useState('');
  async function snapshot() { setSaving(true); setMessage(''); try { const result = await api.createRun(); await onRefresh(); setMessage(`Execução #${result.id} registrada.`); } catch (error) { setMessage(error instanceof Error ? error.message : 'Falha ao registrar execução.'); } finally { setSaving(false); } }
  return <>
    <PageIntro eyebrow="Auditoria" title="Execuções registradas" description="Snapshots preservam fonte, configuração e ranking para consulta posterior." action={<button className="primary-button" onClick={snapshot} disabled={saving}>{saving ? 'Registrando…' : 'Registrar execução atual'}</button>} />
    {message && <div className="toast-inline">{message}</div>}
    <SectionCard title="Histórico" subtitle={`${data.runs.length} snapshots disponíveis.`}>{data.runs.length ? <div className="timeline">{data.runs.map((run) => <article key={run.id}><div className="timeline-dot" /><div><div className="run-title"><strong>Execução #{run.id}</strong><Badge tone="neutral">{run.prioritized_skus} SKUs</Badge></div><p>{formatDateTime(run.created_at)}</p><code>{run.source_hash.slice(0, 16)}…</code></div></article>)}</div> : <EmptyState title="Nenhuma execução registrada" description="Crie o primeiro snapshot auditável do ranking." />}</SectionCard>
  </>;
}

export function FeedbackPage({ data, onRefresh }: PageProps) {
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
    try {
      await api.createFeedback({ sku, action, user_name: user, note, partner_data_effect: partnerDataEffect, analysis_minutes: analysisMinutes === '' ? null : Number(analysisMinutes) });
      setNote(''); setPartnerDataEffect('nao_utilizado'); setAnalysisMinutes('');
      await onRefresh(); setMessage('Decisão registrada com sucesso.');
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Falha ao registrar decisão.'); }
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
        <label>Usuário<input value={user} onChange={(event) => setUser(event.target.value)} placeholder="Seu nome" /></label>
        <label>Observação<textarea value={note} onChange={(event) => setNote(event.target.value)} placeholder="Contexto da decisão" /></label>
        {message && <span className="form-message">{message}</span>}<button className="primary-button" disabled={saving}>{saving ? 'Salvando…' : 'Registrar decisão'}</button>
      </form></SectionCard>
      <SectionCard title="Histórico recente" subtitle="Ação, influência dos dados e tempo de análise.">{data.feedback.length ? <div className="feedback-list">{data.feedback.map((item, index) => <article key={`${item.sku}-${item.created_at}-${index}`}>
        <div className="feedback-head"><strong>{item.sku}</strong><Badge tone={item.action === 'aceita' ? 'good' : item.action === 'rejeitada' ? 'low' : 'medium'}>{statusNames[item.action] ?? item.action}</Badge><Badge tone={item.partner_data_effect === 'alterou_decisao' ? 'good' : item.partner_data_effect === 'aumentou_confianca' ? 'medium' : 'neutral'}>{partnerDataEffectNames[item.partner_data_effect] ?? item.partner_data_effect}</Badge></div>
        <p>{item.note || 'Sem observação.'}</p>
        <div className="feedback-meta"><span>{item.analysis_minutes === null ? 'Tempo não informado' : `${item.analysis_minutes} min de análise`}</span><span>{item.user_name || 'Usuário não informado'} · {formatDateTime(item.created_at)}</span></div>
      </article>)}</div> : <EmptyState title="Nenhuma decisão registrada" description="O feedback do PCP aparecerá aqui." />}</SectionCard>
    </div>
  </>;
}

export function SkuDrawer({ priority, onClose }: { priority: SelectedSku | null; onClose: () => void }) {
  const [detail, setDetail] = useState<SkuDetail>();
  const [error, setError] = useState('');
  useEffect(() => { setDetail(undefined); setError(''); if (priority) api.skuDetail(priority.sku).then(setDetail).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : 'Falha ao carregar detalhe.')); }, [priority]);
  if (!priority) return null;
  const indicator = detail?.indicator;
  const forecast = detail?.forecast;
  const recommendation = detail?.operational_recommendation;
  const rankedPriority = detail?.priority[0];
  const priorityNumber = rankedPriority?.priority ?? priority.priority;
  const attentionScore = rankedPriority?.attention_score ?? priority.attention_score;
  const rankingConfidence = rankedPriority?.confidence ?? priority.confidence;
  const rankingConfidenceReason = rankedPriority?.confidence_reason ?? priority.confidence_reason;
  const delayDays = indicator ? positiveDelayDays(indicator.first_promised_date, indicator.first_production_completion) : null;
  return <>
    <div className="drawer-scrim" onClick={onClose} />
    <aside className="detail-drawer" aria-label={`Detalhe do SKU ${priority.sku}`}>
      <div className="drawer-head">
        <div><span>{priorityNumber === null ? 'SKU fora do ranking oficial' : `Prioridade #${priorityNumber}`}</span><h2>{priority.sku}</h2><p>{priority.product}</p></div>
        <button className="icon-button" onClick={onClose} aria-label="Fechar detalhe"><Icon name="close" /></button>
      </div>
      {error ? <div className="inline-error">{error}</div> : !detail || !indicator ? <div className="drawer-loading"><span /><span /><span /></div> : <div className="drawer-body">
        <div className="drawer-summary">
          <div><span>Score</span><strong>{displayNumber(attentionScore)}</strong></div>
          <div><span>Confiança</span><Badge tone={confidenceTone(rankingConfidence)}>{rankingConfidence}</Badge></div>
          <div><span>Família</span><strong>{indicator.family}</strong></div>
        </div>

        <section className="drawer-section detail-section">
          <div className="drawer-section-heading"><div><span>Contexto operacional</span><h3>Demanda e atendimento</h3></div><Badge tone="neutral">{indicator.analysis_scope}</Badge></div>
          <div className="detail-metrics-grid">
            <div><span>Estoque atual</span><strong>{displayNumber(indicator.current_stock)}</strong></div>
            <div><span>Carteira</span><strong>{displayNumber(indicator.backlog_order_quantity)}</strong></div>
            <div><span>Produção aberta</span><strong>{displayNumber(indicator.production_order_quantity)}</strong></div>
            <div><span>Estoque projetado</span><strong>{displayNumber(indicator.projected_stock_quantity)}</strong></div>
            <div className={indicator.operational_gap_quantity > 0 ? 'metric-alert' : ''}><span>Lacuna operacional</span><strong>{displayNumber(indicator.operational_gap_quantity)}</strong><small>Quantidade para análise</small></div>
            <div><span>Cobertura</span><strong>{displayNumber(indicator.coverage_days_calculated)} dias</strong><small>Lead time: {displayNumber(indicator.lead_time_days)} dias</small></div>
          </div>
          <div className="date-comparison">
            <div><span>Primeira data prometida</span><strong>{formatDate(indicator.first_promised_date)}</strong></div>
            <div><span>Primeira conclusão prevista</span><strong>{formatDate(indicator.first_production_completion)}</strong></div>
            {delayDays !== null && <div className="delay-callout"><span>Atraso identificado</span><strong>{delayDays} {delayDays === 1 ? 'dia' : 'dias'}</strong></div>}
          </div>
        </section>

        <section className="drawer-section detail-section">
          <div className="drawer-section-heading"><div><span>Qualidade da análise</span><h3>Canal e confiança</h3></div><Badge tone={confidenceTone(rankingConfidence)}>{rankingConfidence}</Badge></div>
          <div className="detail-metrics-grid channel-grid">
            <div><span>Sell-in acumulado</span><strong>{displayNumber(indicator.sell_in_quantity)}</strong></div>
            <div><span>Sell-out acumulado</span><strong>{displayNumber(indicator.sell_out_quantity)}</strong></div>
            <div><span>Diferença observada</span><strong>{displayNumber(indicator.sell_in_minus_sell_out_quantity)}</strong></div>
            <div><span>Parceiros com sell-out</span><strong>{displayNumber(indicator.sell_out_partner_count)}</strong></div>
            <div><span>Forecast disponível</span><strong>{displayNumber(indicator.forecast_quantity)}</strong></div>
          </div>
          <div className="confidence-explanation"><strong>Por que esta confiança?</strong><p>{rankingConfidenceReason}</p></div>
          {indicator.missing_data.length > 0 ? <div className="missing-data"><strong>Dados ausentes</strong><ul>{indicator.missing_data.map((field) => <li key={field}>{missingDataNames[field] ?? field.split('_').join(' ')}</li>)}</ul><p>Ausência de dado não é interpretada como valor zero.</p></div> : <div className="data-complete"><span>✓</span><p><strong>Dados principais disponíveis</strong>Não foram identificadas ausências nos campos desta análise.</p></div>}
        </section>

        {forecast && recommendation && <section className="drawer-section detail-section forecast-section">
          <div className="drawer-section-heading"><div><span>Modelo preditivo</span><h3>Previsão e recomendação</h3></div><Badge tone={confidenceTone(recommendation.confidence)}>{recommendation.confidence}</Badge></div>
          {forecast.status === 'insufficient_data' ? <div className="forecast-empty"><strong>Dados insuficientes</strong><p>{forecast.limitation}</p><Badge tone="medium">{recommendation.action_label}</Badge></div> : <>
            <div className="detail-metrics-grid forecast-metrics">
              <div><span>Tendência</span><strong className={`trend-${forecast.trend}`}>{forecast.trend}</strong><small>{forecast.trend_change_ratio === null ? 'Sem comparação percentual' : displayPercent(forecast.trend_change_ratio)}</small></div>
              <div><span>Modelo selecionado</span><strong>{forecast.model_label}</strong><small>{forecast.history_months} meses analisados</small></div>
              <div><span>Erro no backtest</span><strong>{displayPercent(forecast.backtest_wape)}</strong><small>WAPE nos 3 meses reservados</small></div>
              <div><span>Próximo mês</span><strong>{displayNumber(forecast.forecast_next_month)}</strong><small>unidades previstas</small></div>
              <div><span>Próximos 3 meses</span><strong>{displayNumber(forecast.forecast_total_3m)}</strong><small>unidades previstas</small></div>
              <div className={recommendation.suggested_quantity && recommendation.suggested_quantity > 0 ? 'metric-recommendation' : ''}><span>Quantidade sugerida</span><strong>{displayNumber(recommendation.suggested_quantity)}</strong><small>{recommendation.horizon}</small></div>
            </div>
            <div className="forecast-months">{forecast.forecast_months.map((month, index) => <div key={month}><span>{formatDate(month)}</span><strong>{displayNumber(forecast.forecast_values[index])}</strong><small>unidades</small></div>)}</div>
            <div className="recommendation-card">
              <div><span>Ação sugerida</span><strong>{recommendation.action_label}</strong><Badge tone={recommendation.capacity_status === 'requires_review' ? 'medium' : 'good'}>{recommendation.capacity_status === 'requires_review' ? 'Validar capacidade' : 'Contexto familiar disponível'}</Badge></div>
              <p>{recommendation.rationale.join(' ')}</p>
              <div className="calculation-line"><span>Demanda a cobrir</span><strong>{displayNumber(recommendation.calculation.demand_to_cover)}</strong><span>+ Segurança</span><strong>{displayNumber(recommendation.calculation.safety_stock_quantity)}</strong><span>− Estoque</span><strong>{displayNumber(recommendation.calculation.current_stock)}</strong><span>− Produção aberta</span><strong>{displayNumber(recommendation.calculation.open_production_quantity)}</strong></div>
            </div>
            <div className="human-review"><strong>Revisão humana obrigatória</strong><p>{recommendation.confidence_reason} A sugestão não cria nem libera ordem de produção.</p></div>
          </>}
          <p className="forecast-limitation">{forecast.limitation}</p>
        </section>}

        <div className="drawer-section"><h3>Riscos e evidências</h3>{detail.issues.map((issue) => <article className="issue-card" key={issue.code}><div><Badge tone={severityTone(issue.severity)}>{issue.severity}</Badge><strong>{reasonNames[issue.code] ?? issue.code}</strong></div><p>{issue.description}</p><dl>{Object.entries(issue.values_used).map(([key, value]) => <div key={key}><dt>{key.split('_').join(' ')}</dt><dd>{String(value)}</dd></div>)}</dl><small>Origem: {issue.data_origin.join(' · ')}</small></article>)}</div>
        <div className="drawer-note"><strong>Limitação conhecida</strong><p>{detail.limitation}</p></div>
      </div>}
    </aside>
  </>;
}
