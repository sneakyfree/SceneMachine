/**
 * Assembly/Timeline state store using Zustand.
 *
 * Manages video assembly, timeline editing, and export workflow.
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';
import {
  api,
  type AssemblyStatus,
  type Timeline,
  type TimelineClip,
  type TimelineScene,
  type ExportFormat,
  type QualityPreset,
  type ExportRequest,
  type ExportJobResult,
  type ExportHistoryItem,
} from '../api/client';

interface AssemblyStoreState {
  // Assembly status
  assemblyStatus: AssemblyStatus | null;

  // Timeline data
  timeline: Timeline | null;
  selectedClipId: string | null;
  selectedSceneId: string | null;

  // Export configuration
  exportFormats: ExportFormat[];
  qualityPresets: QualityPreset[];
  selectedFormat: string;
  selectedQuality: string;

  // Export state
  isExporting: boolean;
  exportProgress: number;
  currentExportJob: ExportJobResult | null;

  // Export history
  exportHistory: ExportHistoryItem[];

  // Assembly state
  isAssembling: boolean;
  assemblyProgress: number;

  // Loading states
  isLoading: boolean;
  error: string | null;

  // Actions - State setters
  setAssemblyStatus: (status: AssemblyStatus | null) => void;
  setTimeline: (timeline: Timeline | null) => void;
  setSelectedClipId: (id: string | null) => void;
  setSelectedSceneId: (id: string | null) => void;
  setSelectedFormat: (format: string) => void;
  setSelectedQuality: (quality: string) => void;
  setExportProgress: (progress: number) => void;
  setError: (error: string | null) => void;

  // Async actions - Status & Timeline
  fetchAssemblyStatus: (projectId: string) => Promise<AssemblyStatus | null>;
  fetchTimeline: (projectId: string) => Promise<Timeline | null>;

  // Async actions - Assembly
  assembleScene: (sceneId: string) => Promise<boolean>;
  assembleMovie: (projectId: string) => Promise<boolean>;

  // Async actions - Export
  fetchExportFormats: () => Promise<ExportFormat[]>;
  fetchQualityPresets: () => Promise<QualityPreset[]>;
  exportMovie: (request: ExportRequest) => Promise<ExportJobResult | null>;
  fetchExportHistory: (projectId: string) => Promise<ExportHistoryItem[]>;

  // Computed helpers
  isReadyForAssembly: () => boolean;
  isReadyForExport: () => boolean;
  getClipById: (clipId: string) => TimelineClip | undefined;
  getSceneById: (sceneId: string) => TimelineScene | undefined;
  getTotalDuration: () => number;
  getAssemblyPercentage: () => number;

  // Reset
  reset: () => void;
}

const initialState = {
  assemblyStatus: null,
  timeline: null,
  selectedClipId: null,
  selectedSceneId: null,
  exportFormats: [],
  qualityPresets: [],
  selectedFormat: 'mp4',
  selectedQuality: 'high',
  isExporting: false,
  exportProgress: 0,
  currentExportJob: null,
  exportHistory: [],
  isAssembling: false,
  assemblyProgress: 0,
  isLoading: false,
  error: null,
};

export const useAssemblyStore = create<AssemblyStoreState>()(
  devtools(
    immer((set, get) => ({
      ...initialState,

      // State setters
      setAssemblyStatus: (status) =>
        set((state) => {
          state.assemblyStatus = status;
        }),

      setTimeline: (timeline) =>
        set((state) => {
          state.timeline = timeline;
        }),

      setSelectedClipId: (id) =>
        set((state) => {
          state.selectedClipId = id;
        }),

      setSelectedSceneId: (id) =>
        set((state) => {
          state.selectedSceneId = id;
        }),

      setSelectedFormat: (format) =>
        set((state) => {
          state.selectedFormat = format;
        }),

      setSelectedQuality: (quality) =>
        set((state) => {
          state.selectedQuality = quality;
        }),

      setExportProgress: (progress) =>
        set((state) => {
          state.exportProgress = progress;
        }),

      setError: (error) =>
        set((state) => {
          state.error = error;
        }),

      // Async actions - Status & Timeline
      fetchAssemblyStatus: async (projectId) => {
        set((state) => {
          state.isLoading = true;
          state.error = null;
        });
        try {
          const status = await api.getAssemblyStatus(projectId);
          set((state) => {
            state.assemblyStatus = status;
            state.isLoading = false;
          });
          return status;
        } catch (error) {
          console.error('Failed to fetch assembly status:', error);
          set((state) => {
            state.isLoading = false;
            state.error = 'Failed to fetch assembly status';
          });
          return null;
        }
      },

      fetchTimeline: async (projectId) => {
        set((state) => {
          state.isLoading = true;
          state.error = null;
        });
        try {
          const timeline = await api.getTimeline(projectId);
          set((state) => {
            state.timeline = timeline;
            state.isLoading = false;
          });
          return timeline;
        } catch (error) {
          console.error('Failed to fetch timeline:', error);
          set((state) => {
            state.isLoading = false;
            state.error = 'Failed to fetch timeline';
          });
          return null;
        }
      },

      // Async actions - Assembly
      assembleScene: async (sceneId) => {
        set((state) => {
          state.isAssembling = true;
          state.assemblyProgress = 0;
          state.error = null;
        });
        try {
          const result = await api.assembleScene(sceneId);
          set((state) => {
            state.assemblyProgress = 100;
            state.isAssembling = false;
          });
          return result.success;
        } catch (error) {
          console.error('Failed to assemble scene:', error);
          set((state) => {
            state.isAssembling = false;
            state.assemblyProgress = 0;
            state.error = 'Failed to assemble scene';
          });
          return false;
        }
      },

      assembleMovie: async (projectId) => {
        set((state) => {
          state.isAssembling = true;
          state.assemblyProgress = 0;
          state.error = null;
        });
        try {
          // Progress updates would come from WebSocket in production
          set((state) => {
            state.assemblyProgress = 20;
          });
          const result = await api.assembleMovie(projectId);
          set((state) => {
            state.assemblyProgress = 100;
            state.isAssembling = false;
            if (result.outputPath) {
              // Update assembly status
              if (state.assemblyStatus) {
                state.assemblyStatus.state = 'complete';
                state.assemblyStatus.outputPath = result.outputPath;
              }
            }
          });
          return result.success;
        } catch (error) {
          console.error('Failed to assemble movie:', error);
          set((state) => {
            state.isAssembling = false;
            state.assemblyProgress = 0;
            state.error = 'Failed to assemble movie';
          });
          return false;
        }
      },

      // Async actions - Export
      fetchExportFormats: async () => {
        try {
          const formats = await api.getExportFormats();
          set((state) => {
            state.exportFormats = formats;
            if (formats.length > 0 && !state.selectedFormat) {
              state.selectedFormat = formats[0].id;
            }
          });
          return formats;
        } catch (error) {
          console.error('Failed to fetch export formats:', error);
          return [];
        }
      },

      fetchQualityPresets: async () => {
        try {
          const presets = await api.getQualityPresets();
          set((state) => {
            state.qualityPresets = presets;
            if (presets.length > 0 && !state.selectedQuality) {
              state.selectedQuality = presets[0].id;
            }
          });
          return presets;
        } catch (error) {
          console.error('Failed to fetch quality presets:', error);
          return [];
        }
      },

      exportMovie: async (request) => {
        set((state) => {
          state.isExporting = true;
          state.exportProgress = 0;
          state.currentExportJob = null;
          state.error = null;
        });
        try {
          // Start export
          const job = await api.exportMovie(request);
          set((state) => {
            state.currentExportJob = job;
            if (job.status === 'completed') {
              state.exportProgress = 100;
              state.isExporting = false;
            }
          });
          return job;
        } catch (error) {
          console.error('Failed to export movie:', error);
          set((state) => {
            state.isExporting = false;
            state.exportProgress = 0;
            state.error = 'Failed to export movie';
          });
          return null;
        }
      },

      fetchExportHistory: async (projectId) => {
        try {
          const history = await api.getExportHistory(projectId);
          set((state) => {
            state.exportHistory = history;
          });
          return history;
        } catch (error) {
          console.error('Failed to fetch export history:', error);
          return [];
        }
      },

      // Computed helpers
      isReadyForAssembly: () => {
        const state = get();
        return (
          state.assemblyStatus !== null &&
          state.assemblyStatus.approvedShotCount > 0 &&
          !state.isAssembling
        );
      },

      isReadyForExport: () => {
        const state = get();
        return (
          state.assemblyStatus !== null &&
          state.assemblyStatus.state === 'complete' &&
          state.assemblyStatus.outputPath !== null &&
          !state.isExporting
        );
      },

      getClipById: (clipId) => {
        const timeline = get().timeline;
        if (!timeline) return undefined;
        for (const scene of timeline.scenes) {
          const clip = scene.clips.find((c) => c.id === clipId);
          if (clip) return clip;
        }
        return undefined;
      },

      getSceneById: (sceneId) => {
        return get().timeline?.scenes.find((s) => s.id === sceneId);
      },

      getTotalDuration: () => {
        return get().timeline?.totalDurationSeconds ?? 0;
      },

      getAssemblyPercentage: () => {
        const status = get().assemblyStatus;
        if (!status || status.totalShotCount === 0) return 0;
        return Math.round((status.approvedShotCount / status.totalShotCount) * 100);
      },

      // Reset
      reset: () => set(initialState),
    })),
    { name: 'AssemblyStore' }
  )
);

/**
 * Hook to get assembly readiness state.
 */
