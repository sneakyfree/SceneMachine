/**
 * Shot state store using Zustand.
 *
 * Manages individual shot data, updates, generation queue, and approval workflow.
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';
import {
  api,
  type Shot,
  type ShotUpdateRequest,
  type ShotAddRequest,
  type GenerationJob,
  type QueuedJobResult,
} from '../api/client';

interface ShotStoreState {
  // Shots map by ID
  shotMap: Record<string, Shot>;

  // Shots grouped by scene
  shotsByScene: Record<string, Shot[]>;

  // Currently selected shot
  selectedShotId: string | null;
  selectedShot: Shot | null;

  // Generation jobs for shots
  shotJobs: Record<string, GenerationJob[]>;

  // Loading states
  isLoading: boolean;
  isUpdating: string | null; // shot ID being updated
  isQueuing: string | null; // shot ID being queued
  error: string | null;

  // Actions - State setters
  setShots: (shots: Shot[]) => void;
  setSelectedShotId: (id: string | null) => void;
  updateShotInState: (shot: Shot) => void;
  removeShotFromState: (shotId: string) => void;
  setError: (error: string | null) => void;

  // Async actions - Get
  fetchShot: (shotId: string) => Promise<Shot | null>;
  fetchShotJobs: (shotId: string) => Promise<GenerationJob[]>;

  // Async actions - Update
  updateShot: (shotId: string, data: ShotUpdateRequest) => Promise<Shot | null>;
  addShot: (data: ShotAddRequest) => Promise<Shot | null>;
  deleteShot: (shotId: string) => Promise<boolean>;

  // Async actions - Generation
  queueShot: (shotId: string, provider?: string, priority?: number) => Promise<QueuedJobResult | null>;
  approveShot: (shotId: string) => Promise<boolean>;
  rejectShot: (shotId: string, notes?: string) => Promise<boolean>;

  // Computed helpers
  getShotById: (id: string) => Shot | undefined;
  getShotsForScene: (sceneId: string) => Shot[];
  getShotsByState: (state: Shot['state']) => Shot[];
  getPendingShots: () => Shot[];
  getApprovedShots: () => Shot[];
  getShotGenerationProgress: (shotId: string) => number;

  // Reset
  reset: () => void;
}

const initialState = {
  shotMap: {},
  shotsByScene: {},
  selectedShotId: null,
  selectedShot: null,
  shotJobs: {},
  isLoading: false,
  isUpdating: null,
  isQueuing: null,
  error: null,
};

export const useShotStore = create<ShotStoreState>()(
  devtools(
    immer((set, get) => ({
      ...initialState,

      // State setters
      setShots: (shots) =>
        set((state) => {
          state.shotMap = {};
          state.shotsByScene = {};
          shots.forEach((shot) => {
            state.shotMap[shot.id] = shot;
            if (!state.shotsByScene[shot.sceneId]) {
              state.shotsByScene[shot.sceneId] = [];
            }
            state.shotsByScene[shot.sceneId].push(shot);
          });
          // Sort shots by number within each scene
          Object.keys(state.shotsByScene).forEach((sceneId) => {
            state.shotsByScene[sceneId].sort((a, b) => a.shotNumber - b.shotNumber);
          });
        }),

      setSelectedShotId: (id) =>
        set((state) => {
          state.selectedShotId = id;
          state.selectedShot = id ? state.shotMap[id] ?? null : null;
        }),

      updateShotInState: (shot) =>
        set((state) => {
          state.shotMap[shot.id] = shot;
          // Update in scene list
          if (state.shotsByScene[shot.sceneId]) {
            const idx = state.shotsByScene[shot.sceneId].findIndex((s) => s.id === shot.id);
            if (idx >= 0) {
              state.shotsByScene[shot.sceneId][idx] = shot;
            } else {
              state.shotsByScene[shot.sceneId].push(shot);
              state.shotsByScene[shot.sceneId].sort((a, b) => a.shotNumber - b.shotNumber);
            }
          } else {
            state.shotsByScene[shot.sceneId] = [shot];
          }
          // Update selected if current
          if (state.selectedShotId === shot.id) {
            state.selectedShot = shot;
          }
        }),

      removeShotFromState: (shotId) =>
        set((state) => {
          const shot = state.shotMap[shotId];
          if (shot) {
            delete state.shotMap[shotId];
            if (state.shotsByScene[shot.sceneId]) {
              state.shotsByScene[shot.sceneId] = state.shotsByScene[shot.sceneId].filter(
                (s) => s.id !== shotId
              );
            }
            if (state.selectedShotId === shotId) {
              state.selectedShotId = null;
              state.selectedShot = null;
            }
          }
        }),

      setError: (error) =>
        set((state) => {
          state.error = error;
        }),

      // Async actions - Get
      fetchShot: async (shotId) => {
        set((state) => {
          state.isLoading = true;
          state.error = null;
        });
        try {
          const shot = await api.getShot(shotId);
          set((state) => {
            state.shotMap[shotId] = shot;
            // Update in scene list
            if (!state.shotsByScene[shot.sceneId]) {
              state.shotsByScene[shot.sceneId] = [];
            }
            const idx = state.shotsByScene[shot.sceneId].findIndex((s) => s.id === shotId);
            if (idx >= 0) {
              state.shotsByScene[shot.sceneId][idx] = shot;
            } else {
              state.shotsByScene[shot.sceneId].push(shot);
              state.shotsByScene[shot.sceneId].sort((a, b) => a.shotNumber - b.shotNumber);
            }
            if (state.selectedShotId === shotId) {
              state.selectedShot = shot;
            }
            state.isLoading = false;
          });
          return shot;
        } catch (error) {
          console.error('Failed to fetch shot:', error);
          set((state) => {
            state.isLoading = false;
            state.error = 'Failed to fetch shot';
          });
          return null;
        }
      },

      fetchShotJobs: async (shotId) => {
        try {
          const jobs = await api.getShotJobs(shotId);
          set((state) => {
            state.shotJobs[shotId] = jobs;
          });
          return jobs;
        } catch (error) {
          console.error('Failed to fetch shot jobs:', error);
          return [];
        }
      },

      // Async actions - Update
      updateShot: async (shotId, data) => {
        set((state) => {
          state.isUpdating = shotId;
          state.error = null;
        });
        try {
          const shot = await api.updateShot(shotId, data);
          set((state) => {
            state.shotMap[shotId] = shot;
            // Update in scene list
            if (state.shotsByScene[shot.sceneId]) {
              const idx = state.shotsByScene[shot.sceneId].findIndex((s) => s.id === shotId);
              if (idx >= 0) {
                state.shotsByScene[shot.sceneId][idx] = shot;
              }
            }
            if (state.selectedShotId === shotId) {
              state.selectedShot = shot;
            }
            state.isUpdating = null;
          });
          return shot;
        } catch (error) {
          console.error('Failed to update shot:', error);
          set((state) => {
            state.isUpdating = null;
            state.error = 'Failed to update shot';
          });
          return null;
        }
      },

      addShot: async (data) => {
        set((state) => {
          state.isLoading = true;
          state.error = null;
        });
        try {
          const shot = await api.addShot(data);
          set((state) => {
            state.shotMap[shot.id] = shot;
            if (!state.shotsByScene[shot.sceneId]) {
              state.shotsByScene[shot.sceneId] = [];
            }
            state.shotsByScene[shot.sceneId].push(shot);
            state.shotsByScene[shot.sceneId].sort((a, b) => a.shotNumber - b.shotNumber);
            state.isLoading = false;
          });
          return shot;
        } catch (error) {
          console.error('Failed to add shot:', error);
          set((state) => {
            state.isLoading = false;
            state.error = 'Failed to add shot';
          });
          return null;
        }
      },

      deleteShot: async (shotId) => {
        set((state) => {
          state.isUpdating = shotId;
          state.error = null;
        });
        try {
          const result = await api.deleteShot(shotId);
          if (result.success) {
            set((state) => {
              const shot = state.shotMap[shotId];
              if (shot) {
                delete state.shotMap[shotId];
                if (state.shotsByScene[shot.sceneId]) {
                  state.shotsByScene[shot.sceneId] = state.shotsByScene[shot.sceneId].filter(
                    (s) => s.id !== shotId
                  );
                }
              }
              if (state.selectedShotId === shotId) {
                state.selectedShotId = null;
                state.selectedShot = null;
              }
              state.isUpdating = null;
            });
          }
          return result.success;
        } catch (error) {
          console.error('Failed to delete shot:', error);
          set((state) => {
            state.isUpdating = null;
            state.error = 'Failed to delete shot';
          });
          return false;
        }
      },

      // Async actions - Generation
      queueShot: async (shotId, provider = 'local', priority = 0) => {
        set((state) => {
          state.isQueuing = shotId;
          state.error = null;
        });
        try {
          const result = await api.queueShot(shotId, provider, priority);
          set((state) => {
            // Update shot state to queued
            const shot = state.shotMap[shotId];
            if (shot) {
              const updated = { ...shot, state: 'queued' as const };
              state.shotMap[shotId] = updated;
              if (state.shotsByScene[shot.sceneId]) {
                const idx = state.shotsByScene[shot.sceneId].findIndex((s) => s.id === shotId);
                if (idx >= 0) {
                  state.shotsByScene[shot.sceneId][idx] = updated;
                }
              }
              if (state.selectedShotId === shotId) {
                state.selectedShot = updated;
              }
            }
            state.isQueuing = null;
          });
          return result;
        } catch (error) {
          console.error('Failed to queue shot:', error);
          set((state) => {
            state.isQueuing = null;
            state.error = 'Failed to queue shot';
          });
          return null;
        }
      },

      approveShot: async (shotId) => {
        set((state) => {
          state.isUpdating = shotId;
          state.error = null;
        });
        try {
          const result = await api.approveGeneratedShot(shotId);
          if (result.success) {
            set((state) => {
              const shot = state.shotMap[shotId];
              if (shot) {
                const updated = { ...shot, state: 'approved' as const };
                state.shotMap[shotId] = updated;
                if (state.shotsByScene[shot.sceneId]) {
                  const idx = state.shotsByScene[shot.sceneId].findIndex((s) => s.id === shotId);
                  if (idx >= 0) {
                    state.shotsByScene[shot.sceneId][idx] = updated;
                  }
                }
                if (state.selectedShotId === shotId) {
                  state.selectedShot = updated;
                }
              }
              state.isUpdating = null;
            });
          }
          return result.success;
        } catch (error) {
          console.error('Failed to approve shot:', error);
          set((state) => {
            state.isUpdating = null;
            state.error = 'Failed to approve shot';
          });
          return false;
        }
      },

      rejectShot: async (shotId, notes) => {
        set((state) => {
          state.isUpdating = shotId;
          state.error = null;
        });
        try {
          const result = await api.rejectGeneratedShot(shotId, notes);
          if (result.success) {
            set((state) => {
              const shot = state.shotMap[shotId];
              if (shot) {
                const updated = { ...shot, state: 'rejected' as const };
                state.shotMap[shotId] = updated;
                if (state.shotsByScene[shot.sceneId]) {
                  const idx = state.shotsByScene[shot.sceneId].findIndex((s) => s.id === shotId);
                  if (idx >= 0) {
                    state.shotsByScene[shot.sceneId][idx] = updated;
                  }
                }
                if (state.selectedShotId === shotId) {
                  state.selectedShot = updated;
                }
              }
              state.isUpdating = null;
            });
          }
          return result.success;
        } catch (error) {
          console.error('Failed to reject shot:', error);
          set((state) => {
            state.isUpdating = null;
            state.error = 'Failed to reject shot';
          });
          return false;
        }
      },

      // Computed helpers
      getShotById: (id) => {
        return get().shotMap[id];
      },

      getShotsForScene: (sceneId) => {
        return get().shotsByScene[sceneId] ?? [];
      },

      getShotsByState: (targetState) => {
        return Object.values(get().shotMap).filter((s) => s.state === targetState);
      },

      getPendingShots: () => {
        return Object.values(get().shotMap).filter(
          (s) => s.state === 'planned' || s.state === 'queued' || s.state === 'generating'
        );
      },

      getApprovedShots: () => {
        return Object.values(get().shotMap).filter((s) => s.state === 'approved');
      },

      getShotGenerationProgress: (shotId) => {
        const jobs = get().shotJobs[shotId];
        if (!jobs || jobs.length === 0) return 0;
        const latestJob = jobs[0];
        return latestJob.progress ?? 0;
      },

      // Reset
      reset: () => set(initialState),
    })),
    { name: 'ShotStore' }
  )
);

/**
 * Hook to get shot generation statistics.
 */
