import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import api from '@/lib/api';
import { REFRESH, STALE } from '@/lib/constants';
import { formatCurrency, formatPercent } from '@/lib/formatters';
import { CardGrid, StatCard } from '@/components';
import type { PortfolioSummary } from '@/types/portfolio';
import type { RiskConfig } from '@/types/risk';

export function StatCards() {
  const { data: summary, isLoading, isError } = useQuery<PortfolioSummary>({
    queryKey: ['portfolio', 'summary'],
    queryFn: () => api.get('/portfolio/summary').then((r) => r.data),
    staleTime: STALE.portfolioSummary,
    refetchInterval: REFRESH.portfolioSummary,
  });

  const { data: riskConfig } = useQuery<RiskConfig>({
    queryKey: ['risk', 'config'],
    queryFn: () => api.get('/risk/config').then((r) => r.data),
    staleTime: STALE.riskOverview,
  });

  if (isError) {
    return (
      <CardGrid>
        {Array.from({ length: 4 }).map((_, i) => (
          <StatCard key={i} label="—" value="Error loading data" loading={false} />
        ))}
      </CardGrid>
    );
  }

  const drawdownLimit = riskConfig?.maxDrawdownPercent ?? 10;

  return (
    <CardGrid>
      <Link to="/portfolio" className="block">
        <StatCard
          label="Total Equity"
          value={summary ? formatCurrency(summary.equity) : '—'}
          subtitle={summary ? formatPercent(summary.totalReturnPercent) + ' return' : undefined}
          loading={isLoading}
        />
      </Link>
      <StatCard
        label="Today's PnL"
        value={summary ? formatCurrency((summary.unrealizedPnl ?? 0) + (summary.realizedPnlTotal ?? 0)) : '—'}
        trend={summary ? ((summary.unrealizedPnl ?? 0) >= 0 ? 'up' : 'down') : undefined}
        trendValue={summary ? formatPercent(summary.totalReturnPercent) : undefined}
        loading={isLoading}
      />
      <Link to="/portfolio" className="block">
        <StatCard
          label="Open Positions"
          value={summary?.openPositionsCount ?? '—'}
          loading={isLoading}
        />
      </Link>
      <Link to="/risk" className="block">
        <StatCard
          label="Drawdown"
          value={summary ? formatPercent(summary.drawdownPercent) : '—'}
          progress={summary ? {
            value: Math.abs(summary.drawdownPercent),
            max: drawdownLimit,
            threshold: drawdownLimit * 0.8,
          } : undefined}
          loading={isLoading}
        />
      </Link>
    </CardGrid>
  );
}
