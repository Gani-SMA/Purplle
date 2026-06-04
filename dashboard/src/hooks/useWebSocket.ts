import { useEffect, useRef, useState } from 'react';

interface WebSocketMessage {
  event_types: string[];
  count: number;
}

export function useWebSocket(storeId: string, onMessage: (msg: WebSocketMessage) => void) {
  const [isConnected, setIsConnected]   = useState(false);
  const [wsEventCount, setWsEventCount] = useState(0);
  const wsRef                           = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef             = useRef<number | null>(null);

  useEffect(() => {
    let active = true;

    function connect() {
      if (wsRef.current) {
        wsRef.current.close();
      }

      let wsUrl = '';
      if (import.meta.env.VITE_WS_URL) {
        wsUrl = `${import.meta.env.VITE_WS_URL}/ws/stores/${storeId}`;
      } else {
        const apiBase = import.meta.env.VITE_API_URL || '';
        if (apiBase.startsWith('http://') || apiBase.startsWith('https://')) {
          const wsProtocol = apiBase.startsWith('https://') ? 'wss:' : 'ws:';
          const host = apiBase.replace(/^https?:\/\//, '');
          wsUrl = `${wsProtocol}//${host}/ws/stores/${storeId}`;
        } else {
          const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
          const host = window.location.host;
          wsUrl = `${protocol}//${host}/ws/stores/${storeId}`;
        }
      }

      console.log(`Connecting to WebSocket: ${wsUrl}`);
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        if (active) {
          console.log(`WebSocket connected: ${storeId}`);
          setIsConnected(true);
        }
      };

      ws.onmessage = (event) => {
        if (!active) return;
        try {
          const data = JSON.parse(event.data) as WebSocketMessage;
          console.log('WebSocket message received:', data);
          setWsEventCount(c => c + 1);
          onMessage(data);
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err);
        }
      };

      ws.onclose = (event) => {
        if (active) {
          console.log(`WebSocket closed: ${storeId}`, event.reason);
          setIsConnected(false);
          // Try reconnecting in 3 seconds
          reconnectTimeoutRef.current = window.setTimeout(() => {
            connect();
          }, 3000);
        }
      };

      ws.onerror = (err) => {
        console.error('WebSocket error:', err);
        ws.close();
      };
    }

    connect();

    return () => {
      active = false;
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [storeId]);

  return { isConnected, wsEventCount };
}
