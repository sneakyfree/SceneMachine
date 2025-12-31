/**
 * Enhanced keyboard shortcuts hook with customization support.
 */

import { useEffect, useCallback, useRef, useState, useMemo } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useProjectStore } from '../stores/project-store';
import {
  ShortcutDefinition,
  ShortcutCustomization,
  DEFAULT_SHORTCUTS,
  CATEGORY_LABELS,
  loadCustomShortcuts,
  saveCustomShortcuts,
  getEffectiveShortcuts,
  matchesShortcut,
  formatShortcut,
  getShortcutsByCategory,
  findConflicts,
  resetShortcut,
  resetAllShortcuts,
} from '../lib/shortcuts-manager';

// Re-export types and utilities
export type { ShortcutDefinition, ShortcutCustomization };
export {
  formatShortcut,
  getShortcutsByCategory,
  findConflicts,
  CATEGORY_LABELS,
  DEFAULT_SHORTCUTS,
};

// Legacy Shortcut interface for backward compatibility
export interface Shortcut {
  key: string;
  ctrl?: boolean;
  alt?: boolean;
  shift?: boolean;
  meta?: boolean;
  description: string;
  action: () => void;
  global?: boolean;
}

// Check if we're in an input element
function isInInput(element: EventTarget | null): boolean {
  if (!element || !(element instanceof HTMLElement)) return false;

  const tagName = element.tagName.toLowerCase();
  const isInput = tagName === 'input' || tagName === 'textarea' || tagName === 'select';
  const isEditable = element.isContentEditable;

  return isInput || isEditable;
}

