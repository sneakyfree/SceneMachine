/**
 * Operation Progress Component
 *
 * Reusable progress indicator for async operations like
 * generation, export, TTS, and lip sync.
 */

import { memo, useMemo } from 'react';
import { X, Loader2, CheckCircle, AlertCircle, Clock, Pause, Play } from 'lucide-react';
import { cn } from '../../lib/utils';

export type ProgressStatus =
  | 'pending'
  | 'running'
  | 'paused'
  | 'completed'
  | 'failed'
  | 'cancelled';

export interface ProgressData {
  /**
   * Current progress percentage (0-100)
   */
  percentage: number;

  /**
   * Current operation status
   */
  status: ProgressStatus;

  /**
   * Current step label
   */
  currentStep?: string;

  /**
   * Total number of steps
   */
  totalSteps?: number;

  /**
   * Current step number
   */
  currentStepNumber?: number;

  /**
   * Estimated time remaining in seconds
   */
  etaSeconds?: number;

  /**
   * Time elapsed in seconds
   */
  elapsedSeconds?: number;

  /**
   * Error message if failed
   */
  errorMessage?: string;

  /**
   * Whether the operation can be cancelled
   */
  cancellable?: boolean;

  /**
   * Whether the operation can be paused
   */
  pausable?: boolean;
}

interface OperationProgressProps {
  /**
   * Progress data
   */
  progress: ProgressData;

  /**
   * Operation title
   */
  title: string;

  /**
   * Size variant
   */
  size?: 'sm' | 'md' | 'lg';

  /**
   * Show detailed info (ETA, elapsed time)
   */
  showDetails?: boolean;

  /**
   * Called when cancel button is clicked
   */
  onCancel?: () => void;

  /**
   * Called when pause button is clicked
   */
  onPause?: () => void;

  /**
   * Called when resume button is clicked
   */
  onResume?: () => void;

  /**
   * Called when retry button is clicked (for failed operations)
   */
  onRetry?: () => void;

  /**
   * Additional CSS classes
   */
  className?: string;
}

const sizeClasses = {
  sm: {
    container: 'p-2',
    title: 'text-sm',
    bar: 'h-1',
    text: 'text-xs',
    icon: 'w-3.5 h-3.5',
  },
  md: {
    container: 'p-3',
    title: 'text-base',
    bar: 'h-1.5',
    text: 'text-sm',
    icon: 'w-4 h-4',
  },
  lg: {
    container: 'p-4',
    title: 'text-lg',
    bar: 'h-2',
    text: 'text-base',
    icon: 'w-5 h-5',
  },
};

const statusColors = {
  pending: {
    bar: 'bg-surface-500',
    text: 'text-surface-400',
  },
  running: {
    bar: 'bg-primary-500',
    text: 'text-primary-400',
  },
  paused: {
    bar: 'bg-yellow-500',
    text: 'text-yellow-400',
  },
  completed: {
    bar: 'bg-green-500',
    text: 'text-green-400',
  },
  failed: {
    bar: 'bg-red-500',
    text: 'text-red-400',
  },
  cancelled: {
    bar: 'bg-surface-500',
    text: 'text-surface-400',
  },
};

/**
 * Format seconds into human-readable time
 */
function formatTime(seconds: number): string {
  if (seconds < 60) {
    return `${Math.round(seconds)}s`;
  }
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.round(seconds % 60);
  if (minutes < 60) {
    return `${minutes}m ${remainingSeconds}s`;
  }
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return `${hours}h ${remainingMinutes}m`;
}

/**
 * Get status icon
 */
function StatusIcon({ status, className }: { status: ProgressStatus; className: string }) {
  switch (status) {
    case 'running':
      return <Loader2 className={cn(className, 'animate-spin')} />;
    case 'paused':
      return <Pause className={className} />;
    case 'completed':
      return <CheckCircle className={className} />;
    case 'failed':
      return <AlertCircle className={className} />;
    case 'cancelled':
      return <X className={className} />;
    case 'pending':
    default:
      return <Clock className={className} />;
  }
}

/**
 * Operation Progress Component
 */
