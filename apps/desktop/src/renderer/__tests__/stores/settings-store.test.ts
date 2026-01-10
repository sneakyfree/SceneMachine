/**
 * Tests for the settings store.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useSettingsStore } from '../../stores/settings-store';

describe('SettingsStore', () => {
  beforeEach(() => {
    // Reset store state before each test
    useSettingsStore.setState({
      settings: null,
      providerStatuses: [],
      storageStats: null,
      llmProviders: [],
      videoProviders: [],
      themeOptions: [],
      isLoading: false,
      isSaving: false,
      isValidating: false,
      error: null,
    });
  });

  describe('Initial State', () => {
    it('should have correct initial values', () => {
      const state = useSettingsStore.getState();

      expect(state.settings).toBeNull();
      expect(state.providerStatuses).toEqual([]);
      expect(state.storageStats).toBeNull();
      expect(state.llmProviders).toEqual([]);
      expect(state.videoProviders).toEqual([]);
      expect(state.themeOptions).toEqual([]);
      expect(state.isLoading).toBe(false);
      expect(state.isSaving).toBe(false);
      expect(state.isValidating).toBe(false);
      expect(state.error).toBeNull();
    });
  });

  describe('Settings Management', () => {
    const mockSettings = {
      id: 'settings-1',
      llmProvider: 'anthropic',
      videoProvider: 'replicate',
      maxConcurrentGenerations: 3,
      generationTimeoutSeconds: 300,
      defaultVideoResolution: '1920x1080',
      defaultVideoFps: 24,
      themeMode: 'dark',
      autoSaveEnabled: true,
      showAdvancedOptions: false,
      autoCleanupTempFiles: true,
      maxCacheSizeGb: 10,
      defaultExportFormat: 'mp4',
      defaultExportQuality: 'high',
      fontSizeScale: 'medium' as const,
      highContrastEnabled: false,
      reduceMotionEnabled: false,
      largeClickTargetsEnabled: false,
      additionalSettings: {},
      createdAt: '2024-01-01',
      updatedAt: '2024-01-01',
    };

    it('should set settings', () => {
      const { setSettings } = useSettingsStore.getState();

      setSettings(mockSettings);

      const state = useSettingsStore.getState();
      expect(state.settings).toEqual(mockSettings);
      expect(state.error).toBeNull();
    });

    it('should update settings partially', () => {
      const { setSettings, updateSettings } = useSettingsStore.getState();

      setSettings(mockSettings);
      updateSettings({ themeMode: 'light', maxConcurrentGenerations: 5 });

      const state = useSettingsStore.getState();
      expect(state.settings?.themeMode).toBe('light');
      expect(state.settings?.maxConcurrentGenerations).toBe(5);
      expect(state.settings?.videoProvider).toBe('replicate'); // unchanged
    });

    it('should not update settings if none set', () => {
      const { updateSettings } = useSettingsStore.getState();

      updateSettings({ themeMode: 'light' });

      const state = useSettingsStore.getState();
      expect(state.settings).toBeNull();
    });
  });

  describe('Provider Statuses', () => {
    it('should set provider statuses', () => {
      const { setProviderStatuses } = useSettingsStore.getState();

      const statuses = [
        { provider: 'anthropic', name: 'Anthropic', available: true, configured: true, message: 'OK', latencyMs: 100 },
        { provider: 'replicate', name: 'Replicate', available: true, configured: false, message: 'API key not set', latencyMs: null },
      ];

      setProviderStatuses(statuses);

      const state = useSettingsStore.getState();
      expect(state.providerStatuses).toHaveLength(2);
      expect(state.providerStatuses[0].provider).toBe('anthropic');
    });
  });

  describe('Storage Stats', () => {
    it('should set storage stats', () => {
      const { setStorageStats } = useSettingsStore.getState();

      const stats = {
        dataDir: '/data',
        uploadDir: '/data/uploads',
        outputDir: '/data/output',
        cacheDir: '/data/cache',
        totalSizeBytes: 1000000000,
        uploadSizeBytes: 200000000,
        outputSizeBytes: 500000000,
        cacheSizeBytes: 300000000,
        tempFilesCount: 15,
      };

      setStorageStats(stats);

      const state = useSettingsStore.getState();
      expect(state.storageStats).toEqual(stats);
    });
  });

  describe('Provider Options', () => {
    it('should set LLM providers', () => {
      const { setLlmProviders } = useSettingsStore.getState();

      const providers = [
        { value: 'anthropic', label: 'Anthropic', description: 'Claude AI', requiresKey: true },
        { value: 'openai', label: 'OpenAI', description: 'GPT models', requiresKey: true },
      ];

      setLlmProviders(providers);

      const state = useSettingsStore.getState();
      expect(state.llmProviders).toHaveLength(2);
    });

    it('should set video providers', () => {
      const { setVideoProviders } = useSettingsStore.getState();

      const providers = [
        { value: 'replicate', label: 'Replicate', description: 'Cloud video gen', requiresKey: true },
        { value: 'local', label: 'Local', description: 'Local ComfyUI', requiresKey: false },
      ];

      setVideoProviders(providers);

      const state = useSettingsStore.getState();
      expect(state.videoProviders).toHaveLength(2);
    });

    it('should set theme options', () => {
      const { setThemeOptions } = useSettingsStore.getState();

      const options = [
        { value: 'light', label: 'Light' },
        { value: 'dark', label: 'Dark' },
        { value: 'system', label: 'System' },
      ];

      setThemeOptions(options);

      const state = useSettingsStore.getState();
      expect(state.themeOptions).toHaveLength(3);
    });
  });

  describe('Loading States', () => {
    it('should set loading state', () => {
      const { setLoading } = useSettingsStore.getState();

      setLoading(true);
      expect(useSettingsStore.getState().isLoading).toBe(true);

      setLoading(false);
      expect(useSettingsStore.getState().isLoading).toBe(false);
    });

    it('should set saving state', () => {
      const { setSaving } = useSettingsStore.getState();

      setSaving(true);
      expect(useSettingsStore.getState().isSaving).toBe(true);

      setSaving(false);
      expect(useSettingsStore.getState().isSaving).toBe(false);
    });

    it('should set validating state', () => {
      const { setValidating } = useSettingsStore.getState();

      setValidating(true);
      expect(useSettingsStore.getState().isValidating).toBe(true);

      setValidating(false);
      expect(useSettingsStore.getState().isValidating).toBe(false);
    });
  });

  describe('Error Handling', () => {
    it('should set error', () => {
      const { setError } = useSettingsStore.getState();

      setError('Failed to save settings');

      expect(useSettingsStore.getState().error).toBe('Failed to save settings');
    });

    it('should clear error', () => {
      const { setError } = useSettingsStore.getState();

      setError('Some error');
      setError(null);

      expect(useSettingsStore.getState().error).toBeNull();
    });
  });

  describe('Accessibility Settings', () => {
    const mockSettings = {
      id: 'settings-1',
      llmProvider: 'anthropic',
      videoProvider: 'replicate',
      maxConcurrentGenerations: 3,
      generationTimeoutSeconds: 300,
      defaultVideoResolution: '1920x1080',
      defaultVideoFps: 24,
      themeMode: 'dark',
      autoSaveEnabled: true,
      showAdvancedOptions: false,
      autoCleanupTempFiles: true,
      maxCacheSizeGb: 10,
      defaultExportFormat: 'mp4',
      defaultExportQuality: 'high',
      fontSizeScale: 'medium' as const,
      highContrastEnabled: false,
      reduceMotionEnabled: false,
      largeClickTargetsEnabled: false,
      additionalSettings: {},
      createdAt: '2024-01-01',
      updatedAt: '2024-01-01',
    };

    it('should update font size scale', () => {
      const { setSettings, updateSettings } = useSettingsStore.getState();

      setSettings(mockSettings);
      updateSettings({ fontSizeScale: 'large' as const });

      const state = useSettingsStore.getState();
      expect(state.settings?.fontSizeScale).toBe('large');
    });

    it('should update high contrast setting', () => {
      const { setSettings, updateSettings } = useSettingsStore.getState();

      setSettings(mockSettings);
      updateSettings({ highContrastEnabled: true });

      const state = useSettingsStore.getState();
      expect(state.settings?.highContrastEnabled).toBe(true);
    });

    it('should update reduce motion setting', () => {
      const { setSettings, updateSettings } = useSettingsStore.getState();

      setSettings(mockSettings);
      updateSettings({ reduceMotionEnabled: true });

      const state = useSettingsStore.getState();
      expect(state.settings?.reduceMotionEnabled).toBe(true);
    });

    it('should update large click targets setting', () => {
      const { setSettings, updateSettings } = useSettingsStore.getState();

      setSettings(mockSettings);
      updateSettings({ largeClickTargetsEnabled: true });

      const state = useSettingsStore.getState();
      expect(state.settings?.largeClickTargetsEnabled).toBe(true);
    });
  });

  describe('Reset', () => {
    it('should reset all state', () => {
      const { setSettings, setProviderStatuses, setError, reset } = useSettingsStore.getState();

      // Modify state
      setSettings({
        id: 'settings-1',
        llmProvider: 'anthropic',
        videoProvider: 'replicate',
        maxConcurrentGenerations: 3,
        generationTimeoutSeconds: 300,
        defaultVideoResolution: '1920x1080',
        defaultVideoFps: 24,
        themeMode: 'dark',
        autoSaveEnabled: true,
        showAdvancedOptions: false,
        autoCleanupTempFiles: true,
        maxCacheSizeGb: 10,
        defaultExportFormat: 'mp4',
        defaultExportQuality: 'high',
        fontSizeScale: 'medium' as const,
        highContrastEnabled: false,
        reduceMotionEnabled: false,
        largeClickTargetsEnabled: false,
        additionalSettings: {},
        createdAt: '2024-01-01',
        updatedAt: '2024-01-01',
      });
      setProviderStatuses([{ provider: 'test', name: 'Test', available: true, configured: true, message: 'OK', latencyMs: 50 }]);
      setError('Some error');

      // Reset
      reset();

      const state = useSettingsStore.getState();
      expect(state.settings).toBeNull();
      expect(state.providerStatuses).toEqual([]);
      expect(state.error).toBeNull();
    });
  });
});
