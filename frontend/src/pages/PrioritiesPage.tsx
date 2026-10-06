import { useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Icon, PageIntro, PriorityTable, SectionCard } from '../components';
import type { PageProps } from './shared';

export default function PrioritiesPage({ data, onSelect }: PageProps<'priorities' | 'config'>) {
  const [params, setParams] = useSearchParams();
  const [extra, setExtra] = useState(0);
  const search = params.get('busca') ?? '';
  const family = params.get('familia') ?? '';
  const confidence = params.get('confianca') ?? '';
  const update = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value); else next.delete(key);
    setParams(next, { replace: true });
    setExtra(0);
  };
  const families = useMemo(() => [...new Set(data.priorities.map((item) => item.family))].sort(), [data.priorities]);
  const filtered = useMemo(() => data.priorities.filter((item) => {
    const query = search.trim().toLocaleLowerCase('pt-BR');
    return (!query || item.sku.toLocaleLowerCase('pt-BR').includes(query) || item.product.toLocaleLowerCase('pt-BR').includes(query))
      && (!family || item.family === family)
      && (!confidence || item.confidence === confidence);
  }), [confidence, data.priorities, family, search]);

  const pageSize = (window.matchMedia('(max-width: 620px)').matches ? 10 : 25) + extra;
  const visible = filtered.slice(0, pageSize);
  return <>
    <PageIntro title="Em que ordem analisar os SKUs" description="Os pontos de atenção ordenam a análise. Abra um SKU para ver os motivos, os valores e a origem de cada evidência." />
    <div className="filter-bar" role="search" aria-label="Filtrar prioridades">
      <label className="search-field"><span>Buscar</span><Icon name="search" /><input value={search} onChange={(event) => update('busca', event.target.value)} placeholder="Buscar SKU ou produto" /></label>
      <label><span>Família</span><select value={family} onChange={(event) => update('familia', event.target.value)}><option value="">Todas</option>{families.map((item) => <option key={item}>{item}</option>)}</select></label>
      <label><span>Confiança</span><select value={confidence} onChange={(event) => update('confianca', event.target.value)}><option value="">Todas</option><option value="baixa">Baixa</option><option value="média">Média</option><option value="alta">Alta</option></select></label>
      <div className="filter-count"><strong>{filtered.length}</strong><span>de {data.priorities.length} SKUs</span></div>{params.size > 0 && <button className="secondary-button" onClick={() => setParams({}, { replace: true })}>Limpar filtros</button>}
    </div>
    <SectionCard title="Ranking oficial" subtitle="Ordenado pela soma dos pesos de cada sinal. O motivo principal é o sinal de maior peso."><PriorityTable rows={visible} onSelect={onSelect} weights={data.config.weights} />{filtered.length > visible.length && <div className="show-more"><button className="secondary-button" onClick={() => setExtra(value => value + 25)}>Ver mais ({filtered.length - visible.length} restantes)</button></div>}</SectionCard>
  </>;
}
