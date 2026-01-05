/**
 * useInfiniteScroll Hook
 *
 * Trigger callback when scrolling near the bottom.
 */

import { useEffect, useRef, useCallback } from 'react';

export interface UseInfiniteScrollOptions {
  threshold?: number; // Pixels from bottom to trigger
  enabled?: boolean;
  rootMargin?: string;
}

export function useInfiniteScroll(
  callback: () => void,
  options: UseInfiniteScrollOptions = {}
) {
  const { threshold = 200, enabled = true, rootMargin = '0px' } = options;
  const observerRef = useRef<IntersectionObserver | null>(null);
  const targetRef = useRef<HTMLDivElement | null>(null);

  const handleIntersect = useCallback(
    (entries: IntersectionObserverEntry[]) => {
      const [entry] = entries;
      if (entry.isIntersecting && enabled) {
        callback();
      }
    },
    [callback, enabled]
  );

  useEffect(() => {
    if (!enabled) return;

    observerRef.current = new IntersectionObserver(handleIntersect, {
      rootMargin: `0px 0px ${threshold}px 0px`,
    });

    if (targetRef.current) {
      observerRef.current.observe(targetRef.current);
    }

    return () => {
      if (observerRef.current) {
        observerRef.current.disconnect();
      }
    };
  }, [handleIntersect, threshold, enabled]);

  // Sentinel element to place at the bottom of the list
  const SentinelComponent = useCallback(
    () => <div ref={targetRef} style={{ height: 1 }} aria-hidden="true" />,
    []
  );

  return {
    targetRef,
    Sentinel: SentinelComponent,
  };
}

export default useInfiniteScroll;
