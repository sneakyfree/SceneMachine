/**
 * Keyboard Shortcuts Overlay Component
 *
 * Displays all available keyboard shortcuts in an overlay triggered by `?` key.
 * Helps users discover and learn keyboard shortcuts.
 */

import { memo, useState, useEffect, useCallback, useMemo } from 'react';
import { createPortal } from 'react-dom';
import { X, Search, Keyboard, Star, Clock, RotateCcw } from 'lucide-react';
import { cn } from '../lib/utils';
import {
  DEFAULT_SHORTCUTS,
  CATEGORY_LABELS,
  ShortcutCategory,
  ShortcutDefinition,
  formatShortcut,
  getShortcutsByCategory,
  getEffectiveShortcuts,
  loadCustomShortcuts,
} from '../lib/shortcuts-manager';

/**
 * Recently used shortcuts storage key
 */
const RECENT_SHORTCUTS_KEY = 'scenemachine:recent-shortcuts';
const MAX_RECENT_SHORTCUTS = 5;

/**
 * Load recently used shortcuts from storage
 */
function loadRecentShortcuts(): string[] {
  try {
    const stored = localStorage.getItem(RECENT_SHORTCUTS_KEY);
    if (stored) {
      return JSON.parse(stored);
    }
  } catch (e) {
    console.error('Failed to load recent shortcuts:', e);
  }
  return [];
}

/**
 * Save a shortcut to recent list
 */
function saveRecentShortcut(id: string): void {
  try {
    const recent = loadRecentShortcuts();
    const filtered = recent.filter((r) => r !== id);
    const updated = [id, ...filtered].slice(0, MAX_RECENT_SHORTCUTS);
    localStorage.setItem(RECENT_SHORTCUTS_KEY, JSON.stringify(updated));
  } catch (e) {
    console.error('Failed to save recent shortcut:', e);
  }
}

interface ShortcutsOverlayProps {
  /**
   * Whether the overlay is open
   */
  isOpen: boolean;

  /**
   * Called when the overlay should close
   */
  onClose: () => void;

  /**
   * Called when a shortcut is selected (for execution)
   */
  onShortcutSelect?: (shortcut: ShortcutDefinition) => void;
}

/**
 * Shortcut key badge component
 */
const ShortcutBadge = memo(function ShortcutBadge({
  shortcut,
  className,
}: {
  shortcut: ShortcutDefinition;
  className?: string;
}) {
  const formatted = formatShortcut(shortcut);
  const parts = formatted.split(/(?=[+])|(?<=\+)/);

  return (
    <div className={cn('flex items-center gap-0.5', className)}>
      {parts.map((part, index) => {
        if (part === '+') {
          return (
            <span key={index} className="text-surface-500 text-xs">
              +
            </span>
          );
        }
        return (
          <kbd
            key={index}
            className={cn(
              'inline-flex items-center justify-center min-w-[24px] h-6 px-1.5',
              'bg-surface-700 border border-surface-600 rounded',
              'text-xs font-mono text-surface-200'
            )}
          >
            {part}
          </kbd>
        );
      })}
    </div>
  );
});

/**
 * Shortcut row component
 */
const ShortcutRow = memo(function ShortcutRow({
  shortcut,
  isRecent,
  onClick,
}: {
  shortcut: ShortcutDefinition;
  isRecent?: boolean;
  onClick?: () => void;
}) {
  return (
    <div
      className={cn(
        'flex items-center justify-between py-2 px-3 rounded-lg',
        'transition-colors cursor-pointer',
        'hover:bg-surface-700/50',
        isRecent && 'bg-primary-500/5 border border-primary-500/20'
      )}
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick?.();
        }
      }}
    >
      <div className="flex items-center gap-2">
        {isRecent && <Clock className="w-3.5 h-3.5 text-primary-400" />}
        <span className="text-sm text-surface-200">{shortcut.description}</span>
        {shortcut.global && (
          <span className="px-1.5 py-0.5 bg-yellow-500/10 text-yellow-400 text-xs rounded">
            Global
          </span>
        )}
      </div>
      <ShortcutBadge shortcut={shortcut} />
    </div>
  );
});

/**
 * Category section component
 */
