/**
 * TimelineMinimap Component
 * Minimap overview with viewport indicator and zoom controls
 */

import React from 'react';
import { ZoomIn, ZoomOut, Maximize2, Minus, Plus } from 'lucide-react';
import { cn } from '../../lib/utils';

interface Clip {
    id: string;
    startTime: number;
    duration: number;
    color?: string;
    trackIndex: number;
}

interface TimelineMinimapProps {
    clips: Clip[];
    totalDuration: number;
    viewportStart: number;
    viewportEnd: number;
    zoom: number;
    onViewportChange: (start: number, end: number) => void;
    onZoomChange: (zoom: number) => void;
    minZoom?: number;
    maxZoom?: number;
    trackCount?: number;
    className?: string;
}

export const TimelineMinimap: React.FC<TimelineMinimapProps> = ({
    clips,
    totalDuration,
    viewportStart,
    viewportEnd,
    zoom,
    onViewportChange,
    onZoomChange,
    minZoom = 0.25,
    maxZoom = 4,
    trackCount = 4,
    className = '',
}) => {
    const minimapRef = React.useRef<HTMLDivElement>(null);
    const [isDragging, setIsDragging] = React.useState(false);
    const [dragStart, setDragStart] = React.useState({ x: 0, start: 0 });

    // Calculate viewport dimensions
    const viewportWidth = ((viewportEnd - viewportStart) / totalDuration) * 100;
    const viewportLeft = (viewportStart / totalDuration) * 100;

    // Handle viewport dragging
    const handleMouseDown = (e: React.MouseEvent) => {
        if (!minimapRef.current) return;

        const rect = minimapRef.current.getBoundingClientRect();
        const clickX = e.clientX - rect.left;
        const clickPosition = (clickX / rect.width) * totalDuration;

        // Check if clicking on viewport indicator
        const vpStartPx = (viewportStart / totalDuration) * rect.width;
        const vpEndPx = (viewportEnd / totalDuration) * rect.width;

        if (clickX >= vpStartPx && clickX <= vpEndPx) {
            // Drag viewport
            setIsDragging(true);
            setDragStart({ x: e.clientX, start: viewportStart });
        } else {
            // Click to center viewport at that position
            const viewportDuration = viewportEnd - viewportStart;
            const newStart = Math.max(0, Math.min(
                totalDuration - viewportDuration,
                clickPosition - viewportDuration / 2
            ));
            onViewportChange(newStart, newStart + viewportDuration);
        }
    };

    const handleMouseMove = (e: React.MouseEvent) => {
        if (!isDragging || !minimapRef.current) return;

        const rect = minimapRef.current.getBoundingClientRect();
        const deltaX = e.clientX - dragStart.x;
        const deltaDuration = (deltaX / rect.width) * totalDuration;
        const viewportDuration = viewportEnd - viewportStart;

        const newStart = Math.max(0, Math.min(
            totalDuration - viewportDuration,
            dragStart.start + deltaDuration
        ));

        onViewportChange(newStart, newStart + viewportDuration);
    };

    const handleMouseUp = () => {
        setIsDragging(false);
    };

    // Zoom controls
    const handleZoomIn = () => {
        const newZoom = Math.min(maxZoom, zoom * 1.5);
        onZoomChange(newZoom);
    };

    const handleZoomOut = () => {
        const newZoom = Math.max(minZoom, zoom / 1.5);
        onZoomChange(newZoom);
    };

    const handleFitToView = () => {
        onZoomChange(1);
        onViewportChange(0, totalDuration);
    };

    // Format time as MM:SS
    const formatTime = (seconds: number): string => {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    return (
        <div className={cn('flex flex-col gap-2', className)}>
            {/* Zoom controls */}
            <div className="flex items-center justify-between px-2">
                <div className="flex items-center gap-1">
                    <button
                        onClick={handleZoomOut}
                        disabled={zoom <= minZoom}
                        className="p-1 hover:bg-surface-700 rounded disabled:opacity-50 disabled:cursor-not-allowed"
                        title="Zoom out"
                    >
                        <ZoomOut className="w-4 h-4" />
                    </button>

                    <div className="flex items-center gap-0.5 px-2 bg-surface-800 rounded">
                        <button
                            onClick={() => onZoomChange(Math.max(minZoom, zoom - 0.1))}
                            className="p-0.5 hover:bg-surface-700 rounded"
                        >
                            <Minus className="w-3 h-3" />
                        </button>
                        <span className="text-xs font-mono w-12 text-center">
                            {Math.round(zoom * 100)}%
                        </span>
                        <button
                            onClick={() => onZoomChange(Math.min(maxZoom, zoom + 0.1))}
                            className="p-0.5 hover:bg-surface-700 rounded"
                        >
                            <Plus className="w-3 h-3" />
                        </button>
                    </div>

                    <button
                        onClick={handleZoomIn}
                        disabled={zoom >= maxZoom}
                        className="p-1 hover:bg-surface-700 rounded disabled:opacity-50 disabled:cursor-not-allowed"
                        title="Zoom in"
                    >
                        <ZoomIn className="w-4 h-4" />
                    </button>
                </div>

                <button
                    onClick={handleFitToView}
                    className="p-1 hover:bg-surface-700 rounded"
                    title="Fit to window"
                >
                    <Maximize2 className="w-4 h-4" />
                </button>
            </div>

            {/* Minimap */}
            <div
                ref={minimapRef}
                className="relative h-12 bg-surface-900 border border-surface-700 rounded cursor-pointer overflow-hidden"
                onMouseDown={handleMouseDown}
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
                onMouseLeave={handleMouseUp}
            >
                {/* Clips visualization */}
                {clips.map((clip) => {
                    const left = (clip.startTime / totalDuration) * 100;
                    const width = (clip.duration / totalDuration) * 100;
                    const top = (clip.trackIndex / trackCount) * 100;
                    const height = (1 / trackCount) * 100;

                    return (
                        <div
                            key={clip.id}
                            className="absolute rounded-sm"
                            style={{
                                left: `${left}%`,
                                width: `${Math.max(1, width)}%`,
                                top: `${top}%`,
                                height: `${height}%`,
                                backgroundColor: clip.color || '#3b82f6',
                                opacity: 0.6,
                            }}
                        />
                    );
                })}

                {/* Viewport indicator */}
                <div
                    className={cn(
                        'absolute top-0 bottom-0 border-2 bg-white/10 transition-colors',
                        isDragging ? 'border-brand-400' : 'border-white/30 hover:border-white/50'
                    )}
                    style={{
                        left: `${viewportLeft}%`,
                        width: `${Math.max(2, viewportWidth)}%`,
                        cursor: isDragging ? 'grabbing' : 'grab',
                    }}
                />

                {/* Time markers */}
                <div className="absolute bottom-0 left-0 right-0 flex justify-between px-1 text-[9px] text-surface-500">
                    <span>{formatTime(0)}</span>
                    <span>{formatTime(totalDuration / 2)}</span>
                    <span>{formatTime(totalDuration)}</span>
                </div>
            </div>

            {/* Keyboard shortcut hints */}
            <div className="text-[10px] text-surface-500 text-center">
                Scroll to pan • ⌘+Scroll to zoom
            </div>
        </div>
    );
};

// Hook for timeline zoom/pan state
export function useTimelineViewport(totalDuration: number) {
    const [zoom, setZoom] = React.useState(1);
    const [viewportStart, setViewportStart] = React.useState(0);

    const viewportDuration = totalDuration / zoom;
    const viewportEnd = Math.min(totalDuration, viewportStart + viewportDuration);

    const setViewport = React.useCallback((start: number, end: number) => {
        setViewportStart(start);
        setZoom(totalDuration / (end - start));
    }, [totalDuration]);

    const pan = React.useCallback((delta: number) => {
        setViewportStart((prev) =>
            Math.max(0, Math.min(totalDuration - viewportDuration, prev + delta))
        );
    }, [totalDuration, viewportDuration]);

    const handleZoomChange = React.useCallback((newZoom: number) => {
        // Zoom centered on current viewport
        const currentCenter = viewportStart + viewportDuration / 2;
        setZoom(newZoom);
        const newDuration = totalDuration / newZoom;
        setViewportStart(Math.max(0, Math.min(
            totalDuration - newDuration,
            currentCenter - newDuration / 2
        )));
    }, [totalDuration, viewportStart, viewportDuration]);

    return {
        zoom,
        viewportStart,
        viewportEnd,
        viewportDuration,
        setZoom: handleZoomChange,
        setViewport,
        pan,
    };
}
