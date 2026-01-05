/**
 * React hooks for responsive design.
 */

import { useState, useEffect, useCallback } from 'react';
import {
  breakpoints,
  Breakpoint,
  getCurrentBreakpoint,
  isTouchDevice,
  isMobile,
  isTablet,
  isDesktop,
  isLandscape,
  prefersReducedMotion,
  getOptimalVideoQuality,
} from '../utils/responsive';

/**
 * Hook to track media query matches
 */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.matchMedia(query).matches;
  });

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const mediaQuery = window.matchMedia(query);
    setMatches(mediaQuery.matches);

    const handler = (event: MediaQueryListEvent) => {
      setMatches(event.matches);
    };

    // Modern browsers
    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', handler);
      return () => mediaQuery.removeEventListener('change', handler);
    }
    // Legacy browsers
    mediaQuery.addListener(handler);
    return () => mediaQuery.removeListener(handler);
  }, [query]);

  return matches;
}

/**
 * Hook to track current breakpoint
 */
export function useBreakpoint(): Breakpoint {
  const [breakpoint, setBreakpoint] = useState<Breakpoint>(() =>
    getCurrentBreakpoint()
  );

  useEffect(() => {
    const handleResize = () => {
      setBreakpoint(getCurrentBreakpoint());
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return breakpoint;
}

/**
 * Hook to check if viewport is at or above a breakpoint
 */
export function useBreakpointUp(breakpoint: Breakpoint): boolean {
  return useMediaQuery(`(min-width: ${breakpoints[breakpoint]}px)`);
}

/**
 * Hook to check if viewport is below a breakpoint
 */
export function useBreakpointDown(breakpoint: Breakpoint): boolean {
  return useMediaQuery(`(max-width: ${breakpoints[breakpoint] - 1}px)`);
}

/**
 * Hook to detect touch device
 */
export function useIsTouchDevice(): boolean {
  const [isTouch, setIsTouch] = useState(() => isTouchDevice());

  useEffect(() => {
    // Re-check on first interaction
    const handler = () => {
      setIsTouch(isTouchDevice());
    };

    window.addEventListener('touchstart', handler, { once: true });
    return () => window.removeEventListener('touchstart', handler);
  }, []);

  return isTouch;
}

/**
 * Hook to detect mobile device
 */
export function useIsMobile(): boolean {
  const isTouch = useIsTouchDevice();
  const isMd = useBreakpointUp('md');
  return isTouch && !isMd;
}

/**
 * Hook to detect tablet device
 */
export function useIsTablet(): boolean {
  const isTouch = useIsTouchDevice();
  const isMd = useBreakpointUp('md');
  const isLg = useBreakpointUp('lg');
  return isTouch && isMd && !isLg;
}

/**
 * Hook to detect desktop device
 */
export function useIsDesktop(): boolean {
  const isTouch = useIsTouchDevice();
  const isLg = useBreakpointUp('lg');
  return !isTouch || isLg;
}

/**
 * Hook to detect orientation
 */
export function useOrientation(): 'portrait' | 'landscape' {
  const isLandscapeMode = useMediaQuery('(orientation: landscape)');
  return isLandscapeMode ? 'landscape' : 'portrait';
}

/**
 * Hook to detect reduced motion preference
 */
export function usePrefersReducedMotion(): boolean {
  return useMediaQuery('(prefers-reduced-motion: reduce)');
}

/**
 * Hook to detect dark mode preference
 */
export function usePrefersDarkMode(): boolean {
  return useMediaQuery('(prefers-color-scheme: dark)');
}

/**
 * Hook to get optimal video quality
 */
export function useOptimalVideoQuality(): '360p' | '480p' | '720p' | '1080p' | '4k' {
  const [quality, setQuality] = useState<'360p' | '480p' | '720p' | '1080p' | '4k'>(
    () => getOptimalVideoQuality()
  );

  useEffect(() => {
    const handleChange = () => {
      setQuality(getOptimalVideoQuality());
    };

    window.addEventListener('resize', handleChange);

    // Listen for connection changes if available
    const connection = (navigator as any).connection;
    if (connection) {
      connection.addEventListener('change', handleChange);
    }

    return () => {
      window.removeEventListener('resize', handleChange);
      if (connection) {
        connection.removeEventListener('change', handleChange);
      }
    };
  }, []);

  return quality;
}

/**
 * Hook to track viewport dimensions
 */
export function useViewportSize(): { width: number; height: number } {
  const [size, setSize] = useState(() => ({
    width: typeof window !== 'undefined' ? window.innerWidth : 0,
    height: typeof window !== 'undefined' ? window.innerHeight : 0,
  }));

  useEffect(() => {
    const handleResize = () => {
      setSize({
        width: window.innerWidth,
        height: window.innerHeight,
      });
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return size;
}

/**
 * Hook to detect online/offline status
 */
export function useOnlineStatus(): boolean {
  const [isOnline, setIsOnline] = useState(() =>
    typeof navigator !== 'undefined' ? navigator.onLine : true
  );

  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  return isOnline;
}

/**
 * Hook to detect network connection info
 */
export function useNetworkInfo(): {
  effectiveType: '4g' | '3g' | '2g' | 'slow-2g' | undefined;
  downlink: number | undefined;
  rtt: number | undefined;
  saveData: boolean;
} {
  const [info, setInfo] = useState(() => {
    const connection = typeof navigator !== 'undefined'
      ? (navigator as any).connection
      : null;

    return {
      effectiveType: connection?.effectiveType,
      downlink: connection?.downlink,
      rtt: connection?.rtt,
      saveData: connection?.saveData || false,
    };
  });

  useEffect(() => {
    const connection = (navigator as any).connection;
    if (!connection) return;

    const handleChange = () => {
      setInfo({
        effectiveType: connection.effectiveType,
        downlink: connection.downlink,
        rtt: connection.rtt,
        saveData: connection.saveData || false,
      });
    };

    connection.addEventListener('change', handleChange);
    return () => connection.removeEventListener('change', handleChange);
  }, []);

  return info;
}
