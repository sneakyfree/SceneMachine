/**
 * TimelineTrackLayers Component
 * Visual track stacking with drag-to-reorder and visibility controls
 */

import React from 'react';
import {
  Eye,
  EyeOff,
  Lock,
  Unlock,
  GripVertical,
  Film,
  Volume2,
  Music,
  ChevronDown,
  ChevronRight,
  Plus,
  Trash2,
} from 'lucide-react';
import { cn } from '../../lib/utils';

export type TrackType = 'video' | 'audio' | 'dialogue' | 'music' | 'sfx' | 'text';

export interface Track {
  id: string;
  name: string;
  type: TrackType;
  isVisible: boolean;
  isLocked: boolean;
  isCollapsed: boolean;
  height: number;
  color: string;
  zIndex: number;
}

interface TimelineTrackLayersProps {
  tracks: Track[];
  selectedTrackId: string | null;
  onTrackSelect: (trackId: string) => void;
  onTrackUpdate: (trackId: string, updates: Partial<Track>) => void;
  onTrackReorder: (fromIndex: number, toIndex: number) => void;
  onTrackAdd?: (type: TrackType) => void;
  onTrackDelete?: (trackId: string) => void;
  className?: string;
}

// Track type configuration
const TRACK_CONFIG: Record<
  TrackType,
  { icon: React.ReactNode; defaultColor: string; label: string }
> = {
  video: { icon: <Film className="w-4 h-4" />, defaultColor: '#3b82f6', label: 'Video' },
  audio: { icon: <Volume2 className="w-4 h-4" />, defaultColor: '#22c55e', label: 'Audio' },
  dialogue: { icon: <Volume2 className="w-4 h-4" />, defaultColor: '#f59e0b', label: 'Dialogue' },
  music: { icon: <Music className="w-4 h-4" />, defaultColor: '#8b5cf6', label: 'Music' },
  sfx: { icon: <Volume2 className="w-4 h-4" />, defaultColor: '#ec4899', label: 'SFX' },
  text: { icon: <Film className="w-4 h-4" />, defaultColor: '#6b7280', label: 'Text' },
};

interface TrackRowProps {
  track: Track;
  isSelected: boolean;
  onSelect: () => void;
  onUpdate: (updates: Partial<Track>) => void;
  onDelete?: () => void;
  onDragStart: (e: React.DragEvent) => void;
  onDragOver: (e: React.DragEvent) => void;
  onDrop: (e: React.DragEvent) => void;
  isDragOver: boolean;
}

