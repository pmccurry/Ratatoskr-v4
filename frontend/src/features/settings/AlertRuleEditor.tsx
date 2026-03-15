import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';
import { DataTable, StatusPill, LoadingState, EmptyState, ErrorState, SectionHeader } from '@/components';
import type { Column } from '@/components';
import type { AlertRule, AlertInstance } from '@/types/observability';

type AlertInstanceRow = AlertInstance & Record<string, unknown>;

export function AlertRuleEditor() {
  const queryClient = useQueryClient();

  const {
    data: rules,
    isLoading: rulesLoading,
    isError: rulesError,
    refetch: refetchRules,
  } = useQuery<AlertRule[]>({
    queryKey: ['observability', 'alert-rules'],
    queryFn: () => api.get('/observability/alert-rules').then((r) => r.data),
    staleTime: 30_000,
  });

  const {
    data: alerts,
    isLoading: alertsLoading,
    isError: alertsError,
    refetch: refetchAlerts,
  } = useQuery<AlertInstance[]>({
    queryKey: ['observability', 'alerts'],
    queryFn: () => api.get('/observability/alerts').then((r) => r.data),
    staleTime: 15_000,
    refetchInterval: 15_000,
  });

  const toggleRuleMutation = useMutation({
    mutationFn: ({ ruleId, enabled }: { ruleId: string; enabled: boolean }) =>
      api.put(`/observability/alert-rules/${ruleId}`, { enabled }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['observability', 'alert-rules'] });
    },
  });

  const acknowledgeMutation = useMutation({
    mutationFn: (alertId: string) =>
      api.post(`/observability/alerts/${alertId}/ack`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['observability', 'alerts'] });
    },
  });

  const alertColumns: Column<AlertInstanceRow>[] = [
    { key: 'triggeredAt', label: 'Triggered', type: 'timestamp', sortable: true },
    {
      key: 'severity',
      label: 'Severity',
      render: (row: AlertInstanceRow) => <StatusPill status={row.severity} />,
    },
    { key: 'summary', label: 'Summary' },
    {
      key: 'status',
      label: 'Status',
      render: (row: AlertInstanceRow) => <StatusPill status={row.status} />,
    },
    {
      key: 'acknowledgedBy',
      label: 'Acknowledged By',
      render: (row: AlertInstanceRow) => (
        <span className="text-text-secondary">{row.acknowledgedBy ?? '---'}</span>
      ),
    },
    {
      key: 'ack',
      label: '',
      render: (row: AlertInstanceRow) => {
        if (row.acknowledgedAt || row.status === 'resolved') return null;
        return (
          <button
            onClick={() => acknowledgeMutation.mutate(row.id)}
            disabled={acknowledgeMutation.isPending}
            className="px-3 py-1 text-xs bg-accent/20 text-accent rounded hover:bg-accent/30 transition-colors"
          >
            Acknowledge
          </button>
        );
      },
    },
  ];

  const alertTableData: AlertInstanceRow[] = (alerts ?? []) as AlertInstanceRow[];

  return (
    <div className="space-y-8">
      {/* Section 1 -- Alert Rules */}
      <div>
        <SectionHeader title="Alert Rules" />

        {rulesLoading && <LoadingState rows={4} />}

        {rulesError && (
          <ErrorState message="Failed to load alert rules" onRetry={() => refetchRules()} />
        )}

        {!rulesLoading && !rulesError && (!rules || rules.length === 0) && (
          <EmptyState message="No alert rules configured" />
        )}

        {!rulesLoading && !rulesError && rules && rules.length > 0 && (
          <div className="space-y-2">
            {rules.map((rule) => (
              <div
                key={rule.id}
                className="bg-surface border border-border rounded-lg p-4 flex items-center justify-between"
              >
                <div className="flex items-center gap-4 flex-1 min-w-0">
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-medium text-text-primary truncate">
                      {rule.name}
                    </div>
                    {rule.description && (
                      <div className="text-xs text-text-tertiary truncate mt-0.5">
                        {rule.description}
                      </div>
                    )}
                  </div>
                  <span className="text-xs text-text-secondary">{rule.category}</span>
                  <span className="text-xs text-text-secondary">{rule.conditionType}</span>
                  <StatusPill status={rule.severity} />
                </div>
                <button
                  role="switch"
                  aria-checked={rule.enabled}
                  onClick={() =>
                    toggleRuleMutation.mutate({ ruleId: rule.id, enabled: !rule.enabled })
                  }
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ml-4 flex-shrink-0 ${
                    rule.enabled ? 'bg-accent' : 'bg-border'
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      rule.enabled ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Section 2 -- Alert History */}
      <div>
        <SectionHeader title="Alert History" />

        {alertsLoading && <LoadingState rows={5} />}

        {alertsError && (
          <ErrorState message="Failed to load alert history" onRetry={() => refetchAlerts()} />
        )}

        {!alertsLoading && !alertsError && alertTableData.length === 0 && (
          <EmptyState message="No alerts triggered" />
        )}

        {!alertsLoading && !alertsError && alertTableData.length > 0 && (
          <DataTable<AlertInstanceRow>
            columns={alertColumns}
            data={alertTableData}
          />
        )}
      </div>
    </div>
  );
}
