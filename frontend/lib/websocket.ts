/**
 * WebSocket Client for TradeMaster Pro
 *
 * Real-time data streaming using Socket.io
 * Connects to FastAPI backend with Socket.io support
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { io, Socket } from 'socket.io-client';
import { getApiBaseUrl } from './api';

// WebSocket configuration
const resolveSocketUrl = () => {
  const envSocketUrl = process.env.NEXT_PUBLIC_WS_URL || process.env.NEXT_PUBLIC_WEBSOCKET_URL;
  const trimmed = envSocketUrl ? envSocketUrl.trim() : '';
  if (trimmed) {
    return trimmed;
  }
  return getApiBaseUrl().replace(/^http/, 'ws');
};

const SOCKET_URL = resolveSocketUrl();
const RECONNECTION_ATTEMPTS = 5;
const RECONNECTION_DELAY = 3000; // 3 seconds

// Supported channels
export type WebSocketChannel = 'prices' | 'news' | 'social' | 'predictions' | 'alerts';

// Message types for different channels
export interface PriceUpdate {
  ticker: string;
  price: number;
  change: number;
  changePercent: number;
  volume: number;
  timestamp: string;
}

export interface NewsUpdate {
  id: string;
  ticker?: string;
  headline: string;
  summary: string;
  category: string;
  isHot: boolean;
  impact: 'LOW' | 'MEDIUM' | 'HIGH';
  timestamp: string;
  url?: string;
  source?: string;
}

export interface SocialUpdate {
  ticker: string;
  platform: 'reddit' | 'twitter' | 'stocktwits';
  mentions: number;
  sentiment: number;
  spike: boolean; // True if unusual activity
  timestamp: string;
}

export interface PredictionUpdate {
  ticker: string;
  type: 'stock' | 'crypto';
  score: number;
  signal: string;
  timestamp: string;
}

export type WebSocketMessage = PriceUpdate | NewsUpdate | SocialUpdate | PredictionUpdate;

// Connection status
export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

// ============================================================================
// SOCKET CLIENT CLASS
// ============================================================================

class WebSocketClient {
  private socket: Socket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = RECONNECTION_ATTEMPTS;
  private subscriptions = new Set<string>();
  private listeners = new Map<string, Set<(data: any) => void>>();
  private statusListeners = new Set<(status: ConnectionStatus) => void>();
  private currentStatus: ConnectionStatus = 'disconnected';

  constructor() {
    // Initialize socket but don't connect yet
    // Connection happens on first subscribe
  }

  /**
   * Initialize socket connection
   */
  private initializeSocket() {
    if (this.socket) {
      return;
    }

    // Skip WebSocket connection - all data comes from REST API
    // WebSocket is optional for real-time streaming
    console.log('[WebSocket] Skipping connection - using REST API instead');
    this.updateStatus('disconnected');
    return;

    // Original connection code (disabled)
    /*
    console.log('[WebSocket] Initializing connection to:', SOCKET_URL);
    this.updateStatus('connecting');

    this.socket = io(SOCKET_URL, {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: this.maxReconnectAttempts,
      reconnectionDelay: RECONNECTION_DELAY,
      timeout: 10000,
    });

    this.setupEventHandlers();
    */
  }

  /**
   * Setup Socket.io event handlers
   */
  private setupEventHandlers() {
    if (!this.socket) return;

    // Connection events
    this.socket.on('connect', () => {
      console.log('[WebSocket] Connected:', this.socket?.id);
      this.updateStatus('connected');
      this.reconnectAttempts = 0;

      // Resubscribe to channels after reconnection
      this.resubscribeAll();
    });

    this.socket.on('disconnect', (reason) => {
      console.log('[WebSocket] Disconnected:', reason);
      this.updateStatus('disconnected');
    });

    this.socket.on('connect_error', (error) => {
      console.error('[WebSocket] Connection error:', error.message);
      this.updateStatus('error');
      this.reconnectAttempts++;

      if (this.reconnectAttempts >= this.maxReconnectAttempts) {
        console.error('[WebSocket] Max reconnection attempts reached');
      }
    });

    this.socket.on('reconnect', (attemptNumber) => {
      console.log(`[WebSocket] Reconnected after ${attemptNumber} attempts`);
      this.updateStatus('connected');
    });

    this.socket.on('reconnect_attempt', (attemptNumber) => {
      console.log(`[WebSocket] Reconnection attempt ${attemptNumber}/${this.maxReconnectAttempts}`);
    });

    this.socket.on('reconnect_error', (error) => {
      console.error('[WebSocket] Reconnection error:', error.message);
    });

    this.socket.on('reconnect_failed', () => {
      console.error('[WebSocket] Reconnection failed');
      this.updateStatus('error');
    });

    // Channel-specific events
    this.socket.on('price_update', (data: PriceUpdate) => {
      this.notifyListeners('prices', data);
    });

    this.socket.on('news_update', (data: NewsUpdate) => {
      this.notifyListeners('news', data);
    });

    this.socket.on('social_update', (data: SocialUpdate) => {
      this.notifyListeners('social', data);
    });

    this.socket.on('prediction_update', (data: PredictionUpdate) => {
      this.notifyListeners('predictions', data);
    });

    // Generic message handler
    this.socket.on('message', (data: any) => {
      console.log('[WebSocket] Message received:', data);
    });
  }

  /**
   * Update connection status and notify listeners
   */
  private updateStatus(status: ConnectionStatus) {
    this.currentStatus = status;
    this.statusListeners.forEach(listener => listener(status));
  }

  /**
   * Notify all listeners for a specific channel
   */
  private notifyListeners(channel: string, data: any) {
    const channelListeners = this.listeners.get(channel);
    if (channelListeners) {
      channelListeners.forEach(listener => listener(data));
    }
  }

  /**
   * Resubscribe to all channels after reconnection
   */
  private resubscribeAll() {
    this.subscriptions.forEach(channel => {
      this.subscribe(channel as WebSocketChannel);
    });
  }

  /**
   * Subscribe to a channel
   */
  public subscribe(channel: WebSocketChannel, ticker?: string) {
    // Initialize socket if not already done
    if (!this.socket) {
      this.initializeSocket();
    }

    const subscriptionKey = ticker ? `${channel}:${ticker}` : channel;

    if (this.subscriptions.has(subscriptionKey)) {
      console.log(`[WebSocket] Already subscribed to ${subscriptionKey}`);
      return;
    }

    console.log(`[WebSocket] Subscribing to ${subscriptionKey}`);
    this.subscriptions.add(subscriptionKey);

    // Send subscription event to server
    if (this.socket?.connected) {
      if (ticker) {
        this.socket.emit('subscribe_ticker', { channel, ticker });
      } else {
        this.socket.emit('subscribe', { channel });
      }
    }
  }

  /**
   * Unsubscribe from a channel
   */
  public unsubscribe(channel: WebSocketChannel, ticker?: string) {
    const subscriptionKey = ticker ? `${channel}:${ticker}` : channel;

    if (!this.subscriptions.has(subscriptionKey)) {
      return;
    }

    console.log(`[WebSocket] Unsubscribing from ${subscriptionKey}`);
    this.subscriptions.delete(subscriptionKey);

    // Send unsubscription event to server
    if (this.socket?.connected) {
      if (ticker) {
        this.socket.emit('unsubscribe_ticker', { channel, ticker });
      } else {
        this.socket.emit('unsubscribe', { channel });
      }
    }
  }

  /**
   * Add listener for a specific channel
   */
  public addListener(channel: WebSocketChannel, callback: (data: any) => void) {
    if (!this.listeners.has(channel)) {
      this.listeners.set(channel, new Set());
    }
    this.listeners.get(channel)!.add(callback);
  }

  /**
   * Remove listener for a specific channel
   */
  public removeListener(channel: WebSocketChannel, callback: (data: any) => void) {
    const channelListeners = this.listeners.get(channel);
    if (channelListeners) {
      channelListeners.delete(callback);
    }
  }

  /**
   * Add status listener
   */
  public addStatusListener(callback: (status: ConnectionStatus) => void) {
    this.statusListeners.add(callback);
    // Immediately call with current status
    callback(this.currentStatus);
  }

  /**
   * Remove status listener
   */
  public removeStatusListener(callback: (status: ConnectionStatus) => void) {
    this.statusListeners.delete(callback);
  }

  /**
   * Get current connection status
   */
  public getStatus(): ConnectionStatus {
    return this.currentStatus;
  }

  /**
   * Check if connected
   */
  public isConnected(): boolean {
    return this.socket?.connected || false;
  }

  /**
   * Manually connect
   */
  public connect() {
    if (!this.socket) {
      this.initializeSocket();
    } else if (!this.socket.connected) {
      this.socket.connect();
    }
  }

  /**
   * Manually disconnect
   */
  public disconnect() {
    if (this.socket) {
      console.log('[WebSocket] Disconnecting...');
      this.socket.disconnect();
      this.subscriptions.clear();
    }
  }

  /**
   * Send custom event to server
   */
  public emit(event: string, data: any) {
    if (this.socket?.connected) {
      this.socket.emit(event, data);
    } else {
      console.warn('[WebSocket] Cannot emit, not connected');
    }
  }
}

