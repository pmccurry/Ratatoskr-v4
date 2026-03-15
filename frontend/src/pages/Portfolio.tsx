import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import { STALE, REFRESH } from '@/lib/constants';
import { formatCurrency, formatPercent } from '@/lib/formatters';
import { PageContainer } from '@/components/PageContainer';
import { PageHeader } from '@/components/PageHeader';
import { TabContainer } from '@/components/TabContainer';
import { CardGrid, StatCard, SectionHeader } from '@/components';
import { PositionTable } from '@/features/portfolio/PositionTable';
import { EditStopLossDialog } from '@/features/portfolio/EditStopLossDialog';
import { PnlSummary } from '@/features/portfolio/PnlSummary';
import { PnlCalendar } from '@/features/portfolio/PnlCalendar';
import { EquityCurve } from '@/features/portfolio/EquityCurve';
import { DrawdownChart } from '@/features/portfolio/DrawdownChart';
import { DividendTable } from '@/features/portfolio/DividendTable';
import type { PortfolioSummary, EquityBreakdown } from '@/types/portfolio';
import type { Position } from '@/types/position';

const TABS = [
  { key: 'positions', label: 'Positions' },
  { key: 'pnl', label: 'PnL Analysis' },
  { key: 'equity', label: 'Equity' },
  { key: 'dividends', label: 'Dividends' },
];

export default function Portfolio() {
  const [editPosition, setEditPosition] = useState<Position | null>(null);
  const [closedOpen, setClosedOpen] = useState(false);

  const { data: summary, isLoading: summaryLoading } = useQuery<PortfolioSummary>({
    queryKey: ['portfolio', 'summary'],
    queryFn: () => api.get('/portfolio/summary').then((r) => r.data),
    staleTime: STALE.portfolioSummary,
    refetchInterval: REFRESH.portfolioSummary,
  });

  const { data: equityBreakdown } = useQuery<EquityBreakdown>({
    queryKey: ['portfolio', 'equity-breakdown'],
    queryFn: () => api.get('/portfolio/equity').then((r) => r.data),
    staleTime: STALE.portfolioSummary,
    refetchInterval: REFRESH.portfolioSummary,
  });

  return (
    <PageContainer>
      <PageHeader title="Portfolio" subtitle="Positions, PnL, and equity" />
      <TabContainer tabs={TABS}>
        {(activeTab) => (
          <>
            {activeTab === 'positions' && (
              <div className="space-y-6">
                <CardGrid>
                  <StatCard
                    label="Equity"
                    value={summary ? formatCurrency(summary.equity) : '—'}
                    subtitle={summary ? formatPercent(summary.totalReturnPercent) + ' return' : undefined}
                    loading={summaryLoading}
                  />
                  <StatCard
                    label="Cash"
                    value={summary ? formatCurrency(summary.cash) : '—'}
                    loading={summaryLoading}
                  />
                  <StatCard
                    label="Positions Value"
                    value={summary ? formatCurrency(summary.positionsValue) : '—'}
                    loading={summaryLoading}
                  />
                  <StatCard
                    label="Unrealized PnL"
                    value={summary ? formatCurrency(summary.unrealizedPnl) : '—'}
                    trend={summary ? ((summary.unrealizedPnl ?? 0) >= 0 ? 'up' : 'down') : undefined}
                    loading={summaryLoading}
                  />
                </CardGrid>

                <PositionTable
                  status="open"
                  onEditPosition={(p: Position) => setEditPosition(p)}
                />

                <div>
                  <button
                    onClick={() => setClosedOpen(!closedOpen)}
                    className="flex items-center gap-2 text-sm text-text-secondary hover:text-text-primary transition-colors mb-4"
                  >
                    <span className={`transform transition-transform ${closedOpen ? 'rotate-90' : ''}`}>▶</span>
                    Closed Positions
                  </button>
                  {closedOpen && <PositionTable status="closed" />}
                </div>
              </div>
            )}

            {activeTab === 'pnl' && (
              <div className="space-y-6">
                <PnlSummary />
                <PnlCalendar />
              </div>
            )}

            {activeTab === 'equity' && (
              <div className="space-y-6">
                <EquityCurve />
                <DrawdownChart />
                {equityBreakdown && (
                  <div className="grid grid-cols-2 gap-6">
                    <div className="bg-surface rounded-lg border border-border p-4">
                      <SectionHeader title="Cash vs Positions" />
                      <div className="space-y-3">
                        <div className="flex justify-between text-sm">
                          <span className="text-text-secondary">Cash</span>
                          <span className="font-mono text-text-primary">{formatCurrency(equityBreakdown.totalCash ?? 0)}</span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-text-secondary">Positions</span>
                          <span className="font-mono text-text-primary">{formatCurrency(equityBreakdown.totalPositionsValue ?? 0)}</span>
                        </div>
                        <div className="h-2 bg-border rounded-full overflow-hidden flex">
                          <div
                            className="bg-accent h-full"
                            style={{ width: `${(equityBreakdown.totalEquity ?? 0) > 0 ? ((equityBreakdown.totalCash ?? 0) / equityBreakdown.totalEquity) * 100 : 50}%` }}
                          />
                          <div
                            className="bg-info h-full"
                            style={{ width: `${(equityBreakdown.totalEquity ?? 0) > 0 ? ((equityBreakdown.totalPositionsValue ?? 0) / equityBreakdown.totalEquity) * 100 : 50}%` }}
                          />
                        </div>
                      </div>
                    </div>
                    <div className="bg-surface rounded-lg border border-border p-4">
                      <SectionHeader title="Equities vs Forex" />
                      <div className="space-y-3">
                        <div className="flex justify-between text-sm">
                          <span className="text-text-secondary">Equities</span>
                          <span className="font-mono text-text-primary">{formatCurrency((equityBreakdown.equitiesCash ?? 0) + (equityBreakdown.equitiesPositionsValue ?? 0))}</span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-text-secondary">Forex</span>
                          <span className="font-mono text-text-primary">{formatCurrency((equityBreakdown.forexCash ?? 0) + (equityBreakdown.forexPositionsValue ?? 0))}</span>
                        </div>
                        <div className="h-2 bg-border rounded-full overflow-hidden flex">
                          <div
                            className="bg-success h-full"
                            style={{ width: `${(equityBreakdown.totalEquity ?? 0) > 0 ? (((equityBreakdown.equitiesCash ?? 0) + (equityBreakdown.equitiesPositionsValue ?? 0)) / equityBreakdown.totalEquity) * 100 : 50}%` }}
                          />
                          <div
                            className="bg-warning h-full"
                            style={{ width: `${(equityBreakdown.totalEquity ?? 0) > 0 ? (((equityBreakdown.forexCash ?? 0) + (equityBreakdown.forexPositionsValue ?? 0)) / equityBreakdown.totalEquity) * 100 : 50}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'dividends' && <DividendTable />}
          </>
        )}
      </TabContainer>

      <EditStopLossDialog
        open={editPosition !== null}
        position={editPosition}
        onClose={() => setEditPosition(null)}
        onSaved={() => setEditPosition(null)}
      />
    </PageContainer>
  );
}
