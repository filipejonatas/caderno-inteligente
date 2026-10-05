import { useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Icon, PageIntro, PriorityTable, SectionCard } from '../components';
import type { PageProps } from './shared';

export default function PrioritiesPage({ data, onSelect }: PageProps) {
  const [params, setParams] = useSearchParams();
  const search = params.get('busca') ?? '';
  const family = params.get('familia') ?? '';
  const confidence = params.get('confianca') ?? '';
  const update = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value); else next.delete(key);
    setParams(next, { replace: true });
  };
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
      <label className="search-field"><span className="sr-only">Buscar</span><Icon name="search" /><input value={search} onChange={(event) => update('busca', event.target.value)} placeholder="Buscar SKU ou produto" /></label>
      <label><span>Família</span><select value={family} onChange={(event) => update('familia', event.target.value)}><option value="">Todas</option>{families.map((item) => <option key={item}>{item}</option>)}</select></label>
      <label><span>Confiança</span><select value={confidence} onChange={(event) => update('confianca', event.target.value)}><option value="">Todas</option><option value="baixa">Baixa</option><option value="média">Média</option></select></label>
      <div className="filter-count"><strong>{filtered.length}</strong><span>resultados</span></div>
    </div>
    <SectionCard title="Ranking oficial" subtitle="Ordenado pela soma transparente dos pesos de cada sinal."><PriorityTable rows={filtered} onSelect={onSelect} /></SectionCard>
  </>;
}
