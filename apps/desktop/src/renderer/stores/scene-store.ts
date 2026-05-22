/**
 * Scene state store using Zustand.
 *
 * Manages scene data, analysis, and shot breakdown generation.
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';
import {
  api,
  type Scene,
  type SceneAnalysis,
  type ShotBreakdown,
  type ShotTypeInfo,
  type CameraMovementInfo,
} from '../api/client';

interface SceneStoreState {
  // Scenes list
  scenes: Scene[];
  sceneMap: Record<string, Scene>;

  // Currently selected scene
  selectedSceneId: string | null;
  selectedScene: Scene | null;

  // Scene analysis cache
  analysisCache: Record<string, SceneAnalysis>;

  // Reference data
  shotTypes: ShotTypeInfo[];
  cameraMovements: CameraMovementInfo[];

  // Loading states
  isLoading: boolean;
  isAnalyzing: string | null; // scene ID being analyzed
  isGeneratingBreakdown: string | null; // scene ID generating breakdown
  error: string | null;

  // Actions - State setters
  setScenes: (scenes: Scene[]) => void;
  setSelectedSceneId: (id: string | null) => void;
  setError: (error: string | null) => void;

  // Async actions - List & Get
  fetchScenes: (projectId: string, includeShots?: boolean) => Promise<Scene[]>;
  fetchScene: (sceneId: string, includeShots?: boolean) => Promise<Scene | null>;

  // Async actions - Analysis
  analyzeScene: (sceneId: string) => Promise<SceneAnalysis | null>;

  // Async actions - Shot breakdown
  generateShotBreakdown: (sceneId: string, regenerate?: boolean) => Promise<ShotBreakdown | null>;
  approveSceneBreakdown: (sceneId: string) => Promise<boolean>;

  // Async actions - Reference data
  fetchShotTypes: () => Promise<ShotTypeInfo[]>;
  fetchCameraMovements: () => Promise<CameraMovementInfo[]>;

  // Computed helpers
  getSceneById: (id: string) => Scene | undefined;
  getScenesByState: (state: Scene['state']) => Scene[];
  getScenesReadyForGeneration: () => Scene[];
  getScenesNeedingBreakdown: () => Scene[];
  getSceneAnalysis: (sceneId: string) => SceneAnalysis | undefined;
  getTotalShotCount: () => number;

  // Reset
  reset: () => void;
}

const initialState = {
  scenes: [],
  sceneMap: {},
  selectedSceneId: null,
  selectedScene: null,
  analysisCache: {},
  shotTypes: [],
  cameraMovements: [],
  isLoading: false,
  isAnalyzing: null,
  isGeneratingBreakdown: null,
  error: null,
};

export const useSceneStore = create<SceneStoreState>()(
  devtools(
    immer((set, get) => ({
      ...initialState,

      // State setters
      setScenes: (scenes) =>
        set((state) => {
          state.scenes = scenes;
          state.sceneMap = {};
          scenes.forEach((s) => {
            state.sceneMap[s.id] = s;
          });
        }),

      setSelectedSceneId: (id) =>
        set((state) => {
          state.selectedSceneId = id;
          state.selectedScene = id ? (state.sceneMap[id] ?? null) : null;
        }),

      setError: (error) =>
        set((state) => {
          state.error = error;
        }),

      // Async actions - List & Get
      fetchScenes: async (projectId, includeShots = false) => {
        set((state) => {
          state.isLoading = true;
          state.error = null;
        });
        try {
          const scenes = await api.listScenes(projectId, includeShots);
          set((state) => {
            state.scenes = scenes;
            state.sceneMap = {};
            scenes.forEach((s) => {
              state.sceneMap[s.id] = s;
            });
            state.isLoading = false;
          });
          return scenes;
        } catch (error) {
          console.error('Failed to fetch scenes:', error);
          set((state) => {
            state.isLoading = false;
            state.error = 'Failed to fetch scenes';
          });
          return [];
        }
      },

      fetchScene: async (sceneId, includeShots = true) => {
        set((state) => {
          state.isLoading = true;
          state.error = null;
        });
        try {
          const scene = await api.getScene(sceneId, includeShots);
          set((state) => {
            state.sceneMap[sceneId] = scene;
            const idx = state.scenes.findIndex((s) => s.id === sceneId);
            if (idx >= 0) {
              state.scenes[idx] = scene;
            } else {
              state.scenes.push(scene);
            }
            if (state.selectedSceneId === sceneId) {
              state.selectedScene = scene;
            }
            state.isLoading = false;
          });
          return scene;
        } catch (error) {
          console.error('Failed to fetch scene:', error);
          set((state) => {
            state.isLoading = false;
            state.error = 'Failed to fetch scene';
          });
          return null;
        }
      },

      // Async actions - Analysis
      analyzeScene: async (sceneId) => {
        set((state) => {
          state.isAnalyzing = sceneId;
          state.error = null;
        });
        try {
          const analysis = await api.analyzeScene(sceneId);
          set((state) => {
            state.analysisCache[sceneId] = analysis;
            // Update scene state if needed
            const existing = state.sceneMap[sceneId];
            if (existing && existing.state === 'draft') {
              const updated = { ...existing, state: 'analyzed' as const };
              state.sceneMap[sceneId] = updated;
              const idx = state.scenes.findIndex((s) => s.id === sceneId);
              if (idx >= 0) {
                state.scenes[idx] = updated;
              }
              if (state.selectedSceneId === sceneId) {
                state.selectedScene = updated;
              }
            }
            state.isAnalyzing = null;
          });
          return analysis;
        } catch (error) {
          console.error('Failed to analyze scene:', error);
          set((state) => {
            state.isAnalyzing = null;
            state.error = 'Failed to analyze scene';
          });
          return null;
        }
      },

      // Async actions - Shot breakdown
      generateShotBreakdown: async (sceneId, regenerate = false) => {
        set((state) => {
          state.isGeneratingBreakdown = sceneId;
          state.error = null;
        });
        try {
          const breakdown = await api.generateShotBreakdown(sceneId, regenerate);
          set((state) => {
            // Update scene with breakdown data
            const existing = state.sceneMap[sceneId];
            if (existing) {
              const updated = {
                ...existing,
                state: 'breakdown_generated' as const,
                shotCount: breakdown.shots.length,
                shots: breakdown.shots,
              };
              state.sceneMap[sceneId] = updated;
              const idx = state.scenes.findIndex((s) => s.id === sceneId);
              if (idx >= 0) {
                state.scenes[idx] = updated;
              }
              if (state.selectedSceneId === sceneId) {
                state.selectedScene = updated;
              }
            }
            state.isGeneratingBreakdown = null;
          });
          return breakdown;
        } catch (error) {
          console.error('Failed to generate shot breakdown:', error);
          set((state) => {
            state.isGeneratingBreakdown = null;
            state.error = 'Failed to generate shot breakdown';
          });
          return null;
        }
      },

      approveSceneBreakdown: async (sceneId) => {
        set((state) => {
          state.isLoading = true;
          state.error = null;
        });
        try {
          const result = await api.approveSceneBreakdown(sceneId);
          if (result.shotBreakdownApproved) {
            set((state) => {
              const existing = state.sceneMap[sceneId];
              if (existing) {
                const updated = {
                  ...existing,
                  state: result.state as Scene['state'],
                  shotBreakdownApproved: true,
                };
                state.sceneMap[sceneId] = updated;
                const idx = state.scenes.findIndex((s) => s.id === sceneId);
                if (idx >= 0) {
                  state.scenes[idx] = updated;
                }
                if (state.selectedSceneId === sceneId) {
                  state.selectedScene = updated;
                }
              }
              state.isLoading = false;
            });
          }
          return result.shotBreakdownApproved;
        } catch (error) {
          console.error('Failed to approve scene breakdown:', error);
          set((state) => {
            state.isLoading = false;
            state.error = 'Failed to approve breakdown';
          });
          return false;
        }
      },

      // Async actions - Reference data
      fetchShotTypes: async () => {
        try {
          const types = await api.getShotTypes();
          set((state) => {
            state.shotTypes = types;
          });
          return types;
        } catch (error) {
          console.error('Failed to fetch shot types:', error);
          return [];
        }
      },

      fetchCameraMovements: async () => {
        try {
          const movements = await api.getCameraMovements();
          set((state) => {
            state.cameraMovements = movements;
          });
          return movements;
        } catch (error) {
          console.error('Failed to fetch camera movements:', error);
          return [];
        }
      },

      // Computed helpers
      getSceneById: (id) => {
        return get().sceneMap[id];
      },

      getScenesByState: (targetState) => {
        return get().scenes.filter((s) => s.state === targetState);
      },

      getScenesReadyForGeneration: () => {
        return get().scenes.filter(
          (s) =>
            s.state === 'breakdown_approved' || s.state === 'generating' || s.state === 'generated'
        );
      },

      getScenesNeedingBreakdown: () => {
        return get().scenes.filter((s) => s.state === 'draft' || s.state === 'analyzed');
      },

      getSceneAnalysis: (sceneId) => {
        return get().analysisCache[sceneId];
      },

      getTotalShotCount: () => {
        return get().scenes.reduce((sum, s) => sum + (s.shotCount ?? 0), 0);
      },

      // Reset
      reset: () => set(initialState),
    })),
    { name: 'SceneStore' }
  )
);

/**
 * Hook to get scene workflow progress.
 */
