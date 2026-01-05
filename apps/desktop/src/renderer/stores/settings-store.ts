/**
 * Global settings state store using Zustand.
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';

// Types for settings
export interface ApiKeyInfo {
  configured: boolean;
  masked: string | null;
}

export interface ApiKeys {
  anthropic: ApiKeyInfo;
  openai: ApiKeyInfo;
  replicate: ApiKeyInfo;
  fal: ApiKeyInfo;
  runwayml: ApiKeyInfo;
  elevenlabs: ApiKeyInfo;
}

export type FontSizeScale = 'small' | 'medium' | 'large' | 'extra-large';

export interface UserSettings {
  id: string;
  llmProvider: string;
  videoProvider: string;
  maxConcurrentGenerations: number;
  generationTimeoutSeconds: number;
  defaultVideoResolution: string;
  defaultVideoFps: number;
  themeMode: string;
  autoSaveEnabled: boolean;
  showAdvancedOptions: boolean;
  autoCleanupTempFiles: boolean;
  maxCacheSizeGb: number;
  defaultExportFormat: string;
  defaultExportQuality: string;
  // Accessibility settings
  fontSizeScale: FontSizeScale;
  highContrastEnabled: boolean;
  reduceMotionEnabled: boolean;
  largeClickTargetsEnabled: boolean;
  additionalSettings: Record<string, any>;
  apiKeys?: ApiKeys;
  createdAt: string | null;
  updatedAt: string | null;
}

export interface ProviderStatus {
  provider: string;
  name: string;
  available: boolean;
  configured: boolean;
  message: string;
  latencyMs: number | null;
}

export interface StorageStats {
  dataDir: string;
  uploadDir: string;
  outputDir: string;
  cacheDir: string;
  totalSizeBytes: number;
  uploadSizeBytes: number;
  outputSizeBytes: number;
  cacheSizeBytes: number;
  tempFilesCount: number;
}

export interface ProviderOption {
  value: string;
  label: string;
  description: string;
  requiresKey?: boolean;
}

export interface ThemeOption {
  value: string;
  label: string;
}

interface SettingsStoreState {
  // Settings data
  settings: UserSettings | null;
  providerStatuses: ProviderStatus[];
  storageStats: StorageStats | null;

  // Options (cached reference data)
  llmProviders: ProviderOption[];
  videoProviders: ProviderOption[];
  themeOptions: ThemeOption[];

  // Loading states
  isLoading: boolean;
  isSaving: boolean;
  isValidating: boolean;

  // Error state
  error: string | null;

  // Actions
  setSettings: (settings: UserSettings) => void;
  updateSettings: (updates: Partial<UserSettings>) => void;
  setProviderStatuses: (statuses: ProviderStatus[]) => void;
  setStorageStats: (stats: StorageStats) => void;
  setLlmProviders: (providers: ProviderOption[]) => void;
  setVideoProviders: (providers: ProviderOption[]) => void;
  setThemeOptions: (options: ThemeOption[]) => void;
  setLoading: (loading: boolean) => void;
  setSaving: (saving: boolean) => void;
  setValidating: (validating: boolean) => void;
  setError: (error: string | null) => void;
  reset: () => void;

  // Async actions (to be used with IPC)
  fetchSettings: () => Promise<void>;
  saveSettings: (updates: Partial<UserSettings>) => Promise<void>;
  setApiKey: (provider: string, apiKey: string) => Promise<void>;
  removeApiKey: (provider: string) => Promise<void>;
  validateApiKey: (provider: string, apiKey?: string) => Promise<ProviderStatus>;
  checkAllProviders: () => Promise<void>;
  fetchStorageStats: () => Promise<void>;
  clearCache: (cacheType: string) => Promise<{ bytesFreed: number }>;
  fetchProviderOptions: () => Promise<void>;
}

const initialState = {
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
};

export const useSettingsStore = create<SettingsStoreState>()(
  devtools(
    persist(
      immer((set, get) => ({
        ...initialState,

        setSettings: (settings) =>
          set((state) => {
            state.settings = settings;
            state.error = null;
          }),

        updateSettings: (updates) =>
          set((state) => {
            if (state.settings) {
              Object.assign(state.settings, updates);
            }
          }),

        setProviderStatuses: (statuses) =>
          set((state) => {
            state.providerStatuses = statuses;
          }),

        setStorageStats: (stats) =>
          set((state) => {
            state.storageStats = stats;
          }),

        setLlmProviders: (providers) =>
          set((state) => {
            state.llmProviders = providers;
          }),

        setVideoProviders: (providers) =>
          set((state) => {
            state.videoProviders = providers;
          }),

        setThemeOptions: (options) =>
          set((state) => {
            state.themeOptions = options;
          }),

        setLoading: (loading) =>
          set((state) => {
            state.isLoading = loading;
          }),

        setSaving: (saving) =>
          set((state) => {
            state.isSaving = saving;
          }),

        setValidating: (validating) =>
          set((state) => {
            state.isValidating = validating;
          }),

        setError: (error) =>
          set((state) => {
            state.error = error;
          }),

        reset: () => set(initialState),

        // Async actions
        fetchSettings: async () => {
          set((state) => {
            state.isLoading = true;
            state.error = null;
          });

          try {
            const settings = await window.electronAPI.backendRequest<UserSettings>(
              'settings.get',
              {}
            );
            set((state) => {
              state.settings = settings;
              state.isLoading = false;
            });
          } catch (error) {
            set((state) => {
              state.error = error instanceof Error ? error.message : 'Failed to fetch settings';
              state.isLoading = false;
            });
          }
        },

        saveSettings: async (updates) => {
          set((state) => {
            state.isSaving = true;
            state.error = null;
          });

          try {
            // Map camelCase to snake_case for backend
            const backendParams: Record<string, any> = {};
            const fieldMap: Record<string, string> = {
              llmProvider: 'llm_provider',
              videoProvider: 'video_provider',
              maxConcurrentGenerations: 'max_concurrent_generations',
              generationTimeoutSeconds: 'generation_timeout_seconds',
              defaultVideoResolution: 'default_video_resolution',
              defaultVideoFps: 'default_video_fps',
              themeMode: 'theme_mode',
              autoSaveEnabled: 'auto_save_enabled',
              showAdvancedOptions: 'show_advanced_options',
              autoCleanupTempFiles: 'auto_cleanup_temp_files',
              maxCacheSizeGb: 'max_cache_size_gb',
              defaultExportFormat: 'default_export_format',
              defaultExportQuality: 'default_export_quality',
              // Accessibility settings
              fontSizeScale: 'font_size_scale',
              highContrastEnabled: 'high_contrast_enabled',
              reduceMotionEnabled: 'reduce_motion_enabled',
              largeClickTargetsEnabled: 'large_click_targets_enabled',
            };

            for (const [camel, snake] of Object.entries(fieldMap)) {
              if (camel in updates) {
                backendParams[snake] = (updates as any)[camel];
              }
            }

            const settings = await window.electronAPI.backendRequest<UserSettings>(
              'settings.update',
              backendParams
            );
            set((state) => {
              state.settings = settings;
              state.isSaving = false;
            });
          } catch (error) {
            set((state) => {
              state.error = error instanceof Error ? error.message : 'Failed to save settings';
              state.isSaving = false;
            });
            throw error;
          }
        },

        setApiKey: async (provider, apiKey) => {
          set((state) => {
            state.isSaving = true;
            state.error = null;
          });

          try {
            await window.electronAPI.backendRequest('settings.setApiKey', {
              provider,
              api_key: apiKey,
            });
            // Refresh settings to get updated key info
            await get().fetchSettings();
            set((state) => {
              state.isSaving = false;
            });
          } catch (error) {
            set((state) => {
              state.error = error instanceof Error ? error.message : 'Failed to set API key';
              state.isSaving = false;
            });
            throw error;
          }
        },

        removeApiKey: async (provider) => {
          set((state) => {
            state.isSaving = true;
            state.error = null;
          });

          try {
            await window.electronAPI.backendRequest('settings.removeApiKey', {
              provider,
            });
            // Refresh settings to get updated key info
            await get().fetchSettings();
            set((state) => {
              state.isSaving = false;
            });
          } catch (error) {
            set((state) => {
              state.error = error instanceof Error ? error.message : 'Failed to remove API key';
              state.isSaving = false;
            });
            throw error;
          }
        },

        validateApiKey: async (provider, apiKey) => {
          set((state) => {
            state.isValidating = true;
          });

          try {
            const status = await window.electronAPI.backendRequest<ProviderStatus>(
              'settings.validateApiKey',
              { provider, api_key: apiKey }
            );
            set((state) => {
              state.isValidating = false;
            });
            return status;
          } catch (error) {
            set((state) => {
              state.isValidating = false;
            });
            throw error;
          }
        },

        checkAllProviders: async () => {
          set((state) => {
            state.isValidating = true;
          });

          try {
            const statuses = await window.electronAPI.backendRequest<ProviderStatus[]>(
              'settings.checkProviders',
              {}
            );
            set((state) => {
              state.providerStatuses = statuses;
              state.isValidating = false;
            });
          } catch (error) {
            set((state) => {
              state.isValidating = false;
              state.error = error instanceof Error ? error.message : 'Failed to check providers';
            });
          }
        },

        fetchStorageStats: async () => {
          try {
            const stats = await window.electronAPI.backendRequest<StorageStats>(
              'settings.getStorageStats',
              {}
            );
            set((state) => {
              state.storageStats = stats;
            });
          } catch (error) {
            set((state) => {
              state.error = error instanceof Error ? error.message : 'Failed to fetch storage stats';
            });
          }
        },

        clearCache: async (cacheType) => {
          try {
            const result = await window.electronAPI.backendRequest<{
              modelCacheCleared: number;
              tempFilesCleared: number;
              bytesFreed: number;
            }>('settings.clearCache', { cache_type: cacheType });
            // Refresh storage stats
            await get().fetchStorageStats();
            return { bytesFreed: result.bytesFreed };
          } catch (error) {
            set((state) => {
              state.error = error instanceof Error ? error.message : 'Failed to clear cache';
            });
            throw error;
          }
        },

        fetchProviderOptions: async () => {
          try {
            const [llmProviders, videoProviders, themeOptions] = await Promise.all([
              window.electronAPI.backendRequest<ProviderOption[]>(
                'settings.getLlmProviders',
                {}
              ),
              window.electronAPI.backendRequest<ProviderOption[]>(
                'settings.getVideoProviders',
                {}
              ),
              window.electronAPI.backendRequest<ThemeOption[]>(
                'settings.getThemeOptions',
                {}
              ),
            ]);

            set((state) => {
              state.llmProviders = llmProviders;
              state.videoProviders = videoProviders;
              state.themeOptions = themeOptions;
            });
          } catch (error) {
            set((state) => {
              state.error =
                error instanceof Error ? error.message : 'Failed to fetch provider options';
            });
          }
        },
      })),
      {
        name: 'scenemachine-settings-store',
        partialize: (state) => ({
          // Persist theme and accessibility preferences locally for quick loading
          settings: state.settings
            ? {
                themeMode: state.settings.themeMode,
                fontSizeScale: state.settings.fontSizeScale,
                highContrastEnabled: state.settings.highContrastEnabled,
                reduceMotionEnabled: state.settings.reduceMotionEnabled,
                largeClickTargetsEnabled: state.settings.largeClickTargetsEnabled,
              }
            : null,
        }),
      }
    ),
    { name: 'SettingsStore' }
  )
);
