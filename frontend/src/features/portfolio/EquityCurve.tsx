import { useQuery } from '@tanstack/react-query';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import api from '@/lib/api';
import { COLORS } from '@/lib/constants';
import { formatCurrency } from '@/lib/formatters';
import { ChartContainer } from '@/components';
import { useUIStore } from '@/lib/store';
import type { PortfolioSnapshot } from '@/types/portfolio';

const PERIOD_MAP: Record<string, string> = {
  '1D': '1d',
  '7D': '7d',
  '30D': '30d',
  '90D': '90d',
  'YTD': 'ytd',
  'ALL': 'all',
};

export function EquityCurve() {
  const period = useUIStore((s) => s.equityCurvePeriod);
  const setPeriod = useUIStore((s) => s.setEquityCurvePeriod);

  const { data, isLoading } = useQuery<PortfolioSnapshot[]>({
    queryKey: ['portfolio', 'equity-curve', period],
    queryFn: () =>
      api.get('/portfolio/equity-curve', { params: { period } }).then((r) => r.data),
    staleTime: 60_000,
    refetchInterval: 300_000,
  });

  const chartData = (data ?? []).map((s) => ({
    ts: new Date(s.ts).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    equity: s.equity,
  }));

  const handlePeriodChange = (p: string) => {
    const mapped = PERIOD_MAP[p];
    if (mapped) setPeriod(mapped as '1d' | '7d' | '30d' | '90d' | 'ytd' | 'all');
  };

  const defaultPeriod = Object.entries(PERIOD_MAP).find(([, v]) => v === period)?.[0] ?? '30D';

  return (
    <ChartContainer
      title="Equity Curve"
      loading={isLoading}
      empty={chartData.length === 0}
      onPeriodChange={handlePeriodChange}
      defaultPeriod={defaultPeriod}
    >
      <ResponsiveContainer width="100%" height={300}>
        <AreaChart data={chartData} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
          <defs>
            <linearGradient id="portfolioEquityGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={COLORS.success} stopOpacity={0.3} />
              <stop offset="95%" stopColor={COLORS.success} stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis
            dataKey="ts"
            axisLine={false}
            tickLine={false}
            tick={{ fill: COLORS.textTertiary, fontSize: 12 }}
          />
          <YAxis
            axisLine={false}
            tickLine={false}
            tick={{ fill: COLORS.textTertiary, fontSize: 12 }}
            tickFormatter={(v: number) => formatCurrency(v)}
            width={80}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: COLORS.surface,
              border: `1px solid ${COLORS.border}`,
              borderRadius: 8,
              color: COLORS.textPrimary,
              fontSize: 13,
            }}
            formatter={(v: number) => [formatCurrency(v), 'Equity']}
          />
          <Area
            type="monotone"
            dataKey="equity"
            stroke={COLORS.success}
            strokeWidth={2}
            fill="url(#portfolioEquityGradient)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </ChartContainer>
  );
}
