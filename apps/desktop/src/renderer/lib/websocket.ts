/**
 * WebSocket utilities for SceneMachine
 * Provides real-time communication with the backend
 */

// ============================================================================
// Types
// ============================================================================

export type WebSocketStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

export interface WebSocketMessage<T = unknown> {
  type: string;
  payload: T;
  timestamp: number;
}

/** Generic event payload used across consumers */
export interface WebSocketEvent<T = unknown> {
  type: string;
  data: T;
  timestamp: number;
  jobId?: string;
  shotId?: string;
  progress?: number;
  error?: string;
}

/** Connection state enum for connection-status component */
export enum ConnectionState {
  CONNECTING = 'connecting',
  CONNECTED = 'connected',
  DISCONNECTED = 'disconnected',
  RECONNECTING = 'reconnecting',
  ERROR = 'error',
  POLLING = 'polling',
}

export interface WebSocketOptions {
  url: string;
  reconnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  onOpen?: () => void;
  onClose?: () => void;
  onError?: (error: Event) => void;
  onMessage?: (message: WebSocketMessage) => void;
  onStatusChange?: (status: WebSocketStatus) => void;
}

// ============================================================================
// WebSocket Manager Class
// ============================================================================

export class WebSocketManager {
  private ws: WebSocket | null = null;
  private options: Required<WebSocketOptions>;
  private reconnectAttempts = 0;
  private reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
  private messageHandlers = new Map<string, Set<(payload: unknown) => void>>();
  private status: WebSocketStatus = 'disconnected';

  constructor(options: WebSocketOptions) {
    this.options = {
      reconnect: true,
      reconnectInterval: 3000,
      maxReconnectAttempts: 10,
      onOpen: () => {},
      onClose: () => {},
      onError: () => {},
      onMessage: () => {},
      onStatusChange: () => {},
      ...options,
    };
  }

  /**
   * Connect to the WebSocket server
   */
  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return;
    }

    this.setStatus('connecting');

    try {
      this.ws = new WebSocket(this.options.url);

      this.ws.onopen = () => {
        this.reconnectAttempts = 0;
        this.setStatus('connected');
        this.options.onOpen();
      };

      this.ws.onclose = () => {
        this.setStatus('disconnected');
        this.options.onClose();
        this.handleReconnect();
      };

      this.ws.onerror = (error) => {
        this.setStatus('error');
        this.options.onError(error);
      };

      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as WebSocketMessage;
          this.options.onMessage(message);
          this.dispatchMessage(message);
        } catch (e) {
          console.warn('Failed to parse WebSocket message:', e);
        }
      };
    } catch (error) {
      this.setStatus('error');
      this.handleReconnect();
    }
  }

  /**
   * Disconnect from the WebSocket server
   */
  disconnect(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    this.setStatus('disconnected');
  }

  /**
   * Send a message to the server
   */
  send<T>(type: string, payload: T): boolean {
    if (this.ws?.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket is not connected');
      return false;
    }

    const message: WebSocketMessage<T> = {
      type,
      payload,
      timestamp: Date.now(),
    };

    try {
      this.ws.send(JSON.stringify(message));
      return true;
    } catch (e) {
      console.error('Failed to send WebSocket message:', e);
      return false;
    }
  }

  /**
   * Subscribe to a message type
   */
  subscribe<T>(type: string, handler: (payload: T) => void): () => void {
    if (!this.messageHandlers.has(type)) {
      this.messageHandlers.set(type, new Set());
    }

    const handlers = this.messageHandlers.get(type)!;
    handlers.add(handler as (payload: unknown) => void);

    // Return unsubscribe function
    return () => {
      handlers.delete(handler as (payload: unknown) => void);
      if (handlers.size === 0) {
        this.messageHandlers.delete(type);
      }
    };
  }

  /**
   * Get current connection status
   */
  getStatus(): WebSocketStatus {
    return this.status;
  }

  /**
   * Check if connected
   */
  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  // Private methods

  private setStatus(status: WebSocketStatus): void {
    if (this.status !== status) {
      this.status = status;
      this.options.onStatusChange(status);
    }
  }

  private handleReconnect(): void {
    if (!this.options.reconnect) return;
    if (this.reconnectAttempts >= this.options.maxReconnectAttempts) {
      console.warn('Max reconnect attempts reached');
      return;
    }

    this.reconnectAttempts++;
    const delay = this.options.reconnectInterval * Math.pow(1.5, this.reconnectAttempts - 1);

    this.reconnectTimeout = setTimeout(() => {
      console.log(
        `Attempting to reconnect (${this.reconnectAttempts}/${this.options.maxReconnectAttempts})...`
      );
      this.connect();
    }, delay);
  }

  private dispatchMessage(message: WebSocketMessage): void {
    const handlers = this.messageHandlers.get(message.type);
    if (handlers) {
      for (const handler of handlers) {
        try {
          handler(message.payload);
        } catch (e) {
          console.error('Error in message handler:', e);
        }
      }
    }
  }
}

