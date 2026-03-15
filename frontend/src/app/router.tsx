import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { AppShell } from '@/layouts/AppShell';
import { AuthLayout } from '@/layouts/AuthLayout';
import { AuthGuard } from '@/features/auth/AuthGuard';
import { AdminGuard } from '@/features/auth/AdminGuard';

import Login from '@/pages/Login';
import Dashboard from '@/pages/Dashboard';
import StrategyList from '@/pages/StrategyList';
import StrategyBuilder from '@/pages/StrategyBuilder';
import StrategyDetail from '@/pages/StrategyDetail';
import Signals from '@/pages/Signals';
import Orders from '@/pages/Orders';
import Portfolio from '@/pages/Portfolio';
import Risk from '@/pages/Risk';
import System from '@/pages/System';
import SettingsPage from '@/pages/Settings';
import NotFound from '@/pages/NotFound';

function AdminLayout() {
  return (
    <AdminGuard>
      <Outlet />
    </AdminGuard>
  );
}

export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public routes */}
        <Route element={<AuthLayout />}>
          <Route path="/login" element={<Login />} />
        </Route>

        {/* Protected routes */}
        <Route
          element={
            <AuthGuard>
              <AppShell />
            </AuthGuard>
          }
        >
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/strategies" element={<StrategyList />} />
          <Route path="/strategies/new" element={<StrategyBuilder />} />
          <Route path="/strategies/:id" element={<StrategyDetail />} />
          <Route path="/strategies/:id/edit" element={<StrategyBuilder />} />
          <Route path="/signals" element={<Signals />} />
          <Route path="/orders" element={<Orders />} />
          <Route path="/portfolio" element={<Portfolio />} />
          <Route path="/risk" element={<Risk />} />

          {/* Admin routes */}
          <Route element={<AdminLayout />}>
            <Route path="/system" element={<System />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/settings/risk" element={<SettingsPage />} />
            <Route path="/settings/accounts" element={<SettingsPage />} />
            <Route path="/settings/users" element={<SettingsPage />} />
            <Route path="/settings/alerts" element={<SettingsPage />} />
            <Route path="/settings/system" element={<SettingsPage />} />
          </Route>
        </Route>

        {/* 404 */}
        <Route path="*" element={<NotFound />} />
      </Routes>
    </BrowserRouter>
  );
}
