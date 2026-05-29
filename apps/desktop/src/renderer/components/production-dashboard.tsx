/**
 * Production Dashboard - Full pipeline status and control.
 *
 * Shows real-time progress for screenplay-to-movie generation,
 * including stage progression, shot status, cost tracking, and controls.
 */

import { useState, useEffect, useMemo, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Play,
  Pause,
  Square,
  Film,
  FileText,
  Users,
  Video,
  Mic,
  CheckCircle2,
  Clock,
  AlertCircle,
  DollarSign,
  Layers,
  BarChart3,
  RefreshCw,
  ChevronRight,
  Loader2,
  Download,
  Eye,
} from 'lucide-react';
import { cn } from '../lib/utils';
import { useTranslation } from '../i18n/use-translation';

// Pipeline stages matching backend
type PipelineStage =
  | 'initialized'
  | 'parsing'
  | 'shot_breakdown'
  | 'character_prep'
  | 'blocker_check'
  | 'video_generation'
  | 'quality_review'
  | 'audio_generation'
  | 'lip_sync'
  | 'assembly'
  | 'completed'
  | 'failed'
  | 'paused';

// Shot status
type ShotStatus = 'queued' | 'generating' | 'reviewing' | 'completed' | 'failed';

interface ShotProgress {
  shotId: string;
  sceneId: string;
  status: ShotStatus;
  qualityScore: number;
  regenerationCount: number;
  videoPath?: string;
  error?: string;
}

interface PipelineStatus {
  projectId: string;
  stage: PipelineStage;
  percent: number;
  message: string;
  shotsCompleted: number;
  shotsTotal: number;
  totalCost: number;
  budgetRemaining: number;
  estimatedTimeRemaining?: number;
  shots: ShotProgress[];
  error?: string;
}

interface ProductionDashboardProps {
  projectId: string;
  onPreviewClick?: (shotId: string) => void;
  onDownloadClick?: () => void;
  className?: string;
}

// Stage configuration
const STAGES: {
  id: PipelineStage;
  labelKey: string;
  label: string;
  icon: typeof Film;
  descriptionKey: string;
  description: string;
}[] = [
  { id: 'parsing', labelKey: 'prodDash.stageParseLabel', label: 'Parse', icon: FileText, descriptionKey: 'prodDash.stageParseDesc', description: 'Analyzing screenplay' },
  { id: 'shot_breakdown', labelKey: 'prodDash.stageBreakdownLabel', label: 'Breakdown', icon: Layers, descriptionKey: 'prodDash.stageBreakdownDesc', description: 'Generating shot list' },
  { id: 'character_prep', labelKey: 'prodDash.stageCharactersLabel', label: 'Characters', icon: Users, descriptionKey: 'prodDash.stageCharactersDesc', description: 'Preparing references' },
  { id: 'video_generation', labelKey: 'prodDash.stageVideoLabel', label: 'Video', icon: Video, descriptionKey: 'prodDash.stageVideoDesc', description: 'Generating clips' },
  { id: 'audio_generation', labelKey: 'prodDash.stageAudioLabel', label: 'Audio', icon: Mic, descriptionKey: 'prodDash.stageAudioDesc', description: 'Generating dialogue' },
  { id: 'assembly', labelKey: 'prodDash.stageAssemblyLabel', label: 'Assembly', icon: Film, descriptionKey: 'prodDash.stageAssemblyDesc', description: 'Combining clips' },
];

// Get stage index for progress bar
function getStageIndex(stage: PipelineStage): number {
  if (stage === 'initialized') return -1;
  if (stage === 'completed') return STAGES.length;
  if (stage === 'failed' || stage === 'paused') return -1;

  const stages: PipelineStage[] = [
    'parsing',
    'shot_breakdown',
    'character_prep',
    'blocker_check',
    'video_generation',
    'quality_review',
    'audio_generation',
    'lip_sync',
    'assembly',
  ];

  return stages.indexOf(stage);
}

