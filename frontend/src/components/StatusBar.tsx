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

  const dot = (status: string) => (
    <span className={`inline-block w-2 h-2 rounded-full ${status === 'running' ? 'bg-success' : 'bg-error'}`} />
  );

  const alpacaStatus = health?.marketData?.status || 'unknown';
  const oandaStatus = health?.marketData?.status || 'unknown';
  const strategiesStatus = health?.strategies?.status || 'unknown';

  return (
    <div
      className="fixed bottom-0 right-0 h-8 bg-surface border-t border-border flex items-center px-4 gap-4 text-sm text-text-secondary z-30"
      style={{ left: sidebarWidth }}
    >
      <div className="flex items-center gap-1.5">
        {dot(alpacaStatus)}
        <span>Alpaca {alpacaStatus === 'running' ? 'Connected' : 'Disconnected'}</span>
      </div>
      <div className="flex items-center gap-1.5">
        {dot(oandaStatus)}
        <span>OANDA {oandaStatus === 'running' ? 'Connected' : 'Disconnected'}</span>
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
