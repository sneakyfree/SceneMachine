/**
 * IPC client for communicating with Python backend.
 */

import * as net from 'net';
import { EventEmitter } from 'events';
import { v4 as uuidv4 } from 'uuid';

interface IPCMessage {
  type: 'request' | 'response' | 'notification' | 'stream';
  method: string;
  id: string;
  params?: Record<string, unknown>;
  result?: unknown;
  error?: {
    code: string;
    message: string;
  };
}

interface PendingRequest {
  resolve: (value: unknown) => void;
  reject: (error: Error) => void;
  timeout: NodeJS.Timeout;
}

/**
 * IPC client for communicating with Python backend via Unix socket.
 */
export class IPCClient extends EventEmitter {
  private socket: net.Socket | null = null;
  private socketPath: string;
  private connected = false;
  private pendingRequests: Map<string, PendingRequest> = new Map();
  private buffer: Buffer = Buffer.alloc(0);
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private reconnectDelay = 1000;
  private reconnectTimer: NodeJS.Timeout | null = null;

  constructor(socketPath: string) {
    super();
    this.socketPath = socketPath;
  }

  /**
   * Check if client is connected.
   */
  get isConnected(): boolean {
    return this.connected;
  }

  /**
   * Connect to the IPC server.
   */
  async connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.socket = net.createConnection(this.socketPath);

      this.socket.on('connect', () => {
        this.connected = true;
        this.reconnectAttempts = 0;
        this.emit('connected');
        resolve();
      });

      this.socket.on('data', (data) => this.handleData(data));

      this.socket.on('close', () => {
        this.connected = false;
        this.emit('disconnected');
        this.attemptReconnect();
      });

      this.socket.on('error', (error) => {
        if (!this.connected) {
          reject(error);
        }
        this.emit('error', error);
      });

      // Connection timeout
      setTimeout(() => {
        if (!this.connected) {
          reject(new Error('Connection timeout'));
        }
      }, 10000);
    });
  }

  /**
   * Handle incoming data from socket.
   */
  private handleData(data: Buffer): void {
    this.buffer = Buffer.concat([this.buffer, data]);

    // Process complete messages
    while (this.buffer.length >= 4) {
      const length = this.buffer.readUInt32BE(0);

      if (length === 0 || length > 10_000_000) {
        console.error(`Invalid message length: ${length}`);
        this.buffer = Buffer.alloc(0);
        return;
      }

      if (this.buffer.length < 4 + length) {
        // Wait for more data
        break;
      }

      const messageData = this.buffer.subarray(4, 4 + length);
      this.buffer = this.buffer.subarray(4 + length);

      try {
        const message: IPCMessage = JSON.parse(messageData.toString('utf-8'));
        this.handleMessage(message);
      } catch (error) {
        console.error('Failed to parse IPC message:', error);
        this.emit('error', new Error(`Failed to parse IPC message: ${error}`));
      }
    }
  }

  /**
   * Handle a parsed message.
   */
  private handleMessage(message: IPCMessage): void {
    if (message.type === 'response') {
      const pending = this.pendingRequests.get(message.id);
      if (pending) {
        clearTimeout(pending.timeout);
        this.pendingRequests.delete(message.id);

        if (message.error) {
          pending.reject(new Error(`${message.error.code}: ${message.error.message}`));
        } else {
          pending.resolve(message.result);
        }
      }
    } else if (message.type === 'notification') {
      this.emit('notification', message);
    } else if (message.type === 'stream') {
      this.emit('stream', message);
    }
  }

  /**
   * Send a request to the backend.
   */
  async request<T>(
    method: string,
    params?: Record<string, unknown>,
    timeoutMs = 30000
  ): Promise<T> {
    if (!this.connected || !this.socket) {
      throw new Error('Not connected to IPC server');
    }

    const id = uuidv4();
    const message: IPCMessage = {
      type: 'request',
      method,
      id,
      params,
    };

    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        this.pendingRequests.delete(id);
        reject(new Error(`Request timeout: ${method}`));
      }, timeoutMs);

      this.pendingRequests.set(id, {
        resolve: resolve as (value: unknown) => void,
        reject,
        timeout,
      });

      const data = Buffer.from(JSON.stringify(message), 'utf-8');
      const lengthBuffer = Buffer.alloc(4);
      lengthBuffer.writeUInt32BE(data.length, 0);

      this.socket!.write(lengthBuffer);
      this.socket!.write(data);
    });
  }

  /**
   * Attempt to reconnect to the server.
   */
  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      this.emit('reconnectFailed');
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(1.5, this.reconnectAttempts - 1);

    console.log(
      `Attempting reconnect ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${delay}ms`
    );

    this.reconnectTimer = setTimeout(() => {
      this.connect().catch(() => {
        // Will trigger another reconnect attempt via 'close' event
      });
    }, delay);
  }

  /**
   * Disconnect from the server.
   */
  disconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    // Cancel pending requests
    for (const [_id, pending] of this.pendingRequests) {
      clearTimeout(pending.timeout);
      pending.reject(new Error('Disconnected'));
    }
    this.pendingRequests.clear();

    if (this.socket) {
      this.socket.destroy();
      this.socket = null;
    }
    this.connected = false;
  }
}


