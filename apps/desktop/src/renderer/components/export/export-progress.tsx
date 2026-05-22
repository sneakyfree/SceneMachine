/**
 * Export Progress Component
 *
 * Displays real-time FFmpeg export progress via WebSocket events.
 * Shows frame count, FPS, ETA, and file size.
 */

import { memo, useState, useEffect, useCallback } from 'react';
import { X, Loader2, CheckCircle, AlertCircle, Clock, HardDrive, Film, Gauge } from 'lucide-react';
import { cn } from '../../lib/utils';
import { useWebSocketEvent, EventType, WebSocketEvent } from '../../lib/websocket';

export interface ExportProgressData {
  /**
   * Export job ID
   */
  jobId: string;

  /**
   * Current status
   */
  status:
    | 'pending'
    | 'processing'
    | 'encoding'
    | 'finalizing'
    | 'completed'
    | 'failed'
    | 'cancelled';

  /**
   * Progress percentage (0-100)
   */
  percentage: number;

  /**
   * Current frame being processed
   */
  frame: number;

  /**
   * Total frames to process
   */
  totalFrames: number;

  /**
   * Current encoding FPS
   */
  fps: number;

  /**
   * Estimated time remaining in seconds
   */
  etaSeconds: number;

  /**
   * Current output file size in bytes
   */
  currentSize: number;

  /**
   * Estimated final file size in bytes
   */
  estimatedSize: number;

  /**
   * Current encoding bitrate in kbps
   */
  bitrate: number;

  /**
   * Current encoding speed (e.g., "1.5x")
   */
  speed: string;

  /**
   * Time elapsed in seconds
   */
  elapsedSeconds: number;

  /**
   * Error message if failed
   */
  errorMessage?: string;

  /**
   * Output file path on completion
   */
  outputPath?: string;
}

interface ExportProgressProps {
  /**
   * Export job ID to track
   */
  jobId: string;

  /**
   * Project name for display
   */
  projectName?: string;

  /**
   * Called when export completes
   */
  onComplete?: (outputPath: string) => void;

  /**
   * Called when export fails
   */
  onError?: (error: string) => void;

  /**
   * Called when cancel button is clicked
   */
  onCancel?: () => void;

  /**
   * Whether cancel is allowed
   */
  cancellable?: boolean;

  /**
   * Additional CSS classes
   */
  className?: string;
}

// Event payload from WebSocket
interface FFmpegProgressPayload {
  jobId: string;
  frame: number;
  totalFrames: number;
  fps: number;
  bitrate: number;
  speed: string;
  size: number;
  time: number; // Current timestamp in video
  percentage: number;
}

interface ExportCompletePayload {
  jobId: string;
  outputPath: string;
  duration: number;
  size: number;
}

interface ExportFailedPayload {
  jobId: string;
  error: string;
}

