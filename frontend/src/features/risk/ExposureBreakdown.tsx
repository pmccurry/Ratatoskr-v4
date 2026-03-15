import { useQuery } from '@tanstack/react-query';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import api from '@/lib/api';
import { COLORS, STALE, REFRESH } from '@/lib/constants';
import { SectionHeader, EmptyState } from '@/components';
import type { RiskOverview } from '@/types/risk';

export function ExposureBreakdown() {
  const { data } = useQuery<RiskOverview>({
    queryKey: ['risk', 'overview'],
    queryFn: () => api.get('/risk/overview').then((r) => r.data),
    staleTime: STALE.riskOverview,
    refetchInterval: REFRESH.riskOverview,
  });

  const symbolData = Object.entries(data?.symbolExposure ?? {}).map(([name, value]) => ({
    name,
    exposure: value,
  }));

  const strategyData = Object.entries(data?.strategyExposure ?? {}).map(([name, value]) => ({
    name,
    exposure: value,
  }));

  return (
    <div className="grid grid-cols-2 gap-6">
      <div className="bg-surface rounded-lg border border-border p-4">
        <SectionHeader title="Per-Symbol Exposure" />
        {symbolData.length === 0 ? (
          <EmptyState message="No symbol exposure data" />
        ) : (
          <ResponsiveContainer width="100%" height={Math.max(symbolData.length * 36, 120)}>
            <BarChart data={symbolData} layout="vertical" margin={{ top: 0, right: 16, bottom: 0, left: 0 }}>
              <XAxis
                type="number"
                axisLine={false}
                tickLine={false}
                tick={{ fill: COLORS.textTertiary, fontSize: 12 }}
                tickFormatter={(v: number) => `${v}%`}
              />
              <YAxis
                type="category"
                dataKey="name"
                axisLine={false}
                tickLine={false}
                tick={{ fill: COLORS.textSecondary, fontSize: 12 }}
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
                formatter={(v: unknown) => [`${typeof v === 'number' ? v.toFixed(2) : '—'}%`, 'Exposure']}
              />
              <Bar dataKey="exposure" fill={COLORS.accent} radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      <div className="bg-surface rounded-lg border border-border p-4">
        <SectionHeader title="Per-Strategy Exposure" />
        {strategyData.length === 0 ? (
          <EmptyState message="No strategy exposure data" />
        ) : (
          <ResponsiveContainer width="100%" height={Math.max(strategyData.length * 36, 120)}>
            <BarChart data={strategyData} layout="vertical" margin={{ top: 0, right: 16, bottom: 0, left: 0 }}>
              <XAxis
                type="number"
                axisLine={false}
                tickLine={false}
                tick={{ fill: COLORS.textTertiary, fontSize: 12 }}
                tickFormatter={(v: number) => `${v}%`}
              />
              <YAxis
                type="category"
                dataKey="name"
                axisLine={false}
                tickLine={false}
                tick={{ fill: COLORS.textSecondary, fontSize: 12 }}
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
                formatter={(v: unknown) => [`${typeof v === 'number' ? v.toFixed(2) : '—'}%`, 'Exposure']}
              />
              <Bar dataKey="exposure" fill={COLORS.info} radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
