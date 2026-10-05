import { useState } from 'react';
import { api } from '../api';
import { Badge, PageIntro, PriorityTable, SectionCard } from '../components';
import type { ScenarioResult } from '../types';
import type { PageProps } from './shared';

export default function ScenariosPage({ data, onSelect }: PageProps) {
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
