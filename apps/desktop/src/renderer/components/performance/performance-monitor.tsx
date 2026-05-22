/**
 * Performance Monitoring
 * Core Web Vitals tracking and performance insights
 */

import React from 'react';
import { cn } from '../../lib/utils';

// Core Web Vitals types
export interface WebVitals {
  lcp: number | null; // Largest Contentful Paint
  fid: number | null; // First Input Delay
  cls: number | null; // Cumulative Layout Shift
  fcp: number | null; // First Contentful Paint
  ttfb: number | null; // Time to First Byte
}

// Performance metric thresholds (in ms, except CLS)
const THRESHOLDS = {
  lcp: { good: 2500, poor: 4000 },
  fid: { good: 100, poor: 300 },
  cls: { good: 0.1, poor: 0.25 },
  fcp: { good: 1800, poor: 3000 },
  ttfb: { good: 800, poor: 1800 },
};

// Rating for metrics
type Rating = 'good' | 'needs-improvement' | 'poor';

function getMetricRating(name: keyof WebVitals, value: number): Rating {
  const threshold = THRESHOLDS[name];
  if (value <= threshold.good) return 'good';
  if (value <= threshold.poor) return 'needs-improvement';
  return 'poor';
}

// Hook to track Core Web Vitals
export function useWebVitals(onReport?: (vitals: WebVitals) => void) {
  const [vitals, setVitals] = React.useState<WebVitals>({
    lcp: null,
    fid: null,
    cls: null,
    fcp: null,
    ttfb: null,
  });

  React.useEffect(() => {
    // LCP - Largest Contentful Paint
    const lcpObserver = new PerformanceObserver((list) => {
      const entries = list.getEntries();
      const lastEntry = entries[entries.length - 1];
      setVitals((v) => ({ ...v, lcp: lastEntry.startTime }));
    });

    // CLS - Cumulative Layout Shift
    let clsValue = 0;
    const clsObserver = new PerformanceObserver((list) => {
      for (const entry of list.getEntries() as any[]) {
        if (!entry.hadRecentInput) {
          clsValue += entry.value;
          setVitals((v) => ({ ...v, cls: clsValue }));
        }
      }
    });

    // FID - First Input Delay
    const fidObserver = new PerformanceObserver((list) => {
      const entry = list.getEntries()[0] as any;
      setVitals((v) => ({ ...v, fid: entry.processingStart - entry.startTime }));
    });

    // FCP - First Contentful Paint
    const fcpObserver = new PerformanceObserver((list) => {
      const entry = list.getEntries()[0];
      setVitals((v) => ({ ...v, fcp: entry.startTime }));
    });

    try {
      lcpObserver.observe({ type: 'largest-contentful-paint', buffered: true });
      clsObserver.observe({ type: 'layout-shift', buffered: true });
      fidObserver.observe({ type: 'first-input', buffered: true });
      fcpObserver.observe({ type: 'paint', buffered: true });
    } catch (e) {
      console.warn('Performance Observer not supported:', e);
    }

    // TTFB - Time to First Byte
    const navEntry = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
    if (navEntry) {
      setVitals((v) => ({ ...v, ttfb: navEntry.responseStart - navEntry.requestStart }));
    }

    return () => {
      lcpObserver.disconnect();
      clsObserver.disconnect();
      fidObserver.disconnect();
      fcpObserver.disconnect();
    };
  }, []);

  // Report vitals when they change
  React.useEffect(() => {
    if (onReport && Object.values(vitals).some((v) => v !== null)) {
      onReport(vitals);
    }
  }, [vitals, onReport]);

  return vitals;
}

