import { api } from '../api';
import { useApiResource } from '../hooks/useApiResource';
import { DirectChannelsRevenue, OverviewKpis, RevenueByFamily, TopSkusByRevenue } from '../components/OverviewPanel';
import { DecisionsToday } from '../components/DecisionsToday';
import { JourneyStrip } from '../components/JourneyStrip';
import { ProjectedStockChart } from '../components/ProjectedStockChart';
import { RegionMap } from '../components/RegionMap';
import { PageIntro } from '../components';
import type { PageProps } from './shared';

/**
 * Início como painel: o caminho em cinco passos e os indicadores no topo, os gráficos e as decisões de hoje numa grade de três colunas.
 * Cada bloco carrega e falha por si; o faturamento previsto e as regiões são lidos uma vez e repartidos entre os blocos que os usam.
 */
export default function OverviewPage({ data, refreshToken }: PageProps<'overview'> & { refreshToken: number }) {
  const { overview } = data;
  const revenue = useApiResource(api.revenueForecast, refreshToken);
  const allocation = useApiResource(api.allocationRegions, refreshToken);
  return <div className="decision-journey">
    <PageIntro title="O que olho primeiro?" description="Cinco passos, do que arde agora até o quanto confiar. Cada um abre a tela completa." />
    <JourneyStrip overview={overview} allocation={allocation} refreshToken={refreshToken} />
    <OverviewKpis overview={overview} revenue={revenue} refreshToken={refreshToken} />
    {/* Mosaico de três colunas: falta de estoque (larga) e regiões; SKUs e faturamento por família (larga); decisões (larga) e canais. */}
    <div className="home-mosaic">
      <ProjectedStockChart summary={overview.projected_stock ?? null} />
      <RegionMap allocation={allocation} />
      <TopSkusByRevenue revenue={revenue} />
      <RevenueByFamily revenue={revenue} />
      <DecisionsToday data={overview.decisions_today} />
      <DirectChannelsRevenue refreshToken={refreshToken} />
    </div>
  </div>;
}
