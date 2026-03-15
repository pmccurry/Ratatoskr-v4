import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { X, AlertTriangle } from 'lucide-react';
import { Link } from 'react-router-dom';
import api from '@/lib/api';
import { REFRESH } from '@/lib/constants';
import type { AlertInstance } from '@/types/observability';

const SEVERITY_STYLES: Record<string, string> = {
  critical: 'bg-error/20 border-error text-error',
  error: 'bg-error/15 border-error/70 text-error',
  warning: 'bg-warning/15 border-warning/70 text-warning',
};

export function AlertBanner() {
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());

  const { data: alerts } = useQuery<AlertInstance[]>({
    queryKey: ['alerts', 'active'],
    queryFn: async () => {
      const res = await api.get('/observability/alerts/active');
      return res.data;
    },
    refetchInterval: REFRESH.alertBanner,
  });

  if (!alerts?.length) return null;

  // Show highest severity non-dismissed alert
  const severityOrder = ['critical', 'error', 'warning'];
  const visibleAlerts = alerts.filter((a) => !dismissed.has(a.id));
  if (!visibleAlerts.length) return null;

  const topAlert = visibleAlerts.sort(
    (a, b) => severityOrder.indexOf(a.severity) - severityOrder.indexOf(b.severity)
  )[0];

  const styles = SEVERITY_STYLES[topAlert.severity] || SEVERITY_STYLES.warning;
  const isDismissible = topAlert.severity === 'warning';

  return (
    <div className={`px-4 py-2 border-b flex items-center gap-3 ${styles}`}>
      <AlertTriangle size={16} className="shrink-0" />
      <span className="text-sm flex-1">{topAlert.summary}</span>
      {visibleAlerts.length > 1 && (
        <span className="text-sm opacity-70">+{visibleAlerts.length - 1} more</span>
      )}
      <Link to="/system" className="text-sm underline opacity-80 hover:opacity-100">
        View All
      </Link>
      {isDismissible && (
        <button
          onClick={() => setDismissed((prev) => new Set(prev).add(topAlert.id))}
          className="hover:opacity-70"
        >
          <X size={16} />
        </button>
      )}
    </div>
  );
}
