"use client";

import { useEffect, useState } from "react";
import { useWebSocket, categoryLabel, categoryColor } from "@/hooks/useWebSocket";
import {
  TrendingUp, Award, Zap, Wifi, WifiOff, Search, Filter,
} from "lucide-react";

const CAT_OPTIONS = [
  { value: "", label: "All Categories" },
  { value: "ev_charger", label: "EV Charger" },
  { value: "commercial_electrical", label: "Commercial" },
  { value: "general_electrical", label: "General" },
  { value: "solar_electrical", label: "Solar" },
  { value: "generator", label: "Generator" },
  { value: "lighting", label: "Lighting" },
];

export default function Dashboard() {
  const { isConnected, stats, leads, loadLeads } = useWebSocket();
  const [category, setCategory] = useState("");
  const [minScore, setMinScore] = useState("");

  useEffect(() => {
    loadLeads({ category: category || undefined, minScore: minScore ? Number(minScore) : undefined });
  }, [loadLeads, category, minScore]);

  const evLeads = leads.filter((l) => l.service_category === "ev_charger").slice(0, 10);

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100">
      <header className="border-b border-gray-800">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-yellow-400 flex items-center gap-2">
              <Zap className="w-6 h-6" /> Amy Electric
            </h1>
            <p className="text-gray-500 text-xs">Lead Generation Agent — Los Angeles</p>
          </div>
          <div className="flex items-center gap-2">
            {isConnected ? (
              <Wifi className="w-4 h-4 text-green-400" />
            ) : (
              <WifiOff className="w-4 h-4 text-red-400" />
            )}
            <span className="text-xs text-gray-400">
              {isConnected ? "Live" : "Reconnecting..."}
            </span>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6">
        {stats && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
            <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-400 text-xs uppercase tracking-wide mb-1">Total Leads</p>
                  <p className="text-3xl font-bold text-white">{stats.total_leads}</p>
                </div>
                <div className="bg-blue-900/30 p-3 rounded-lg">
                  <TrendingUp className="w-6 h-6 text-blue-400" />
                </div>
              </div>
            </div>
            <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-400 text-xs uppercase tracking-wide mb-1">High Value (≥50)</p>
                  <p className="text-3xl font-bold text-green-400">{stats.high_value_leads}</p>
                </div>
                <div className="bg-green-900/30 p-3 rounded-lg">
                  <Award className="w-6 h-6 text-green-400" />
                </div>
              </div>
            </div>
            <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-400 text-xs uppercase tracking-wide mb-1">EV Charger</p>
                  <p className="text-3xl font-bold text-yellow-400">{stats.by_category.ev_charger || 0}</p>
                </div>
                <div className="bg-yellow-900/30 p-3 rounded-lg">
                  <Zap className="w-6 h-6 text-yellow-400" />
                </div>
              </div>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          <div className="lg:col-span-3">
            <div className="bg-gray-800 rounded-xl border border-gray-700">
              <div className="p-4 border-b border-gray-700">
                <div className="flex flex-wrap items-center gap-3">
                  <Filter className="w-4 h-4 text-gray-400" />
                  <select
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                    className="bg-gray-700 text-sm rounded-lg px-3 py-2 border border-gray-600 text-gray-200"
                  >
                    {CAT_OPTIONS.map((o) => (
                      <option key={o.value} value={o.value}>{o.label}</option>
                    ))}
                  </select>
                  <input
                    type="number"
                    value={minScore}
                    onChange={(e) => setMinScore(e.target.value)}
                    placeholder="Min score"
                    className="bg-gray-700 text-sm rounded-lg px-3 py-2 border border-gray-600 w-24 text-gray-200"
                  />
                </div>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-gray-500 border-b border-gray-700 text-xs uppercase tracking-wide">
                      <th className="text-left py-3 px-4">Score</th>
                      <th className="text-left py-3 px-4">Company</th>
                      <th className="text-left py-3 px-4">Category</th>
                      <th className="text-left py-3 px-4">Zip</th>
                      <th className="text-left py-3 px-4">Contact</th>
                    </tr>
                  </thead>
                  <tbody>
                    {leads.length === 0 && (
                      <tr>
                        <td colSpan={5} className="text-center py-12 text-gray-500">No leads found</td>
                      </tr>
                    )}
                    {leads.map((l) => (
                      <tr key={l.id} className="border-b border-gray-700/50 hover:bg-gray-750 transition-colors">
                        <td className={`py-3 px-4 font-bold ${l.score >= 60 ? "text-green-400" : l.score >= 40 ? "text-yellow-400" : "text-gray-400"}`}>
                          {l.score}
                        </td>
                        <td className="py-3 px-4">
                          <div className="font-medium text-gray-100">{l.company_name || "-"}</div>
                          {l.contact_name && <div className="text-xs text-gray-500">{l.contact_name}</div>}
                        </td>
                        <td className="py-3 px-4">
                          <span className={`text-xs ${categoryColor(l.service_category)} bg-gray-700 px-2 py-1 rounded-md`}>
                            {categoryLabel(l.service_category)}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-gray-400">{l.zip_code || "-"}</td>
                        <td className="py-3 px-4">
                          {l.email && <div className="text-xs text-blue-400 truncate max-w-[180px]">{l.email}</div>}
                          {l.phone && <div className="text-xs text-gray-400">{l.phone}</div>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          <div className="space-y-6">
            <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
              <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide mb-4">Categories</h2>
              {stats && (() => {
                const total = stats.total_leads || 1;
                const barColors: Record<string, string> = {
                  ev_charger: "bg-yellow-500",
                  commercial_electrical: "bg-blue-500",
                  general_electrical: "bg-gray-500",
                  solar_electrical: "bg-orange-500",
                  generator: "bg-purple-500",
                  lighting: "bg-green-500",
                };
                return (
                  <div className="space-y-3">
                    {Object.entries(stats.by_category)
                      .sort(([, a], [, b]) => b - a)
                      .map(([k, v]) => (
                        <div key={k}>
                          <div className="flex justify-between text-xs mb-1">
                            <span className="text-gray-400">{categoryLabel(k)}</span>
                            <span className="text-gray-300 font-medium">{v}</span>
                          </div>
                          <div className="w-full bg-gray-700 rounded-full h-2">
                            <div className={`${barColors[k] || "bg-blue-500"} rounded-full h-2 transition-all`} style={{ width: `${(v / total) * 100}%` }} />
                          </div>
                        </div>
                      ))}
                  </div>
                );
              })()}
            </div>

            <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
              <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide mb-4">Top EV Leads</h2>
              {evLeads.length === 0 ? (
                <p className="text-gray-500 text-sm">No EV charger leads yet</p>
              ) : (
                <div className="space-y-2">
                  {evLeads.map((l) => (
                    <div key={l.id} className="bg-gray-700/50 rounded-lg p-3">
                      <div className="font-medium text-sm text-gray-100">{l.company_name || "Unknown"}</div>
                      <div className="text-xs text-gray-400 mt-1">
                        {l.zip_code} · Score: {l.score}
                        {l.email && <span> · {l.email}</span>}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
