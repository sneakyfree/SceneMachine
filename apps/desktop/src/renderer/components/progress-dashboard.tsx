/**
 * Visual Progress Dashboard Component
 *
 * A user-friendly progress view for movie creation.
 * Shows overall progress, current activity, and completed items.
 */

import { useState, useEffect } from 'react';
import {
  Check,
  Clock,
  Play,
  Pause,
  Loader2,
  AlertCircle,
  Film,
  Users,
  Clapperboard,
  Video,
  Sparkles,
  ChevronDown,
  ChevronUp,
  Eye,
  RotateCcw,
} from 'lucide-react';
import { cn } from '../lib/utils';
import { useExperienceMode } from '../stores/experience-store';

// Progress stage definition
interface ProgressStage {
  id: string;
  label: string;
  friendlyLabel: string;
  icon: typeof Film;
  status: 'pending' | 'active' | 'completed' | 'error';
  progress?: number;
  details?: string;
  friendlyDetails?: string;
  items?: {
    id: string;
    label: string;
    status: 'pending' | 'active' | 'completed' | 'error';
    thumbnail?: string;
  }[];
}

interface ProgressDashboardProps {
  projectName: string;
  stages: ProgressStage[];
  currentStageIndex: number;
  overallProgress: number;
  estimatedTimeRemaining?: string;
  isPaused?: boolean;
  onPause?: () => void;
  onResume?: () => void;
  onPreviewItem?: (stageId: string, itemId: string) => void;
  onRetryItem?: (stageId: string, itemId: string) => void;
}

