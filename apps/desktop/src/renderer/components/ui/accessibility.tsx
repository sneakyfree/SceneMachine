/**
 * Accessibility Components
 * Keyboard navigation, skip links, focus management, and ARIA utilities
 */

import React from 'react';
import { cn } from '../../lib/utils';

// =====================
// Skip Links
// =====================

export const SkipLinks: React.FC<{
  links?: { id: string; label: string }[];
}> = ({
  links = [
    { id: 'main-content', label: 'Skip to main content' },
    { id: 'main-nav', label: 'Skip to navigation' },
  ],
}) => (
  <div className="sr-only focus-within:not-sr-only">
    {links.map((link) => (
      <a
        key={link.id}
        href={`#${link.id}`}
        className="absolute top-0 left-0 z-[100] bg-brand-500 text-white px-4 py-2 rounded-br-lg focus:outline-none focus:ring-2 focus:ring-brand-400"
      >
        {link.label}
      </a>
    ))}
  </div>
);

// =====================
// Focus Trap
// =====================

export const FocusTrap: React.FC<{
  children: React.ReactNode;
  active?: boolean;
  className?: string;
}> = ({ children, active = true, className }) => {
  const containerRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (!active) return;

    const container = containerRef.current;
    if (!container) return;

    const focusableElements = container.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    // Focus first element
    firstElement?.focus();

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return;

      if (e.shiftKey) {
        if (document.activeElement === firstElement) {
          e.preventDefault();
          lastElement?.focus();
        }
      } else {
        if (document.activeElement === lastElement) {
          e.preventDefault();
          firstElement?.focus();
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [active]);

  return (
    <div ref={containerRef} className={className}>
      {children}
    </div>
  );
};

// =====================
// Focus Ring
// =====================

export const focusRingStyles = `
.focus-ring:focus {
  outline: none;
  box-shadow: 0 0 0 2px var(--brand-500, #3b82f6);
}

.focus-ring:focus:not(:focus-visible) {
  box-shadow: none;
}

.focus-ring:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px var(--brand-500, #3b82f6);
}
`;

// =====================
// Keyboard Shortcuts
// =====================

interface KeyboardShortcut {
  key: string;
  ctrl?: boolean;
  shift?: boolean;
  alt?: boolean;
  meta?: boolean;
  description: string;
  handler: () => void;
  scope?: string;
}

const KeyboardShortcutsContext = React.createContext<{
  shortcuts: KeyboardShortcut[];
  registerShortcut: (shortcut: KeyboardShortcut) => void;
  unregisterShortcut: (key: string) => void;
} | null>(null);

export const KeyboardShortcutsProvider: React.FC<{
  children: React.ReactNode;
}> = ({ children }) => {
  const [shortcuts, setShortcuts] = React.useState<KeyboardShortcut[]>([]);

  const registerShortcut = React.useCallback((shortcut: KeyboardShortcut) => {
    setShortcuts((prev) => [...prev.filter((s) => s.key !== shortcut.key), shortcut]);
  }, []);

  const unregisterShortcut = React.useCallback((key: string) => {
    setShortcuts((prev) => prev.filter((s) => s.key !== key));
  }, []);

  // Global keyboard handler
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger shortcuts when typing in inputs
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement ||
        e.target instanceof HTMLSelectElement
      ) {
        return;
      }

      for (const shortcut of shortcuts) {
        const keyMatch = e.key.toLowerCase() === shortcut.key.toLowerCase();
        const ctrlMatch = !!shortcut.ctrl === (e.ctrlKey || e.metaKey);
        const shiftMatch = !!shortcut.shift === e.shiftKey;
        const altMatch = !!shortcut.alt === e.altKey;

        if (keyMatch && ctrlMatch && shiftMatch && altMatch) {
          e.preventDefault();
          shortcut.handler();
          return;
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [shortcuts]);

  return (
    <KeyboardShortcutsContext.Provider value={{ shortcuts, registerShortcut, unregisterShortcut }}>
      {children}
    </KeyboardShortcutsContext.Provider>
  );
};

// Hook to register keyboard shortcuts
export function useKeyboardShortcut(
  shortcut: Omit<KeyboardShortcut, 'handler'>,
  handler: () => void
) {
  const context = React.useContext(KeyboardShortcutsContext);

  React.useEffect(() => {
    if (!context) return;
    context.registerShortcut({ ...shortcut, handler });
    return () => context.unregisterShortcut(shortcut.key);
  }, [context, shortcut.key, handler]);
}

// Hook to get all shortcuts
export function useKeyboardShortcuts() {
  const context = React.useContext(KeyboardShortcutsContext);
  return context?.shortcuts ?? [];
}

// Keyboard shortcuts help modal
export const KeyboardShortcutsHelp: React.FC<{
  isOpen: boolean;
  onClose: () => void;
}> = ({ isOpen, onClose }) => {
  const shortcuts = useKeyboardShortcuts();

  // Group by scope
  const grouped = React.useMemo(() => {
    const groups: Record<string, KeyboardShortcut[]> = {};
    shortcuts.forEach((s) => {
      const scope = s.scope || 'General';
      if (!groups[scope]) groups[scope] = [];
      groups[scope].push(s);
    });
    return groups;
  }, [shortcuts]);

  if (!isOpen) return null;

  const formatKey = (s: KeyboardShortcut): string => {
    const parts: string[] = [];
    if (s.ctrl) parts.push('⌘');
    if (s.shift) parts.push('⇧');
    if (s.alt) parts.push('⌥');
    parts.push(s.key.toUpperCase());
    return parts.join(' + ');
  };

  return (
    <FocusTrap>
      <div
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
        onClick={onClose}
      >
        <div
          className="bg-surface-900 rounded-xl p-6 max-w-md w-full max-h-[80vh] overflow-y-auto"
          onClick={(e) => e.stopPropagation()}
          role="dialog"
          aria-labelledby="shortcuts-title"
          aria-modal="true"
        >
          <h2 id="shortcuts-title" className="text-lg font-bold mb-4">
            Keyboard Shortcuts
          </h2>

          {Object.entries(grouped).map(([scope, items]) => (
            <div key={scope} className="mb-4">
              <h3 className="text-sm font-medium text-surface-400 mb-2">{scope}</h3>
              <div className="space-y-1">
                {items.map((s) => (
                  <div key={s.key} className="flex items-center justify-between py-1">
                    <span className="text-sm">{s.description}</span>
                    <kbd className="px-2 py-1 bg-surface-800 rounded text-xs font-mono">
                      {formatKey(s)}
                    </kbd>
                  </div>
                ))}
              </div>
            </div>
          ))}

          <button
            onClick={onClose}
            className="w-full mt-4 px-4 py-2 bg-surface-800 hover:bg-surface-700 rounded-lg transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </FocusTrap>
  );
};

// =====================
// ARIA Live Regions
// =====================

export const LiveRegion: React.FC<{
  children: React.ReactNode;
  politeness?: 'polite' | 'assertive' | 'off';
  atomic?: boolean;
  relevant?: 'additions' | 'removals' | 'text' | 'all';
}> = ({ children, politeness = 'polite', atomic = true, relevant = 'additions' }) => (
  <div aria-live={politeness} aria-atomic={atomic} aria-relevant={relevant} className="sr-only">
    {children}
  </div>
);

// Hook for announcing messages to screen readers
export function useAnnounce() {
  const [message, setMessage] = React.useState('');

  const announce = React.useCallback((text: string) => {
    setMessage('');
    // Small delay to ensure change is detected
    setTimeout(() => setMessage(text), 100);
  }, []);

  const Announcer = React.useCallback(() => <LiveRegion>{message}</LiveRegion>, [message]);

  return { announce, Announcer };
}

// =====================
// Visually Hidden
// =====================

export const VisuallyHidden: React.FC<{
  children: React.ReactNode;
  as?: keyof JSX.IntrinsicElements;
}> = ({ children, as: Component = 'span' }) => (
  // @ts-ignore
  <Component className="sr-only">{children}</Component>
);

// =====================
// Focus Management
// =====================

export function useFocusReturn() {
  const previousActiveElement = React.useRef<HTMLElement | null>(null);

  React.useEffect(() => {
    previousActiveElement.current = document.activeElement as HTMLElement;
    return () => {
      previousActiveElement.current?.focus();
    };
  }, []);
}

// =====================
// High Contrast Mode
// =====================

export function useHighContrast() {
  const [isHighContrast, setIsHighContrast] = React.useState(false);

  React.useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-contrast: more)');
    setIsHighContrast(mediaQuery.matches);

    const handler = (e: MediaQueryListEvent) => setIsHighContrast(e.matches);
    mediaQuery.addEventListener('change', handler);
    return () => mediaQuery.removeEventListener('change', handler);
  }, []);

  return isHighContrast;
}

// =====================
// Reduced Motion
// =====================

export function useReducedMotion() {
  const [prefersReducedMotion, setPrefersReducedMotion] = React.useState(false);

  React.useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    setPrefersReducedMotion(mediaQuery.matches);

    const handler = (e: MediaQueryListEvent) => setPrefersReducedMotion(e.matches);
    mediaQuery.addEventListener('change', handler);
    return () => mediaQuery.removeEventListener('change', handler);
  }, []);

  return prefersReducedMotion;
}

// =====================
// Accessible Icon Button
// =====================

export const IconButton: React.FC<{
  icon: React.ReactNode;
  label: string;
  onClick?: () => void;
  disabled?: boolean;
  className?: string;
}> = ({ icon, label, onClick, disabled, className }) => (
  <button
    onClick={onClick}
    disabled={disabled}
    className={cn(
      'p-2 rounded-lg transition-colors focus-ring',
      disabled ? 'opacity-50 cursor-not-allowed' : 'hover:bg-surface-700',
      className
    )}
    aria-label={label}
    title={label}
  >
    {icon}
  </button>
);
