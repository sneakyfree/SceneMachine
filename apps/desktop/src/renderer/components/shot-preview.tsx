/**
 * Shot preview component for displaying generated shot output.
 */

import { useState, memo, useCallback } from 'react';
import {
  Play,
  Pause,
  RotateCcw,
  Check,
  X,
  Loader2,
  AlertCircle,
  Clock,
  Maximize2,
  Download,
  ThumbsUp,
  ThumbsDown,
  Minimize,
} from 'lucide-react';
import { cn } from '../lib/utils';
import { VideoPlayer } from './video-player';

interface Shot {
  id: string;
  shotNumber: string;
  description: string;
  state: string;
  outputVideoPath?: string;
  outputThumbnailPath?: string;
  durationSeconds: number;
}

interface Job {
  id: string;
  jobNumber: number;
  status: string;
  progressPercent?: number;
  progressMessage?: string;
  errorMessage?: string;
  outputPath?: string;
}

interface ShotPreviewProps {
  shot: Shot;
  latestJob?: Job;
  onApprove: (shotId: string) => void;
  onReject: (shotId: string, notes?: string) => void;
  onRegenerate: (shotId: string) => void;
  disabled?: boolean;
}

export const ShotPreview = memo(function ShotPreview({
  shot,
  latestJob,
  onApprove,
  onReject,
  onRegenerate,
  disabled = false,
}: ShotPreviewProps) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [rejectNotes, setRejectNotes] = useState('');

  const isGenerating = latestJob?.status === 'running' || latestJob?.status === 'preparing';
  const isFailed = shot.state === 'failed' || latestJob?.status === 'failed';
  const isGenerated = shot.state === 'generated' || shot.state === 'review';
  const isApproved = shot.state === 'approved';

  const handleReject = useCallback(() => {
    onReject(shot.id, rejectNotes);
    setShowRejectModal(false);
    setRejectNotes('');
  }, [onReject, shot.id, rejectNotes]);

  return (
    <div className="bg-surface-800 rounded-lg overflow-hidden">
      {/* Preview Area */}
      <div className="relative aspect-video bg-surface-900">
        {isGenerating ? (
          /* Generation in progress */
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <Loader2 className="w-12 h-12 text-brand-400 animate-spin mb-4" />
            <div className="text-center px-4">
              <p className="font-medium mb-1">
                {latestJob?.progressMessage || 'Generating...'}
              </p>
              {latestJob?.progressPercent !== undefined && (
                <div className="w-48 h-2 bg-surface-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-brand-500 transition-all"
                    style={{ width: `${latestJob.progressPercent}%` }}
                  />
                </div>
              )}
            </div>
          </div>
        ) : isFailed ? (
          /* Failed state */
          <div className="absolute inset-0 flex flex-col items-center justify-center text-red-400">
            <AlertCircle className="w-12 h-12 mb-4" />
            <p className="font-medium mb-2">Generation Failed</p>
            <p className="text-sm text-surface-400 text-center px-4 max-w-xs">
              {latestJob?.errorMessage || 'An error occurred during generation'}
            </p>
            <button
              onClick={() => onRegenerate(shot.id)}
              disabled={disabled}
              className="mt-4 btn-secondary text-sm"
            >
              <RotateCcw className="w-4 h-4 mr-1" />
              Retry
            </button>
          </div>
        ) : isGenerated || isApproved ? (
          /* Video preview */
          <>
            {isPlaying && shot.outputVideoPath ? (
              /* Video Player - Inline */
              <>
                <VideoPlayer
                  src={shot.outputVideoPath}
                  poster={shot.outputThumbnailPath}
                  className="w-full h-full"
                  onError={(error) => {
                    console.error('Video playback error:', error);
                    setIsPlaying(false);
                  }}
                />
                {/* Collapse button */}
                <button
                  onClick={() => setIsPlaying(false)}
                  className="absolute top-3 left-3 p-2 bg-black/50 hover:bg-black/70 text-white rounded-lg transition-colors z-10"
                  title="Close player"
                >
                  <Minimize className="w-4 h-4" />
                </button>
              </>
            ) : (
              <>
                {/* Thumbnail Preview */}
                {shot.outputThumbnailPath ? (
                  <img
                    src={`file://${shot.outputThumbnailPath}`}
                    alt={shot.description}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full bg-gradient-to-br from-surface-800 to-surface-900 flex items-center justify-center">
                    <Play className="w-16 h-16 text-surface-600" />
                  </div>
                )}

                {/* Play overlay */}
                {shot.outputVideoPath && (
                  <button
                    onClick={() => setIsPlaying(true)}
                    className="absolute inset-0 flex items-center justify-center bg-black/30 opacity-0 hover:opacity-100 transition-opacity group"
                  >
                    <div className="w-16 h-16 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center transition-transform group-hover:scale-110">
                      <Play className="w-8 h-8 text-white ml-1" />
                    </div>
                    <span className="absolute bottom-4 text-white text-sm font-medium">
                      Click to preview
                    </span>
                  </button>
                )}
              </>
            )}

            {/* Approval badge */}
            {isApproved && !isPlaying && (
              <div className="absolute top-3 right-3 flex items-center gap-1 px-2 py-1 bg-green-500/90 text-white text-xs font-medium rounded-full">
                <Check className="w-3 h-3" />
                Approved
              </div>
            )}
          </>
        ) : (
          /* Not generated yet */
          <div className="absolute inset-0 flex flex-col items-center justify-center text-surface-500">
            <Clock className="w-12 h-12 mb-4" />
            <p className="font-medium">Not Generated</p>
            <p className="text-sm text-surface-500 mt-1">
              Waiting in queue
            </p>
          </div>
        )}
      </div>

      {/* Info Bar */}
      <div className="p-4">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="font-mono text-sm bg-surface-700 px-2 py-0.5 rounded">
              {shot.shotNumber}
            </span>
            <span className="text-sm text-surface-400">
              {shot.durationSeconds.toFixed(1)}s
            </span>
          </div>

          {/* Status Badge */}
          <div
            className={cn(
              'text-xs px-2 py-0.5 rounded-full',
              shot.state === 'approved' && 'bg-green-500/20 text-green-400',
              shot.state === 'generated' && 'bg-brand-500/20 text-brand-400',
              shot.state === 'generating' && 'bg-yellow-500/20 text-yellow-400',
              shot.state === 'queued' && 'bg-surface-700 text-surface-400',
              shot.state === 'failed' && 'bg-red-500/20 text-red-400',
              shot.state === 'rejected' && 'bg-orange-500/20 text-orange-400',
              shot.state === 'planned' && 'bg-surface-700 text-surface-500'
            )}
          >
            {shot.state.charAt(0).toUpperCase() + shot.state.slice(1)}
          </div>
        </div>

        <p className="text-sm text-surface-400 line-clamp-2">{shot.description}</p>

        {/* Quick Actions when video is playing */}
        {isPlaying && shot.outputVideoPath && (
          <div className="flex gap-2 mt-4 pt-4 border-t border-surface-700">
            <button
              onClick={() => {
                onApprove(shot.id);
                setIsPlaying(false);
              }}
              disabled={disabled || isApproved}
              className="flex-1 btn-primary text-sm"
              title="Approve this take"
            >
              <Check className="w-4 h-4 mr-1" />
              Use This Take
            </button>
            <button
              onClick={() => {
                onRegenerate(shot.id);
                setIsPlaying(false);
              }}
              disabled={disabled}
              className="flex-1 btn-secondary text-sm"
              title="Generate another take"
            >
              <RotateCcw className="w-4 h-4 mr-1" />
              Regenerate
            </button>
            <button
              onClick={async () => {
                if (shot.outputVideoPath) {
                  try {
                    await window.electronAPI.backendRequest('files.downloadFile', {
                      path: shot.outputVideoPath,
                      filename: `shot-${shot.shotNumber}.mp4`,
                    });
                  } catch (error) {
                    console.error('Download failed:', error);
                  }
                }
              }}
              disabled={disabled}
              className="btn-secondary text-sm"
              title="Download video file"
            >
              <Download className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Action Buttons when not playing */}
        {!isPlaying && isGenerated && !isApproved && (
          <div className="flex gap-2 mt-4">
            <button
              onClick={() => onApprove(shot.id)}
              disabled={disabled}
              className="flex-1 btn-primary text-sm"
            >
              <ThumbsUp className="w-4 h-4 mr-1" />
              Approve
            </button>
            <button
              onClick={() => setShowRejectModal(true)}
              disabled={disabled}
              className="flex-1 btn-secondary text-sm"
            >
              <ThumbsDown className="w-4 h-4 mr-1" />
              Reject
            </button>
            <button
              onClick={() => onRegenerate(shot.id)}
              disabled={disabled}
              className="btn-secondary text-sm"
              title="Regenerate"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          </div>
        )}

        {!isPlaying && (isFailed || shot.state === 'rejected') && (
          <button
            onClick={() => onRegenerate(shot.id)}
            disabled={disabled}
            className="w-full btn-primary text-sm mt-4"
          >
            <RotateCcw className="w-4 h-4 mr-1" />
            Regenerate
          </button>
        )}
      </div>

      {/* Reject Modal */}
      {showRejectModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-surface-800 rounded-lg p-6 w-full max-w-md">
            <h3 className="text-lg font-medium mb-4">Reject Shot</h3>
            <p className="text-sm text-surface-400 mb-4">
              Provide feedback for regeneration (optional):
            </p>
            <textarea
              value={rejectNotes}
              onChange={(e) => setRejectNotes(e.target.value)}
              placeholder="e.g., Character looks different, lighting is too dark..."
              rows={3}
              className="w-full px-3 py-2 bg-surface-900 border border-surface-700 rounded-lg text-sm focus:outline-none focus:border-brand-500 resize-none mb-4"
            />
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setShowRejectModal(false)}
                className="btn-secondary"
              >
                Cancel
              </button>
              <button
                onClick={handleReject}
                className="btn-primary bg-red-500 hover:bg-red-600"
              >
                Reject Shot
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
});
