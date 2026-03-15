const STATUS_COLORS: Record<string, string> = {
  enabled: 'bg-success/20 text-success',
  active: 'bg-success/20 text-success',
  running: 'bg-success/20 text-success',
  open: 'bg-success/20 text-success',
  approved: 'bg-success/20 text-success',
  filled: 'bg-success/20 text-success',
  paid: 'bg-success/20 text-success',
  healthy: 'bg-success/20 text-success',
  pending: 'bg-warning/20 text-warning',
  draft: 'bg-warning/20 text-warning',
  paused: 'bg-warning/20 text-warning',
  acknowledged: 'bg-warning/20 text-warning',
  degraded: 'bg-warning/20 text-warning',
  disabled: 'bg-text-tertiary/20 text-text-tertiary',
  closed: 'bg-text-tertiary/20 text-text-tertiary',
  cancelled: 'bg-text-tertiary/20 text-text-tertiary',
  resolved: 'bg-text-tertiary/20 text-text-tertiary',
  stopped: 'bg-text-tertiary/20 text-text-tertiary',
  rejected: 'bg-error/20 text-error',
  error: 'bg-error/20 text-error',
  failed: 'bg-error/20 text-error',
  critical: 'bg-error/20 text-error',
  unhealthy: 'bg-error/20 text-error',
};

export function StatusPill({ status }: { status: string }) {
  const colorClass = STATUS_COLORS[status.toLowerCase()] || 'bg-text-tertiary/20 text-text-tertiary';
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-sm font-medium ${colorClass}`}>
      {status}
    </span>
  );
}
