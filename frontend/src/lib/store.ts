import { create } from 'zustand';

interface UIStore {
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;

  equityCurvePeriod: '1d' | '7d' | '30d' | '90d' | 'ytd' | 'all';
  setEquityCurvePeriod: (period: '1d' | '7d' | '30d' | '90d' | 'ytd' | 'all') => void;

  activityFeedPaused: boolean;
  toggleActivityFeed: () => void;
}

export const useUIStore = create<UIStore>((set) => ({
  sidebarCollapsed: false,
  toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),

  equityCurvePeriod: '30d',
  setEquityCurvePeriod: (period) => set({ equityCurvePeriod: period }),

  activityFeedPaused: false,
  toggleActivityFeed: () =>
    set((state) => ({ activityFeedPaused: !state.activityFeedPaused })),
}));
