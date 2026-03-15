import { useRef, useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import { REFRESH, STALE } from '@/lib/constants';
import { SectionHeader, ActivityFeedItem, LoadingState, EmptyState, ErrorState } from '@/components';
import type { AuditEvent } from '@/types/observability';

const SEVERITY_OPTIONS = ['all', 'critical', 'error', 'warning', 'info', 'debug'] as const;
const CATEGORY_OPTIONS = ['all', 'strategy', 'signal', 'risk', 'paper_trading', 'portfolio', 'system'] as const;
const CATEGORY_LABELS: Record<string, string> = {
  all: 'all',
  strategy: 'strategy',
  signal: 'signal',
  risk: 'risk',
  paper_trading: 'trading',
  portfolio: 'portfolio',
  system: 'system',
};

export function ActivityFeed() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [hovered, setHovered] = useState(false);
  const [severityFilter, setSeverityFilter] = useState('all');
  const [categoryFilter, setCategoryFilter] = useState('all');

  const { data: events, isLoading, isError, refetch } = useQuery<AuditEvent[]>({
    queryKey: ['observability', 'events', 'recent'],
    queryFn: () => api.get('/observability/events/recent', { params: { limit: 20 } }).then((r) => r.data),
    staleTime: STALE.systemHealth,
    refetchInterval: REFRESH.activityFeed,
  });

  // Auto-scroll to bottom when new events arrive (unless hovered)
  useEffect(() => {
    if (!hovered && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [events, hovered]);

  const filtered = (events ?? []).filter((e) => {
    if (severityFilter !== 'all' && e.severity !== severityFilter) return false;
    if (categoryFilter !== 'all' && e.category !== categoryFilter) return false;
    return true;
  });

  const FilterButton = ({ value, current, onClick, label }: { value: string; current: string; onClick: (v: string) => void; label?: string }) => (
    <button
      onClick={() => onClick(value)}
      className={`px-2 py-0.5 text-xs rounded transition-colors ${
        current === value
          ? 'bg-accent text-white'
          : 'text-text-tertiary hover:text-text-secondary hover:bg-surface-hover'
      }`}
    >
      {label ?? value}
    </button>
  );

  return (
    <div className="bg-surface rounded-lg border border-border p-4">
      <div className="flex items-center justify-between mb-3">
        <SectionHeader title="Activity Feed" />
        <div className="flex items-center gap-2">
          <div className="flex gap-0.5">
            {SEVERITY_OPTIONS.map((s) => (
              <FilterButton key={s} value={s} current={severityFilter} onClick={setSeverityFilter} />
            ))}
          </div>
          <div className="w-px h-4 bg-border" />
          <div className="flex gap-0.5">
            {CATEGORY_OPTIONS.map((c) => (
              <FilterButton key={c} value={c} current={categoryFilter} onClick={setCategoryFilter} label={CATEGORY_LABELS[c] ?? c} />
            ))}
          </div>
        </div>
      </div>
      {isLoading ? (
        <LoadingState rows={5} />
      ) : isError ? (
        <ErrorState message="Failed to load activity feed" onRetry={refetch} />
      ) : !filtered.length ? (
        <EmptyState message="No recent events" />
      ) : (
        <div
          ref={containerRef}
          onMouseEnter={() => setHovered(true)}
          onMouseLeave={() => setHovered(false)}
          className="max-h-80 overflow-y-auto space-y-0.5"
        >
          {filtered.map((event) => (
            <ActivityFeedItem
              key={event.id}
              summary={event.summary}
              ts={event.ts}
              severity={event.severity}
            />
          ))}
        </div>
      )}
    </div>
  );
}
