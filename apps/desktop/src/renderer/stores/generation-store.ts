/**
 * Generation state store using Zustand.
 *
 * Manages video generation settings including provider selection,
 * model selection, and cost estimation.
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';
import { api, type ProviderModel, type ProviderHealth, type WorkerStatus } from '../api/client';

interface GenerationStoreState {
  // Provider and model selection
  selectedProvider: string;
  selectedModel: string | null;
  availableModels: Record<string, ProviderModel[]>;
  providersHealth: ProviderHealth[];

  // Worker status
  workerStatus: WorkerStatus | null;

  // Cost estimation cache
  lastCostEstimate: {
    provider: string;
    model: string;
    durationSeconds: number;
    costPerShot: number;
    totalCost: number;
  } | null;

  // Loading states
  isLoadingModels: boolean;
  isLoadingHealth: boolean;

  // Actions
  setSelectedProvider: (provider: string) => void;
  setSelectedModel: (model: string | null) => void;
  setAvailableModels: (provider: string, models: ProviderModel[]) => void;
  setProvidersHealth: (health: ProviderHealth[]) => void;
  setWorkerStatus: (status: WorkerStatus | null) => void;
  setLastCostEstimate: (estimate: GenerationStoreState['lastCostEstimate']) => void;
  setLoadingModels: (loading: boolean) => void;
  setLoadingHealth: (loading: boolean) => void;

  // Convenience aliases
  setProvider: (provider: string) => void;
  setModel: (model: string | null) => void;

  // Async actions
  fetchProvidersHealth: () => Promise<void>;
  fetchModelsForProvider: (provider: string) => Promise<void>;
  fetchWorkerStatus: () => Promise<void>;
  pauseWorker: () => Promise<boolean>;
  resumeWorker: () => Promise<boolean>;

  // Computed helpers
  getCurrentModel: () => ProviderModel | null;
  getModelsForProvider: (provider: string) => ProviderModel[];
}

const initialState = {
  selectedProvider: 'replicate',
  selectedModel: null,
  availableModels: {},
  providersHealth: [],
  workerStatus: null,
  lastCostEstimate: null,
  isLoadingModels: false,
  isLoadingHealth: false,
};

export const useGenerationStore = create<GenerationStoreState>()(
  devtools(
    persist(
      immer((set, get) => ({
        ...initialState,

        setSelectedProvider: (provider) =>
          set((state) => {
            state.selectedProvider = provider;
            // Reset model when provider changes
            const models = state.availableModels[provider];
            state.selectedModel = models?.[0]?.id ?? null;
          }),

        setSelectedModel: (model) =>
          set((state) => {
            state.selectedModel = model;
          }),

        setAvailableModels: (provider, models) =>
          set((state) => {
            state.availableModels[provider] = models;
            // Auto-select first model if none selected for this provider
            if (state.selectedProvider === provider && !state.selectedModel && models.length > 0) {
              state.selectedModel = models[0].id;
            }
          }),

        setProvidersHealth: (health) =>
          set((state) => {
            state.providersHealth = health;
          }),

        setWorkerStatus: (status) =>
          set((state) => {
            state.workerStatus = status;
          }),

        setLastCostEstimate: (estimate) =>
          set((state) => {
            state.lastCostEstimate = estimate;
          }),

        setLoadingModels: (loading) =>
          set((state) => {
            state.isLoadingModels = loading;
          }),

        setLoadingHealth: (loading) =>
          set((state) => {
            state.isLoadingHealth = loading;
          }),

        getCurrentModel: () => {
          const state = get();
          const models = state.availableModels[state.selectedProvider];
          if (!models || !state.selectedModel) return null;
          return models.find((m) => m.id === state.selectedModel) ?? null;
        },

        getModelsForProvider: (provider) => {
          return get().availableModels[provider] ?? [];
        },

        // Convenience aliases
        setProvider: (provider) =>
          set((state) => {
            state.selectedProvider = provider;
            const models = state.availableModels[provider];
            state.selectedModel = models?.[0]?.id ?? null;
          }),

        setModel: (model) =>
          set((state) => {
            state.selectedModel = model;
          }),

        // Async actions
        fetchProvidersHealth: async () => {
          set((state) => {
            state.isLoadingHealth = true;
          });
          try {
            const health = await api.getProvidersHealth();
            set((state) => {
              state.providersHealth = health;
              state.isLoadingHealth = false;
            });
          } catch (error) {
            console.error('Failed to fetch providers health:', error);
            set((state) => {
              state.isLoadingHealth = false;
            });
          }
        },

        fetchModelsForProvider: async (provider) => {
          set((state) => {
            state.isLoadingModels = true;
          });
          try {
            const models = await api.getProviderModels(provider);
            set((state) => {
              state.availableModels[provider] = models;
              state.isLoadingModels = false;
              // Auto-select first model if none selected
              if (
                state.selectedProvider === provider &&
                !state.selectedModel &&
                models.length > 0
              ) {
                state.selectedModel = models[0].id;
              }
            });
          } catch (error) {
            console.error('Failed to fetch models for provider:', error);
            set((state) => {
              state.isLoadingModels = false;
            });
          }
        },

        fetchWorkerStatus: async () => {
          try {
            const status = await api.getWorkerStatus();
            set((state) => {
              state.workerStatus = status;
            });
          } catch (error) {
            console.error('Failed to fetch worker status:', error);
          }
        },

        pauseWorker: async () => {
          try {
            const result = await api.pauseWorker();
            if (result.success) {
              set((state) => {
                if (state.workerStatus) {
                  state.workerStatus.is_paused = true;
                }
              });
            }
            return result.success;
          } catch (error) {
            console.error('Failed to pause worker:', error);
            return false;
          }
        },

        resumeWorker: async () => {
          try {
            const result = await api.resumeWorker();
            if (result.success) {
              set((state) => {
                if (state.workerStatus) {
                  state.workerStatus.is_paused = false;
                }
              });
            }
            return result.success;
          } catch (error) {
            console.error('Failed to resume worker:', error);
            return false;
          }
        },
      })),
      {
        name: 'scenemachine-generation-store',
        partialize: (state) => ({
          // Only persist provider/model selection
          selectedProvider: state.selectedProvider,
          selectedModel: state.selectedModel,
        }),
      }
    ),
    { name: 'GenerationStore' }
  )
);

/**
 * Hook to get the currently selected model info.
 */
export function useCurrentModel(): ProviderModel | null {
  return useGenerationStore((state) => {
    const models = state.availableModels[state.selectedProvider];
    if (!models || !state.selectedModel) return null;
    return models.find((m) => m.id === state.selectedModel) ?? null;
  });
}

/**
 * Hook to check if generation is ready (provider configured and model selected).
 */
export function useGenerationReady(): boolean {
  return useGenerationStore((state) => {
    const health = state.providersHealth.find((p) => p.provider === state.selectedProvider);
    return !!(health?.configured && health?.available && state.selectedModel);
  });
}
