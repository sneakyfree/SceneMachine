/**
 * Keyboard shortcuts hook.
 */

import { useEffect, useCallback, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useProjectStore } from '../stores/project-store';

// Shortcut definition
interface Shortcut {
  key: string;
  ctrl?: boolean;
  alt?: boolean;
  shift?: boolean;
  meta?: boolean;
  description: string;
  action: () => void;
  global?: boolean; // Works even in inputs
}

// Check if key combo matches
function matchesShortcut(event: KeyboardEvent, shortcut: Shortcut): boolean {
  const key = event.key.toLowerCase();
  const ctrl = event.ctrlKey || event.metaKey; // Handle both Ctrl and Cmd
  const alt = event.altKey;
  const shift = event.shiftKey;

  return (
    key === shortcut.key.toLowerCase() &&
    (shortcut.ctrl ?? false) === ctrl &&
    (shortcut.alt ?? false) === alt &&
    (shortcut.shift ?? false) === shift
  );
}

// Check if we're in an input element
function isInInput(element: EventTarget | null): boolean {
  if (!element || !(element instanceof HTMLElement)) return false;

  const tagName = element.tagName.toLowerCase();
  const isInput = tagName === 'input' || tagName === 'textarea' || tagName === 'select';
  const isEditable = element.isContentEditable;

  return isInput || isEditable;
}

// Hook for using keyboard shortcuts
export function useKeyboardShortcuts(shortcuts: Shortcut[]) {
  const shortcutsRef = useRef(shortcuts);
  shortcutsRef.current = shortcuts;

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Check if in input (unless shortcut is global)
      const inInput = isInInput(event.target);

      for (const shortcut of shortcutsRef.current) {
        if (matchesShortcut(event, shortcut)) {
          // Skip if in input and shortcut isn't global
          if (inInput && !shortcut.global) continue;

          event.preventDefault();
          shortcut.action();
          return;
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);
}

// Global application shortcuts
export function useGlobalShortcuts() {
  const navigate = useNavigate();
  const location = useLocation();
  const { currentProject, toggleSidebar } = useProjectStore();

  // Save handler - trigger save across the app
  const handleSave = useCallback(() => {
    // Dispatch custom event that pages can listen to
    window.dispatchEvent(new CustomEvent('app:save'));
  }, []);

  // Navigation shortcuts
  const shortcuts: Shortcut[] = [
    // Navigation
    {
      key: 'h',
      ctrl: true,
      description: 'Go to Home',
      action: () => navigate('/'),
    },
    {
      key: 's',
      ctrl: true,
      description: 'Save',
      action: handleSave,
      global: true,
    },
    {
      key: ',',
      ctrl: true,
      description: 'Open Settings',
      action: () => navigate('/settings'),
    },
    {
      key: 'b',
      ctrl: true,
      description: 'Toggle Sidebar',
      action: toggleSidebar,
    },

    // Project shortcuts (when in project context)
    ...(currentProject
      ? [
          {
            key: '1',
            ctrl: true,
            description: 'Go to Project Overview',
            action: () => navigate(`/project/${currentProject.id}`),
          },
          {
            key: '2',
            ctrl: true,
            description: 'Go to Characters',
            action: () => navigate(`/project/${currentProject.id}/characters`),
          },
          {
            key: '3',
            ctrl: true,
            description: 'Go to Scene Planning',
            action: () => navigate(`/project/${currentProject.id}/scenes`),
          },
          {
            key: '4',
            ctrl: true,
            description: 'Go to Generation',
            action: () => navigate(`/project/${currentProject.id}/generate`),
          },
          {
            key: '5',
            ctrl: true,
            description: 'Go to Export',
            action: () => navigate(`/project/${currentProject.id}/export`),
          },
        ]
      : []),

    // Escape to close modals/dialogs
    {
      key: 'Escape',
      description: 'Close/Cancel',
      action: () => {
        window.dispatchEvent(new CustomEvent('app:escape'));
      },
      global: true,
    },
  ];

  useKeyboardShortcuts(shortcuts);

  return shortcuts;
}

// Get formatted shortcut string for display
export function formatShortcut(shortcut: Shortcut): string {
  const parts: string[] = [];

  // Use ⌘ on Mac, Ctrl on others
  const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;

  if (shortcut.ctrl) parts.push(isMac ? '⌘' : 'Ctrl');
  if (shortcut.alt) parts.push(isMac ? '⌥' : 'Alt');
  if (shortcut.shift) parts.push('⇧');

  // Format the key
  let key = shortcut.key;
  if (key === ' ') key = 'Space';
  if (key === 'Escape') key = 'Esc';
  if (key.length === 1) key = key.toUpperCase();

  parts.push(key);

  return parts.join(isMac ? '' : '+');
}

// All available shortcuts for help display
export function getAllShortcuts(): { category: string; shortcuts: Shortcut[] }[] {
  return [
    {
      category: 'Navigation',
      shortcuts: [
        { key: 'h', ctrl: true, description: 'Go to Home', action: () => {} },
        { key: ',', ctrl: true, description: 'Open Settings', action: () => {} },
        { key: 'b', ctrl: true, description: 'Toggle Sidebar', action: () => {} },
      ],
    },
    {
      category: 'Project',
      shortcuts: [
        { key: '1', ctrl: true, description: 'Project Overview', action: () => {} },
        { key: '2', ctrl: true, description: 'Characters', action: () => {} },
        { key: '3', ctrl: true, description: 'Scene Planning', action: () => {} },
        { key: '4', ctrl: true, description: 'Generation', action: () => {} },
        { key: '5', ctrl: true, description: 'Export', action: () => {} },
      ],
    },
    {
      category: 'General',
      shortcuts: [
        { key: 's', ctrl: true, description: 'Save', action: () => {}, global: true },
        { key: 'Escape', description: 'Close/Cancel', action: () => {}, global: true },
      ],
    },
  ];
}
