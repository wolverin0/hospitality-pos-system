
import { useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { WebSocketEvent } from '@/types/ticket.types';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/kds';
const RECONNECT_INTERVAL = 3000;

export const useTicketSocket = () => {
  const [isConnected, setIsConnected] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);
  const queryClient = useQueryClient();

  useEffect(() => {
    const connect = () => {
      if (socketRef.current?.readyState === WebSocket.OPEN) return;

      const ws = new WebSocket(WS_URL);
      socketRef.current = ws;

      ws.onopen = () => {
        console.log('KDS WebSocket Connected');
        setIsConnected(true);
      };

      ws.onclose = () => {
        console.log('KDS WebSocket Disconnected');
        setIsConnected(false);
        setTimeout(connect, RECONNECT_INTERVAL);
      };

      ws.onerror = (error) => {
        console.error('KDS WebSocket Error:', error);
        ws.close();
      };

      ws.onmessage = (event) => {
        try {
          const data: WebSocketEvent = JSON.parse(event.data);
          handleSocketMessage(data);
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e);
        }
      };
    };

    const handleSocketMessage = (event: WebSocketEvent) => {
      // Invalidate queries based on event type
      switch (event.type) {
        case 'TicketCreated':
        case 'TicketUpdated':
        case 'TicketFired':
        case 'TicketHeld':
        case 'TicketVoided':
        case 'TicketCompleted':
          queryClient.invalidateQueries({ queryKey: ['tickets'] });
          break;
      }
    };

    connect();

    return () => {
      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, [queryClient]);

  return { isConnected };
};
