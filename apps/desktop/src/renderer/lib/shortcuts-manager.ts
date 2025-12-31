/**
 * Comprehensive keyboard shortcuts manager with customization support.
 * Handles shortcut registration, customization, and persistence.
 */

// Shortcut category types
export type ShortcutCategory =
  | 'navigation'
  | 'project'
  | 'editing'
  | 'timeline'
  | 'generation'
  | 'playback'
  | 'view'
  | 'general';

// Shortcut definition
export interface ShortcutDefinition {
  id: string;
  key: string;
  ctrl?: boolean;
  alt?: boolean;
  shift?: boolean;
  meta?: boolean;
  description: string;
  category: ShortcutCategory;
  global?: boolean; // Works even in inputs
  enabled?: boolean;
}

// User customization
export interface ShortcutCustomization {
  id: string;
  key?: string;
  ctrl?: boolean;
  alt?: boolean;
  shift?: boolean;
  meta?: boolean;
  enabled?: boolean;
}

// Default shortcuts configuration
export const DEFAULT_SHORTCUTS: ShortcutDefinition[] = [
  // Navigation
  { id: 'nav.home', key: 'h', ctrl: true, description: 'Go to Home', category: 'navigation' },
  { id: 'nav.settings', key: ',', ctrl: true, description: 'Open Settings', category: 'navigation' },
  { id: 'nav.help', key: '?', shift: true, description: 'Show Help', category: 'navigation' },
  { id: 'nav.back', key: 'ArrowLeft', alt: true, description: 'Go Back', category: 'navigation' },
  { id: 'nav.forward', key: 'ArrowRight', alt: true, description: 'Go Forward', category: 'navigation' },

  // Project shortcuts
  { id: 'project.overview', key: '1', ctrl: true, description: 'Project Overview', category: 'project' },
  { id: 'project.characters', key: '2', ctrl: true, description: 'Characters', category: 'project' },
  { id: 'project.scenes', key: '3', ctrl: true, description: 'Scene Planning', category: 'project' },
  { id: 'project.generation', key: '4', ctrl: true, description: 'Generation', category: 'project' },
  { id: 'project.export', key: '5', ctrl: true, description: 'Export', category: 'project' },
  { id: 'project.timeline', key: '6', ctrl: true, description: 'Timeline', category: 'project' },
  { id: 'project.analytics', key: '7', ctrl: true, description: 'Analytics', category: 'project' },

  // Editing shortcuts
  { id: 'edit.save', key: 's', ctrl: true, description: 'Save', category: 'editing', global: true },
  { id: 'edit.undo', key: 'z', ctrl: true, description: 'Undo', category: 'editing', global: true },
  { id: 'edit.redo', key: 'z', ctrl: true, shift: true, description: 'Redo', category: 'editing', global: true },
  { id: 'edit.redo.alt', key: 'y', ctrl: true, description: 'Redo (Alt)', category: 'editing', global: true },
  { id: 'edit.cut', key: 'x', ctrl: true, description: 'Cut', category: 'editing' },
  { id: 'edit.copy', key: 'c', ctrl: true, description: 'Copy', category: 'editing' },
  { id: 'edit.paste', key: 'v', ctrl: true, description: 'Paste', category: 'editing' },
  { id: 'edit.selectAll', key: 'a', ctrl: true, description: 'Select All', category: 'editing' },
  { id: 'edit.delete', key: 'Delete', description: 'Delete Selected', category: 'editing' },
  { id: 'edit.delete.alt', key: 'Backspace', description: 'Delete Selected (Alt)', category: 'editing' },
  { id: 'edit.duplicate', key: 'd', ctrl: true, description: 'Duplicate', category: 'editing' },
  { id: 'edit.rename', key: 'F2', description: 'Rename', category: 'editing' },

  // Timeline shortcuts
  { id: 'timeline.playPause', key: ' ', description: 'Play/Pause', category: 'timeline', global: true },
  { id: 'timeline.stop', key: 's', description: 'Stop', category: 'timeline' },
  { id: 'timeline.frameForward', key: 'ArrowRight', description: 'Next Frame', category: 'timeline' },
  { id: 'timeline.frameBack', key: 'ArrowLeft', description: 'Previous Frame', category: 'timeline' },
  { id: 'timeline.jumpForward', key: 'ArrowRight', shift: true, description: 'Jump Forward 10 Frames', category: 'timeline' },
  { id: 'timeline.jumpBack', key: 'ArrowLeft', shift: true, description: 'Jump Back 10 Frames', category: 'timeline' },
  { id: 'timeline.goToStart', key: 'Home', description: 'Go to Start', category: 'timeline' },
  { id: 'timeline.goToEnd', key: 'End', description: 'Go to End', category: 'timeline' },
  { id: 'timeline.zoomIn', key: '=', ctrl: true, description: 'Zoom In', category: 'timeline' },
  { id: 'timeline.zoomIn.alt', key: '+', ctrl: true, description: 'Zoom In (Alt)', category: 'timeline' },
  { id: 'timeline.zoomOut', key: '-', ctrl: true, description: 'Zoom Out', category: 'timeline' },
  { id: 'timeline.zoomReset', key: '0', ctrl: true, description: 'Reset Zoom', category: 'timeline' },
  { id: 'timeline.toggleLock', key: 'l', description: 'Toggle Lock', category: 'timeline' },
  { id: 'timeline.toggleVisibility', key: 'v', description: 'Toggle Visibility', category: 'timeline' },
  { id: 'timeline.splitClip', key: 's', ctrl: true, shift: true, description: 'Split Clip', category: 'timeline' },
  { id: 'timeline.trimStart', key: '[', description: 'Trim Start', category: 'timeline' },
  { id: 'timeline.trimEnd', key: ']', description: 'Trim End', category: 'timeline' },
  { id: 'timeline.nextClip', key: 'ArrowDown', description: 'Next Clip', category: 'timeline' },
  { id: 'timeline.prevClip', key: 'ArrowUp', description: 'Previous Clip', category: 'timeline' },

  // Generation shortcuts
  { id: 'generation.queue', key: 'g', ctrl: true, description: 'Queue Selected', category: 'generation' },
  { id: 'generation.queueAll', key: 'g', ctrl: true, shift: true, description: 'Queue All', category: 'generation' },
  { id: 'generation.approve', key: 'Enter', ctrl: true, description: 'Approve Selected', category: 'generation' },
  { id: 'generation.reject', key: 'r', ctrl: true, description: 'Reject Selected', category: 'generation' },
  { id: 'generation.retry', key: 'r', ctrl: true, shift: true, description: 'Retry Failed', category: 'generation' },
  { id: 'generation.cancel', key: 'Escape', description: 'Cancel Generation', category: 'generation' },
  { id: 'generation.preview', key: 'p', ctrl: true, description: 'Preview', category: 'generation' },

  // Playback shortcuts
  { id: 'playback.fullscreen', key: 'f', description: 'Toggle Fullscreen', category: 'playback' },
  { id: 'playback.mute', key: 'm', description: 'Toggle Mute', category: 'playback' },
  { id: 'playback.volumeUp', key: 'ArrowUp', ctrl: true, description: 'Volume Up', category: 'playback' },
  { id: 'playback.volumeDown', key: 'ArrowDown', ctrl: true, description: 'Volume Down', category: 'playback' },
  { id: 'playback.speedUp', key: '.', ctrl: true, description: 'Speed Up', category: 'playback' },
  { id: 'playback.speedDown', key: ',', ctrl: true, description: 'Speed Down', category: 'playback' },
  { id: 'playback.loop', key: 'l', ctrl: true, description: 'Toggle Loop', category: 'playback' },

  // View shortcuts
  { id: 'view.sidebar', key: 'b', ctrl: true, description: 'Toggle Sidebar', category: 'view' },
  { id: 'view.panel', key: 'j', ctrl: true, description: 'Toggle Bottom Panel', category: 'view' },
  { id: 'view.inspector', key: 'i', ctrl: true, description: 'Toggle Inspector', category: 'view' },
  { id: 'view.commandPalette', key: 'k', ctrl: true, description: 'Command Palette', category: 'view', global: true },
  { id: 'view.search', key: 'f', ctrl: true, description: 'Search', category: 'view' },
  { id: 'view.focusMode', key: 'f', ctrl: true, shift: true, description: 'Focus Mode', category: 'view' },
  { id: 'view.darkMode', key: 'd', ctrl: true, shift: true, description: 'Toggle Dark Mode', category: 'view' },

  // General shortcuts
  { id: 'general.escape', key: 'Escape', description: 'Close/Cancel', category: 'general', global: true },
  { id: 'general.refresh', key: 'r', ctrl: true, description: 'Refresh', category: 'general' },
  { id: 'general.newProject', key: 'n', ctrl: true, description: 'New Project', category: 'general' },
  { id: 'general.openProject', key: 'o', ctrl: true, description: 'Open Project', category: 'general' },
  { id: 'general.closeProject', key: 'w', ctrl: true, description: 'Close Project', category: 'general' },
  { id: 'general.export', key: 'e', ctrl: true, shift: true, description: 'Export', category: 'general' },
];

