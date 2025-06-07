import { useState, useEffect, useCallback, useRef } from 'react';

type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

export function useWebSocket<T>(urlFactory: (requestId: string) => string) {
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
  const [lastMessage, setLastMessage] = useState<T | null>(null);
  const socket = useRef<WebSocket | null>(null);
  const activeRequestId = useRef<string | null>(null);
  
  // Connect to WebSocket
  const connect = useCallback((requestId: string) => {
    if (!requestId) return;
    
    // Store the request ID
    activeRequestId.current = requestId;
    
    // Close previous connection if any
    if (socket.current) {
      socket.current.close();
    }
    
    // Connect to new WebSocket
    try {
      setConnectionStatus('connecting');
      const wsUrl = urlFactory(requestId);
      socket.current = new WebSocket(wsUrl);
      
      socket.current.onopen = () => {
        setConnectionStatus('connected');
        console.log(`WebSocket connected for request ${requestId}`);
      };
      
      socket.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as T;
          setLastMessage(data);
          console.log('WebSocket message received:', data);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };
      
      socket.current.onclose = () => {
        setConnectionStatus('disconnected');
        console.log(`WebSocket disconnected for request ${requestId}`);
      };
      
      socket.current.onerror = (error) => {
        setConnectionStatus('error');
        console.error('WebSocket error:', error);
      };
      
    } catch (error) {
      console.error('Error creating WebSocket connection:', error);
      setConnectionStatus('error');
    }
  }, [urlFactory]);
  
  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    if (socket.current) {
      socket.current.close();
      socket.current = null;
      activeRequestId.current = null;
    }
  }, []);
  
  // Send message to WebSocket
  const sendMessage = useCallback((message: string) => {
    if (socket.current && socket.current.readyState === WebSocket.OPEN) {
      socket.current.send(message);
      return true;
    }
    return false;
  }, []);
  
  // Clean up WebSocket on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);
  
  return {
    connect,
    disconnect,
    sendMessage,
    lastMessage,
    connectionStatus,
    activeRequestId: activeRequestId.current,
  };
}