export function useSceneProgress(): {
  total: number;
  draft: number;
  analyzed: number;
  breakdownGenerated: number;
  approved: number;
  generating: number;
  generated: number;
  percentage: number;
} {
  return useSceneStore((state) => {
    const total = state.scenes.length;
    const draft = state.scenes.filter((s) => s.state === 'draft').length;
    const analyzed = state.scenes.filter((s) => s.state === 'analyzed').length;
    const breakdownGenerated = state.scenes.filter((s) => s.state === 'breakdown_generated').length;
    const approved = state.scenes.filter((s) => s.state === 'breakdown_approved').length;
    const generating = state.scenes.filter((s) => s.state === 'generating').length;
    const generated = state.scenes.filter(
      (s) => s.state === 'generated' || s.state === 'approved'
    ).length;

    const percentage = total > 0 ? Math.round((generated / total) * 100) : 0;

    return {
      total,
      draft,
      analyzed,
      breakdownGenerated,
      approved,
      generating,
      generated,
      percentage,
    };
  });
}

/**
 * Hook to check if all scenes are ready for assembly.
 */
export function useAllScenesGenerated(): boolean {
  return useSceneStore((state) => {
    if (state.scenes.length === 0) return false;
    return state.scenes.every((s) => s.state === 'generated' || s.state === 'approved');
  });
}

/**
 * Hook to get scene by index (1-based scene number).
 */
export function useSceneByNumber(sceneNumber: number): Scene | undefined {
  return useSceneStore((state) => state.scenes.find((s) => s.sceneNumber === sceneNumber));
}
