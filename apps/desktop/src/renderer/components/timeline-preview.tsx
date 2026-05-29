/**
 * Timeline preview component for assembly/export.
 */

import { useMemo } from 'react';
import { Film, Play, Image, Clock } from 'lucide-react';
import { cn } from '../lib/utils';
import { useTranslation } from '../i18n/use-translation';

interface TimelineShot {
  shotId: string;
  shotNumber: string;
  duration: number;
  hasOutput: boolean;
  thumbnail?: string;
}

interface TimelineScene {
  sceneId: string;
  sceneNumber: string;
  title?: string;
  duration: number;
  shots: TimelineShot[];
}

interface TimelinePreviewProps {
  scenes: TimelineScene[];
  totalDuration: number;
  selectedSceneId?: string;
  selectedShotId?: string;
  onSceneClick?: (sceneId: string) => void;
  onShotClick?: (sceneId: string, shotId: string) => void;
  className?: string;
}

function formatDuration(seconds: number | undefined | null): string {
  // Guard NaN/undefined so timeline axis labels don't render "NaN:NaN" on
  // an empty project (caught by /qa_screenshot_tour iter 13).
  if (seconds === undefined || seconds === null || !Number.isFinite(seconds) || seconds < 0) {
    return '0:00';
  }
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

export function TimelinePreview({
  scenes,
  totalDuration,
  selectedSceneId,
  selectedShotId,
  onSceneClick,
  onShotClick,
  className,
}: TimelinePreviewProps) {
  const { t } = useTranslation();
  // Calculate progress. `scenes` and `scene.shots` may be undefined when
  // the backend returns partial state (new project, mid-load, etc.) —
  // guarding both prevents a render-time `.forEach` crash that took down
  // the entire Export page. Found by /qa_screenshot_tour.
  const stats = useMemo(() => {
    let totalShots = 0;
    let completedShots = 0;

    (scenes ?? []).forEach((scene) => {
      (scene.shots ?? []).forEach((shot) => {
        totalShots++;
        if (shot.hasOutput) completedShots++;
      });
    });

    return {
      totalShots,
      completedShots,
      progress: totalShots > 0 ? (completedShots / totalShots) * 100 : 0,
      isComplete: completedShots === totalShots && totalShots > 0,
    };
  }, [scenes]);

  // Calculate shot widths based on duration
  const getSceneWidth = (scene: TimelineScene) => {
    if (totalDuration <= 0) return '0%';
    return `${(scene.duration / totalDuration) * 100}%`;
  };

  return (
    <div className={cn('bg-surface-900 rounded-lg p-4', className)}>
      {/* Header with stats */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Film className="w-4 h-4 text-surface-400" />
            <span className="text-sm text-surface-400">
              {(scenes ?? []).length} {t('tlPreview.scenes', 'scenes')}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Image className="w-4 h-4 text-surface-400" />
            <span className="text-sm text-surface-400">
              {stats.completedShots}/{stats.totalShots} {t('tlPreview.shots', 'shots')}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-surface-400" />
            <span className="text-sm text-surface-400">{formatDuration(totalDuration)}</span>
          </div>
        </div>

        {/* Progress indicator */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-surface-400">
            {stats.progress.toFixed(0)}% {t('tlPreview.ready', 'ready')}
          </span>
          {stats.isComplete && (
            <span className="px-2 py-0.5 bg-green-500/20 text-green-400 text-xs rounded">
              {t('tlPreview.readyToExport', 'Ready to export')}
            </span>
          )}
        </div>
      </div>

      {/* Progress bar */}
      <div className="w-full h-2 bg-surface-800 rounded-full overflow-hidden mb-4">
        <div
          className={cn(
            'h-full transition-all duration-300',
            stats.isComplete ? 'bg-green-500' : 'bg-brand-500'
          )}
          style={{ width: `${stats.progress}%` }}
        />
      </div>

      {/* Timeline visualization */}
      <div className="relative">
        {/* Time markers */}
        <div className="flex justify-between text-xs text-surface-500 mb-2">
          <span>0:00</span>
          <span>{formatDuration(totalDuration / 4)}</span>
          <span>{formatDuration(totalDuration / 2)}</span>
          <span>{formatDuration((totalDuration * 3) / 4)}</span>
          <span>{formatDuration(totalDuration)}</span>
        </div>

        {/* Scene blocks */}
        <div className="flex gap-1 h-24">
          {(scenes ?? []).map((scene) => (
            <div
              key={scene.sceneId}
              className={cn(
                'relative rounded overflow-hidden cursor-pointer transition-all',
                'border-2',
                selectedSceneId === scene.sceneId
                  ? 'border-brand-500'
                  : 'border-transparent hover:border-surface-600'
              )}
              style={{ width: getSceneWidth(scene), minWidth: '40px' }}
              onClick={() => onSceneClick?.(scene.sceneId)}
            >
              {/* Scene background */}
              <div className="absolute inset-0 bg-surface-800" />

              {/* Shot blocks within scene */}
              <div className="absolute inset-0 flex">
                {scene.shots.map((shot, idx) => {
                  const shotWidth =
                    scene.duration > 0 ? `${(shot.duration / scene.duration) * 100}%` : '0%';

                  return (
                    <div
                      key={shot.shotId}
                      className={cn(
                        'h-full border-r border-surface-700 last:border-r-0',
                        'flex items-center justify-center',
                        shot.hasOutput ? 'bg-green-500/20' : 'bg-surface-700/50',
                        selectedShotId === shot.shotId && 'ring-2 ring-brand-400'
                      )}
                      style={{ width: shotWidth, minWidth: '4px' }}
                      onClick={(e) => {
                        e.stopPropagation();
                        onShotClick?.(scene.sceneId, shot.shotId);
                      }}
                    >
                      {shot.hasOutput && shot.thumbnail ? (
                        <img
                          src={`file://${shot.thumbnail}`}
                          alt=""
                          className="w-full h-full object-cover opacity-50"
                        />
                      ) : shot.hasOutput ? (
                        <Play className="w-3 h-3 text-green-400" />
                      ) : null}
                    </div>
                  );
                })}
              </div>

              {/* Scene label */}
              <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-1">
                <span className="text-xs text-white font-medium truncate block">
                  {scene.sceneNumber}
                </span>
              </div>
            </div>
          ))}
        </div>

        {/* Playhead (if needed) */}
        {/* <div
          className="absolute top-0 bottom-0 w-0.5 bg-red-500 pointer-events-none"
          style={{ left: `${playbackProgress}%` }}
        /> */}
      </div>

      {/* Scene details panel */}
      {selectedSceneId && (
        <div className="mt-4 p-3 bg-surface-800/50 rounded-lg">
          {scenes
            .filter((s) => s.sceneId === selectedSceneId)
            .map((scene) => (
              <div key={scene.sceneId}>
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium">
                    {t('tlPreview.scene', 'Scene')} {scene.sceneNumber}
                    {scene.title && ` - ${scene.title}`}
                  </span>
                  <span className="text-sm text-surface-400">{formatDuration(scene.duration)}</span>
                </div>
                <div className="flex gap-2 flex-wrap">
                  {scene.shots.map((shot) => (
                    <div
                      key={shot.shotId}
                      className={cn(
                        'px-2 py-1 rounded text-xs',
                        shot.hasOutput
                          ? 'bg-green-500/20 text-green-300'
                          : 'bg-surface-700 text-surface-400',
                        selectedShotId === shot.shotId && 'ring-1 ring-brand-400'
                      )}
                      onClick={() => onShotClick?.(scene.sceneId, shot.shotId)}
                    >
                      {t('tlPreview.shot', 'Shot')} {shot.shotNumber}
                    </div>
                  ))}
                </div>
              </div>
            ))}
        </div>
      )}
    </div>
  );
}
