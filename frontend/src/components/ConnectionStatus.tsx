"use client";

import { Wifi, WifiOff } from "lucide-react";

export function ConnectionStatus({ isConnected }: { isConnected: boolean }) {
  return (
    <div className="flex items-center gap-2">
      {isConnected ? (
        <Wifi className="w-5 h-5 text-green-400" />
      ) : (
        <WifiOff className="w-5 h-5 text-red-400" />
      )}
      <span className="text-sm text-gray-300">
        {isConnected ? "Live" : "Reconnecting..."}
      </span>
    </div>
  );
}