// ============================================================================
// Singleton instance
// ============================================================================

let defaultManager: WebSocketManager | null = null;

/**
 * Get or create the default WebSocket manager
 */
export function getWebSocketManager(url?: string): WebSocketManager {
  if (!defaultManager && url) {
    defaultManager = new WebSocketManager({ url });
  }
  if (!defaultManager) {
    throw new Error('WebSocket manager not initialized. Provide a URL.');
  }
  return defaultManager;
}

/**
 * Initialize the default WebSocket manager
 */
export function initWebSocket(options: WebSocketOptions): WebSocketManager {
  if (defaultManager) {
    defaultManager.disconnect();
  }
  defaultManager = new WebSocketManager(options);
  return defaultManager;
}

// ============================================================================
// Hook-friendly helpers
// ============================================================================

/**
 * Create a WebSocket URL from current location
 */
export function createWebSocketUrl(path: string = '/ws'): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  return `${protocol}//${host}${path}`;
}

// ============================================================================
// Event Types
// ============================================================================

export enum EventType {
  // Generation events
  GENERATION_STARTED = 'generation.started',
  GENERATION_PROGRESS = 'generation.progress',
  GENERATION_COMPLETED = 'generation.completed',
  GENERATION_FAILED = 'generation.failed',

  // Job events (used by generation page + queue manager)
  JOB_QUEUED = 'job.queued',
  JOB_STARTED = 'job.started',
  JOB_PROGRESS = 'job.progress',
  JOB_COMPLETED = 'job.completed',
  JOB_FAILED = 'job.failed',
  QUEUE_UPDATED = 'queue.updated',

  // Shot events
  SHOT_UPDATED = 'shot.updated',
  SHOT_APPROVED = 'shot.approved',
  SHOT_REJECTED = 'shot.rejected',

  // Assembly events
  ASSEMBLY_STARTED = 'assembly.started',
  ASSEMBLY_PROGRESS = 'assembly.progress',
  ASSEMBLY_COMPLETED = 'assembly.completed',

  // Export events
  EXPORT_STARTED = 'export.started',
  EXPORT_PROGRESS = 'export.progress',
  EXPORT_COMPLETED = 'export.completed',

  // Agent events
  AGENT_ACTION = 'agent.action',
  AGENT_DECISION = 'agent.decision',

  // Project events
  PROJECT_UPDATED = 'project.updated',
  SNAPSHOT_CREATED = 'snapshot.created',

  // Error events
  BACKEND_ERROR = 'backend.error',
}

// ============================================================================
// React Hook: useWebSocketEvent
// ============================================================================

/**
 * React hook to subscribe to a specific WebSocket event type.
 * Automatically cleans up the subscription on unmount.
 *
 * The handler receives a full WebSocketMessage<T> so consumers can
 * access event.payload (matching the pattern used across the codebase).
 *
 * @param eventType - The event type to subscribe to
 * @param handler - Callback invoked with the full WebSocketMessage
 */
