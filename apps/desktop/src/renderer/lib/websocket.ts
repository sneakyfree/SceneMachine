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
            onOpen: () => { },
            onClose: () => { },
            onError: () => { },
            onMessage: () => { },
            onStatusChange: () => { },
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
            console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.options.maxReconnectAttempts})...`);
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
