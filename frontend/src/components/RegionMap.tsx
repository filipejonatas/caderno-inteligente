import type { CSSProperties } from 'react';
import { Link } from 'react-router-dom';
import { SectionCard, Tooltip } from '../components';
import type { AllocationRegion, AllocationRegions } from '../types-allocation';
import { displayCurrency, displayNumber, displayUnits } from '../pages/shared';
import { BlockError, BlockLoading, compactCurrency } from './OverviewPanel';
import type { Resource } from './OverviewPanel';

/** Macrorregiões no desenho do Brasil: cada bloco ocupa o lugar aproximado da região. Região fora desta lista (ex.: "Nacional") vai para a linha abaixo do mapa. */
const TILES: Array<{ name: string; area: string }> = [
  { name: 'Norte', area: 'n' }, { name: 'Nordeste', area: 'ne' },
  { name: 'Centro-Oeste', area: 'co' }, { name: 'Sudeste', area: 'se' }, { name: 'Sul', area: 's' },
];

const amount = (region: AllocationRegion) => region.uncovered_value === null ? displayUnits(region.uncovered_units) : compactCurrency(region.uncovered_value);

/**
 * Pedidos confirmados sem cobertura por região, em mapa de blocos. A cor mais forte marca mais valor sem cobertura
 * (sem preço em alguma região, a escala usa as unidades). Região sem pedidos sem cobertura fica tracejada: ausência não é zero.
 */
export function RegionMap({ allocation }: { allocation: Resource<AllocationRegions> }) {
  const { data, error, loading, refresh } = allocation;
  const title = 'Pedidos sem cobertura por região';
  if (!data && loading) return <BlockLoading title={title} />;
  if (!data) return <BlockError title={title} error={error} retry={refresh} />;

  const byName = new Map(data.regions.map((region) => [region.region, region]));
  const useValue = data.regions.length > 0 && data.regions.every((region) => region.uncovered_value !== null);
  const measure = (region: AllocationRegion) => useValue ? region.uncovered_value ?? 0 : region.uncovered_units;
  const peak = Math.max(1, ...data.regions.map(measure));
  const others = data.regions.filter((region) => !TILES.some((tile) => tile.name === region.region));
  const totals = data.totals;
  const subtitle = totals.orders > 0
    ? `${totals.uncovered_value === null ? displayUnits(totals.uncovered_units) : displayCurrency(totals.uncovered_value)} em ${displayNumber(totals.orders)} pedidos confirmados.`
    : 'Nenhum pedido confirmado sem cobertura.';
  const tag = <Tooltip label="Natureza dos números">{data.limitations.join(' ')}</Tooltip>;

  return <SectionCard className="region-card" title={title} subtitle={subtitle} action={tag}>
    <ul className="region-map" aria-label="Pedidos sem cobertura por macrorregião">
      {TILES.map((tile) => {
        const region = byName.get(tile.name);
        if (!region) return <li key={tile.name} className="region-tile region-empty" style={{ gridArea: tile.area }}><strong>{tile.name}</strong><small>Sem pedidos</small></li>;
        return <li key={tile.name} className="region-tile" style={{ gridArea: tile.area, '--heat': measure(region) / peak } as CSSProperties}>
          <strong>{tile.name}</strong>
          <span className="region-value">{amount(region)}</span>
          <small>{region.orders} {region.orders === 1 ? 'pedido' : 'pedidos'} · {region.skus.length} {region.skus.length === 1 ? 'SKU' : 'SKUs'}</small>
        </li>;
      })}
      <li className="region-legend" aria-hidden="true"><span className="region-scale" />Mais escuro, mais {useValue ? 'valor' : 'unidades'} sem cobertura</li>
    </ul>
    {others.map((region) => <p key={region.region} className="fact-line"><strong>{region.region}:</strong> {amount(region)} em {region.orders} {region.orders === 1 ? 'pedido' : 'pedidos'}, sem região definida no mapa.</p>)}
    <Link className="secondary-button" to="/parceiros">Ver o detalhe por região</Link>
  </SectionCard>;
}
