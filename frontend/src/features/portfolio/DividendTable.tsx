import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import { CardGrid, StatCard, SectionHeader, DataTable, LoadingState, EmptyState, ErrorState } from '@/components';
import type { Column } from '@/components';
import type { DividendPayment } from '@/types/portfolio';
import { formatCurrency } from '@/lib/formatters';

interface UpcomingDividend {
  symbol: string;
  exDate: string;
  payableDate: string;
  sharesHeld: number;
  estimatedAmount: number;
}

interface DividendSummary {
  today: number;
  thisMonth: number;
  thisYear: number;
  allTime: number;
  bySymbol: Record<string, number>;
}

type UpcomingRecord = UpcomingDividend & Record<string, unknown>;
type PaymentRecord = DividendPayment & Record<string, unknown>;

export function DividendTable() {
  const {
    data: upcoming,
    isLoading: upcomingLoading,
    isError: upcomingError,
    refetch: refetchUpcoming,
  } = useQuery<UpcomingDividend[]>({
    queryKey: ['portfolio', 'dividends', 'upcoming'],
    queryFn: () => api.get('/portfolio/dividends/upcoming').then((r) => r.data),
    staleTime: 60_000,
  });

  const {
    data: history,
    isLoading: historyLoading,
    isError: historyError,
    refetch: refetchHistory,
  } = useQuery<DividendPayment[]>({
    queryKey: ['portfolio', 'dividends', 'history'],
    queryFn: () => api.get('/portfolio/dividends').then((r) => r.data),
    staleTime: 60_000,
  });

  const {
    data: summary,
    isLoading: summaryLoading,
    isError: summaryError,
    refetch: refetchSummary,
  } = useQuery<DividendSummary>({
    queryKey: ['portfolio', 'dividends', 'summary'],
    queryFn: () => api.get('/portfolio/dividends/summary').then((r) => r.data),
    staleTime: 60_000,
  });

  const isLoading = upcomingLoading || historyLoading || summaryLoading;
  const isError = upcomingError || historyError || summaryError;

  if (isLoading) return <LoadingState rows={6} />;
  if (isError) {
    return (
      <ErrorState
        message="Failed to load dividend data"
        onRetry={() => {
          refetchUpcoming();
          refetchHistory();
          refetchSummary();
        }}
      />
    );
  }

  const upcomingColumns: Column<UpcomingRecord>[] = [
    { key: 'symbol', label: 'Symbol', sortable: true },
    { key: 'exDate', label: 'Ex-Date', type: 'timestamp' },
    { key: 'payableDate', label: 'Payable Date', type: 'timestamp' },
    { key: 'sharesHeld', label: 'Shares', type: 'number' },
    {
      key: 'estimatedAmount',
      label: 'Est. Amount',
      render: (row) => <span className="font-mono">{formatCurrency(row.estimatedAmount as number)}</span>,
    },
  ];

  const historyColumns: Column<PaymentRecord>[] = [
    { key: 'symbol', label: 'Symbol', sortable: true },
    { key: 'exDate', label: 'Ex-Date', type: 'timestamp' },
    { key: 'paidAt', label: 'Paid Date', type: 'timestamp' },
    { key: 'sharesHeld', label: 'Shares', type: 'number' },
    {
      key: 'amountPerShare',
      label: '$/Share',
      type: 'price',
    },
    {
      key: 'grossAmount',
      label: 'Gross',
      render: (row) => <span className="font-mono">{formatCurrency(row.grossAmount as number)}</span>,
    },
    {
      key: 'netAmount',
      label: 'Net',
      render: (row) => <span className="font-mono">{formatCurrency(row.netAmount as number)}</span>,
    },
    { key: 'status', label: 'Status', type: 'status' },
  ];

  const bySymbolEntries = summary ? Object.entries(summary.bySymbol) : [];

  return (
    <div>
      <CardGrid columns={4}>
        <StatCard label="Today" value={formatCurrency(summary?.today ?? 0)} />
        <StatCard label="This Month" value={formatCurrency(summary?.thisMonth ?? 0)} />
        <StatCard label="This Year" value={formatCurrency(summary?.thisYear ?? 0)} />
        <StatCard label="All Time" value={formatCurrency(summary?.allTime ?? 0)} />
      </CardGrid>

      <div className="mt-6">
        <SectionHeader title="Upcoming Dividends" />
        {!upcoming || upcoming.length === 0 ? (
          <EmptyState message="No upcoming dividends" />
        ) : (
          <DataTable<UpcomingRecord>
            columns={upcomingColumns}
            data={upcoming as UpcomingRecord[]}
            emptyMessage="No upcoming dividends"
            keyField="symbol"
          />
        )}
      </div>

      <div className="mt-6">
        <SectionHeader title="Dividend History" />
        {!history || history.length === 0 ? (
          <EmptyState message="No dividend history" />
        ) : (
          <DataTable<PaymentRecord>
            columns={historyColumns}
            data={history as PaymentRecord[]}
            emptyMessage="No dividend history"
          />
        )}
      </div>

      {bySymbolEntries.length > 0 && (
        <div className="mt-6">
          <SectionHeader title="By Symbol" />
          <div className="flex flex-col gap-1 mt-2">
            {bySymbolEntries.map(([symbol, amount]) => (
              <div key={symbol} className="flex justify-between items-center py-1">
                <span className="text-sm text-text-secondary">{symbol}</span>
                <span className="font-mono text-sm text-text-primary">{formatCurrency(amount)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