export function useShotStats(): {
  total: number;
  planned: number;
  queued: number;
  generating: number;
  generated: number;
  approved: number;
  rejected: number;
  progressPercentage: number;
} {
  return useShotStore((state) => {
    const shots = Object.values(state.shotMap);
    const total = shots.length;
    const planned = shots.filter((s) => s.state === 'planned').length;
    const queued = shots.filter((s) => s.state === 'queued').length;
    const generating = shots.filter((s) => s.state === 'generating').length;
    const generated = shots.filter((s) => s.state === 'generated').length;
    const approved = shots.filter((s) => s.state === 'approved').length;
    const rejected = shots.filter((s) => s.state === 'rejected').length;

    const progressPercentage = total > 0
      ? Math.round(((generated + approved) / total) * 100)
      : 0;

    return {
      total,
      planned,
      queued,
      generating,
      generated,
      approved,
      rejected,
      progressPercentage,
    };
  });
}

/**
 * Hook to check if all shots for a scene are approved.
 */
export function useSceneShotsApproved(sceneId: string): boolean {
  return useShotStore((state) => {
    const shots = state.shotsByScene[sceneId] ?? [];
    if (shots.length === 0) return false;
    return shots.every((s) => s.state === 'approved');
  });
}

/**
 * Hook to get the next shot to review (first generated but not approved).
 */
export function useNextShotToReview(): Shot | null {
  return useShotStore((state) => {
    const shots = Object.values(state.shotMap);
    return shots.find((s) => s.state === 'generated') ?? null;
  });
}
