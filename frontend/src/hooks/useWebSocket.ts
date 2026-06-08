"use client";

import { useEffect, useRef, useState, useCallback } from "react";

export interface Lead {
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
  contact_name: string | null;
  estimated_cost: number | null;
  created_at: string | null;
}

export interface Stats {
  total_leads: number;
  high_value_leads: number;
  by_category: Record<string, number>;
}

const CAT_LABELS: Record<string, string> = {
  ev_charger: "EV Charger",
  commercial_electrical: "Commercial",
  general_electrical: "General",
  solar_electrical: "Solar",
  generator: "Generator",
  lighting: "Lighting",
};

export function categoryLabel(cat: string): string {
  return CAT_LABELS[cat] || cat;
}

const CAT_COLORS: Record<string, string> = {
  ev_charger: "text-yellow-400",
  commercial_electrical: "text-blue-400",
  general_electrical: "text-gray-400",
  solar_electrical: "text-orange-400",
  generator: "text-purple-400",
  lighting: "text-green-400",
};

export function categoryColor(cat: string): string {
  return CAT_COLORS[cat] || "text-gray-400";
}

const WS_BASE = typeof window !== "undefined"
  ? (window.location.protocol === "https:" ? "wss:" : "ws:") + "//" + window.location.hostname + ":8000"
  : "ws://localhost:8000";

export function useWebSocket() {
  const [isConnected, setIsConnected] = useState(false);
  const [stats, setStats] = useState<Stats | null>(null);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    try {
      const ws = new WebSocket(`${WS_BASE}/ws`);
      wsRef.current = ws;

      ws.onopen = () => setIsConnected(true);

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          setLastUpdate(new Date());

          if (msg.type === "stats") {
            setStats(msg.payload);
          }
        } catch {
          /* ignore parse errors */
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        reconnectRef.current = setTimeout(connect, 3000);
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {
      reconnectRef.current = setTimeout(connect, 3000);
    }
  }, []);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectRef.current) clearTimeout(reconnectRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const loadLeads = useCallback(async (opts?: {
    category?: string;
    minScore?: number;
    limit?: number;
  }) => {
    const params = new URLSearchParams();
    if (opts?.category) params.set("category", opts.category);
    if (opts?.minScore) params.set("min_score", String(opts.minScore));
    params.set("limit", String(opts?.limit ?? 50));

    try {
      const r = await fetch(`/api/leads?${params}`);
      const data = await r.json();
      if (data.leads) setLeads(data.leads);
    } catch {
      /* ignore */
    }
  }, []);

  return { isConnected, stats, leads, lastUpdate, loadLeads };
}