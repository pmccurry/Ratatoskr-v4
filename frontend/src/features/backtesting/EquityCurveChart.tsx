import {
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';
import { COLORS } from '@/lib/constants';
import { formatCurrency, formatPercent } from '@/lib/formatters';
import { ChartContainer } from '@/components';

export interface EquityPoint {
  barTime: string;
  equity: number;
  drawdownPct: number;
  cash: number;
  openPositions: number;
  unrealizedPnl: number;
  barIndex: number;
}

interface EquityCurveChartProps {
  data: EquityPoint[];
  initialCapital: number;
  loading?: boolean;
}

function formatDateShort(iso: string): string {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export function EquityCurveChart({ data, initialCapital, loading }: EquityCurveChartProps) {
  const chartData = data.map((p) => ({
    ...p,
    dateLabel: formatDateShort(p.barTime),
    drawdownDisplay: Math.abs(p.drawdownPct),
  }));

  // Check if all equity values are identical (flat line / 0-trade backtest)
  const allSameEquity = chartData.length > 0 && chartData.every((p) => p.equity === chartData[0].equity);

  if (chartData.length > 0 && allSameEquity) {
    return (
      <ChartContainer title="Equity Curve" loading={loading} empty={false}>
        <div className="flex items-center justify-center h-[350px] text-text-secondary text-sm">
          No equity change during backtest period. Starting capital: {formatCurrency(initialCapital)}
        </div>
      </ChartContainer>
    );
  }

  return (
    <ChartContainer title="Equity Curve" loading={loading} empty={chartData.length === 0}>
      <ResponsiveContainer width="100%" height={350}>
        <ComposedChart data={chartData} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <defs>
            <linearGradient id="backtestDrawdownGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="rgba(255,80,80,0.15)" stopOpacity={1} />
              <stop offset="95%" stopColor="rgba(255,80,80,0.15)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke={COLORS.border} />
          <XAxis
            dataKey="dateLabel"
            axisLine={false}
            tickLine={false}
            tick={{ fill: COLORS.textTertiary, fontSize: 12 }}
          />
          <YAxis
            yAxisId="equity"
            axisLine={false}
            tickLine={false}
            tick={{ fill: COLORS.textTertiary, fontSize: 12 }}
            tickFormatter={(v: number) => formatCurrency(v)}
            width={90}
            domain={[(dataMin: number) => Math.floor(dataMin * 0.98), (dataMax: number) => Math.ceil(dataMax * 1.02)]}
          />
          <YAxis
            yAxisId="drawdown"
            orientation="right"
            axisLine={false}
            tickLine={false}
            tick={{ fill: COLORS.textTertiary, fontSize: 12 }}
            tickFormatter={(v: number) => `${v.toFixed(1)}%`}
            width={60}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: COLORS.surface,
              border: `1px solid ${COLORS.border}`,
              borderRadius: 8,
              color: COLORS.textPrimary,
              fontSize: 13,
            }}
            formatter={(value: number, name: string) => {
              if (name === 'equity') return [formatCurrency(value), 'Equity'];
              if (name === 'drawdownDisplay') return [formatPercent(-value), 'Drawdown'];
              return [value, name];
            }}
            labelFormatter={(label: string) => label}
          />
          <ReferenceLine
            yAxisId="equity"
            y={initialCapital}
            stroke={COLORS.textTertiary}
            strokeDasharray="4 4"
          />
          <Line
            yAxisId="equity"
            type="monotone"
            dataKey="equity"
            stroke={COLORS.info}
            strokeWidth={2}
            dot={false}
            name="equity"
          />
          <Area
            yAxisId="drawdown"
            type="monotone"
            dataKey="drawdownDisplay"
            fill="rgba(255,80,80,0.15)"
            stroke="rgba(255,80,80,0.4)"
            name="drawdownDisplay"
          />
        </ComposedChart>
      </ResponsiveContainer>
    </ChartContainer>
  );
}
