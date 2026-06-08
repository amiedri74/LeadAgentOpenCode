"use client";

import { useEffect, useRef, useState, useCallback } from "react";

interface Lead {
  id: string;
  company_name: string;
  service_category: string;
  score: number;
  zip_code: string;
  address: string;
  permit_type: string;
  phone: string;
  email: string;
  website: string;
  source: string;
  is_high_value: boolean;
}

interface Stats {
  total_leads: number;
  high_value_leads: number;
  by_category: Record<string, number>;
}

interface WebSocketMessage {
  type: "stats" | "lead_added" | "lead_updated" | "lead_deleted" | "workflow_status";
  payload: any;
}

export function useWebSocket(url: string) {
  const [isConnected, setIsConnected] = useState(false);
  const [stats, setStats] = useState<Stats | null>(null);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const messageHandlersRef = useRef<Map<string, (payload: any) => void>>(new Map());

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        console.log("WebSocket connected");
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          setLastUpdate(new Date());

          switch (message.type) {
            case "stats":
              setStats(message.payload);
              break;
            case "lead_added":
              setLeads((prev) => [message.payload, ...prev].slice(0, 100));
              break;
            case "lead_updated":
              setLeads((prev) =>
                prev.map((l) => (l.id === message.payload.id ? message.payload : l))
              );
              break;
            case "lead_deleted":
              setLeads((prev) => prev.filter((l) => l.id !== message.payload.id));
              break;
            case "workflow_status":
              console.log("Workflow status:", message.payload);
              break;
          }

          const handler = messageHandlersRef.current.get(message.type);
          if (handler) handler(message.payload);
        } catch (e) {
          console.error("Failed to parse WebSocket message:", e);
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        console.log("WebSocket disconnected, reconnecting in 5s...");
        reconnectTimeoutRef.current = setTimeout(connect, 5000);
      };

      ws.onerror = (error) => {
        console.error("WebSocket error:", error);
      };
    } catch (e) {
      console.error("Failed to create WebSocket:", e);
      reconnectTimeoutRef.current = setTimeout(connect, 5000);
    }
  }, [url]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, [connect]);

  const sendMessage = useCallback((type: string, payload: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type, payload }));
    }
  }, []);

  const onMessage = useCallback((type: string, handler: (payload: any) => void) => {
    messageHandlersRef.current.set(type, handler);
    return () => messageHandlersRef.current.delete(type);
  }, []);

  return { isConnected, stats, leads, lastUpdate, sendMessage, onMessage };
}