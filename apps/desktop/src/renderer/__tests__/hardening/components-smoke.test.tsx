/**
 * Components Smoke Tests
 *
 * Tests that all major components can be imported without errors.
 * This ensures there are no import/export issues or missing dependencies.
 */

import { describe, it, expect, vi } from 'vitest';
import React from 'react';

// Mock window.matchMedia for components that use it
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

describe('Component Imports', () => {
  describe('Layout Components', () => {
    it('should import ToastContainer', async () => {
      const { ToastContainer } = await import('../../components/toast');
      expect(ToastContainer).toBeDefined();
    });

    it('should import ErrorBoundary', async () => {
      const { ErrorBoundary } = await import('../../components/error-boundary');
      expect(ErrorBoundary).toBeDefined();
    });
  });

  describe('Form Components', () => {
    it('should import ScreenplayUpload', async () => {
      const { ScreenplayUpload } = await import('../../components/screenplay-upload');
      expect(ScreenplayUpload).toBeDefined();
    });
  });

  describe('Display Components', () => {
    it('should import Skeleton components', async () => {
      const skeletonModule = await import('../../components/skeleton');
      // Check actual export names from skeleton.tsx
      expect(skeletonModule.Skeleton).toBeDefined();
      expect(skeletonModule.SkeletonProjectCard).toBeDefined();
      expect(skeletonModule.SkeletonScene).toBeDefined();
      expect(skeletonModule.SkeletonShotCard).toBeDefined();
      expect(skeletonModule.SkeletonQueueJob).toBeDefined();
    });

    it('should import ShotCard', async () => {
      const { ShotCard } = await import('../../components/shot-card');
      expect(ShotCard).toBeDefined();
    });
  });

  describe('Feature Components', () => {
    it('should import QueueManager', async () => {
      const { QueueManager } = await import('../../components/queue-manager');
      expect(QueueManager).toBeDefined();
    });

    it('should import CommandPalette', async () => {
      const { CommandPalette } = await import('../../components/command-palette');
      expect(CommandPalette).toBeDefined();
    });

    it('should import CharacterCard', async () => {
      const { CharacterCard } = await import('../../components/character-card');
      expect(CharacterCard).toBeDefined();
    });
  });

  describe('Sharing Components', () => {
    it('should import ShareDialog', async () => {
      const { ShareDialog } = await import('../../components/share-dialog');
      expect(ShareDialog).toBeDefined();
    });

    it('should import CommentsPanel', async () => {
      const { CommentsPanel } = await import('../../components/comments-panel');
      expect(CommentsPanel).toBeDefined();
    });
  });

  describe('Generation Components', () => {
    it('should import ModelSelector', async () => {
      const { ModelSelector } = await import('../../components/model-selector');
      expect(ModelSelector).toBeDefined();
    });

    it('should import CostEstimate', async () => {
      const { CostEstimate } = await import('../../components/cost-estimate');
      expect(CostEstimate).toBeDefined();
    });
  });

  describe('Character Components', () => {
    it('should import PhysicalDescriptionForm', async () => {
      const { PhysicalDescriptionForm } =
        await import('../../components/physical-description-form');
      expect(PhysicalDescriptionForm).toBeDefined();
    });
  });

  describe('Settings Components', () => {
    it('should import BudgetSettings', async () => {
      const { BudgetSettings } = await import('../../components/budget-settings');
      expect(BudgetSettings).toBeDefined();
    });

    it('should import CircuitBreakerPanel', async () => {
      // Actual export is CircuitBreakerPanel, not CircuitBreakerStatus
      const { CircuitBreakerPanel } = await import('../../components/circuit-breaker-status');
      expect(CircuitBreakerPanel).toBeDefined();
    });
  });

  describe('Experience Mode Components', () => {
    it('should import ExperienceModeSelector', async () => {
      const { ExperienceModeSelector } = await import('../../components/experience-mode-selector');
      expect(ExperienceModeSelector).toBeDefined();
    });

    it('should import StevenAssistant', async () => {
      const { StevenAssistant } = await import('../../components/steven-assistant');
      expect(StevenAssistant).toBeDefined();
    });

    it('should import StoryModeWizard', async () => {
      const { StoryModeWizard } = await import('../../components/story-mode-wizard');
      expect(StoryModeWizard).toBeDefined();
    });
  });

  describe('Utility Components', () => {
    it('should import WatermarkPicker', async () => {
      const { WatermarkPicker } = await import('../../components/watermark-picker');
      expect(WatermarkPicker).toBeDefined();
    });

    it('should import ProgressDashboard', async () => {
      const { ProgressDashboard } = await import('../../components/progress-dashboard');
      expect(ProgressDashboard).toBeDefined();
    });
  });
});

describe('Hook Imports', () => {
  it('should import useToast', async () => {
    const { useToast } = await import('../../components/toast');
    expect(useToast).toBeDefined();
  });

  it('should import useAutoSave', async () => {
    const { useAutoSave } = await import('../../hooks/use-auto-save');
    expect(useAutoSave).toBeDefined();
  });

  it('should import useKeyboardShortcuts', async () => {
    // The actual hook is use-keyboard-shortcuts, not use-shortcuts
    const module = await import('../../hooks/use-keyboard-shortcuts');
    expect(module).toBeDefined();
  });

  it('should import useUndoRedo', async () => {
    const { useUndoRedo } = await import('../../hooks/use-undo-redo');
    expect(useUndoRedo).toBeDefined();
  });
});

describe('Utility Imports', () => {
  it('should import cn utility', async () => {
    const { cn } = await import('../../lib/utils');
    expect(cn).toBeDefined();
    expect(typeof cn).toBe('function');
  });

  it('should import shortcuts manager', async () => {
    const shortcutsManager = await import('../../lib/shortcuts-manager');
    expect(shortcutsManager).toBeDefined();
  });
});
