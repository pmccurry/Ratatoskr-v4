import { describe, expect, test, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ErrorState } from '@/components';

describe('ErrorState', () => {
  test('renders error message', () => {
    render(<ErrorState message="Failed to load." />);
    expect(screen.getByText('Failed to load.')).toBeInTheDocument();
  });

  test('renders retry button when onRetry provided', () => {
    render(<ErrorState message="Error" onRetry={() => {}} />);
    expect(screen.getByText(/retry/i)).toBeInTheDocument();
  });

  test('calls onRetry when clicked', async () => {
    const handler = vi.fn();
    render(<ErrorState message="Error" onRetry={handler} />);
    await userEvent.click(screen.getByText(/retry/i));
    expect(handler).toHaveBeenCalledOnce();
  });

  test('does not render retry button without onRetry', () => {
    render(<ErrorState message="Error" />);
    expect(screen.queryByText(/retry/i)).not.toBeInTheDocument();
  });
});
