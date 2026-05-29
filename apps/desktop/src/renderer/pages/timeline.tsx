/**
 * Interactive timeline editor page.
 * Allows reordering, trimming, and previewing of assembled shots.
 */

import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useDebouncedCallback } from 'use-debounce';
import {
  Film,
  Play,
  Pause,
  SkipBack,
  SkipForward,
  Volume2,
  VolumeX,
  ZoomIn,
  ZoomOut,
  Trash2,
  GripVertical,
  ChevronLeft,
  Loader2,
  Save,
  Undo,
  Redo,
  Lock,
  Unlock,
  Eye,
  EyeOff,
  Layers,
  AlertCircle,
  Check,
  CloudOff,
} from 'lucide-react';
import { cn } from '../lib/utils';
import { useTranslation } from '../i18n/use-translation';
import { useUndoRedo } from '../hooks/use-undo-redo';
import { useWebSocketEvent, EventType } from '../lib/websocket';
import { VideoPlayer } from '../components/video-player';
import {
  ClipContextMenu,
  LipSyncQuickModal,
  TransitionZone,
  TransitionConfig,
} from '../components/timeline';
import { AudioMixer, useAudioMixer, AudioTrack } from '../components/audio-mixer';

// Transition types (extended to match TransitionZone)
type TransitionType = 'cut' | 'fade' | 'crossfade' | 'dissolve' | 'wipe' | 'slide';

// Timeline clip interface
interface TimelineClip {
  id: string;
  shotId: string;
  shotNumber: string;
  sceneId: string;
  sceneNumber: number;
  startTime: number;
  duration: number;
  thumbnailUrl?: string;
  videoUrl?: string;
  isLocked: boolean;
  isVisible: boolean;
  transition: TransitionType;
  transitionDuration: number;
}

// Scene group for timeline
interface SceneGroup {
  id: string;
  sceneNumber: number;
  title: string;
  clips: TimelineClip[];
  totalDuration: number;
}

