import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import { formatCurrency } from '@/lib/formatters';
import { SectionHeader, LoadingState } from '@/components';

interface ForexPoolAccount {
  accountId: string;
  label: string;
  capitalAllocation: number;
  active: boolean;
}

export function BrokerAccountManager() {
  const {
    data: poolAccounts,
    isLoading,
    isError,
  } = useQuery<ForexPoolAccount[]>({
    queryKey: ['paper-trading', 'forex-pool', 'status'],
    queryFn: () => api.get('/paper-trading/forex-pool/status').then((r) => r.data),
    staleTime: 60_000,
    retry: 1,
  });

  return (
    <div className="space-y-8">
      {/* Section 1 -- Broker Connections */}
      <div>
        <SectionHeader title="Broker Connections" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-surface border border-border rounded-lg p-5">
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-sm font-medium text-text-primary">Alpaca</h4>
              <div className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full bg-success" />
                <span className="text-sm text-success">Connected</span>
              </div>
            </div>
            <span className="text-xs text-text-tertiary">Equities &amp; Options</span>
          </div>

          <div className="bg-surface border border-border rounded-lg p-5">
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-sm font-medium text-text-primary">OANDA</h4>
              <div className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full bg-success" />
                <span className="text-sm text-success">Connected</span>
              </div>
            </div>
            <span className="text-xs text-text-tertiary">Forex</span>
          </div>
        </div>
      </div>

      {/* Section 2 -- Forex Pool Accounts */}
      <div>
        <SectionHeader title="Forex Pool Accounts" />

        {isLoading && <LoadingState rows={3} />}

        {!isLoading && (isError || !poolAccounts || poolAccounts.length === 0) && (
          <div className="bg-surface border border-border rounded-lg p-6 text-center">
            <p className="text-sm text-text-secondary">
              Forex pool status available when forex strategies are active
            </p>
          </div>
        )}

        {!isLoading && !isError && poolAccounts && poolAccounts.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {poolAccounts.map((account) => (
              <div
                key={account.accountId}
                className="bg-surface border border-border rounded-lg p-4"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-text-primary">
                    {account.label}
                  </span>
                  <div className="flex items-center gap-1.5">
                    <span
                      className={`h-2 w-2 rounded-full ${
                        account.active ? 'bg-success' : 'bg-text-tertiary'
                      }`}
                    />
                    <span
                      className={`text-xs ${
                        account.active ? 'text-success' : 'text-text-tertiary'
                      }`}
                    >
                      {account.active ? 'Active' : 'Inactive'}
                    </span>
                  </div>
                </div>
                <div className="text-sm text-text-secondary">
                  Capital: <span className="font-mono text-text-primary">{formatCurrency(account.capitalAllocation)}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
