import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { BarChart, Bar, Cell, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import api from '@/lib/api';
import { SectionHeader, LoadingState, EmptyState, ErrorState } from '@/components';
import { formatCurrency } from '@/lib/formatters';
import { COLORS } from '@/lib/constants';
import type { RealizedPnlEntry } from '@/types/portfolio';

interface DayData {
  date: string;
  dayNum: number;
  pnl: number;
  trades: number;
}

interface BucketData {
  range: string;
  count: number;
  color: string;
}

function getDateString(dt: Date): string {
  return dt.toISOString().slice(0, 10);
}

function buildLast30Days(entries: RealizedPnlEntry[]): DayData[] {
  const byDate: Record<string, { pnl: number; trades: number }> = {};
  for (const e of entries) {
    const d = e.closedAt.slice(0, 10);
    if (!byDate[d]) byDate[d] = { pnl: 0, trades: 0 };
    byDate[d].pnl += e.netPnl;
    byDate[d].trades += 1;
  }

  const days: DayData[] = [];
  const now = new Date();
  for (let i = 29; i >= 0; i--) {
    const dt = new Date(now);
    dt.setDate(dt.getDate() - i);
    const key = getDateString(dt);
    const info = byDate[key];
    days.push({
      date: key,
      dayNum: dt.getDate(),
      pnl: info?.pnl ?? 0,
      trades: info?.trades ?? 0,
    });
  }
  return days;
}

function buildBuckets(entries: RealizedPnlEntry[]): BucketData[] {
  const ranges: { label: string; min: number; max: number; positive: boolean }[] = [
    { label: '< -500', min: -Infinity, max: -500, positive: false },
    { label: '-500 to -100', min: -500, max: -100, positive: false },
    { label: '-100 to 0', min: -100, max: 0, positive: false },
    { label: '0 to 100', min: 0, max: 100, positive: true },
    { label: '100 to 500', min: 100, max: 500, positive: true },
    { label: '> 500', min: 500, max: Infinity, positive: true },
  ];

  return ranges.map((r) => ({
    range: r.label,
    count: entries.filter((e) => e.netPnl >= r.min && e.netPnl < r.max).length,
    color: r.positive ? COLORS.success : COLORS.error,
  }));
}

export function PnlCalendar() {
  const [hoveredDay, setHoveredDay] = useState<string | null>(null);

  const { data: entries, isLoading, isError, refetch } = useQuery<RealizedPnlEntry[]>({
    queryKey: ['portfolio', 'pnl', 'realized'],
    queryFn: () => api.get('/portfolio/pnl/realized').then((r) => r.data),
    staleTime: 30_000,
    refetchInterval: 60_000,
  });

  const days = useMemo(() => buildLast30Days(entries ?? []), [entries]);
  const buckets = useMemo(() => buildBuckets(entries ?? []), [entries]);

  const maxAbsPnl = useMemo(
    () => Math.max(...days.map((d) => Math.abs(d.pnl)), 1),
    [days],
  );

  const hoveredData = hoveredDay ? days.find((d) => d.date === hoveredDay) : null;

  if (isLoading) return <LoadingState rows={6} />;
  if (isError) return <ErrorState message="Failed to load PnL data" onRetry={refetch} />;
  if (!entries || entries.length === 0) return <EmptyState message="No realized PnL data yet" />;

  return (
    <div>
      <SectionHeader title="PnL Calendar" />
      <div className="grid grid-cols-7 gap-1 mt-3">
        {days.map((day) => {
          const opacity = day.pnl === 0
            ? 0
            : 0.2 + (Math.abs(day.pnl) / maxAbsPnl) * 0.6;
          const baseColor = day.pnl > 0 ? COLORS.success : day.pnl < 0 ? COLORS.error : undefined;

          let bgColor: string | undefined;
          if (baseColor) {
            const r = parseInt(baseColor.slice(1, 3), 16);
            const g = parseInt(baseColor.slice(3, 5), 16);
            const b = parseInt(baseColor.slice(5, 7), 16);
            bgColor = `rgba(${r}, ${g}, ${b}, ${opacity})`;
          }

          return (
            <div
              key={day.date}
              className="w-full aspect-square rounded cursor-pointer flex items-center justify-center text-xs text-text-primary"
              style={{ backgroundColor: bgColor ?? 'var(--color-surface, #1a1d27)' }}
              onMouseEnter={() => setHoveredDay(day.date)}
              onMouseLeave={() => setHoveredDay(null)}
            >
              {day.dayNum}
            </div>
          );
        })}
      </div>

      {hoveredData && (
        <div className="bg-surface border border-border rounded p-3 mt-2 text-sm">
          <p className="text-text-primary">{hoveredData.date}</p>
          <p className={hoveredData.pnl >= 0 ? 'text-success' : 'text-error'}>
            PnL: {formatCurrency(hoveredData.pnl)}
          </p>
          <p className="text-text-secondary">Trades: {hoveredData.trades}</p>
        </div>
      )}

      <div className="mt-6">
        <SectionHeader title="Win/Loss Distribution" />
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={buckets} margin={{ top: 8, right: 4, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={COLORS.border} />
            <XAxis
              dataKey="range"
              axisLine={false}
              tickLine={false}
              tick={{ fill: COLORS.textTertiary, fontSize: 11 }}
            />
            <YAxis
              axisLine={false}
              tickLine={false}
              tick={{ fill: COLORS.textTertiary, fontSize: 12 }}
              allowDecimals={false}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: COLORS.surface,
                border: `1px solid ${COLORS.border}`,
                borderRadius: 8,
                color: COLORS.textPrimary,
                fontSize: 13,
              }}
            />
            <Bar
              dataKey="count"
              name="Trades"
              radius={[4, 4, 0, 0]}
            >
              {buckets.map((entry, index) => (
                <Cell key={index} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
