import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';
import { ConfirmDialog } from '@/components';

interface KillSwitchStatus {
  global: boolean;
  perStrategy: Record<string, boolean>;
}

export function KillSwitchControl() {
  const queryClient = useQueryClient();
  const [showDialog, setShowDialog] = useState(false);

  const { data } = useQuery<KillSwitchStatus>({
    queryKey: ['risk', 'kill-switch', 'status'],
    queryFn: () => api.get('/risk/kill-switch/status').then((r) => r.data),
    staleTime: 10_000,
    refetchInterval: 15_000,
  });

  const isActive = data?.global ?? false;

  const activateMutation = useMutation({
    mutationFn: () => api.post('/risk/kill-switch/activate'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['risk'] });
      setShowDialog(false);
    },
  });

  const deactivateMutation = useMutation({
    mutationFn: () => api.post('/risk/kill-switch/deactivate'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['risk'] });
      setShowDialog(false);
    },
  });

  const isPending = activateMutation.isPending || deactivateMutation.isPending;

  return (
    <div>
      {isActive ? (
        <button
          onClick={() => setShowDialog(true)}
          disabled={isPending}
          className="flex items-center gap-3 px-6 py-3 bg-error/10 border-2 border-error rounded-lg text-error font-semibold text-lg hover:bg-error/20 transition-colors disabled:opacity-50"
        >
          <span className="relative flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-error opacity-75" />
            <span className="relative inline-flex rounded-full h-3 w-3 bg-error" />
          </span>
          KILL SWITCH ACTIVE
        </button>
      ) : (
        <button
          onClick={() => setShowDialog(true)}
          disabled={isPending}
          className="flex items-center gap-3 px-6 py-3 bg-surface border-2 border-success rounded-lg text-success font-medium hover:bg-surface-hover transition-colors disabled:opacity-50"
        >
          <span className="inline-flex rounded-full h-3 w-3 bg-success" />
          Kill Switch Inactive
        </button>
      )}

      <ConfirmDialog
        open={showDialog}
        title={isActive ? 'Deactivate Kill Switch?' : 'Activate Kill Switch?'}
        message={
          isActive
            ? 'Deactivating the kill switch will allow new entry signals to be processed again.'
            : 'Activating the kill switch will block ALL new entry signals. Exit signals will still be allowed.'
        }
        confirmLabel={isActive ? 'Deactivate' : 'Activate'}
        variant={isActive ? 'default' : 'danger'}
        onConfirm={() => {
          if (isActive) {
            deactivateMutation.mutate();
          } else {
            activateMutation.mutate();
          }
        }}
        onCancel={() => setShowDialog(false)}
      />
    </div>
  );
}