function formatTime(seconds: number): string {
  if (!isFinite(seconds) || seconds < 0) return '--:--';
  const hours = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  if (hours > 0) {
    return `${hours}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

function formatBitrate(kbps: number): string {
  if (kbps < 1000) return `${kbps.toFixed(0)} kbps`;
  return `${(kbps / 1000).toFixed(1)} Mbps`;
}

const initialProgress: ExportProgressData = {
  jobId: '',
  status: 'pending',
  percentage: 0,
  frame: 0,
  totalFrames: 0,
  fps: 0,
  etaSeconds: 0,
  currentSize: 0,
  estimatedSize: 0,
  bitrate: 0,
  speed: '0x',
  elapsedSeconds: 0,
};

/**
 * Export Progress Component
 */
export const ExportProgress = memo(function ExportProgress({
  jobId,
  projectName,
  onComplete,
  onError,
  onCancel,
  cancellable = true,
  className,
}: ExportProgressProps) {
  const [progress, setProgress] = useState<ExportProgressData>({
    ...initialProgress,
    jobId,
  });
  const [startTime] = useState(() => Date.now());

  // Listen for FFmpeg progress events
  useWebSocketEvent<FFmpegProgressPayload>(EventType.ASSEMBLY_PROGRESS, (event) => {
    if (event.payload.jobId !== jobId) return;

    const elapsed = (Date.now() - startTime) / 1000;
    const percentComplete = event.payload.percentage;

    // Calculate ETA based on progress
    let eta = 0;
    if (percentComplete > 0 && percentComplete < 100) {
      eta = (elapsed / percentComplete) * (100 - percentComplete);
    }

    // Estimate final size
    let estimatedSize = 0;
    if (percentComplete > 0) {
      estimatedSize = (event.payload.size / percentComplete) * 100;
    }

    setProgress({
      jobId,
      status: 'encoding',
      percentage: percentComplete,
      frame: event.payload.frame,
      totalFrames: event.payload.totalFrames,
      fps: event.payload.fps,
      etaSeconds: eta,
      currentSize: event.payload.size,
      estimatedSize,
      bitrate: event.payload.bitrate,
      speed: event.payload.speed,
      elapsedSeconds: elapsed,
    });
  });

  // Listen for completion
  useWebSocketEvent<ExportCompletePayload>(EventType.ASSEMBLY_COMPLETED, (event) => {
    if (event.payload.jobId !== jobId) return;

    const elapsed = (Date.now() - startTime) / 1000;

    setProgress((prev) => ({
      ...prev,
      status: 'completed',
      percentage: 100,
      currentSize: event.payload.size,
      estimatedSize: event.payload.size,
      elapsedSeconds: elapsed,
      outputPath: event.payload.outputPath,
    }));

    onComplete?.(event.payload.outputPath);
  });

  // Listen for errors (using BACKEND_ERROR since there's no specific export error event)
  useWebSocketEvent<ExportFailedPayload>(EventType.BACKEND_ERROR, (event) => {
    if (event.payload.jobId !== jobId) return;

    setProgress((prev) => ({
      ...prev,
      status: 'failed',
      errorMessage: event.payload.error,
    }));

    onError?.(event.payload.error);
  });

  const statusConfig = {
    pending: { label: 'Waiting...', color: 'text-surface-400', bg: 'bg-surface-500' },
    processing: { label: 'Processing...', color: 'text-blue-400', bg: 'bg-blue-500' },
    encoding: { label: 'Encoding...', color: 'text-primary-400', bg: 'bg-primary-500' },
    finalizing: { label: 'Finalizing...', color: 'text-green-400', bg: 'bg-green-500' },
    completed: { label: 'Complete!', color: 'text-green-400', bg: 'bg-green-500' },
    failed: { label: 'Failed', color: 'text-red-400', bg: 'bg-red-500' },
    cancelled: { label: 'Cancelled', color: 'text-yellow-400', bg: 'bg-yellow-500' },
  };

  const config = statusConfig[progress.status];

  return (
    <div
      className={cn(
        'rounded-xl bg-surface-800 border border-surface-700 overflow-hidden',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-surface-700">
        <div className="flex items-center gap-3">
          {progress.status === 'completed' ? (
            <CheckCircle className="w-5 h-5 text-green-400" />
          ) : progress.status === 'failed' ? (
            <AlertCircle className="w-5 h-5 text-red-400" />
          ) : (
            <Loader2 className="w-5 h-5 text-primary-400 animate-spin" />
          )}
          <div>
            <h3 className="font-medium text-surface-100">
              {projectName ? `Exporting ${projectName}` : 'Exporting...'}
            </h3>
            <p className={cn('text-sm', config.color)}>{config.label}</p>
          </div>
        </div>

        {/* Cancel button */}
        {cancellable &&
          progress.status !== 'completed' &&
          progress.status !== 'failed' &&
          onCancel && (
            <button
              onClick={onCancel}
              className="p-2 rounded-lg hover:bg-surface-700 transition-colors"
              title="Cancel export"
            >
              <X className="w-4 h-4 text-surface-400" />
            </button>
          )}
      </div>

      {/* Progress bar */}
      <div className="px-4 py-4">
        <div className="h-3 bg-surface-700 rounded-full overflow-hidden">
          <div
            className={cn(
              'h-full transition-all duration-300 ease-out',
              config.bg,
              progress.status === 'encoding' && 'animate-pulse'
            )}
            style={{ width: `${progress.percentage}%` }}
          />
        </div>
        <div className="flex items-center justify-between mt-2 text-sm">
          <span className="text-surface-400">
            {progress.frame > 0 && progress.totalFrames > 0
              ? `Frame ${progress.frame.toLocaleString()} / ${progress.totalFrames.toLocaleString()}`
              : 'Preparing...'}
          </span>
          <span className={cn('font-medium', config.color)}>{progress.percentage.toFixed(1)}%</span>
        </div>
      </div>

      {/* Stats grid */}
      {progress.status === 'encoding' && (
        <div className="grid grid-cols-4 gap-3 px-4 pb-4">
          <div className="p-3 rounded-lg bg-surface-900">
            <div className="flex items-center gap-2 text-surface-400 text-xs mb-1">
              <Film className="w-3.5 h-3.5" />
              <span>Encoding FPS</span>
            </div>
            <div className="text-lg font-medium text-surface-100">{progress.fps.toFixed(1)}</div>
          </div>

          <div className="p-3 rounded-lg bg-surface-900">
            <div className="flex items-center gap-2 text-surface-400 text-xs mb-1">
              <Gauge className="w-3.5 h-3.5" />
              <span>Speed</span>
            </div>
            <div className="text-lg font-medium text-surface-100">{progress.speed}</div>
          </div>

          <div className="p-3 rounded-lg bg-surface-900">
            <div className="flex items-center gap-2 text-surface-400 text-xs mb-1">
              <Clock className="w-3.5 h-3.5" />
              <span>ETA</span>
            </div>
            <div className="text-lg font-medium text-surface-100">
              {formatTime(progress.etaSeconds)}
            </div>
          </div>

          <div className="p-3 rounded-lg bg-surface-900">
            <div className="flex items-center gap-2 text-surface-400 text-xs mb-1">
              <HardDrive className="w-3.5 h-3.5" />
              <span>Size</span>
            </div>
            <div className="text-lg font-medium text-surface-100">
              {formatFileSize(progress.currentSize)}
            </div>
          </div>
        </div>
      )}

      {/* Additional info */}
      {progress.status === 'encoding' && (
        <div className="px-4 pb-4 text-xs text-surface-500 space-y-1">
          <div className="flex justify-between">
            <span>Bitrate</span>
            <span>{formatBitrate(progress.bitrate)}</span>
          </div>
          <div className="flex justify-between">
            <span>Elapsed</span>
            <span>{formatTime(progress.elapsedSeconds)}</span>
          </div>
          <div className="flex justify-between">
            <span>Est. Final Size</span>
            <span>{formatFileSize(progress.estimatedSize)}</span>
          </div>
        </div>
      )}

      {/* Completion info */}
      {progress.status === 'completed' && progress.outputPath && (
        <div className="px-4 pb-4">
          <div className="p-3 rounded-lg bg-green-500/10 border border-green-500/20">
            <div className="flex items-center gap-2 text-green-400 text-sm mb-1">
              <CheckCircle className="w-4 h-4" />
              <span>Export Complete!</span>
            </div>
            <p className="text-xs text-surface-400 break-all">{progress.outputPath}</p>
            <div className="flex items-center gap-4 mt-2 text-xs text-surface-500">
              <span>Size: {formatFileSize(progress.currentSize)}</span>
              <span>Time: {formatTime(progress.elapsedSeconds)}</span>
            </div>
          </div>
        </div>
      )}

      {/* Error info */}
      {progress.status === 'failed' && progress.errorMessage && (
        <div className="px-4 pb-4">
          <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20">
            <div className="flex items-center gap-2 text-red-400 text-sm mb-1">
              <AlertCircle className="w-4 h-4" />
              <span>Export Failed</span>
            </div>
            <p className="text-xs text-surface-400">{progress.errorMessage}</p>
          </div>
        </div>
      )}
    </div>
  );
});

/**
 * Compact export progress bar
 */
export const ExportProgressBar = memo(function ExportProgressBar({
  jobId,
  className,
}: {
  jobId: string;
  className?: string;
}) {
  const [percentage, setPercentage] = useState(0);
  const [status, setStatus] = useState<'pending' | 'encoding' | 'completed' | 'failed'>('pending');

  useWebSocketEvent<FFmpegProgressPayload>(EventType.ASSEMBLY_PROGRESS, (event) => {
    if (event.payload.jobId !== jobId) return;
    setPercentage(event.payload.percentage);
    setStatus('encoding');
  });

  useWebSocketEvent<ExportCompletePayload>(EventType.ASSEMBLY_COMPLETED, (event) => {
    if (event.payload.jobId !== jobId) return;
    setPercentage(100);
    setStatus('completed');
  });

  useWebSocketEvent<ExportFailedPayload>(EventType.BACKEND_ERROR, (event) => {
    if (event.payload.jobId !== jobId) return;
    setStatus('failed');
  });

  const barColor =
    status === 'completed' ? 'bg-green-500' : status === 'failed' ? 'bg-red-500' : 'bg-primary-500';

  return (
    <div className={cn('flex items-center gap-2', className)}>
      <div className="flex-1 h-2 bg-surface-700 rounded-full overflow-hidden">
        <div
          className={cn('h-full transition-all duration-300', barColor)}
          style={{ width: `${percentage}%` }}
        />
      </div>
      <span className="text-xs text-surface-400 min-w-[3rem] text-right">
        {percentage.toFixed(0)}%
      </span>
    </div>
  );
});

export default ExportProgress;
