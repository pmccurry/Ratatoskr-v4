import { ArrowUp, ArrowDown } from 'lucide-react';

interface StatCardProps {
  label: string;
  value: string | number;
  subtitle?: string;
  trend?: 'up' | 'down';
  trendValue?: string;
  progress?: { value: number; max: number; threshold?: number };
  loading?: boolean;
}

export function StatCard({ label, value, subtitle, trend, trendValue, progress, loading }: StatCardProps) {
  if (loading) {
    return (
      <div className="bg-surface rounded-lg border border-border p-4 animate-pulse">
        <div className="h-3 bg-border rounded w-20 mb-3" />
        <div className="h-6 bg-border rounded w-28 mb-2" />
        <div className="h-3 bg-border rounded w-16" />
      </div>
    );
  }

  return (
    <div className="bg-surface rounded-lg border border-border p-4">
      <p className="text-sm text-text-secondary mb-1">{label}</p>
      <div className="flex items-baseline gap-2">
        <span className="text-xl font-semibold font-mono text-text-primary">{value}</span>
        {trend && (
          <span className={`flex items-center text-sm ${trend === 'up' ? 'text-success' : 'text-error'}`}>
            {trend === 'up' ? <ArrowUp size={14} /> : <ArrowDown size={14} />}
            {trendValue}
          </span>
        )}
      </div>
      {subtitle && <p className="text-sm text-text-tertiary mt-1">{subtitle}</p>}
      {progress && (
        <div className="mt-3">
          <div className="h-1.5 bg-border rounded-full overflow-hidden relative">
            <div
              className="h-full bg-accent rounded-full transition-all"
              style={{ width: `${Math.min((progress.value / progress.max) * 100, 100)}%` }}
            />
            {progress.threshold !== undefined && (
              <div
                className="absolute top-0 h-full w-0.5 bg-warning"
                style={{ left: `${(progress.threshold / progress.max) * 100}%` }}
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
}
