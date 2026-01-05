/**
 * Generation page.
 *
 * Manages the video generation queue and displays shot previews
 * for review and approval.
 */

import { useState, useCallback, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Play,
  ArrowLeft,
  Check,
  Loader2,
  AlertCircle,
  RefreshCw,
  Pause,
  SkipForward,
  Grid,
  List,
  Filter,
  Clock,
  Sparkles,
  CheckCircle,
  XCircle,
  Settings,
  ChevronDown,
} from 'lucide-react';
import { ShotPreview, ModelSelector, BatchCostSummary } from '../components';
import { cn } from '../lib/utils';
import { useWebSocketEvent, EventType, WebSocketEvent } from '../lib/websocket';
import { useToast } from '../stores/toast-store';
import { useGenerationStore } from '../stores/generation-store';

interface Scene {
  id: string;
  sceneNumber: string;
  heading: string;
  shots: Shot[];
}

interface Shot {
  id: string;
  sceneId: string;
  shotNumber: string;
  sequenceNumber: number;
  shotType: string;
  cameraMovement: string;
  description: string;
  durationSeconds: number;
  state: string;
  outputVideoPath?: string;
  outputThumbnailPath?: string;
}

interface Job {
  id: string;
  shotId: string;
  jobNumber: number;
  status: string;
  progressPercent?: number;
  progressMessage?: string;
  errorMessage?: string;
  outputPath?: string;
  queuedAt?: string;
}

interface QueueStatus {
  totalJobs: number;
  pending: number;
  running: number;
  completed: number;
  failed: number;
}

type ViewMode = 'grid' | 'list';
type FilterType = 'all' | 'pending' | 'generating' | 'review' | 'approved' | 'failed';

