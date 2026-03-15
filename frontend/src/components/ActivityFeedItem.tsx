import { formatTimeAgo } from '@/lib/formatters';

interface ActivityFeedItemProps {
  summary: string;
  ts: string;
  severity?: string;
}

export function ActivityFeedItem({ summary, ts, severity }: ActivityFeedItemProps) {
  const borderColor =
    severity === 'critical' || severity === 'error'
      ? 'border-l-error'
      : severity === 'warning'
        ? 'border-l-warning'
        : 'border-l-border';

  return (
    <div className={`flex items-start gap-3 py-2 px-3 border-l-2 ${borderColor} hover:bg-surface-hover transition-colors`}>
      <span className="text-sm text-text-primary flex-1 min-w-0 break-words">{summary}</span>
      <span className="text-sm text-text-tertiary whitespace-nowrap">{formatTimeAgo(ts)}</span>
    </div>
  );
}
