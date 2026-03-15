import { create } from 'zustand';
import api from '@/lib/api';
import type { User, TokenResponse } from '@/types/auth';

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isAdmin: boolean;
  isLoading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<boolean>;
  checkAuth: () => Promise<void>;
  clearError: () => void;
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: !!localStorage.getItem('access_token'),
  isAdmin: false,
  isLoading: true,
  error: null,

  login: async (email: string, password: string) => {
    set({ error: null, isLoading: true });
    try {
      const response = await api.post<TokenResponse>('/auth/login', { email, password });
      const tokens = response.data;
      localStorage.setItem('access_token', tokens.accessToken);
      localStorage.setItem('refresh_token', tokens.refreshToken);

      // Fetch user profile
      const userResponse = await api.get<User>('/auth/me');
      const user = userResponse.data;
      set({
        user,
        isAuthenticated: true,
        isAdmin: user.role === 'admin',
        isLoading: false,
      });
    } catch (err: unknown) {
      const message =
        err && typeof err === 'object' && 'message' in err
          ? (err as { message: string }).message
          : 'Login failed';
      set({ error: message, isLoading: false });
      throw err;
    }
  },

  logout: async () => {
    try {
      await api.post('/auth/logout');
    } catch {
      // Ignore logout errors
    }
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    set({ user: null, isAuthenticated: false, isAdmin: false, isLoading: false });
    window.location.href = '/login';
  },

  refreshToken: async () => {
    try {
      const refreshToken = localStorage.getItem('refresh_token');
      if (!refreshToken) return false;

      const response = await api.post<TokenResponse>('/auth/refresh', { refreshToken });
      const tokens = response.data;
      localStorage.setItem('access_token', tokens.accessToken);
      localStorage.setItem('refresh_token', tokens.refreshToken);
      return true;
    } catch {
      return false;
    }
  },

  checkAuth: async () => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      set({ isAuthenticated: false, isLoading: false, user: null });
      return;
    }

    try {
      const response = await api.get<User>('/auth/me');
      const user = response.data;
      set({
        user,
        isAuthenticated: true,
        isAdmin: user.role === 'admin',
        isLoading: false,
      });
    } catch {
      set({ isAuthenticated: false, isLoading: false, user: null, isAdmin: false });
    }
  },

  clearError: () => set({ error: null }),
}));
