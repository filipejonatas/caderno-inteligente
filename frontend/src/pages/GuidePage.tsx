import { Link } from 'react-router-dom';
import { Badge, Icon, PageIntro, SectionCard, navigation } from '../components';

const pageDescriptions: Record<string, { eyebrow: string; description: string }> = {
  overview: { eyebrow: 'Comece aqui', description: 'Veja o pulso da operação, os principais riscos e o que exige atenção hoje.' },
  priorities: { eyebrow: 'Ordene a análise', description: 'Consulte os SKUs ordenados por urgência e abra as evidências de cada sinal.' },
  forecasts: { eyebrow: 'Planeje a demanda', description: 'Compare forecast, confiança e ação sugerida antes da validação humana.' },
  cases: { eyebrow: 'Acompanhe ações', description: 'Transforme um alerta em responsável, prazo e acompanhamento operacional.' },
  quality: { eyebrow: 'Valide a base', description: 'Entenda cobertura, integridade e lacunas antes de tomar uma decisão.' },
  b2b: { eyebrow: 'Observe o canal', description: 'Compare a cobertura de sell-out e o nível demonstrativo dos parceiros.' },
  scenarios: { eyebrow: 'Teste hipóteses', description: 'Altere pesos em uma simulação segura, sem modificar o ranking oficial.' },
  runs: { eyebrow: 'Preserve o histórico', description: 'Registre snapshots auditáveis da fonte, configuração e ranking.' },
  feedback: { eyebrow: 'Feche o ciclo', description: 'Registre a decisão humana e como os dados do parceiro influenciaram a análise.' },
};

const guidePages = navigation.filter((item) => item.id !== 'guide').map((item) => ({ ...item, ...pageDescriptions[item.id] }));

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

export default function GuidePage() {
  return <div className="guide-page">
    <PageIntro eyebrow="Onboarding do protótipo" title="Entenda o Caderno Inteligente em poucos minutos" description="Siga o fluxo recomendado, conheça cada área e use os indicadores como apoio para uma decisão humana mais rápida e explicável." action={<Link className="primary-button" to="/">Começar pela visão geral <Icon name="arrow" size={17} /></Link>} />
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
      <div className="guide-pages-grid">{guidePages.map((item) => <article className="guide-page-card" key={item.id}><div className="guide-page-icon"><Icon name={item.id} /></div><div className="guide-page-copy"><span>{item.eyebrow}</span><h4>{item.label}</h4><p>{item.description}</p></div><Link className="guide-link" to={item.path}>Abrir página <Icon name="arrow" size={15} /></Link></article>)}</div>
    </SectionCard>
    <SectionCard title="Entenda os indicadores" subtitle="Conceitos essenciais em linguagem simples."><dl className="guide-glossary">{guideGlossary.map((item) => <div key={item.term}><dt>{item.term}</dt><dd>{item.description}</dd></div>)}</dl></SectionCard>
    <div className="guide-two-columns">
      <section className="guide-limitations" aria-labelledby="guide-limitations-title"><span className="guide-section-label">Transparência</span><h3 id="guide-limitations-title">O que este protótipo não faz</h3><ul><li>Não executa decisões ou libera produção automaticamente.</li><li>Pode utilizar dados simulados para demonstrar o conceito.</li><li>Não substitui a validação manual quando há baixa confiança ou dados ausentes.</li><li>Uma simulação não equivale a uma ordem real de produção ou compra.</li></ul></section>
      <section className="guide-demo" aria-labelledby="guide-demo-title"><span className="guide-section-label">Apresentação</span><h3 id="guide-demo-title">Roteiro de demonstração</h3><p className="guide-demo-time">2–3 minutos</p><ol><li><strong>30s</strong><span>Mostre o problema na Visão geral.</span></li><li><strong>45s</strong><span>Abra uma prioridade e explique as evidências.</span></li><li><strong>30s</strong><span>Destaque a qualidade e a visibilidade do parceiro.</span></li><li><strong>45s</strong><span>Simule um cenário e registre a decisão humana.</span></li></ol></section>
    </div>
    <SectionCard title="Dúvidas frequentes" subtitle="Respostas rápidas para usar o protótipo com segurança."><div className="guide-faq">{guideFaq.map((item) => <details key={item.question}><summary>{item.question}<span aria-hidden="true">+</span></summary><p>{item.answer}</p></details>)}</div></SectionCard>
    <div className="guide-footer-cta"><div><span>Pronto para explorar?</span><strong>Comece pelo panorama e siga os sinais.</strong></div><Link className="primary-button" to="/">Abrir visão geral <Icon name="arrow" size={17} /></Link></div>
  </div>;
}
