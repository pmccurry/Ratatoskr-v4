import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import { STALE, REFRESH } from '@/lib/constants';
import { formatDateTime } from '@/lib/formatters';
import { DataTable, SectionHeader } from '@/components';
import type { Column } from '@/components';
import type { RiskOverview, RiskDecision } from '@/types/risk';

type DecisionRow = RiskDecision & Record<string, unknown>;

const STATUS_ICONS: Record<string, string> = {
  approved: '\u2705',
  rejected: '\u274C',
  modified: '\u2699\uFE0F',
};

export function RiskDecisionTable() {
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data, isLoading } = useQuery<RiskOverview>({
    queryKey: ['risk', 'overview'],
    queryFn: () => api.get('/risk/overview').then((r) => r.data),
    staleTime: STALE.riskOverview,
    refetchInterval: REFRESH.riskOverview,
  });

  const decisions: DecisionRow[] = useMemo(() => {
    const all = (data?.recentDecisions ?? []) as DecisionRow[];
    if (statusFilter === 'all') return all;
    return all.filter((d) => d.status === statusFilter);
  }, [data, statusFilter]);

  const selected = decisions.find((d) => d.id === selectedId);

  const columns: Column<DecisionRow>[] = [
    {
      key: 'ts',
      label: 'Time',
      sortable: true,
      render: (row) => <span className="text-sm font-mono">{formatDateTime(row.ts)}</span>,
    },
    {
      key: 'signalId',
      label: 'Signal ID',
      render: (row) => (
        <span className="font-mono text-xs text-text-secondary">{row.signalId.slice(0, 8)}</span>
      ),
    },
    {
      key: 'symbol',
      label: 'Symbol',
      render: (row) => {
        const symbol =
          (row.portfolioStateSnapshot as Record<string, unknown>)?.symbol as string | undefined;
        return <span>{symbol ?? '—'}</span>;
      },
    },
    {
      key: 'status',
      label: 'Status',
      sortable: true,
      render: (row) => (
        <span>
          {STATUS_ICONS[row.status] ?? row.status} {row.status}
        </span>
      ),
    },
    {
      key: 'reasonText',
      label: 'Reason',
      render: (row) => (
        <span className="text-sm text-text-secondary">{row.reasonText ?? '—'}</span>
      ),
    },
    {
      key: 'checksPassed',
      label: 'Checks Passed',
      render: (row) => (
        <span className="font-mono text-sm">{row.checksPassed?.length ?? 0}</span>
      ),
    },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <SectionHeader title="Risk Decisions" />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="bg-surface border border-border rounded px-3 py-1.5 text-sm text-text-primary"
        >
          <option value="all">All Statuses</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
          <option value="modified">Modified</option>
        </select>
      </div>

      <div
        onClick={(e) => {
          const row = (e.target as HTMLElement).closest('tr');
          if (!row) return;
          const idx = row.rowIndex - 1;
          if (idx >= 0 && idx < decisions.length) {
            setSelectedId(decisions[idx].id === selectedId ? null : decisions[idx].id);
          }
        }}
      >
        <DataTable<DecisionRow>
          columns={columns}
          data={decisions}
          loading={isLoading}
          emptyMessage="No risk decisions to display"
          keyField="id"
        />
      </div>

      {selected && (
        <div className="mt-4 bg-surface rounded-lg border border-border p-4">
          <h4 className="text-sm font-medium text-text-primary mb-3">Portfolio State Snapshot</h4>
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(selected.portfolioStateSnapshot).map(([key, value]) => (
              <div key={key} className="flex items-baseline gap-2 text-sm">
                <span className="text-text-secondary">{key}:</span>
                <span className="font-mono text-text-primary">
                  {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