// Individual stage row
function StageRow({
  stage,
  isExpanded,
  onToggle,
  onPreview,
  onRetry,
  isSimplified,
}: {
  stage: ProgressStage;
  isExpanded: boolean;
  onToggle: () => void;
  onPreview?: (itemId: string) => void;
  onRetry?: (itemId: string) => void;
  isSimplified: boolean;
}) {
  const Icon = stage.icon;

  const statusStyles = {
    pending: 'text-surface-500 bg-surface-800',
    active: 'text-brand-400 bg-brand-500/20',
    completed: 'text-green-400 bg-green-500/20',
    error: 'text-red-400 bg-red-500/20',
  };

  const statusIcons = {
    pending: <Clock className="w-4 h-4" />,
    active: <Loader2 className="w-4 h-4 animate-spin" />,
    completed: <Check className="w-4 h-4" />,
    error: <AlertCircle className="w-4 h-4" />,
  };

  const hasItems = stage.items && stage.items.length > 0;
  const completedItems = stage.items?.filter((i) => i.status === 'completed').length || 0;
  const totalItems = stage.items?.length || 0;

  return (
    <div className="border border-surface-800 rounded-xl overflow-hidden">
      {/* Stage header */}
      <button
        onClick={onToggle}
        disabled={!hasItems}
        className={cn(
          'w-full flex items-center gap-4 p-4 transition-colors',
          hasItems ? 'hover:bg-surface-800/50 cursor-pointer' : 'cursor-default',
          stage.status === 'active' && 'bg-surface-800/30'
        )}
      >
        {/* Icon */}
        <div
          className={cn(
            'w-10 h-10 rounded-lg flex items-center justify-center',
            statusStyles[stage.status]
          )}
        >
          <Icon className="w-5 h-5" />
        </div>

        {/* Label and details */}
        <div className="flex-1 text-left">
          <p className="font-medium">{isSimplified ? stage.friendlyLabel : stage.label}</p>
          {stage.details && (
            <p className="text-sm text-surface-400">
              {isSimplified ? stage.friendlyDetails || stage.details : stage.details}
            </p>
          )}
        </div>

        {/* Progress or status */}
        <div className="flex items-center gap-3">
          {hasItems && (
            <span className="text-sm text-surface-400">
              {completedItems}/{totalItems}
            </span>
          )}

          {stage.progress !== undefined && stage.status === 'active' && (
            <div className="w-24 h-2 bg-surface-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-brand-500 rounded-full transition-all"
                style={{ width: `${stage.progress}%` }}
              />
            </div>
          )}

          <div
            className={cn(
              'w-8 h-8 rounded-full flex items-center justify-center',
              statusStyles[stage.status]
            )}
          >
            {statusIcons[stage.status]}
          </div>

          {hasItems &&
            (isExpanded ? (
              <ChevronUp className="w-4 h-4 text-surface-500" />
            ) : (
              <ChevronDown className="w-4 h-4 text-surface-500" />
            ))}
        </div>
      </button>

      {/* Expanded items */}
      {isExpanded && hasItems && (
        <div className="border-t border-surface-800 p-4 bg-surface-800/20">
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
            {stage.items!.map((item) => (
              <div
                key={item.id}
                className={cn(
                  'relative aspect-video rounded-lg overflow-hidden border',
                  item.status === 'completed'
                    ? 'border-green-500/30'
                    : item.status === 'active'
                      ? 'border-brand-500'
                      : item.status === 'error'
                        ? 'border-red-500/30'
                        : 'border-surface-700'
                )}
              >
                {/* Thumbnail or placeholder */}
                {item.thumbnail ? (
                  <img
                    src={item.thumbnail}
                    alt={item.label}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div
                    className={cn(
                      'w-full h-full flex items-center justify-center',
                      item.status === 'active' ? 'bg-brand-500/10' : 'bg-surface-800'
                    )}
                  >
                    {item.status === 'active' ? (
                      <Loader2 className="w-6 h-6 text-brand-400 animate-spin" />
                    ) : item.status === 'error' ? (
                      <AlertCircle className="w-6 h-6 text-red-400" />
                    ) : item.status === 'completed' ? (
                      <Check className="w-6 h-6 text-green-400" />
                    ) : (
                      <Clock className="w-6 h-6 text-surface-500" />
                    )}
                  </div>
                )}

                {/* Overlay for completed items */}
                {item.status === 'completed' && (
                  <div className="absolute inset-0 bg-black/40 flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity">
                    <button
                      onClick={() => onPreview?.(item.id)}
                      className="p-2 bg-white/20 rounded-full hover:bg-white/30"
                    >
                      <Eye className="w-4 h-4 text-white" />
                    </button>
                  </div>
                )}

                {/* Retry button for errors */}
                {item.status === 'error' && (
                  <button
                    onClick={() => onRetry?.(item.id)}
                    className="absolute bottom-1 right-1 p-1 bg-red-500 rounded hover:bg-red-600"
                  >
                    <RotateCcw className="w-3 h-3 text-white" />
                  </button>
                )}

                {/* Label */}
                <div className="absolute bottom-0 left-0 right-0 px-2 py-1 bg-gradient-to-t from-black/80 to-transparent">
                  <p className="text-xs text-white truncate">{item.label}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export function ProgressDashboard({
  projectName,
  stages,
  currentStageIndex,
  overallProgress,
  estimatedTimeRemaining,
  isPaused = false,
  onPause,
  onResume,
  onPreviewItem,
  onRetryItem,
}: ProgressDashboardProps) {
  const [expandedStages, setExpandedStages] = useState<Set<string>>(new Set());
  const { isStory } = useExperienceMode();

  // Auto-expand active stage
  useEffect(() => {
    const activeStage = stages.find((s) => s.status === 'active');
    if (activeStage) {
      setExpandedStages((prev) => new Set([...prev, activeStage.id]));
    }
  }, [stages]);

  const toggleStage = (stageId: string) => {
    setExpandedStages((prev) => {
      const next = new Set(prev);
      if (next.has(stageId)) {
        next.delete(stageId);
      } else {
        next.add(stageId);
      }
      return next;
    });
  };

  const completedStages = stages.filter((s) => s.status === 'completed').length;
  const currentStage = stages[currentStageIndex];

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 bg-brand-500/20 rounded-xl flex items-center justify-center">
            <Film className="w-6 h-6 text-brand-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold">
              {isStory ? `Creating "${projectName}"` : `Project: ${projectName}`}
            </h1>
            <p className="text-sm text-surface-400">
              {isStory
                ? currentStage?.friendlyLabel || 'Preparing...'
                : `Stage ${currentStageIndex + 1} of ${stages.length}: ${currentStage?.label}`}
            </p>
          </div>
        </div>

        {/* Pause/Resume button */}
        {(onPause || onResume) && (
          <button
            onClick={isPaused ? onResume : onPause}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-lg transition-colors',
              isPaused
                ? 'bg-green-500 hover:bg-green-600 text-white'
                : 'bg-surface-800 hover:bg-surface-700'
            )}
          >
            {isPaused ? (
              <>
                <Play className="w-4 h-4" />
                Resume
              </>
            ) : (
              <>
                <Pause className="w-4 h-4" />
                Pause
              </>
            )}
          </button>
        )}
      </div>

      {/* Overall progress bar */}
      <div className="bg-surface-900 rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <p className="text-3xl font-bold text-brand-400">{overallProgress}%</p>
            <p className="text-sm text-surface-400">
              {isStory ? 'Your movie is' : 'Overall progress'}
              {overallProgress < 100 ? ' being created' : ' ready!'}
            </p>
          </div>
          {estimatedTimeRemaining && overallProgress < 100 && (
            <div className="text-right">
              <p className="text-sm text-surface-400">
                {isStory ? 'About' : 'Estimated time remaining'}
              </p>
              <p className="text-lg font-medium">{estimatedTimeRemaining}</p>
            </div>
          )}
        </div>

        <div className="h-4 bg-surface-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-brand-500 via-purple-500 to-green-500 rounded-full transition-all duration-500"
            style={{ width: `${overallProgress}%` }}
          />
        </div>

        {/* Stage dots */}
        <div className="flex items-center justify-between mt-4 px-2">
          {stages.map((stage, index) => (
            <div key={stage.id} className="flex flex-col items-center gap-1">
              <div
                className={cn(
                  'w-3 h-3 rounded-full transition-colors',
                  stage.status === 'completed'
                    ? 'bg-green-500'
                    : stage.status === 'active'
                      ? 'bg-brand-500 animate-pulse'
                      : stage.status === 'error'
                        ? 'bg-red-500'
                        : 'bg-surface-700'
                )}
              />
              <span className="text-xs text-surface-500 hidden sm:block">
                {isStory ? stage.friendlyLabel.split(' ')[0] : stage.label.split(' ')[0]}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Current activity highlight */}
      {currentStage && currentStage.status === 'active' && (
        <div className="flex items-center gap-4 p-4 bg-brand-500/10 border border-brand-500/30 rounded-xl">
          <Loader2 className="w-6 h-6 text-brand-400 animate-spin" />
          <div className="flex-1">
            <p className="font-medium">
              {isStory ? currentStage.friendlyLabel : currentStage.label}
            </p>
            <p className="text-sm text-surface-400">
              {isStory ? currentStage.friendlyDetails || 'Working on it...' : currentStage.details}
            </p>
          </div>
          {currentStage.progress !== undefined && (
            <span className="text-lg font-bold text-brand-400">{currentStage.progress}%</span>
          )}
        </div>
      )}

      {/* Tip for Story mode users */}
      {isStory && overallProgress > 0 && overallProgress < 100 && (
        <div className="flex items-start gap-3 p-4 bg-surface-800/50 rounded-lg">
          <Sparkles className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-medium text-sm">
              {isStory ? 'Tip: You can preview completed shots' : 'Preview available'}
            </p>
            <p className="text-sm text-surface-400">
              Click on any completed shot below to watch it while the rest are being created.
            </p>
          </div>
        </div>
      )}

      {/* Stage list */}
      <div className="space-y-3">
        {stages.map((stage) => (
          <StageRow
            key={stage.id}
            stage={stage}
            isExpanded={expandedStages.has(stage.id)}
            onToggle={() => toggleStage(stage.id)}
            onPreview={(itemId) => onPreviewItem?.(stage.id, itemId)}
            onRetry={(itemId) => onRetryItem?.(stage.id, itemId)}
            isSimplified={isStory}
          />
        ))}
      </div>

      {/* Completion celebration */}
      {overallProgress === 100 && (
        <div className="text-center p-8 bg-gradient-to-br from-brand-500/20 to-purple-500/20 rounded-xl border border-brand-500/30">
          <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <Check className="w-8 h-8 text-green-400" />
          </div>
          <h2 className="text-2xl font-bold mb-2">
            {isStory ? 'Your movie is ready!' : 'Generation Complete'}
          </h2>
          <p className="text-surface-400 mb-6">
            {isStory
              ? 'All your scenes have been created. Time to export and share your masterpiece!'
              : 'All stages completed successfully.'}
          </p>
          <button className="px-6 py-3 bg-brand-500 hover:bg-brand-600 rounded-lg font-medium">
            {isStory ? 'Export My Movie' : 'Continue to Export'}
          </button>
        </div>
      )}
    </div>
  );
}

// Demo data generator for testing
export function createDemoProgressData(): {
  stages: ProgressStage[];
  currentStageIndex: number;
  overallProgress: number;
} {
  return {
    stages: [
      {
        id: 'upload',
        label: 'Screenplay Parsed',
        friendlyLabel: 'Read your script',
        icon: Film,
        status: 'completed',
        details: 'Found 24 scenes, 8 characters',
        friendlyDetails: 'Found 24 scenes and 8 characters',
      },
      {
        id: 'characters',
        label: 'Characters Defined',
        friendlyLabel: 'Described your characters',
        icon: Users,
        status: 'completed',
        details: '8/8 characters with descriptions',
        friendlyDetails: 'All 8 characters are ready',
      },
      {
        id: 'scenes',
        label: 'Shot Breakdown',
        friendlyLabel: 'Planned camera shots',
        icon: Clapperboard,
        status: 'completed',
        details: '142 shots planned across 24 scenes',
        friendlyDetails: 'Created 142 camera shots for your scenes',
      },
      {
        id: 'generate',
        label: 'Video Generation',
        friendlyLabel: 'Creating your movie',
        icon: Video,
        status: 'active',
        progress: 65,
        details: 'Generating shot 92 of 142',
        friendlyDetails: 'Making video clip 92 of 142',
        items: Array.from({ length: 12 }, (_, i) => ({
          id: `shot-${i}`,
          label: `Scene ${Math.floor(i / 3) + 1}, Shot ${(i % 3) + 1}`,
          status:
            i < 8
              ? ('completed' as const)
              : i === 8
                ? ('active' as const)
                : i === 9
                  ? ('error' as const)
                  : ('pending' as const),
        })),
      },
      {
        id: 'export',
        label: 'Assembly & Export',
        friendlyLabel: 'Putting it all together',
        icon: Sparkles,
        status: 'pending',
        details: 'Waiting for generation',
        friendlyDetails: 'Will combine all clips into your movie',
      },
    ],
    currentStageIndex: 3,
    overallProgress: 65,
  };
}
