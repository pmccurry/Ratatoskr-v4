import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';
import { DataTable, StatusPill, LoadingState, EmptyState, ErrorState, ConfirmDialog } from '@/components';
import type { Column } from '@/components';
import type { User } from '@/types/auth';

type UserRow = User & Record<string, unknown>;

interface CreateUserForm {
  email: string;
  username: string;
  password: string;
  role: 'admin' | 'user';
}

export function UserManagement() {
  const queryClient = useQueryClient();
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [confirmAction, setConfirmAction] = useState<{
    userId: string;
    action: 'suspend' | 'activate';
  } | null>(null);
  const [form, setForm] = useState<CreateUserForm>({
    email: '',
    username: '',
    password: '',
    role: 'user',
  });

  const { data, isLoading, isError, refetch } = useQuery<User[]>({
    queryKey: ['auth', 'users'],
    queryFn: () => api.get('/auth/users').then((r) => r.data),
    staleTime: 30_000,
  });

  const updateStatusMutation = useMutation({
    mutationFn: ({ userId, status }: { userId: string; status: string }) =>
      api.put(`/auth/users/${userId}`, { status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['auth', 'users'] });
      setConfirmAction(null);
    },
  });

  const changeRoleMutation = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: string }) =>
      api.put(`/auth/users/${userId}`, { role }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['auth', 'users'] });
    },
  });

  const createUserMutation = useMutation({
    mutationFn: (payload: CreateUserForm) =>
      api.post('/auth/users', payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['auth', 'users'] });
      setShowCreateModal(false);
      setForm({ email: '', username: '', password: '', role: 'user' });
    },
  });

  const columns: Column<UserRow>[] = [
    { key: 'email', label: 'Email', sortable: true },
    { key: 'username', label: 'Username', sortable: true },
    {
      key: 'role',
      label: 'Role',
      render: (row: UserRow) => <StatusPill status={row.role} />,
    },
    {
      key: 'status',
      label: 'Status',
      render: (row: UserRow) => <StatusPill status={row.status} />,
    },
    { key: 'lastLoginAt', label: 'Last Login', type: 'timestamp', sortable: true },
    {
      key: 'actions',
      label: 'Actions',
      render: (row: UserRow) => (
        <div className="flex items-center gap-2">
          {row.status === 'active' ? (
            <button
              onClick={() => setConfirmAction({ userId: row.id, action: 'suspend' })}
              className="px-3 py-1 text-xs bg-error/20 text-error rounded hover:bg-error/30 transition-colors"
            >
              Suspend
            </button>
          ) : (
            <button
              onClick={() => setConfirmAction({ userId: row.id, action: 'activate' })}
              className="px-3 py-1 text-xs bg-success/20 text-success rounded hover:bg-success/30 transition-colors"
            >
              Activate
            </button>
          )}
          <select
            value={row.role}
            onChange={(e) =>
              changeRoleMutation.mutate({ userId: row.id, role: e.target.value })
            }
            className="bg-surface border border-border rounded px-2 py-1 text-xs text-text-primary"
          >
            <option value="user">user</option>
            <option value="admin">admin</option>
          </select>
        </div>
      ),
    },
  ];

  const tableData: UserRow[] = (data ?? []) as UserRow[];

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-text-secondary">User Accounts</h3>
        <button
          onClick={() => setShowCreateModal(true)}
          className="px-4 py-2 text-sm bg-accent hover:bg-accent-hover text-white rounded transition-colors"
        >
          Create User
        </button>
      </div>

      {isLoading && <LoadingState rows={5} />}

      {isError && (
        <ErrorState message="Failed to load users" onRetry={() => refetch()} />
      )}

      {!isLoading && !isError && tableData.length === 0 && (
        <EmptyState message="No users found" />
      )}

      {!isLoading && !isError && tableData.length > 0 && (
        <DataTable<UserRow>
          columns={columns}
          data={tableData}
        />
      )}

      <ConfirmDialog
        open={confirmAction !== null}
        title={confirmAction?.action === 'suspend' ? 'Suspend User' : 'Activate User'}
        message={
          confirmAction?.action === 'suspend'
            ? 'Are you sure you want to suspend this user? They will be unable to log in.'
            : 'Are you sure you want to activate this user?'
        }
        confirmLabel={confirmAction?.action === 'suspend' ? 'Suspend' : 'Activate'}
        variant={confirmAction?.action === 'suspend' ? 'danger' : 'default'}
        onConfirm={() => {
          if (confirmAction) {
            updateStatusMutation.mutate({
              userId: confirmAction.userId,
              status: confirmAction.action === 'suspend' ? 'suspended' : 'active',
            });
          }
        }}
        onCancel={() => setConfirmAction(null)}
      />

      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-surface border border-border rounded-lg p-6 w-96 space-y-4">
            <h3 className="text-lg font-medium text-text-primary">Create User</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-sm text-text-secondary mb-1">Email</label>
                <input
                  type="email"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  className="bg-surface border border-border rounded px-3 py-1.5 text-sm text-text-primary w-full"
                />
              </div>
              <div>
                <label className="block text-sm text-text-secondary mb-1">Username</label>
                <input
                  type="text"
                  value={form.username}
                  onChange={(e) => setForm({ ...form, username: e.target.value })}
                  className="bg-surface border border-border rounded px-3 py-1.5 text-sm text-text-primary w-full"
                />
              </div>
              <div>
                <label className="block text-sm text-text-secondary mb-1">Password</label>
                <input
                  type="password"
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  className="bg-surface border border-border rounded px-3 py-1.5 text-sm text-text-primary w-full"
                />
              </div>
              <div>
                <label className="block text-sm text-text-secondary mb-1">Role</label>
                <select
                  value={form.role}
                  onChange={(e) => setForm({ ...form, role: e.target.value as 'admin' | 'user' })}
                  className="bg-surface border border-border rounded px-3 py-1.5 text-sm text-text-primary w-full"
                >
                  <option value="user">User</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => {
                  setShowCreateModal(false);
                  setForm({ email: '', username: '', password: '', role: 'user' });
                }}
                className="px-4 py-2 text-sm bg-surface border border-border rounded hover:bg-surface-hover text-text-primary transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => createUserMutation.mutate(form)}
                disabled={!form.email || !form.username || !form.password || createUserMutation.isPending}
                className="px-4 py-2 text-sm bg-accent hover:bg-accent-hover text-white rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {createUserMutation.isPending ? 'Creating...' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
