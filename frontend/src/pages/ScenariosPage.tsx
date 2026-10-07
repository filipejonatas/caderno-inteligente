import { useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import { Badge, PageIntro, PriorityTable, SectionCard } from '../components';
import type { ScenarioResult } from '../types';
import type { PageProps } from './shared';

export default function ScenariosPage({ data, onSelect }: PageProps<'config'>) {
  const [excess, setExcess] = useState(data.config.weights.EXCESS_COVERAGE ?? 3);
  const [capacity, setCapacity] = useState(data.config.weights.CAPACITY_SHORTFALL ?? 7);
  const [result, setResult] = useState<ScenarioResult>();
  const [running, setRunning] = useState(false);
  const [error, setError] = useState('');
  async function simulate() { setRunning(true); setError(''); try { setResult(await api.scenario({ weights: { EXCESS_COVERAGE: excess, CAPACITY_SHORTFALL: capacity } })); } catch (reason) { setError(reason instanceof Error ? reason.message : 'Falha ao simular.'); } finally { setRunning(false); } }
  return <>
    <PageIntro title="E se o peso de um sinal mudar?" action={<Link className="secondary-button" to="/fila">Voltar à fila</Link>} />
    <div className="scenario-layout"><SectionCard title={`Simular 2 dos ${Object.keys(data.config.weights).length} pesos (nada é gravado)`}><div className="slider-field"><div><label htmlFor="excess">Excesso de cobertura</label><output>{excess}</output></div><input id="excess" type="range" min="0" max="20" value={excess} onChange={(event) => setExcess(Number(event.target.value))} /><small>Oficial: {data.config.weights.EXCESS_COVERAGE}</small></div><div className="slider-field"><div><label htmlFor="capacity">Não cabe na capacidade</label><output>{capacity}</output></div><input id="capacity" type="range" min="0" max="20" value={capacity} onChange={(event) => setCapacity(Number(event.target.value))} /><small>Oficial: {data.config.weights.CAPACITY_SHORTFALL}</small></div>{error && <p className="inline-error">{error}</p>}<button className="primary-button full-button" onClick={simulate} disabled={running}>{running ? 'Simulando…' : 'Executar simulação'}</button></SectionCard></div>
    {result && <SectionCard title="Resultado simulado" subtitle={result.warning} action={<Badge tone="medium">Cenário hipotético</Badge>}><PriorityTable rows={result.ranking.slice(0, 10)} onSelect={onSelect} weights={result.weights} /></SectionCard>}
  </>;
}
