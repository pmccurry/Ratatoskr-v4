import { describe, expect, test } from 'vitest';
import { render, screen } from '@testing-library/react';
import { PercentValue } from '@/components';

describe('PercentValue', () => {
  test('renders formatted percent', () => {
    render(<PercentValue value={12.5} />);
    expect(screen.getByText(/12\.50%/)).toBeInTheDocument();
  });

  test('renders negative percent', () => {
    render(<PercentValue value={-5.5} />);
    expect(screen.getByText(/-5\.50%/)).toBeInTheDocument();
  });

  test('colored positive has success class', () => {
    const { container } = render(<PercentValue value={10} colored />);
    expect(container.innerHTML).toContain('success');
  });

  test('colored negative has error class', () => {
    const { container } = render(<PercentValue value={-10} colored />);
    expect(container.innerHTML).toContain('error');
  });

  test('uses monospace font', () => {
    const { container } = render(<PercentValue value={5} />);
    expect(container.innerHTML).toContain('mono');
  });
});