// Stage progress indicator
function StageProgress({
  stages,
  currentStage,
}: {
  stages: typeof STAGES;
  currentStage: PipelineStage;
}) {
  const { t } = useTranslation();
  const currentIndex = useMemo(() => {
    if (currentStage === 'completed') return stages.length;
    return stages.findIndex((s) => s.id === currentStage);
  }, [stages, currentStage]);

  return (
    <div className="flex items-center gap-1 p-3 bg-surface-800 rounded-lg overflow-x-auto">
      {stages.map((stage, index) => {
        const Icon = stage.icon;
        const isCompleted = index < currentIndex;
        const isCurrent = index === currentIndex;
        const isPending = index > currentIndex;

        return (
          <div key={stage.id} className="flex items-center">
            <div
              className={cn(
                'flex items-center gap-2 px-3 py-2 rounded-lg transition-all',
                isCompleted && 'bg-green-500/20',
                isCurrent && 'bg-brand-500/20 ring-1 ring-brand-500/50',
                isPending && 'opacity-40'
              )}
            >
              <div
                className={cn(
                  'w-8 h-8 rounded-full flex items-center justify-center',
                  isCompleted && 'bg-green-500 text-white',
                  isCurrent && 'bg-brand-500 text-white',
                  isPending && 'bg-surface-700 text-surface-400'
                )}
              >
                {isCompleted ? (
                  <CheckCircle2 className="w-4 h-4" />
                ) : isCurrent ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Icon className="w-4 h-4" />
                )}
              </div>
              <div className="hidden sm:block">
                <p
                  className={cn(
                    'text-xs font-medium',
                    isCompleted
                      ? 'text-green-400'
                      : isCurrent
                        ? 'text-brand-400'
                        : 'text-surface-400'
                  )}
                >
                  {t(stage.labelKey, stage.label)}
                </p>
                {isCurrent && (
                  <p className="text-[10px] text-surface-400">
                    {t(stage.descriptionKey, stage.description)}
                  </p>
                )}
              </div>
            </div>
            {index < stages.length - 1 && (
              <ChevronRight
                className={cn(
                  'w-4 h-4 mx-1 flex-shrink-0',
                  isCompleted ? 'text-green-400' : 'text-surface-600'
                )}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

// Shot grid showing generation progress
function ShotGrid({
  shots,
  onPreviewClick,
}: {
  shots: ShotProgress[];
  onPreviewClick?: (shotId: string) => void;
}) {
  const { t } = useTranslation();
  const statusColors: Record<ShotStatus, string> = {
    queued: 'bg-surface-700',
    generating: 'bg-brand-500 animate-pulse',
    reviewing: 'bg-yellow-500',
    completed: 'bg-green-500',
    failed: 'bg-red-500',
  };

  return (
    <div className="grid grid-cols-8 sm:grid-cols-12 lg:grid-cols-16 gap-1 p-3">
      {shots.map((shot) => (
        <button
          key={shot.shotId}
          onClick={() => shot.videoPath && onPreviewClick?.(shot.shotId)}
          disabled={!shot.videoPath}
          className={cn(
            'aspect-video rounded transition-all relative group',
            statusColors[shot.status],
            shot.videoPath && 'hover:ring-2 hover:ring-brand-400 cursor-pointer'
          )}
          title={`${t('prodDash.shotTitlePrefix', 'Shot')} ${shot.shotId} - ${shot.status}`}
        >
          {shot.status === 'completed' && (
            <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-black/50 rounded">
              <Eye className="w-3 h-3 text-white" />
            </div>
          )}
          {shot.regenerationCount > 0 && (
            <span className="absolute -top-1 -right-1 w-3 h-3 bg-yellow-500 rounded-full text-[8px] flex items-center justify-center text-black font-bold">
              {shot.regenerationCount}
            </span>
          )}
        </button>
      ))}
    </div>
  );
}

// Stats card
function StatCard({
  icon: Icon,
  label,
  value,
  subValue,
  color = 'brand',
}: {
  icon: typeof Film;
  label: string;
  value: string | number;
  subValue?: string;
  color?: 'brand' | 'green' | 'yellow' | 'red';
}) {
  const colorClasses = {
    brand: 'text-brand-400 bg-brand-500/10',
    green: 'text-green-400 bg-green-500/10',
    yellow: 'text-yellow-400 bg-yellow-500/10',
    red: 'text-red-400 bg-red-500/10',
  };

  return (
    <div className="bg-surface-800 rounded-lg p-3">
      <div className="flex items-center gap-2 mb-2">
        <div className={cn('p-1.5 rounded', colorClasses[color])}>
          <Icon className="w-4 h-4" />
        </div>
        <span className="text-xs text-surface-400">{label}</span>
      </div>
      <p className="text-xl font-bold text-white">{value}</p>
      {subValue && <p className="text-xs text-surface-400 mt-0.5">{subValue}</p>}
    </div>
  );
}

export function ProductionDashboard({
  projectId,
  onPreviewClick,
  onDownloadClick,
  className,
}: ProductionDashboardProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [isRunning, setIsRunning] = useState(false);

  // Fetch pipeline status with polling
  const { data: status, isLoading } = useQuery({
    queryKey: ['pipeline-status', projectId],
    queryFn: async () => {
      const result = await window.electronAPI.backendRequest<PipelineStatus>('pipeline.status', {
        project_id: projectId,
      });
      return result;
    },
    enabled: !!projectId,
    refetchInterval: isRunning ? 2000 : false, // Poll when running
  });

  // Start pipeline mutation
  const startMutation = useMutation({
    mutationFn: async () => {
      return await window.electronAPI.backendRequest('pipeline.start', {
        project_id: projectId,
        mode: 'full_auto',
      });
    },
    onSuccess: () => {
      setIsRunning(true);
      queryClient.invalidateQueries({ queryKey: ['pipeline-status', projectId] });
    },
  });

  // Pause pipeline mutation
  const pauseMutation = useMutation({
    mutationFn: async () => {
      return await window.electronAPI.backendRequest('pipeline.pause', { project_id: projectId });
    },
    onSuccess: () => {
      setIsRunning(false);
      queryClient.invalidateQueries({ queryKey: ['pipeline-status', projectId] });
    },
  });

  // Update running state based on status
  useEffect(() => {
    if (status) {
      const activeStages: PipelineStage[] = [
        'parsing',
        'shot_breakdown',
        'character_prep',
        'blocker_check',
        'video_generation',
        'quality_review',
        'audio_generation',
        'lip_sync',
        'assembly',
      ];
      setIsRunning(activeStages.includes(status.stage));
    }
  }, [status]);

  // Calculate stats
  const stats = useMemo(() => {
    if (!status) return null;

    // status.shots can be absent (partial/empty backend payload) — guard so the
    // dashboard renders an empty state instead of crashing the tab.
    const shots = status.shots ?? [];
    const completedShots = shots.filter((s) => s.status === 'completed').length;
    const failedShots = shots.filter((s) => s.status === 'failed').length;
    const avgQuality = shots
      .filter((s) => s.qualityScore > 0)
      .reduce((sum, s, _, arr) => sum + s.qualityScore / arr.length, 0);

    return {
      completedShots,
      failedShots,
      totalShots: status.shotsTotal ?? 0,
      avgQuality,
      cost: status.totalCost ?? 0,
      budgetRemaining: status.budgetRemaining ?? 0,
    };
  }, [status]);

  if (isLoading) {
    return (
      <div className={cn('flex items-center justify-center p-12', className)}>
        <Loader2 className="w-8 h-8 animate-spin text-brand-400" />
      </div>
    );
  }

  return (
    <div className={cn('flex flex-col h-full', className)}>
      {/* Header with controls */}
      <div className="flex items-center justify-between p-4 border-b border-surface-700">
        <div className="flex items-center gap-3">
          <Film className="w-6 h-6 text-brand-400" />
          <div>
            <h2 className="font-semibold text-white">
              {t('prodDash.headerTitle', 'Production Pipeline')}
            </h2>
            <p className="text-xs text-surface-400">
              {status?.message || t('prodDash.readyToStart', 'Ready to start')}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {status?.stage === 'completed' ? (
            <button
              onClick={onDownloadClick}
              className="flex items-center gap-2 px-4 py-2 bg-green-500 hover:bg-green-600 text-white rounded-lg transition-colors"
            >
              <Download className="w-4 h-4" />
              {t('prodDash.downloadMovie', 'Download Movie')}
            </button>
          ) : isRunning ? (
            <button
              onClick={() => pauseMutation.mutate()}
              disabled={pauseMutation.isPending}
              className="flex items-center gap-2 px-4 py-2 bg-yellow-500 hover:bg-yellow-600 text-black rounded-lg transition-colors"
            >
              {pauseMutation.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Pause className="w-4 h-4" />
              )}
              {t('prodDash.pause', 'Pause')}
            </button>
          ) : (
            <button
              onClick={() => startMutation.mutate()}
              disabled={startMutation.isPending}
              className="flex items-center gap-2 px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white rounded-lg transition-colors"
            >
              {startMutation.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Play className="w-4 h-4" />
              )}
              {status?.stage === 'paused'
                ? t('prodDash.resume', 'Resume')
                : t('prodDash.generateMovie', 'Generate Movie')}
            </button>
          )}

          <button
            onClick={() =>
              queryClient.invalidateQueries({ queryKey: ['pipeline-status', projectId] })
            }
            className="p-2 hover:bg-surface-700 rounded-lg transition-colors"
            title={t('prodDash.refresh', 'Refresh')}
          >
            <RefreshCw className="w-4 h-4 text-surface-400" />
          </button>
        </div>
      </div>

      {/* Stage progress */}
      <div className="p-4 border-b border-surface-700">
        <StageProgress stages={STAGES} currentStage={status?.stage || 'initialized'} />
      </div>

      {/* Stats grid */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 p-4 border-b border-surface-700">
          <StatCard
            icon={Video}
            label={t('prodDash.statShots', 'Shots')}
            value={`${stats.completedShots}/${stats.totalShots}`}
            subValue={`${Math.round((stats.completedShots / Math.max(1, stats.totalShots)) * 100)}% ${t('prodDash.complete', 'complete')}`}
            color="brand"
          />
          <StatCard
            icon={BarChart3}
            label={t('prodDash.statAvgQuality', 'Avg Quality')}
            value={`${Math.round(stats.avgQuality * 100)}%`}
            subValue={t('prodDash.qualityThreshold', '0.7 threshold')}
            color={stats.avgQuality >= 0.7 ? 'green' : 'yellow'}
          />
          <StatCard
            icon={DollarSign}
            label={t('prodDash.statCost', 'Cost')}
            value={`$${stats.cost.toFixed(2)}`}
            subValue={`$${stats.budgetRemaining.toFixed(2)} ${t('prodDash.remaining', 'remaining')}`}
            color={stats.budgetRemaining > 0 ? 'green' : 'red'}
          />
          <StatCard
            icon={Clock}
            label={t('prodDash.statTime', 'Time')}
            value={
              status?.estimatedTimeRemaining
                ? `${Math.ceil(status.estimatedTimeRemaining / 60)}m`
                : '--'
            }
            subValue={t('prodDash.remaining', 'remaining')}
            color="brand"
          />
        </div>
      )}

      {/* Shot grid */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-4">
          <h3 className="text-sm font-medium text-surface-300 mb-3">
            {t('prodDash.shotProgress', 'Shot Progress')}
          </h3>
          {status?.shots && status.shots.length > 0 ? (
            <ShotGrid shots={status.shots} onPreviewClick={onPreviewClick} />
          ) : (
            <div className="text-center py-8 text-surface-400">
              <Layers className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>{t('prodDash.noShots', 'No shots yet. Start the pipeline to generate.')}</p>
            </div>
          )}
        </div>
      </div>

      {/* Error display */}
      {status?.stage === 'failed' && status.error && (
        <div className="p-4 bg-red-500/10 border-t border-red-500/30">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
            <div>
              <h4 className="font-medium text-red-400">
                {t('prodDash.pipelineFailed', 'Pipeline Failed')}
              </h4>
              <p className="text-sm text-red-300 mt-1">{status.error}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default ProductionDashboard;
