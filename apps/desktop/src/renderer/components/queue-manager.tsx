/**
 * Queue manager component for viewing and managing generation jobs.
 * Provides priority control, cancellation, and monitoring.
 */

import { useState, useEffect, memo, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Clock,
  Play,
  Pause,
  XCircle,
  RefreshCw,
  ChevronUp,
  ChevronDown,
  ChevronsUp,
  ChevronsDown,
  Loader2,
  AlertTriangle,
  CheckCircle,
  Film,
  Trash2,
  RotateCcw,
  MoreVertical,
  Zap,
} from 'lucide-react';
import { cn } from '../lib/utils';
import { useWebSocketEvent, EventType } from '../lib/websocket';
import { useGenerationStore } from '../stores/generation-store';
import { useExperienceStore } from '../stores/experience-store';
import { useSettingsStore } from '../stores/settings-store';
import {
  estimateQueueTime,
  formatTimeEstimate,
  formatCompletionTime,
  formatQueuePosition,
  formatElapsedTime,
} from '../lib/time-estimates';

// Job interface
interface QueueJob {
  id: string;
  shotId: string;
  shotNumber: string | null;
  sceneId: string | null;
  jobNumber: number;
  status: string;
  provider: string;
  priority: number;
  progressPercent: number | null;
  progressMessage: string | null;
  errorMessage: string | null;
  queuedAt: string | null;
  startedAt: string | null;
  estimatedCompletionAt: string | null;
}

// Queue stats
interface QueueStats {
  pending: number;
  running: number;
  completed: number;
  failed: number;
  total: number;
}

interface QueueManagerProps {
  projectId?: string;
  compact?: boolean;
  onJobClick?: (jobId: string) => void;
}

// Status badge component
function StatusBadge({ status }: { status: string }) {
  const { getTerm } = useExperienceStore();

  const config: Record<string, { color: string; icon: typeof Clock }> = {
    pending: { color: 'bg-yellow-500/20 text-yellow-400', icon: Clock },
    preparing: { color: 'bg-blue-500/20 text-blue-400', icon: Loader2 },
    running: { color: 'bg-brand-500/20 text-brand-400', icon: Loader2 },
    post_processing: { color: 'bg-purple-500/20 text-purple-400', icon: Loader2 },
    completed: { color: 'bg-green-500/20 text-green-400', icon: CheckCircle },
    failed: { color: 'bg-red-500/20 text-red-400', icon: XCircle },
    cancelled: { color: 'bg-surface-500/20 text-surface-400', icon: XCircle },
    timeout: { color: 'bg-orange-500/20 text-orange-400', icon: AlertTriangle },
  };

  const conf = config[status] || config.pending;
  const Icon = conf.icon;
  const isAnimated = ['preparing', 'running', 'post_processing'].includes(status);
  const label = getTerm(status, 'generation');

  return (
    <span
      className={cn('inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs', conf.color)}
      role="status"
      aria-label={`Status: ${label}`}
    >
      <Icon className={cn('w-3 h-3', isAnimated && 'animate-spin')} aria-hidden="true" />
      {label}
    </span>
  );
}

// Progress bar
function ProgressBar({ percent }: { percent: number }) {
  return (
    <div
      className="h-1.5 bg-surface-700 rounded-full overflow-hidden"
      role="progressbar"
      aria-valuenow={Math.round(percent)}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={`Progress: ${Math.round(percent)}%`}
    >
      <div
        className="h-full bg-brand-500 rounded-full transition-all duration-300"
        style={{ width: `${Math.min(percent, 100)}%` }}
      />
    </div>
  );
}

