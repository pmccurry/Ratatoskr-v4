import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import { STALE, REFRESH } from '@/lib/constants';
import { formatCurrency, formatPercent } from '@/lib/formatters';
import { CardGrid, StatCard } from '@/components';
import type { RiskOverview } from '@/types/risk';

export function RiskStatCards() {
  const { data, isLoading } = useQuery<RiskOverview>({
    queryKey: ['risk', 'overview'],
    queryFn: () => api.get('/risk/overview').then((r) => r.data),
    staleTime: STALE.riskOverview,
    refetchInterval: REFRESH.riskOverview,
  });

  const approved = data?.recentDecisions?.filter((d) => d.status === 'approved').length ?? 0;
  const rejected = data?.recentDecisions?.filter((d) => d.status === 'rejected').length ?? 0;

  return (
    <CardGrid>
      <StatCard
        label="Drawdown"
        value={data ? formatPercent(data.drawdown?.current) : '—'}
        progress={
          data?.drawdown
            ? {
                value: Math.abs(data.drawdown.current ?? 0),
                max: data.drawdown.limit ?? 10,
                threshold: (data.drawdown.limit ?? 10) * 0.8,
              }
            : undefined
        }
        loading={isLoading}
      />
      <StatCard
        label="Daily Loss"
        value={data ? formatCurrency(data.dailyLoss?.current) : '—'}
        progress={
          data?.dailyLoss
            ? {
                value: Math.abs(data.dailyLoss.current ?? 0),
                max: data.dailyLoss.limit ?? 1000,
              }
            : undefined
        }
        loading={isLoading}
      />
      <StatCard
        label="Total Exposure"
        value={data ? formatPercent(data.totalExposure?.current) : '—'}
        progress={
          data?.totalExposure
            ? {
                value: Math.abs(data.totalExposure.current ?? 0),
                max: data.totalExposure.limit ?? 80,
              }
            : undefined
        }
        loading={isLoading}
      />
      <StatCard
        label="Decisions Today"
        value={data?.recentDecisions?.length ?? '—'}
        subtitle={data ? `${approved} approved / ${rejected} rejected` : undefined}
        loading={isLoading}
      />
    </CardGrid>
  );
}
