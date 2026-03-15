import { describe, expect, test, beforeEach } from 'vitest';
import { useUIStore } from '@/lib/store';

describe('UIStore', () => {
  beforeEach(() => {
    // Reset store between tests
    useUIStore.setState({
      sidebarCollapsed: false,
      equityCurvePeriod: '30d',
      activityFeedPaused: false,
    });
  });

  test('sidebar starts expanded', () => {
    expect(useUIStore.getState().sidebarCollapsed).toBe(false);
  });

  test('toggleSidebar flips state to collapsed', () => {
    useUIStore.getState().toggleSidebar();
    expect(useUIStore.getState().sidebarCollapsed).toBe(true);
  });

  test('toggleSidebar flips back to expanded', () => {
    useUIStore.getState().toggleSidebar();
    useUIStore.getState().toggleSidebar();
    expect(useUIStore.getState().sidebarCollapsed).toBe(false);
  });

  test('equityCurvePeriod defaults to 30d', () => {
    expect(useUIStore.getState().equityCurvePeriod).toBe('30d');
  });

  test('setEquityCurvePeriod updates period', () => {
    useUIStore.getState().setEquityCurvePeriod('7d');
    expect(useUIStore.getState().equityCurvePeriod).toBe('7d');
  });

  test('activityFeedPaused defaults to false', () => {
    expect(useUIStore.getState().activityFeedPaused).toBe(false);
  });

  test('toggleActivityFeed flips paused state', () => {
    useUIStore.getState().toggleActivityFeed();
    expect(useUIStore.getState().activityFeedPaused).toBe(true);
  });
});