// Queue job row - memoized for performance in lists
const QueueJobRow = memo(function QueueJobRow({
  job,
  position,
  onMoveUp,
  onMoveDown,
  onMoveToTop,
  onCancel,
  onRetry,
  onClick,
  isProcessing,
}: {
  job: QueueJob;
  position: number;
  onMoveUp: () => void;
  onMoveDown: () => void;
  onMoveToTop: () => void;
  onCancel: () => void;
  onRetry: () => void;
  onClick?: () => void;
  isProcessing: boolean;
}) {
  const [showActions, setShowActions] = useState(false);
  const { getMode } = useExperienceStore();
  const mode = getMode('generation');

  const isPending = job.status === 'pending';
  const isRunning = ['preparing', 'running', 'post_processing'].includes(job.status);
  const isFailed = ['failed', 'timeout'].includes(job.status);

  const shotLabel = `Shot ${job.shotNumber || job.shotId.slice(0, 8)}`;

  // Get position string for pending jobs
  const positionString = isPending ? formatQueuePosition(position, mode) : null;

  // Get elapsed time for running jobs
  const elapsedString = isRunning && job.startedAt ? formatElapsedTime(job.startedAt, mode) : null;

  return (
    <article
      className={cn(
        'p-3 bg-surface-800/50 rounded-lg border border-surface-700 hover:border-surface-600 transition-colors',
        onClick && 'cursor-pointer'
      )}
      onClick={onClick}
      aria-label={`${shotLabel}, Status: ${job.status}${job.progressPercent ? `, Progress: ${Math.round(job.progressPercent)}%` : ''}`}
      role={onClick ? 'button' : 'article'}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={onClick ? (e) => e.key === 'Enter' && onClick() : undefined}
    >
      <div className="flex items-center gap-3">
        {/* Shot info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <Film className="w-4 h-4 text-surface-400 shrink-0" aria-hidden="true" />
            <span className="font-medium truncate">
              {shotLabel}
            </span>
            <StatusBadge status={job.status} />
            {/* Queue position for pending jobs */}
            {positionString && (
              <span className="text-xs text-surface-500 bg-surface-700/50 px-2 py-0.5 rounded">
                {positionString}
              </span>
            )}
            {/* Elapsed time for running jobs */}
            {elapsedString && (
              <span className="text-xs text-brand-400">
                {elapsedString}
              </span>
            )}
          </div>
          {job.progressMessage && isRunning && (
            <p className="text-xs text-surface-400 mt-1" aria-live="polite">{job.progressMessage}</p>
          )}
          {job.errorMessage && isFailed && (
            <p className="text-xs text-red-400 mt-1 truncate" role="alert">{job.errorMessage}</p>
          )}
        </div>

        {/* Progress */}
        {isRunning && job.progressPercent !== null && (
          <div className="w-24">
            <div className="text-xs text-surface-400 text-right mb-1">
              {job.progressPercent.toFixed(0)}%
            </div>
            <ProgressBar percent={job.progressPercent} />
          </div>
        )}

        {/* Priority controls (only for pending) */}
        {isPending && (
          <div className="flex items-center gap-1" role="group" aria-label="Queue priority controls">
            <button
              onClick={(e) => {
                e.stopPropagation();
                onMoveToTop();
              }}
              disabled={isProcessing}
              className="icon-btn p-2 hover:bg-surface-700 rounded text-surface-400 hover:text-surface-200 disabled:opacity-50"
              title="Move to top"
              aria-label="Move job to top of queue"
            >
              <ChevronsUp className="w-4 h-4" aria-hidden="true" />
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onMoveUp();
              }}
              disabled={isProcessing}
              className="icon-btn p-2 hover:bg-surface-700 rounded text-surface-400 hover:text-surface-200 disabled:opacity-50"
              title="Move up"
              aria-label="Move job up in queue"
            >
              <ChevronUp className="w-4 h-4" aria-hidden="true" />
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onMoveDown();
              }}
              disabled={isProcessing}
              className="icon-btn p-2 hover:bg-surface-700 rounded text-surface-400 hover:text-surface-200 disabled:opacity-50"
              title="Move down"
              aria-label="Move job down in queue"
            >
              <ChevronDown className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Actions */}
        <div className="relative">
          <button
            onClick={(e) => {
              e.stopPropagation();
              setShowActions(!showActions);
            }}
            className="icon-btn p-2 hover:bg-surface-700 rounded"
            aria-label="More actions"
          >
            <MoreVertical className="w-4 h-4 text-surface-400" />
          </button>

          {showActions && (
            <div
              className="absolute right-0 top-full mt-1 py-1 bg-surface-800 border border-surface-700 rounded-lg shadow-xl z-10 min-w-32"
              onClick={(e) => e.stopPropagation()}
            >
              {isPending && (
                <button
                  onClick={() => {
                    onCancel();
                    setShowActions(false);
                  }}
                  disabled={isProcessing}
                  className="w-full px-3 py-1.5 text-left text-sm hover:bg-surface-700 flex items-center gap-2 text-red-400"
                >
                  <XCircle className="w-4 h-4" />
                  Cancel
                </button>
              )}
              {isFailed && (
                <button
                  onClick={() => {
                    onRetry();
                    setShowActions(false);
                  }}
                  disabled={isProcessing}
                  className="w-full px-3 py-1.5 text-left text-sm hover:bg-surface-700 flex items-center gap-2"
                >
                  <RotateCcw className="w-4 h-4" />
                  Retry
                </button>
              )}
              {isRunning && (
                <button
                  onClick={() => {
                    onCancel();
                    setShowActions(false);
                  }}
                  disabled={isProcessing}
                  className="w-full px-3 py-1.5 text-left text-sm hover:bg-surface-700 flex items-center gap-2 text-red-400"
                >
                  <Pause className="w-4 h-4" />
                  Cancel
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </article>
  );
});

// Stats summary with time estimates
function QueueStatsSummary({ stats }: { stats: QueueStats }) {
  const { getMode } = useExperienceStore();
  const settings = useSettingsStore((s) => s.settings);
  const mode = getMode('generation');

  // Calculate time estimate
  const provider = settings?.videoProvider || 'local';
  const concurrency = settings?.maxConcurrentGenerations || 1;
  const estimate = estimateQueueTime(stats.pending, stats.running, provider, concurrency);
  const timeString = formatTimeEstimate(estimate, mode);
  const completionString = formatCompletionTime(estimate, mode);

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-4 text-sm">
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full bg-yellow-400" />
          <span className="text-surface-400">Pending:</span>
          <span className="font-medium">{stats.pending}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full bg-brand-400 animate-pulse" />
          <span className="text-surface-400">Running:</span>
          <span className="font-medium">{stats.running}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full bg-green-400" />
          <span className="text-surface-400">Completed:</span>
          <span className="font-medium">{stats.completed}</span>
        </div>
        {stats.failed > 0 && (
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full bg-red-400" />
            <span className="text-surface-400">Failed:</span>
            <span className="font-medium text-red-400">{stats.failed}</span>
          </div>
        )}
      </div>

      {/* Time estimate */}
      {(stats.pending > 0 || stats.running > 0) && (
        <div className="flex items-center gap-2 text-sm">
          <Clock className="w-4 h-4 text-brand-400" />
          <span className="text-brand-400 font-medium">{timeString}</span>
          {completionString && (
            <span className="text-surface-500">({completionString})</span>
          )}
        </div>
      )}
    </div>
  );
}

