import { Link } from 'react-router-dom';
import { Badge, Icon, PageIntro, SectionCard } from '../components';
import { glossary } from './shared';

const trails = [
  { id: 'pcp', role: 'PCP', question: 'O que devo olhar primeiro e preciso produzir?', steps: [{ label: 'Início', to: '/', text: 'Veja o primeiro SKU da fila e o porquê.' }, { label: 'Fila de atenção', to: '/prioridades', text: 'Confira a ordem completa e os sinais de cada SKU.' }, { label: 'Previsão e ação', to: '/previsoes', text: 'Veja a ação e a quantidade sugeridas; abra o SKU para ver o cálculo.' }, { label: 'Registrar decisão', to: '/decisoes', text: 'Guarde o que você decidiu e quanto tempo levou.' }] },
  { id: 'comercial', role: 'Comercial', question: 'Qual parceiro tem oportunidade de reposição?', steps: [{ label: 'Parceiros · Oportunidades', to: '/parceiros', text: 'Lista de oportunidades de reposição por parceiro e SKU.' }, { label: 'Detalhe do parceiro', to: '/parceiros', text: 'Escolha um parceiro e abra as evidências mensais de cada SKU.' }] },
  { id: 'gestao', role: 'Gestão', question: 'Quanto posso confiar nessas recomendações?', steps: [{ label: 'Confiança nas recomendações', to: '/validacao', text: 'Veredito, erro da previsão, casos de teste e falhas conhecidas.' }, { label: 'Dados da planilha', to: '/qualidade', text: 'Integridade da base e cobertura de sell-out.' }, { label: 'Execuções', to: '/execucoes', text: 'Compare duas execuções para explicar por que uma prioridade mudou.' }] },
];

const guideGlossary = [
  ...(['score', 'confianca_dados', 'confianca_previsao', 'wape', 'baseline', 'holdout', 'sellin', 'sellout', 'leadtime', 'cobertura', 'ausente', 'op'] as const).map((term) => ({ term: glossary[term].name, description: glossary[term].text })),
  { term: 'Data crítica', description: 'Primeira referência operacional relevante, como a data prometida ao cliente ou a conclusão prevista da produção.' },
  { term: 'Lacuna operacional', description: 'Carteira menos estoque e produção aberta, quando positiva. É quantidade para análise, não ordem recomendada.' },
  { term: 'Recomendação operacional', description: 'Ação e quantidade sugeridas por SKU a partir de previsão, carteira, segurança, estoque e lote mínimo. Sempre exige revisão humana.' },
  { term: 'Recomendação comercial', description: 'Sugestão por parceiro e SKU (repor, monitorar, investigar ou pedir dados), baseada apenas em sell-in, sell-out e estoque estimado daquele parceiro.' },
];

const guideFaq = [
  { question: 'Como os dados são atualizados?', answer: 'O botão “Atualizar” recarrega a página atual a partir do backend. A planilha de origem é somente leitura; a página Execuções registra uma foto do momento para auditoria.' },
  { question: 'O que significa confiança baixa?', answer: 'Significa que informações relevantes estão ausentes ou têm cobertura limitada. Use o ranking como sinal de investigação e valide as evidências antes de decidir.' },
  { question: 'O que fazer quando o sell-out ou outro dado está zerado?', answer: 'Primeiro confirme se o zero foi realmente informado. Campo ausente e valor zero têm significados diferentes; o sistema sinaliza dados ausentes para evitar essa confusão.' },
  { question: 'Um SKU com prioridade alta precisa ser produzido?', answer: 'Não necessariamente. A prioridade indica o que investigar primeiro; a recomendação operacional pode ser “Sem ação necessária” quando estoque e produção aberta já cobrem a demanda. Isso não elimina os riscos.' },
  { question: 'Como explicar por que uma prioridade mudou?', answer: 'Em Avançado › Execuções, compare duas execuções. A tela mostra sinais novos ou removidos, pesos alterados e a decomposição da diferença de score.' },
  { question: 'Uma simulação altera os dados reais?', answer: 'Não. Cenários são temporários, não persistem os pesos testados e não alteram o ranking oficial nem as decisões já registradas.' },
  { question: 'O que significam os avisos “Demonstração” e “Somente leitura”?', answer: 'Em demonstração, os dados são fictícios e os registros podem ser apagados. Em somente leitura, a publicação permite consultar tudo, mas não registrar decisões, casos ou execuções.' },
  { question: 'O sistema emite uma ordem de produção automaticamente?', answer: 'Não. O protótipo organiza sinais e evidências para apoiar o PCP, mas toda decisão e execução continuam sob responsabilidade humana.' },
];

