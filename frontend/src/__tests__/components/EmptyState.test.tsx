import { describe, expect, test, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { EmptyState } from '@/components';

describe('EmptyState', () => {
  test('renders message text', () => {
    render(<EmptyState message="No strategies yet." />);
    expect(screen.getByText('No strategies yet.')).toBeInTheDocument();
  });

  test('renders action button when provided', () => {
    render(<EmptyState message="No data." action={{ label: 'Create', onClick: () => {} }} />);
    expect(screen.getByText('Create')).toBeInTheDocument();
  });

  test('calls onClick when action button clicked', async () => {
    const handler = vi.fn();
    render(<EmptyState message="No data." action={{ label: 'Create', onClick: handler }} />);
    await userEvent.click(screen.getByText('Create'));
    expect(handler).toHaveBeenCalledOnce();
  });

  test('does not render button without action prop', () => {
    render(<EmptyState message="No data." />);
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });
});