// Hook for using keyboard shortcuts (legacy API)
export function useKeyboardShortcuts(shortcuts: Shortcut[]) {
  const shortcutsRef = useRef(shortcuts);
  shortcutsRef.current = shortcuts;

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      const inInput = isInInput(event.target);

      for (const shortcut of shortcutsRef.current) {
        const key = event.key.toLowerCase();
        const ctrl = event.ctrlKey || event.metaKey;
        const alt = event.altKey;
        const shift = event.shiftKey;

        const matches =
          key === shortcut.key.toLowerCase() &&
          (shortcut.ctrl ?? false) === ctrl &&
          (shortcut.alt ?? false) === alt &&
          (shortcut.shift ?? false) === shift;

        if (matches) {
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

// Shortcut handler registry
type ShortcutHandler = () => void;
const shortcutHandlers = new Map<string, ShortcutHandler>();

/**
 * Register a handler for a shortcut ID
 */
export function registerShortcutHandler(id: string, handler: ShortcutHandler): () => void {
  shortcutHandlers.set(id, handler);
  return () => shortcutHandlers.delete(id);
}

/**
 * Enhanced hook for customizable keyboard shortcuts
 */
export function useShortcuts() {
  const [customizations, setCustomizations] = useState<ShortcutCustomization[]>(() =>
    loadCustomShortcuts()
  );

  const shortcuts = useMemo(
    () => getEffectiveShortcuts(customizations),
    [customizations]
  );

  // Handle shortcut trigger
  const handleShortcut = useCallback((id: string) => {
    const handler = shortcutHandlers.get(id);
    if (handler) {
      handler();
      return true;
    }
    // Dispatch event for handlers not registered via registerShortcutHandler
    window.dispatchEvent(new CustomEvent('shortcut:triggered', { detail: { id } }));
    return false;
  }, []);

  // Keyboard event handler
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      const inInput = isInInput(event.target);

      for (const shortcut of shortcuts) {
        if (matchesShortcut(event, shortcut)) {
          if (inInput && !shortcut.global) continue;

          event.preventDefault();
          handleShortcut(shortcut.id);
          return;
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [shortcuts, handleShortcut]);

  // Update a shortcut
  const updateShortcut = useCallback((customization: ShortcutCustomization) => {
    setCustomizations((prev) => {
      const existing = prev.findIndex((c) => c.id === customization.id);
      let next: ShortcutCustomization[];
      if (existing >= 0) {
        next = [...prev];
        next[existing] = { ...prev[existing], ...customization };
      } else {
        next = [...prev, customization];
      }
      saveCustomShortcuts(next);
      return next;
    });
  }, []);

  // Reset a single shortcut
  const resetShortcutById = useCallback((id: string) => {
    setCustomizations((prev) => {
      const next = resetShortcut(id, prev);
      saveCustomShortcuts(next);
      return next;
    });
  }, []);

  // Reset all shortcuts
  const resetAll = useCallback(() => {
    resetAllShortcuts();
    setCustomizations([]);
  }, []);

  // Check conflicts
  const conflicts = useMemo(() => findConflicts(shortcuts), [shortcuts]);

  return {
    shortcuts,
    customizations,
    updateShortcut,
    resetShortcut: resetShortcutById,
    resetAll,
    conflicts,
    registerHandler: registerShortcutHandler,
  };
}

/**
 * Hook for registering a shortcut handler
 */
export function useShortcutHandler(id: string, handler: ShortcutHandler, deps: any[] = []) {
  useEffect(() => {
    const unregister = registerShortcutHandler(id, handler);
    return unregister;
  }, [id, ...deps]);
}

/**
 * Global application shortcuts - sets up handlers for common actions
 */
export function useGlobalShortcuts() {
  const navigate = useNavigate();
  const location = useLocation();
  const { currentProject, toggleSidebar } = useProjectStore();

  // Navigation handlers
  useShortcutHandler('nav.home', () => navigate('/'), [navigate]);
  useShortcutHandler('nav.settings', () => navigate('/settings'), [navigate]);
  useShortcutHandler('nav.help', () => navigate('/help'), [navigate]);
  useShortcutHandler('nav.back', () => window.history.back(), []);
  useShortcutHandler('nav.forward', () => window.history.forward(), []);

  // Project navigation handlers (only active when in project context)
  useShortcutHandler(
    'project.overview',
    () => currentProject && navigate(`/project/${currentProject.id}`),
    [navigate, currentProject]
  );
  useShortcutHandler(
    'project.characters',
    () => currentProject && navigate(`/project/${currentProject.id}/characters`),
    [navigate, currentProject]
  );
  useShortcutHandler(
    'project.scenes',
    () => currentProject && navigate(`/project/${currentProject.id}/scenes`),
    [navigate, currentProject]
  );
  useShortcutHandler(
    'project.generation',
    () => currentProject && navigate(`/project/${currentProject.id}/generate`),
    [navigate, currentProject]
  );
  useShortcutHandler(
    'project.export',
    () => currentProject && navigate(`/project/${currentProject.id}/export`),
    [navigate, currentProject]
  );
  useShortcutHandler(
    'project.timeline',
    () => currentProject && navigate(`/project/${currentProject.id}/timeline`),
    [navigate, currentProject]
  );
  useShortcutHandler(
    'project.analytics',
    () => currentProject && navigate('/analytics'),
    [navigate]
  );

  // View handlers
  useShortcutHandler('view.sidebar', toggleSidebar, [toggleSidebar]);
  useShortcutHandler(
    'view.commandPalette',
    () => window.dispatchEvent(new CustomEvent('app:commandPalette')),
    []
  );

  // Editing handlers (dispatch events for page-specific handling)
  useShortcutHandler(
    'edit.save',
    () => window.dispatchEvent(new CustomEvent('app:save')),
    []
  );
  useShortcutHandler(
    'edit.undo',
    () => window.dispatchEvent(new CustomEvent('app:undo')),
    []
  );
  useShortcutHandler(
    'edit.redo',
    () => window.dispatchEvent(new CustomEvent('app:redo')),
    []
  );
  useShortcutHandler(
    'edit.redo.alt',
    () => window.dispatchEvent(new CustomEvent('app:redo')),
    []
  );

  // General handlers
  useShortcutHandler(
    'general.escape',
    () => window.dispatchEvent(new CustomEvent('app:escape')),
    []
  );
  useShortcutHandler(
    'general.newProject',
    () => window.dispatchEvent(new CustomEvent('app:newProject')),
    []
  );
  useShortcutHandler(
    'general.openProject',
    () => window.dispatchEvent(new CustomEvent('app:openProject')),
    []
  );
  useShortcutHandler(
    'general.closeProject',
    () => window.dispatchEvent(new CustomEvent('app:closeProject')),
    []
  );

  // Initialize the shortcuts system
  useShortcuts();
}

/**
 * Get all available shortcuts for help display
 */
export function getAllShortcuts(): { category: string; shortcuts: ShortcutDefinition[] }[] {
  const shortcuts = getEffectiveShortcuts(loadCustomShortcuts());
  const grouped = getShortcutsByCategory(shortcuts);

  return Object.entries(grouped)
    .filter(([_, shortcuts]) => shortcuts.length > 0)
    .map(([category, shortcuts]) => ({
      category: CATEGORY_LABELS[category as keyof typeof CATEGORY_LABELS],
      shortcuts,
    }));
}

/**
 * Hook for timeline-specific shortcuts
 */
export function useTimelineShortcuts(callbacks: {
  onPlayPause?: () => void;
  onStop?: () => void;
  onFrameForward?: () => void;
  onFrameBack?: () => void;
  onJumpForward?: () => void;
  onJumpBack?: () => void;
  onGoToStart?: () => void;
  onGoToEnd?: () => void;
  onZoomIn?: () => void;
  onZoomOut?: () => void;
  onZoomReset?: () => void;
  onToggleLock?: () => void;
  onToggleVisibility?: () => void;
  onSplitClip?: () => void;
  onTrimStart?: () => void;
  onTrimEnd?: () => void;
  onNextClip?: () => void;
  onPrevClip?: () => void;
}) {
  useShortcutHandler('timeline.playPause', callbacks.onPlayPause || (() => {}), [callbacks.onPlayPause]);
  useShortcutHandler('timeline.stop', callbacks.onStop || (() => {}), [callbacks.onStop]);
  useShortcutHandler('timeline.frameForward', callbacks.onFrameForward || (() => {}), [callbacks.onFrameForward]);
  useShortcutHandler('timeline.frameBack', callbacks.onFrameBack || (() => {}), [callbacks.onFrameBack]);
  useShortcutHandler('timeline.jumpForward', callbacks.onJumpForward || (() => {}), [callbacks.onJumpForward]);
  useShortcutHandler('timeline.jumpBack', callbacks.onJumpBack || (() => {}), [callbacks.onJumpBack]);
  useShortcutHandler('timeline.goToStart', callbacks.onGoToStart || (() => {}), [callbacks.onGoToStart]);
  useShortcutHandler('timeline.goToEnd', callbacks.onGoToEnd || (() => {}), [callbacks.onGoToEnd]);
  useShortcutHandler('timeline.zoomIn', callbacks.onZoomIn || (() => {}), [callbacks.onZoomIn]);
  useShortcutHandler('timeline.zoomIn.alt', callbacks.onZoomIn || (() => {}), [callbacks.onZoomIn]);
  useShortcutHandler('timeline.zoomOut', callbacks.onZoomOut || (() => {}), [callbacks.onZoomOut]);
  useShortcutHandler('timeline.zoomReset', callbacks.onZoomReset || (() => {}), [callbacks.onZoomReset]);
  useShortcutHandler('timeline.toggleLock', callbacks.onToggleLock || (() => {}), [callbacks.onToggleLock]);
  useShortcutHandler('timeline.toggleVisibility', callbacks.onToggleVisibility || (() => {}), [callbacks.onToggleVisibility]);
  useShortcutHandler('timeline.splitClip', callbacks.onSplitClip || (() => {}), [callbacks.onSplitClip]);
  useShortcutHandler('timeline.trimStart', callbacks.onTrimStart || (() => {}), [callbacks.onTrimStart]);
  useShortcutHandler('timeline.trimEnd', callbacks.onTrimEnd || (() => {}), [callbacks.onTrimEnd]);
  useShortcutHandler('timeline.nextClip', callbacks.onNextClip || (() => {}), [callbacks.onNextClip]);
  useShortcutHandler('timeline.prevClip', callbacks.onPrevClip || (() => {}), [callbacks.onPrevClip]);
}

/**
 * Hook for generation page shortcuts
 */
export function useGenerationShortcuts(callbacks: {
  onQueue?: () => void;
  onQueueAll?: () => void;
  onApprove?: () => void;
  onReject?: () => void;
  onRetry?: () => void;
  onCancel?: () => void;
  onPreview?: () => void;
}) {
  useShortcutHandler('generation.queue', callbacks.onQueue || (() => {}), [callbacks.onQueue]);
  useShortcutHandler('generation.queueAll', callbacks.onQueueAll || (() => {}), [callbacks.onQueueAll]);
  useShortcutHandler('generation.approve', callbacks.onApprove || (() => {}), [callbacks.onApprove]);
  useShortcutHandler('generation.reject', callbacks.onReject || (() => {}), [callbacks.onReject]);
  useShortcutHandler('generation.retry', callbacks.onRetry || (() => {}), [callbacks.onRetry]);
  useShortcutHandler('generation.cancel', callbacks.onCancel || (() => {}), [callbacks.onCancel]);
  useShortcutHandler('generation.preview', callbacks.onPreview || (() => {}), [callbacks.onPreview]);
}

/**
 * Hook for playback shortcuts
 */
export function usePlaybackShortcuts(callbacks: {
  onFullscreen?: () => void;
  onMute?: () => void;
  onVolumeUp?: () => void;
  onVolumeDown?: () => void;
  onSpeedUp?: () => void;
  onSpeedDown?: () => void;
  onLoop?: () => void;
}) {
  useShortcutHandler('playback.fullscreen', callbacks.onFullscreen || (() => {}), [callbacks.onFullscreen]);
  useShortcutHandler('playback.mute', callbacks.onMute || (() => {}), [callbacks.onMute]);
  useShortcutHandler('playback.volumeUp', callbacks.onVolumeUp || (() => {}), [callbacks.onVolumeUp]);
  useShortcutHandler('playback.volumeDown', callbacks.onVolumeDown || (() => {}), [callbacks.onVolumeDown]);
  useShortcutHandler('playback.speedUp', callbacks.onSpeedUp || (() => {}), [callbacks.onSpeedUp]);
  useShortcutHandler('playback.speedDown', callbacks.onSpeedDown || (() => {}), [callbacks.onSpeedDown]);
  useShortcutHandler('playback.loop', callbacks.onLoop || (() => {}), [callbacks.onLoop]);
}