const CategorySection = memo(function CategorySection({
  category,
  shortcuts,
  recentIds,
  onShortcutClick,
}: {
  category: ShortcutCategory;
  shortcuts: ShortcutDefinition[];
  recentIds: Set<string>;
  onShortcutClick?: (shortcut: ShortcutDefinition) => void;
}) {
  if (shortcuts.length === 0) return null;

  return (
    <div className="mb-6">
      <h3 className="text-xs font-semibold text-surface-400 uppercase tracking-wider mb-2 px-3">
        {CATEGORY_LABELS[category]}
      </h3>
      <div className="space-y-1">
        {shortcuts.map((shortcut) => (
          <ShortcutRow
            key={shortcut.id}
            shortcut={shortcut}
            isRecent={recentIds.has(shortcut.id)}
            onClick={() => onShortcutClick?.(shortcut)}
          />
        ))}
      </div>
    </div>
  );
});

/**
 * Main shortcuts overlay component
 */
export const ShortcutsOverlay = memo(function ShortcutsOverlay({
  isOpen,
  onClose,
  onShortcutSelect,
}: ShortcutsOverlayProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<ShortcutCategory | 'all' | 'recent'>(
    'all'
  );

  // Load effective shortcuts (with customizations)
  const shortcuts = useMemo(() => {
    const customizations = loadCustomShortcuts();
    return getEffectiveShortcuts(customizations);
  }, []);

  // Load recent shortcuts
  const [recentIds, setRecentIds] = useState<Set<string>>(() => new Set(loadRecentShortcuts()));

  // Get recent shortcuts
  const recentShortcuts = useMemo(() => {
    const recent = loadRecentShortcuts();
    return recent
      .map((id) => shortcuts.find((s) => s.id === id))
      .filter((s): s is ShortcutDefinition => s !== undefined);
  }, [shortcuts]);

  // Filter shortcuts by search and category
  const filteredShortcuts = useMemo(() => {
    let filtered = shortcuts.filter((s) => s.enabled !== false);

    // Apply search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (s) =>
          s.description.toLowerCase().includes(query) ||
          s.id.toLowerCase().includes(query) ||
          formatShortcut(s).toLowerCase().includes(query)
      );
    }

    // Apply category filter
    if (selectedCategory === 'recent') {
      return recentShortcuts;
    } else if (selectedCategory !== 'all') {
      filtered = filtered.filter((s) => s.category === selectedCategory);
    }

    return filtered;
  }, [shortcuts, searchQuery, selectedCategory, recentShortcuts]);

  // Group by category
  const groupedShortcuts = useMemo(() => {
    return getShortcutsByCategory(filteredShortcuts);
  }, [filteredShortcuts]);

  // Handle escape key
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Handle shortcut click
  const handleShortcutClick = useCallback(
    (shortcut: ShortcutDefinition) => {
      saveRecentShortcut(shortcut.id);
      setRecentIds(new Set(loadRecentShortcuts()));
      onShortcutSelect?.(shortcut);
    },
    [onShortcutSelect]
  );

  // Clear search on close
  useEffect(() => {
    if (!isOpen) {
      setSearchQuery('');
      setSelectedCategory('all');
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const categories: Array<ShortcutCategory | 'all' | 'recent'> = [
    'all',
    'recent',
    'navigation',
    'project',
    'editing',
    'timeline',
    'generation',
    'playback',
    'view',
    'general',
  ];

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal */}
      <div
        className={cn(
          'relative w-full max-w-3xl max-h-[80vh] mx-4',
          'bg-surface-900 rounded-xl border border-surface-700 shadow-2xl',
          'flex flex-col overflow-hidden',
          'animate-in fade-in zoom-in-95 duration-200'
        )}
        role="dialog"
        aria-label="Keyboard Shortcuts"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-surface-700">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary-500/10 rounded-lg">
              <Keyboard className="w-5 h-5 text-primary-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-surface-100">Keyboard Shortcuts</h2>
              <p className="text-sm text-surface-400">
                Press <kbd className="px-1.5 py-0.5 bg-surface-700 rounded text-xs">?</kbd> anytime
                to show this overlay
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-surface-700 transition-colors"
            aria-label="Close"
          >
            <X className="w-5 h-5 text-surface-400" />
          </button>
        </div>

        {/* Search and filter bar */}
        <div className="px-6 py-3 border-b border-surface-800">
          <div className="flex items-center gap-4">
            {/* Search input */}
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-500" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search shortcuts..."
                className={cn(
                  'w-full pl-10 pr-4 py-2 rounded-lg',
                  'bg-surface-800 border border-surface-700',
                  'text-surface-100 placeholder-surface-500',
                  'focus:outline-none focus:ring-2 focus:ring-primary-500/50'
                )}
                autoFocus
              />
            </div>

            {/* Category filter chips */}
            <div className="flex items-center gap-1 overflow-x-auto">
              {categories.map((cat) => (
                <button
                  key={cat}
                  onClick={() => setSelectedCategory(cat)}
                  className={cn(
                    'px-3 py-1.5 rounded-lg text-sm whitespace-nowrap transition-colors',
                    selectedCategory === cat
                      ? 'bg-primary-500 text-white'
                      : 'bg-surface-800 text-surface-400 hover:bg-surface-700'
                  )}
                >
                  {cat === 'all' ? (
                    'All'
                  ) : cat === 'recent' ? (
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      Recent
                    </span>
                  ) : (
                    CATEGORY_LABELS[cat]
                  )}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Shortcuts list */}
        <div className="flex-1 overflow-y-auto p-6">
          {filteredShortcuts.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Search className="w-12 h-12 text-surface-600 mb-4" />
              <p className="text-surface-400">No shortcuts match your search</p>
              <button
                onClick={() => {
                  setSearchQuery('');
                  setSelectedCategory('all');
                }}
                className="mt-4 flex items-center gap-2 px-4 py-2 rounded-lg bg-surface-800 text-surface-300 hover:bg-surface-700 transition-colors"
              >
                <RotateCcw className="w-4 h-4" />
                Clear filters
              </button>
            </div>
          ) : selectedCategory === 'all' || selectedCategory === 'recent' ? (
            // Show grouped by category
            Object.entries(groupedShortcuts).map(([category, categoryShortcuts]) => (
              <CategorySection
                key={category}
                category={category as ShortcutCategory}
                shortcuts={categoryShortcuts}
                recentIds={recentIds}
                onShortcutClick={handleShortcutClick}
              />
            ))
          ) : (
            // Show single category
            <div className="space-y-1">
              {filteredShortcuts.map((shortcut) => (
                <ShortcutRow
                  key={shortcut.id}
                  shortcut={shortcut}
                  isRecent={recentIds.has(shortcut.id)}
                  onClick={() => handleShortcutClick(shortcut)}
                />
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-surface-700 bg-surface-800/50">
          <div className="flex items-center justify-between text-xs text-surface-500">
            <div className="flex items-center gap-4">
              <span className="flex items-center gap-1">
                <kbd className="px-1.5 py-0.5 bg-surface-700 rounded">↑</kbd>
                <kbd className="px-1.5 py-0.5 bg-surface-700 rounded">↓</kbd>
                to navigate
              </span>
              <span className="flex items-center gap-1">
                <kbd className="px-1.5 py-0.5 bg-surface-700 rounded">Enter</kbd>
                to execute
              </span>
              <span className="flex items-center gap-1">
                <kbd className="px-1.5 py-0.5 bg-surface-700 rounded">Esc</kbd>
                to close
              </span>
            </div>
            <span>
              {filteredShortcuts.length} shortcut{filteredShortcuts.length !== 1 ? 's' : ''}
            </span>
          </div>
        </div>
      </div>
    </div>,
    document.body
  );
});

/**
 * Hook to manage shortcuts overlay visibility
 */
export function useShortcutsOverlay() {
  const [isOpen, setIsOpen] = useState(false);

  // Listen for `?` key to open overlay
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Check if `?` is pressed (Shift + /)
      if (e.key === '?' && !e.ctrlKey && !e.altKey && !e.metaKey) {
        // Don't trigger in input fields
        const target = e.target as HTMLElement;
        if (
          target.tagName === 'INPUT' ||
          target.tagName === 'TEXTAREA' ||
          target.isContentEditable
        ) {
          return;
        }

        e.preventDefault();
        setIsOpen((prev) => !prev);
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  const open = useCallback(() => setIsOpen(true), []);
  const close = useCallback(() => setIsOpen(false), []);
  const toggle = useCallback(() => setIsOpen((prev) => !prev), []);

  return {
    isOpen,
    open,
    close,
    toggle,
  };
}

export default ShortcutsOverlay;
