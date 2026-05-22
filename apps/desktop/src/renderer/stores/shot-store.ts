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
      setShots: (shots: Shot[]) =>
        set((state) => {
          state.shotMap = {};
          state.shotsByScene = {};
          shots.forEach((shot: Shot) => {
            state.shotMap[shot.id] = shot;
            if (!state.shotsByScene[shot.sceneId]) {
              state.shotsByScene[shot.sceneId] = [];
            }
            state.shotsByScene[shot.sceneId].push(shot);
          });
          // Sort shots by number within each scene
          Object.keys(state.shotsByScene).forEach((sceneId: string) => {
            state.shotsByScene[sceneId].sort((a: Shot, b: Shot) => a.sequenceNumber - b.sequenceNumber);
          });
        }),

      setSelectedShotId: (id: string | null) =>
        set((state) => {
          state.selectedShotId = id;
          state.selectedShot = id ? state.shotMap[id] ?? null : null;
        }),

      updateShotInState: (shot: Shot) =>
        set((state) => {
          state.shotMap[shot.id] = shot;
          // Update in scene list
          if (state.shotsByScene[shot.sceneId]) {
            const idx = state.shotsByScene[shot.sceneId].findIndex((s: Shot) => s.id === shot.id);
            if (idx >= 0) {
              state.shotsByScene[shot.sceneId][idx] = shot;
            } else {
              state.shotsByScene[shot.sceneId].push(shot);
              state.shotsByScene[shot.sceneId].sort((a: Shot, b: Shot) => a.sequenceNumber - b.sequenceNumber);
            }
          } else {
            state.shotsByScene[shot.sceneId] = [shot];
          }
          // Update selected if current
          if (state.selectedShotId === shot.id) {
            state.selectedShot = shot;
          }
        }),

      removeShotFromState: (shotId: string) =>
        set((state) => {
          const shot = state.shotMap[shotId];
          if (shot) {
            delete state.shotMap[shotId];
            if (state.shotsByScene[shot.sceneId]) {
              state.shotsByScene[shot.sceneId] = state.shotsByScene[shot.sceneId].filter(
                (s: Shot) => s.id !== shotId
              );
            }
            if (state.selectedShotId === shotId) {
              state.selectedShotId = null;
              state.selectedShot = null;
            }
          }
        }),

      setError: (error: string | null) =>
        set((state) => {
          state.error = error;
        }),

      // Async actions - Get
      fetchShot: async (shotId: string) => {
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
            const idx = state.shotsByScene[shot.sceneId].findIndex((s: Shot) => s.id === shotId);
            if (idx >= 0) {
              state.shotsByScene[shot.sceneId][idx] = shot;
            } else {
              state.shotsByScene[shot.sceneId].push(shot);
              state.shotsByScene[shot.sceneId].sort((a: Shot, b: Shot) => a.sequenceNumber - b.sequenceNumber);
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

      fetchShotJobs: async (shotId: string) => {
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
      updateShot: async (shotId: string, data: ShotUpdateRequest) => {
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
              const idx = state.shotsByScene[shot.sceneId].findIndex((s: Shot) => s.id === shotId);
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

      addShot: async (data: ShotAddRequest) => {
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
            state.shotsByScene[shot.sceneId].sort((a: Shot, b: Shot) => a.sequenceNumber - b.sequenceNumber);
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

      deleteShot: async (shotId: string) => {
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
                    (s: Shot) => s.id !== shotId
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
      queueShot: async (shotId: string, provider = 'local', priority = 0) => {
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
                const idx = state.shotsByScene[shot.sceneId].findIndex((s: Shot) => s.id === shotId);
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

      approveShot: async (shotId: string) => {
        set((state) => {
          state.isUpdating = shotId;
          state.error = null;
        });
        try {
          // The approve IPC response shape is { id, state, approved } —
          // same alignment story as rejectShot above.
          const result = (await api.approveGeneratedShot(shotId)) as {
            id: string;
            state: string;
            approved: boolean;
            success?: boolean;
          };
          const succeeded = result.success ?? result.approved ?? false;
          if (succeeded) {
            set((state) => {
              const shot = state.shotMap[shotId];
              if (shot) {
                const updated = { ...shot, state: 'approved' as const };
                state.shotMap[shotId] = updated;
                if (state.shotsByScene[shot.sceneId]) {
                  const idx = state.shotsByScene[shot.sceneId].findIndex((s: Shot) => s.id === shotId);
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
          return succeeded;
        } catch (error) {
          console.error('Failed to approve shot:', error);
          set((state) => {
            state.isUpdating = null;
            state.error = 'Failed to approve shot';
          });
          return false;
        }
      },

      rejectShot: async (shotId: string, notes?: string) => {
        set((state) => {
          state.isUpdating = shotId;
          state.error = null;
        });
        try {
          // The reject IPC response shape is { id, state, rejected } — no
          // `success` key. We treat the presence of `rejected: true` as the
          // success signal. Stage 2 typing pass should align the type.
          const result = (await api.rejectGeneratedShot(shotId, notes)) as {
            id: string;
            state: string;
            rejected: boolean;
            success?: boolean;
          };
          const succeeded = result.success ?? result.rejected ?? false;
          if (succeeded) {
            set((state) => {
              const shot = state.shotMap[shotId];
              if (shot && shot.sceneId) {
                const sceneId = shot.sceneId;
                const updated = { ...shot, state: 'rejected' as const };
                state.shotMap[shotId] = updated;
                if (state.shotsByScene[sceneId]) {
                  const idx = state.shotsByScene[sceneId].findIndex(
                    (s: Shot) => s.id === shotId,
                  );
                  if (idx >= 0) {
                    state.shotsByScene[sceneId][idx] = updated;
                  }
                }
                if (state.selectedShotId === shotId) {
                  state.selectedShot = updated;
                }
              }
              state.isUpdating = null;
            });
          }
          return succeeded;
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
      getShotById: (id: string) => {
        return get().shotMap[id];
      },

      getShotsForScene: (sceneId: string) => {
        return get().shotsByScene[sceneId] ?? [];
      },

      getShotsByState: (targetState: Shot['state']) => {
        return Object.values(get().shotMap).filter((s: Shot) => s.state === targetState);
      },

      getPendingShots: () => {
        return Object.values(get().shotMap).filter(
          (s: Shot) => s.state === 'planned' || s.state === 'queued' || s.state === 'generating'
        );
      },

      getApprovedShots: () => {
        return Object.values(get().shotMap).filter((s: Shot) => s.state === 'approved');
      },

      getShotGenerationProgress: (shotId: string) => {
        const jobs = get().shotJobs[shotId];
        if (!jobs || jobs.length === 0) return 0;
        // The backend GenerationJob shape uses `progress` informally; the
        // generated TS type is missing the field. Cast through unknown for
        // now; Stage 2 typing pass should add `progress?: number` to the
        // GenerationJob interface.
        const latestJob = jobs[0] as unknown as { progress?: number };
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
    const shots = Object.values(state.shotMap) as Shot[];
    const total = shots.length;
    const planned = shots.filter((s: Shot) => s.state === 'planned').length;
    const queued = shots.filter((s: Shot) => s.state === 'queued').length;
    const generating = shots.filter((s: Shot) => s.state === 'generating').length;
    const generated = shots.filter((s: Shot) => s.state === 'generated').length;
    const approved = shots.filter((s: Shot) => s.state === 'approved').length;
    const rejected = shots.filter((s: Shot) => s.state === 'rejected').length;

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
    return shots.every((s: Shot) => s.state === 'approved');
  });
}

/**
 * Hook to get the next shot to review (first generated but not approved).
 */
export function useNextShotToReview(): Shot | null {
  return useShotStore((state) => {
    const shots = Object.values(state.shotMap) as Shot[];
    return shots.find((s: Shot) => s.state === 'generated') ?? null;
  });
}
