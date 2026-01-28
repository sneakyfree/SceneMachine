/**
 * DraggableAudioItem Component
 * Audio item that can be dragged onto timeline tracks
 */

import React from 'react';
import { Music, Volume2, GripVertical, Clock } from 'lucide-react';
import { cn } from '../../lib/utils';

export interface AudioItem {
    id: string;
    name: string;
    type: 'dialogue' | 'music' | 'sfx' | 'voiceover';
    duration: number;
    src: string;
    waveformUrl?: string;
}

interface DraggableAudioItemProps {
    item: AudioItem;
    onSelect?: (item: AudioItem) => void;
    isSelected?: boolean;
    compact?: boolean;
    className?: string;
}

// Format duration as MM:SS
function formatDuration(seconds: number): string {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// Type-specific colors
const TYPE_COLORS: Record<AudioItem['type'], string> = {
    dialogue: 'bg-blue-500',
    music: 'bg-purple-500',
    sfx: 'bg-green-500',
    voiceover: 'bg-amber-500',
};

const TYPE_ICONS: Record<AudioItem['type'], React.ReactNode> = {
    dialogue: <Volume2 className="w-4 h-4" />,
    music: <Music className="w-4 h-4" />,
    sfx: <Volume2 className="w-4 h-4" />,
    voiceover: <Volume2 className="w-4 h-4" />,
};

export const DraggableAudioItem: React.FC<DraggableAudioItemProps> = ({
    item,
    onSelect,
    isSelected = false,
    compact = false,
    className = '',
}) => {
    const handleDragStart = (e: React.DragEvent) => {
        // Set drag data with item info
        e.dataTransfer.setData('application/json', JSON.stringify(item));
        e.dataTransfer.setData('text/plain', item.name);
        e.dataTransfer.effectAllowed = 'copy';

        // Add visual feedback
        if (e.currentTarget instanceof HTMLElement) {
            e.currentTarget.style.opacity = '0.5';
        }
    };

    const handleDragEnd = (e: React.DragEvent) => {
        if (e.currentTarget instanceof HTMLElement) {
            e.currentTarget.style.opacity = '1';
        }
    };

    if (compact) {
        return (
            <div
                draggable
                onDragStart={handleDragStart}
                onDragEnd={handleDragEnd}
                onClick={() => onSelect?.(item)}
                className={cn(
                    'flex items-center gap-2 p-2 rounded cursor-grab active:cursor-grabbing transition-colors',
                    isSelected
                        ? 'bg-brand-500/20 border border-brand-500'
                        : 'bg-surface-800 hover:bg-surface-700 border border-transparent',
                    className
                )}
            >
                <GripVertical className="w-3 h-3 text-surface-500" />
                <div className={cn('w-5 h-5 rounded flex items-center justify-center text-white', TYPE_COLORS[item.type])}>
                    {TYPE_ICONS[item.type]}
                </div>
                <span className="text-xs truncate flex-1">{item.name}</span>
                <span className="text-xs text-surface-500">{formatDuration(item.duration)}</span>
            </div>
        );
    }

    return (
        <div
            draggable
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
            onClick={() => onSelect?.(item)}
            className={cn(
                'flex items-center gap-3 p-3 rounded-lg cursor-grab active:cursor-grabbing transition-all group',
                isSelected
                    ? 'bg-brand-500/20 border-2 border-brand-500'
                    : 'bg-surface-800 hover:bg-surface-700 border-2 border-transparent',
                className
            )}
        >
            {/* Drag handle */}
            <GripVertical className="w-4 h-4 text-surface-500 opacity-0 group-hover:opacity-100 transition-opacity" />

            {/* Type indicator */}
            <div className={cn('w-8 h-8 rounded-lg flex items-center justify-center text-white', TYPE_COLORS[item.type])}>
                {TYPE_ICONS[item.type]}
            </div>

            {/* Info */}
            <div className="flex-1 min-w-0">
                <div className="font-medium text-sm truncate">{item.name}</div>
                <div className="flex items-center gap-2 text-xs text-surface-400">
                    <span className="capitalize">{item.type}</span>
                    <span>•</span>
                    <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {formatDuration(item.duration)}
                    </span>
                </div>
            </div>
        </div>
    );
};
