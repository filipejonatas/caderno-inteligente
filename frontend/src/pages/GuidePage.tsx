import { Link } from 'react-router-dom';
import { Badge, Icon, PageIntro, SectionCard, navigation } from '../components';

const pageDescriptions: Record<string, { eyebrow: string; description: string }> = {
  overview: { eyebrow: 'Comece aqui', description: 'Veja o primeiro SKU da fila, os riscos de ruptura e a qualidade da evidência disponível.' },
  priorities: { eyebrow: 'Ordene a análise', description: 'Consulte o ranking oficial, filtre por família ou confiança e abra as evidências de cada sinal.' },
  forecasts: { eyebrow: 'Planeje a demanda', description: 'Compare previsão, erro no holdout, ação operacional sugerida e quantidade para revisão.' },
  cases: { eyebrow: 'Acompanhe ações', description: 'Transforme um alerta em responsável, prazo e acompanhamento operacional.' },
  quality: { eyebrow: 'Valide a base', description: 'Entenda cobertura, integridade e lacunas antes de tomar uma decisão.' },
  b2b: { eyebrow: 'Observe o canal', description: 'Veja a cobertura medida de cada parceiro e as sugestões comerciais por parceiro e SKU, com evidências mensais.' },
  scenarios: { eyebrow: 'Teste hipóteses', description: 'Altere pesos em uma simulação segura, sem modificar o ranking oficial.' },
  runs: { eyebrow: 'Preserve o histórico', description: 'Registre snapshots auditáveis e compare duas execuções para explicar por que uma prioridade mudou.' },
  feedback: { eyebrow: 'Feche o ciclo', description: 'Registre a decisão humana, o efeito do dado do parceiro e o tempo de análise.' },
  validation: { eyebrow: 'Prove a aplicabilidade', description: 'Compare com o processo atual, avalie a previsão contra a baseline e confira casos congelados e falhas.' },
};

const guidePages = navigation.filter((item) => item.id !== 'guide').map((item) => ({ ...item, ...pageDescriptions[item.id] }));

const guideGlossary = [
  { term: 'Pontuação de atenção', description: 'Soma transparente dos pesos dos sinais encontrados. Quanto maior o score, mais cedo o item deve ser analisado — não significa decisão automática.' },
  { term: 'Confiança', description: 'Indica a qualidade e a cobertura dos dados usados. Confiança baixa pede validação humana antes de agir.' },
  { term: 'Data crítica', description: 'Primeira referência operacional relevante, como a data prometida ao cliente ou a conclusão prevista da produção.' },
  { term: 'Lacuna operacional', description: 'Carteira menos estoque e produção aberta, quando positiva. É quantidade para análise, não ordem recomendada.' },
  { term: 'Recomendação operacional', description: 'Ação e quantidade sugeridas por SKU a partir de previsão, carteira, segurança, estoque e lote mínimo. Sempre exige revisão humana.' },
  { term: 'Recomendação comercial', description: 'Sugestão por parceiro e SKU (repor, monitorar, investigar ou pedir dados), baseada apenas em sell-in, sell-out e estoque estimado daquele parceiro.' },
  { term: 'WAPE e baseline', description: 'WAPE é o erro absoluto ponderado nos três meses reservados. A baseline repete o último mês e mostra se o modelo realmente acrescenta algo.' },
  { term: 'Dado ausente', description: 'Informação que não foi observada na fonte. Ausência nunca é interpretada automaticamente como valor zero.' },
  { term: 'Nível B2B2C', description: 'Classificação demonstrativa da visibilidade de cada parceiro, baseada na cobertura e na recorrência dos dados compartilhados.' },
];

const guideFaq = [
  { question: 'Como os dados são atualizados?', answer: 'O botão “Atualizar” recarrega a página atual a partir do backend. A planilha de origem é somente leitura; a página Execuções registra um snapshot do momento para auditoria.' },
  { question: 'O que significa confiança baixa?', answer: 'Significa que informações relevantes estão ausentes ou têm cobertura limitada. Use o ranking como sinal de investigação e valide as evidências antes de decidir.' },
  { question: 'O que fazer quando o sell-out ou outro dado está zerado?', answer: 'Primeiro confirme se o zero foi realmente informado. Campo ausente e valor zero têm significados diferentes; o sistema sinaliza dados ausentes para evitar essa confusão.' },
  { question: 'Um SKU com prioridade alta precisa ser produzido?', answer: 'Não necessariamente. A prioridade indica o que investigar primeiro; a recomendação operacional pode ser “Sem ação necessária” quando estoque e produção aberta já cobrem a demanda.' },
  { question: 'Como explicar por que uma prioridade mudou?', answer: 'Em Execuções, compare duas execuções. A tela mostra sinais novos ou removidos, pesos alterados e a decomposição da diferença de score.' },
  { question: 'Uma simulação altera os dados reais?', answer: 'Não. Cenários são temporários, não persistem os pesos testados e não alteram o ranking oficial nem as decisões já registradas.' },
  { question: 'O que significam os avisos “Demonstração” e “Somente leitura”?', answer: 'Em demonstração, os dados são fictícios e os registros podem ser apagados. Em somente leitura, a publicação permite consultar tudo, mas não registrar decisões, casos ou execuções.' },
  { question: 'O sistema emite uma ordem de produção automaticamente?', answer: 'Não. O protótipo organiza sinais e evidências para apoiar o PCP, mas toda decisão e execução continuam sob responsabilidade humana.' },
];

