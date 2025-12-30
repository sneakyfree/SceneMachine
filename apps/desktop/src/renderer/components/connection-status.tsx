/**
 * WebSocket connection status indicator component.
 * Shows the current connection state and allows manual reconnection.
 */

import { useEffect } from 'react';
import { Wifi, WifiOff, Loader2, RefreshCw } from 'lucide-react';
import { wsClient, useWebSocketStore, ConnectionState } from '../lib/websocket';
import { cn } from '../lib/utils';

interface ConnectionStatusProps {
  showLabel?: boolean;
  className?: string;
}

const statusConfig: Record<
  ConnectionState,
  { icon: typeof Wifi; color: string; label: string }
> = {
  connected: {
    icon: Wifi,
    color: 'text-green-400',
    label: 'Connected',
  },
  connecting: {
    icon: Loader2,
    color: 'text-yellow-400',
    label: 'Connecting...',
  },
  reconnecting: {
    icon: RefreshCw,
    color: 'text-yellow-400',
    label: 'Reconnecting...',
  },
  disconnected: {
    icon: WifiOff,
    color: 'text-red-400',
    label: 'Disconnected',
  },
};

export function ConnectionStatus({ showLabel = false, className }: ConnectionStatusProps) {
  const { connectionState, reconnectAttempts, error } = useWebSocketStore();
  const config = statusConfig[connectionState];
  const Icon = config.icon;
  const isAnimating = connectionState === 'connecting' || connectionState === 'reconnecting';

  const handleReconnect = () => {
    wsClient.connect();
  };

  return (
    <div
      className={cn('flex items-center gap-2', className)}
      title={
        error
          ? `Error: ${error}`
          : reconnectAttempts > 0
          ? `Reconnect attempt ${reconnectAttempts}`
          : config.label
      }
    >
      <Icon
        className={cn(
          'w-4 h-4',
          config.color,
          isAnimating && 'animate-spin'
        )}
      />
      {showLabel && (
        <span className={cn('text-sm', config.color)}>{config.label}</span>
      )}
      {connectionState === 'disconnected' && (
        <button
          onClick={handleReconnect}
          className="text-xs text-brand-400 hover:text-brand-300"
        >
          Reconnect
        </button>
      )}
    </div>
  );
}

/**
 * Hook to initialize WebSocket connection on mount.
 */
export function useWebSocketConnection() {
  useEffect(() => {
    // Connect on mount
    wsClient.connect();

    // Disconnect on unmount
    return () => {
      wsClient.disconnect();
    };
  }, []);
}
