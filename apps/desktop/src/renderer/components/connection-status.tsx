/**
 * WebSocket Connection Status Indicator Component
 *
 * Shows the current connection state with reconnection info and actions.
 * Supports multiple display modes and provides visual feedback for
 * reconnection attempts, polling fallback, and errors.
 */

import { memo, useState } from 'react';
import { Wifi, WifiOff, RefreshCw, Radio, AlertTriangle, CheckCircle } from 'lucide-react';
import {
  wsClient,
  useWebSocketStore,
  ConnectionState,
  getConnectionStatusInfo,
} from '../lib/websocket';
import { cn } from '../lib/utils';

interface ConnectionStatusProps {
  /**
   * Display mode
   * - 'icon': Just icon
   * - 'badge': Icon + label
   * - 'full': Icon + label + message
   */
  mode?: 'icon' | 'badge' | 'full';

  /**
   * Size variant
   */
  size?: 'sm' | 'md' | 'lg';

  /**
   * Additional CSS classes
   */
  className?: string;

  /**
   * Show tooltip on hover
   */
  showTooltip?: boolean;

  /**
   * @deprecated Use mode='badge' with showLabel functionality
   */
  showLabel?: boolean;
}

const sizeClasses = {
  sm: {
    icon: 'w-3.5 h-3.5',
    text: 'text-xs',
    padding: 'px-1.5 py-0.5',
  },
  md: {
    icon: 'w-4 h-4',
    text: 'text-sm',
    padding: 'px-2 py-1',
  },
  lg: {
    icon: 'w-5 h-5',
    text: 'text-base',
    padding: 'px-3 py-1.5',
  },
};

const colorClasses = {
  green: {
    bg: 'bg-green-500/20',
    text: 'text-green-400',
    border: 'border-green-500/30',
  },
  yellow: {
    bg: 'bg-yellow-500/20',
    text: 'text-yellow-400',
    border: 'border-yellow-500/30',
  },
  red: {
    bg: 'bg-red-500/20',
    text: 'text-red-400',
    border: 'border-red-500/30',
  },
  blue: {
    bg: 'bg-blue-500/20',
    text: 'text-blue-400',
    border: 'border-blue-500/30',
  },
};

function getIcon(icon: string, className: string) {
  switch (icon) {
    case 'connected':
      return <CheckCircle className={className} />;
    case 'disconnected':
      return <WifiOff className={className} />;
    case 'reconnecting':
      return <RefreshCw className={cn(className, 'animate-spin')} />;
    case 'polling':
      return <Radio className={className} />;
    case 'error':
      return <AlertTriangle className={className} />;
    default:
      return <Wifi className={className} />;
  }
}

/**
 * Connection Status Indicator
 */
