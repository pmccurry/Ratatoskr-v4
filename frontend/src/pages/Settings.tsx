import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';
import { formatPercent, formatCurrency } from '@/lib/formatters';
import { PageContainer } from '@/components/PageContainer';
import { PageHeader } from '@/components/PageHeader';
import { TabContainer } from '@/components/TabContainer';
import { SectionHeader, LoadingState, ConfirmDialog, DataTable } from '@/components';
import type { Column } from '@/components';
import { UserManagement } from '@/features/settings/UserManagement';
import { AlertRuleEditor } from '@/features/settings/AlertRuleEditor';
import { BrokerAccountManager } from '@/features/settings/BrokerAccountManager';
import type { RiskConfig } from '@/types/risk';

interface AuditEntry extends Record<string, unknown> {
  id: string;
  field: string;
  oldValue: string;
  newValue: string;
  changedBy: string;
  changedAt: string;
}

const AUDIT_COLUMNS: Column<AuditEntry>[] = [
  { key: 'field', label: 'Field', sortable: true },
  { key: 'oldValue', label: 'Old Value' },
  { key: 'newValue', label: 'New Value' },
  { key: 'changedBy', label: 'Changed By' },
  { key: 'changedAt', label: 'Timestamp', type: 'timestamp' },
];

const TABS = [
  { key: 'risk', label: 'Risk Config' },
  { key: 'accounts', label: 'Accounts' },
  { key: 'users', label: 'Users' },
  { key: 'alerts', label: 'Alerts' },
  { key: 'system', label: 'System' },
];

const RISK_FIELDS: Array<{ key: keyof RiskConfig; label: string; format: 'percent' | 'currency' }> = [
  { key: 'maxPositionSizePercent', label: 'Max Position Size', format: 'percent' },
  { key: 'maxSymbolExposurePercent', label: 'Max Symbol Exposure', format: 'percent' },
  { key: 'maxStrategyExposurePercent', label: 'Max Strategy Exposure', format: 'percent' },
  { key: 'maxTotalExposurePercent', label: 'Max Total Exposure', format: 'percent' },
  { key: 'maxDrawdownPercent', label: 'Max Drawdown', format: 'percent' },
  { key: 'maxDrawdownCatastrophicPercent', label: 'Catastrophic Drawdown', format: 'percent' },
  { key: 'maxDailyLossPercent', label: 'Max Daily Loss', format: 'percent' },
  { key: 'minPositionValue', label: 'Min Position Value', format: 'currency' },
];

function pathToTab(pathname: string): string {
  if (pathname.startsWith('/settings/risk')) return 'risk';
  if (pathname.startsWith('/settings/accounts')) return 'accounts';
  if (pathname.startsWith('/settings/users')) return 'users';
  if (pathname.startsWith('/settings/alerts')) return 'alerts';
  if (pathname.startsWith('/settings/system')) return 'system';
  return 'risk';
}

