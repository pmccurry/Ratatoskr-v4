import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import api from '@/lib/api';
import { formatCurrency, formatPercent } from '@/lib/formatters';
import { LoadingState } from '@/components';
import type { RiskConfig } from '@/types/risk';

interface ConfigRow {
  label: string;
  value: string;
}

export function RiskConfigSummary() {
  const { data, isLoading } = useQuery<RiskConfig>({
    queryKey: ['risk', 'config'],
    queryFn: () => api.get('/risk/config').then((r) => r.data),
    staleTime: 60_000,
  });

  if (isLoading) {
    return (
      <div className="bg-surface rounded-lg border border-border p-4">
        <LoadingState rows={8} />
      </div>
    );
  }

  if (!data) return null;

  const rows: ConfigRow[] = [
    { label: 'Max Position Size', value: formatPercent(data.maxPositionSizePercent) },
    { label: 'Max Symbol Exposure', value: formatPercent(data.maxSymbolExposurePercent) },
    { label: 'Max Strategy Exposure', value: formatPercent(data.maxStrategyExposurePercent) },
    { label: 'Max Total Exposure', value: formatPercent(data.maxTotalExposurePercent) },
    { label: 'Max Drawdown', value: formatPercent(data.maxDrawdownPercent) },
    { label: 'Catastrophic Drawdown', value: formatPercent(data.maxDrawdownCatastrophicPercent) },
    { label: 'Max Daily Loss', value: formatPercent(data.maxDailyLossPercent) },
    { label: 'Min Position Value', value: formatCurrency(data.minPositionValue) },
  ];

  return (
    <div className="bg-surface rounded-lg border border-border p-4">
      <h3 className="text-sm font-medium text-text-primary mb-4">Risk Configuration</h3>
      <div className="space-y-2">
        {rows.map((row) => (
          <div key={row.label} className="flex items-center justify-between text-sm">
            <span className="text-text-secondary">{row.label}</span>
            <span className="font-mono text-text-primary">{row.value}</span>
          </div>
        ))}
      </div>
      <div className="mt-4 pt-3 border-t border-border">
        <Link
          to="/settings/risk"
          className="text-sm text-accent hover:text-accent-hover transition-colors"
        >
          Edit in Settings &rarr;
        </Link>
      </div>
    </div>
  );
}
