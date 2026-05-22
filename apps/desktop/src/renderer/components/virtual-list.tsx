/**
 * Virtual List component for efficient rendering of large lists.
 *
 * Renders only visible items plus a buffer, dramatically improving
 * performance for lists with thousands of items.
 */

import React, {
  useRef,
  useState,
  useCallback,
  useEffect,
  useMemo,
  forwardRef,
  useImperativeHandle,
} from 'react';
import { cn } from '../lib/utils';

// ============================================================================
// Types
// ============================================================================

interface VirtualListProps<T> {
  /** Array of items to render */
  items: T[];
  /** Height of each item in pixels (for fixed height) or estimation function */
  itemHeight: number | ((index: number, item: T) => number);
  /** Render function for each item */
  renderItem: (item: T, index: number, style: React.CSSProperties) => React.ReactNode;
  /** Height of the container */
  height: number;
  /** Width of the container (optional, defaults to 100%) */
  width?: number | string;
  /** Number of items to render above/below visible area */
  overscan?: number;
  /** Key extractor for React keys */
  getItemKey?: (item: T, index: number) => string | number;
  /** Callback when scroll position changes */
  onScroll?: (scrollTop: number, scrollDirection: 'up' | 'down') => void;
  /** Callback when visible items change */
  onVisibleRangeChange?: (startIndex: number, endIndex: number) => void;
  /** Additional class name for container */
  className?: string;
  /** Whether to show scrollbar */
  showScrollbar?: boolean;
  /** Scroll to index on mount */
  initialScrollIndex?: number;
  /** Enable smooth scrolling */
  smoothScroll?: boolean;
}

export interface VirtualListHandle {
  /** Scroll to a specific index */
  scrollToIndex: (index: number, align?: 'start' | 'center' | 'end') => void;
  /** Scroll to a specific offset */
  scrollToOffset: (offset: number) => void;
  /** Get current scroll offset */
  getScrollOffset: () => number;
  /** Get visible range */
  getVisibleRange: () => { start: number; end: number };
  /** Force re-render of all items */
  forceUpdate: () => void;
}

// ============================================================================
// Fixed Height Virtual List
// ============================================================================