// Global singleton instance
let websocketClient: WebSocketClient | null = null;

/**
 * Get or create global WebSocket client
 */
export function getWebSocketClient(): WebSocketClient {
  if (!websocketClient) {
    websocketClient = new WebSocketClient();
  }
  return websocketClient;
}

// ============================================================================
// REACT HOOKS
// ============================================================================

/**
 * React hook for WebSocket connection to a specific channel
 *
 * @param channel - Channel to subscribe to
 * @param ticker - Optional ticker symbol for ticker-specific updates
 * @param autoConnect - Automatically connect on mount (default: true)
 * @returns Object with data, status, and control methods
 *
 * @example
 * ```tsx
 * const { data, status, isConnected } = useWebSocket('prices', 'NVDA');
 *
 * useEffect(() => {
 *   if (data) {
 *     console.log('Price update:', data);
 *   }
 * }, [data]);
 * ```
 */
export function useWebSocket<T = WebSocketMessage>(
  channel: WebSocketChannel,
  ticker?: string,
  autoConnect: boolean = true
) {
  const [data, setData] = useState<T | null>(null);
  const [status, setStatus] = useState<ConnectionStatus>('disconnected');
  const [error, setError] = useState<Error | null>(null);
  const clientRef = useRef<WebSocketClient>();
  const callbackRef = useRef<(data: any) => void>();

  // Initialize client
  useEffect(() => {
    clientRef.current = getWebSocketClient();
  }, []);

  // Handle messages
  const handleMessage = useCallback((message: any) => {
    try {
      setData(message as T);
      setError(null);
    } catch (err) {
      setError(err as Error);
      console.error('[useWebSocket] Error processing message:', err);
    }
  }, []);

  // Store callback ref
  useEffect(() => {
    callbackRef.current = handleMessage;
  }, [handleMessage]);

  // Subscribe/unsubscribe
  useEffect(() => {
    const client = clientRef.current;
    if (!client || !autoConnect) return;

    // Subscribe to channel
    client.subscribe(channel, ticker);

    // Add listener
    const listener = (data: any) => {
      callbackRef.current?.(data);
    };
    client.addListener(channel, listener);

    // Add status listener
    const statusListener = (newStatus: ConnectionStatus) => {
      setStatus(newStatus);
    };
    client.addStatusListener(statusListener);

    // Cleanup
    return () => {
      client.removeListener(channel, listener);
      client.removeStatusListener(statusListener);
      client.unsubscribe(channel, ticker);
    };
  }, [channel, ticker, autoConnect]);

  // Control methods
  const connect = useCallback(() => {
    clientRef.current?.connect();
  }, []);

  const disconnect = useCallback(() => {
    clientRef.current?.disconnect();
  }, []);

  const clearData = useCallback(() => {
    setData(null);
  }, []);

  return {
    data,
    status,
    error,
    isConnected: status === 'connected',
    isConnecting: status === 'connecting',
    isDisconnected: status === 'disconnected',
    hasError: status === 'error',
    connect,
    disconnect,
    clearData,
  };
}

