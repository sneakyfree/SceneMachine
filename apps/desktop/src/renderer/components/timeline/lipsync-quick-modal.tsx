/**
 * Lip Sync Quick Modal component.
 * Simplified modal for applying lip sync from timeline context menu.
 */

import { useEffect, useState, useCallback } from 'react';
import { X, Mic, Loader2, AlertCircle } from 'lucide-react';
import { cn } from '../../lib/utils';
import {
  useLipSyncStore,
  selectAvailableProviders,
  selectProcessingJobs,
} from '../../stores/lipsync-store';

interface AudioTrack {
  id: string;
  label: string;
  path: string;
}

interface LipSyncQuickModalProps {
  isOpen: boolean;
  onClose: () => void;
  clipId: string;
  clipLabel: string;
  availableAudioTracks: AudioTrack[];
  onSuccess?: (jobId: string) => void;
}

export function LipSyncQuickModal({
  isOpen,
  onClose,
  clipId,
  clipLabel,
  availableAudioTracks,
  onSuccess,
}: LipSyncQuickModalProps) {
  const [selectedAudio, setSelectedAudio] = useState<string>('');
  const [selectedProvider, setSelectedProvider] = useState<string>('mock');
  const [isStarting, setIsStarting] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  const providers = useLipSyncStore(selectAvailableProviders);
  const processingJobs = useLipSyncStore(selectProcessingJobs);
  const storeError = useLipSyncStore((state) => state.error);

  const startLipSync = useLipSyncStore((state) => state.startLipSync);
  const fetchProviders = useLipSyncStore((state) => state.fetchProviders);
  const clearError = useLipSyncStore((state) => state.clearError);

  // Fetch providers on mount
  useEffect(() => {
    if (isOpen) {
      fetchProviders();
      setLocalError(null);
      clearError();
    }
  }, [isOpen, fetchProviders, clearError]);

  // Auto-select first provider if available
  useEffect(() => {
    if (providers.length > 0 && !selectedProvider) {
      setSelectedProvider(providers[0].provider);
    }
  }, [providers, selectedProvider]);

  // Auto-select first audio track if only one available
  useEffect(() => {
    if (availableAudioTracks.length === 1 && !selectedAudio) {
      setSelectedAudio(availableAudioTracks[0].id);
    }
  }, [availableAudioTracks, selectedAudio]);

  // Close on Escape
  useEffect(() => {
    if (!isOpen) return;

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  const handleApply = useCallback(async () => {
    if (!selectedAudio || !selectedProvider) {
      setLocalError('Please select an audio track and provider');
      return;
    }

    setIsStarting(true);
    setLocalError(null);

    try {
      const job = await startLipSync(clipId, selectedAudio, selectedProvider);
      onSuccess?.(job.job_id);
      onClose();
    } catch (error: any) {
      setLocalError(error?.message || 'Failed to start lip sync');
    } finally {
      setIsStarting(false);
    }
  }, [clipId, selectedAudio, selectedProvider, startLipSync, onSuccess, onClose]);

  const error = localError || storeError;
  const isProcessing = processingJobs.length > 0;
  const canApply = selectedAudio && selectedProvider && !isStarting && !isProcessing;

  if (!isOpen) {
    return null;
  }

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 animate-in fade-in-0 duration-150"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        className={cn(
          'w-[400px] bg-surface-900 border border-surface-700 rounded-xl shadow-2xl',
          'animate-in zoom-in-95 duration-150'
        )}
        role="dialog"
        aria-modal="true"
        aria-labelledby="lipsync-modal-title"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-surface-700">
          <div className="flex items-center gap-2">
            <Mic className="w-5 h-5 text-brand-400" />
            <h2 id="lipsync-modal-title" className="text-lg font-bold">
              Apply Lip Sync
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-surface-800 rounded-lg transition-colors"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-4">
          {/* Clip info */}
          <div className="text-sm text-surface-400">
            Applying lip sync to: <span className="text-surface-200 font-medium">{clipLabel}</span>
          </div>

          {/* Error Display */}
          {error && (
            <div className="flex items-start gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
              <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-red-400">{error}</p>
            </div>
          )}

          {/* Audio Track Selector */}
          <div>
            <label htmlFor="lipsync-audio-select" className="block text-sm font-medium mb-2">
              Audio Track
            </label>
            {availableAudioTracks.length === 0 ? (
              <div className="px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg text-sm text-surface-500">
                No audio tracks available
              </div>
            ) : (
              <select
                id="lipsync-audio-select"
                value={selectedAudio}
                onChange={(e) => setSelectedAudio(e.target.value)}
                className="w-full px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg text-sm focus:outline-none focus:border-brand-500"
                disabled={isStarting}
              >
                <option value="">Select audio track...</option>
                {availableAudioTracks.map((track) => (
                  <option key={track.id} value={track.id}>
                    {track.label}
                  </option>
                ))}
              </select>
            )}
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
              disabled={isStarting}
            >
              {providers.length === 0 ? (
                <option value="">No providers available</option>
              ) : (
                providers.map((provider) => (
                  <option key={provider.provider} value={provider.provider}>
                    {provider.name}
                    {provider.provider === 'rhubarb' && ' (Recommended)'}
                    {provider.provider === 'mock' && ' (Fast)'}
                  </option>
                ))
              )}
            </select>
            <p className="text-xs text-surface-500 mt-1">
              {selectedProvider === 'mock' && 'Mock provider for testing purposes'}
              {selectedProvider === 'rhubarb' && 'Open-source phoneme extraction (fast)'}
              {selectedProvider === 'wav2lip' && 'AI-based lip sync (high quality)'}
              {selectedProvider === 'sadtalker' && 'Talking head generation (premium)'}
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 p-4 border-t border-surface-700">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium hover:bg-surface-800 rounded-lg transition-colors"
            disabled={isStarting}
          >
            Cancel
          </button>
          <button
            onClick={handleApply}
            disabled={!canApply}
            className={cn(
              'px-4 py-2 text-sm font-medium rounded-lg transition-colors',
              canApply
                ? 'bg-brand-500 hover:bg-brand-600 text-white'
                : 'bg-surface-700 text-surface-500 cursor-not-allowed'
            )}
          >
            {isStarting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin inline mr-2" />
                Starting...
              </>
            ) : (
              'Apply'
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