// Category labels
export const CATEGORY_LABELS: Record<ShortcutCategory, string> = {
  navigation: 'Navigation',
  project: 'Project',
  editing: 'Editing',
  timeline: 'Timeline',
  generation: 'Generation',
  playback: 'Playback',
  view: 'View',
  general: 'General',
};

// Storage key
const STORAGE_KEY = 'scenemachine:shortcuts';

/**
 * Load custom shortcuts from storage
 */
export function loadCustomShortcuts(): ShortcutCustomization[] {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      return JSON.parse(stored);
    }
  } catch (e) {
    console.error('Failed to load custom shortcuts:', e);
  }
  return [];
}

/**
 * Save custom shortcuts to storage
 */
export function saveCustomShortcuts(customizations: ShortcutCustomization[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(customizations));
  } catch (e) {
    console.error('Failed to save custom shortcuts:', e);
  }
}

/**
 * Merge default shortcuts with customizations
 */
export function getEffectiveShortcuts(
  customizations: ShortcutCustomization[] = []
): ShortcutDefinition[] {
  const customMap = new Map(customizations.map((c) => [c.id, c]));

  return DEFAULT_SHORTCUTS.map((shortcut) => {
    const custom = customMap.get(shortcut.id);
    if (!custom) return shortcut;

    return {
      ...shortcut,
      key: custom.key ?? shortcut.key,
      ctrl: custom.ctrl ?? shortcut.ctrl,
      alt: custom.alt ?? shortcut.alt,
      shift: custom.shift ?? shortcut.shift,
      meta: custom.meta ?? shortcut.meta,
      enabled: custom.enabled ?? shortcut.enabled ?? true,
    };
  });
}