/**
 * React hook for multiple WebSocket channels
 *
 * @param channels - Array of channels to subscribe to
 * @returns Map of channel data and connection status
 *
 * @example
 * ```tsx
 * const { data, status } = useMultipleWebSockets(['prices', 'news', 'social']);
 *
 * const priceData = data.get('prices');
 * const newsData = data.get('news');
 * ```
 */
export function useMultipleWebSockets(channels: WebSocketChannel[]) {
  const [data, setData] = useState<Map<WebSocketChannel, any>>(new Map());
  const [status, setStatus] = useState<ConnectionStatus>('disconnected');
  const clientRef = useRef<WebSocketClient>();

  useEffect(() => {
    clientRef.current = getWebSocketClient();
    const client = clientRef.current;

    // Subscribe to all channels
    const listeners = new Map<WebSocketChannel, (data: any) => void>();

    channels.forEach(channel => {
      client.subscribe(channel);

      const listener = (channelData: any) => {
        setData(prev => new Map(prev).set(channel, channelData));
      };

      listeners.set(channel, listener);
      client.addListener(channel, listener);
    });

    // Status listener
    const statusListener = (newStatus: ConnectionStatus) => {
      setStatus(newStatus);
    };
    client.addStatusListener(statusListener);

    // Cleanup
    return () => {
      listeners.forEach((listener, channel) => {
        client.removeListener(channel, listener);
        client.unsubscribe(channel);
      });
      client.removeStatusListener(statusListener);
    };
  }, [channels.join(',')]);

  return {
    data,
    status,
    isConnected: status === 'connected',
  };
}

/**
 * React hook for WebSocket connection status only
 *
 * @returns Connection status and control methods
 */
export function useWebSocketStatus() {
  const [status, setStatus] = useState<ConnectionStatus>('disconnected');
  const clientRef = useRef<WebSocketClient>();

  useEffect(() => {
    clientRef.current = getWebSocketClient();
    const client = clientRef.current;

    const statusListener = (newStatus: ConnectionStatus) => {
      setStatus(newStatus);
    };

    client.addStatusListener(statusListener);

    return () => {
      client.removeStatusListener(statusListener);
    };
  }, []);

  const connect = useCallback(() => {
    clientRef.current?.connect();
  }, []);

  const disconnect = useCallback(() => {
    clientRef.current?.disconnect();
  }, []);

  return {
    status,
    isConnected: status === 'connected',
    isConnecting: status === 'connecting',
    isDisconnected: status === 'disconnected',
    hasError: status === 'error',
    connect,
    disconnect,
  };
}

// Export singleton for direct access if needed
export { websocketClient };
