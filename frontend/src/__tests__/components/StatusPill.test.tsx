import { describe, expect, test } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StatusPill } from '@/components/StatusPill';

describe('StatusPill', () => {
  test('renders status text', () => {
    render(<StatusPill status="enabled" />);
    expect(screen.getByText('enabled')).toBeInTheDocument();
  });

  test('enabled has success styling', () => {
    const { container } = render(<StatusPill status="enabled" />);
    expect(container.innerHTML).toContain('success');
  });

  test('disabled has neutral styling', () => {
    const { container } = render(<StatusPill status="disabled" />);
    expect(container.innerHTML).toContain('tertiary');
  });

  test('error has error styling', () => {
    const { container } = render(<StatusPill status="error" />);
    expect(container.innerHTML).toContain('error');
  });

  test('paused has warning styling', () => {
    const { container } = render(<StatusPill status="paused" />);
    expect(container.innerHTML).toContain('warning');
  });

  test('draft has warning styling', () => {
    const { container } = render(<StatusPill status="draft" />);
    expect(container.innerHTML).toContain('warning');
  });

  test('pending has warning styling', () => {
    const { container } = render(<StatusPill status="pending" />);
    expect(container.innerHTML).toContain('warning');
  });

  test('approved has success styling', () => {
    const { container } = render(<StatusPill status="approved" />);
    expect(container.innerHTML).toContain('success');
  });

  test('rejected has error styling', () => {
    const { container } = render(<StatusPill status="rejected" />);
    expect(container.innerHTML).toContain('error');
  });
});
