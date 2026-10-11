import { api } from '../api';
import { useApiResource } from '../hooks/useApiResource';
import { DirectChannelsRevenue, OverviewKpis, RevenueByFamily, TopSkusByRevenue } from '../components/OverviewPanel';
import { JourneyStrip } from '../components/JourneyStrip';
import { DecisionsToday } from '../components/DecisionsToday';
import { ProjectedStockChart } from '../components/ProjectedStockChart';
import { PageIntro } from '../components';
import type { PageProps } from './shared';

/**
 * Início como painel: o caminho em cinco passos no topo, depois os indicadores e os gráficos. O primeiro da fila fica no Planejamento (/fila).
 * Cada bloco carrega e falha por si; o faturamento previsto é lido uma vez e repartido entre cartões, pizza e ranking.
 */
export default function OverviewPage({ data, refreshToken }: PageProps<'overview'> & { refreshToken: number }) {
  const { overview } = data;
  const revenue = useApiResource(api.revenueForecast, refreshToken);
  return <div className="decision-journey">
    <PageIntro title="O que olho primeiro?" description="Cinco passos, do que arde agora até o quanto confiar. Cada um abre a tela completa." />
    <JourneyStrip overview={overview} refreshToken={refreshToken} />
    <OverviewKpis overview={overview} revenue={revenue} refreshToken={refreshToken} />
    <DecisionsToday data={overview.decisions_today} />
    {/* Mosaico 2 × 2: falta de estoque e faturamento por família em cima; SKUs e canais embaixo. */}
    <div className="home-mosaic">
      <ProjectedStockChart summary={overview.projected_stock ?? null} />
      <RevenueByFamily revenue={revenue} />
      <TopSkusByRevenue revenue={revenue} />
      <DirectChannelsRevenue refreshToken={refreshToken} />
    </div>
  </div>;
}
