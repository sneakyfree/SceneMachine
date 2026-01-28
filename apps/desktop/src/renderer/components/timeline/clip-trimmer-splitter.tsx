/**
 * ClipTrimmerSplitter Component
 * Handles clip trimming with handles and split-at-playhead functionality
 */

import React from 'react';
import { Scissors, Trash2, ArrowLeftRight, CornerUpLeft } from 'lucide-react';
import { cn } from '../../lib/utils';

interface TimelineClip {
    id: string;
    startTime: number;
    duration: number;
    trimStart: number;  // How much trimmed from start
    trimEnd: number;    // How much trimmed from end
    originalDuration: number;
}

interface ClipTrimmerSplitterProps {
    clip: TimelineClip;
    zoom: number;
    playheadTime: number;
    isSelected: boolean;
    onTrimStart: (id: string, delta: number) => void;
    onTrimEnd: (id: string, delta: number) => void;
    onSplit: (id: string, splitTime: number) => void;
    onDelete: (id: string) => void;
    onRippleDelete?: (id: string) => void;
    className?: string;
}

export const ClipTrimmerSplitter: React.FC<ClipTrimmerSplitterProps> = ({
    clip,
    zoom,
    playheadTime,
    isSelected,
    onTrimStart,
    onTrimEnd,
    onSplit,
    onDelete,
    onRippleDelete,
    className = '',
}) => {
    const [isDraggingStart, setIsDraggingStart] = React.useState(false);
    const [isDraggingEnd, setIsDraggingEnd] = React.useState(false);
    const [showActions, setShowActions] = React.useState(false);
    const clipRef = React.useRef<HTMLDivElement>(null);
    const dragStartRef = React.useRef<{ x: number; value: number }>({ x: 0, value: 0 });

    const clipWidth = clip.duration * 50 * zoom;
    const pixelsPerSecond = 50 * zoom;

    // Check if playhead is within this clip
    const playheadInClip = playheadTime >= clip.startTime &&
        playheadTime < clip.startTime + clip.duration;

    // Handle start trim drag
    const handleTrimStartMouseDown = (e: React.MouseEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDraggingStart(true);
        dragStartRef.current = { x: e.clientX, value: clip.trimStart };

        const handleMouseMove = (moveEvent: MouseEvent) => {
            const deltaX = moveEvent.clientX - dragStartRef.current.x;
            const deltaTime = deltaX / pixelsPerSecond;
            const newTrimStart = Math.max(0, Math.min(
                clip.originalDuration - clip.trimEnd - 0.5, // Min 0.5s clip
                dragStartRef.current.value + deltaTime
            ));
            onTrimStart(clip.id, newTrimStart);
        };

        const handleMouseUp = () => {
            setIsDraggingStart(false);
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
        };

        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('mouseup', handleMouseUp);
    };

    // Handle end trim drag
    const handleTrimEndMouseDown = (e: React.MouseEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDraggingEnd(true);
        dragStartRef.current = { x: e.clientX, value: clip.trimEnd };

        const handleMouseMove = (moveEvent: MouseEvent) => {
            const deltaX = moveEvent.clientX - dragStartRef.current.x;
            const deltaTime = -deltaX / pixelsPerSecond; // Negative because dragging right reduces trim
            const newTrimEnd = Math.max(0, Math.min(
                clip.originalDuration - clip.trimStart - 0.5,
                dragStartRef.current.value + deltaTime
            ));
            onTrimEnd(clip.id, newTrimEnd);
        };

        const handleMouseUp = () => {
            setIsDraggingEnd(false);
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
        };

        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('mouseup', handleMouseUp);
    };

    // Handle split at playhead
    const handleSplit = () => {
        if (playheadInClip) {
            onSplit(clip.id, playheadTime - clip.startTime);
        }
    };

    // Handle ripple delete
    const handleRippleDelete = () => {
        if (onRippleDelete) {
            onRippleDelete(clip.id);
        } else {
            onDelete(clip.id);
        }
    };

    return (
        <div
            ref={clipRef}
            className={cn(
                'relative group',
                className
            )}
            style={{ width: clipWidth }}
            onMouseEnter={() => setShowActions(true)}
            onMouseLeave={() => setShowActions(false)}
        >
            {/* Left trim handle */}
            <div
                className={cn(
                    'absolute left-0 top-0 bottom-0 w-3 cursor-ew-resize z-10 transition-opacity',
                    'bg-gradient-to-r from-brand-500 to-transparent',
                    isDraggingStart ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'
                )}
                onMouseDown={handleTrimStartMouseDown}
            >
                <div className="absolute left-0.5 top-1/2 -translate-y-1/2">
                    <ArrowLeftRight className="w-2 h-2 text-white" />
                </div>
            </div>

            {/* Right trim handle */}
            <div
                className={cn(
                    'absolute right-0 top-0 bottom-0 w-3 cursor-ew-resize z-10 transition-opacity',
                    'bg-gradient-to-l from-brand-500 to-transparent',
                    isDraggingEnd ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'
                )}
                onMouseDown={handleTrimEndMouseDown}
            >
                <div className="absolute right-0.5 top-1/2 -translate-y-1/2">
                    <ArrowLeftRight className="w-2 h-2 text-white" />
                </div>
            </div>

            {/* Trim indicators (showing amount trimmed) */}
            {clip.trimStart > 0 && (
                <div
                    className="absolute left-0 top-0 bottom-0 bg-red-500/30 border-r border-red-500"
                    style={{ width: clip.trimStart * pixelsPerSecond }}
                />
            )}
            {clip.trimEnd > 0 && (
                <div
                    className="absolute right-0 top-0 bottom-0 bg-red-500/30 border-l border-red-500"
                    style={{ width: clip.trimEnd * pixelsPerSecond }}
                />
            )}

            {/* Action buttons (shown on hover when selected) */}
            {isSelected && showActions && (
                <div className="absolute -top-8 left-1/2 -translate-x-1/2 flex items-center gap-1 bg-surface-800 border border-surface-700 rounded-lg shadow-lg p-1">
                    {/* Split at playhead */}
                    <button
                        onClick={handleSplit}
                        disabled={!playheadInClip}
                        className={cn(
                            'p-1.5 rounded transition-colors',
                            playheadInClip
                                ? 'hover:bg-surface-700 text-surface-300'
                                : 'text-surface-600 cursor-not-allowed'
                        )}
                        title={playheadInClip ? 'Split at playhead (S)' : 'Move playhead to clip to split'}
                    >
                        <Scissors className="w-4 h-4" />
                    </button>

                    {/* Ripple delete */}
                    <button
                        onClick={handleRippleDelete}
                        className="p-1.5 rounded hover:bg-surface-700 text-surface-300 transition-colors"
                        title="Ripple delete (close gap)"
                    >
                        <CornerUpLeft className="w-4 h-4" />
                    </button>

                    {/* Delete */}
                    <button
                        onClick={() => onDelete(clip.id)}
                        className="p-1.5 rounded hover:bg-red-500/20 text-red-400 transition-colors"
                        title="Delete (Del)"
                    >
                        <Trash2 className="w-4 h-4" />
                    </button>
                </div>
            )}

            {/* Playhead marker inside clip */}
            {playheadInClip && (
                <div
                    className="absolute top-0 bottom-0 w-0.5 bg-red-500 z-20 pointer-events-none"
                    style={{
                        left: (playheadTime - clip.startTime) * pixelsPerSecond
                    }}
                />
            )}
        </div>
    );
};

