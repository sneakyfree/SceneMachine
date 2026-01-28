/**
 * Virtual Scrolling Component
 * Efficient rendering for long lists with windowing
 */

import React from 'react';
import { cn } from '../../lib/utils';

interface VirtualListProps<T> {
    items: T[];
    itemHeight: number;
    containerHeight: number;
    renderItem: (item: T, index: number) => React.ReactNode;
    overscan?: number;
    className?: string;
    onLoadMore?: () => void;
    loadMoreThreshold?: number;
}

export function VirtualList<T>({
    items,
    itemHeight,
    containerHeight,
    renderItem,
    overscan = 3,
    className,
    onLoadMore,
    loadMoreThreshold = 5,
}: VirtualListProps<T>) {
    const [scrollTop, setScrollTop] = React.useState(0);
    const containerRef = React.useRef<HTMLDivElement>(null);

    // Calculate visible range
    const totalHeight = items.length * itemHeight;
    const startIndex = Math.max(0, Math.floor(scrollTop / itemHeight) - overscan);
    const endIndex = Math.min(
        items.length - 1,
        Math.ceil((scrollTop + containerHeight) / itemHeight) + overscan
    );

    // Get visible items
    const visibleItems = items.slice(startIndex, endIndex + 1);

    // Handle scroll
    const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
        const target = e.currentTarget;
        setScrollTop(target.scrollTop);

        // Check if we need to load more
        if (onLoadMore) {
            const remainingItems = items.length - endIndex;
            if (remainingItems <= loadMoreThreshold) {
                onLoadMore();
            }
        }
    };

    return (
        <div
            ref={containerRef}
            className={cn('overflow-auto', className)}
            style={{ height: containerHeight }}
            onScroll={handleScroll}
        >
            <div style={{ height: totalHeight, position: 'relative' }}>
                {visibleItems.map((item, i) => (
                    <div
                        key={startIndex + i}
                        style={{
                            position: 'absolute',
                            top: (startIndex + i) * itemHeight,
                            left: 0,
                            right: 0,
                            height: itemHeight,
                        }}
                    >
                        {renderItem(item, startIndex + i)}
                    </div>
                ))}
            </div>
        </div>
    );
}

// Virtual grid for 2D layouts
interface VirtualGridProps<T> {
    items: T[];
    itemWidth: number;
    itemHeight: number;
    containerWidth: number;
    containerHeight: number;
    renderItem: (item: T, index: number) => React.ReactNode;
    gap?: number;
    overscan?: number;
    className?: string;
}

export function VirtualGrid<T>({
    items,
    itemWidth,
    itemHeight,
    containerWidth,
    containerHeight,
    renderItem,
    gap = 8,
    overscan = 2,
    className,
}: VirtualGridProps<T>) {
    const [scrollTop, setScrollTop] = React.useState(0);

    // Calculate columns and rows
    const columns = Math.max(1, Math.floor((containerWidth + gap) / (itemWidth + gap)));
    const rows = Math.ceil(items.length / columns);
    const totalHeight = rows * (itemHeight + gap) - gap;

    // Calculate visible range
    const startRow = Math.max(0, Math.floor(scrollTop / (itemHeight + gap)) - overscan);
    const endRow = Math.min(
        rows - 1,
        Math.ceil((scrollTop + containerHeight) / (itemHeight + gap)) + overscan
    );

    const startIndex = startRow * columns;
    const endIndex = Math.min(items.length - 1, (endRow + 1) * columns - 1);

    // Get visible items
    const visibleItems = items.slice(startIndex, endIndex + 1);

    return (
        <div
            className={cn('overflow-auto', className)}
            style={{ height: containerHeight }}
            onScroll={(e) => setScrollTop(e.currentTarget.scrollTop)}
        >
            <div style={{ height: totalHeight, position: 'relative' }}>
                {visibleItems.map((item, i) => {
                    const index = startIndex + i;
                    const row = Math.floor(index / columns);
                    const col = index % columns;

                    return (
                        <div
                            key={index}
                            style={{
                                position: 'absolute',
                                top: row * (itemHeight + gap),
                                left: col * (itemWidth + gap),
                                width: itemWidth,
                                height: itemHeight,
                            }}
                        >
                            {renderItem(item, index)}
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

// Hook for virtualization state
export function useVirtualization(itemCount: number, itemHeight: number) {
    const [scrollTop, setScrollTop] = React.useState(0);
    const containerRef = React.useRef<HTMLDivElement>(null);

    const scrollTo = React.useCallback((index: number, align: 'start' | 'center' | 'end' = 'start') => {
        if (!containerRef.current) return;

        const containerHeight = containerRef.current.clientHeight;
        let offset = index * itemHeight;

        if (align === 'center') {
            offset -= containerHeight / 2 - itemHeight / 2;
        } else if (align === 'end') {
            offset -= containerHeight - itemHeight;
        }

        containerRef.current.scrollTop = Math.max(0, offset);
    }, [itemHeight]);

    return { scrollTop, setScrollTop, containerRef, scrollTo };
}