export const ConnectionStatus = memo(function ConnectionStatus({
  mode = 'badge',
  size = 'sm',
  className,
  showTooltip = true,
  showLabel = false,
}: ConnectionStatusProps) {
  const { connectionState, error, reconnectAttempts, isPolling } = useWebSocketStore();
  const [showDetails, setShowDetails] = useState(false);

  // Support legacy showLabel prop
  const displayMode = showLabel ? 'badge' : mode;

  const statusInfo = getConnectionStatusInfo(connectionState, reconnectAttempts, error);
  const sizes = sizeClasses[size];
  const colors = colorClasses[statusInfo.color];

  const IconComponent = getIcon(statusInfo.icon, sizes.icon);

  const handleReconnect = () => {
    wsClient.forceReconnect();
  };

  // Icon only mode
  if (displayMode === 'icon') {
    return (
      <div
        className={cn('relative inline-flex', className)}
        title={showTooltip ? statusInfo.label : undefined}
      >
        <span className={colors.text}>{IconComponent}</span>

        {/* Pulse indicator for reconnecting */}
        {connectionState === ConnectionState.RECONNECTING && (
          <span className="absolute -top-0.5 -right-0.5 w-2 h-2">
            <span className="absolute inline-flex h-full w-full rounded-full bg-yellow-400 opacity-75 animate-ping" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-yellow-500" />
          </span>
        )}
      </div>
    );
  }

  // Badge mode
  if (displayMode === 'badge') {
    return (
      <div className={cn('flex items-center gap-2', className)}>
        <div
          className={cn(
            'inline-flex items-center gap-1.5 rounded-full',
            colors.bg,
            colors.text,
            sizes.padding,
            sizes.text,
            'cursor-pointer hover:opacity-80 transition-opacity'
          )}
          onClick={() => setShowDetails(!showDetails)}
          title={showTooltip && statusInfo.message ? statusInfo.message : undefined}
          role="status"
          aria-label={`Connection status: ${statusInfo.label}`}
        >
          {IconComponent}
          <span className="font-medium">{statusInfo.label}</span>
        </div>

        {/* Show reconnect button for problem states */}
        {(connectionState === ConnectionState.DISCONNECTED ||
          connectionState === ConnectionState.ERROR ||
          connectionState === ConnectionState.POLLING) && (
          <button
            onClick={handleReconnect}
            className="text-xs text-primary-400 hover:text-primary-300"
          >
            Reconnect
          </button>
        )}
      </div>
    );
  }

  // Full mode with expandable details
  return (
    <div className={cn('space-y-2', className)}>
      <div
        className={cn(
          'inline-flex items-center gap-2 rounded-lg',
          colors.bg,
          colors.text,
          sizes.padding,
          sizes.text
        )}
        role="status"
        aria-label={`Connection status: ${statusInfo.label}`}
      >
        {IconComponent}
        <span className="font-medium">{statusInfo.label}</span>
      </div>

      {statusInfo.message && (
        <p className={cn('text-surface-400', sizes.text)}>{statusInfo.message}</p>
      )}

      {isPolling && (
        <p className="text-yellow-300 text-xs">Real-time updates may be delayed while polling</p>
      )}

      {/* Reconnect button for error/disconnected states */}
      {(connectionState === ConnectionState.ERROR ||
        connectionState === ConnectionState.DISCONNECTED ||
        connectionState === ConnectionState.POLLING) && (
        <button
          onClick={handleReconnect}
          className={cn(
            'flex items-center gap-1.5 rounded-lg',
            'bg-surface-700 text-surface-200',
            'hover:bg-surface-600 transition-colors',
            sizes.padding,
            sizes.text
          )}
        >
          <RefreshCw className={sizes.icon} />
          <span>Reconnect</span>
        </button>
      )}
    </div>
  );
});

/**
 * Connection Status Banner
 *
 * Full-width banner for prominent connection status display.
 * Only shows when there's a connection problem.
 */
export const ConnectionStatusBanner = memo(function ConnectionStatusBanner({
  className,
}: {
  className?: string;
}) {
  const { connectionState, error, reconnectAttempts, isPolling } = useWebSocketStore();

  // Don't show banner when connected normally
  if (connectionState === ConnectionState.CONNECTED) {
    return null;
  }

  const statusInfo = getConnectionStatusInfo(connectionState, reconnectAttempts, error);
  const colors = colorClasses[statusInfo.color];

  const handleReconnect = () => {
    wsClient.forceReconnect();
  };

  return (
    <div
      className={cn(
        'flex items-center justify-between px-4 py-2',
        colors.bg,
        'border-b',
        colors.border,
        className
      )}
      role="alert"
    >
      <div className="flex items-center gap-3">
        <span className={colors.text}>{getIcon(statusInfo.icon, 'w-4 h-4')}</span>
        <div>
          <span className={cn('font-medium', colors.text)}>{statusInfo.label}</span>
          {statusInfo.message && (
            <span className="ml-2 text-surface-400 text-sm">{statusInfo.message}</span>
          )}
          {isPolling && (
            <span className="ml-2 text-yellow-300 text-sm">Updates may be delayed</span>
          )}
        </div>
      </div>

      {(connectionState === ConnectionState.ERROR ||
        connectionState === ConnectionState.DISCONNECTED ||
        connectionState === ConnectionState.POLLING) && (
        <button
          onClick={handleReconnect}
          className={cn(
            'flex items-center gap-1.5 px-3 py-1 rounded-lg text-sm',
            'bg-surface-800/50 text-surface-200',
            'hover:bg-surface-700 transition-colors'
          )}
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Reconnect</span>
        </button>
      )}
    </div>
  );
});

export default ConnectionStatus;