export default function SettingsPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const defaultTab = pathToTab(location.pathname);

  const [confirmSave, setConfirmSave] = useState(false);
  const [formValues, setFormValues] = useState<Record<string, string>>({});

  const { data: riskConfig, isLoading: configLoading } = useQuery<RiskConfig>({
    queryKey: ['risk', 'config'],
    queryFn: () => api.get('/risk/config').then((r) => r.data),
    staleTime: 30_000,
  });

  const { data: auditEntries, isLoading: auditLoading } = useQuery<AuditEntry[]>({
    queryKey: ['risk', 'config', 'audit'],
    queryFn: () => api.get('/risk/config/audit').then((r) => r.data?.data ?? r.data),
    staleTime: 30_000,
  });

  const saveMutation = useMutation({
    mutationFn: (payload: Record<string, number>) => api.put('/risk/config', payload),
    onSuccess: () => {
      setConfirmSave(false);
      queryClient.invalidateQueries({ queryKey: ['risk', 'config'] });
    },
  });

  const handleTabChange = (tab: string) => {
    const path = tab === 'risk' ? '/settings' : `/settings/${tab}`;
    navigate(path, { replace: true });
  };

  const handleRiskSave = () => {
    const payload: Record<string, number> = {};
    for (const field of RISK_FIELDS) {
      const val = formValues[field.key];
      if (val !== undefined && val !== '') {
        payload[field.key] = parseFloat(val);
      } else if (riskConfig) {
        payload[field.key] = riskConfig[field.key] as number;
      }
    }
    saveMutation.mutate(payload);
  };

  const getFieldValue = (key: keyof RiskConfig): string => {
    if (formValues[key] !== undefined) return formValues[key];
    if (riskConfig) return String(riskConfig[key]);
    return '';
  };

  return (
    <PageContainer>
      <PageHeader title="Settings" subtitle="Platform configuration" />
      <TabContainer tabs={TABS} defaultTab={defaultTab} onTabChange={handleTabChange}>
        {(activeTab) => (
            <>
              {activeTab === 'risk' && (
                <div className="space-y-6">
                  <div className="bg-surface rounded-lg border border-border p-6">
                    <SectionHeader title="Risk Configuration" />
                    {configLoading ? (
                      <LoadingState rows={4} />
                    ) : (
                      <div className="space-y-4">
                        {RISK_FIELDS.map((field) => (
                          <div key={field.key} className="grid grid-cols-3 gap-4 items-center">
                            <label className="text-sm text-text-secondary">{field.label}</label>
                            <input
                              type="number"
                              step="any"
                              value={getFieldValue(field.key)}
                              onChange={(e) =>
                                setFormValues((prev) => ({ ...prev, [field.key]: e.target.value }))
                              }
                              className="bg-surface border border-border rounded px-3 py-1.5 text-sm text-text-primary font-mono focus:outline-none focus:ring-1 focus:ring-accent"
                            />
                            <span className="text-xs text-text-tertiary">
                              {field.format === 'percent'
                                ? `Current: ${riskConfig ? formatPercent(riskConfig[field.key] as number) : '—'}`
                                : `Current: ${riskConfig ? formatCurrency(riskConfig[field.key] as number) : '—'}`}
                            </span>
                          </div>
                        ))}
                        <div className="pt-4">
                          <button
                            onClick={() => setConfirmSave(true)}
                            disabled={saveMutation.isPending}
                            className="px-4 py-2 text-sm bg-accent text-white rounded hover:bg-accent/80 disabled:opacity-50"
                          >
                            Save Configuration
                          </button>
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="bg-surface rounded-lg border border-border p-6">
                    <SectionHeader title="Change History" />
                    {auditLoading ? (
                      <LoadingState rows={3} />
                    ) : (
                      <DataTable
                        columns={AUDIT_COLUMNS}
                        data={(auditEntries ?? []) as AuditEntry[]}
                        emptyMessage="No configuration changes recorded"
                        keyField="id"
                      />
                    )}
                  </div>
                </div>
              )}

              {activeTab === 'accounts' && <BrokerAccountManager />}
              {activeTab === 'users' && <UserManagement />}
              {activeTab === 'alerts' && <AlertRuleEditor />}

              {activeTab === 'system' && (
                <div className="bg-surface rounded-lg border border-border p-6">
                  <SectionHeader title="System Information" />
                  <div className="space-y-3">
                    <div className="flex justify-between text-sm">
                      <span className="text-text-secondary">Environment</span>
                      <span className="text-text-primary font-mono">paper-trading</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-text-secondary">Version</span>
                      <span className="text-text-primary font-mono">1.0.0</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-text-secondary">Database</span>
                      <span className="text-text-primary font-mono">PostgreSQL</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-text-secondary">API</span>
                      <span className="text-text-primary font-mono">FastAPI / Python 3.12</span>
                    </div>
                  </div>
                </div>
              )}
            </>
        )}
      </TabContainer>

      <ConfirmDialog
        open={confirmSave}
        title="Update Risk Configuration"
        message="Are you sure you want to update the risk configuration? Changes take effect immediately."
        confirmLabel="Save"
        onConfirm={handleRiskSave}
        onCancel={() => setConfirmSave(false)}
      />
    </PageContainer>
  );
}
