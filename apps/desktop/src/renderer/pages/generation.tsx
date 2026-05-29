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
  GitCompare,
} from 'lucide-react';
import { ShotPreview, ModelSelector, BatchCostSummary, ComparisonView } from '../components';
import { QualityRadarChart } from '../components/quality-radar-chart';
import { IPAdapterControls } from '../components/ip-adapter-controls';
import { cn } from '../lib/utils';
import { useTranslation } from '../i18n/use-translation';
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
  const [compareMode, setCompareMode] = useState(false);
  const [selectedForCompare, setSelectedForCompare] = useState<Set<string>>(new Set());
  const [showComparison, setShowComparison] = useState(false);
  const toast = useToast();
  const { t } = useTranslation();

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
  const {
    data: scenes,
    isLoading: isLoadingScenes,
    refetch: refetchScenes,
  } = useQuery({
    queryKey: ['scenes', projectId, 'withShots'],
    queryFn: async () => {
      const result = await window.electronAPI.backendRequest<Scene[]>('scenes.list', {
        project_id: projectId,
        include_shots: true,
      });
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
      const result = await window.electronAPI.backendRequest<Job[]>('generation.getPendingJobs', {
        limit: 50,
      });
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
    toast.info(
      t('generation.generationStarted', 'Generation started'),
      event.data?.message || t('generation.processingShot', 'Processing shot...')
    );
  });

  useWebSocketEvent(EventType.JOB_PROGRESS, () => {
    refetchJobs();
  });

  useWebSocketEvent(EventType.JOB_COMPLETED, (event: WebSocketEvent) => {
    refetchScenes();
    refetchJobs();
    refetchQueueStatus();
    toast.success(
      t('generation.shotGenerated', 'Shot generated'),
      event.data?.message || t('generation.generationCompletedSuccessfully', 'Generation completed successfully')
    );
  });

  useWebSocketEvent(EventType.JOB_FAILED, (event: WebSocketEvent) => {
    refetchScenes();
    refetchJobs();
    refetchQueueStatus();
    toast.error(
      t('generation.generationFailed', 'Generation failed'),
      event.data?.error_message || t('generation.anErrorOccurredDuringGeneration', 'An error occurred during generation'),
      {
        action: event.data?.job_id
          ? {
              label: t('generation.retry', 'Retry'),
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
      toast.success(
        t('generation.generationStarted', 'Generation started'),
        t('generation.projectQueuedForGeneration', 'Project queued for generation')
      );
    },
    onError: (error: Error) => {
      toast.error(t('generation.failedToQueueProject', 'Failed to queue project'), error.message);
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
      toast.error(t('generation.failedToProcessJob', 'Failed to process job'), error.message);
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
      toast.success(
        t('generation.shotApproved', 'Shot approved'),
        t('generation.shotMarkedAsApproved', 'Shot marked as approved')
      );
    },
    onError: (error: Error) => {
      toast.error(t('generation.failedToApproveShot', 'Failed to approve shot'), error.message);
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
      toast.info(
        t('generation.shotRejected', 'Shot rejected'),
        t('generation.shotWillBeRegenerated', 'Shot will be regenerated')
      );
    },
    onError: (error: Error) => {
      toast.error(t('generation.failedToRejectShot', 'Failed to reject shot'), error.message);
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
      toast.info(
        t('generation.shotQueued', 'Shot queued'),
        t('generation.shotAddedToGenerationQueue', 'Shot added to generation queue')
      );
    },
    onError: (error: Error) => {
      toast.error(t('generation.failedToQueueShot', 'Failed to queue shot'), error.message);
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

  const toggleCompareMode = useCallback(() => {
    setCompareMode((prev) => !prev);
    setSelectedForCompare(new Set());
  }, []);

  const toggleShotSelection = useCallback(
    (shotId: string) => {
      setSelectedForCompare((prev) => {
        const newSet = new Set(prev);
        if (newSet.has(shotId)) {
          newSet.delete(shotId);
        } else {
          // Limit to 3 selections
          if (newSet.size < 3) {
            newSet.add(shotId);
          } else {
            toast.warning(
              t('generation.maximum3Videos', 'Maximum 3 videos'),
              t('generation.youCanOnlyCompareUpTo3VideosAtOnce', 'You can only compare up to 3 videos at once')
            );
          }
        }
        return newSet;
      });
    },
    [toast]
  );

  const handleCompare = useCallback(() => {
    if (selectedForCompare.size >= 2) {
      setShowComparison(true);
    } else {
      toast.info(
        t('generation.selectVideos', 'Select videos'),
        t('generation.selectAtLeast2VideosToCompare', 'Select at least 2 videos to compare')
      );
    }
  }, [selectedForCompare, toast]);

  const handleSelectBest = useCallback(
    (shotId: string) => {
      approveShotMutation.mutate(shotId);
      setShowComparison(false);
      setCompareMode(false);
      setSelectedForCompare(new Set());
    },
    [approveShotMutation]
  );

  if (isLoadingScenes) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-surface-400">{t('generation.loadingShots', 'Loading shots...')}</div>
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
              {t('generation.generation', 'Generation')}
            </h1>
            <p className="text-surface-400 mt-1">{t('generation.generateAndReviewVideoContentForEachShot', 'Generate and review video content for each shot')}</p>
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
              {t('generation.generateAll', 'Generate All')} ({stats.pending})
            </button>
          )}

          {isProcessing && (
            <button onClick={() => setIsProcessing(false)} className="btn-secondary">
              <Pause className="w-4 h-4 mr-2" />
              {t('generation.pause', 'Pause')}
            </button>
          )}
        </div>
      </div>

      {/* Stats Bar */}
      <div className="grid grid-cols-6 gap-4 mb-6">
        <div className="card p-4">
          <div className="text-sm text-surface-400 mb-1">{t('generation.total', 'Total')}</div>
          <div className="text-2xl font-bold">{stats.total}</div>
        </div>
        <div className="card p-4">
          <div className="text-sm text-surface-400 mb-1">{t('generation.pending', 'Pending')}</div>
          <div className="text-2xl font-bold flex items-center gap-2">
            <Clock className="w-5 h-5 text-surface-500" />
            {stats.pending}
          </div>
        </div>
        <div className="card p-4">
          <div className="text-sm text-surface-400 mb-1">{t('generation.generating', 'Generating')}</div>
          <div className="text-2xl font-bold flex items-center gap-2">
            <Loader2
              className={cn('w-5 h-5 text-yellow-400', stats.generating > 0 && 'animate-spin')}
            />
            {stats.generating}
          </div>
        </div>
        <div className="card p-4">
          <div className="text-sm text-surface-400 mb-1">{t('generation.review', 'Review')}</div>
          <div className="text-2xl font-bold flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-brand-400" />
            {stats.review}
          </div>
        </div>
        <div className="card p-4">
          <div className="text-sm text-surface-400 mb-1">{t('generation.approved', 'Approved')}</div>
          <div className="text-2xl font-bold flex items-center gap-2">
            <CheckCircle className="w-5 h-5 text-green-400" />
            {stats.approved}
          </div>
        </div>
        <div className="card p-4">
          <div className="text-sm text-surface-400 mb-1">{t('generation.failed', 'Failed')}</div>
          <div className="text-2xl font-bold flex items-center gap-2">
            <XCircle className="w-5 h-5 text-red-400" />
            {stats.failed}
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="card p-4 mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-surface-400">{t('generation.overallProgress', 'Overall Progress')}</span>
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
            {t('generation.processing', 'Processing...')} {queueStatus?.running || 0}{' '}
            {t('generation.jobsRunning', 'job(s) running')}
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
            <span className="font-medium">{t('generation.generationSettings', 'Generation Settings')}</span>
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
                <label className="block text-sm text-surface-400 mb-2">{t('generation.videoProvider', 'Video Provider')}</label>
                <select
                  value={selectedProvider || ''}
                  onChange={(e) => {
                    setProvider(e.target.value);
                    setModel(null);
                  }}
                  className="w-full px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg text-sm focus:outline-none focus:border-brand-500"
                >
                  <option value="">{t('generation.selectProvider', 'Select provider...')}</option>
                  {useGenerationStore.getState().providersHealth.length > 0 ? (
                    useGenerationStore.getState().providersHealth.map((p) => (
                      <option key={p.provider} value={p.provider}>
                        {p.name} {p.available ? '✓' : t('generation.unavailable', '(unavailable)')}
                      </option>
                    ))
                  ) : (
                    <>
                      <option value="local">{t('generation.mockTesting', 'Mock (Testing)')}</option>
                      <option value="replicate">Replicate</option>
                      <option value="fal">Fal.ai</option>
                      <option value="comfyui">{t('generation.comfyuiLocal', 'ComfyUI (Local)')}</option>
                      <option value="runpod">RunPod</option>
                      <option value="actcore">ActCore</option>
                    </>
                  )}
                </select>
              </div>

              {/* Model Selection */}
              {selectedProvider && (
                <div>
                  <label className="block text-sm text-surface-400 mb-2">{t('generation.model', 'Model')}</label>
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
                  totalDurationSeconds={allShots
                    .filter((s) => s.state === 'planned' || s.state === 'queued')
                    .reduce((sum, s) => sum + (s.durationSeconds || 5), 0)}
                />
              </div>
            )}

            {/* IP-Adapter Character Consistency Controls */}
            <div className="mt-4 pt-4 border-t border-surface-700">
              <IPAdapterControls />
            </div>
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
                {t(
                  `generation.filter${filterType.charAt(0).toUpperCase() + filterType.slice(1)}`,
                  filterType.charAt(0).toUpperCase() + filterType.slice(1)
                )}
                {filterType !== 'all' && (
                  <span className="ml-1 text-surface-500">
                    ({stats[filterType as keyof typeof stats]})
                  </span>
                )}
              </button>
            )
          )}
        </div>

        {/* View and Compare Controls */}
        <div className="flex items-center gap-2">
          {/* Compare Mode Toggle */}
          {stats.review > 0 && (
            <button
              onClick={toggleCompareMode}
              className={cn(
                'px-3 py-1.5 rounded-lg text-sm transition-colors flex items-center gap-2',
                compareMode
                  ? 'bg-brand-500/20 text-brand-400'
                  : 'bg-surface-800 text-surface-400 hover:bg-surface-700'
              )}
            >
              <GitCompare className="w-4 h-4" />
              {compareMode
                ? t('generation.cancelCompare', 'Cancel Compare')
                : t('generation.compare', 'Compare')}
            </button>
          )}

          {/* Compare Selected Button */}
          {compareMode && selectedForCompare.size >= 2 && (
            <button
              onClick={handleCompare}
              className="px-3 py-1.5 bg-brand-500 hover:bg-brand-600 text-white rounded-lg text-sm transition-colors"
            >
              {t('generation.compareSelected', 'Compare Selected')} ({selectedForCompare.size})
            </button>
          )}

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
            const isSelected = selectedForCompare.has(shot.id);
            const canSelect =
              shot.outputVideoPath && (shot.state === 'generated' || shot.state === 'approved');

            return (
              <div key={shot.id} className="relative">
                {/* Compare Mode Checkbox */}
                {compareMode && canSelect && (
                  <div className="absolute top-2 right-2 z-20">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => toggleShotSelection(shot.id)}
                      className="w-5 h-5 rounded border-2 border-white bg-black/50 checked:bg-brand-500 checked:border-brand-500 cursor-pointer"
                      aria-label={`${t('generation.select', 'Select')} ${shot.shotNumber} ${t('generation.forComparison', 'for comparison')}`}
                    />
                  </div>
                )}

                <ShotPreview
                  shot={shot}
                  latestJob={latestJob}
                  onApprove={handleApprove}
                  onReject={handleReject}
                  onRegenerate={handleRegenerate}
                  disabled={
                    compareMode ||
                    approveShotMutation.isPending ||
                    rejectShotMutation.isPending ||
                    regenerateShotMutation.isPending
                  }
                />

                {/* Quality Radar Chart for completed/approved shots */}
                {(shot.state === 'generated' || shot.state === 'approved') && latestJob?.id && (
                  <div className="mt-2">
                    <QualityRadarChart review={null} compact={viewMode === 'grid'} />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        <div className="text-center py-16">
          <Play className="w-16 h-16 mx-auto text-surface-600 mb-4" />
          <h3 className="text-lg font-medium mb-2">{t('generation.noShotsFound', 'No Shots Found')}</h3>
          <p className="text-surface-400">
            {filter !== 'all'
              ? t('generation.noShotsMatchTheCurrentFilter', 'No shots match the current filter.')
              : t('generation.shotsWillAppearHereOnceScenesArePlanned', 'Shots will appear here once scenes are planned.')}
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
            {t('generation.continueToExport', 'Continue to Export')}
          </button>
        </div>
      )}

      {/* Comparison View Modal */}
      {showComparison && selectedForCompare.size >= 2 && (
        <ComparisonView
          videos={Array.from(selectedForCompare)
            .map((shotId) => {
              const shot = allShots.find((s) => s.id === shotId);
              if (!shot || !shot.outputVideoPath) return null;
              return {
                id: shot.id,
                src: shot.outputVideoPath,
                label: `${t('generation.shot', 'Shot')} ${shot.shotNumber}`,
                poster: shot.outputThumbnailPath,
              };
            })
            .filter((v): v is NonNullable<typeof v> => v !== null)}
          onClose={() => setShowComparison(false)}
          onSelectBest={handleSelectBest}
        />
      )}
    </div>
  );
}
