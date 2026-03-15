import { describe, expect, test } from 'vitest';
import { render, screen } from '@testing-library/react';
import { PriceValue } from '@/components';

describe('PriceValue', () => {
  test('renders formatted equity price', () => {
    render(<PriceValue value={150.5} />);
    expect(screen.getByText(/\$150\.50/)).toBeInTheDocument();
  });

  test('renders forex price without $', () => {
    render(<PriceValue value={1.2345} market="forex" />);
    expect(screen.getByText(/1\.23450/)).toBeInTheDocument();
  });

  test('uses monospace font', () => {
    const { container } = render(<PriceValue value={100} />);
    expect(container.innerHTML).toContain('mono');
  });

  test('renders zero price', () => {
    render(<PriceValue value={0} />);
    expect(screen.getByText(/\$0\.00/)).toBeInTheDocument();
  });
});
