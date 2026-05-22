/**
 * GPU Exchange state store using Zustand.
 *
 * Manages GPU provider selection, pricing, routing, and budget tracking
 * for the GPU Exchange marketplace.
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';
import {
  api,
  type GPUProviderInfo,
  type GPUProviderHealth,
  type GPUPricing,
  type GPUPricingComparison,
  type GPUProviderSelection,
  type GPURoutingStats,
  type GPURoutingConfig,
  type GPUTypeInfo,
  type GPUCostEstimate,
} from '../api/client';

interface GPUExchangeStoreState {
  // Providers
  providers: GPUProviderInfo[];
  providersHealth: Record<string, GPUProviderHealth>;
  healthyCount: number;

  // Selected configuration
  selectedGPUType: string;
  selectedProvider: string | null;
  selectedRegion: string;
  routingPriority: 'low' | 'normal' | 'high' | 'urgent';
  allowSpot: boolean;
  maxPriceUsd: number | null;

  // Pricing
  pricingCache: Record<string, GPUPricing>;
  pricingComparison: GPUPricingComparison | null;
  lastCostEstimate: GPUCostEstimate | null;

  // Routing
  lastProviderSelection: GPUProviderSelection | null;
  routingStats: GPURoutingStats | null;

  // Reference data
  gpuTypes: GPUTypeInfo[];

  // Budget
  projectBudgets: Record<string, number>;

  // Loading states
  isLoadingProviders: boolean;
  isLoadingHealth: boolean;
  isLoadingPricing: boolean;
  isLoadingRouting: boolean;

  // Error state
  error: string | null;

  // Actions - Provider management
  setProviders: (providers: GPUProviderInfo[]) => void;
  setProvidersHealth: (health: Record<string, GPUProviderHealth>, healthyCount: number) => void;

  // Actions - Configuration
  setSelectedGPUType: (gpuType: string) => void;
  setSelectedProvider: (provider: string | null) => void;
  setSelectedRegion: (region: string) => void;
  setRoutingPriority: (priority: 'low' | 'normal' | 'high' | 'urgent') => void;
  setAllowSpot: (allow: boolean) => void;
  setMaxPriceUsd: (price: number | null) => void;

  // Actions - Pricing
  setPricingCache: (key: string, pricing: GPUPricing) => void;
  setPricingComparison: (comparison: GPUPricingComparison | null) => void;
  setLastCostEstimate: (estimate: GPUCostEstimate | null) => void;

  // Actions - Routing
  setLastProviderSelection: (selection: GPUProviderSelection | null) => void;
  setRoutingStats: (stats: GPURoutingStats | null) => void;

  // Actions - Reference data
  setGPUTypes: (types: GPUTypeInfo[]) => void;

  // Actions - Budget
  setProjectBudget: (projectId: string, budget: number) => void;

  // Actions - Loading states
  setLoadingProviders: (loading: boolean) => void;
  setLoadingHealth: (loading: boolean) => void;
  setLoadingPricing: (loading: boolean) => void;
  setLoadingRouting: (loading: boolean) => void;
  setError: (error: string | null) => void;

  // Async actions
  fetchProviders: () => Promise<void>;
  fetchProvidersHealth: () => Promise<void>;
  fetchGPUTypes: () => Promise<void>;
  fetchPricingComparison: (gpuType?: string, region?: string) => Promise<void>;
  fetchRoutingStats: () => Promise<void>;
  selectOptimalProvider: (params: {
    gpuType: string;
    durationSeconds: number;
    requiredCapability?: string;
  }) => Promise<GPUProviderSelection | null>;
  estimateCost: (params: {
    gpuType: string;
    durationSeconds: number;
    providerId?: string;
    useSpot?: boolean;
  }) => Promise<GPUCostEstimate | null>;
  setBudgetLimit: (projectId: string, limitUsd: number) => Promise<boolean>;
  checkBudget: (
    projectId: string,
    estimatedCost: number,
    currentSpent?: number
  ) => Promise<{
    allowed: boolean;
    warning?: string;
  }>;

  // Computed helpers
  getProviderById: (id: string) => GPUProviderInfo | undefined;
  getHealthyProviders: () => GPUProviderInfo[];
  getProvidersForGPUType: (gpuType: string) => GPUProviderInfo[];
  getCurrentRoutingConfig: () => GPURoutingConfig;
  getBestValueProvider: () => string | null;
}

const initialState = {
  providers: [],
  providersHealth: {},
  healthyCount: 0,
  selectedGPUType: 'a100_80gb',
  selectedProvider: null,
  selectedRegion: 'us-east-1',
  routingPriority: 'normal' as const,
  allowSpot: true,
  maxPriceUsd: null,
  pricingCache: {},
  pricingComparison: null,
  lastCostEstimate: null,
  lastProviderSelection: null,
  routingStats: null,
  gpuTypes: [],
  projectBudgets: {},
  isLoadingProviders: false,
  isLoadingHealth: false,
  isLoadingPricing: false,
  isLoadingRouting: false,
  error: null,
};

export const useGPUExchangeStore = create<GPUExchangeStoreState>()(
  devtools(
    persist(
      immer((set, get) => ({
        ...initialState,

        // Provider management
        setProviders: (providers) =>
          set((state) => {
            state.providers = providers;
          }),

        setProvidersHealth: (health, healthyCount) =>
          set((state) => {
            state.providersHealth = health;
            state.healthyCount = healthyCount;
          }),

        // Configuration
        setSelectedGPUType: (gpuType) =>
          set((state) => {
            state.selectedGPUType = gpuType;
            // Clear pricing comparison when GPU type changes
            state.pricingComparison = null;
          }),

        setSelectedProvider: (provider) =>
          set((state) => {
            state.selectedProvider = provider;
          }),

        setSelectedRegion: (region) =>
          set((state) => {
            state.selectedRegion = region;
          }),

        setRoutingPriority: (priority) =>
          set((state) => {
            state.routingPriority = priority;
          }),

        setAllowSpot: (allow) =>
          set((state) => {
            state.allowSpot = allow;
          }),

        setMaxPriceUsd: (price) =>
          set((state) => {
            state.maxPriceUsd = price;
          }),

        // Pricing
        setPricingCache: (key, pricing) =>
          set((state) => {
            state.pricingCache[key] = pricing;
          }),

        setPricingComparison: (comparison) =>
          set((state) => {
            state.pricingComparison = comparison;
          }),

        setLastCostEstimate: (estimate) =>
          set((state) => {
            state.lastCostEstimate = estimate;
          }),

        // Routing
        setLastProviderSelection: (selection) =>
          set((state) => {
            state.lastProviderSelection = selection;
          }),

        setRoutingStats: (stats) =>
          set((state) => {
            state.routingStats = stats;
          }),

        // Reference data
        setGPUTypes: (types) =>
          set((state) => {
            state.gpuTypes = types;
          }),

        // Budget
        setProjectBudget: (projectId, budget) =>
          set((state) => {
            state.projectBudgets[projectId] = budget;
          }),

        // Loading states
        setLoadingProviders: (loading) =>
          set((state) => {
            state.isLoadingProviders = loading;
          }),

        setLoadingHealth: (loading) =>
          set((state) => {
            state.isLoadingHealth = loading;
          }),

        setLoadingPricing: (loading) =>
          set((state) => {
            state.isLoadingPricing = loading;
          }),

        setLoadingRouting: (loading) =>
          set((state) => {
            state.isLoadingRouting = loading;
          }),

        setError: (error) =>
          set((state) => {
            state.error = error;
          }),

        // Async actions
        fetchProviders: async () => {
          set((state) => {
            state.isLoadingProviders = true;
            state.error = null;
          });
          try {
            const providers = await api.listGPUProviders();
            set((state) => {
              state.providers = providers;
              state.isLoadingProviders = false;
            });
          } catch (error) {
            console.error('Failed to fetch GPU providers:', error);
            set((state) => {
              state.isLoadingProviders = false;
              state.error = 'Failed to fetch GPU providers';
            });
          }
        },

        fetchProvidersHealth: async () => {
          set((state) => {
            state.isLoadingHealth = true;
          });
          try {
            const result = await api.getAllGPUProvidersHealth();
            set((state) => {
              state.providersHealth = result.providers;
              state.healthyCount = result.healthy_count;
              state.isLoadingHealth = false;
            });
          } catch (error) {
            console.error('Failed to fetch providers health:', error);
            set((state) => {
              state.isLoadingHealth = false;
            });
          }
        },

        fetchGPUTypes: async () => {
          try {
            const types = await api.listGPUTypes();
            set((state) => {
              state.gpuTypes = types;
            });
          } catch (error) {
            console.error('Failed to fetch GPU types:', error);
          }
        },

        fetchPricingComparison: async (gpuType, region) => {
          const state = get();
          const targetGPUType = gpuType || state.selectedGPUType;
          const targetRegion = region || state.selectedRegion;

          set((s) => {
            s.isLoadingPricing = true;
          });
          try {
            const comparison = await api.compareGPUPricing(targetGPUType, targetRegion);
            set((s) => {
              s.pricingComparison = comparison;
              s.isLoadingPricing = false;
            });
          } catch (error) {
            console.error('Failed to fetch pricing comparison:', error);
            set((s) => {
              s.isLoadingPricing = false;
            });
          }
        },

        fetchRoutingStats: async () => {
          try {
            const stats = await api.getGPURoutingStats();
            set((state) => {
              state.routingStats = stats;
            });
          } catch (error) {
            console.error('Failed to fetch routing stats:', error);
          }
        },

        selectOptimalProvider: async (params) => {
          const state = get();
          set((s) => {
            s.isLoadingRouting = true;
          });
          try {
            const selection = await api.selectGPUProvider({
              gpuType: params.gpuType,
              durationSeconds: params.durationSeconds,
              config: state.getCurrentRoutingConfig(),
              requiredCapability: params.requiredCapability,
            });
            set((s) => {
              s.lastProviderSelection = selection;
              s.isLoadingRouting = false;
            });
            return selection;
          } catch (error) {
            console.error('Failed to select optimal provider:', error);
            set((s) => {
              s.isLoadingRouting = false;
            });
            return null;
          }
        },

        estimateCost: async (params) => {
          try {
            const estimate = await api.estimateGPUCost(params);
            set((state) => {
              state.lastCostEstimate = estimate;
            });
            return estimate;
          } catch (error) {
            console.error('Failed to estimate cost:', error);
            return null;
          }
        },

        setBudgetLimit: async (projectId, limitUsd) => {
          try {
            await api.setGPUBudgetLimit(projectId, limitUsd);
            set((state) => {
              state.projectBudgets[projectId] = limitUsd;
            });
            return true;
          } catch (error) {
            console.error('Failed to set budget limit:', error);
            return false;
          }
        },

        checkBudget: async (projectId, estimatedCost, currentSpent) => {
          try {
            return await api.checkGPUBudget({
              projectId,
              estimatedCost,
              currentSpent,
            });
          } catch (error) {
            console.error('Failed to check budget:', error);
            return { allowed: true };
          }
        },

        // Computed helpers
        getProviderById: (id) => {
          return get().providers.find((p) => p.id === id);
        },

        getHealthyProviders: () => {
          const state = get();
          return state.providers.filter((p) => state.providersHealth[p.id]?.available);
        },

        getProvidersForGPUType: (gpuType) => {
          return get().providers.filter((p) => p.supported_gpu_types.includes(gpuType));
        },

        getCurrentRoutingConfig: () => {
          const state = get();
          return {
            priority: state.routingPriority,
            max_price_usd: state.maxPriceUsd ?? undefined,
            preferred_providers: state.selectedProvider ? [state.selectedProvider] : [],
            preferred_regions: [state.selectedRegion],
            allow_spot: state.allowSpot,
          };
        },

        getBestValueProvider: () => {
          const state = get();
          return state.pricingComparison?.best_value_provider ?? null;
        },
      })),
      {
        name: 'scenemachine-gpu-exchange-store',
        partialize: (state) => ({
          // Only persist configuration preferences
          selectedGPUType: state.selectedGPUType,
          selectedProvider: state.selectedProvider,
          selectedRegion: state.selectedRegion,
          routingPriority: state.routingPriority,
          allowSpot: state.allowSpot,
          maxPriceUsd: state.maxPriceUsd,
          projectBudgets: state.projectBudgets,
        }),
      }
    ),
    { name: 'GPUExchangeStore' }
  )
);

/**
 * Hook to get the cheapest available provider for a GPU type.
 */
export function useCheapestProvider(): string | null {
  return useGPUExchangeStore((state) => state.pricingComparison?.cheapest_provider ?? null);
}

/**
 * Hook to get the fastest available provider for a GPU type.
 */
export function useFastestProvider(): string | null {
  return useGPUExchangeStore((state) => state.pricingComparison?.fastest_provider ?? null);
}

/**
 * Hook to check if any GPU providers are available.
 */
export function useHasAvailableProviders(): boolean {
  return useGPUExchangeStore((state) => state.healthyCount > 0);
}

/**
 * Hook to get GPU type options for selection.
 */
export function useGPUTypeOptions(): Array<{ value: string; label: string }> {
  return useGPUExchangeStore((state) =>
    state.gpuTypes.map((t) => ({ value: t.id, label: t.name }))
  );
}
