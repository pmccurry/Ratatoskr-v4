interface ProgressBarProps {
  value: number;
  max: number;
  threshold?: number;
  label?: string;
  className?: string;
}

export function ProgressBar({ value, max, threshold, label, className = '' }: ProgressBarProps) {
  const pct = Math.min((value / max) * 100, 100);
  const barColor = threshold && value > threshold ? 'bg-warning' : 'bg-accent';

  return (
    <div className={className}>
      {label && <p className="text-sm text-text-secondary mb-1">{label}</p>}
      <div className="h-2 bg-border rounded-full overflow-hidden relative">
        <div className={`h-full rounded-full transition-all ${barColor}`} style={{ width: `${pct}%` }} />
        {threshold !== undefined && (
          <div
            className="absolute top-0 h-full w-0.5 bg-warning"
            style={{ left: `${(threshold / max) * 100}%` }}
          />
        )}
      </div>
    </div>
  );
}
