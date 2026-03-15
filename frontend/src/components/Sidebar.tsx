import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  LineChart,
  Zap,
  FileText,
  Briefcase,
  Shield,
  Monitor,
  Settings,
  ChevronLeft,
  ChevronRight,
  LogOut,
  User,
} from 'lucide-react';
import { useUIStore } from '@/lib/store';
import { useAuth } from '@/features/auth/useAuth';
import { SIDEBAR_WIDTH } from '@/lib/constants';

const NAV_ITEMS = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/strategies', icon: LineChart, label: 'Strategies' },
  { to: '/signals', icon: Zap, label: 'Signals' },
  { to: '/orders', icon: FileText, label: 'Orders' },
  { to: '/portfolio', icon: Briefcase, label: 'Portfolio' },
  { to: '/risk', icon: Shield, label: 'Risk' },
];

const ADMIN_ITEMS = [
  { to: '/system', icon: Monitor, label: 'System' },
  { to: '/settings', icon: Settings, label: 'Settings' },
];

export function Sidebar() {
  const collapsed = useUIStore((s) => s.sidebarCollapsed);
  const toggle = useUIStore((s) => s.toggleSidebar);
  const { user, isAdmin, logout } = useAuth();
  const width = collapsed ? SIDEBAR_WIDTH.collapsed : SIDEBAR_WIDTH.expanded;

  const linkClass = (isActive: boolean) =>
    `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
      isActive
        ? 'bg-accent/10 text-accent'
        : 'text-text-secondary hover:text-text-primary hover:bg-surface-hover'
    }`;

  return (
    <aside
      className="fixed top-0 left-0 h-full bg-surface border-r border-border flex flex-col z-40 transition-all duration-200"
      style={{ width }}
    >
      {/* Logo */}
      <div className="h-14 flex items-center px-4 border-b border-border">
        {!collapsed && (
          <span className="text-base font-bold text-text-primary truncate">Ratatoskr</span>
        )}
        {collapsed && (
          <span className="text-base font-bold text-accent mx-auto">R</span>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto p-3 space-y-1">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) => linkClass(isActive)}
            title={collapsed ? item.label : undefined}
          >
            <item.icon size={20} className="shrink-0" />
            {!collapsed && <span>{item.label}</span>}
          </NavLink>
        ))}

        {isAdmin && (
          <>
            <div className="my-3 border-t border-border" />
            {ADMIN_ITEMS.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) => linkClass(isActive)}
                title={collapsed ? item.label : undefined}
              >
                <item.icon size={20} className="shrink-0" />
                {!collapsed && <span>{item.label}</span>}
              </NavLink>
            ))}
          </>
        )}
      </nav>

      {/* Footer */}
      <div className="border-t border-border p-3 space-y-2">
        {/* Collapse toggle */}
        <button
          onClick={toggle}
          className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-text-secondary hover:text-text-primary hover:bg-surface-hover transition-colors w-full"
        >
          {collapsed ? <ChevronRight size={20} /> : <ChevronLeft size={20} />}
          {!collapsed && <span>Collapse</span>}
        </button>

        {/* User info */}
        {user && !collapsed && (
          <div className="flex items-center gap-3 px-3 py-2">
            <User size={20} className="text-text-tertiary shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm text-text-primary truncate">{user.username}</p>
              <p className="text-sm text-text-tertiary">{user.role}</p>
            </div>
          </div>
        )}

        {/* Logout */}
        <button
          onClick={logout}
          className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-text-secondary hover:text-error hover:bg-surface-hover transition-colors w-full"
          title={collapsed ? 'Log out' : undefined}
        >
          <LogOut size={20} className="shrink-0" />
          {!collapsed && <span>Log Out</span>}
        </button>
      </div>
    </aside>
  );
}