const TrackRow: React.FC<TrackRowProps> = ({
  track,
  isSelected,
  onSelect,
  onUpdate,
  onDelete,
  onDragStart,
  onDragOver,
  onDrop,
  isDragOver,
}) => {
  const config = TRACK_CONFIG[track.type];

  return (
    <div
      draggable
      onDragStart={onDragStart}
      onDragOver={onDragOver}
      onDrop={onDrop}
      onClick={onSelect}
      className={cn(
        'flex items-center gap-2 px-2 py-1.5 border-b border-surface-700 cursor-pointer transition-all',
        isSelected ? 'bg-brand-500/10 border-l-2 border-l-brand-500' : 'hover:bg-surface-800',
        isDragOver && 'border-t-2 border-t-brand-500',
        !track.isVisible && 'opacity-50'
      )}
      style={{ minHeight: track.isCollapsed ? 32 : track.height }}
    >
      {/* Drag handle */}
      <GripVertical className="w-3 h-3 text-surface-500 cursor-grab active:cursor-grabbing flex-shrink-0" />

      {/* Track color indicator */}
      <div
        className="w-2 h-full rounded-full flex-shrink-0"
        style={{ backgroundColor: track.color, minHeight: 20 }}
      />

      {/* Collapse toggle */}
      <button
        onClick={(e) => {
          e.stopPropagation();
          onUpdate({ isCollapsed: !track.isCollapsed });
        }}
        className="p-0.5 hover:bg-surface-700 rounded flex-shrink-0"
      >
        {track.isCollapsed ? (
          <ChevronRight className="w-3 h-3 text-surface-400" />
        ) : (
          <ChevronDown className="w-3 h-3 text-surface-400" />
        )}
      </button>

      {/* Track icon */}
      <div className="flex-shrink-0" style={{ color: track.color }}>
        {config.icon}
      </div>

      {/* Track name */}
      <span className="text-xs truncate flex-1">{track.name}</span>

      {/* Controls */}
      <div className="flex items-center gap-1 flex-shrink-0">
        {/* Visibility toggle */}
        <button
          onClick={(e) => {
            e.stopPropagation();
            onUpdate({ isVisible: !track.isVisible });
          }}
          className="p-1 hover:bg-surface-700 rounded"
          title={track.isVisible ? 'Hide track' : 'Show track'}
        >
          {track.isVisible ? (
            <Eye className="w-3 h-3 text-surface-400" />
          ) : (
            <EyeOff className="w-3 h-3 text-red-400" />
          )}
        </button>

        {/* Lock toggle */}
        <button
          onClick={(e) => {
            e.stopPropagation();
            onUpdate({ isLocked: !track.isLocked });
          }}
          className="p-1 hover:bg-surface-700 rounded"
          title={track.isLocked ? 'Unlock track' : 'Lock track'}
        >
          {track.isLocked ? (
            <Lock className="w-3 h-3 text-yellow-400" />
          ) : (
            <Unlock className="w-3 h-3 text-surface-400" />
          )}
        </button>

        {/* Delete button */}
        {onDelete && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
            className="p-1 hover:bg-red-500/20 rounded opacity-0 group-hover:opacity-100"
            title="Delete track"
          >
            <Trash2 className="w-3 h-3 text-red-400" />
          </button>
        )}
      </div>
    </div>
  );
};

