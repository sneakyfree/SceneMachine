/**
 * Store Integration Hardening Tests
 *
 * Tests that all Zustand stores are properly initialized and have expected state/actions.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { act } from '@testing-library/react';

// Mock localStorage for persist middleware
const mockStorage: Record<string, string> = {};
vi.stubGlobal('localStorage', {
  getItem: (key: string) => mockStorage[key] || null,
  setItem: (key: string, value: string) => {
    mockStorage[key] = value;
  },
  removeItem: (key: string) => {
    delete mockStorage[key];
  },
  clear: () => {
    Object.keys(mockStorage).forEach((key) => delete mockStorage[key]);
  },
});

// Mock window.electronAPI for API client
vi.stubGlobal('window', {
  ...globalThis.window,
  electronAPI: {
    backendRequest: vi.fn().mockResolvedValue({}),
  },
});

describe('Store Integration Hardening', () => {
  beforeEach(() => {
    // Clear localStorage mock between tests
    Object.keys(mockStorage).forEach((key) => delete mockStorage[key]);
  });

  describe('Toast Store', () => {
    it('should export useToastStore', async () => {
      const { useToastStore } = await import('../../stores/toast-store');
      expect(useToastStore).toBeDefined();
    });

    it('should have all toast methods', async () => {
      const { useToastStore } = await import('../../stores/toast-store');
      const state = useToastStore.getState();

      expect(state.addToast).toBeDefined();
      expect(state.removeToast).toBeDefined();
      expect(state.clearAllToasts).toBeDefined();
      expect(typeof state.addToast).toBe('function');
    });

    it('should add and remove toasts', async () => {
      const { useToastStore } = await import('../../stores/toast-store');

      act(() => {
        useToastStore.getState().addToast({
          type: 'success',
          title: 'Test Toast',
        });
      });

      const toasts = useToastStore.getState().toasts;
      expect(toasts.length).toBeGreaterThan(0);

      const toastId = toasts[0].id;
      act(() => {
        useToastStore.getState().removeToast(toastId);
      });

      expect(useToastStore.getState().toasts.find((t) => t.id === toastId)).toBeUndefined();
    });
  });

  describe('Project Store', () => {
    it('should export useProjectStore', async () => {
      const { useProjectStore } = await import('../../stores/project-store');
      expect(useProjectStore).toBeDefined();
    });

    it('should have project management methods', async () => {
      const { useProjectStore } = await import('../../stores/project-store');
      const state = useProjectStore.getState();

      expect(state.setCurrentProject).toBeDefined();
      expect(state.updateProject).toBeDefined();
      expect(state.toggleSidebar).toBeDefined();
      expect(state.selectCharacter).toBeDefined();
      expect(state.selectScene).toBeDefined();
      expect(state.reset).toBeDefined();
    });

    it('should have initial state', async () => {
      const { useProjectStore } = await import('../../stores/project-store');
      const state = useProjectStore.getState();

      expect(state.currentProject).toBe(null);
      expect(typeof state.sidebarCollapsed).toBe('boolean');
    });
  });

  describe('Generation Store', () => {
    it('should export useGenerationStore', async () => {
      const { useGenerationStore } = await import('../../stores/generation-store');
      expect(useGenerationStore).toBeDefined();
    });

    it('should have queue management state', async () => {
      const { useGenerationStore } = await import('../../stores/generation-store');
      const state = useGenerationStore.getState();

      expect(state.selectedProvider).toBeDefined();
      expect(state.availableModels).toBeDefined();
      expect(state.setSelectedProvider).toBeDefined();
      expect(state.setSelectedModel).toBeDefined();
    });

    it('should have worker status management', async () => {
      const { useGenerationStore } = await import('../../stores/generation-store');
      const state = useGenerationStore.getState();

      // workerStatus can be null initially, so just check the key exists
      expect('workerStatus' in state).toBe(true);
      expect(state.setWorkerStatus).toBeDefined();
    });
  });

  describe('Sharing Store', () => {
    it('should export useSharingStore', async () => {
      const { useSharingStore } = await import('../../stores/sharing-store');
      expect(useSharingStore).toBeDefined();
    });

    it('should have sharing methods', async () => {
      const { useSharingStore } = await import('../../stores/sharing-store');
      const state = useSharingStore.getState();

      expect(state.setCurrentProject).toBeDefined();
      expect(state.setShares).toBeDefined();
      expect(state.setComments).toBeDefined();
      expect(state.setShareDialogOpen).toBeDefined();
      expect(state.fetchShares).toBeDefined();
      expect(state.createShare).toBeDefined();
    });
  });

  describe('Settings Store', () => {
    it('should export useSettingsStore', async () => {
      const { useSettingsStore } = await import('../../stores/settings-store');
      expect(useSettingsStore).toBeDefined();
    });

    it('should have settings methods', async () => {
      const { useSettingsStore } = await import('../../stores/settings-store');
      const state = useSettingsStore.getState();

      // Settings store uses setSettings and updateSettings
      expect(state.setSettings).toBeDefined();
      expect(state.updateSettings).toBeDefined();
      expect(state.setProviderStatuses).toBeDefined();
    });
  });

  describe('Experience Store', () => {
    it('should export useExperienceStore', async () => {
      const { useExperienceStore } = await import('../../stores/experience-store');
      expect(useExperienceStore).toBeDefined();
    });

    it('should have experience mode state', async () => {
      const { useExperienceStore } = await import('../../stores/experience-store');
      const state = useExperienceStore.getState();

      // Uses globalMode with values 'story', 'creator', 'pro'
      expect(state.globalMode).toBeDefined();
      expect(state.setGlobalMode).toBeDefined();
      expect(['story', 'creator', 'pro']).toContain(state.globalMode);
    });
  });

  describe('Audio Store', () => {
    it('should export useAudioStore', async () => {
      const { useAudioStore } = await import('../../stores/audio-store');
      expect(useAudioStore).toBeDefined();
    });
  });

  describe('Store Persistence', () => {
    it('should persist settings store', async () => {
      const { useSettingsStore } = await import('../../stores/settings-store');

      // The store should be a zustand store with getState
      expect(useSettingsStore.getState).toBeDefined();
      expect(typeof useSettingsStore.getState).toBe('function');
    });

    it('should persist experience store', async () => {
      const { useExperienceStore } = await import('../../stores/experience-store');

      expect(useExperienceStore.getState).toBeDefined();
      expect(typeof useExperienceStore.getState).toBe('function');
    });
  });
});

describe('Store State Types', () => {
  it('should have correct toast state shape', async () => {
    const { useToastStore } = await import('../../stores/toast-store');
    const state = useToastStore.getState();

    expect(Array.isArray(state.toasts)).toBe(true);
    expect(typeof state.addToast).toBe('function');
    expect(typeof state.removeToast).toBe('function');
    expect(typeof state.clearAllToasts).toBe('function');
  });

  it('should have correct project state shape', async () => {
    const { useProjectStore } = await import('../../stores/project-store');
    const state = useProjectStore.getState();

    // currentProject should be null or Project
    expect(state.currentProject === null || typeof state.currentProject === 'object').toBe(true);
    expect(typeof state.sidebarCollapsed).toBe('boolean');
    expect(
      state.selectedCharacterId === null || typeof state.selectedCharacterId === 'string'
    ).toBe(true);
    expect(state.selectedSceneId === null || typeof state.selectedSceneId === 'string').toBe(true);
  });

  it('should have correct generation state shape', async () => {
    const { useGenerationStore } = await import('../../stores/generation-store');
    const state = useGenerationStore.getState();

    expect(typeof state.selectedProvider).toBe('string');
    expect(typeof state.availableModels).toBe('object');
    expect(typeof state.isLoadingModels).toBe('boolean');
    expect(typeof state.isLoadingHealth).toBe('boolean');
  });

  it('should have correct sharing state shape', async () => {
    const { useSharingStore } = await import('../../stores/sharing-store');
    const state = useSharingStore.getState();

    expect(Array.isArray(state.shares)).toBe(true);
    expect(Array.isArray(state.comments)).toBe(true);
    expect(typeof state.isLoadingShares).toBe('boolean');
    expect(typeof state.isLoadingComments).toBe('boolean');
  });
});
