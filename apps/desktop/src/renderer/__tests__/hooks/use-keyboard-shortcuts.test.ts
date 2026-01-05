/**
 * Keyboard shortcuts hook tests.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { formatShortcut, getAllShortcuts } from '../../hooks/use-keyboard-shortcuts';

describe('formatShortcut', () => {
  const originalPlatform = navigator.platform;

  afterEach(() => {
    Object.defineProperty(navigator, 'platform', {
      value: originalPlatform,
      writable: true,
    });
  });

  describe('on Mac', () => {
    beforeEach(() => {
      Object.defineProperty(navigator, 'platform', {
        value: 'MacIntel',
        writable: true,
      });
    });

    it('should format Ctrl as Command symbol', () => {
      const result = formatShortcut({
        key: 's',
        ctrl: true,
        description: 'Save',
        action: () => {},
      });

      expect(result).toBe('⌘S');
    });

    it('should format Alt as Option symbol', () => {
      const result = formatShortcut({
        key: 'p',
        alt: true,
        description: 'Preview',
        action: () => {},
      });

      expect(result).toBe('⌥P');
    });

    it('should format Shift as arrow symbol', () => {
      const result = formatShortcut({
        key: 'a',
        shift: true,
        description: 'Select All',
        action: () => {},
      });

      expect(result).toBe('⇧A');
    });

    it('should combine modifiers without separator', () => {
      const result = formatShortcut({
        key: 'z',
        ctrl: true,
        shift: true,
        description: 'Redo',
        action: () => {},
      });

      expect(result).toBe('⌘⇧Z');
    });
  });

  describe('on Windows/Linux', () => {
    beforeEach(() => {
      Object.defineProperty(navigator, 'platform', {
        value: 'Win32',
        writable: true,
      });
    });

    it('should format Ctrl as Ctrl+', () => {
      const result = formatShortcut({
        key: 's',
        ctrl: true,
        description: 'Save',
        action: () => {},
      });

      expect(result).toBe('Ctrl+S');
    });

    it('should format Alt as Alt+', () => {
      const result = formatShortcut({
        key: 'p',
        alt: true,
        description: 'Preview',
        action: () => {},
      });

      expect(result).toBe('Alt+P');
    });

    it('should combine modifiers with + separator', () => {
      const result = formatShortcut({
        key: 'z',
        ctrl: true,
        shift: true,
        description: 'Redo',
        action: () => {},
      });

      expect(result).toBe('Ctrl+⇧+Z');
    });
  });

  describe('special keys', () => {
    beforeEach(() => {
      Object.defineProperty(navigator, 'platform', {
        value: 'Win32',
        writable: true,
      });
    });

    it('should format Escape as Esc', () => {
      const result = formatShortcut({
        key: 'Escape',
        description: 'Close',
        action: () => {},
      });

      expect(result).toBe('Esc');
    });

    it('should format space as Space', () => {
      const result = formatShortcut({
        key: ' ',
        description: 'Play/Pause',
        action: () => {},
      });

      expect(result).toBe('Space');
    });

    it('should uppercase single character keys', () => {
      const result = formatShortcut({
        key: 'h',
        ctrl: true,
        description: 'Home',
        action: () => {},
      });

      expect(result).toBe('Ctrl+H');
    });
  });
});

describe('getAllShortcuts', () => {
  it('should return shortcut categories', () => {
    const shortcuts = getAllShortcuts();

    expect(shortcuts).toBeInstanceOf(Array);
    expect(shortcuts.length).toBeGreaterThan(0);
  });

  it('should have Navigation category', () => {
    const shortcuts = getAllShortcuts();
    const navigationCategory = shortcuts.find((c) => c.category === 'Navigation');

    expect(navigationCategory).toBeDefined();
    expect(navigationCategory?.shortcuts.length).toBeGreaterThan(0);
  });

  it('should have Project category', () => {
    const shortcuts = getAllShortcuts();
    const projectCategory = shortcuts.find((c) => c.category === 'Project');

    expect(projectCategory).toBeDefined();
    expect(projectCategory?.shortcuts.length).toBeGreaterThan(0);
  });

  it('should have General category', () => {
    const shortcuts = getAllShortcuts();
    const generalCategory = shortcuts.find((c) => c.category === 'General');

    expect(generalCategory).toBeDefined();
    // General category has Escape and new project shortcuts
    expect(generalCategory?.shortcuts.some((s) => s.key === 'Escape')).toBe(true);
  });

  it('each shortcut should have required properties', () => {
    const shortcuts = getAllShortcuts();

    for (const category of shortcuts) {
      for (const shortcut of category.shortcuts) {
        // ShortcutDefinition uses 'id' instead of 'action' - actions are registered separately
        expect(shortcut).toHaveProperty('key');
        expect(shortcut).toHaveProperty('description');
        expect(shortcut).toHaveProperty('id');
        expect(typeof shortcut.key).toBe('string');
        expect(typeof shortcut.description).toBe('string');
        expect(typeof shortcut.id).toBe('string');
      }
    }
  });
});