export function useAssemblyReadiness(): {
  canAssemble: boolean;
  canExport: boolean;
  progress: number;
  message: string;
} {
  return useAssemblyStore((state) => {
    const status = state.assemblyStatus;
    if (!status) {
      return {
        canAssemble: false,
        canExport: false,
        progress: 0,
        message: 'Loading assembly status...',
      };
    }

    const progress =
      status.totalShotCount > 0
        ? Math.round((status.approvedShotCount / status.totalShotCount) * 100)
        : 0;

    if (status.approvedShotCount === 0) {
      return {
        canAssemble: false,
        canExport: false,
        progress: 0,
        message: 'No approved shots to assemble',
      };
    }

    if (status.state === 'complete') {
      return {
        canAssemble: true,
        canExport: true,
        progress: 100,
        message: 'Ready for export',
      };
    }

    if (status.approvedShotCount < status.totalShotCount) {
      return {
        canAssemble: true,
        canExport: false,
        progress,
        message: `${status.approvedShotCount}/${status.totalShotCount} shots approved`,
      };
    }

    return {
      canAssemble: true,
      canExport: false,
      progress,
      message: 'Ready for assembly',
    };
  });
}

/**
 * Hook to get the selected export configuration.
 */
export function useExportConfig(): {
  format: ExportFormat | undefined;
  quality: QualityPreset | undefined;
} {
  return useAssemblyStore((state) => ({
    format: state.exportFormats.find((f) => f.id === state.selectedFormat),
    quality: state.qualityPresets.find((q) => q.id === state.selectedQuality),
  }));
}

/**
 * Hook to check if export is in progress.
 */
export function useIsExporting(): boolean {
  return useAssemblyStore((state) => state.isExporting);
}
