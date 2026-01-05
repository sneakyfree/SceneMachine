/**
 * Touch gesture handlers for mobile video player and navigation.
 */

import { useRef, useEffect, useCallback, useState } from 'react';

/**
 * Gesture types
 */
export type GestureType =
  | 'tap'
  | 'double-tap'
  | 'long-press'
  | 'swipe-left'
  | 'swipe-right'
  | 'swipe-up'
  | 'swipe-down'
  | 'pinch-in'
  | 'pinch-out'
  | 'pan';

export interface GestureEvent {
  type: GestureType;
  x: number;
  y: number;
  deltaX?: number;
  deltaY?: number;
  scale?: number;
  velocity?: number;
}

export interface GestureHandlers {
  onTap?: (e: GestureEvent) => void;
  onDoubleTap?: (e: GestureEvent) => void;
  onLongPress?: (e: GestureEvent) => void;
  onSwipeLeft?: (e: GestureEvent) => void;
  onSwipeRight?: (e: GestureEvent) => void;
  onSwipeUp?: (e: GestureEvent) => void;
  onSwipeDown?: (e: GestureEvent) => void;
  onPinchIn?: (e: GestureEvent) => void;
  onPinchOut?: (e: GestureEvent) => void;
  onPan?: (e: GestureEvent) => void;
  onPanEnd?: (e: GestureEvent) => void;
}

export interface GestureConfig {
  /** Minimum distance for swipe detection (px) */
  swipeThreshold?: number;
  /** Maximum time for swipe detection (ms) */
  swipeTimeout?: number;
  /** Maximum time between taps for double-tap (ms) */
  doubleTapDelay?: number;
  /** Minimum hold time for long press (ms) */
  longPressDelay?: number;
  /** Minimum scale change for pinch detection */
  pinchThreshold?: number;
  /** Disable default touch behavior */
  preventDefault?: boolean;
}

const defaultConfig: Required<GestureConfig> = {
  swipeThreshold: 50,
  swipeTimeout: 300,
  doubleTapDelay: 300,
  longPressDelay: 500,
  pinchThreshold: 0.1,
  preventDefault: true,
};

/**
 * Hook for handling touch gestures
 */
