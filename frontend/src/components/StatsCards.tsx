"use client";

import { TrendingUp, Zap, Award } from "lucide-react";

interface StatsCardsProps {
  stats: {
    total_leads: number;
    high_value_leads: number;
    by_category: Record<string, number>;
  } | null;
}

const CAT_LABELS: Record<string, string> = {
  ev_charger: "EV Charger",
  commercial_electrical: "Commercial",
  general_electrical: "General",
  solar_electrical: "Solar",
  generator: "Generator",
  lighting: "Lighting",
};

export function StatsCards({ stats }: StatsCardsProps) {
  if (!stats) return null;

  const evCount = stats.by_category.ev_charger || 0;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
      <div className="bg-gray-800 rounded-lg p-5 border border-gray-700">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-gray-400 text-sm mb-1">Total Leads</p>
            <p className="text-3xl font-bold text-white">{stats.total_leads}</p>
          </div>
          <div className="bg-blue-900/30 p-3 rounded-lg">
            <TrendingUp className="w-6 h-6 text-blue-400" />
          </div>
        </div>
      </div>

      <div className="bg-gray-800 rounded-lg p-5 border border-gray-700">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-gray-400 text-sm mb-1">High Value (≥50)</p>
            <p className="text-3xl font-bold text-green-400">{stats.high_value_leads}</p>
          </div>
          <div className="bg-green-900/30 p-3 rounded-lg">
            <Award className="w-6 h-6 text-green-400" />
          </div>
        </div>
      </div>

      <div className="bg-gray-800 rounded-lg p-5 border border-gray-700">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-gray-400 text-sm mb-1">EV Charger Leads</p>
            <p className="text-3xl font-bold text-yellow-400">{evCount}</p>
          </div>
          <div className="bg-yellow-900/30 p-3 rounded-lg">
            <Zap className="w-6 h-6 text-yellow-400" />
          </div>
        </div>
      </div>
    </div>
  );
}