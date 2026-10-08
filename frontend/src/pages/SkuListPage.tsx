import { useState } from 'react';
import { Link, useLocation, useSearchParams } from 'react-router-dom';
import { api } from '../api';
import { useApiResource } from '../hooks/useApiResource';
import { usePageLoadStatus } from '../hooks/usePageLoadStatus';
import { EmptyState, ErrorState, Icon, LoadingState, PageIntro, Pagination, SectionCard } from '../components';

const PAGE_SIZE = 10;

/** Lista completa de SKUs, com busca e família; cada linha leva à página do SKU (/skus/:sku). */
export default function SkuListPage({ refreshToken }: { refreshToken: number }) {
  const { data, error, loading, loadedAt, refresh } = useApiResource(api.forecasts, refreshToken);
  usePageLoadStatus(loading, data ? '' : error, loadedAt);
  const location = useLocation();
  const [params, setParams] = useSearchParams();
  const [page, setPage] = useState(1);
  const search = params.get('busca') ?? '';
  const family = params.get('familia') ?? '';

  const update = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value); else next.delete(key);
    setParams(next, { replace: true });
    setPage(1);
  };

  if (!data) return error ? <ErrorState message={error} onRetry={() => void refresh()} /> : <LoadingState />;
  const families = [...new Set(data.map((item) => item.family))].sort((a, b) => a.localeCompare(b, 'pt-BR'));
  const query = search.trim().toLocaleLowerCase('pt-BR');
  const filtered = data
    .filter((item) => (!query || item.sku.toLocaleLowerCase('pt-BR').includes(query) || item.product.toLocaleLowerCase('pt-BR').includes(query)) && (!family || item.family === family))
    .sort((a, b) => a.sku.localeCompare(b.sku, 'pt-BR'));
  const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const current = Math.min(page, pages);
  const visible = filtered.slice((current - 1) * PAGE_SIZE, current * PAGE_SIZE);
  const from = `${location.pathname}${location.search}`;

  return <div className="sku-list-page">
    <PageIntro title="Todos os SKUs" description={`${data.length} SKUs no cadastro. Abra um SKU para ver resumo, evidências, parceiros e impacto financeiro.`} />
    <div className="filter-bar" role="search" aria-label="Filtrar SKUs">
      <label className="search-field"><span>Buscar</span><Icon name="search" /><input value={search} onChange={(event) => update('busca', event.target.value)} placeholder="SKU ou produto" /></label>
      <label><span>Família</span><select value={family} onChange={(event) => update('familia', event.target.value)}><option value="">Todas</option>{families.map((item) => <option key={item}>{item}</option>)}</select></label>
      <div className="filter-count" role="status"><strong>{filtered.length}</strong><span>de {data.length} SKUs</span></div>
      {params.size > 0 && <button className="secondary-button" onClick={() => { setParams({}, { replace: true }); setPage(1); }}>Limpar filtros</button>}
    </div>
    <SectionCard title="SKUs">
      {!visible.length ? <EmptyState title="Nenhum SKU encontrado" description="Ajuste a busca ou a família." />
        : <div className="table-shell" tabIndex={0} role="region" aria-label="Lista de SKUs; role horizontalmente para ver todas as colunas"><table className="data-table responsive-table"><thead><tr><th>SKU / Produto</th><th>Família</th><th>Posição na fila</th><th>Ação sugerida</th></tr></thead><tbody>{visible.map((item) => <tr key={item.sku}>
          <td data-label="SKU"><Link className="link-button" to={`/skus/${encodeURIComponent(item.sku)}`} state={{ from }} aria-label={`Abrir ${item.sku}`}><strong>{item.sku}</strong></Link><small>{item.product}</small></td>
          <td data-label="Família">{item.family}</td>
          <td data-label="Posição na fila">{item.priority ?? <span className="queue-none">Fora da fila</span>}</td>
          <td data-label="Ação sugerida">{item.operational_recommendation.action_label}</td>
        </tr>)}</tbody></table></div>}
      <Pagination page={current} pages={pages} onChange={setPage} label="Páginas da lista de SKUs" />
    </SectionCard>
  </div>;
}