function VirtualListInner<T>(
  props: VirtualListProps<T>,
  ref: React.ForwardedRef<VirtualListHandle>
) {
  const {
    items,
    itemHeight,
    renderItem,
    height,
    width = '100%',
    overscan = 3,
    getItemKey,
    onScroll,
    onVisibleRangeChange,
    className,
    showScrollbar = true,
    initialScrollIndex,
    smoothScroll = false,
  } = props;

  const containerRef = useRef<HTMLDivElement>(null);
  const [scrollTop, setScrollTop] = useState(0);
  const [, setForceRender] = useState(0);
  const lastScrollTop = useRef(0);

  // Calculate item height (fixed or dynamic)
  const getHeight = useCallback(
    (index: number): number => {
      if (typeof itemHeight === 'number') {
        return itemHeight;
      }
      return itemHeight(index, items[index]);
    },
    [itemHeight, items]
  );

  // Calculate total height and item positions
  const { totalHeight, itemPositions } = useMemo(() => {
    const positions: number[] = [];
    let total = 0;

    for (let i = 0; i < items.length; i++) {
      positions.push(total);
      total += getHeight(i);
    }

    return { totalHeight: total, itemPositions: positions };
  }, [items.length, getHeight]);

  // Find visible range
  const visibleRange = useMemo(() => {
    if (typeof itemHeight === 'number') {
      // Optimized path for fixed height
      const start = Math.floor(scrollTop / itemHeight);
      const visibleCount = Math.ceil(height / itemHeight);
      const end = Math.min(start + visibleCount, items.length);

      return {
        start: Math.max(0, start - overscan),
        end: Math.min(items.length, end + overscan),
      };
    }

    // Binary search for variable height
    let start = 0;
    let end = items.length;

    // Find start index (first item that ends after scrollTop)
    for (let i = 0; i < items.length; i++) {
      if (itemPositions[i] + getHeight(i) > scrollTop) {
        start = i;
        break;
      }
    }

    // Find end index (first item that starts after scrollTop + height)
    for (let i = start; i < items.length; i++) {
      if (itemPositions[i] > scrollTop + height) {
        end = i;
        break;
      }
    }

    return {
      start: Math.max(0, start - overscan),
      end: Math.min(items.length, end + overscan),
    };
  }, [scrollTop, height, items.length, itemHeight, itemPositions, getHeight, overscan]);

  // Notify visible range changes
  useEffect(() => {
    onVisibleRangeChange?.(visibleRange.start, visibleRange.end);
  }, [visibleRange.start, visibleRange.end, onVisibleRangeChange]);

  // Handle scroll
  const handleScroll = useCallback(
    (e: React.UIEvent<HTMLDivElement>) => {
      const newScrollTop = e.currentTarget.scrollTop;
      setScrollTop(newScrollTop);

      const direction = newScrollTop > lastScrollTop.current ? 'down' : 'up';
      lastScrollTop.current = newScrollTop;

      onScroll?.(newScrollTop, direction);
    },
    [onScroll]
  );

  // Scroll to index
  const scrollToIndex = useCallback(
    (index: number, align: 'start' | 'center' | 'end' = 'start') => {
      if (!containerRef.current || index < 0 || index >= items.length) return;

      let targetOffset = typeof itemHeight === 'number' ? index * itemHeight : itemPositions[index];

      if (align === 'center') {
        const itemH = getHeight(index);
        targetOffset = targetOffset - height / 2 + itemH / 2;
      } else if (align === 'end') {
        const itemH = getHeight(index);
        targetOffset = targetOffset - height + itemH;
      }

      targetOffset = Math.max(0, Math.min(targetOffset, totalHeight - height));

      containerRef.current.scrollTo({
        top: targetOffset,
        behavior: smoothScroll ? 'smooth' : 'auto',
      });
    },
    [items.length, itemHeight, itemPositions, getHeight, height, totalHeight, smoothScroll]
  );

  // Scroll to offset
  const scrollToOffset = useCallback(
    (offset: number) => {
      if (!containerRef.current) return;
      containerRef.current.scrollTo({
        top: Math.max(0, Math.min(offset, totalHeight - height)),
        behavior: smoothScroll ? 'smooth' : 'auto',
      });
    },
    [totalHeight, height, smoothScroll]
  );

  // Expose methods via ref
  useImperativeHandle(
    ref,
    () => ({
      scrollToIndex,
      scrollToOffset,
      getScrollOffset: () => scrollTop,
      getVisibleRange: () => visibleRange,
      forceUpdate: () => setForceRender((n) => n + 1),
    }),
    [scrollToIndex, scrollToOffset, scrollTop, visibleRange]
  );

  // Initial scroll
  useEffect(() => {
    if (initialScrollIndex !== undefined) {
      scrollToIndex(initialScrollIndex);
    }
  }, []);

  // Render visible items
  const visibleItems = useMemo(() => {
    const result: React.ReactNode[] = [];

    for (let i = visibleRange.start; i < visibleRange.end; i++) {
      const item = items[i];
      const itemH = getHeight(i);
      const top = typeof itemHeight === 'number' ? i * itemHeight : itemPositions[i];

      const style: React.CSSProperties = {
        position: 'absolute',
        top,
        left: 0,
        right: 0,
        height: itemH,
      };

      const key = getItemKey ? getItemKey(item, i) : i;
      result.push(
        <div key={key} style={style}>
          {renderItem(item, i, style)}
        </div>
      );
    }

    return result;
  }, [visibleRange, items, getHeight, itemHeight, itemPositions, getItemKey, renderItem]);

  return (
    <div
      ref={containerRef}
      className={cn('relative overflow-auto', !showScrollbar && 'scrollbar-hide', className)}
      style={{ height, width }}
      onScroll={handleScroll}
    >
      <div
        style={{
          height: totalHeight,
          width: '100%',
          position: 'relative',
        }}
      >
        {visibleItems}
      </div>
    </div>
  );
}

// Export with forwardRef
export const VirtualList = forwardRef(VirtualListInner) as <T>(
  props: VirtualListProps<T> & { ref?: React.ForwardedRef<VirtualListHandle> }
) => React.ReactElement;

// ============================================================================
// Virtual Grid (for 2D layouts)
// ============================================================================

interface VirtualGridProps<T> {
  /** Array of items to render */
  items: T[];
  /** Number of columns */
  columns: number;
  /** Height of each row */
  rowHeight: number;
  /** Width of each column (auto-calculated if not provided) */
  columnWidth?: number;
  /** Gap between items */
  gap?: number;
  /** Render function for each item */
  renderItem: (item: T, index: number, style: React.CSSProperties) => React.ReactNode;
  /** Height of the container */
  height: number;
  /** Width of the container */
  width?: number | string;
  /** Number of rows to render above/below visible area */
  overscan?: number;
  /** Key extractor */
  getItemKey?: (item: T, index: number) => string | number;
  /** Additional class name */
  className?: string;
}