// Hook for clip trimming/splitting state management
export function useClipEditor(initialClips: TimelineClip[] = []) {
    const [clips, setClips] = React.useState<TimelineClip[]>(initialClips);
    const [undoStack, setUndoStack] = React.useState<TimelineClip[][]>([]);
    const [redoStack, setRedoStack] = React.useState<TimelineClip[][]>([]);

    const saveState = React.useCallback(() => {
        setUndoStack((prev) => [...prev.slice(-49), clips]);
        setRedoStack([]);
    }, [clips]);

    const undo = React.useCallback(() => {
        if (undoStack.length === 0) return;
        const prevState = undoStack[undoStack.length - 1];
        setRedoStack((prev) => [...prev, clips]);
        setUndoStack((prev) => prev.slice(0, -1));
        setClips(prevState);
    }, [clips, undoStack]);

    const redo = React.useCallback(() => {
        if (redoStack.length === 0) return;
        const nextState = redoStack[redoStack.length - 1];
        setUndoStack((prev) => [...prev, clips]);
        setRedoStack((prev) => prev.slice(0, -1));
        setClips(nextState);
    }, [clips, redoStack]);

    const trimStart = React.useCallback((clipId: string, newTrimStart: number) => {
        saveState();
        setClips((prev) =>
            prev.map((c) => {
                if (c.id !== clipId) return c;
                const newDuration = c.originalDuration - newTrimStart - c.trimEnd;
                return {
                    ...c,
                    trimStart: newTrimStart,
                    startTime: c.startTime + (newTrimStart - c.trimStart),
                    duration: newDuration,
                };
            })
        );
    }, [saveState]);

    const trimEnd = React.useCallback((clipId: string, newTrimEnd: number) => {
        saveState();
        setClips((prev) =>
            prev.map((c) => {
                if (c.id !== clipId) return c;
                const newDuration = c.originalDuration - c.trimStart - newTrimEnd;
                return { ...c, trimEnd: newTrimEnd, duration: newDuration };
            })
        );
    }, [saveState]);

    const splitClip = React.useCallback((clipId: string, splitTime: number) => {
        saveState();
        setClips((prev) => {
            const clipIndex = prev.findIndex((c) => c.id === clipId);
            if (clipIndex === -1) return prev;

            const clip = prev[clipIndex];
            const leftDuration = splitTime;
            const rightDuration = clip.duration - splitTime;

            if (leftDuration < 0.5 || rightDuration < 0.5) return prev; // Min duration

            const leftClip: TimelineClip = {
                ...clip,
                id: `${clip.id}-left`,
                duration: leftDuration,
                trimEnd: clip.originalDuration - clip.trimStart - leftDuration,
            };

            const rightClip: TimelineClip = {
                ...clip,
                id: `${clip.id}-right`,
                startTime: clip.startTime + leftDuration,
                duration: rightDuration,
                trimStart: clip.trimStart + leftDuration,
                trimEnd: clip.trimEnd,
            };

            return [
                ...prev.slice(0, clipIndex),
                leftClip,
                rightClip,
                ...prev.slice(clipIndex + 1),
            ];
        });
    }, [saveState]);

    const deleteClip = React.useCallback((clipId: string) => {
        saveState();
        setClips((prev) => prev.filter((c) => c.id !== clipId));
    }, [saveState]);

    const rippleDelete = React.useCallback((clipId: string) => {
        saveState();
        setClips((prev) => {
            const clipToDelete = prev.find((c) => c.id === clipId);
            if (!clipToDelete) return prev;

            const gap = clipToDelete.duration;

            return prev
                .filter((c) => c.id !== clipId)
                .map((c) => {
                    if (c.startTime > clipToDelete.startTime) {
                        return { ...c, startTime: c.startTime - gap };
                    }
                    return c;
                });
        });
    }, [saveState]);

    return {
        clips,
        setClips,
        trimStart,
        trimEnd,
        splitClip,
        deleteClip,
        rippleDelete,
        undo,
        redo,
        canUndo: undoStack.length > 0,
        canRedo: redoStack.length > 0,
    };
}
