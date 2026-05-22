/**
 * LipsyncButton Component
 * Button to apply lip sync to a shot's video using its audio
 */

import React from 'react';
import { useLipSyncStore, selectActiveJob } from '../../stores/lipsync-store';

interface LipsyncButtonProps {
  videoId: string;
  audioId: string;
  shotId?: string;
  className?: string;
}

export const LipsyncButton: React.FC<LipsyncButtonProps> = ({
  videoId,
  audioId,
  shotId,
  className = '',
}) => {
  const { startLipSync, fetchProviders, providers, isLoadingProviders, error } = useLipSyncStore();
  const activeJob = useLipSyncStore(selectActiveJob);

  const [isProcessing, setIsProcessing] = React.useState(false);
  const [localError, setLocalError] = React.useState<string | null>(null);

  // Fetch providers on mount
  React.useEffect(() => {
    if (providers.length === 0 && !isLoadingProviders) {
      fetchProviders();
    }
  }, [providers.length, isLoadingProviders, fetchProviders]);

  // Check if this shot has an active job
  const shotJob =
    activeJob?.video_id === videoId && activeJob?.audio_id === audioId ? activeJob : null;

  const handleClick = async () => {
    setLocalError(null);
    setIsProcessing(true);

    try {
      // Use first available provider (defaults to 'mock')
      const availableProviders = providers.filter((p) => p.available);
      const provider = availableProviders[0]?.provider || 'mock';

      await startLipSync(videoId, audioId, provider);
    } catch (err: any) {
      setLocalError(err?.message || 'Failed to start lip sync');
    } finally {
      setIsProcessing(false);
    }
  };

  const getButtonState = () => {
    if (shotJob) {
      return {
        disabled: true,
        text: `${shotJob.progress_percent.toFixed(0)}% - ${shotJob.progress_message}`,
        className: 'bg-blue-500 text-white cursor-wait',
      };
    }

    if (isProcessing || isLoadingProviders) {
      return {
        disabled: true,
        text: 'Starting...',
        className: 'bg-gray-400 text-white cursor-wait',
      };
    }

    if (!videoId || !audioId) {
      return {
        disabled: true,
        text: 'Lip Sync',
        className: 'bg-gray-300 text-gray-500 cursor-not-allowed',
      };
    }

    return {
      disabled: false,
      text: 'Lip Sync',
      className: 'bg-purple-600 hover:bg-purple-700 text-white cursor-pointer',
    };
  };

  const buttonState = getButtonState();
  const displayError = localError || error;

  return (
    <div className={`flex flex-col gap-1 ${className}`}>
      <button
        onClick={handleClick}
        disabled={buttonState.disabled}
        className={`px-3 py-2 rounded-md font-medium text-sm transition-colors ${buttonState.className}`}
        aria-label={
          shotJob ? `Lip sync in progress: ${shotJob.progress_message}` : buttonState.text
        }
        title={
          !videoId
            ? 'Video not yet generated'
            : !audioId
              ? 'Audio not yet generated'
              : buttonState.text
        }
      >
        {shotJob && <span className="inline-block mr-2 animate-spin">⚙️</span>}
        {buttonState.text}
      </button>

      {displayError && (
        <div
          className="text-xs text-red-600 px-2 py-1 bg-red-50 rounded border border-red-200"
          role="alert"
        >
          {displayError}
        </div>
      )}

      {shotJob?.status === 'completed' && (
        <div className="text-xs text-green-600 px-2 py-1 bg-green-50 rounded border border-green-200">
          ✓ Lip sync complete
        </div>
      )}

      {shotJob?.status === 'failed' && (
        <div className="text-xs text-red-600 px-2 py-1 bg-red-50 rounded border border-red-200">
          ✗ {shotJob.error_message || 'Lip sync failed'}
        </div>
      )}
    </div>
  );
};
