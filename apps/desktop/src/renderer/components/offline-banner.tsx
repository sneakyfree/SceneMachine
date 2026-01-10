/**
 * Offline Banner Component
 *
 * Displays when the application loses network connectivity.
 * Shows reconnection status and available offline actions.
 */

import { useState, useEffect, useCallback, memo } from 'react';
import { WifiOff, Wifi, RefreshCw, AlertCircle, CheckCircle } from 'lucide-react';
import { cn } from '../lib/utils';
import { useOnlineStatus, formatTimeSinceOnline } from '../hooks/use-online-status';

interface OfflineBannerProps {
  /**
   * Additional CSS classes
   */
  className?: string;

  /**
   * Called when online status changes
   */
  onStatusChange?: (isOnline: boolean) => void;

  /**
   * Auto-dismiss delay for "back online" message (ms)
   * @default 3000
   */
  autoDismissDelay?: number;
}

type BannerState = 'offline' | 'reconnecting' | 'online' | 'hidden';

/**
 * Offline Banner Component
 *
 * Fixed position banner that appears when connectivity is lost.
 * Shows helpful messaging and auto-dismisses when back online.
 */
export const OfflineBanner = memo(function OfflineBanner({
  className,
  onStatusChange,
  autoDismissDelay = 3000,
}: OfflineBannerProps) {
  const { isOnline, lastOnline, isChecking, checkConnection } = useOnlineStatus();
  const [bannerState, setBannerState] = useState<BannerState>(isOnline ? 'hidden' : 'offline');
  const [showDetails, setShowDetails] = useState(false);

  // Track previous online state for transitions
  const [wasOffline, setWasOffline] = useState(!isOnline);

  // Handle state transitions
  useEffect(() => {
    if (isOnline && wasOffline) {
      // Just came back online
      setBannerState('online');
      setWasOffline(false);

      // Auto-dismiss after delay
      const timer = setTimeout(() => {
        setBannerState('hidden');
      }, autoDismissDelay);

      return () => clearTimeout(timer);
    } else if (!isOnline) {
      // Went offline
      setBannerState('offline');
      setWasOffline(true);
    }
  }, [isOnline, wasOffline, autoDismissDelay]);

  // Update checking state
  useEffect(() => {
    if (isChecking && bannerState === 'offline') {
      setBannerState('reconnecting');
    } else if (!isChecking && bannerState === 'reconnecting' && !isOnline) {
      setBannerState('offline');
    }
  }, [isChecking, bannerState, isOnline]);

  // Notify parent of status changes
  useEffect(() => {
    onStatusChange?.(isOnline);
  }, [isOnline, onStatusChange]);

  // Manual retry handler
  const handleRetry = useCallback(() => {
    setBannerState('reconnecting');
    checkConnection();
  }, [checkConnection]);

  // Don't render if hidden
  if (bannerState === 'hidden') {
    return null;
  }

  const getBannerConfig = () => {
    switch (bannerState) {
      case 'offline':
        return {
          bgColor: 'bg-yellow-500/95',
          textColor: 'text-yellow-950',
          icon: WifiOff,
          iconColor: 'text-yellow-900',
          message: "You're offline",
          subMessage: 'Some features may be unavailable',
        };
      case 'reconnecting':
        return {
          bgColor: 'bg-blue-500/95',
          textColor: 'text-white',
          icon: RefreshCw,
          iconColor: 'text-blue-100',
          message: 'Reconnecting...',
          subMessage: 'Checking connection',
          iconSpin: true,
        };
      case 'online':
        return {
          bgColor: 'bg-green-500/95',
          textColor: 'text-white',
          icon: CheckCircle,
          iconColor: 'text-green-100',
          message: 'Back online!',
          subMessage: 'All features restored',
        };
      default:
        return null;
    }
  };

  const config = getBannerConfig();
  if (!config) return null;

  const Icon = config.icon;

  return (
    <div
      role="alert"
      aria-live="polite"
      className={cn(
        // Base styles
        'fixed top-0 left-0 right-0 z-50',
        'transition-all duration-300 ease-in-out',
        // Animate in
        bannerState === 'hidden'
          ? 'translate-y-[-100%] opacity-0'
          : 'translate-y-0 opacity-100',
        className
      )}
    >
      <div
        className={cn(
          'flex items-center justify-between',
          'px-4 py-2 shadow-lg',
          config.bgColor,
          config.textColor
        )}
      >
        {/* Left side - Status */}
        <div className="flex items-center gap-3">
          <Icon
            className={cn(
              'w-5 h-5',
              config.iconColor,
              'iconSpin' in config && config.iconSpin && 'animate-spin'
            )}
          />
          <div>
            <span className="font-medium">{config.message}</span>
            {showDetails && config.subMessage && (
              <span className="ml-2 text-sm opacity-80">
                — {config.subMessage}
              </span>
            )}
          </div>
        </div>

        {/* Right side - Actions */}
        <div className="flex items-center gap-2">
          {/* Last online info */}
          {bannerState === 'offline' && lastOnline && (
            <button
              onClick={() => setShowDetails(!showDetails)}
              className={cn(
                'text-sm opacity-70 hover:opacity-100 transition-opacity',
                'focus:outline-none focus:ring-2 focus:ring-yellow-900/30 rounded px-2 py-1'
              )}
              aria-label={showDetails ? 'Hide details' : 'Show details'}
            >
              Last online: {formatTimeSinceOnline(lastOnline)}
            </button>
          )}

          {/* Retry button */}
          {bannerState === 'offline' && (
            <button
              onClick={handleRetry}
              className={cn(
                'flex items-center gap-1.5 px-3 py-1 rounded',
                'bg-yellow-600/30 hover:bg-yellow-600/50',
                'transition-colors focus:outline-none',
                'focus:ring-2 focus:ring-yellow-900/50'
              )}
              aria-label="Retry connection"
            >
              <RefreshCw className="w-4 h-4" />
              <span className="text-sm font-medium">Retry</span>
            </button>
          )}

          {/* Dismiss button for online state */}
          {bannerState === 'online' && (
            <button
              onClick={() => setBannerState('hidden')}
              className={cn(
                'p-1 rounded hover:bg-green-600/30',
                'transition-colors focus:outline-none',
                'focus:ring-2 focus:ring-green-400/50'
              )}
              aria-label="Dismiss"
            >
              <span className="sr-only">Dismiss</span>
              <svg
                className="w-4 h-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* Expanded details panel */}
      {showDetails && bannerState === 'offline' && (
        <div
          className={cn(
            'px-4 py-3',
            'bg-yellow-400/90 text-yellow-900',
            'border-t border-yellow-500/30'
          )}
        >
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
            <div className="text-sm space-y-2">
              <p className="font-medium">Available while offline:</p>
              <ul className="list-disc list-inside space-y-1 opacity-90">
                <li>View cached projects and scenes</li>
                <li>Review generated content</li>
                <li>Edit character details (changes sync when online)</li>
              </ul>
              <p className="font-medium mt-3">Unavailable while offline:</p>
              <ul className="list-disc list-inside space-y-1 opacity-90">
                <li>Generate new video clips</li>
                <li>Create TTS audio</li>
                <li>Export final videos</li>
                <li>Real-time collaboration</li>
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
});

/**
 * Compact offline indicator for use in headers/footers
 */
export const OfflineIndicator = memo(function OfflineIndicator({
  className,
}: {
  className?: string;
}) {
  const { isOnline, isChecking } = useOnlineStatus();

  return (
    <div
      className={cn(
        'flex items-center gap-1.5 text-sm',
        isOnline ? 'text-green-400' : 'text-yellow-400',
        className
      )}
      role="status"
      aria-label={isOnline ? 'Online' : 'Offline'}
    >
      {isChecking ? (
        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
      ) : isOnline ? (
        <Wifi className="w-3.5 h-3.5" />
      ) : (
        <WifiOff className="w-3.5 h-3.5" />
      )}
      <span className="hidden sm:inline">
        {isChecking ? 'Checking...' : isOnline ? 'Online' : 'Offline'}
      </span>
    </div>
  );
});

export default OfflineBanner;