export function useGestures<T extends HTMLElement = HTMLElement>(
  handlers: GestureHandlers,
  config: GestureConfig = {}
): React.RefObject<T> {
  const ref = useRef<T>(null);
  const configRef = useRef({ ...defaultConfig, ...config });

  // Touch state
  const touchState = useRef({
    startX: 0,
    startY: 0,
    startTime: 0,
    lastTapTime: 0,
    isMultiTouch: false,
    initialDistance: 0,
    longPressTimer: null as NodeJS.Timeout | null,
    isPanning: false,
  });

  // Calculate distance between two touch points
  const getDistance = useCallback((touches: TouchList): number => {
    if (touches.length < 2) return 0;
    const dx = touches[0].clientX - touches[1].clientX;
    const dy = touches[0].clientY - touches[1].clientY;
    return Math.sqrt(dx * dx + dy * dy);
  }, []);

  // Handle touch start
  const handleTouchStart = useCallback((e: TouchEvent) => {
    const { preventDefault, longPressDelay } = configRef.current;
    const state = touchState.current;

    if (preventDefault && e.cancelable) {
      e.preventDefault();
    }

    const touch = e.touches[0];
    state.startX = touch.clientX;
    state.startY = touch.clientY;
    state.startTime = Date.now();
    state.isMultiTouch = e.touches.length > 1;
    state.isPanning = false;

    // Multi-touch: record initial distance for pinch
    if (e.touches.length === 2) {
      state.initialDistance = getDistance(e.touches);
    }

    // Start long press timer
    if (handlers.onLongPress) {
      state.longPressTimer = setTimeout(() => {
        const event: GestureEvent = {
          type: 'long-press',
          x: state.startX,
          y: state.startY,
        };
        handlers.onLongPress?.(event);
      }, longPressDelay);
    }
  }, [handlers, getDistance]);

  // Handle touch move
  const handleTouchMove = useCallback((e: TouchEvent) => {
    const { preventDefault, swipeThreshold, pinchThreshold } = configRef.current;
    const state = touchState.current;

    // Cancel long press on move
    if (state.longPressTimer) {
      clearTimeout(state.longPressTimer);
      state.longPressTimer = null;
    }

    if (preventDefault && e.cancelable) {
      e.preventDefault();
    }

    const touch = e.touches[0];
    const deltaX = touch.clientX - state.startX;
    const deltaY = touch.clientY - state.startY;

    // Handle pinch
    if (e.touches.length === 2 && state.initialDistance > 0) {
      const currentDistance = getDistance(e.touches);
      const scale = currentDistance / state.initialDistance;

      if (Math.abs(scale - 1) > pinchThreshold) {
        const event: GestureEvent = {
          type: scale > 1 ? 'pinch-out' : 'pinch-in',
          x: (e.touches[0].clientX + e.touches[1].clientX) / 2,
          y: (e.touches[0].clientY + e.touches[1].clientY) / 2,
          scale,
        };

        if (scale > 1) {
          handlers.onPinchOut?.(event);
        } else {
          handlers.onPinchIn?.(event);
        }
      }
      return;
    }

    // Handle pan
    if (
      handlers.onPan &&
      (Math.abs(deltaX) > 10 || Math.abs(deltaY) > 10)
    ) {
      state.isPanning = true;
      const event: GestureEvent = {
        type: 'pan',
        x: touch.clientX,
        y: touch.clientY,
        deltaX,
        deltaY,
      };
      handlers.onPan(event);
    }
  }, [handlers, getDistance]);

  // Handle touch end
  const handleTouchEnd = useCallback((e: TouchEvent) => {
    const { swipeThreshold, swipeTimeout, doubleTapDelay } = configRef.current;
    const state = touchState.current;

    // Cancel long press timer
    if (state.longPressTimer) {
      clearTimeout(state.longPressTimer);
      state.longPressTimer = null;
    }

    const touch = e.changedTouches[0];
    const deltaX = touch.clientX - state.startX;
    const deltaY = touch.clientY - state.startY;
    const deltaTime = Date.now() - state.startTime;
    const velocity = Math.sqrt(deltaX * deltaX + deltaY * deltaY) / deltaTime;

    // Handle pan end
    if (state.isPanning && handlers.onPanEnd) {
      const event: GestureEvent = {
        type: 'pan',
        x: touch.clientX,
        y: touch.clientY,
        deltaX,
        deltaY,
        velocity,
      };
      handlers.onPanEnd(event);
      state.isPanning = false;
      return;
    }

    // Check for swipe
    if (deltaTime < swipeTimeout) {
      const absX = Math.abs(deltaX);
      const absY = Math.abs(deltaY);

      if (absX > swipeThreshold || absY > swipeThreshold) {
        let type: GestureType;
        if (absX > absY) {
          type = deltaX > 0 ? 'swipe-right' : 'swipe-left';
        } else {
          type = deltaY > 0 ? 'swipe-down' : 'swipe-up';
        }

        const event: GestureEvent = {
          type,
          x: touch.clientX,
          y: touch.clientY,
          deltaX,
          deltaY,
          velocity,
        };

        switch (type) {
          case 'swipe-left':
            handlers.onSwipeLeft?.(event);
            break;
          case 'swipe-right':
            handlers.onSwipeRight?.(event);
            break;
          case 'swipe-up':
            handlers.onSwipeUp?.(event);
            break;
          case 'swipe-down':
            handlers.onSwipeDown?.(event);
            break;
        }
        return;
      }
    }

    // Check for tap/double-tap
    if (Math.abs(deltaX) < 10 && Math.abs(deltaY) < 10 && deltaTime < 300) {
      const now = Date.now();

      if (now - state.lastTapTime < doubleTapDelay && handlers.onDoubleTap) {
        // Double tap
        const event: GestureEvent = {
          type: 'double-tap',
          x: touch.clientX,
          y: touch.clientY,
        };
        handlers.onDoubleTap(event);
        state.lastTapTime = 0;
      } else {
        // Single tap (with delay to check for double tap)
        state.lastTapTime = now;
        if (handlers.onTap && !handlers.onDoubleTap) {
          const event: GestureEvent = {
            type: 'tap',
            x: touch.clientX,
            y: touch.clientY,
          };
          handlers.onTap(event);
        } else if (handlers.onTap) {
          setTimeout(() => {
            if (Date.now() - state.lastTapTime >= doubleTapDelay) {
              const event: GestureEvent = {
                type: 'tap',
                x: touch.clientX,
                y: touch.clientY,
              };
              handlers.onTap?.(event);
            }
          }, doubleTapDelay);
        }
      }
    }
  }, [handlers]);

  // Attach event listeners
  useEffect(() => {
    const element = ref.current;
    if (!element) return;

    element.addEventListener('touchstart', handleTouchStart, { passive: false });
    element.addEventListener('touchmove', handleTouchMove, { passive: false });
    element.addEventListener('touchend', handleTouchEnd, { passive: false });

    return () => {
      element.removeEventListener('touchstart', handleTouchStart);
      element.removeEventListener('touchmove', handleTouchMove);
      element.removeEventListener('touchend', handleTouchEnd);

      // Clean up any pending timers
      if (touchState.current.longPressTimer) {
        clearTimeout(touchState.current.longPressTimer);
      }
    };
  }, [handleTouchStart, handleTouchMove, handleTouchEnd]);

  return ref;
}

