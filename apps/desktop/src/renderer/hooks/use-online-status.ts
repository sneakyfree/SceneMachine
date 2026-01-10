/**
 * Online Status Hook
 *
 * Detects online/offline status using browser events and API ping.
 * Provides real-time connectivity state for offline support.
 */

import { useState, useEffect, useCallback, useRef } from 'react';

export interface OnlineStatus {
  /**
   * Whether the app is currently online
   */
  isOnline: boolean;

  /**
   * Last time the app was confirmed online
   */
  lastOnline: Date | null;

  /**
   * Whether currently checking connectivity
   */
  isChecking: boolean;

  /**
   * Force a connectivity check
   */
  checkConnection: () => Promise<boolean>;
}

interface UseOnlineStatusOptions {
  /**
   * Interval for API ping checks (ms)
   * @default 30000 (30 seconds)
   */
  pingInterval?: number;

  /**
   * Timeout for ping requests (ms)
   * @default 5000 (5 seconds)
   */
  pingTimeout?: number;

  /**
   * API endpoint to ping for connectivity check
   * @default '/api/health'
   */
  pingEndpoint?: string;

  /**
   * Whether to enable API ping checks
   * @default true
   */
  enablePing?: boolean;
}

/**
 * Hook to track online/offline status
 *
 * Uses both browser navigator.onLine events and periodic API pings
 * for reliable connectivity detection.
 *
 * @example
 * ```tsx
 * function App() {
 *   const { isOnline, lastOnline } = useOnlineStatus();
 *
 *   if (!isOnline) {
 *     return <OfflineBanner lastOnline={lastOnline} />;
 *   }
 *
 *   return <MainApp />;
 * }
 * ```
 */
export function useOnlineStatus(options: UseOnlineStatusOptions = {}): OnlineStatus {
  const {
    pingInterval = 30000,
    pingTimeout = 5000,
    pingEndpoint = '/api/health',
    enablePing = true,
  } = options;

  const [isOnline, setIsOnline] = useState<boolean>(
    typeof navigator !== 'undefined' ? navigator.onLine : true
  );
  const [lastOnline, setLastOnline] = useState<Date | null>(
    isOnline ? new Date() : null
  );
  const [isChecking, setIsChecking] = useState(false);

  const pingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Update lastOnline when coming online
  useEffect(() => {
    if (isOnline) {
      setLastOnline(new Date());
    }
  }, [isOnline]);

  // Ping the API to verify actual connectivity
  const checkConnection = useCallback(async (): Promise<boolean> => {
    if (!enablePing) {
      return navigator.onLine;
    }

    setIsChecking(true);

    // Cancel any pending request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    abortControllerRef.current = new AbortController();

    try {
      const response = await fetch(pingEndpoint, {
        method: 'HEAD',
        cache: 'no-store',
        signal: abortControllerRef.current.signal,
        // Add timeout
        ...(typeof AbortSignal !== 'undefined' && AbortSignal.timeout
          ? { signal: AbortSignal.any([
              abortControllerRef.current.signal,
              AbortSignal.timeout(pingTimeout),
            ]) }
          : {}),
      });

      const online = response.ok;
      setIsOnline(online);
      return online;
    } catch (error) {
      // Network error or timeout - assume offline
      if (error instanceof Error && error.name !== 'AbortError') {
        setIsOnline(false);
      }
      return false;
    } finally {
      setIsChecking(false);
    }
  }, [enablePing, pingEndpoint, pingTimeout]);

  // Handle browser online/offline events
  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      // Verify with API ping
      if (enablePing) {
        checkConnection();
      }
    };

    const handleOffline = () => {
      setIsOnline(false);
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [enablePing, checkConnection]);

  // Periodic API ping for more reliable detection
  useEffect(() => {
    if (!enablePing) {
      return;
    }

    // Initial check
    checkConnection();

    // Set up interval
    pingIntervalRef.current = setInterval(() => {
      checkConnection();
    }, pingInterval);

    return () => {
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
      }
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [enablePing, pingInterval, checkConnection]);

  return {
    isOnline,
    lastOnline,
    isChecking,
    checkConnection,
  };
}

/**
 * Format time since last online for display
 */
export function formatTimeSinceOnline(lastOnline: Date | null): string {
  if (!lastOnline) {
    return 'Unknown';
  }

  const now = new Date();
  const diffMs = now.getTime() - lastOnline.getTime();
  const diffSeconds = Math.floor(diffMs / 1000);
  const diffMinutes = Math.floor(diffSeconds / 60);
  const diffHours = Math.floor(diffMinutes / 60);

  if (diffSeconds < 60) {
    return 'Just now';
  } else if (diffMinutes < 60) {
    return `${diffMinutes} minute${diffMinutes !== 1 ? 's' : ''} ago`;
  } else if (diffHours < 24) {
    return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
  } else {
    return lastOnline.toLocaleDateString();
  }
}

export default useOnlineStatus;