/**
 * Check if a key combo matches a shortcut
 */
export function matchesShortcut(
  event: KeyboardEvent,
  shortcut: ShortcutDefinition
): boolean {
  const key = event.key.toLowerCase();
  const ctrl = event.ctrlKey || event.metaKey;
  const alt = event.altKey;
  const shift = event.shiftKey;

  // Handle special keys
  let shortcutKey = shortcut.key.toLowerCase();
  if (shortcutKey === ' ') shortcutKey = ' ';
  if (shortcutKey === 'space') shortcutKey = ' ';

  return (
    key === shortcutKey &&
    (shortcut.ctrl ?? false) === ctrl &&
    (shortcut.alt ?? false) === alt &&
    (shortcut.shift ?? false) === shift &&
    (shortcut.enabled ?? true)
  );
}

/**
 * Format shortcut for display
 */
export function formatShortcut(shortcut: ShortcutDefinition): string {
  const parts: string[] = [];
  const isMac = typeof navigator !== 'undefined' && navigator.platform?.toUpperCase().includes('MAC');

  if (shortcut.ctrl) parts.push(isMac ? '\u2318' : 'Ctrl');
  if (shortcut.alt) parts.push(isMac ? '\u2325' : 'Alt');
  if (shortcut.shift) parts.push('\u21E7');
  if (shortcut.meta) parts.push(isMac ? '\u2318' : 'Win');

  let key = shortcut.key;
  const keyMap: Record<string, string> = {
    ' ': 'Space',
    'ArrowUp': '\u2191',
    'ArrowDown': '\u2193',
    'ArrowLeft': '\u2190',
    'ArrowRight': '\u2192',
    'Escape': 'Esc',
    'Delete': 'Del',
    'Backspace': '\u232B',
    'Enter': '\u23CE',
    'Tab': '\u21E5',
  };

  key = keyMap[key] ?? (key.length === 1 ? key.toUpperCase() : key);
  parts.push(key);

  return parts.join(isMac ? '' : '+');
}

