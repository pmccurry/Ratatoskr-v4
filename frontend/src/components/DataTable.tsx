import { useState, useMemo } from 'react';
import { ChevronUp, ChevronDown } from 'lucide-react';
import { PnlValue } from './PnlValue';
import { PriceValue } from './PriceValue';
import { StatusPill } from './StatusPill';
import { TimeAgo } from './TimeAgo';
import { EmptyState } from './EmptyState';

export type ColumnType = 'text' | 'number' | 'price' | 'pnl' | 'timestamp' | 'status';

export interface Column<T> {
  key: string;
  label: string;
  type?: ColumnType;
  sortable?: boolean;
  market?: string;
  render?: (row: T) => React.ReactNode;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  loading?: boolean;
  emptyMessage?: string;
  page?: number;
  pageSize?: number;
  total?: number;
  onPageChange?: (page: number) => void;
  onPageSizeChange?: (size: number) => void;
  keyField?: string;
}

export function DataTable<T extends Record<string, unknown>>({
  columns,
  data,
  loading,
  emptyMessage = 'No data available',
  page = 1,
  pageSize = 20,
  total,
  onPageChange,
  onPageSizeChange,
  keyField = 'id',
}: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  };

  const sortedData = useMemo(() => {
    if (!sortKey) return data;
    return [...data].sort((a, b) => {
      const aVal = a[sortKey];
      const bVal = b[sortKey];
      if (aVal == null) return 1;
      if (bVal == null) return -1;
      const cmp = aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
      return sortDir === 'asc' ? cmp : -cmp;
    });
  }, [data, sortKey, sortDir]);

  const renderCell = (row: T, col: Column<T>) => {
    if (col.render) return col.render(row);
    const val = row[col.key];
    switch (col.type) {
      case 'pnl':
        return <PnlValue value={val as number} />;
      case 'price':
        return <PriceValue value={val as number} market={col.market} />;
      case 'status':
        return <StatusPill status={val as string} />;
      case 'timestamp':
        return val ? <TimeAgo value={val as string} /> : '—';
      case 'number':
        return <span className="font-mono">{(val as number)?.toLocaleString()}</span>;
      default:
        return <span>{val != null ? String(val) : '—'}</span>;
    }
  };

  if (loading) {
    return (
      <div className="animate-pulse space-y-2">
        <div className="h-10 bg-surface rounded border border-border" />
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-12 bg-surface/50 rounded border border-border" />
        ))}
      </div>
    );
  }

  if (!data.length) {
    return <EmptyState message={emptyMessage} />;
  }

  const totalPages = total ? Math.ceil(total / pageSize) : 1;

  return (
    <div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border">
              {columns.map((col) => (
                <th
                  key={col.key}
                  className={`px-4 py-3 text-left text-text-secondary font-medium ${
                    col.sortable ? 'cursor-pointer hover:text-text-primary select-none' : ''
                  }`}
                  onClick={col.sortable ? () => handleSort(col.key) : undefined}
                >
                  <div className="flex items-center gap-1">
                    {col.label}
                    {col.sortable && sortKey === col.key && (
                      sortDir === 'asc' ? <ChevronUp size={14} /> : <ChevronDown size={14} />
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sortedData.map((row, i) => (
              <tr
                key={row[keyField] != null ? String(row[keyField]) : i}
                className="border-b border-border hover:bg-surface-hover transition-colors"
              >
                {columns.map((col) => (
                  <td key={col.key} className="px-4 py-3 text-text-primary">
                    {renderCell(row, col)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {total !== undefined && onPageChange && (
        <div className="flex items-center justify-between px-4 py-3 border-t border-border">
          <div className="flex items-center gap-2 text-sm text-text-secondary">
            <span>{total} items</span>
            {onPageSizeChange && (
              <select
                value={pageSize}
                onChange={(e) => onPageSizeChange(Number(e.target.value))}
                className="bg-surface border border-border rounded px-2 py-1 text-text-primary"
              >
                {[10, 20, 50, 100].map((s) => (
                  <option key={s} value={s}>{s} / page</option>
                ))}
              </select>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              disabled={page <= 1}
              onClick={() => onPageChange(page - 1)}
              className="px-3 py-1 text-sm bg-surface border border-border rounded hover:bg-surface-hover disabled:opacity-50 disabled:cursor-not-allowed text-text-primary"
            >
              Prev
            </button>
            <span className="text-sm text-text-secondary">
              {page} / {totalPages}
            </span>
            <button
              disabled={page >= totalPages}
              onClick={() => onPageChange(page + 1)}
              className="px-3 py-1 text-sm bg-surface border border-border rounded hover:bg-surface-hover disabled:opacity-50 disabled:cursor-not-allowed text-text-primary"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