export function GenerationPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  const [filter, setFilter] = useState<FilterType>('all');
  const [isProcessing, setIsProcessing] = useState(false);
  const [showModelSettings, setShowModelSettings] = useState(false);
  const toast = useToast();

  // Generation store for provider/model selection
  const {
    selectedProvider,
    selectedModel,
    setProvider,
    setModel,
    fetchProvidersHealth,
    fetchModelsForProvider,
  } = useGenerationStore();

  // Fetch provider health on mount
  useEffect(() => {
    fetchProvidersHealth();
  }, [fetchProvidersHealth]);

  // Fetch models when provider changes
  useEffect(() => {
    if (selectedProvider) {
      fetchModelsForProvider(selectedProvider);
    }
  }, [selectedProvider, fetchModelsForProvider]);

  // Fetch scenes with shots
  const { data: scenes, isLoading: isLoadingScenes, refetch: refetchScenes } = useQuery({
    queryKey: ['scenes', projectId, 'withShots'],
    queryFn: async () => {
      const result = await window.electronAPI.backendRequest<Scene[]>(
        'scenes.list',
        { project_id: projectId, include_shots: true }
      );
      return result;
    },
    enabled: !!projectId,
    refetchInterval: isProcessing ? 3000 : false,
  });

  // Fetch queue status
  const { data: queueStatus, refetch: refetchQueueStatus } = useQuery({
    queryKey: ['queueStatus', projectId],
    queryFn: async () => {
      const result = await window.electronAPI.backendRequest<QueueStatus>(
        'generation.getQueueStatus',
        { project_id: projectId }
      );
      return result;
    },
    enabled: !!projectId,
    refetchInterval: isProcessing ? 2000 : false,
  });

  // Fetch pending jobs
  const { data: pendingJobs, refetch: refetchJobs } = useQuery({
    queryKey: ['pendingJobs'],
    queryFn: async () => {
      const result = await window.electronAPI.backendRequest<Job[]>(
        'generation.getPendingJobs',
        { limit: 50 }
      );
      return result;
    },
    refetchInterval: isProcessing ? 2000 : false,
  });

  // Listen for WebSocket updates - real-time generation status
  useWebSocketEvent(EventType.JOB_QUEUED, () => {
    refetchJobs();
    refetchQueueStatus();
  });

  useWebSocketEvent(EventType.JOB_STARTED, (event: WebSocketEvent) => {
    refetchJobs();
    refetchQueueStatus();
    setIsProcessing(true);
    toast.info('Generation started', event.data?.message || 'Processing shot...');
  });

  useWebSocketEvent(EventType.JOB_PROGRESS, () => {
    refetchJobs();
  });

  useWebSocketEvent(EventType.JOB_COMPLETED, (event: WebSocketEvent) => {
    refetchScenes();
    refetchJobs();
    refetchQueueStatus();
    toast.success('Shot generated', event.data?.message || 'Generation completed successfully');
  });

  useWebSocketEvent(EventType.JOB_FAILED, (event: WebSocketEvent) => {
    refetchScenes();
    refetchJobs();
    refetchQueueStatus();
    toast.error(
      'Generation failed',
      event.data?.error_message || 'An error occurred during generation',
      {
        action: event.data?.job_id
          ? {
              label: 'Retry',
              onClick: () => {
                window.electronAPI.backendRequest('generation.retryJob', {
                  job_id: event.data.job_id,
                });
              },
            }
          : undefined,
      }
    );
  });

  useWebSocketEvent(EventType.QUEUE_UPDATED, () => {
    refetchQueueStatus();
  });

  // Queue project mutation
  const queueProjectMutation = useMutation({
    mutationFn: async () => {
      return window.electronAPI.backendRequest('generation.queueProject', {
        project_id: projectId,
        provider: selectedProvider || 'mock',
        model: selectedModel || undefined,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scenes', projectId] });
      queryClient.invalidateQueries({ queryKey: ['queueStatus', projectId] });
      setIsProcessing(true);
      toast.success('Generation started', 'Project queued for generation');
    },
    onError: (error: Error) => {
      toast.error('Failed to queue project', error.message);
    },
  });

  // Process next job mutation
  const processJobMutation = useMutation({
    mutationFn: async (jobId: string) => {
      return window.electronAPI.backendRequest('generation.processJob', {
        job_id: jobId,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scenes', projectId] });
      queryClient.invalidateQueries({ queryKey: ['queueStatus', projectId] });
      queryClient.invalidateQueries({ queryKey: ['pendingJobs'] });
    },
    onError: (error: Error) => {
      toast.error('Failed to process job', error.message);
    },
  });

  // Approve shot mutation
  const approveShotMutation = useMutation({
    mutationFn: async (shotId: string) => {
      return window.electronAPI.backendRequest('generation.approveShot', {
        shot_id: shotId,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scenes', projectId] });
      toast.success('Shot approved', 'Shot marked as approved');
    },
    onError: (error: Error) => {
      toast.error('Failed to approve shot', error.message);
    },
  });

  // Reject shot mutation
  const rejectShotMutation = useMutation({
    mutationFn: async ({ shotId, notes }: { shotId: string; notes?: string }) => {
      return window.electronAPI.backendRequest('generation.rejectShot', {
        shot_id: shotId,
        notes,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scenes', projectId] });
      toast.info('Shot rejected', 'Shot will be regenerated');
    },
    onError: (error: Error) => {
      toast.error('Failed to reject shot', error.message);
    },
  });

  // Queue shot for regeneration
  const regenerateShotMutation = useMutation({
    mutationFn: async (shotId: string) => {
      return window.electronAPI.backendRequest('generation.queueShot', {
        shot_id: shotId,
        provider: selectedProvider || 'mock',
        model: selectedModel || undefined,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scenes', projectId] });
      queryClient.invalidateQueries({ queryKey: ['queueStatus', projectId] });
      toast.info('Shot queued', 'Shot added to generation queue');
    },
    onError: (error: Error) => {
      toast.error('Failed to queue shot', error.message);
    },
  });

  // Process pending jobs automatically
  useEffect(() => {
    if (isProcessing && pendingJobs && pendingJobs.length > 0) {
      const nextJob = pendingJobs[0];
      if (nextJob && !processJobMutation.isPending) {
        processJobMutation.mutate(nextJob.id);
      }
    } else if (pendingJobs?.length === 0 && queueStatus?.running === 0) {
      setIsProcessing(false);
    }
  }, [pendingJobs, isProcessing, processJobMutation, queueStatus]);

  // Get all shots flat
  const allShots = scenes?.flatMap((s) => s.shots) || [];

  // Filter shots
  const filteredShots = allShots.filter((shot) => {
    switch (filter) {
      case 'pending':
        return shot.state === 'planned' || shot.state === 'queued';
      case 'generating':
        return shot.state === 'generating';
      case 'review':
        return shot.state === 'generated';
      case 'approved':
        return shot.state === 'approved';
      case 'failed':
        return shot.state === 'failed' || shot.state === 'rejected';
      default:
        return true;
    }
  });

  // Stats
  const stats = {
    total: allShots.length,
    pending: allShots.filter((s) => s.state === 'planned' || s.state === 'queued').length,
    generating: allShots.filter((s) => s.state === 'generating').length,
    review: allShots.filter((s) => s.state === 'generated').length,
    approved: allShots.filter((s) => s.state === 'approved').length,
    failed: allShots.filter((s) => s.state === 'failed' || s.state === 'rejected').length,
  };

  const allApproved = stats.total > 0 && stats.approved === stats.total;
  const progress = stats.total > 0 ? ((stats.approved + stats.review) / stats.total) * 100 : 0;

  const handleApprove = useCallback(
    (shotId: string) => {
      approveShotMutation.mutate(shotId);
    },
    [approveShotMutation]
  );

  const handleReject = useCallback(
    (shotId: string, notes?: string) => {
      rejectShotMutation.mutate({ shotId, notes });
    },
    [rejectShotMutation]
  );

  const handleRegenerate = useCallback(
    (shotId: string) => {
      regenerateShotMutation.mutate(shotId);
    },
    [regenerateShotMutation]
  );

  if (isLoadingScenes) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-surface-400">Loading shots...</div>
      </div>
    );
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate(`/project/${projectId}`)}
            className="p-2 hover:bg-surface-800 rounded-lg transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Play className="w-7 h-7 text-brand-400" />
              Generation
            </h1>
            <p className="text-surface-400 mt-1">
              Generate and review video content for each shot
            </p>
          </div>
        </div>

        {/* Controls */}
        <div className="flex items-center gap-4">
          {!isProcessing && stats.pending > 0 && (
            <button
              onClick={() => queueProjectMutation.mutate()}
              disabled={queueProjectMutation.isPending}
              className="btn-primary"
            >
              <Sparkles className="w-4 h-4 mr-2" />
              Generate All ({stats.pending})
            </button>
          )}

          {isProcessing && (
            <button
              onClick={() => setIsProcessing(false)}
              className="btn-secondary"
            >
              <Pause className="w-4 h-4 mr-2" />
              Pause
            </button>
          )}
        </div>
      </div>

      {/* Stats Bar */}
      <div className="grid grid-cols-6 gap-4 mb-6">
        <div className="card p-4">
          <div className="text-sm text-surface-400 mb-1">Total</div>
          <div className="text-2xl font-bold">{stats.total}</div>
        </div>
        <div className="card p-4">
          <div className="text-sm text-surface-400 mb-1">Pending</div>
          <div className="text-2xl font-bold flex items-center gap-2">
            <Clock className="w-5 h-5 text-surface-500" />
            {stats.pending}
          </div>
        </div>
        <div className="card p-4">
          <div className="text-sm text-surface-400 mb-1">Generating</div>
          <div className="text-2xl font-bold flex items-center gap-2">
            <Loader2
              className={cn(
                'w-5 h-5 text-yellow-400',
                stats.generating > 0 && 'animate-spin'
              )}
            />
            {stats.generating}
          </div>
        </div>
        <div className="card p-4">
          <div className="text-sm text-surface-400 mb-1">Review</div>
          <div className="text-2xl font-bold flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-brand-400" />
            {stats.review}
          </div>
        </div>
        <div className="card p-4">
          <div className="text-sm text-surface-400 mb-1">Approved</div>
          <div className="text-2xl font-bold flex items-center gap-2">
            <CheckCircle className="w-5 h-5 text-green-400" />
            {stats.approved}
          </div>
        </div>
        <div className="card p-4">
          <div className="text-sm text-surface-400 mb-1">Failed</div>
          <div className="text-2xl font-bold flex items-center gap-2">
            <XCircle className="w-5 h-5 text-red-400" />
            {stats.failed}
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="card p-4 mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-surface-400">Overall Progress</span>
          <span className="text-sm font-medium">{Math.round(progress)}%</span>
        </div>
        <div className="w-full h-3 bg-surface-700 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-brand-500 to-green-500 transition-all"
            style={{ width: `${progress}%` }}
          />
        </div>
        {isProcessing && (
          <p className="text-xs text-surface-500 mt-2">
            Processing... {queueStatus?.running || 0} job(s) running
          </p>
        )}
      </div>

      {/* Model Settings Panel */}
      <div className="card p-4 mb-6">
        <button
          onClick={() => setShowModelSettings(!showModelSettings)}
          className="flex items-center justify-between w-full"
        >
          <div className="flex items-center gap-2">
            <Settings className="w-5 h-5 text-brand-400" />
            <span className="font-medium">Generation Settings</span>
            {selectedProvider && (
              <span className="px-2 py-0.5 bg-surface-700 text-xs rounded">
                {selectedProvider}
                {selectedModel && ` / ${selectedModel}`}
              </span>
            )}
          </div>
          <ChevronDown
            className={cn(
              'w-5 h-5 text-surface-400 transition-transform',
              showModelSettings && 'rotate-180'
            )}
          />
        </button>

        {showModelSettings && (
          <div className="mt-4 pt-4 border-t border-surface-700 space-y-4">
            <div className="grid grid-cols-2 gap-4">
              {/* Provider Selection */}
              <div>
                <label className="block text-sm text-surface-400 mb-2">
                  Video Provider
                </label>
                <select
                  value={selectedProvider || ''}
                  onChange={(e) => {
                    setProvider(e.target.value);
                    setModel(null);
                  }}
                  className="w-full px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg text-sm focus:outline-none focus:border-brand-500"
                >
                  <option value="">Select provider...</option>
                  <option value="mock">Mock (Testing)</option>
                  <option value="replicate">Replicate</option>
                  <option value="fal">Fal.ai</option>
                  <option value="comfyui">ComfyUI (Local)</option>
                  <option value="runpod">RunPod</option>
                </select>
              </div>

              {/* Model Selection */}
              {selectedProvider && (
                <div>
                  <label className="block text-sm text-surface-400 mb-2">
                    Model
                  </label>
                  <ModelSelector
                    providerId={selectedProvider}
                    selectedModel={selectedModel}
                    onModelSelect={setModel}
                    showCost
                  />
                </div>
              )}
            </div>

            {/* Cost Estimate for Pending Shots */}
            {stats.pending > 0 && selectedProvider && (
              <div className="mt-4 pt-4 border-t border-surface-700">
                <BatchCostSummary
                  provider={selectedProvider}
                  modelId={selectedModel || undefined}
                  shotCount={stats.pending}
                  totalDurationSeconds={
                    allShots
                      .filter((s) => s.state === 'planned' || s.state === 'queued')
                      .reduce((sum, s) => sum + (s.durationSeconds || 5), 0)
                  }
                />
              </div>
            )}
          </div>
        )}
      </div>

      {/* Toolbar */}
      <div className="flex items-center justify-between mb-6">
        {/* Filters */}
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-surface-500" />
          {(['all', 'pending', 'generating', 'review', 'approved', 'failed'] as FilterType[]).map(
            (filterType) => (
              <button
                key={filterType}
                onClick={() => setFilter(filterType)}
                className={cn(
                  'px-3 py-1.5 rounded-lg text-sm transition-colors',
                  filter === filterType
                    ? 'bg-brand-500/20 text-brand-400'
                    : 'bg-surface-800 text-surface-400 hover:bg-surface-700'
                )}
              >
                {filterType.charAt(0).toUpperCase() + filterType.slice(1)}
                {filterType !== 'all' && (
                  <span className="ml-1 text-surface-500">
                    ({stats[filterType as keyof typeof stats]})
                  </span>
                )}
              </button>
            )
          )}
        </div>

        {/* View Toggle */}
        <div className="flex items-center gap-1 bg-surface-800 rounded-lg p-1">
          <button
            onClick={() => setViewMode('grid')}
            className={cn(
              'p-1.5 rounded transition-colors',
              viewMode === 'grid'
                ? 'bg-surface-700 text-white'
                : 'text-surface-400 hover:text-white'
            )}
          >
            <Grid className="w-4 h-4" />
          </button>
          <button
            onClick={() => setViewMode('list')}
            className={cn(
              'p-1.5 rounded transition-colors',
              viewMode === 'list'
                ? 'bg-surface-700 text-white'
                : 'text-surface-400 hover:text-white'
            )}
          >
            <List className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Shots Grid/List */}
      {filteredShots.length > 0 ? (
        <div
          className={cn(
            viewMode === 'grid'
              ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4'
              : 'space-y-4'
          )}
        >
          {filteredShots.map((shot) => {
            const jobsForShot = pendingJobs?.filter((j) => j.shotId === shot.id);
            const latestJob = jobsForShot?.[0];

            return (
              <ShotPreview
                key={shot.id}
                shot={shot}
                latestJob={latestJob}
                onApprove={handleApprove}
                onReject={handleReject}
                onRegenerate={handleRegenerate}
                disabled={
                  approveShotMutation.isPending ||
                  rejectShotMutation.isPending ||
                  regenerateShotMutation.isPending
                }
              />
            );
          })}
        </div>
      ) : (
        <div className="text-center py-16">
          <Play className="w-16 h-16 mx-auto text-surface-600 mb-4" />
          <h3 className="text-lg font-medium mb-2">No Shots Found</h3>
          <p className="text-surface-400">
            {filter !== 'all'
              ? 'No shots match the current filter.'
              : 'Shots will appear here once scenes are planned.'}
          </p>
        </div>
      )}

      {/* Continue Button */}
      {allApproved && (
        <div className="fixed bottom-8 right-8">
          <button
            onClick={() => navigate(`/project/${projectId}`)}
            className="btn-primary shadow-lg"
          >
            <Check className="w-4 h-4 mr-2" />
            Continue to Export
          </button>
        </div>
      )}
    </div>
  );
}