export const OperationProgress = memo(function OperationProgress({
  progress,
  title,
  size = 'md',
  showDetails = true,
  onCancel,
  onPause,
  onResume,
  onRetry,
  className,
}: OperationProgressProps) {
  const sizes = sizeClasses[size];
  const colors = statusColors[progress.status];

  const percentage = Math.min(100, Math.max(0, progress.percentage));

  const etaText = useMemo(() => {
    if (progress.etaSeconds === undefined || progress.etaSeconds <= 0) {
      return null;
    }
    return `~${formatTime(progress.etaSeconds)} remaining`;
  }, [progress.etaSeconds]);

  const elapsedText = useMemo(() => {
    if (progress.elapsedSeconds === undefined) {
      return null;
    }
    return `${formatTime(progress.elapsedSeconds)} elapsed`;
  }, [progress.elapsedSeconds]);

  const stepText = useMemo(() => {
    if (progress.totalSteps && progress.currentStepNumber) {
      return `Step ${progress.currentStepNumber}/${progress.totalSteps}`;
    }
    return null;
  }, [progress.totalSteps, progress.currentStepNumber]);

  return (
    <div
      className={cn(
        'rounded-lg bg-surface-800 border border-surface-700',
        sizes.container,
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <StatusIcon status={progress.status} className={cn(sizes.icon, colors.text)} />
          <span className={cn('font-medium text-surface-100', sizes.title)}>{title}</span>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-1">
          {progress.status === 'running' && progress.pausable && onPause && (
            <button
              onClick={onPause}
              className="p-1 rounded hover:bg-surface-700 transition-colors"
              title="Pause"
            >
              <Pause className={cn(sizes.icon, 'text-surface-400')} />
            </button>
          )}

          {progress.status === 'paused' && onResume && (
            <button
              onClick={onResume}
              className="p-1 rounded hover:bg-surface-700 transition-colors"
              title="Resume"
            >
              <Play className={cn(sizes.icon, 'text-surface-400')} />
            </button>
          )}

          {(progress.status === 'running' || progress.status === 'paused') &&
            progress.cancellable &&
            onCancel && (
              <button
                onClick={onCancel}
                className="p-1 rounded hover:bg-surface-700 transition-colors"
                title="Cancel"
              >
                <X className={cn(sizes.icon, 'text-surface-400')} />
              </button>
            )}

          {progress.status === 'failed' && onRetry && (
            <button
              onClick={onRetry}
              className={cn(
                'px-2 py-0.5 rounded text-xs font-medium',
                'bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-colors'
              )}
            >
              Retry
            </button>
          )}
        </div>
      </div>

      {/* Progress bar */}
      <div className={cn('w-full rounded-full bg-surface-700 overflow-hidden', sizes.bar)}>
        <div
          className={cn(
            'h-full transition-all duration-300 ease-out',
            colors.bar,
            progress.status === 'running' && 'animate-pulse'
          )}
          style={{ width: `${percentage}%` }}
        />
      </div>

      {/* Details */}
      <div className={cn('flex items-center justify-between mt-2', sizes.text)}>
        <div className="flex items-center gap-2 text-surface-400">
          {progress.currentStep && <span>{progress.currentStep}</span>}
          {stepText && !progress.currentStep && <span>{stepText}</span>}
          {progress.status === 'failed' && progress.errorMessage && (
            <span className="text-red-400">{progress.errorMessage}</span>
          )}
        </div>

        <div className="flex items-center gap-3 text-surface-500">
          {showDetails && (
            <>
              {progress.status === 'running' && etaText && <span>{etaText}</span>}
              {elapsedText && <span>{elapsedText}</span>}
            </>
          )}
          <span className={cn('font-medium', colors.text)}>{percentage.toFixed(0)}%</span>
        </div>
      </div>
    </div>
  );
});

/**
 * Compact progress bar without container
 */
export const ProgressBar = memo(function ProgressBar({
  percentage,
  status = 'running',
  size = 'md',
  showPercentage = true,
  className,
}: {
  percentage: number;
  status?: ProgressStatus;
  size?: 'sm' | 'md' | 'lg';
  showPercentage?: boolean;
  className?: string;
}) {
  const sizes = sizeClasses[size];
  const colors = statusColors[status];
  const clampedPercentage = Math.min(100, Math.max(0, percentage));

  return (
    <div className={cn('flex items-center gap-2', className)}>
      <div className={cn('flex-1 rounded-full bg-surface-700 overflow-hidden', sizes.bar)}>
        <div
          className={cn(
            'h-full transition-all duration-300 ease-out',
            colors.bar,
            status === 'running' && 'animate-pulse'
          )}
          style={{ width: `${clampedPercentage}%` }}
        />
      </div>
      {showPercentage && (
        <span className={cn('font-medium min-w-[3rem] text-right', sizes.text, colors.text)}>
          {clampedPercentage.toFixed(0)}%
        </span>
      )}
    </div>
  );
});

/**
 * Indeterminate progress spinner
 */
export const IndeterminateProgress = memo(function IndeterminateProgress({
  label,
  size = 'md',
  className,
}: {
  label?: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}) {
  const sizes = sizeClasses[size];

  return (
    <div className={cn('flex items-center gap-2', className)}>
      <Loader2 className={cn(sizes.icon, 'text-primary-400 animate-spin')} />
      {label && <span className={cn('text-surface-400', sizes.text)}>{label}</span>}
    </div>
  );
});

export default OperationProgress;