export default function GuidePage() {
  return <div className="guide-page">
    <PageIntro eyebrow="Onboarding do protótipo" title="Entenda o Caderno Inteligente em poucos minutos" description="Siga o fluxo recomendado, conheça cada área e use os indicadores como apoio para uma decisão humana mais rápida e explicável." action={<Link className="primary-button" to="/">Começar pela visão geral <Icon name="arrow" size={17} /></Link>} />
    <section className="guide-start" aria-labelledby="guide-start-title">
      <div className="guide-start-copy"><Badge tone="good">Fluxo recomendado</Badge><h3 id="guide-start-title">Do sinal à decisão, em cinco passos</h3><p>Uma sequência simples para explorar o protótipo sem se perder entre as telas.</p></div>
      <ol className="guide-steps">
        <li><span>1</span><div><strong>Confira o panorama</strong><p>Abra a Visão geral e identifique o primeiro SKU da fila e os riscos de ruptura.</p></div></li>
        <li><span>2</span><div><strong>Entenda a prioridade</strong><p>Abra as evidências do SKU e compare a prioridade com a ação operacional sugerida.</p></div></li>
        <li><span>3</span><div><strong>Consulte o parceiro</strong><p>Veja o contexto comercial por parceiro, sem misturar com o estoque do CD.</p></div></li>
        <li><span>4</span><div><strong>Valide a confiança</strong><p>Confira dados ausentes, qualidade e a Central de validação antes de agir.</p></div></li>
        <li><span>5</span><div><strong>Registre a decisão</strong><p>Crie o acompanhamento e guarde o feedback do PCP com o tempo de análise.</p></div></li>
      </ol>
    </section>
    <SectionCard title="O que há em cada página" subtitle="Use os atalhos para ir direto ao ponto.">
      <div className="guide-pages-grid">{guidePages.map((item) => <article className="guide-page-card" key={item.id}><div className="guide-page-icon"><Icon name={item.id} /></div><div className="guide-page-copy"><span>{item.eyebrow}</span><h4>{item.label}</h4><p>{item.description}</p></div><Link className="guide-link" to={item.path}>Abrir página <Icon name="arrow" size={15} /></Link></article>)}</div>
    </SectionCard>
    <SectionCard title="Entenda os indicadores" subtitle="Conceitos essenciais em linguagem simples."><dl className="guide-glossary">{guideGlossary.map((item) => <div key={item.term}><dt>{item.term}</dt><dd>{item.description}</dd></div>)}</dl></SectionCard>
    <div className="guide-two-columns">
      <section className="guide-limitations" aria-labelledby="guide-limitations-title"><span className="guide-section-label">Transparência</span><h3 id="guide-limitations-title">O que este protótipo não faz</h3><ul><li>Não executa decisões nem libera produção automaticamente.</li><li>Usa uma base fictícia de demonstração; não está integrado a sistemas reais.</li><li>Não distribui estoque, produção ou previsão global entre parceiros.</li><li>Não substitui a validação manual quando há baixa confiança ou dados ausentes.</li><li>Não possui login; publicações abertas devem usar o modo somente leitura.</li></ul></section>
      <section className="guide-demo" aria-labelledby="guide-demo-title"><span className="guide-section-label">Apresentação</span><h3 id="guide-demo-title">Roteiro de demonstração</h3><p className="guide-demo-time">5 minutos</p><ol><li><strong>1 min</strong><span>Problema e linha de base: 22 h semanais de análise e visibilidade parcial do parceiro.</span></li><li><strong>1 min</strong><span>Visão geral: primeiro SKU da fila, riscos e qualidade da evidência.</span></li><li><strong>1 min</strong><span>Prioridade e recomendação operacional no detalhe do SKU.</span></li><li><strong>1 min</strong><span>Parceiro e recomendação comercial com evidências mensais.</span></li><li><strong>1 min</strong><span>Validação: baseline, casos congelados e comportamento seguro.</span></li></ol></section>
    </div>
    <SectionCard title="Dúvidas frequentes" subtitle="Respostas rápidas para usar o protótipo com segurança."><div className="guide-faq">{guideFaq.map((item) => <details key={item.question}><summary>{item.question}<span aria-hidden="true">+</span></summary><p>{item.answer}</p></details>)}</div></SectionCard>
    <div className="guide-footer-cta"><div><span>Pronto para explorar?</span><strong>Comece pelo panorama e siga os sinais.</strong></div><Link className="primary-button" to="/">Abrir visão geral <Icon name="arrow" size={17} /></Link></div>
  </div>;
}