export function useWebSocketEvent<T = unknown>(
  eventType: EventType | string,
  handler: (message: WebSocketMessage<T>) => void
): void {
  // Inline React import to avoid top-level import in a non-React file
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const { useEffect, useRef } = require('react');

  const handlerRef = useRef(handler);
  handlerRef.current = handler;

  useEffect(() => {
    let unsubscribe: (() => void) | undefined;

    try {
      const manager = getWebSocketManager();
      unsubscribe = manager.subscribe<T>(eventType, (payload) => {
        // Wrap payload in WebSocketMessage shape so consumers
        // can use event.payload.* consistently
        handlerRef.current({
          type: eventType,
          payload,
          timestamp: Date.now(),
        });
      });
    } catch {
      // WebSocket manager not initialized yet — no-op
    }

    return () => {
      unsubscribe?.();
    };
  }, [eventType]);
}

// ============================================================================
// Connection Status Helpers (used by connection-status.tsx)
// ============================================================================

interface ConnectionStatusInfo {
  label: string;
  message: string;
  color: 'green' | 'yellow' | 'red' | 'blue';
  icon: string;
}

export function getConnectionStatusInfo(
  state: ConnectionState,
  reconnectAttempts: number = 0,
  error: string | null = null
): ConnectionStatusInfo {
  switch (state) {
    case ConnectionState.CONNECTED:
      return {
        label: 'Connected',
        message: 'Real-time updates active',
        color: 'green',
        icon: 'connected',
      };
    case ConnectionState.CONNECTING:
      return {
        label: 'Connecting',
        message: 'Establishing connection...',
        color: 'blue',
        icon: 'reconnecting',
      };
    case ConnectionState.RECONNECTING:
      return {
        label: 'Reconnecting',
        message: `Attempt ${reconnectAttempts}...`,
        color: 'yellow',
        icon: 'reconnecting',
      };
    case ConnectionState.POLLING:
      return {
        label: 'Polling',
        message: 'Using fallback polling',
        color: 'yellow',
        icon: 'polling',
      };
    case ConnectionState.ERROR:
      return { label: 'Error', message: error || 'Connection error', color: 'red', icon: 'error' };
    case ConnectionState.DISCONNECTED:
    default:
      return {
        label: 'Disconnected',
        message: 'No connection',
        color: 'red',
        icon: 'disconnected',
      };
  }
}

// ============================================================================
// WebSocket Store (Zustand-compatible reactive state)
// ============================================================================

interface WebSocketStoreState {
  connectionState: ConnectionState;
  error: string | null;
  reconnectAttempts: number;
  isPolling: boolean;
}

type StoreListener = () => void;

class WebSocketStore {
  private state: WebSocketStoreState = {
    connectionState: ConnectionState.DISCONNECTED,
    error: null,
    reconnectAttempts: 0,
    isPolling: false,
  };
  private listeners = new Set<StoreListener>();

  getState(): WebSocketStoreState {
    return this.state;
  }

  setState(partial: Partial<WebSocketStoreState>): void {
    this.state = { ...this.state, ...partial };
    this.listeners.forEach((l) => l());
  }

  subscribe(listener: StoreListener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }
}

const wsStore = new WebSocketStore();

/** React hook to access WebSocket connection state */
export function useWebSocketStore(): WebSocketStoreState {
  const { useSyncExternalStore } = require('react');
  return useSyncExternalStore(
    (cb: StoreListener) => wsStore.subscribe(cb),
    () => wsStore.getState()
  );
}

// ============================================================================
// WebSocket Client Singleton (used by connection-status.tsx)
// ============================================================================

class WebSocketClient {
  private manager: WebSocketManager | null = null;

  initialize(url: string): void {
    this.manager = new WebSocketManager({
      url,
      onStatusChange: (status) => {
        wsStore.setState({
          connectionState: status as ConnectionState,
          error: status === 'error' ? 'Connection failed' : null,
        });
      },
    });
  }

  connect(): void {
    this.manager?.connect();
  }

  disconnect(): void {
    this.manager?.disconnect();
  }

  forceReconnect(): void {
    this.disconnect();
    wsStore.setState({ reconnectAttempts: 0, error: null });
    setTimeout(() => this.connect(), 100);
  }

  send<T>(type: string, payload: T): boolean {
    return this.manager?.send(type, payload) ?? false;
  }

  getManager(): WebSocketManager | null {
    return this.manager;
  }
}

export const wsClient = new WebSocketClient();