// Format time in MM:SS.ms format
function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  const ms = Math.floor((seconds % 1) * 100);
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}.${ms.toString().padStart(2, '0')}`;
}

// Timeline ruler component
function TimelineRuler({
  duration,
  zoom,
  scrollLeft,
}: {
  duration: number;
  zoom: number;
  scrollLeft: number;
}) {
  const marks: number[] = [];
  const interval = zoom > 1.5 ? 1 : zoom > 0.5 ? 5 : 10;

  for (let i = 0; i <= Math.ceil(duration); i += interval) {
    marks.push(i);
  }

  return (
    <div className="h-6 bg-surface-900 border-b border-surface-700 relative overflow-hidden">
      <div
        className="absolute top-0 left-0 h-full flex"
        style={{ transform: `translateX(-${scrollLeft}px)` }}
      >
        {marks.map((time) => (
          <div
            key={time}
            className="flex-shrink-0 border-l border-surface-700 relative"
            style={{ width: `${interval * 50 * zoom}px` }}
          >
            <span className="absolute top-1 left-1 text-xs text-surface-500">
              {formatTime(time)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// Timeline clip component
function TimelineClipComponent({
  clip,
  zoom,
  isSelected,
  onSelect,
  onDragStart,
  onToggleLock,
  onToggleVisibility,
  onContextMenu,
  onTrimStart,
  onTrimEnd,
}: {
  clip: TimelineClip;
  zoom: number;
  isSelected: boolean;
  onSelect: () => void;
  onDragStart: (e: React.DragEvent) => void;
  onToggleLock: () => void;
  onToggleVisibility: () => void;
  onContextMenu: (e: React.MouseEvent) => void;
  onTrimStart?: (deltaSeconds: number) => void;
  onTrimEnd?: (deltaSeconds: number) => void;
}) {
  const { t } = useTranslation();
  const [isTrimming, setIsTrimming] = useState<'start' | 'end' | null>(null);
  const trimStartRef = useRef<{ startX: number; originalDuration: number } | null>(null);
  const width = clip.duration * 50 * zoom;

  // Handle trim drag start
  const handleTrimMouseDown = useCallback(
    (e: React.MouseEvent, edge: 'start' | 'end') => {
      e.preventDefault();
      e.stopPropagation();
      setIsTrimming(edge);
      trimStartRef.current = { startX: e.clientX, originalDuration: clip.duration };
    },
    [clip.duration]
  );

  // Handle trim drag
  useEffect(() => {
    if (!isTrimming || !trimStartRef.current) return;

    const handleMouseMove = (e: MouseEvent) => {
      if (!trimStartRef.current) return;

      const deltaX = e.clientX - trimStartRef.current.startX;
      const deltaSeconds = deltaX / (50 * zoom);

      if (isTrimming === 'end') {
        // Trim end: increase/decrease duration
        const newDuration = Math.max(0.5, trimStartRef.current.originalDuration + deltaSeconds);
        if (onTrimEnd && Math.abs(newDuration - clip.duration) > 0.01) {
          onTrimEnd(newDuration - clip.duration);
        }
      } else if (isTrimming === 'start') {
        // Trim start: decrease/increase duration (reverse direction)
        const newDuration = Math.max(0.5, trimStartRef.current.originalDuration - deltaSeconds);
        if (onTrimStart && Math.abs(newDuration - clip.duration) > 0.01) {
          onTrimStart(clip.duration - newDuration);
        }
      }
    };

    const handleMouseUp = () => {
      setIsTrimming(null);
      trimStartRef.current = null;
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isTrimming, zoom, clip.duration, onTrimStart, onTrimEnd]);

  return (
    <div
      className={cn(
        'relative h-16 rounded border-2 cursor-pointer transition-all group overflow-hidden',
        isSelected
          ? 'border-brand-500 bg-brand-500/20'
          : 'border-surface-600 bg-surface-800 hover:border-surface-500',
        clip.isLocked && 'opacity-60',
        !clip.isVisible && 'opacity-30'
      )}
      style={{ width: `${width}px`, minWidth: '60px' }}
      onClick={onSelect}
      onContextMenu={onContextMenu}
      draggable={!clip.isLocked}
      onDragStart={onDragStart}
    >
      {/* Thumbnail */}
      {clip.thumbnailUrl ? (
        <img
          src={clip.thumbnailUrl}
          alt={`${t('timeline.shot', 'Shot')} ${clip.shotNumber}`}
          className="absolute inset-0 w-full h-full object-cover opacity-50"
        />
      ) : (
        <div className="absolute inset-0 bg-gradient-to-br from-surface-700 to-surface-800" />
      )}

      {/* Content */}
      <div className="absolute inset-0 flex flex-col justify-between p-1.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1">
            <GripVertical className="w-3 h-3 text-surface-400 opacity-0 group-hover:opacity-100" />
            <span className="text-xs font-medium bg-black/50 px-1 rounded">{clip.shotNumber}</span>
          </div>
          <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100">
            <button
              onClick={(e) => {
                e.stopPropagation();
                onToggleLock();
              }}
              className="p-0.5 hover:bg-black/50 rounded"
              title={clip.isLocked ? t('timeline.unlock', 'Unlock') : t('timeline.lock', 'Lock')}
            >
              {clip.isLocked ? (
                <Lock className="w-3 h-3 text-yellow-400" />
              ) : (
                <Unlock className="w-3 h-3 text-surface-400" />
              )}
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onToggleVisibility();
              }}
              className="p-0.5 hover:bg-black/50 rounded"
              title={clip.isVisible ? t('timeline.hide', 'Hide') : t('timeline.show', 'Show')}
            >
              {clip.isVisible ? (
                <Eye className="w-3 h-3 text-surface-400" />
              ) : (
                <EyeOff className="w-3 h-3 text-red-400" />
              )}
            </button>
          </div>
        </div>
        <div className="text-xs text-surface-300">{formatTime(clip.duration)}</div>
      </div>

      {/* Resize handles */}
      {!clip.isLocked && (
        <>
          <div
            className={cn(
              'absolute left-0 top-0 bottom-0 w-2 cursor-ew-resize bg-brand-500 transition-opacity',
              isTrimming === 'start' ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'
            )}
            onMouseDown={(e) => handleTrimMouseDown(e, 'start')}
          />
          <div
            className={cn(
              'absolute right-0 top-0 bottom-0 w-2 cursor-ew-resize bg-brand-500 transition-opacity',
              isTrimming === 'end' ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'
            )}
            onMouseDown={(e) => handleTrimMouseDown(e, 'end')}
          />
        </>
      )}
    </div>
  );
}

// Playhead component
function Playhead({ position, zoom }: { position: number; zoom: number }) {
  return (
    <div
      className="absolute top-0 bottom-0 w-0.5 bg-red-500 z-20 pointer-events-none"
      style={{ left: `${position * 50 * zoom}px` }}
    >
      <div className="absolute -top-1 left-1/2 -translate-x-1/2 w-3 h-3 bg-red-500 rounded-b-full" />
    </div>
  );
}

// Transport controls
function TransportControls({
  isPlaying,
  currentTime,
  duration,
  volume,
  isMuted,
  onPlayPause,
  onSeek,
  onVolumeChange,
  onMuteToggle,
  onPrevious,
  onNext,
}: {
  isPlaying: boolean;
  currentTime: number;
  duration: number;
  volume: number;
  isMuted: boolean;
  onPlayPause: () => void;
  onSeek: (time: number) => void;
  onVolumeChange: (volume: number) => void;
  onMuteToggle: () => void;
  onPrevious: () => void;
  onNext: () => void;
}) {
  const { t } = useTranslation();
  return (
    <div className="flex items-center gap-4 p-3 bg-surface-900 border-t border-surface-700">
      {/* Time display */}
      <div className="w-32 text-sm font-mono">
        <span className="text-brand-400">{formatTime(currentTime)}</span>
        <span className="text-surface-500"> / {formatTime(duration)}</span>
      </div>

      {/* Transport buttons */}
      <div className="flex items-center gap-1">
        <button
          onClick={onPrevious}
          className="p-2 hover:bg-surface-700 rounded transition-colors"
          title={t('timeline.previousClip', 'Previous clip')}
        >
          <SkipBack className="w-4 h-4" />
        </button>
        <button
          onClick={onPlayPause}
          className="p-2 bg-brand-500 hover:bg-brand-600 rounded-full transition-colors"
        >
          {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5" />}
        </button>
        <button
          onClick={onNext}
          className="p-2 hover:bg-surface-700 rounded transition-colors"
          title={t('timeline.nextClip', 'Next clip')}
        >
          <SkipForward className="w-4 h-4" />
        </button>
      </div>

      {/* Scrubber */}
      <div className="flex-1">
        <input
          type="range"
          min={0}
          max={duration}
          step={0.1}
          value={currentTime}
          onChange={(e) => onSeek(parseFloat(e.target.value))}
          className="w-full h-1 bg-surface-700 rounded-full appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-brand-500"
        />
      </div>

      {/* Volume */}
      <div className="flex items-center gap-2">
        <button
          onClick={onMuteToggle}
          className="p-1 hover:bg-surface-700 rounded transition-colors"
        >
          {isMuted ? <VolumeX className="w-4 h-4 text-red-400" /> : <Volume2 className="w-4 h-4" />}
        </button>
        <input
          type="range"
          min={0}
          max={1}
          step={0.1}
          value={isMuted ? 0 : volume}
          onChange={(e) => onVolumeChange(parseFloat(e.target.value))}
          className="w-20 h-1 bg-surface-700 rounded-full appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-2 [&::-webkit-slider-thumb]:h-2 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-surface-400"
        />
      </div>
    </div>
  );
}

// Timeline state type for undo/redo
interface TimelineState {
  clips: TimelineClip[];
  sceneGroups: SceneGroup[];
}

export function TimelinePage() {
  const { t } = useTranslation();
  const { projectId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // Timeline state
  const [zoom, setZoom] = useState(1);
  const [scrollLeft, setScrollLeft] = useState(0);
  const [selectedClipId, setSelectedClipId] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [volume, setVolume] = useState(0.8);
  const [isMuted, setIsMuted] = useState(false);

  // Auto-save state
  const [autoSaveStatus, setAutoSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>(
    'idle'
  );
  const saveStatusTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const previousClipsRef = useRef<TimelineClip[] | null>(null);

  // Context menu state
  const [contextMenuState, setContextMenuState] = useState<{
    isOpen: boolean;
    position: { x: number; y: number };
    clipId: string | null;
  }>({
    isOpen: false,
    position: { x: 0, y: 0 },
    clipId: null,
  });

  // Lip sync modal state
  const [lipSyncModalState, setLipSyncModalState] = useState<{
    isOpen: boolean;
    clipId: string;
    clipLabel: string;
  }>({
    isOpen: false,
    clipId: '',
    clipLabel: '',
  });

  // Audio mixer state
  const [showAudioMixer, setShowAudioMixer] = useState(false);
  const audioMixer = useAudioMixer([
    {
      id: 'dialogue',
      name: t('timeline.dialogue', 'Dialogue'),
      type: 'dialogue',
      volume: 0.8,
      pan: 0,
      muted: false,
      solo: false,
      color: '#3b82f6',
    },
    {
      id: 'music',
      name: t('timeline.music', 'Music'),
      type: 'music',
      volume: 0.5,
      pan: 0,
      muted: false,
      solo: false,
      color: '#8b5cf6',
    },
    {
      id: 'sfx',
      name: 'SFX',
      type: 'sfx',
      volume: 0.7,
      pan: 0,
      muted: false,
      solo: false,
      color: '#22c55e',
    },
  ] as AudioTrack[]);

  // Undo/Redo state for timeline clips
  const {
    state: timelineState,
    set: setTimelineState,
    undo,
    redo,
    canUndo,
    canRedo,
    historySize,
  } = useUndoRedo<TimelineState>(
    {
      clips: [],
      sceneGroups: [],
    },
    {
      maxHistorySize: 50,
      onChange: () => {
        // Track that there are unsaved changes
      },
    }
  );

  const hasChanges = historySize > 0;

  const timelineRef = useRef<HTMLDivElement>(null);
  const playbackRef = useRef<number | null>(null);

  // Fetch project and shots for timeline
  const {
    data: timelineData,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ['timeline', projectId],
    queryFn: async () => {
      // Fetch scenes with shots
      const scenes = await window.electronAPI.backendRequest<any[]>('scenes.list', {
        project_id: projectId,
      });

      // Build timeline clips from scenes
      const sceneGroups: SceneGroup[] = [];
      let currentTime = 0;

      for (const scene of scenes || []) {
        const clips: TimelineClip[] = [];

        // Fetch shots for scene
        const shots = await window.electronAPI.backendRequest<any[]>('shots.list', {
          scene_id: scene.id,
        });

        for (const shot of shots || []) {
          if (shot.state === 'completed' || shot.state === 'approved') {
            clips.push({
              id: shot.id,
              shotId: shot.id,
              shotNumber: shot.shot_number,
              sceneId: scene.id,
              sceneNumber: scene.sequence_number,
              startTime: currentTime,
              duration: shot.duration_seconds || 3,
              thumbnailUrl: shot.thumbnail_path ? `file://${shot.thumbnail_path}` : undefined,
              videoUrl: shot.output_path ? `file://${shot.output_path}` : undefined,
              isLocked: shot.timeline_locked || false,
              isVisible: shot.timeline_visible !== false,
              transition: (shot.transition_type as TransitionType) || 'cut',
              transitionDuration: shot.transition_duration || 0.5,
            });
            currentTime += shot.duration_seconds || 3;
          }
        }

        if (clips.length > 0) {
          sceneGroups.push({
            id: scene.id,
            sceneNumber: scene.sequence_number,
            title: scene.title || `${t('timeline.scene', 'Scene')} ${scene.sequence_number}`,
            clips,
            totalDuration: clips.reduce((sum, c) => sum + c.duration, 0),
          });
        }
      }

      // Initialize undo/redo state with loaded data
      const allClips = sceneGroups.flatMap((g) => g.clips);
      setTimelineState({ clips: allClips, sceneGroups }, { merge: true });

      return {
        sceneGroups,
        totalDuration: currentTime,
      };
    },
    enabled: !!projectId,
  });

  // Listen for WebSocket updates - refresh timeline when shots complete
  useWebSocketEvent(EventType.GENERATION_COMPLETED, () => {
    refetch();
  });

  useWebSocketEvent(EventType.SHOT_UPDATED, () => {
    refetch();
  });

  // Playback animation
  useEffect(() => {
    if (isPlaying && timelineData) {
      const startTime = performance.now();
      const startPosition = currentTime;

      const animate = (time: number) => {
        const elapsed = (time - startTime) / 1000;
        const newTime = startPosition + elapsed;

        if (newTime >= timelineData.totalDuration) {
          setCurrentTime(0);
          setIsPlaying(false);
        } else {
          setCurrentTime(newTime);
          playbackRef.current = requestAnimationFrame(animate);
        }
      };

      playbackRef.current = requestAnimationFrame(animate);

      return () => {
        if (playbackRef.current) {
          cancelAnimationFrame(playbackRef.current);
        }
      };
    }
  }, [isPlaying, timelineData]);

  // Clip manipulation handlers with undo support
  const handleDeleteClip = useCallback(
    (clipId: string) => {
      setTimelineState((prev) => ({
        ...prev,
        clips: prev.clips.filter((c) => c.id !== clipId),
        sceneGroups: prev.sceneGroups.map((g) => ({
          ...g,
          clips: g.clips.filter((c) => c.id !== clipId),
        })),
      }));
      setSelectedClipId(null);
    },
    [setTimelineState]
  );

  const handleToggleClipLock = useCallback(
    (clipId: string) => {
      setTimelineState((prev) => ({
        ...prev,
        clips: prev.clips.map((c) => (c.id === clipId ? { ...c, isLocked: !c.isLocked } : c)),
        sceneGroups: prev.sceneGroups.map((g) => ({
          ...g,
          clips: g.clips.map((c) => (c.id === clipId ? { ...c, isLocked: !c.isLocked } : c)),
        })),
      }));
    },
    [setTimelineState]
  );

  const handleToggleClipVisibility = useCallback(
    (clipId: string) => {
      setTimelineState((prev) => ({
        ...prev,
        clips: prev.clips.map((c) => (c.id === clipId ? { ...c, isVisible: !c.isVisible } : c)),
        sceneGroups: prev.sceneGroups.map((g) => ({
          ...g,
          clips: g.clips.map((c) => (c.id === clipId ? { ...c, isVisible: !c.isVisible } : c)),
        })),
      }));
    },
    [setTimelineState]
  );

  const handleUpdateClipDuration = useCallback(
    (clipId: string, duration: number) => {
      setTimelineState((prev) => ({
        ...prev,
        clips: prev.clips.map((c) => (c.id === clipId ? { ...c, duration } : c)),
        sceneGroups: prev.sceneGroups.map((g) => ({
          ...g,
          clips: g.clips.map((c) => (c.id === clipId ? { ...c, duration } : c)),
        })),
      }));
    },
    [setTimelineState]
  );

  // Handle keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if typing in an input
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }

      // Undo: Cmd/Ctrl+Z
      if ((e.metaKey || e.ctrlKey) && e.key === 'z' && !e.shiftKey) {
        e.preventDefault();
        if (canUndo) undo();
        return;
      }
      // Redo: Cmd/Ctrl+Shift+Z or Cmd/Ctrl+Y
      if ((e.metaKey || e.ctrlKey) && (e.key === 'y' || (e.key === 'z' && e.shiftKey))) {
        e.preventDefault();
        if (canRedo) redo();
        return;
      }

      // Playback controls
      if (e.code === 'Space') {
        e.preventDefault();
        setIsPlaying((p) => !p);
      } else if (e.code === 'Home') {
        e.preventDefault();
        setCurrentTime(0);
      } else if (e.code === 'End' && timelineData) {
        e.preventDefault();
        setCurrentTime(timelineData.totalDuration);
      }
      // Frame navigation: Arrow keys (step by 1/24th of a second at 24fps)
      else if (e.code === 'ArrowLeft') {
        e.preventDefault();
        const step = e.shiftKey ? 1 : 1 / 24; // Shift = 1 second, otherwise 1 frame
        setCurrentTime((t) => Math.max(0, t - step));
      } else if (e.code === 'ArrowRight' && timelineData) {
        e.preventDefault();
        const step = e.shiftKey ? 1 : 1 / 24;
        setCurrentTime((t) => Math.min(timelineData.totalDuration, t + step));
      }
      // Zoom controls: +/- or Cmd/Ctrl +/-
      else if (e.key === '=' || e.key === '+') {
        e.preventDefault();
        setZoom((z) => Math.min(z * 1.2, 4));
      } else if (e.key === '-') {
        e.preventDefault();
        setZoom((z) => Math.max(z / 1.2, 0.25));
      } else if (e.key === '0' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setZoom(1); // Reset zoom
      }
      // Clip actions
      else if (e.code === 'Delete' && selectedClipId) {
        e.preventDefault();
        handleDeleteClip(selectedClipId);
      } else if (e.key === 'l' && selectedClipId) {
        e.preventDefault();
        handleToggleClipLock(selectedClipId);
      } else if (e.key === 'v' && selectedClipId) {
        e.preventDefault();
        handleToggleClipVisibility(selectedClipId);
      }
      // Escape to deselect
      else if (e.code === 'Escape' && selectedClipId) {
        e.preventDefault();
        setSelectedClipId(null);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [
    selectedClipId,
    timelineData,
    canUndo,
    canRedo,
    undo,
    redo,
    handleDeleteClip,
    handleToggleClipLock,
    handleToggleClipVisibility,
  ]);

  // Handlers
  const handleZoomIn = () => setZoom((z) => Math.min(z * 1.5, 4));
  const handleZoomOut = () => setZoom((z) => Math.max(z / 1.5, 0.25));

  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    setScrollLeft(e.currentTarget.scrollLeft);
  };

  const handleSeek = (time: number) => {
    setCurrentTime(time);
    if (isPlaying) {
      setIsPlaying(false);
    }
  };

  const handlePrevious = () => {
    // Find previous clip boundary
    if (!timelineData) return;
    let prevTime = 0;
    for (const group of timelineData.sceneGroups) {
      for (const clip of group.clips) {
        if (clip.startTime < currentTime - 0.1) {
          prevTime = clip.startTime;
        }
      }
    }
    setCurrentTime(prevTime);
  };

  const handleNext = () => {
    // Find next clip boundary
    if (!timelineData) return;
    for (const group of timelineData.sceneGroups) {
      for (const clip of group.clips) {
        if (clip.startTime > currentTime + 0.1) {
          setCurrentTime(clip.startTime);
          return;
        }
      }
    }
  };

  // Context menu handlers
  const handleClipContextMenu = useCallback((e: React.MouseEvent, clipId: string) => {
    e.preventDefault();
    e.stopPropagation();
    setContextMenuState({
      isOpen: true,
      position: { x: e.clientX, y: e.clientY },
      clipId,
    });
    setSelectedClipId(clipId);
  }, []);

  const handleCloseContextMenu = useCallback(() => {
    setContextMenuState((prev) => ({
      ...prev,
      isOpen: false,
    }));
  }, []);

  const handleOpenLipSyncModal = useCallback(() => {
    const clipId = contextMenuState.clipId;
    if (!clipId) return;

    // Find the clip to get its label
    let clip: TimelineClip | null = null;
    for (const group of timelineState.sceneGroups) {
      const found = group.clips.find((c) => c.id === clipId);
      if (found) {
        clip = found;
        break;
      }
    }

    if (clip) {
      setLipSyncModalState({
        isOpen: true,
        clipId: clip.id,
        clipLabel: `${t('timeline.shot', 'Shot')} ${clip.shotNumber} (${t('timeline.scene', 'Scene')} ${clip.sceneNumber})`,
      });
    }
    handleCloseContextMenu();
  }, [contextMenuState.clipId, timelineState.sceneGroups, handleCloseContextMenu]);

  const handleCloseLipSyncModal = useCallback(() => {
    setLipSyncModalState((prev) => ({
      ...prev,
      isOpen: false,
    }));
  }, []);

  const handleLipSyncSuccess = useCallback((jobId: string) => {
    // Show toast notification
    console.log('Lip sync job started:', jobId);
    // Optionally refetch timeline to show updated clip when lip sync completes
  }, []);

  // Get available audio tracks for lip sync (from TTS or imported audio)
  const availableAudioTracks = useMemo(() => {
    // For now, return mock audio tracks
    // TODO: Integrate with actual audio tracks from project
    return [
      {
        id: 'audio-1',
        label: `${t('timeline.dialogueTrack', 'Dialogue Track')} 1`,
        path: '/audio/dialogue-1.wav',
      },
      {
        id: 'audio-2',
        label: `${t('timeline.dialogueTrack', 'Dialogue Track')} 2`,
        path: '/audio/dialogue-2.wav',
      },
    ];
  }, []);

  // Get the context menu clip info
  const contextMenuClip = useMemo(() => {
    if (!contextMenuState.clipId) return null;
    for (const group of timelineState.sceneGroups) {
      const clip = group.clips.find((c) => c.id === contextMenuState.clipId);
      if (clip) return clip;
    }
    return null;
  }, [contextMenuState.clipId, timelineState.sceneGroups]);

  // Save timeline mutation with optimistic updates
  const saveMutation = useMutation({
    mutationFn: async (clips: TimelineClip[]) => {
      return window.electronAPI.backendRequest('timeline.save', {
        project_id: projectId,
        clips: clips.map((clip, index) => ({
          shotId: clip.shotId,
          duration: clip.duration,
          isVisible: clip.isVisible,
          isLocked: clip.isLocked,
          orderIndex: index,
          transition: {
            type: clip.transition,
            duration: clip.transitionDuration,
          },
        })),
      });
    },
    onMutate: async () => {
      // Store previous state for potential rollback
      previousClipsRef.current = timelineState.clips;
      setAutoSaveStatus('saving');
      // Clear any existing status timeout
      if (saveStatusTimeoutRef.current) {
        clearTimeout(saveStatusTimeoutRef.current);
      }
    },
    onSuccess: () => {
      setAutoSaveStatus('saved');
      // Clear "saved" status after 2 seconds
      saveStatusTimeoutRef.current = setTimeout(() => {
        setAutoSaveStatus('idle');
      }, 2000);
      queryClient.invalidateQueries({ queryKey: ['timeline', projectId] });
    },
    onError: (error) => {
      console.error('Timeline save failed:', error);
      setAutoSaveStatus('error');
      // Rollback to previous state
      if (previousClipsRef.current) {
        const prevClips = previousClipsRef.current;
        setTimelineState(
          (prev) => ({
            ...prev,
            clips: prevClips,
            sceneGroups: prev.sceneGroups.map((g) => ({
              ...g,
              clips: prevClips.filter((c) => c.sceneId === g.id),
            })),
          }),
          { merge: true }
        );
      }
      // Show error for 3 seconds, then reset
      saveStatusTimeoutRef.current = setTimeout(() => {
        setAutoSaveStatus('idle');
      }, 3000);
    },
  });

  // Debounced auto-save function (500ms delay)
  const debouncedAutoSave = useDebouncedCallback(
    (clips: TimelineClip[]) => {
      saveMutation.mutate(clips);
    },
    500,
    { leading: false, trailing: true }
  );

  // Trigger auto-save when timeline state changes (after initial load)
  useEffect(() => {
    // Skip if no clips or still loading initial data
    if (isLoading || timelineState.clips.length === 0) return;

    // Skip the initial load (when previousClipsRef is null)
    if (previousClipsRef.current === null) {
      previousClipsRef.current = timelineState.clips;
      return;
    }

    // Only auto-save if there are actual changes
    const hasChanges =
      JSON.stringify(timelineState.clips) !== JSON.stringify(previousClipsRef.current);
    if (hasChanges && historySize > 0) {
      debouncedAutoSave(timelineState.clips);
    }
  }, [timelineState.clips, isLoading, historySize, debouncedAutoSave]);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (saveStatusTimeoutRef.current) {
        clearTimeout(saveStatusTimeoutRef.current);
      }
    };
  }, []);

  const handleSave = async () => {
    const allClips = timelineState.sceneGroups.flatMap((g) => g.clips);
    await saveMutation.mutateAsync(allClips);
  };

  // Get the currently selected clip
  const selectedClip = useMemo(() => {
    if (!selectedClipId) return null;
    for (const group of timelineState.sceneGroups) {
      const clip = group.clips.find((c) => c.id === selectedClipId);
      if (clip) return clip;
    }
    return null;
  }, [selectedClipId, timelineState.sceneGroups]);

  // Handle clip transition change (accepts TransitionConfig from TransitionZone)
  const handleUpdateClipTransition = useCallback(
    (clipId: string, transitionConfig: TransitionConfig) => {
      const transition = transitionConfig.type as TransitionType;
      const transitionDuration = transitionConfig.duration;
      setTimelineState((prev) => ({
        ...prev,
        clips: prev.clips.map((c) =>
          c.id === clipId ? { ...c, transition, transitionDuration } : c
        ),
        sceneGroups: prev.sceneGroups.map((g) => ({
          ...g,
          clips: g.clips.map((c) =>
            c.id === clipId ? { ...c, transition, transitionDuration } : c
          ),
        })),
      }));
    },
    [setTimelineState]
  );

  // Handle drag and drop reorder
  const handleDrop = useCallback(
    (targetSceneId: string, targetIndex: number, draggedClipId: string) => {
      setTimelineState((prev) => {
        // Find the dragged clip
        let draggedClip: TimelineClip | null = null;
        let sourceGroupIndex = -1;
        for (let gi = 0; gi < prev.sceneGroups.length; gi++) {
          const clipIndex = prev.sceneGroups[gi].clips.findIndex((c) => c.id === draggedClipId);
          if (clipIndex !== -1) {
            draggedClip = prev.sceneGroups[gi].clips[clipIndex];
            sourceGroupIndex = gi;
            break;
          }
        }

        if (!draggedClip || sourceGroupIndex === -1) return prev;

        // Create new scene groups with the clip moved
        const newGroups = prev.sceneGroups.map((group, gi) => {
          let newClips = [...group.clips];

          // Remove from source
          if (gi === sourceGroupIndex) {
            newClips = newClips.filter((c) => c.id !== draggedClipId);
          }

          // Add to target
          if (group.id === targetSceneId) {
            newClips.splice(targetIndex, 0, { ...draggedClip!, sceneId: targetSceneId });
          }

          return {
            ...group,
            clips: newClips,
            totalDuration: newClips.reduce((sum, c) => sum + c.duration, 0),
          };
        });

        return {
          ...prev,
          sceneGroups: newGroups,
          clips: newGroups.flatMap((g) => g.clips),
        };
      });
    },
    [setTimelineState]
  );

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-8 h-8 animate-spin text-brand-400" />
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-surface-950">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-surface-800">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate(`/project/${projectId}`)}
            className="p-2 hover:bg-surface-800 rounded-lg transition-colors"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-xl font-bold flex items-center gap-2">
              <Film className="w-5 h-5 text-brand-400" />
              {t('timeline.timelineEditor', 'Timeline Editor')}
            </h1>
            <p className="text-sm text-surface-400">
              {timelineData?.sceneGroups.length || 0} {t('timeline.scenes', 'scenes')},{' '}
              {timelineData?.sceneGroups.reduce((sum, g) => sum + g.clips.length, 0) || 0}{' '}
              {t('timeline.clips', 'clips')}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Zoom controls */}
          <div className="flex items-center gap-1 bg-surface-800 rounded-lg p-1">
            <button
              onClick={handleZoomOut}
              className="p-1.5 hover:bg-surface-700 rounded"
              title={t('timeline.zoomOut', 'Zoom out')}
            >
              <ZoomOut className="w-4 h-4" />
            </button>
            <span className="px-2 text-sm text-surface-400">{Math.round(zoom * 100)}%</span>
            <button
              onClick={handleZoomIn}
              className="p-1.5 hover:bg-surface-700 rounded"
              title={t('timeline.zoomIn', 'Zoom in')}
            >
              <ZoomIn className="w-4 h-4" />
            </button>
          </div>

          {/* Undo/Redo */}
          <div className="flex items-center gap-1">
            <button
              onClick={undo}
              className="p-2 hover:bg-surface-800 rounded-lg transition-colors disabled:opacity-50"
              disabled={!canUndo}
              title={`${t('timeline.undo', 'Undo')} (${historySize} ${t('timeline.steps', 'steps')})`}
            >
              <Undo className="w-4 h-4" />
            </button>
            <button
              onClick={redo}
              className="p-2 hover:bg-surface-800 rounded-lg transition-colors disabled:opacity-50"
              disabled={!canRedo}
              title={t('timeline.redo', 'Redo')}
            >
              <Redo className="w-4 h-4" />
            </button>
          </div>

          {/* Auto-save status indicator */}
          <div className="flex items-center gap-2">
            {autoSaveStatus === 'saving' && (
              <div className="flex items-center gap-1.5 text-surface-400 text-sm">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>{t('timeline.saving', 'Saving...')}</span>
              </div>
            )}
            {autoSaveStatus === 'saved' && (
              <div className="flex items-center gap-1.5 text-green-400 text-sm">
                <Check className="w-4 h-4" />
                <span>{t('timeline.saved', 'Saved')}</span>
              </div>
            )}
            {autoSaveStatus === 'error' && (
              <div className="flex items-center gap-1.5 text-red-400 text-sm">
                <CloudOff className="w-4 h-4" />
                <span>{t('timeline.saveFailed', 'Save failed')}</span>
              </div>
            )}
          </div>

          {/* Manual Save button (shown when there are unsaved changes or error) */}
          {(hasChanges || autoSaveStatus === 'error') && (
            <button
              onClick={handleSave}
              disabled={saveMutation.isPending}
              className="px-4 py-2 bg-brand-500 hover:bg-brand-600 disabled:opacity-50 rounded-lg text-sm flex items-center gap-2"
            >
              {saveMutation.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Save className="w-4 h-4" />
              )}
              {saveMutation.isPending ? t('timeline.saving', 'Saving...') : t('timeline.save', 'Save')}
            </button>
          )}

          {/* Export */}
          <button
            onClick={() => setShowAudioMixer(!showAudioMixer)}
            className={cn(
              'px-4 py-2 rounded-lg text-sm flex items-center gap-2',
              showAudioMixer
                ? 'bg-brand-500/20 text-brand-400'
                : 'bg-surface-700 hover:bg-surface-600'
            )}
            title={t('timeline.toggleAudioMixer', 'Toggle Audio Mixer')}
          >
            <Volume2 className="w-4 h-4" />
            {t('timeline.mixer', 'Mixer')}
          </button>
          <button
            onClick={() => navigate(`/project/${projectId}/export`)}
            className="px-4 py-2 bg-surface-700 hover:bg-surface-600 rounded-lg text-sm"
          >
            {t('timeline.export', 'Export')}
          </button>
        </div>
      </div>

      {/* Preview area */}
      <div className="flex-1 flex">
        {/* Preview panel */}
        <div className="w-1/2 bg-black flex items-center justify-center border-r border-surface-800 p-4">
          {selectedClip?.videoUrl ? (
            <div className="w-full max-w-2xl">
              <VideoPlayer
                src={selectedClip.videoUrl}
                poster={selectedClip.thumbnailUrl}
                autoPlay={false}
                showControls={true}
                className="rounded-lg overflow-hidden"
                onEnded={() => {
                  // Optionally auto-advance to next clip
                }}
              />
              <div className="mt-2 text-center">
                <p className="text-sm text-surface-400">
                  {t('timeline.shot', 'Shot')} {selectedClip.shotNumber} &middot;{' '}
                  {t('timeline.scene', 'Scene')} {selectedClip.sceneNumber}
                </p>
              </div>
            </div>
          ) : selectedClip ? (
            <div className="text-center text-surface-400">
              <div className="w-80 h-48 bg-surface-900 rounded-lg flex items-center justify-center mb-2">
                <AlertCircle className="w-12 h-12 text-surface-600" />
              </div>
              <p className="text-sm">{t('timeline.noVideoFileAvailable', 'No video file available')}</p>
              <p className="text-xs text-surface-500 mt-1">
                {t('timeline.shot', 'Shot')} {selectedClip.shotNumber}{' '}
                {t('timeline.hasNotBeenGeneratedYet', 'has not been generated yet')}
              </p>
            </div>
          ) : (
            <div className="text-center text-surface-400">
              <Film className="w-12 h-12 mx-auto mb-2 opacity-50" />
              <p>{t('timeline.selectAClipToPreview', 'Select a clip to preview')}</p>
            </div>
          )}
        </div>

        {/* Clip properties */}
        <div className="w-1/2 p-4 overflow-y-auto bg-surface-900">
          {selectedClip ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="font-medium">{t('timeline.clipProperties', 'Clip Properties')}</h3>
                <span className="text-xs text-surface-500">
                  {t('timeline.shot', 'Shot')} {selectedClip.shotNumber}
                </span>
              </div>

              <div className="space-y-4">
                {/* Duration */}
                <div>
                  <label className="block text-sm text-surface-400 mb-1">
                    {t('timeline.duration', 'Duration')}
                  </label>
                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      step="0.1"
                      min="0.5"
                      max="60"
                      className="flex-1 bg-surface-800 border border-surface-700 rounded px-3 py-2 disabled:opacity-50"
                      value={selectedClip.duration}
                      disabled={selectedClip.isLocked}
                      onChange={(e) => {
                        const value = parseFloat(e.target.value);
                        if (!isNaN(value) && value >= 0.5) {
                          handleUpdateClipDuration(selectedClip.id, value);
                        }
                      }}
                    />
                    <span className="text-surface-400">{t('timeline.seconds', 'seconds')}</span>
                  </div>
                </div>

                {/* Transition */}
                <div>
                  <label className="block text-sm text-surface-400 mb-1">
                    {t('timeline.transitionIn', 'Transition In')}
                  </label>
                  <select
                    className="w-full bg-surface-800 border border-surface-700 rounded px-3 py-2 disabled:opacity-50"
                    value={selectedClip.transition}
                    disabled={selectedClip.isLocked}
                    onChange={(e) =>
                      handleUpdateClipTransition(selectedClip.id, {
                        type: e.target.value as 'cut' | 'fade' | 'crossfade',
                        duration: selectedClip.transitionDuration,
                      })
                    }
                  >
                    <option value="cut">{t('timeline.cutInstant', 'Cut (instant)')}</option>
                    <option value="fade">{t('timeline.fade', 'Fade')}</option>
                    <option value="crossfade">{t('timeline.crossfade', 'Crossfade')}</option>
                    <option value="dissolve">{t('timeline.dissolve', 'Dissolve')}</option>
                    <option value="wipe">{t('timeline.wipe', 'Wipe')}</option>
                    <option value="slide">{t('timeline.slide', 'Slide')}</option>
                  </select>
                </div>

                {/* Transition duration (only for non-cut transitions) */}
                {selectedClip.transition !== 'cut' && (
                  <div>
                    <label className="block text-sm text-surface-400 mb-1">
                      {t('timeline.transitionDuration', 'Transition Duration')}
                    </label>
                    <div className="flex items-center gap-2">
                      <input
                        type="number"
                        step="0.1"
                        min="0.1"
                        max="3"
                        className="flex-1 bg-surface-800 border border-surface-700 rounded px-3 py-2 disabled:opacity-50"
                        value={selectedClip.transitionDuration}
                        disabled={selectedClip.isLocked}
                        onChange={(e) => {
                          const value = parseFloat(e.target.value);
                          if (!isNaN(value) && value >= 0.1) {
                            handleUpdateClipTransition(selectedClip.id, {
                              type: selectedClip.transition as 'cut' | 'fade' | 'crossfade',
                              duration: value,
                            });
                          }
                        }}
                      />
                      <span className="text-surface-400">{t('timeline.seconds', 'seconds')}</span>
                    </div>
                  </div>
                )}

                {/* Status indicators */}
                <div className="pt-2 border-t border-surface-700 space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-surface-400">{t('timeline.locked', 'Locked')}</span>
                    <button
                      onClick={() => handleToggleClipLock(selectedClip.id)}
                      className={cn(
                        'px-3 py-1 rounded text-xs font-medium',
                        selectedClip.isLocked
                          ? 'bg-yellow-500/20 text-yellow-400'
                          : 'bg-surface-700 text-surface-400'
                      )}
                    >
                      {selectedClip.isLocked ? t('timeline.yes', 'Yes') : t('timeline.no', 'No')}
                    </button>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-surface-400">{t('timeline.visible', 'Visible')}</span>
                    <button
                      onClick={() => handleToggleClipVisibility(selectedClip.id)}
                      className={cn(
                        'px-3 py-1 rounded text-xs font-medium',
                        selectedClip.isVisible
                          ? 'bg-green-500/20 text-green-400'
                          : 'bg-red-500/20 text-red-400'
                      )}
                    >
                      {selectedClip.isVisible ? t('timeline.yes', 'Yes') : t('timeline.no', 'No')}
                    </button>
                  </div>
                </div>

                {/* Actions */}
                <div className="pt-2 border-t border-surface-700">
                  <button
                    onClick={() => handleDeleteClip(selectedClip.id)}
                    disabled={selectedClip.isLocked}
                    className="w-full px-4 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 rounded-lg text-sm flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <Trash2 className="w-4 h-4" />
                    {t('timeline.removeFromTimeline', 'Remove from Timeline')}
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="h-full flex items-center justify-center text-surface-400">
              <div className="text-center">
                <Layers className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p>{t('timeline.selectAClipToEditProperties', 'Select a clip to edit properties')}</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Thumbnail minimap strip */}
      {timelineData && timelineData.sceneGroups.length > 0 && (
        <div className="h-10 bg-surface-900 border-t border-surface-800 flex items-center px-2 gap-0.5 overflow-hidden">
          <span className="text-[10px] text-surface-500 mr-1 shrink-0">{t('timeline.map', 'MAP')}</span>
          {timelineData.sceneGroups
            .flatMap((g) => g.clips)
            .map((clip) => {
              const fraction = clip.duration / (timelineData.totalDuration || 1);
              return (
                <button
                  key={clip.id}
                  onClick={() => {
                    setCurrentTime(clip.startTime);
                    setSelectedClipId(clip.id);
                  }}
                  className={cn(
                    'h-7 rounded-sm border transition-all relative overflow-hidden',
                    selectedClipId === clip.id
                      ? 'border-brand-500 ring-1 ring-brand-500'
                      : 'border-surface-700 hover:border-surface-500'
                  )}
                  style={{ width: `${Math.max(fraction * 100, 1.5)}%` }}
                  title={`${t('timeline.shot', 'Shot')} ${clip.shotNumber} — ${clip.duration.toFixed(1)}s`}
                >
                  {clip.thumbnailUrl ? (
                    <img src={clip.thumbnailUrl} alt="" className="w-full h-full object-cover" />
                  ) : (
                    <div className="w-full h-full bg-surface-800" />
                  )}
                </button>
              );
            })}
          {/* Playhead indicator in minimap */}
          <div
            className="absolute h-7 w-0.5 bg-red-500 pointer-events-none z-10"
            style={{ left: `${2 + (currentTime / (timelineData.totalDuration || 1)) * 96}%` }}
          />
        </div>
      )}

      {/* Timeline area */}
      <div className="h-64 border-t border-surface-800 flex flex-col">
        {/* Ruler */}
        <TimelineRuler
          duration={timelineData?.totalDuration || 0}
          zoom={zoom}
          scrollLeft={scrollLeft}
        />

        {/* Tracks */}
        <div
          ref={timelineRef}
          className="flex-1 overflow-x-auto overflow-y-auto relative"
          onScroll={handleScroll}
        >
          <div
            className="relative"
            style={{ width: `${(timelineData?.totalDuration || 0) * 50 * zoom + 200}px` }}
          >
            {/* Playhead */}
            <Playhead position={currentTime} zoom={zoom} />

            {/* Scene tracks */}
            {timelineData?.sceneGroups.map((group) => (
              <div key={group.id} className="flex items-center border-b border-surface-800">
                {/* Track header */}
                <div className="w-32 shrink-0 p-2 bg-surface-900 border-r border-surface-700">
                  <div className="text-sm font-medium truncate">
                    {t('timeline.scene', 'Scene')} {group.sceneNumber}
                  </div>
                  <div className="text-xs text-surface-400">
                    {group.clips.length} {t('timeline.clips', 'clips')}
                  </div>
                </div>

                {/* Clips */}
                <div
                  className="flex items-center gap-1 p-2 min-h-[80px]"
                  onDragOver={(e) => {
                    e.preventDefault();
                    e.currentTarget.classList.add('bg-brand-500/10');
                  }}
                  onDragLeave={(e) => {
                    e.currentTarget.classList.remove('bg-brand-500/10');
                  }}
                  onDrop={(e) => {
                    e.preventDefault();
                    e.currentTarget.classList.remove('bg-brand-500/10');
                    const clipId = e.dataTransfer.getData('clipId');
                    if (clipId) {
                      // Calculate drop position based on mouse x
                      const rect = e.currentTarget.getBoundingClientRect();
                      const x = e.clientX - rect.left;
                      let insertIndex = 0;
                      let accumulatedWidth = 0;
                      for (let i = 0; i < group.clips.length; i++) {
                        const clipWidth = group.clips[i].duration * 50 * zoom + 4; // 4px gap
                        if (x < accumulatedWidth + clipWidth / 2) {
                          insertIndex = i;
                          break;
                        }
                        accumulatedWidth += clipWidth;
                        insertIndex = i + 1;
                      }
                      handleDrop(group.id, insertIndex, clipId);
                    }
                  }}
                >
                  {group.clips.map((clip, clipIdx) => (
                    <div key={clip.id} className="flex items-center">
                      {/* Transition zone (shown between clips, not before first clip) */}
                      {clipIdx > 0 && (
                        <TransitionZone
                          transition={{
                            type:
                              clip.transition === 'cut' ||
                              clip.transition === 'fade' ||
                              clip.transition === 'crossfade'
                                ? clip.transition
                                : 'cut',
                            duration: clip.transitionDuration,
                          }}
                          onChange={(newTransition) =>
                            handleUpdateClipTransition(clip.id, newTransition)
                          }
                          className="h-16"
                        />
                      )}
                      <TimelineClipComponent
                        clip={clip}
                        zoom={zoom}
                        isSelected={selectedClipId === clip.id}
                        onSelect={() => setSelectedClipId(clip.id)}
                        onDragStart={(e) => {
                          e.dataTransfer.setData('clipId', clip.id);
                          e.dataTransfer.effectAllowed = 'move';
                        }}
                        onContextMenu={(e) => handleClipContextMenu(e, clip.id)}
                        onToggleLock={() => handleToggleClipLock(clip.id)}
                        onToggleVisibility={() => handleToggleClipVisibility(clip.id)}
                        onTrimStart={(delta) => {
                          // Trim from start: decrease duration
                          const newDuration = Math.max(0.5, clip.duration - delta);
                          handleUpdateClipDuration(clip.id, newDuration);
                        }}
                        onTrimEnd={(delta) => {
                          // Trim from end: adjust duration
                          const newDuration = Math.max(0.5, clip.duration + delta);
                          handleUpdateClipDuration(clip.id, newDuration);
                        }}
                      />
                    </div>
                  ))}
                </div>
              </div>
            ))}

            {/* Empty state */}
            {(!timelineData?.sceneGroups || timelineData.sceneGroups.length === 0) && (
              <div className="flex items-center justify-center h-full text-surface-400">
                <div className="text-center">
                  <Film className="w-12 h-12 mx-auto mb-2 opacity-50" />
                  <p>{t('timeline.noCompletedShots', 'No completed shots to add to timeline')}</p>
                  <p className="text-sm mt-1">
                    {t('timeline.generateSomeShotsFirst', 'Generate some shots first')}
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Transport controls */}
      <TransportControls
        isPlaying={isPlaying}
        currentTime={currentTime}
        duration={timelineData?.totalDuration || 0}
        volume={volume}
        isMuted={isMuted}
        onPlayPause={() => setIsPlaying(!isPlaying)}
        onSeek={handleSeek}
        onVolumeChange={setVolume}
        onMuteToggle={() => setIsMuted(!isMuted)}
        onPrevious={handlePrevious}
        onNext={handleNext}
      />

      {/* Audio Mixer Panel */}
      {showAudioMixer && (
        <div className="border-t border-surface-700">
          <AudioMixer
            tracks={audioMixer.tracks}
            onTrackChange={audioMixer.updateTrack}
            onTrackAdd={audioMixer.addTrack}
            onTrackRemove={audioMixer.removeTrack}
            masterVolume={audioMixer.masterVolume}
            onMasterVolumeChange={audioMixer.setMasterVolume}
            isPlaying={isPlaying}
            onPlayPause={() => setIsPlaying(!isPlaying)}
          />
        </div>
      )}

      {/* Context Menu */}
      {contextMenuClip && (
        <ClipContextMenu
          isOpen={contextMenuState.isOpen}
          position={contextMenuState.position}
          onClose={handleCloseContextMenu}
          clipId={contextMenuClip.id}
          isLocked={contextMenuClip.isLocked}
          isVisible={contextMenuClip.isVisible}
          hasVideo={!!contextMenuClip.videoUrl}
          onApplyLipSync={handleOpenLipSyncModal}
          onDelete={() => {
            handleDeleteClip(contextMenuClip.id);
            handleCloseContextMenu();
          }}
          onToggleLock={() => {
            handleToggleClipLock(contextMenuClip.id);
            handleCloseContextMenu();
          }}
          onToggleVisibility={() => {
            handleToggleClipVisibility(contextMenuClip.id);
            handleCloseContextMenu();
          }}
        />
      )}

      {/* Lip Sync Quick Modal */}
      <LipSyncQuickModal
        isOpen={lipSyncModalState.isOpen}
        onClose={handleCloseLipSyncModal}
        clipId={lipSyncModalState.clipId}
        clipLabel={lipSyncModalState.clipLabel}
        availableAudioTracks={availableAudioTracks}
        onSuccess={handleLipSyncSuccess}
      />
    </div>
  );
}

export default TimelinePage;