/**
 * Parse a key string into shortcut definition parts
 */
export function parseKeyString(
  keyString: string
): Pick<ShortcutDefinition, 'key' | 'ctrl' | 'alt' | 'shift' | 'meta'> {
  const parts = keyString.toLowerCase().split('+');
  const key = parts.pop() || '';

  return {
    key,
    ctrl: parts.includes('ctrl') || parts.includes('cmd') || parts.includes('\u2318'),
    alt: parts.includes('alt') || parts.includes('opt') || parts.includes('\u2325'),
    shift: parts.includes('shift') || parts.includes('\u21e7'),
    meta: parts.includes('meta') || parts.includes('win'),
  };
}

/**
 * Get shortcuts grouped by category
 */
export function getShortcutsByCategory(
  shortcuts: ShortcutDefinition[]
): Record<ShortcutCategory, ShortcutDefinition[]> {
  const grouped: Record<ShortcutCategory, ShortcutDefinition[]> = {
    navigation: [],
    project: [],
    editing: [],
    timeline: [],
    generation: [],
    playback: [],
    view: [],
    general: [],
  };

  for (const shortcut of shortcuts) {
    grouped[shortcut.category].push(shortcut);
  }

  return grouped;
}

/**
 * Check for conflicting shortcuts
 */
export function findConflicts(
  shortcuts: ShortcutDefinition[]
): Map<string, ShortcutDefinition[]> {
  const keyMap = new Map<string, ShortcutDefinition[]>();

  for (const shortcut of shortcuts) {
    if (shortcut.enabled === false) continue;

    const keyCombo = formatShortcut(shortcut);
    const existing = keyMap.get(keyCombo) || [];
    existing.push(shortcut);
    keyMap.set(keyCombo, existing);
  }

  // Filter to only conflicting shortcuts
  const conflicts = new Map<string, ShortcutDefinition[]>();
  keyMap.forEach((shortcuts, key) => {
    if (shortcuts.length > 1) {
      conflicts.set(key, shortcuts);
    }
  });

  return conflicts;
}

/**
 * Reset a shortcut to default
 */
export function resetShortcut(
  id: string,
  customizations: ShortcutCustomization[]
): ShortcutCustomization[] {
  return customizations.filter((c) => c.id !== id);
}

/**
 * Reset all shortcuts to default
 */
export function resetAllShortcuts(): void {
  localStorage.removeItem(STORAGE_KEY);
}

/**
 * Export shortcuts configuration
 */
export function exportShortcuts(customizations: ShortcutCustomization[]): string {
  return JSON.stringify(customizations, null, 2);
}

/**
 * Import shortcuts configuration
 */
export function importShortcuts(json: string): ShortcutCustomization[] {
  try {
    const parsed = JSON.parse(json);
    if (!Array.isArray(parsed)) {
      throw new Error('Invalid shortcuts format');
    }
    return parsed;
  } catch (e) {
    throw new Error('Failed to parse shortcuts: ' + (e as Error).message);
  }
}
