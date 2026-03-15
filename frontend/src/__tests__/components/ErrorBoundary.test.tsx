import { describe, expect, test, vi, afterAll } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ErrorBoundary } from '@/components/ErrorBoundary';

// Suppress React error boundary console output during tests
const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
afterAll(() => consoleSpy.mockRestore());

function ThrowingComponent(): JSX.Element {
  throw new Error('Test crash');
}

describe('ErrorBoundary', () => {
  test('renders children when no error', () => {
    render(
      <ErrorBoundary>
        <div>Child content</div>
      </ErrorBoundary>
    );
    expect(screen.getByText('Child content')).toBeInTheDocument();
  });

  test('renders fallback on child error', () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent />
      </ErrorBoundary>
    );
    expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
  });

  test('shows error message in fallback', () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent />
      </ErrorBoundary>
    );
    expect(screen.getByText('Test crash')).toBeInTheDocument();
  });

  test('try again button exists', () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent />
      </ErrorBoundary>
    );
    expect(screen.getByText(/try again/i)).toBeInTheDocument();
  });

  test('renders custom fallback when provided', () => {
    render(
      <ErrorBoundary fallback={<div>Custom error</div>}>
        <ThrowingComponent />
      </ErrorBoundary>
    );
    expect(screen.getByText('Custom error')).toBeInTheDocument();
  });
});
