import { describe, expect, test } from 'vitest';
import { render, screen } from '@testing-library/react';
import { PnlValue } from '@/components';

describe('PnlValue', () => {
  test('renders positive value with + sign', () => {
    render(<PnlValue value={100} />);
    expect(screen.getByText(/\+\$100/)).toBeInTheDocument();
  });

  test('renders negative value with - sign', () => {
    render(<PnlValue value={-100} />);
    expect(screen.getByText(/-\$100/)).toBeInTheDocument();
  });

  test('positive value has success color', () => {
    const { container } = render(<PnlValue value={50} />);
    expect(container.innerHTML).toContain('success');
  });

  test('negative value has error color', () => {
    const { container } = render(<PnlValue value={-50} />);
    expect(container.innerHTML).toContain('error');
  });

  test('uses monospace font', () => {
    const { container } = render(<PnlValue value={50} />);
    expect(container.innerHTML).toContain('mono');
  });

  test('zero value renders as positive', () => {
    render(<PnlValue value={0} />);
    expect(screen.getByText(/\+\$0/)).toBeInTheDocument();
  });
});
