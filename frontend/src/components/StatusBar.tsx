import { useQuery } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import api from '@/lib/api';
import { REFRESH } from '@/lib/constants';

interface StatusBarProps {
  sidebarWidth: number;
}

export function StatusBar({ sidebarWidth }: StatusBarProps) {
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const interval = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(interval);
  }, []);

  const { data: health } = useQuery({
    queryKey: ['health-status'],
    queryFn: async () => {
      const res = await api.get('/health');
      return res.data;
    },
    refetchInterval: REFRESH.statusBar,
  });

  const { data: pipeline } = useQuery({
    queryKey: ['pipeline-status'],
    queryFn: async () => {
      const res = await api.get('/observability/health/pipeline');
      return res.data;
    },
    refetchInterval: REFRESH.statusBar,
  });

  const formatET = (date: Date) => {
    return date.toLocaleTimeString('en-US', {
      timeZone: 'America/New_York',
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    }) + ' ET';
  };

  const brokerLabel = (status: string | undefined): string => {
    if (!status) return 'Unknown';
    if (status === 'connected') return 'Connected';
    if (status === 'unconfigured') return 'Not configured';
    if (status === 'not_started') return 'No symbols';
    return 'Disconnected';
  };

  const brokerColor = (status: string | undefined): string => {
    if (status === 'connected') return 'bg-success';
    if (status === 'unconfigured' || status === 'not_started') return 'bg-warning';
    return 'bg-error';
  };

  const alpacaStatus = health?.brokers?.alpaca?.status;
  const oandaStatus = health?.brokers?.oanda?.status;

  // Pipeline status for strategies (snake_case keys from backend)
  const pipelineData = pipeline?.data ?? pipeline;
  const strategiesStatus = pipelineData?.strategies?.status
    || pipelineData?.market_data?.status
    || 'unknown';

  return (
    <div
      className="fixed bottom-0 right-0 h-8 bg-surface border-t border-border flex items-center px-4 gap-4 text-sm text-text-secondary z-30"
      style={{ left: sidebarWidth }}
    >
      <div className="flex items-center gap-1.5">
        <span className={`inline-block w-2 h-2 rounded-full ${brokerColor(alpacaStatus)}`} />
        <span>Alpaca {brokerLabel(alpacaStatus)}</span>
      </div>
      <div className="flex items-center gap-1.5">
        <span className={`inline-block w-2 h-2 rounded-full ${brokerColor(oandaStatus)}`} />
        <span>OANDA {brokerLabel(oandaStatus)}</span>
      </div>
      <span className="text-border">|</span>
      <span>
        Strategies: {strategiesStatus === 'running' ? 'active' : strategiesStatus}
      </span>
      <div className="flex-1" />
      <span className="font-mono">{formatET(time)}</span>
    </div>
  );
}
