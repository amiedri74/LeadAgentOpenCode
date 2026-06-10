"use client";

import { useEffect, useState, useCallback } from "react";
import { Zap, Wifi, WifiOff, Download, Search } from "lucide-react";

interface Lead {
  id: string;
  company_name: string;
  service_category: string;
  score: number;
  zip_code: string;
  address: string;
  phone: string;
  email: string;
  website: string;
  source: string;
  source_url: string | null;
  is_high_value: boolean;
  contact_name: string | null;
  estimated_cost: number | null;
  city: string | null;
  created_at: string | null;
}

interface Stats {
  total_leads: number;
  high_value_leads: number;
  by_category: Record<string, number>;
}

const CAT_OPTIONS = [
  { value: "", label: "All Categories" },
  { value: "ev_charger", label: "EV Charger" },
  { value: "commercial_electrical", label: "Commercial" },
  { value: "general_electrical", label: "General" },
  { value: "solar_electrical", label: "Solar" },
  { value: "generator", label: "Generator" },
  { value: "lighting", label: "Lighting" },
];

const CAT_LABELS: Record<string, string> = {
  ev_charger: "EV Charger",
  commercial_electrical: "Commercial",
  general_electrical: "General",
  solar_electrical: "Solar",
  generator: "Generator",
  lighting: "Lighting",
};