export function VirtualGrid<T>({
  items,
  columns,
  rowHeight,
  columnWidth,
  gap = 0,
  renderItem,
  height,
  width = '100%',
  overscan = 2,
  getItemKey,
  className,
}: VirtualGridProps<T>): React.ReactElement {
  const containerRef = useRef<HTMLDivElement>(null);
  const [scrollTop, setScrollTop] = useState(0);
  const [containerWidth, setContainerWidth] = useState(0);

  // Calculate dimensions
  const rows = Math.ceil(items.length / columns);
  const totalHeight = rows * (rowHeight + gap) - gap;
  const effectiveColumnWidth = columnWidth || (containerWidth - gap * (columns - 1)) / columns;

  // Observe container width
  useEffect(() => {
    if (!containerRef.current) return;

    const observer = new ResizeObserver((entries) => {
      setContainerWidth(entries[0].contentRect.width);
    });

    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  // Calculate visible rows
  const startRow = Math.floor(scrollTop / (rowHeight + gap));
  const visibleRows = Math.ceil(height / (rowHeight + gap));
  const endRow = Math.min(startRow + visibleRows + 1, rows);

  const renderStart = Math.max(0, startRow - overscan);
  const renderEnd = Math.min(rows, endRow + overscan);

  // Handle scroll
  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    setScrollTop(e.currentTarget.scrollTop);
  }, []);

  // Render visible items
  const visibleItems = useMemo(() => {
    const result: React.ReactNode[] = [];

    for (let row = renderStart; row < renderEnd; row++) {
      for (let col = 0; col < columns; col++) {
        const index = row * columns + col;
        if (index >= items.length) break;

        const item = items[index];
        const top = row * (rowHeight + gap);
        const left = col * (effectiveColumnWidth + gap);

        const style: React.CSSProperties = {
          position: 'absolute',
          top,
          left,
          width: effectiveColumnWidth,
          height: rowHeight,
        };

        const key = getItemKey ? getItemKey(item, index) : index;
        result.push(
          <div key={key} style={style}>
            {renderItem(item, index, style)}
          </div>
        );
      }
    }

    return result;
  }, [
    renderStart,
    renderEnd,
    columns,
    items,
    rowHeight,
    gap,
    effectiveColumnWidth,
    getItemKey,
    renderItem,
  ]);

  return (
    <div
      ref={containerRef}
      className={cn('relative overflow-auto', className)}
      style={{ height, width }}
      onScroll={handleScroll}
    >
      <div
        style={{
          height: totalHeight,
          width: '100%',
          position: 'relative',
        }}
      >
        {visibleItems}
      </div>
    </div>
  );
}

// ============================================================================
// Infinite Scroll Wrapper
// ============================================================================

interface InfiniteScrollProps<T> extends Omit<VirtualListProps<T>, 'height'> {
  /** Whether more items are being loaded */
  isLoading?: boolean;
  /** Whether there are more items to load */
  hasMore?: boolean;
  /** Callback to load more items */
  onLoadMore?: () => void;
  /** Threshold in pixels from bottom to trigger load */
  loadMoreThreshold?: number;
  /** Height of the container */
  height: number;
  /** Loading indicator component */
  loadingComponent?: React.ReactNode;
  /** End of list component */
  endComponent?: React.ReactNode;
}

export function InfiniteScrollList<T>({
  isLoading = false,
  hasMore = false,
  onLoadMore,
  loadMoreThreshold = 200,
  height,
  loadingComponent,
  endComponent,
  ...listProps
}: InfiniteScrollProps<T>): React.ReactElement {
  const listRef = useRef<VirtualListHandle>(null);

  const handleScroll = useCallback(
    (scrollTop: number) => {
      if (isLoading || !hasMore || !onLoadMore) return;

      const { items, itemHeight } = listProps;
      const totalHeight =
        typeof itemHeight === 'number'
          ? items.length * itemHeight
          : items.reduce(
              (sum, _, i) => sum + (typeof itemHeight === 'function' ? itemHeight(i, items[i]) : 0),
              0
            );

      if (scrollTop + height + loadMoreThreshold >= totalHeight) {
        onLoadMore();
      }

      listProps.onScroll?.(scrollTop, scrollTop > 0 ? 'down' : 'up');
    },
    [isLoading, hasMore, onLoadMore, loadMoreThreshold, height, listProps]
  );

  // Append loading/end items
  const itemsWithFooter = useMemo(() => {
    const footerItems: T[] = [...listProps.items];
    return footerItems;
  }, [listProps.items]);

  return (
    <div className="relative">
      <VirtualList
        {...listProps}
        ref={listRef}
        items={itemsWithFooter}
        height={height}
        onScroll={handleScroll}
      />
      {isLoading && (
        <div className="absolute bottom-0 left-0 right-0 flex justify-center py-4 bg-gradient-to-t from-gray-900/90 to-transparent">
          {loadingComponent || (
            <div className="flex items-center gap-2 text-gray-400">
              <div className="w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" />
              Loading more...
            </div>
          )}
        </div>
      )}
      {!hasMore && !isLoading && endComponent}
    </div>
  );
}

export default VirtualList;