// Performance Monitor Display Component
export const PerformanceMonitor: React.FC<{
  className?: string;
  compact?: boolean;
}> = ({ className, compact = false }) => {
  const vitals = useWebVitals();
  const [fps, setFps] = React.useState(60);
  const [memoryUsage, setMemoryUsage] = React.useState<number | null>(null);

  // FPS tracking
  React.useEffect(() => {
    let frameCount = 0;
    let lastTime = performance.now();
    let animationId: number;

    const measureFps = () => {
      frameCount++;
      const currentTime = performance.now();

      if (currentTime - lastTime >= 1000) {
        setFps(frameCount);
        frameCount = 0;
        lastTime = currentTime;
      }

      animationId = requestAnimationFrame(measureFps);
    };

    animationId = requestAnimationFrame(measureFps);
    return () => cancelAnimationFrame(animationId);
  }, []);

  // Memory tracking
  React.useEffect(() => {
    const updateMemory = () => {
      const memory = (performance as any).memory;
      if (memory) {
        setMemoryUsage(memory.usedJSHeapSize / (1024 * 1024));
      }
    };

    updateMemory();
    const interval = setInterval(updateMemory, 1000);
    return () => clearInterval(interval);
  }, []);

  const formatValue = (name: keyof WebVitals, value: number | null): string => {
    if (value === null) return '--';
    if (name === 'cls') return value.toFixed(3);
    return `${Math.round(value)}ms`;
  };

  const getRatingColor = (rating: Rating): string => {
    switch (rating) {
      case 'good':
        return 'text-green-400';
      case 'needs-improvement':
        return 'text-yellow-400';
      case 'poor':
        return 'text-red-400';
    }
  };

  if (compact) {
    return (
      <div className={cn('flex items-center gap-2 text-xs font-mono', className)}>
        <span
          className={fps >= 55 ? 'text-green-400' : fps >= 30 ? 'text-yellow-400' : 'text-red-400'}
        >
          {fps} FPS
        </span>
        {memoryUsage && <span className="text-surface-400">{memoryUsage.toFixed(0)} MB</span>}
      </div>
    );
  }

  return (
    <div className={cn('bg-surface-900 rounded-lg p-4', className)}>
      <h3 className="text-sm font-medium mb-3">Performance</h3>

      <div className="grid grid-cols-2 gap-3">
        {/* FPS */}
        <div className="bg-surface-800 rounded p-2">
          <div className="text-xs text-surface-400">FPS</div>
          <div
            className={cn(
              'text-lg font-mono',
              fps >= 55 ? 'text-green-400' : fps >= 30 ? 'text-yellow-400' : 'text-red-400'
            )}
          >
            {fps}
          </div>
        </div>

        {/* Memory */}
        <div className="bg-surface-800 rounded p-2">
          <div className="text-xs text-surface-400">Memory</div>
          <div className="text-lg font-mono">
            {memoryUsage ? `${memoryUsage.toFixed(0)} MB` : '--'}
          </div>
        </div>

        {/* LCP */}
        <div className="bg-surface-800 rounded p-2">
          <div className="text-xs text-surface-400">LCP</div>
          <div
            className={cn(
              'text-lg font-mono',
              vitals.lcp ? getRatingColor(getMetricRating('lcp', vitals.lcp)) : ''
            )}
          >
            {formatValue('lcp', vitals.lcp)}
          </div>
        </div>

        {/* FID */}
        <div className="bg-surface-800 rounded p-2">
          <div className="text-xs text-surface-400">FID</div>
          <div
            className={cn(
              'text-lg font-mono',
              vitals.fid ? getRatingColor(getMetricRating('fid', vitals.fid)) : ''
            )}
          >
            {formatValue('fid', vitals.fid)}
          </div>
        </div>

        {/* CLS */}
        <div className="bg-surface-800 rounded p-2">
          <div className="text-xs text-surface-400">CLS</div>
          <div
            className={cn(
              'text-lg font-mono',
              vitals.cls !== null ? getRatingColor(getMetricRating('cls', vitals.cls)) : ''
            )}
          >
            {formatValue('cls', vitals.cls)}
          </div>
        </div>

        {/* TTFB */}
        <div className="bg-surface-800 rounded p-2">
          <div className="text-xs text-surface-400">TTFB</div>
          <div
            className={cn(
              'text-lg font-mono',
              vitals.ttfb ? getRatingColor(getMetricRating('ttfb', vitals.ttfb)) : ''
            )}
          >
            {formatValue('ttfb', vitals.ttfb)}
          </div>
        </div>
      </div>
    </div>
  );
};

// Lazy loading wrapper with Suspense
export const LazyComponent: React.FC<{
  children: React.ReactNode;
  fallback?: React.ReactNode;
}> = ({ children, fallback }) => (
  <React.Suspense
    fallback={fallback || <div className="animate-pulse bg-surface-700 rounded h-32" />}
  >
    {children}
  </React.Suspense>
);

// Image lazy loading hook
export function useLazyImage(src: string) {
  const [loaded, setLoaded] = React.useState(false);
  const [error, setError] = React.useState(false);
  const imgRef = React.useRef<HTMLImageElement | null>(null);

  React.useEffect(() => {
    const img = new Image();
    img.src = src;
    img.onload = () => setLoaded(true);
    img.onerror = () => setError(true);
    imgRef.current = img;

    return () => {
      img.onload = null;
      img.onerror = null;
    };
  }, [src]);

  return { loaded, error, imgRef };
}

// Debounce hook for performance
export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = React.useState(value);

  React.useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);

  return debouncedValue;
}

// Throttle hook for performance
export function useThrottle<T>(value: T, limit: number): T {
  const [throttledValue, setThrottledValue] = React.useState(value);
  const lastRan = React.useRef(Date.now());

  React.useEffect(() => {
    const handler = setTimeout(
      () => {
        if (Date.now() - lastRan.current >= limit) {
          setThrottledValue(value);
          lastRan.current = Date.now();
        }
      },
      limit - (Date.now() - lastRan.current)
    );

    return () => clearTimeout(handler);
  }, [value, limit]);

  return throttledValue;
}
