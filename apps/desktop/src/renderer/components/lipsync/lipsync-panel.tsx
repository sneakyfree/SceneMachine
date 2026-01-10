/**
 * Lip Sync Panel component.
 * Provides UI for triggering and monitoring lip sync processing.
 */

import { useEffect, useState, useCallback } from 'react';
import {
  X,
  Play,
  Loader2,
  AlertCircle,
  CheckCircle,
  Info,
  Trash2,
  Download,
} from 'lucide-react';
import { cn } from '../../lib/utils';
import {
  useLipSyncStore,
  selectLipSyncJobs,
  selectAvailableProviders,
  selectProcessingJobs,
} from '../../stores/lipsync-store';

interface LipSyncPanelProps {
  isOpen: boolean;
  onClose: () => void;
  availableVideos?: Array<{ id: string; label: string; path: string }>;
  availableAudio?: Array<{ id: string; label: string; path: string }>;
}

export function LipSyncPanel({
  isOpen,
  onClose,
  availableVideos = [],
  availableAudio = [],
}: LipSyncPanelProps) {
  const [selectedVideo, setSelectedVideo] = useState<string>('');
  const [selectedAudio, setSelectedAudio] = useState<string>('');
  const [selectedProvider, setSelectedProvider] = useState<string>('mock');

  const jobs = useLipSyncStore(selectLipSyncJobs);
  const providers = useLipSyncStore(selectAvailableProviders);
  const processingJobs = useLipSyncStore(selectProcessingJobs);
  const error = useLipSyncStore((state) => state.error);

  const startLipSync = useLipSyncStore((state) => state.startLipSync);
  const cancelLipSync = useLipSyncStore((state) => state.cancelLipSync);
  const fetchProviders = useLipSyncStore((state) => state.fetchProviders);
  const clearError = useLipSyncStore((state) => state.clearError);

  // Fetch providers on mount
  useEffect(() => {
    if (isOpen) {
      fetchProviders();
    }
  }, [isOpen, fetchProviders]);

  // Auto-select first available provider
  useEffect(() => {
    if (providers.length > 0 && !selectedProvider) {
      setSelectedProvider(providers[0].provider);
    }
  }, [providers, selectedProvider]);

  const handleStartLipSync = useCallback(async () => {
    if (!selectedVideo || !selectedAudio) {
      return;
    }

    try {
      await startLipSync(selectedVideo, selectedAudio, selectedProvider);

      // Reset selection after successful start
      setSelectedVideo('');
      setSelectedAudio('');
    } catch (error) {
      console.error('Failed to start lip sync:', error);
    }
  }, [selectedVideo, selectedAudio, selectedProvider, startLipSync]);

  const handleCancelJob = useCallback(
    async (jobId: string) => {
      try {
        await cancelLipSync(jobId);
      } catch (error) {
        console.error('Failed to cancel job:', error);
      }
    },
    [cancelLipSync]
  );

  const handleDownload = useCallback(async (outputPath: string, jobId: string) => {
    try {
      await window.electronAPI.backendRequest('files.downloadFile', {
        path: outputPath,
        filename: `lipsync-${jobId}.mp4`,
      });
    } catch (error) {
      console.error('Failed to download video:', error);
    }
  }, []);

  const canApplyLipSync =
    selectedVideo && selectedAudio && selectedProvider && processingJobs.length === 0;

  if (!isOpen) {
    return null;
  }

  return (
    <div
      className={cn(
        'fixed right-0 top-0 h-full w-[400px] bg-surface-900 border-l border-surface-700 shadow-2xl z-50',
        'transform transition-transform duration-300 ease-in-out',
        isOpen ? 'translate-x-0' : 'translate-x-full'
      )}
      role="dialog"
      aria-label="Lip sync panel"
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-surface-700">
        <div className="flex items-center gap-2">
          <Play className="w-5 h-5 text-brand-400" />
          <h2 className="text-lg font-bold">Lip Sync</h2>
          <button
            onClick={() => {
              // Show info tooltip
            }}
            className="p-1 hover:bg-surface-800 rounded transition-colors"
            title="Automatically sync character lip movements to audio dialogue"
          >
            <Info className="w-4 h-4 text-surface-400" />
          </button>
        </div>

        <button
          onClick={onClose}
          className="p-2 hover:bg-surface-800 rounded-lg transition-colors"
          title="Close panel"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Content */}
      <div className="flex flex-col h-[calc(100%-65px)] overflow-hidden">
        {/* Input Form */}
        <div className="p-4 border-b border-surface-700 space-y-4">
          {/* Error Display */}
          {error && (
            <div className="flex items-start gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
              <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="text-sm text-red-400">{error}</p>
                <button
                  onClick={clearError}
                  className="text-xs text-red-300 hover:text-red-200 mt-1"
                >
                  Dismiss
                </button>
              </div>
            </div>
          )}

          {/* Video Selector */}
          <div>
            <label htmlFor="lipsync-video-select" className="block text-sm font-medium mb-2">
              Video Clip
            </label>
            <select
              id="lipsync-video-select"
              value={selectedVideo}
              onChange={(e) => setSelectedVideo(e.target.value)}
              className="w-full px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg text-sm focus:outline-none focus:border-brand-500"
              disabled={processingJobs.length > 0}
            >
              <option value="">Select a video...</option>
              {availableVideos.map((video) => (
                <option key={video.id} value={video.id}>
                  {video.label}
                </option>
              ))}
            </select>
          </div>

          {/* Audio Selector */}
          <div>
            <label htmlFor="lipsync-audio-select" className="block text-sm font-medium mb-2">
              Audio Track
            </label>
            <select
              id="lipsync-audio-select"
              value={selectedAudio}
              onChange={(e) => setSelectedAudio(e.target.value)}
              className="w-full px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg text-sm focus:outline-none focus:border-brand-500"
              disabled={processingJobs.length > 0}
            >
              <option value="">Select audio...</option>
              {availableAudio.map((audio) => (
                <option key={audio.id} value={audio.id}>
                  {audio.label}
                </option>
              ))}
            </select>
          </div>

          {/* Provider Selector */}
          <div>
            <label htmlFor="lipsync-provider-select" className="block text-sm font-medium mb-2">
              Provider
            </label>
            <select
              id="lipsync-provider-select"
              value={selectedProvider}
              onChange={(e) => setSelectedProvider(e.target.value)}
              className="w-full px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg text-sm focus:outline-none focus:border-brand-500"
              disabled={processingJobs.length > 0}
            >
              {providers.length === 0 ? (
                <option value="">No providers available</option>
              ) : (
                providers.map((provider) => (
                  <option key={provider.provider} value={provider.provider}>
                    {provider.name}
                    {provider.provider === 'mock' && ' (Fast)'}
                    {provider.provider === 'rhubarb' && ' (Recommended)'}
                  </option>
                ))
              )}
            </select>
            <p className="text-xs text-surface-400 mt-1">
              {selectedProvider === 'mock' && 'Mock provider for testing purposes'}
              {selectedProvider === 'rhubarb' && 'Open-source phoneme extraction (fast)'}
              {selectedProvider === 'wav2lip' && 'AI-based lip sync (high quality)'}
              {selectedProvider === 'sadtalker' && 'Talking head generation (premium)'}
            </p>
          </div>

          {/* Apply Button */}
          <button
            onClick={handleStartLipSync}
            disabled={!canApplyLipSync}
            className={cn(
              'w-full px-4 py-3 rounded-lg font-medium transition-colors',
              canApplyLipSync
                ? 'bg-brand-500 hover:bg-brand-600 text-white'
                : 'bg-surface-700 text-surface-500 cursor-not-allowed'
            )}
          >
            {processingJobs.length > 0 ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin inline mr-2" />
                Processing...
              </>
            ) : (
              'Apply Lip Sync'
            )}
          </button>
        </div>

        {/* Results List */}
        <div className="flex-1 overflow-y-auto p-4">
          <h3 className="text-sm font-medium mb-3 text-surface-400">Recent Jobs</h3>

          {jobs.length === 0 ? (
            <div className="text-center py-12">
              <Play className="w-12 h-12 text-surface-600 mx-auto mb-3" />
              <p className="text-sm text-surface-500">No lip sync jobs yet</p>
              <p className="text-xs text-surface-600 mt-1">
                Select a video and audio to get started
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {jobs.map((job) => (
                <div
                  key={job.job_id}
                  className="bg-surface-800 rounded-lg p-3 border border-surface-700"
                >
                  {/* Job Header */}
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1">
                      <p className="text-sm font-medium line-clamp-1">
                        Job {job.job_id.split('-')[1]}
                      </p>
                      <p className="text-xs text-surface-400 mt-0.5">
                        {new Date(job.created_at).toLocaleString()}
                      </p>
                    </div>

                    {/* Status Badge */}
                    <div
                      className={cn(
                        'px-2 py-0.5 rounded-full text-xs font-medium',
                        job.status === 'completed' && 'bg-green-500/20 text-green-400',
                        job.status === 'processing' && 'bg-brand-500/20 text-brand-400',
                        job.status === 'queued' && 'bg-surface-700 text-surface-400',
                        job.status === 'failed' && 'bg-red-500/20 text-red-400',
                        job.status === 'cancelled' && 'bg-orange-500/20 text-orange-400'
                      )}
                    >
                      {job.status === 'completed' && (
                        <CheckCircle className="w-3 h-3 inline mr-1" />
                      )}
                      {job.status === 'processing' && (
                        <Loader2 className="w-3 h-3 inline mr-1 animate-spin" />
                      )}
                      {job.status === 'failed' && <AlertCircle className="w-3 h-3 inline mr-1" />}
                      {job.status.charAt(0).toUpperCase() + job.status.slice(1)}
                    </div>
                  </div>

                  {/* Progress Bar (for processing jobs) */}
                  {(job.status === 'processing' || job.status === 'queued') && (
                    <div className="mb-2">
                      <div className="flex items-center justify-between text-xs text-surface-400 mb-1">
                        <span>{job.progress_message}</span>
                        <span>{Math.round(job.progress_percent)}%</span>
                      </div>
                      <div className="h-1.5 bg-surface-700 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-brand-500 transition-all duration-300"
                          style={{ width: `${job.progress_percent}%` }}
                        />
                      </div>
                    </div>
                  )}

                  {/* Error Message */}
                  {job.error_message && (
                    <div className="flex items-start gap-2 p-2 bg-red-500/10 border border-red-500/20 rounded mb-2">
                      <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
                      <p className="text-xs text-red-400">{job.error_message}</p>
                    </div>
                  )}

                  {/* Actions */}
                  <div className="flex gap-2">
                    {job.status === 'completed' && job.output_path && (
                      <>
                        <button
                          onClick={() => handleDownload(job.output_path!, job.job_id)}
                          className="flex-1 btn-secondary text-xs"
                          title="Download result"
                        >
                          <Download className="w-3 h-3 mr-1" />
                          Download
                        </button>
                        <button
                          onClick={() => {
                            /* TODO: Delete job */
                          }}
                          className="btn-secondary text-xs px-2"
                          title="Delete"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </>
                    )}

                    {(job.status === 'processing' || job.status === 'queued') && (
                      <button
                        onClick={() => handleCancelJob(job.job_id)}
                        className="flex-1 btn-secondary text-xs"
                      >
                        Cancel
                      </button>
                    )}

                    {job.status === 'failed' && (
                      <button
                        onClick={() => {
                          /* TODO: Retry job */
                        }}
                        className="flex-1 btn-primary text-xs"
                      >
                        Retry
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
