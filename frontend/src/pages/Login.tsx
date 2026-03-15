import { useState, FormEvent } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/features/auth/useAuth';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { login, error, clearError, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  // Redirect if already authenticated
  if (isAuthenticated) {
    const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/dashboard';
    navigate(from, { replace: true });
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    clearError();

    try {
      await login(email, password);
      const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/dashboard';
      navigate(from, { replace: true });
    } catch {
      // Error is set in the store
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="bg-surface border border-border rounded-lg p-8">
          <div className="text-center mb-8">
            <h1 className="text-xl font-bold text-text-primary">Ratatoskr Trading Platform</h1>
            <p className="text-sm text-text-secondary mt-1">Sign in to your account</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-sm text-text-secondary mb-1">
                Email
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
                className="w-full px-3 py-2 bg-background border border-border rounded text-text-primary placeholder-text-tertiary focus:outline-none focus:border-accent transition-colors"
                placeholder="admin@ratatoskr.io"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm text-text-secondary mb-1">
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
                className="w-full px-3 py-2 bg-background border border-border rounded text-text-primary placeholder-text-tertiary focus:outline-none focus:border-accent transition-colors"
                placeholder="••••••••••••"
              />
            </div>

            {error && (
              <div className="p-3 bg-error/10 border border-error/30 rounded text-error text-sm">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading || !email || !password}
              className="w-full py-2 bg-accent hover:bg-accent-hover text-white font-medium rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Signing in...' : 'Log In'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