// Worker status badge
function WorkerStatusBadge({ isPaused, isLoading }: { isPaused: boolean; isLoading?: boolean }) {
  if (isLoading) {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs bg-surface-700 text-surface-400">
        <Loader2 className="w-3 h-3 animate-spin" />
        Loading...
      </span>
    );
  }

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium',
        isPaused
          ? 'bg-yellow-500/20 text-yellow-400'
          : 'bg-green-500/20 text-green-400'
      )}
      role="status"
      aria-label={isPaused ? 'Queue worker is paused' : 'Queue worker is running'}
    >
      {isPaused ? (
        <>
          <Pause className="w-3 h-3" />
          Paused
        </>
      ) : (
        <>
          <Zap className="w-3 h-3" />
          Running
        </>
      )}
    </span>
  );
}

export function QueueManager({ projectId, compact = false, onJobClick }: QueueManagerProps) {
  const queryClient = useQueryClient();
  const [isProcessing, setIsProcessing] = useState(false);
  const [isTogglingWorker, setIsTogglingWorker] = useState(false);

  // Get worker status and controls from store
  const {
    workerStatus,
    fetchWorkerStatus,
    pauseWorker,
    resumeWorker,
  } = useGenerationStore();

  // Fetch worker status on mount and periodically
  useEffect(() => {
    fetchWorkerStatus();
    const interval = setInterval(fetchWorkerStatus, 10000); // Every 10 seconds
    return () => clearInterval(interval);
  }, [fetchWorkerStatus]);

  // Handle pause/resume toggle
  const handleToggleWorker = useCallback(async () => {
    setIsTogglingWorker(true);
    try {
      if (workerStatus?.is_paused) {
        await resumeWorker();
      } else {
        await pauseWorker();
      }
      // Refetch status after action
      await fetchWorkerStatus();
    } finally {
      setIsTogglingWorker(false);
    }
  }, [workerStatus?.is_paused, pauseWorker, resumeWorker, fetchWorkerStatus]);

  // Fetch queue
  const { data: jobs, isLoading, refetch } = useQuery({
    queryKey: ['queue', projectId],
    queryFn: async () => {
      return window.electronAPI.backendRequest<QueueJob[]>('queue.getAll', {
        project_id: projectId,
        include_completed: false,
        limit: 50,
      });
    },
    refetchInterval: 5000, // Refresh every 5 seconds
  });

  // Fetch stats
  const { data: stats } = useQuery({
    queryKey: ['queue-stats', projectId],
    queryFn: async () => {
      return window.electronAPI.backendRequest<QueueStats>('queue.getStats', {
        project_id: projectId,
      });
    },
    refetchInterval: 5000,
  });

  // Listen for WebSocket updates - real-time job status changes
  useWebSocketEvent(EventType.JOB_QUEUED, () => {
    refetch();
    queryClient.invalidateQueries({ queryKey: ['queue-stats'] });
  });

  useWebSocketEvent(EventType.JOB_STARTED, () => {
    refetch();
    queryClient.invalidateQueries({ queryKey: ['queue-stats'] });
  });

  useWebSocketEvent(EventType.JOB_PROGRESS, () => {
    refetch();
  });

  useWebSocketEvent(EventType.JOB_COMPLETED, () => {
    refetch();
    queryClient.invalidateQueries({ queryKey: ['queue-stats'] });
    // Also invalidate shots to show new thumbnails
    queryClient.invalidateQueries({ queryKey: ['shots'] });
  });

  useWebSocketEvent(EventType.JOB_FAILED, () => {
    refetch();
    queryClient.invalidateQueries({ queryKey: ['queue-stats'] });
  });

  // Listen for queue-level updates
  useWebSocketEvent(EventType.QUEUE_UPDATED, () => {
    refetch();
    queryClient.invalidateQueries({ queryKey: ['queue-stats'] });
  });

  // Mutations
  const moveToTop = useMutation({
    mutationFn: (jobId: string) =>
      window.electronAPI.backendRequest('queue.moveToTop', { job_id: jobId }),
    onSuccess: () => refetch(),
  });

  const setPriority = useMutation({
    mutationFn: ({ jobId, priority }: { jobId: string; priority: number }) =>
      window.electronAPI.backendRequest('queue.setPriority', { job_id: jobId, priority }),
    onSuccess: () => refetch(),
  });

  const cancelJob = useMutation({
    mutationFn: (jobId: string) =>
      window.electronAPI.backendRequest('generation.cancelJob', { job_id: jobId }),
    onSuccess: () => refetch(),
  });

  const retryJob = useMutation({
    mutationFn: (jobId: string) =>
      window.electronAPI.backendRequest('generation.retryJob', { job_id: jobId }),
    onSuccess: () => refetch(),
  });

  const cancelAll = useMutation({
    mutationFn: () =>
      window.electronAPI.backendRequest('queue.cancelAll', { project_id: projectId }),
    onSuccess: () => {
      refetch();
      queryClient.invalidateQueries({ queryKey: ['queue-stats'] });
    },
  });

  const retryFailed = useMutation({
    mutationFn: () =>
      window.electronAPI.backendRequest('queue.retryFailed', { project_id: projectId }),
    onSuccess: () => {
      refetch();
      queryClient.invalidateQueries({ queryKey: ['queue-stats'] });
    },
  });

  // Helper to change priority
  const handleMoveUp = (job: QueueJob) => {
    setPriority.mutate({ jobId: job.id, priority: job.priority + 5 });
  };

  const handleMoveDown = (job: QueueJob) => {
    setPriority.mutate({ jobId: job.id, priority: job.priority - 5 });
  };

  if (compact) {
    return (
      <div className="p-3 bg-surface-800 rounded-lg">
        <div className="flex items-center justify-between mb-2">
          {stats && <QueueStatsSummary stats={stats} />}
          <WorkerStatusBadge isPaused={workerStatus?.is_paused ?? false} isLoading={!workerStatus} />
        </div>
        {isLoading && <Loader2 className="w-4 h-4 animate-spin text-brand-400" />}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-medium flex items-center gap-2">
              <Clock className="w-5 h-5 text-brand-400" />
              Generation Queue
            </h2>
            <WorkerStatusBadge isPaused={workerStatus?.is_paused ?? false} isLoading={!workerStatus} />
          </div>
          {stats && (
            <div className="mt-1">
              <QueueStatsSummary stats={stats} />
            </div>
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* Pause/Resume Worker Button */}
          <button
            onClick={handleToggleWorker}
            disabled={isTogglingWorker || !workerStatus}
            className={cn(
              'px-3 py-1.5 rounded-lg text-sm flex items-center gap-1.5 transition-colors',
              workerStatus?.is_paused
                ? 'bg-green-500/20 text-green-400 hover:bg-green-500/30'
                : 'bg-yellow-500/20 text-yellow-400 hover:bg-yellow-500/30'
            )}
            title={workerStatus?.is_paused ? 'Resume processing new jobs' : 'Pause processing new jobs'}
            aria-label={workerStatus?.is_paused ? 'Resume queue worker' : 'Pause queue worker'}
          >
            {isTogglingWorker ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : workerStatus?.is_paused ? (
              <Play className="w-4 h-4" />
            ) : (
              <Pause className="w-4 h-4" />
            )}
            {workerStatus?.is_paused ? 'Resume' : 'Pause'}
          </button>

          <button
            onClick={() => refetch()}
            disabled={isLoading}
            className="p-2 hover:bg-surface-700 rounded-lg text-surface-400 hover:text-surface-200"
            title="Refresh"
          >
            <RefreshCw className={cn('w-4 h-4', isLoading && 'animate-spin')} />
          </button>

          {stats && stats.failed > 0 && (
            <button
              onClick={() => retryFailed.mutate()}
              disabled={retryFailed.isPending}
              className="px-3 py-1.5 bg-surface-700 hover:bg-surface-600 rounded-lg text-sm flex items-center gap-1.5"
            >
              <RotateCcw className="w-4 h-4" />
              Retry Failed ({stats.failed})
            </button>
          )}

          {stats && stats.pending > 0 && (
            <button
              onClick={() => cancelAll.mutate()}
              disabled={cancelAll.isPending}
              className="px-3 py-1.5 bg-red-500/20 text-red-400 hover:bg-red-500/30 rounded-lg text-sm flex items-center gap-1.5"
            >
              <Trash2 className="w-4 h-4" />
              Cancel All
            </button>
          )}
        </div>
      </div>

      {/* Queue list */}
      {isLoading ? (
        <div className="space-y-2" aria-label="Loading queue">
          {Array.from({ length: 3 }, (_, i) => (
            <div key={i} className="p-3 bg-surface-800/50 rounded-lg border border-surface-700 animate-pulse">
              <div className="flex items-center gap-3">
                <div className="w-4 h-4 bg-surface-700 rounded" />
                <div className="flex-1 space-y-2">
                  <div className="flex items-center gap-2">
                    <div className="h-5 w-32 bg-surface-700 rounded" />
                    <div className="h-5 w-16 bg-surface-700 rounded-full" />
                  </div>
                </div>
                <div className="h-6 w-20 bg-surface-700 rounded" />
              </div>
            </div>
          ))}
        </div>
      ) : jobs && jobs.length > 0 ? (
        <div className="space-y-2">
          {jobs.map((job, index) => (
            <QueueJobRow
              key={job.id}
              job={job}
              position={index + 1}
              onMoveUp={() => handleMoveUp(job)}
              onMoveDown={() => handleMoveDown(job)}
              onMoveToTop={() => moveToTop.mutate(job.id)}
              onCancel={() => cancelJob.mutate(job.id)}
              onRetry={() => retryJob.mutate(job.id)}
              onClick={onJobClick ? () => onJobClick(job.id) : undefined}
              isProcessing={
                moveToTop.isPending ||
                setPriority.isPending ||
                cancelJob.isPending ||
                retryJob.isPending
              }
            />
          ))}
        </div>
      ) : (
        <div className="text-center py-12 text-surface-400">
          <Clock className="w-8 h-8 mx-auto mb-2 opacity-50" />
          <p>Queue is empty</p>
          <p className="text-sm mt-1">Start generating shots to see them here</p>
        </div>
      )}
    </div>
  );
}

export default QueueManager;
