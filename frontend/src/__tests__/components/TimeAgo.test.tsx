import { describe, expect, test, vi, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { TimeAgo } from '@/components';

describe('TimeAgo', () => {
  // Clear any intervals set by the component
  afterEach(() => {
    vi.restoreAllMocks();
  });

  test('renders relative time for recent timestamp', () => {
    const now = new Date().toISOString();
    render(<TimeAgo value={now} />);
    // Should show "0s ago" or similar
    expect(screen.getByText(/\d+s ago/)).toBeInTheDocument();
  });

  test('renders minutes for older timestamp', () => {
    const fiveMinAgo = new Date(Date.now() - 5 * 60 * 1000).toISOString();
    render(<TimeAgo value={fiveMinAgo} />);
    expect(screen.getByText('5m ago')).toBeInTheDocument();
  });

  test('renders hours for old timestamp', () => {
    const twoHoursAgo = new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString();
    render(<TimeAgo value={twoHoursAgo} />);
    expect(screen.getByText('2h ago')).toBeInTheDocument();
  });

  test('renders days for very old timestamp', () => {
    const threeDaysAgo = new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString();
    render(<TimeAgo value={threeDaysAgo} />);
    expect(screen.getByText('3d ago')).toBeInTheDocument();
  });
});
