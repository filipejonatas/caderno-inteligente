import { Link } from 'react-router-dom';
import { Icon, PageIntro, SectionCard } from '../components';
import { CHALLENGE_DEFINITIONS, CHALLENGE_NAMES } from './shared';

const trails = [
  { id: 'pcp', role: 'PCP', question: 'O que devo olhar primeiro e preciso produzir?', steps: [{ label: 'Início', to: '/', text: 'Veja o primeiro SKU da fila e o porquê.' }, { label: 'Fila operacional', to: '/fila', text: 'Veja a ordem, a ação e a quantidade; abra o SKU para o cálculo.' }, { label: 'Casos', to: '/casos', text: 'Acompanhe e conclua os casos abertos.' }, { label: 'Histórico de decisões', to: '/decisoes', text: 'Consulte o que foi decidido e registre novas decisões.' }] },
  { id: 'comercial', role: 'Comercial', question: 'Qual parceiro tem oportunidade de reposição?', steps: [{ label: 'Comercial · Oportunidades', to: '/parceiros', text: 'Oportunidades de reposição por parceiro e SKU, das mais urgentes.' }, { label: 'Detalhe do parceiro', to: '/carteira', text: 'Escolha um parceiro e abra as evidências de cada SKU.' }] },
  { id: 'gestao', role: 'Gestão', question: 'Quanto posso confiar nessas recomendações?', steps: [{ label: 'Confiança nas recomendações', to: '/validacao', text: 'Resumo, erro da previsão e falhas conhecidas.' }, { label: 'Dados da planilha', to: '/qualidade', text: 'Integridade da base e cobertura de sell-out.' }, { label: 'Auditoria', to: '/auditoria', text: 'Casos de teste, limitações e histórico de ajustes.' }, { label: 'Execuções', to: '/execucoes', text: 'Compare duas execuções para explicar uma mudança no ranking.' }] },
];

const guideGlossary = [
  { term: 'Pontos de atenção (score)', description: 'Soma dos pesos dos problemas do SKU; ordena a análise.' },
  { term: 'Confiança nos dados', description: 'Qualidade da evidência usada no ranking.' },
  { term: 'Confiança na previsão', description: 'Baseada no erro do modelo nos últimos 3 meses.' },
  { term: 'Erro médio (WAPE)', description: 'Quanto a previsão errou, em %, nos últimos 3 meses.' },
  { term: 'Previsão simples (baseline)', description: 'Repete o último mês; serve de comparação.' },
  { term: 'Teste dos últimos 3 meses (holdout)', description: 'Meses reservados para medir o erro do modelo.' },
  { term: 'Sell-in e sell-out', description: 'Vendido ao parceiro e vendido pelo parceiro ao consumidor.' },
  { term: 'Prazo de produção (lead time)', description: 'Dias entre pedir e receber a produção.' },
  { term: 'Cobertura', description: 'Dias que o estoque dura no ritmo atual de venda.' },
  { term: 'Dado ausente', description: 'Não existe na planilha; nunca vale zero.' },
  { term: 'Ordem de produção (OP)', description: 'Este sistema nunca cria nem libera uma OP.' },
  ...Object.entries(CHALLENGE_NAMES).map(([code, name]) => ({ term: `Rótulo: ${name}`, description: CHALLENGE_DEFINITIONS[code] })),
];

const guideFaq = [
  { question: 'Um SKU com prioridade alta precisa ser produzido?', answer: 'Não necessariamente. A prioridade diz o que investigar primeiro; a recomendação pode ser “Sem ação necessária” se estoque e produção já cobrem a demanda. Os riscos continuam.' },
  { question: 'O que significa confiança baixa?', answer: 'Faltam dados ou a cobertura é parcial. Valide as evidências antes de decidir.' },
  { question: 'O que fazer quando o sell-out está zerado ou ausente?', answer: 'Confirme se o zero foi informado. Ausente e zero são coisas diferentes.' },
  { question: 'O sistema emite uma ordem de produção?', answer: 'Não. Toda decisão e execução continuam sob responsabilidade humana.' },
];

export default function GuidePage() {
  return <div className="guide-page">
    <PageIntro title="Entenda o Caderno Inteligente em poucos minutos" action={<Link className="primary-button" to="/">Começar pelo início <Icon name="arrow" size={17} /></Link>} />
    <SectionCard title="Por onde começar, conforme o seu papel">
      <div className="guide-pages-grid">{trails.map((trail) => <article className="guide-page-card" key={trail.id}><div className="guide-page-copy"><span>{trail.role}</span><h4>{trail.question}</h4><ol className="guide-trail">{trail.steps.map((step) => <li key={step.label}><Link className="guide-link" to={step.to}>{step.label}</Link><span>{step.text}</span></li>)}</ol></div></article>)}</div>
    </SectionCard>
    <SectionCard title="Entenda os termos"><dl className="guide-glossary">{guideGlossary.map((item) => <div key={item.term}><dt>{item.term}</dt><dd>{item.description}</dd></div>)}</dl></SectionCard>
    <section className="guide-limitations" aria-labelledby="guide-limitations-title"><span className="guide-section-label">Transparência</span><h3 id="guide-limitations-title">O que este protótipo não faz</h3><ul><li>Não executa decisões nem libera produção.</li><li>Usa uma base fictícia, sem integração com sistemas reais.</li><li>Não distribui estoque, produção ou previsão global entre parceiros.</li></ul></section>
    <SectionCard title="Dúvidas frequentes"><div className="guide-faq">{guideFaq.map((item) => <details key={item.question}><summary>{item.question}<span aria-hidden="true">+</span></summary><p>{item.answer}</p></details>)}</div></SectionCard>
  </div>;
}
