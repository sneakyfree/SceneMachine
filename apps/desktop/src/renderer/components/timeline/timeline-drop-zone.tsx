/**
 * TimelineDropZone Component
 * Drop zone for receiving dragged audio items onto timeline tracks
 */

import React from 'react';
import { Plus } from 'lucide-react';
import { cn } from '../../lib/utils';
import type { AudioItem } from './draggable-audio-item';

interface TimelineDropZoneProps {
    trackType: 'dialogue' | 'music' | 'sfx' | 'voiceover' | 'any';
    trackId: string;
    onDrop: (item: AudioItem, trackId: string) => void;
    className?: string;
    children?: React.ReactNode;
}

// Map track types to accepted audio types
const TRACK_ACCEPTS: Record<TimelineDropZoneProps['trackType'], AudioItem['type'][]> = {
    dialogue: ['dialogue', 'voiceover'],
    music: ['music'],
    sfx: ['sfx'],
    voiceover: ['voiceover', 'dialogue'],
    any: ['dialogue', 'music', 'sfx', 'voiceover'],
};

export const TimelineDropZone: React.FC<TimelineDropZoneProps> = ({
    trackType,
    trackId,
    onDrop,
    className = '',
    children,
}) => {
    const [isDragOver, setIsDragOver] = React.useState(false);
    const [isValidDrop, setIsValidDrop] = React.useState(true);

    const handleDragOver = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();

        // Check if we have valid audio data
        if (e.dataTransfer.types.includes('application/json')) {
            e.dataTransfer.dropEffect = 'copy';
            setIsDragOver(true);
        }
    };

    const handleDragEnter = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragOver(true);
    };

    const handleDragLeave = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragOver(false);
        setIsValidDrop(true);
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragOver(false);

        try {
            const jsonData = e.dataTransfer.getData('application/json');
            if (!jsonData) return;

            const item: AudioItem = JSON.parse(jsonData);

            // Validate item type matches track
            const acceptedTypes = TRACK_ACCEPTS[trackType];
            if (acceptedTypes.includes(item.type)) {
                onDrop(item, trackId);
                setIsValidDrop(true);
            } else {
                setIsValidDrop(false);
                setTimeout(() => setIsValidDrop(true), 2000);
            }
        } catch (err) {
            console.error('Failed to parse drop data:', err);
        }
    };

    return (
        <div
            onDragOver={handleDragOver}
            onDragEnter={handleDragEnter}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={cn(
                'relative min-h-[40px] rounded-lg border-2 border-dashed transition-all',
                isDragOver && isValidDrop
                    ? 'border-brand-500 bg-brand-500/10'
                    : isDragOver && !isValidDrop
                        ? 'border-red-500 bg-red-500/10'
                        : 'border-transparent hover:border-surface-600',
                className
            )}
        >
            {children}

            {/* Drop indicator */}
            {isDragOver && (
                <div
                    className={cn(
                        'absolute inset-0 flex items-center justify-center rounded-lg pointer-events-none',
                        isValidDrop ? 'bg-brand-500/20' : 'bg-red-500/20'
                    )}
                >
                    <div
                        className={cn(
                            'flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium',
                            isValidDrop ? 'bg-brand-500 text-white' : 'bg-red-500 text-white'
                        )}
                    >
                        {isValidDrop ? (
                            <>
                                <Plus className="w-4 h-4" />
                                Drop to add
                            </>
                        ) : (
                            'Wrong track type'
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};
