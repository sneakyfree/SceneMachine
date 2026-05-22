/**
 * Lip Sync Store
 * Manages lip sync processing jobs and state.
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';

interface LipSyncJob {
  job_id: string;
  video_id: string;
  audio_id: string;
  provider: string;
  status: 'queued' | 'processing' | 'completed' | 'failed' | 'cancelled';
  progress_percent: number;
  progress_message: string;
  output_path: string | null;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}

interface Provider {
  provider: string;
  name: string;
  available: boolean;
}

interface LipSyncStore {
  // State
  jobs: LipSyncJob[];
  activeJobId: string | null;
  providers: Provider[];
  isLoadingProviders: boolean;
  error: string | null;

  // Actions
  startLipSync: (videoId: string, audioId: string, provider: string) => Promise<LipSyncJob>;
  cancelLipSync: (jobId: string) => Promise<void>;
  fetchJobs: () => Promise<void>;
  fetchProviders: () => Promise<void>;
  setActiveJob: (jobId: string | null) => void;
  updateJobProgress: (jobId: string, update: Partial<LipSyncJob>) => void;
  clearError: () => void;
  reset: () => void;
}

const initialState = {
  jobs: [],
  activeJobId: null,
  providers: [],
  isLoadingProviders: false,
  error: null,
};

export const useLipSyncStore = create<LipSyncStore>()(
  devtools(
    persist(
      immer((set, get) => ({
        ...initialState,

        startLipSync: async (videoId, audioId, provider) => {
          set((state) => {
            state.error = null;
          });

          try {
            const response = await window.electronAPI.backendRequest('lipsync.start', {
              video_id: videoId,
              audio_id: audioId,
              provider,
            });

            const job = response as LipSyncJob;

            set((state) => {
              state.jobs.unshift(job);
              state.activeJobId = job.job_id;
            });

            // Start WebSocket connection for progress updates
            startJobWebSocket(job.job_id, (update) => {
              get().updateJobProgress(job.job_id, update);
            });

            return job;
          } catch (error: any) {
            const errorMessage = error?.message || 'Failed to start lip sync';
            set((state) => {
              state.error = errorMessage;
            });
            throw error;
          }
        },

        cancelLipSync: async (jobId) => {
          set((state) => {
            state.error = null;
          });

          try {
            await window.electronAPI.backendRequest('lipsync.cancel', { job_id: jobId });

            set((state) => {
              const job = state.jobs.find((j) => j.job_id === jobId);
              if (job) {
                job.status = 'cancelled';
                job.error_message = 'Job cancelled by user';
              }
            });
          } catch (error: any) {
            const errorMessage = error?.message || 'Failed to cancel lip sync';
            set((state) => {
              state.error = errorMessage;
            });
            throw error;
          }
        },

        fetchJobs: async () => {
          try {
            const response = await window.electronAPI.backendRequest('lipsync.listJobs', {});
            const jobs = response as LipSyncJob[];

            set((state) => {
              state.jobs = jobs;
            });
          } catch (error: any) {
            console.error('Failed to fetch lip sync jobs:', error);
            set((state) => {
              state.error = error?.message || 'Failed to fetch jobs';
            });
          }
        },

        fetchProviders: async () => {
          set((state) => {
            state.isLoadingProviders = true;
            state.error = null;
          });

          try {
            // Backend registers this handler as `lipSync.getProviders`
            // (camelCase). Aligning the renderer with that name closes the
            // ghost-IPC bug class — see docs/INVENTORY_DEFECTS.md P0-2.
            const response = await window.electronAPI.backendRequest('lipSync.getProviders', {});

            // Handle response safely
            const providersData = response as { providers?: Provider[] } | undefined;
            const providers = providersData?.providers || [];

            set((state) => {
              state.providers = providers;
              state.isLoadingProviders = false;
            });
          } catch (error: any) {
            console.error('Failed to fetch lip sync providers:', error);
            set((state) => {
              state.error = error?.message || 'Failed to fetch providers';
              state.isLoadingProviders = false;
            });
          }
        },

        setActiveJob: (jobId) => {
          set((state) => {
            state.activeJobId = jobId;
          });
        },

        updateJobProgress: (jobId, update) => {
          set((state) => {
            const job = state.jobs.find((j) => j.job_id === jobId);
            if (job) {
              Object.assign(job, update);
            }
          });
        },

        clearError: () => {
          set((state) => {
            state.error = null;
          });
        },

        reset: () => {
          set(initialState);
        },
      })),
      {
        name: 'lipsync-store',
        partialize: (state) => ({
          // Only persist jobs, not loading states or errors
          jobs: state.jobs,
        }),
      }
    ),
    {
      name: 'LipSyncStore',
    }
  )
);

// WebSocket connection for job progress updates
function startJobWebSocket(jobId: string, onUpdate: (update: Partial<LipSyncJob>) => void): void {
  // TODO: Implement WebSocket connection to /api/lipsync/ws/{job_id}
  // For now, we'll poll the job status
  const pollInterval = setInterval(async () => {
    try {
      const response = await window.electronAPI.backendRequest('lipsync.getJob', {
        job_id: jobId,
      });
      const job = response as LipSyncJob;

      onUpdate(job);

      // Stop polling if job is finished
      if (['completed', 'failed', 'cancelled'].includes(job.status)) {
        clearInterval(pollInterval);
      }
    } catch (error) {
      console.error('Failed to poll lip sync job:', error);
      clearInterval(pollInterval);
    }
  }, 1000); // Poll every second
}

// Selectors
export const selectLipSyncJobs = (state: LipSyncStore) => state.jobs;
export const selectActiveJob = (state: LipSyncStore) =>
  state.jobs.find((j) => j.job_id === state.activeJobId);
export const selectProcessingJobs = (state: LipSyncStore) =>
  state.jobs.filter((j) => j.status === 'processing' || j.status === 'queued');
export const selectCompletedJobs = (state: LipSyncStore) =>
  state.jobs.filter((j) => j.status === 'completed');
export const selectFailedJobs = (state: LipSyncStore) =>
  state.jobs.filter((j) => j.status === 'failed');
export const selectAvailableProviders = (state: LipSyncStore) =>
  state.providers.filter((p) => p.available);
