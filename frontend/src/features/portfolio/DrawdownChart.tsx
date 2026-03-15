import { useQuery } from '@tanstack/react-query';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import api from '@/lib/api';
import { COLORS } from '@/lib/constants';
import { useUIStore } from '@/lib/store';
import type { PortfolioSnapshot } from '@/types/portfolio';
import type { RiskConfig } from '@/types/risk';

export function DrawdownChart() {
  const period = useUIStore((s) => s.equityCurvePeriod);

  const { data: snapshots } = useQuery<PortfolioSnapshot[]>({
    queryKey: ['portfolio', 'equity-curve', period],
    queryFn: () =>
      api.get('/portfolio/equity-curve', { params: { period } }).then((r) => r.data),
    staleTime: 60_000,
    refetchInterval: 300_000,
  });

  const { data: riskConfig } = useQuery<RiskConfig>({
    queryKey: ['risk', 'config'],
    queryFn: () => api.get('/risk/config').then((r) => r.data),
    staleTime: 60_000,
  });

  const chartData = (snapshots ?? []).map((s) => ({
    ts: new Date(s.ts).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    drawdown: s.drawdownPercent,
  }));

  const maxDrawdown = riskConfig?.maxDrawdownPercent;

  return (
    <div className="bg-surface rounded-lg border border-border p-4">
      <h3 className="text-sm font-medium text-text-primary mb-4">Drawdown</h3>
      {chartData.length === 0 ? (
        <div className="h-[180px] flex items-center justify-center text-text-tertiary text-sm">
          No data available
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={180}>
          <AreaChart data={chartData} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
            <defs>
              <linearGradient id="drawdownGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={COLORS.error} stopOpacity={0.3} />
                <stop offset="95%" stopColor={COLORS.error} stopOpacity={0} />
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
              tickFormatter={(v: number) => `${v}%`}
              width={50}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: COLORS.surface,
                border: `1px solid ${COLORS.border}`,
                borderRadius: 8,
                color: COLORS.textPrimary,
                fontSize: 13,
              }}
              formatter={(v: number) => [`${v.toFixed(2)}%`, 'Drawdown']}
            />
            {maxDrawdown !== undefined && (
              <ReferenceLine
                y={maxDrawdown}
                stroke={COLORS.warning}
                strokeDasharray="5 5"
              />
            )}
            <Area
              type="monotone"
              dataKey="drawdown"
              stroke={COLORS.error}
              strokeWidth={2}
              fill="url(#drawdownGradient)"
            />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
