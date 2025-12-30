/**
 * Interactive timeline editor page.
 * Allows reordering, trimming, and previewing of assembled shots.
 */

import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
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
  Maximize2,
  Clock,
  Scissors,
  Trash2,
  Copy,
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
} from 'lucide-react';
import { cn } from '../lib/utils';
import { useUndoRedo } from '../hooks/use-undo-redo';
import { useWebSocketEvent, EventType } from '../lib/websocket';

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
function TimelineRuler({ duration, zoom, scrollLeft }: { duration: number; zoom: number; scrollLeft: number }) {
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
  onDelete,
}: {
  clip: TimelineClip;
  zoom: number;
  isSelected: boolean;
  onSelect: () => void;
  onDragStart: (e: React.DragEvent) => void;
  onToggleLock: () => void;
  onToggleVisibility: () => void;
  onDelete: () => void;
}) {
  const width = clip.duration * 50 * zoom;

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
      draggable={!clip.isLocked}
      onDragStart={onDragStart}
    >
      {/* Thumbnail */}
      {clip.thumbnailUrl ? (
        <img
          src={clip.thumbnailUrl}
          alt={`Shot ${clip.shotNumber}`}
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
            <span className="text-xs font-medium bg-black/50 px-1 rounded">
              {clip.shotNumber}
            </span>
          </div>
          <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100">
            <button
              onClick={(e) => {
                e.stopPropagation();
                onToggleLock();
              }}
              className="p-0.5 hover:bg-black/50 rounded"
              title={clip.isLocked ? 'Unlock' : 'Lock'}
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
              title={clip.isVisible ? 'Hide' : 'Show'}
            >
              {clip.isVisible ? (
                <Eye className="w-3 h-3 text-surface-400" />
              ) : (
                <EyeOff className="w-3 h-3 text-red-400" />
              )}
            </button>
          </div>
        </div>
        <div className="text-xs text-surface-300">
          {formatTime(clip.duration)}
        </div>
      </div>

      {/* Resize handles */}
      {!clip.isLocked && (
        <>
          <div className="absolute left-0 top-0 bottom-0 w-1 cursor-ew-resize bg-brand-500 opacity-0 group-hover:opacity-100" />
          <div className="absolute right-0 top-0 bottom-0 w-1 cursor-ew-resize bg-brand-500 opacity-0 group-hover:opacity-100" />
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
          title="Previous clip"
        >
          <SkipBack className="w-4 h-4" />
        </button>
        <button
          onClick={onPlayPause}
          className="p-2 bg-brand-500 hover:bg-brand-600 rounded-full transition-colors"
        >
          {isPlaying ? (
            <Pause className="w-5 h-5" />
          ) : (
            <Play className="w-5 h-5" />
          )}
        </button>
        <button
          onClick={onNext}
          className="p-2 hover:bg-surface-700 rounded transition-colors"
          title="Next clip"
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
          {isMuted ? (
            <VolumeX className="w-4 h-4 text-red-400" />
          ) : (
            <Volume2 className="w-4 h-4" />
          )}
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

  // Undo/Redo state for timeline clips
  const {
    state: timelineState,
    set: setTimelineState,
    undo,
    redo,
    canUndo,
    canRedo,
    historySize,
  } = useUndoRedo<TimelineState>({
    clips: [],
    sceneGroups: [],
  }, {
    maxHistorySize: 50,
    onChange: () => {
      // Track that there are unsaved changes
    },
  });

  const hasChanges = historySize > 0;

  const timelineRef = useRef<HTMLDivElement>(null);
  const playbackRef = useRef<number | null>(null);

  // Fetch project and shots for timeline
  const { data: timelineData, isLoading, refetch } = useQuery({
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
              isLocked: false,
              isVisible: true,
            });
            currentTime += shot.duration_seconds || 3;
          }
        }

        if (clips.length > 0) {
          sceneGroups.push({
            id: scene.id,
            sceneNumber: scene.sequence_number,
            title: scene.title || `Scene ${scene.sequence_number}`,
            clips,
            totalDuration: clips.reduce((sum, c) => sum + c.duration, 0),
          });
        }
      }

      // Initialize undo/redo state with loaded data
      const allClips = sceneGroups.flatMap(g => g.clips);
      setTimelineState({ clips: allClips, sceneGroups }, { merge: true });

      return {
        sceneGroups,
        totalDuration: currentTime,
      };
    },
    enabled: !!projectId,
  });

  // Listen for WebSocket updates - refresh timeline when shots complete
  useWebSocketEvent(EventType.JOB_COMPLETED, () => {
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
  }, [selectedClipId, timelineData, canUndo, canRedo, undo, redo, handleDeleteClip, handleToggleClipLock, handleToggleClipVisibility]);

  // Clip manipulation handlers with undo support
  const handleDeleteClip = useCallback((clipId: string) => {
    setTimelineState(prev => ({
      ...prev,
      clips: prev.clips.filter(c => c.id !== clipId),
      sceneGroups: prev.sceneGroups.map(g => ({
        ...g,
        clips: g.clips.filter(c => c.id !== clipId),
      })),
    }));
    setSelectedClipId(null);
  }, [setTimelineState]);

  const handleToggleClipLock = useCallback((clipId: string) => {
    setTimelineState(prev => ({
      ...prev,
      clips: prev.clips.map(c =>
        c.id === clipId ? { ...c, isLocked: !c.isLocked } : c
      ),
      sceneGroups: prev.sceneGroups.map(g => ({
        ...g,
        clips: g.clips.map(c =>
          c.id === clipId ? { ...c, isLocked: !c.isLocked } : c
        ),
      })),
    }));
  }, [setTimelineState]);

  const handleToggleClipVisibility = useCallback((clipId: string) => {
    setTimelineState(prev => ({
      ...prev,
      clips: prev.clips.map(c =>
        c.id === clipId ? { ...c, isVisible: !c.isVisible } : c
      ),
      sceneGroups: prev.sceneGroups.map(g => ({
        ...g,
        clips: g.clips.map(c =>
          c.id === clipId ? { ...c, isVisible: !c.isVisible } : c
        ),
      })),
    }));
  }, [setTimelineState]);

  const handleUpdateClipDuration = useCallback((clipId: string, duration: number) => {
    setTimelineState(prev => ({
      ...prev,
      clips: prev.clips.map(c =>
        c.id === clipId ? { ...c, duration } : c
      ),
      sceneGroups: prev.sceneGroups.map(g => ({
        ...g,
        clips: g.clips.map(c =>
          c.id === clipId ? { ...c, duration } : c
        ),
      })),
    }));
  }, [setTimelineState]);

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

  // Save timeline mutation
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
        })),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['timeline', projectId] });
    },
  });

  const handleSave = async () => {
    const allClips = timelineState.sceneGroups.flatMap((g) => g.clips);
    await saveMutation.mutateAsync(allClips);
  };

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
              Timeline Editor
            </h1>
            <p className="text-sm text-surface-400">
              {timelineData?.sceneGroups.length || 0} scenes,{' '}
              {timelineData?.sceneGroups.reduce((sum, g) => sum + g.clips.length, 0) || 0} clips
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Zoom controls */}
          <div className="flex items-center gap-1 bg-surface-800 rounded-lg p-1">
            <button
              onClick={handleZoomOut}
              className="p-1.5 hover:bg-surface-700 rounded"
              title="Zoom out"
            >
              <ZoomOut className="w-4 h-4" />
            </button>
            <span className="px-2 text-sm text-surface-400">{Math.round(zoom * 100)}%</span>
            <button
              onClick={handleZoomIn}
              className="p-1.5 hover:bg-surface-700 rounded"
              title="Zoom in"
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
              title={`Undo (${historySize} steps)`}
            >
              <Undo className="w-4 h-4" />
            </button>
            <button
              onClick={redo}
              className="p-2 hover:bg-surface-800 rounded-lg transition-colors disabled:opacity-50"
              disabled={!canRedo}
              title="Redo"
            >
              <Redo className="w-4 h-4" />
            </button>
          </div>

          {/* Save */}
          {hasChanges && (
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
              {saveMutation.isPending ? 'Saving...' : 'Save'}
            </button>
          )}

          {/* Export */}
          <button
            onClick={() => navigate(`/project/${projectId}/export`)}
            className="px-4 py-2 bg-surface-700 hover:bg-surface-600 rounded-lg text-sm"
          >
            Export
          </button>
        </div>
      </div>

      {/* Preview area */}
      <div className="flex-1 flex">
        {/* Preview panel */}
        <div className="w-1/2 bg-black flex items-center justify-center border-r border-surface-800">
          {selectedClipId ? (
            <div className="text-center">
              <div className="w-80 h-48 bg-surface-900 rounded-lg flex items-center justify-center mb-2">
                <Film className="w-12 h-12 text-surface-600" />
              </div>
              <p className="text-sm text-surface-400">Preview player</p>
            </div>
          ) : (
            <div className="text-center text-surface-400">
              <Film className="w-12 h-12 mx-auto mb-2 opacity-50" />
              <p>Select a clip to preview</p>
            </div>
          )}
        </div>

        {/* Clip properties */}
        <div className="w-1/2 p-4 overflow-y-auto">
          {selectedClipId ? (
            <div className="space-y-4">
              <h3 className="font-medium">Clip Properties</h3>
              {/* Property editors would go here */}
              <div className="space-y-3">
                <div>
                  <label className="block text-sm text-surface-400 mb-1">Duration</label>
                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      step="0.1"
                      min="0.5"
                      className="flex-1 bg-surface-800 border border-surface-700 rounded px-3 py-2"
                      defaultValue="3.0"
                    />
                    <span className="text-surface-400">seconds</span>
                  </div>
                </div>
                <div>
                  <label className="block text-sm text-surface-400 mb-1">Transition</label>
                  <select className="w-full bg-surface-800 border border-surface-700 rounded px-3 py-2">
                    <option>Cut</option>
                    <option>Fade</option>
                    <option>Dissolve</option>
                    <option>Wipe</option>
                  </select>
                </div>
              </div>
            </div>
          ) : (
            <div className="h-full flex items-center justify-center text-surface-400">
              <div className="text-center">
                <Layers className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p>Select a clip to edit properties</p>
              </div>
            </div>
          )}
        </div>
      </div>

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
          <div className="relative" style={{ width: `${(timelineData?.totalDuration || 0) * 50 * zoom + 200}px` }}>
            {/* Playhead */}
            <Playhead position={currentTime} zoom={zoom} />

            {/* Scene tracks */}
            {timelineData?.sceneGroups.map((group, index) => (
              <div
                key={group.id}
                className="flex items-center border-b border-surface-800"
              >
                {/* Track header */}
                <div className="w-32 shrink-0 p-2 bg-surface-900 border-r border-surface-700">
                  <div className="text-sm font-medium truncate">
                    Scene {group.sceneNumber}
                  </div>
                  <div className="text-xs text-surface-400">
                    {group.clips.length} clips
                  </div>
                </div>

                {/* Clips */}
                <div className="flex items-center gap-1 p-2">
                  {group.clips.map((clip) => (
                    <TimelineClipComponent
                      key={clip.id}
                      clip={clip}
                      zoom={zoom}
                      isSelected={selectedClipId === clip.id}
                      onSelect={() => setSelectedClipId(clip.id)}
                      onDragStart={(e) => {
                        e.dataTransfer.setData('clipId', clip.id);
                      }}
                      onToggleLock={() => handleToggleClipLock(clip.id)}
                      onToggleVisibility={() => handleToggleClipVisibility(clip.id)}
                      onDelete={() => handleDeleteClip(clip.id)}
                    />
                  ))}
                </div>
              </div>
            ))}

            {/* Empty state */}
            {(!timelineData?.sceneGroups || timelineData.sceneGroups.length === 0) && (
              <div className="flex items-center justify-center h-full text-surface-400">
                <div className="text-center">
                  <Film className="w-12 h-12 mx-auto mb-2 opacity-50" />
                  <p>No completed shots to add to timeline</p>
                  <p className="text-sm mt-1">Generate some shots first</p>
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
    </div>
  );
}

export default TimelinePage;