export default function GuidePage() {
  return <div className="guide-page">
    <PageIntro title="Entenda o Caderno Inteligente em poucos minutos" description="Escolha o seu papel, siga o caminho sugerido e use os indicadores como apoio para uma decisão humana mais rápida e explicável." action={<Link className="primary-button" to="/">Começar pelo início <Icon name="arrow" size={17} /></Link>} />
    <section className="guide-start" aria-labelledby="guide-start-title">
      <div className="guide-start-copy"><Badge tone="good">Regra de uso</Badge><h3 id="guide-start-title">Toda sugestão exige revisão humana</h3><p>O sistema organiza sinais e evidências. Ele não é uma ordem de produção, não libera produção e não decide por você.</p></div>
      <ol className="guide-steps">
        <li><span>1</span><div><strong>Veja o que pede atenção</strong><p>Fila de atenção e Início.</p></div></li>
        <li><span>2</span><div><strong>Abra as evidências</strong><p>Cada SKU mostra o cálculo e a origem dos dados.</p></div></li>
        <li><span>3</span><div><strong>Confira os parceiros</strong><p>Contexto comercial separado do estoque do CD.</p></div></li>
        <li><span>4</span><div><strong>Cheque a confiança</strong><p>Validação e dados da planilha.</p></div></li>
        <li><span>5</span><div><strong>Registre a decisão</strong><p>Com o tempo de análise.</p></div></li>
      </ol>
    </section>
    <SectionCard title="Por onde começar, conforme o seu papel" subtitle="Cada trilha leva só às telas de que você precisa.">
      <div className="guide-pages-grid">{trails.map((trail) => <article className="guide-page-card" key={trail.id}><div className="guide-page-copy"><span>{trail.role}</span><h4>{trail.question}</h4><ol className="guide-trail">{trail.steps.map((step) => <li key={step.label}><Link className="guide-link" to={step.to}>{step.label}</Link><span>{step.text}</span></li>)}</ol></div></article>)}</div>
    </SectionCard>
    <SectionCard title="Entenda os indicadores" subtitle="Conceitos essenciais em linguagem simples."><dl className="guide-glossary">{guideGlossary.map((item) => <div key={item.term}><dt>{item.term}</dt><dd>{item.description}</dd></div>)}</dl></SectionCard>
    <section className="guide-limitations" aria-labelledby="guide-limitations-title"><span className="guide-section-label">Transparência</span><h3 id="guide-limitations-title">O que este protótipo não faz</h3><ul><li>Não executa decisões nem libera produção automaticamente.</li><li>Usa uma base fictícia de demonstração; não está integrado a sistemas reais.</li><li>Não distribui estoque, produção ou previsão global entre parceiros.</li><li>Não substitui a validação manual quando há baixa confiança ou dados ausentes.</li><li>Não possui login; publicações abertas devem usar o modo somente leitura.</li></ul></section>
    <SectionCard title="Dúvidas frequentes" subtitle="Respostas rápidas para usar o protótipo com segurança."><div className="guide-faq">{guideFaq.map((item) => <details key={item.question}><summary>{item.question}<span aria-hidden="true">+</span></summary><p>{item.answer}</p></details>)}</div></SectionCard>
    <p className="details-note">Roteiro de demonstração de 5 minutos: <code>docs/roteiro-demonstracao.md</code>.</p>
  </div>;
}