export const TimelineTrackLayers: React.FC<TimelineTrackLayersProps> = ({
  tracks,
  selectedTrackId,
  onTrackSelect,
  onTrackUpdate,
  onTrackReorder,
  onTrackAdd,
  onTrackDelete,
  className = '',
}) => {
  const [draggedIndex, setDraggedIndex] = React.useState<number | null>(null);
  const [dragOverIndex, setDragOverIndex] = React.useState<number | null>(null);
  const [showAddMenu, setShowAddMenu] = React.useState(false);

  const handleDragStart = (index: number) => (e: React.DragEvent) => {
    setDraggedIndex(index);
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', index.toString());
  };

  const handleDragOver = (index: number) => (e: React.DragEvent) => {
    e.preventDefault();
    if (draggedIndex !== null && draggedIndex !== index) {
      setDragOverIndex(index);
    }
  };

  const handleDrop = (toIndex: number) => (e: React.DragEvent) => {
    e.preventDefault();
    if (draggedIndex !== null && draggedIndex !== toIndex) {
      onTrackReorder(draggedIndex, toIndex);
    }
    setDraggedIndex(null);
    setDragOverIndex(null);
  };

  const handleDragEnd = () => {
    setDraggedIndex(null);
    setDragOverIndex(null);
  };

  // Sort tracks by z-index (higher z-index = top of visual stack = first in list)
  const sortedTracks = [...tracks].sort((a, b) => b.zIndex - a.zIndex);

  return (
    <div className={cn('flex flex-col bg-surface-900 border-r border-surface-700', className)}>
      {/* Header */}
      <div className="flex items-center justify-between px-2 py-1.5 border-b border-surface-700 bg-surface-800">
        <span className="text-xs font-medium text-surface-400">Tracks</span>
        {onTrackAdd && (
          <div className="relative">
            <button
              onClick={() => setShowAddMenu(!showAddMenu)}
              className="p-1 hover:bg-surface-700 rounded"
              title="Add track"
            >
              <Plus className="w-3 h-3 text-surface-400" />
            </button>

            {showAddMenu && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setShowAddMenu(false)} />
                <div className="absolute right-0 top-full mt-1 bg-surface-800 border border-surface-700 rounded shadow-lg z-20 min-w-[120px]">
                  {(Object.keys(TRACK_CONFIG) as TrackType[]).map((type) => (
                    <button
                      key={type}
                      onClick={() => {
                        onTrackAdd(type);
                        setShowAddMenu(false);
                      }}
                      className="flex items-center gap-2 w-full px-3 py-1.5 text-xs hover:bg-surface-700 text-left"
                    >
                      <span style={{ color: TRACK_CONFIG[type].defaultColor }}>
                        {TRACK_CONFIG[type].icon}
                      </span>
                      {TRACK_CONFIG[type].label}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>
        )}
      </div>

      {/* Track list */}
      <div className="flex-1 overflow-y-auto" onDragEnd={handleDragEnd}>
        {sortedTracks.length > 0 ? (
          sortedTracks.map((track, index) => (
            <TrackRow
              key={track.id}
              track={track}
              isSelected={track.id === selectedTrackId}
              onSelect={() => onTrackSelect(track.id)}
              onUpdate={(updates) => onTrackUpdate(track.id, updates)}
              onDelete={onTrackDelete ? () => onTrackDelete(track.id) : undefined}
              onDragStart={handleDragStart(index)}
              onDragOver={handleDragOver(index)}
              onDrop={handleDrop(index)}
              isDragOver={dragOverIndex === index}
            />
          ))
        ) : (
          <div className="text-center py-4 text-xs text-surface-500">No tracks</div>
        )}
      </div>

      {/* Z-index info */}
      <div className="px-2 py-1 border-t border-surface-700 bg-surface-800">
        <p className="text-[10px] text-surface-500">Drag to reorder • Top = front</p>
      </div>
    </div>
  );
};

// Hook for managing track state
export function useTimelineTracks(initialTracks: Track[] = []) {
  const [tracks, setTracks] = React.useState<Track[]>(initialTracks);
  const [selectedTrackId, setSelectedTrackId] = React.useState<string | null>(null);

  const addTrack = React.useCallback(
    (type: TrackType) => {
      const config = TRACK_CONFIG[type];
      const newTrack: Track = {
        id: `track-${Date.now()}`,
        name: `${config.label} ${tracks.filter((t) => t.type === type).length + 1}`,
        type,
        isVisible: true,
        isLocked: false,
        isCollapsed: false,
        height: 60,
        color: config.defaultColor,
        zIndex: tracks.length,
      };
      setTracks((prev) => [...prev, newTrack]);
      setSelectedTrackId(newTrack.id);
    },
    [tracks]
  );

  const updateTrack = React.useCallback((trackId: string, updates: Partial<Track>) => {
    setTracks((prev) => prev.map((t) => (t.id === trackId ? { ...t, ...updates } : t)));
  }, []);

  const deleteTrack = React.useCallback(
    (trackId: string) => {
      setTracks((prev) => prev.filter((t) => t.id !== trackId));
      if (selectedTrackId === trackId) {
        setSelectedTrackId(null);
      }
    },
    [selectedTrackId]
  );

  const reorderTracks = React.useCallback((fromIndex: number, toIndex: number) => {
    setTracks((prev) => {
      const sorted = [...prev].sort((a, b) => b.zIndex - a.zIndex);
      const [moved] = sorted.splice(fromIndex, 1);
      sorted.splice(toIndex, 0, moved);

      // Update z-indices
      return sorted.map((track, index) => ({
        ...track,
        zIndex: sorted.length - 1 - index,
      }));
    });
  }, []);

  return {
    tracks,
    selectedTrackId,
    setSelectedTrackId,
    addTrack,
    updateTrack,
    deleteTrack,
    reorderTracks,
  };
}
