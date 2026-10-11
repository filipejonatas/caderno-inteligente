/**
 * A jornada do PCP, na ordem em que se trabalha: ver, decidir, caber, atender, confiar.
 * Um mapa só alimenta o Início (JourneyStrip) e o "Próximo passo" no fim de cada página.
 */
export interface JourneyStep { id: 'ver' | 'decidir' | 'caber' | 'atender' | 'confiar'; verb: string; question: string; to: string }

export const JOURNEY: JourneyStep[] = [
  { id: 'ver', verb: 'Ver', question: 'O que arde agora?', to: '/fila?sinal=ruptura' },
  { id: 'decidir', verb: 'Decidir', question: 'O que decido hoje?', to: '/fila' },
  { id: 'caber', verb: 'Caber', question: 'A produção cabe na linha?', to: '/capacidade' },
  { id: 'atender', verb: 'Atender', question: 'Quem recebe primeiro?', to: '/parceiros' },
  { id: 'confiar', verb: 'Confiar', question: 'Posso confiar nisso?', to: '/validacao' },
];

export interface NextStepInfo { text: string; label: string; to: string }

/** Próximo passo por página (só o caminho, sem busca). Quem não está aqui não mostra o rodapé. */
export const NEXT_STEPS: Record<string, NextStepInfo> = {
  '/fila': { text: 'Com a fila vista, falta saber se a produção cabe na linha.', label: 'Seguir para a capacidade', to: '/capacidade' },
  '/capacidade': { text: 'O que não cabe vira pedido sem cobertura. Falta decidir quem recebe primeiro.', label: 'Seguir para as oportunidades', to: '/parceiros' },
  '/parceiros': { text: 'Com a reposição por parceiro definida, veja quanto isso rende.', label: 'Seguir para o faturamento', to: '/faturamento' },
  '/faturamento': { text: 'Antes de agir, confira o quanto dá para confiar nessas estimativas.', label: 'Seguir para a confiança', to: '/validacao' },
  '/validacao': { text: 'Fim do caminho. Volte ao Início para ver o que mudou.', label: 'Voltar ao Início', to: '/' },
};
