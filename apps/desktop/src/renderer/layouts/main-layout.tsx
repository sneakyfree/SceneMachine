/**
 * Main application layout with sidebar navigation.
 */

import { useState } from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import {
  Film,
  FolderOpen,
  Settings,
  Keyboard,
  X,
  HelpCircle,
  BarChart3,
  Archive,
  Search,
  Server,
  Eye,
} from 'lucide-react';
import { useProjectStore } from '../stores/project-store';
import { cn } from '../lib/utils';
import {
  useGlobalShortcuts,
  getAllShortcuts,
  formatShortcut,
} from '../hooks/use-keyboard-shortcuts';
import { CommandPalette, useCommandPalette } from '../components/command-palette';
import { SkipLink } from '../components/skip-link';
import { Breadcrumbs } from '../components/breadcrumbs';
import { StevenAssistant } from '../components/steven-assistant';
import { useExperienceStore } from '../stores/experience-store';
import { useTranslation } from '../i18n/use-translation';
import { LOCALES } from '../i18n';

// Keyboard shortcuts modal
function ShortcutsModal({ onClose }: { onClose: () => void }) {
  const shortcutGroups = getAllShortcuts();

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div className="bg-surface-900 rounded-xl shadow-xl max-w-md w-full max-h-[80vh] overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-surface-800">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Keyboard className="w-5 h-5 text-brand-400" />
            Keyboard Shortcuts
          </h2>
          <button
            onClick={onClose}
            className="p-1 text-surface-400 hover:text-surface-200 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 overflow-y-auto max-h-[60vh] space-y-6">
          {shortcutGroups.map((group) => (
            <div key={group.category}>
              <h3 className="text-sm font-medium text-surface-400 mb-3">{group.category}</h3>
              <div className="space-y-2">
                {group.shortcuts.map((shortcut) => (
                  <div
                    key={shortcut.description}
                    className="flex items-center justify-between py-1"
                  >
                    <span className="text-sm">{shortcut.description}</span>
                    <kbd className="px-2 py-1 bg-surface-800 rounded text-xs font-mono">
                      {formatShortcut(shortcut)}
                    </kbd>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="px-6 py-4 border-t border-surface-800">
          <p className="text-xs text-surface-500">
            Press <kbd className="px-1 bg-surface-800 rounded">?</kbd> anytime to show this dialog
          </p>
        </div>
      </div>
    </div>
  );
}

export function MainLayout() {
  const location = useLocation();
  const { currentProject, sidebarCollapsed, toggleSidebar } = useProjectStore();
  const { t, locale, setLocale } = useTranslation();
  const [showShortcuts, setShowShortcuts] = useState(false);
  const commandPalette = useCommandPalette();
  const { stevenEnabled } = useExperienceStore();

  // Initialize global keyboard shortcuts
  useGlobalShortcuts();

  return (
    <div className="flex h-screen">
      {/* Skip link for accessibility */}
      <SkipLink />

      {/* Sidebar */}
      <aside
        role="navigation"
        aria-label="Main navigation"
        className={cn('sidebar transition-all duration-200', sidebarCollapsed ? 'w-16' : 'w-64')}
      >
        {/* Logo */}
        <div className="flex items-center gap-3 px-4 py-4 border-b border-surface-800">
          <Film className="w-8 h-8 text-brand-500 flex-shrink-0" />
          {!sidebarCollapsed && <span className="font-semibold text-lg">SceneMachine</span>}
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-2 space-y-1">
          <Link
            to="/"
            className={cn('sidebar-item', location.pathname === '/' && 'sidebar-item-active')}
          >
            <FolderOpen className="w-5 h-5 flex-shrink-0" />
            {!sidebarCollapsed && <span>{t('nav.projects')}</span>}
          </Link>

          {currentProject && (
            <Link
              to={`/project/${currentProject.id}`}
              className={cn(
                'sidebar-item',
                location.pathname.startsWith('/project/') && 'sidebar-item-active'
              )}
            >
              <Film className="w-5 h-5 flex-shrink-0" />
              {!sidebarCollapsed && <span className="truncate">{currentProject.name}</span>}
            </Link>
          )}

          <Link
            to="/analytics"
            className={cn(
              'sidebar-item',
              location.pathname === '/analytics' && 'sidebar-item-active'
            )}
          >
            <BarChart3 className="w-5 h-5 flex-shrink-0" />
            {!sidebarCollapsed && <span>{t('nav.analytics')}</span>}
          </Link>

          <Link
            to="/explainability"
            className={cn(
              'sidebar-item',
              location.pathname === '/explainability' && 'sidebar-item-active'
            )}
          >
            <Eye className="w-5 h-5 flex-shrink-0" />
            {!sidebarCollapsed && <span>{t('nav.explainability')}</span>}
          </Link>

          <Link
            to="/archive"
            className={cn(
              'sidebar-item',
              location.pathname === '/archive' && 'sidebar-item-active'
            )}
          >
            <Archive className="w-5 h-5 flex-shrink-0" />
            {!sidebarCollapsed && <span>{t('nav.archive')}</span>}
          </Link>

          <Link
            to="/settings"
            className={cn(
              'sidebar-item',
              location.pathname === '/settings' && 'sidebar-item-active'
            )}
          >
            <Settings className="w-5 h-5 flex-shrink-0" />
            {!sidebarCollapsed && <span>{t('nav.settings')}</span>}
          </Link>

          <Link
            to="/admin"
            className={cn('sidebar-item', location.pathname === '/admin' && 'sidebar-item-active')}
          >
            <Server className="w-5 h-5 flex-shrink-0" />
            {!sidebarCollapsed && <span>{t('nav.systemHealth')}</span>}
          </Link>

          <Link
            to="/help"
            className={cn('sidebar-item', location.pathname === '/help' && 'sidebar-item-active')}
          >
            <HelpCircle className="w-5 h-5 flex-shrink-0" />
            {!sidebarCollapsed && <span>{t('nav.help')}</span>}
          </Link>
        </nav>

        {/* Bottom actions */}
        <div className="border-t border-surface-800">
          {/* Command Palette */}
          <button
            onClick={commandPalette.open}
            className={cn(
              'w-full flex items-center gap-3 px-4 py-3 text-surface-400 hover:text-surface-200 transition-colors',
              sidebarCollapsed && 'justify-center'
            )}
            title="Search Commands (Cmd+K)"
          >
            <Search className="w-5 h-5 flex-shrink-0" />
            {!sidebarCollapsed && (
              <div className="flex items-center justify-between flex-1">
                <span className="text-sm">{t('nav.search')}</span>
                <kbd className="px-1.5 py-0.5 bg-surface-800 rounded text-xs font-mono">
                  {navigator.platform.includes('Mac') ? '⌘' : 'Ctrl'}K
                </kbd>
              </div>
            )}
          </button>

          {/* Keyboard shortcuts */}
          <button
            onClick={() => setShowShortcuts(true)}
            className={cn(
              'w-full flex items-center gap-3 px-4 py-3 text-surface-400 hover:text-surface-200 transition-colors',
              sidebarCollapsed && 'justify-center'
            )}
            title="Keyboard Shortcuts"
          >
            <Keyboard className="w-5 h-5 flex-shrink-0" />
            {!sidebarCollapsed && <span className="text-sm">{t('nav.shortcuts')}</span>}
          </button>

          {/* Language selector (international launch) */}
          {!sidebarCollapsed && (
            <div className="px-4 py-3 flex flex-wrap items-center gap-2" aria-label={t('common.language')}>
              {LOCALES.map((l) => (
                <button
                  key={l.code}
                  onClick={() => setLocale(l.code)}
                  className={cn(
                    'flex items-center gap-1 px-2 py-1 rounded text-xs transition-colors',
                    locale === l.code
                      ? 'bg-brand-500/20 text-brand-300'
                      : 'text-surface-400 hover:bg-surface-800'
                  )}
                  title={l.label}
                  aria-pressed={locale === l.code}
                >
                  <span aria-hidden>{l.flag}</span>
                  <span>{l.code.toUpperCase()}</span>
                </button>
              ))}
            </div>
          )}

          {/* Collapse toggle */}
          <button
            onClick={toggleSidebar}
            className="w-full p-4 text-surface-400 hover:text-surface-200 transition-colors"
          >
            <svg
              className={cn(
                'w-5 h-5 transition-transform mx-auto',
                sidebarCollapsed && 'rotate-180'
              )}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M11 19l-7-7 7-7m8 14l-7-7 7-7"
              />
            </svg>
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main
        id="main-content"
        role="main"
        aria-label="Main content"
        className="flex-1 flex flex-col bg-surface-950"
      >
        {/* Breadcrumb navigation bar */}
        <div className="shrink-0 px-6 py-3 border-b border-surface-800 bg-surface-900/50">
          <Breadcrumbs />
        </div>

        {/* Page content */}
        <div className="flex-1 overflow-auto">
          <Outlet />
        </div>
      </main>

      {/* Keyboard shortcuts modal */}
      {showShortcuts && <ShortcutsModal onClose={() => setShowShortcuts(false)} />}

      {/* Command palette */}
      <CommandPalette isOpen={commandPalette.isOpen} onClose={commandPalette.close} />

      {/* Steven AI Assistant - inside router context */}
      {stevenEnabled && <StevenAssistant />}
    </div>
  );
}