function catClass(cat: string): string {
  const m: Record<string, string> = {
    ev_charger: "bg-yellow-900/50 text-yellow-300",
    commercial_electrical: "bg-blue-900/50 text-blue-300",
    general_electrical: "bg-gray-700 text-gray-300",
    solar_electrical: "bg-orange-900/50 text-orange-300",
    generator: "bg-purple-900/50 text-purple-300",
    lighting: "bg-green-900/50 text-green-300",
  };
  return m[cat] || "bg-gray-700 text-gray-300";
}

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [allLeads, setAllLeads] = useState<Lead[]>([]);
  const [category, setCategory] = useState("");
  const [minScore, setMinScore] = useState("");
  const [search, setSearch] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");
  const [contactFilter, setContactFilter] = useState("");
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    fetch("/api/leads/stats").then(r => r.json()).then(setStats).catch(e => console.error("Stats fetch failed:", e));
    fetch("/api/leads?limit=600").then(r => r.json()).then(d => {
      if (d.leads) setAllLeads(d.leads);
    }).catch(e => console.error("Leads fetch failed:", e));
  }, []);

  useEffect(() => {
    const ws = new WebSocket(
      (location.protocol === "https:" ? "wss:" : "ws:") + "//" + location.hostname + ":8000/ws"
    );
    ws.onopen = () => setIsConnected(true);
    ws.onclose = () => setIsConnected(false);
    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        if (msg.type === "stats") setStats(msg.payload);
      } catch (err) {
        console.error("WS message parse error:", err);
      }
    };
    ws.onerror = (err) => console.error("WS error:", err);
    return () => ws.close();
  }, []);

  const filtered = allLeads.filter(l => {
    if (category && l.service_category !== category) return false;
    if (sourceFilter && l.source !== sourceFilter) return false;
    if (minScore && (l.score < parseInt(minScore))) return false;
    if (contactFilter === "has_email") return !!(l.email && l.email.includes("@"));
    if (contactFilter === "has_phone") return !!l.phone;
    if (contactFilter === "has_any") return (l.email && l.email.includes("@")) || !!l.phone || !!l.website;
    if (contactFilter === "no_contact") return !((l.email && l.email.includes("@")) || l.phone || l.website);
    if (search) {
      const q = search.toLowerCase();
      const name = (l.company_name || "").toLowerCase();
      const email = (l.email || "").toLowerCase();
      const phone = (l.phone || "").toLowerCase();
      const addr = (l.address || "").toLowerCase();
      const contact = (l.contact_name || "").toLowerCase();
      if (!name.includes(q) && !email.includes(q) && !phone.includes(q) && !addr.includes(q) && !contact.includes(q)) return false;
    }
    return true;
  }).sort((a, b) => b.score - a.score);

  const exportCSV = useCallback(() => {
    const rows = filtered.map(l => [
      l.score, l.company_name || "", l.contact_name || "", l.phone || "", l.email || "", l.website || "",
      l.source === "ladbs_permit" ? "LADBS" : "Maps",
      CAT_LABELS[l.service_category] || l.service_category,
      l.zip_code || "", l.address || "", l.city || ""
    ]);
    const csv = [["Score", "Company", "Contact Name", "Phone", "Email", "Website", "Source", "Category", "Zip", "Address", "City"], ...rows]
      .map(r => r.map(v => '"' + String(v).replace(/"/g, '""') + '"').join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "amy_electric_leads.csv";
    a.click();
  }, [filtered]);

  const evCount = allLeads.filter(l => l.service_category === "ev_charger").length;
  const withEmail = allLeads.filter(l => l.email && l.email.includes("@")).length;
  const withPhone = allLeads.filter(l => l.phone).length;
  const withWebsite = allLeads.filter(l => l.website && l.website.startsWith("http")).length;

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100">
      <header className="border-b border-gray-800 bg-gray-900/95 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Zap className="w-6 h-6 text-yellow-400" />
            <div>
              <h1 className="text-lg font-bold text-yellow-400">Amy Electric</h1>
              <p className="text-gray-500 text-xs">Lead Generation Agent — Los Angeles</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs text-gray-500">{allLeads.length} leads</span>
            {isConnected ? (
              <Wifi className="w-4 h-4 text-green-400" />
            ) : (
              <WifiOff className="w-4 h-4 text-red-400" />
            )}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-4">
        {stats && (
          <div className="grid grid-cols-2 sm:grid-cols-6 gap-3 mb-4">
            <div className="bg-gray-800 rounded-xl px-4 py-3 border border-gray-700">
              <p className="text-xs text-gray-500 uppercase tracking-wide">Total</p>
              <p className="text-2xl font-bold text-white">{stats.total_leads}</p>
            </div>
            <div className="bg-gray-800 rounded-xl px-4 py-3 border border-gray-700">
              <p className="text-xs text-gray-500 uppercase tracking-wide">High Value</p>
              <p className="text-2xl font-bold text-green-400">{stats.high_value_leads}</p>
            </div>
            <div className="bg-gray-800 rounded-xl px-4 py-3 border border-gray-700">
              <p className="text-xs text-gray-500 uppercase tracking-wide">With Phone</p>
              <p className="text-2xl font-bold text-blue-400">{withPhone}</p>
            </div>
            <div className="bg-gray-800 rounded-xl px-4 py-3 border border-gray-700">
              <p className="text-xs text-gray-500 uppercase tracking-wide">With Email</p>
              <p className="text-2xl font-bold text-yellow-400">{withEmail}</p>
            </div>
            <div className="bg-gray-800 rounded-xl px-4 py-3 border border-gray-700">
              <p className="text-xs text-gray-500 uppercase tracking-wide">EV Charger</p>
              <p className="text-2xl font-bold text-yellow-400">{evCount}</p>
            </div>
            <div className="bg-gray-800 rounded-xl px-4 py-3 border border-gray-700">
              <p className="text-xs text-gray-500 uppercase tracking-wide">With Website</p>
              <p className="text-2xl font-bold text-purple-400">{withWebsite}</p>
            </div>
          </div>
        )}

        <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-700 flex flex-wrap items-center gap-2">
            <div className="relative flex-1 min-w-[180px]">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
              <input type="text" value={search} onChange={e => setSearch(e.target.value)}
                placeholder="Search name, email, phone..."
                className="w-full bg-gray-700 text-sm rounded-lg pl-10 pr-3 py-2 border border-gray-600 text-gray-200 placeholder-gray-500 focus:outline-none focus:border-yellow-600" />
            </div>
            <select value={category} onChange={e => setCategory(e.target.value)}
              className="bg-gray-700 text-sm rounded-lg px-3 py-2 border border-gray-600 text-gray-200">
              <option value="">All Categories</option>
              {CAT_OPTIONS.slice(1).map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
            <select value={sourceFilter} onChange={e => setSourceFilter(e.target.value)}
              className="bg-gray-700 text-sm rounded-lg px-3 py-2 border border-gray-600 text-gray-200">
              <option value="">All Sources</option>
              <option value="ladbs_permit">LADBS</option>
              <option value="google_maps">Google Maps</option>
            </select>
            <select value={contactFilter} onChange={e => setContactFilter(e.target.value)}
              className="bg-gray-700 text-sm rounded-lg px-3 py-2 border border-gray-600 text-gray-200">
              <option value="">Any Contact</option>
              <option value="has_email">Has Email</option>
              <option value="has_phone">Has Phone</option>
              <option value="has_any">Has Contact Info</option>
              <option value="no_contact">No Contact</option>
            </select>
            <input type="number" value={minScore} onChange={e => setMinScore(e.target.value)}
              placeholder="Min score"
              className="bg-gray-700 text-sm rounded-lg px-3 py-2 border border-gray-600 w-20 text-gray-200 placeholder-gray-500" />
            <button onClick={exportCSV}
              className="flex items-center gap-1 px-3 py-2 text-xs font-medium rounded-lg border border-gray-600 text-gray-300 hover:border-gray-500 transition-colors">
              <Download className="w-3.5 h-3.5" /> CSV
            </button>
          </div>

          <div className="overflow-x-auto" style={{ maxHeight: "calc(100vh - 240px)", overflowY: "auto" }}>
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-gray-800 z-10">
                <tr className="text-gray-500 text-xs uppercase tracking-wide border-b border-gray-700">
                  <th className="text-left py-3 px-3">Score</th>
                  <th className="text-left py-3 px-3">Company</th>
                  <th className="text-left py-3 px-3">Category</th>
                  <th className="text-left py-3 px-3">Source</th>
                  <th className="text-left py-3 px-3">Contact</th>
                  <th className="text-left py-3 px-3">Phone</th>
                  <th className="text-left py-3 px-3">Email</th>
                  <th className="text-left py-3 px-3 desktop-only">Website</th>
                  <th className="text-left py-3 px-3 desktop-only">Zip</th>
                </tr>
              </thead>
              <tbody>
                {filtered.length === 0 && (
                  <tr><td colSpan={9} className="text-center py-16 text-gray-500">No leads found</td></tr>
                )}
                {filtered.map(l => (
                  <tr key={l.id} className="border-b border-gray-800 hover:bg-gray-750/50 transition-colors">
                    <td className={`py-3 px-3 font-bold ${l.score >= 60 ? "text-green-400" : l.score >= 40 ? "text-yellow-400" : "text-gray-500"}`}>{l.score}</td>
                    <td className="py-3 px-3">
                      <div className="font-medium text-gray-100">{l.company_name || "-"}</div>
                      {l.contact_name && <div className="text-xs text-gray-500">{l.contact_name}</div>}
                      {l.address && <div className="text-xs text-gray-600 truncate max-w-[250px]">{l.address}{l.city ? `, ${l.city}` : ""}</div>}
                    </td>
                    <td className="py-3 px-3">
                      <span className={`inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-md ${catClass(l.service_category)}`}>
                        {CAT_LABELS[l.service_category] || l.service_category}
                      </span>
                    </td>
                    <td className="py-3 px-3">
                      {l.source_url ? (
                        <a href={l.source_url} target="_blank" rel="noopener noreferrer"
                          className={`inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-md ${l.source === "ladbs_permit" ? "bg-blue-900/50 text-blue-300 hover:bg-blue-800/50" : "bg-purple-900/50 text-purple-300 hover:bg-purple-800/50"}`}>
                          {l.source === "ladbs_permit" ? "LADBS ↗" : "Maps ↗"}
                        </a>
                      ) : (
                        <span className={`inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-md ${l.source === "ladbs_permit" ? "bg-blue-900/50 text-blue-300" : "bg-purple-900/50 text-purple-300"}`}>
                          {l.source === "ladbs_permit" ? "LADBS" : "Maps"}
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-3">
                      {l.contact_name ? (
                        <span className="text-gray-300">{l.contact_name}</span>
                      ) : (
                        <span className="text-gray-600">-</span>
                      )}
                    </td>
                    <td className="py-3 px-3">
                      {l.phone ? (
                        <a href={`tel:${l.phone.replace(/[^\d]/g, "")}`}
                          className="text-blue-400 hover:text-blue-300 underline underline-offset-2 decoration-blue-800/50">
                          {l.phone}
                        </a>
                      ) : (
                        <span className="text-gray-600">-</span>
                      )}
                    </td>
                    <td className="py-3 px-3">
                      {l.email && l.email.includes("@") ? (
                        <a href={`mailto:${l.email}`}
                          className="text-green-400 hover:text-green-300 underline underline-offset-2 decoration-green-800/50 truncate max-w-[200px] inline-block align-middle">
                          {l.email}
                        </a>
                      ) : (
                        <span className="text-gray-600">-</span>
                      )}
                    </td>
                    <td className="py-3 px-3 desktop-only">
                      {l.website && l.website.startsWith("http") ? (
                        <a href={l.website} target="_blank" rel="noopener noreferrer"
                          className="text-yellow-400 hover:text-yellow-300 underline underline-offset-2 decoration-yellow-800/50 truncate max-w-[180px] inline-block align-middle">
                          {l.website.replace(/^https?:\/\//, "").replace(/\/$/, "")}
                        </a>
                      ) : (
                        <span className="text-gray-600">-</span>
                      )}
                    </td>
                    <td className="py-3 px-3 desktop-only text-gray-400">{l.zip_code || "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </main>

      <style>{`
        @media (max-width: 768px) { .desktop-only { display: none; } }
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: #1a202c; }
        ::-webkit-scrollbar-thumb { background: #4a5568; border-radius: 3px; }
      `}</style>
    </div>
  );
}