/**
 * Hook for video player specific gestures
 */
export function useVideoGestures(options: {
  onSeekForward?: (seconds: number) => void;
  onSeekBackward?: (seconds: number) => void;
  onVolumeChange?: (delta: number) => void;
  onBrightnessChange?: (delta: number) => void;
  onTogglePlayPause?: () => void;
  onToggleFullscreen?: () => void;
  onToggleControls?: () => void;
  seekSeconds?: number;
}) {
  const {
    onSeekForward,
    onSeekBackward,
    onVolumeChange,
    onBrightnessChange,
    onTogglePlayPause,
    onToggleFullscreen,
    onToggleControls,
    seekSeconds = 10,
  } = options;

  const [controlsVisible, setControlsVisible] = useState(true);

  const handlers: GestureHandlers = {
    onTap: () => {
      setControlsVisible(prev => !prev);
      onToggleControls?.();
    },

    onDoubleTap: (e) => {
      // Double tap left side = seek backward
      // Double tap right side = seek forward
      // Double tap center = fullscreen
      const element = document.elementFromPoint(e.x, e.y);
      if (!element) return;

      const rect = element.getBoundingClientRect();
      const relativeX = (e.x - rect.left) / rect.width;

      if (relativeX < 0.33) {
        onSeekBackward?.(seekSeconds);
      } else if (relativeX > 0.66) {
        onSeekForward?.(seekSeconds);
      } else {
        onToggleFullscreen?.();
      }
    },

    onSwipeLeft: () => {
      onSeekBackward?.(seekSeconds);
    },

    onSwipeRight: () => {
      onSeekForward?.(seekSeconds);
    },

    onPan: (e) => {
      if (!e.deltaX || !e.deltaY) return;

      // Vertical swipe on left side = brightness
      // Vertical swipe on right side = volume
      const element = document.elementFromPoint(e.x - (e.deltaX || 0), e.y);
      if (!element) return;

      const rect = element.getBoundingClientRect();
      const relativeX = ((e.x - (e.deltaX || 0)) - rect.left) / rect.width;
      const deltaY = e.deltaY / rect.height;

      if (relativeX < 0.5) {
        onBrightnessChange?.(-deltaY);
      } else {
        onVolumeChange?.(-deltaY);
      }
    },

    onLongPress: () => {
      onTogglePlayPause?.();
    },
  };

  const ref = useGestures(handlers, {
    swipeThreshold: 30,
    doubleTapDelay: 250,
  });

  return { ref, controlsVisible, setControlsVisible };
}

/**
 * Hook for horizontal swipe navigation (e.g., video feed)
 */
export function useSwipeNavigation<T extends HTMLElement = HTMLElement>(options: {
  onNext?: () => void;
  onPrevious?: () => void;
  threshold?: number;
}) {
  const { onNext, onPrevious, threshold = 100 } = options;

  const handlers: GestureHandlers = {
    onSwipeLeft: (e) => {
      if (e.deltaX && Math.abs(e.deltaX) > threshold) {
        onNext?.();
      }
    },
    onSwipeRight: (e) => {
      if (e.deltaX && Math.abs(e.deltaX) > threshold) {
        onPrevious?.();
      }
    },
  };

  return useGestures<T>(handlers, { swipeThreshold: threshold });
}

/**
 * Hook for pull-to-refresh
 */
export function usePullToRefresh<T extends HTMLElement = HTMLElement>(options: {
  onRefresh: () => Promise<void>;
  threshold?: number;
}) {
  const { onRefresh, threshold = 80 } = options;
  const [isPulling, setIsPulling] = useState(false);
  const [pullDistance, setPullDistance] = useState(0);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handlers: GestureHandlers = {
    onPan: (e) => {
      if (!e.deltaY || e.deltaY < 0) return;
      if (window.scrollY > 0) return;

      setIsPulling(true);
      setPullDistance(Math.min(e.deltaY, threshold * 1.5));
    },
    onPanEnd: async (e) => {
      if (!isPulling) return;

      if (pullDistance >= threshold) {
        setIsRefreshing(true);
        try {
          await onRefresh();
        } finally {
          setIsRefreshing(false);
        }
      }

      setIsPulling(false);
      setPullDistance(0);
    },
  };

  const ref = useGestures<T>(handlers, {
    preventDefault: false,
  });

  return { ref, isPulling, pullDistance, isRefreshing };
}
