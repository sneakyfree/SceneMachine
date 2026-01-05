/**
 * Screenplay state store using Zustand.
 *
 * Manages screenplay upload, parsing, and movie plan generation workflow.
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';
import {
  api,
  type ScreenplayUploadResult,
  type ScreenplayParseResult,
  type ScreenplayDetails,
  type ScreenplaySummary,
  type MoviePlan,
} from '../api/client';

interface ScreenplayStoreState {
  // Current screenplay
  currentScreenplay: ScreenplayDetails | null;
  screenplaySummary: ScreenplaySummary | null;

  // Movie plan
  moviePlan: MoviePlan | null;
  moviePlanApproved: boolean;

  // Upload state
  uploadProgress: number;
  isUploading: boolean;

  // Parse state
  isParsing: boolean;
  parseProgress: number;

  // Movie plan generation state
  isGeneratingPlan: boolean;

  // Loading states
  isLoading: boolean;
  error: string | null;

  // Actions - State setters
  setCurrentScreenplay: (screenplay: ScreenplayDetails | null) => void;
  setScreenplaySummary: (summary: ScreenplaySummary | null) => void;
  setMoviePlan: (plan: MoviePlan | null) => void;
  setMoviePlanApproved: (approved: boolean) => void;
  setUploadProgress: (progress: number) => void;
  setParseProgress: (progress: number) => void;
  setError: (error: string | null) => void;

  // Async actions
  fetchScreenplay: (screenplayId: string) => Promise<ScreenplayDetails | null>;
  fetchProjectScreenplay: (projectId: string) => Promise<ScreenplaySummary | null>;
  uploadScreenplay: (
    projectId: string,
    filePath: string,
    filename: string
  ) => Promise<ScreenplayUploadResult | null>;
  parseScreenplay: (screenplayId: string) => Promise<ScreenplayParseResult | null>;
  deleteScreenplay: (screenplayId: string) => Promise<boolean>;

  // Movie plan actions
  fetchMoviePlan: (screenplayId: string) => Promise<MoviePlan | null>;
  generateMoviePlan: (screenplayId: string, regenerate?: boolean) => Promise<MoviePlan | null>;
  approveMoviePlan: (screenplayId: string) => Promise<boolean>;

  // Computed helpers
  isReadyForParsing: () => boolean;
  isReadyForPlanGeneration: () => boolean;
  isReadyForSceneBreakdown: () => boolean;

  // Reset
  reset: () => void;
}

const initialState = {
  currentScreenplay: null,
  screenplaySummary: null,
  moviePlan: null,
  moviePlanApproved: false,
  uploadProgress: 0,
  isUploading: false,
  isParsing: false,
  parseProgress: 0,
  isGeneratingPlan: false,
  isLoading: false,
  error: null,
};

export const useScreenplayStore = create<ScreenplayStoreState>()(
  devtools(
    immer((set, get) => ({
      ...initialState,

      // State setters
      setCurrentScreenplay: (screenplay) =>
        set((state) => {
          state.currentScreenplay = screenplay;
        }),

      setScreenplaySummary: (summary) =>
        set((state) => {
          state.screenplaySummary = summary;
        }),

      setMoviePlan: (plan) =>
        set((state) => {
          state.moviePlan = plan;
        }),

      setMoviePlanApproved: (approved) =>
        set((state) => {
          state.moviePlanApproved = approved;
        }),

      setUploadProgress: (progress) =>
        set((state) => {
          state.uploadProgress = progress;
        }),

      setParseProgress: (progress) =>
        set((state) => {
          state.parseProgress = progress;
        }),

      setError: (error) =>
        set((state) => {
          state.error = error;
        }),

      // Async actions
      fetchScreenplay: async (screenplayId) => {
        set((state) => {
          state.isLoading = true;
          state.error = null;
        });
        try {
          const screenplay = await api.getScreenplay(screenplayId);
          set((state) => {
            state.currentScreenplay = screenplay;
            state.isLoading = false;
          });
          return screenplay;
        } catch (error) {
          console.error('Failed to fetch screenplay:', error);
          set((state) => {
            state.isLoading = false;
            state.error = 'Failed to fetch screenplay';
          });
          return null;
        }
      },

      fetchProjectScreenplay: async (projectId) => {
        set((state) => {
          state.isLoading = true;
          state.error = null;
        });
        try {
          const summary = await api.getProjectScreenplay(projectId);
          set((state) => {
            state.screenplaySummary = summary;
            state.isLoading = false;
          });
          return summary;
        } catch (error) {
          console.error('Failed to fetch project screenplay:', error);
          set((state) => {
            state.isLoading = false;
            state.error = 'Failed to fetch project screenplay';
          });
          return null;
        }
      },

      uploadScreenplay: async (projectId, filePath, filename) => {
        set((state) => {
          state.isUploading = true;
          state.uploadProgress = 0;
          state.error = null;
        });
        try {
          // Simulate progress updates (actual progress would come from backend)
          set((state) => {
            state.uploadProgress = 30;
          });
          const result = await api.uploadScreenplay(projectId, filePath, filename);
          set((state) => {
            state.uploadProgress = 100;
            state.isUploading = false;
            if (result.screenplayId) {
              state.screenplaySummary = {
                id: result.screenplayId,
                filename: result.filename,
                pageCount: result.pageCount ?? 0,
                sceneCount: result.sceneCount ?? 0,
                characterCount: result.characterCount ?? 0,
                uploadedAt: new Date().toISOString(),
                parsedAt: null,
                status: 'uploaded',
              };
            }
          });
          return result;
        } catch (error) {
          console.error('Failed to upload screenplay:', error);
          set((state) => {
            state.isUploading = false;
            state.uploadProgress = 0;
            state.error = 'Failed to upload screenplay';
          });
          return null;
        }
      },

      parseScreenplay: async (screenplayId) => {
        set((state) => {
          state.isParsing = true;
          state.parseProgress = 0;
          state.error = null;
        });
        try {
          // Simulate progress updates
          set((state) => {
            state.parseProgress = 20;
          });
          const result = await api.parseScreenplay(screenplayId);
          set((state) => {
            state.parseProgress = 100;
            state.isParsing = false;
            if (state.screenplaySummary) {
              state.screenplaySummary.status = 'parsed';
              state.screenplaySummary.parsedAt = new Date().toISOString();
              state.screenplaySummary.sceneCount = result.sceneCount;
              state.screenplaySummary.characterCount = result.characterCount;
            }
          });
          return result;
        } catch (error) {
          console.error('Failed to parse screenplay:', error);
          set((state) => {
            state.isParsing = false;
            state.parseProgress = 0;
            state.error = 'Failed to parse screenplay';
          });
          return null;
        }
      },

      deleteScreenplay: async (screenplayId) => {
        set((state) => {
          state.isLoading = true;
          state.error = null;
        });
        try {
          const result = await api.deleteScreenplay(screenplayId);
          if (result.success) {
            set((state) => {
              state.currentScreenplay = null;
              state.screenplaySummary = null;
              state.moviePlan = null;
              state.moviePlanApproved = false;
              state.isLoading = false;
            });
          }
          return result.success;
        } catch (error) {
          console.error('Failed to delete screenplay:', error);
          set((state) => {
            state.isLoading = false;
            state.error = 'Failed to delete screenplay';
          });
          return false;
        }
      },

      // Movie plan actions
      fetchMoviePlan: async (screenplayId) => {
        set((state) => {
          state.isLoading = true;
          state.error = null;
        });
        try {
          const plan = await api.getMoviePlan(screenplayId);
          set((state) => {
            state.moviePlan = plan;
            state.moviePlanApproved = plan?.approved ?? false;
            state.isLoading = false;
          });
          return plan;
        } catch (error) {
          console.error('Failed to fetch movie plan:', error);
          set((state) => {
            state.isLoading = false;
            state.error = 'Failed to fetch movie plan';
          });
          return null;
        }
      },

      generateMoviePlan: async (screenplayId, regenerate = false) => {
        set((state) => {
          state.isGeneratingPlan = true;
          state.error = null;
        });
        try {
          const plan = await api.generateMoviePlan(screenplayId, regenerate);
          set((state) => {
            state.moviePlan = plan;
            state.moviePlanApproved = false;
            state.isGeneratingPlan = false;
          });
          return plan;
        } catch (error) {
          console.error('Failed to generate movie plan:', error);
          set((state) => {
            state.isGeneratingPlan = false;
            state.error = 'Failed to generate movie plan';
          });
          return null;
        }
      },

      approveMoviePlan: async (screenplayId) => {
        set((state) => {
          state.isLoading = true;
          state.error = null;
        });
        try {
          const result = await api.approveMoviePlan(screenplayId);
          if (result.success) {
            set((state) => {
              state.moviePlanApproved = true;
              state.isLoading = false;
            });
          }
          return result.success;
        } catch (error) {
          console.error('Failed to approve movie plan:', error);
          set((state) => {
            state.isLoading = false;
            state.error = 'Failed to approve movie plan';
          });
          return false;
        }
      },

      // Computed helpers
      isReadyForParsing: () => {
        const state = get();
        return (
          state.screenplaySummary !== null &&
          state.screenplaySummary.status === 'uploaded' &&
          !state.isParsing
        );
      },

      isReadyForPlanGeneration: () => {
        const state = get();
        return (
          state.screenplaySummary !== null &&
          state.screenplaySummary.status === 'parsed' &&
          !state.isGeneratingPlan
        );
      },

      isReadyForSceneBreakdown: () => {
        const state = get();
        return state.moviePlanApproved && state.moviePlan !== null;
      },

      // Reset
      reset: () => set(initialState),
    })),
    { name: 'ScreenplayStore' }
  )
);

/**
 * Hook to get screenplay workflow stage.
 */
export function useScreenplayStage(): 'upload' | 'parse' | 'plan' | 'approve' | 'complete' {
  return useScreenplayStore((state) => {
    if (!state.screenplaySummary) return 'upload';
    if (state.screenplaySummary.status === 'uploaded') return 'parse';
    if (!state.moviePlan) return 'plan';
    if (!state.moviePlanApproved) return 'approve';
    return 'complete';
  });
}

/**
 * Hook to check if screenplay is being processed.
 */
export function useScreenplayProcessing(): boolean {
  return useScreenplayStore(
    (state) => state.isUploading || state.isParsing || state.isGeneratingPlan
  );
}
