import { useState } from 'react';

const PERIODS = ['1D', '7D', '30D', '90D', 'YTD', 'ALL'] as const;

interface ChartContainerProps {
  title?: string;
  loading?: boolean;
  empty?: boolean;
  onPeriodChange?: (period: string) => void;
  defaultPeriod?: string;
  children: React.ReactNode;
}

export function ChartContainer({
  title,
  loading,
  empty,
  onPeriodChange,
  defaultPeriod = '30D',
  children,
}: ChartContainerProps) {
  const [period, setPeriod] = useState(defaultPeriod);

  const handlePeriod = (p: string) => {
    setPeriod(p);
    onPeriodChange?.(p);
  };

  return (
    <div className="bg-surface rounded-lg border border-border p-4">
      <div className="flex items-center justify-between mb-4">
        {title && <h3 className="text-sm font-medium text-text-primary">{title}</h3>}
        <div className="flex gap-1">
          {PERIODS.map((p) => (
            <button
              key={p}
              onClick={() => handlePeriod(p)}
              className={`px-2 py-1 text-sm rounded transition-colors ${
                period === p
                  ? 'bg-accent text-white'
                  : 'text-text-secondary hover:text-text-primary hover:bg-surface-hover'
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>
      {loading ? (
        <div className="h-64 bg-border/30 rounded animate-pulse" />
      ) : empty ? (
        <div className="h-64 flex items-center justify-center text-text-tertiary text-sm">
          No data available
        </div>
      ) : (
        children
      )}
    </div>
  );
}
