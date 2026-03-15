import { describe, expect, test, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';

// Mock the auth hook
vi.mock('@/features/auth/useAuth', () => ({
  useAuth: vi.fn(),
}));

import { useAuth } from '@/features/auth/useAuth';
import { AuthGuard } from '@/features/auth/AuthGuard';

const mockUseAuth = useAuth as ReturnType<typeof vi.fn>;

describe('AuthGuard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('renders children when authenticated', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      checkAuth: vi.fn(),
    });
    render(
      <MemoryRouter>
        <AuthGuard>
          <div>Protected content</div>
        </AuthGuard>
      </MemoryRouter>
    );
    expect(screen.getByText('Protected content')).toBeInTheDocument();
  });

  test('shows loading state while checking auth', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      isLoading: true,
      checkAuth: vi.fn(),
    });
    render(
      <MemoryRouter>
        <AuthGuard>
          <div>Protected</div>
        </AuthGuard>
      </MemoryRouter>
    );
    // Should show loading, not the protected content
    expect(screen.queryByText('Protected')).not.toBeInTheDocument();
  });

  test('redirects to login when not authenticated', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
      checkAuth: vi.fn(),
    });
    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <Routes>
          <Route path="/dashboard" element={
            <AuthGuard><div>Protected</div></AuthGuard>
          } />
          <Route path="/login" element={<div>Login page</div>} />
        </Routes>
      </MemoryRouter>
    );
    expect(screen.getByText('Login page')).toBeInTheDocument();
  });

  test('calls checkAuth on mount', () => {
    const checkAuth = vi.fn();
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      checkAuth,
    });
    render(
      <MemoryRouter>
        <AuthGuard>
          <div>Content</div>
        </AuthGuard>
      </MemoryRouter>
    );
    expect(checkAuth).toHaveBeenCalled();
  });
});
