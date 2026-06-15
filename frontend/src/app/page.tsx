"use client";

import { useEffect, useState, useCallback } from "react";
import { Zap, Wifi, WifiOff, Download, Search, Mail, Send, Check, Edit3, X } from "lucide-react";

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

interface Draft {
  id: string;
  lead_id: string;
  status: string;
  subject: string;
  body: string;
  generated_at: string | null;
  company_name: string | null;
  email: string | null;
  phone: string | null;
  score: number | null;
  service_category: string | null;
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

const STATUS_LABELS: Record<string, string> = {
  pending_review: "Pending Review",
  approved: "Approved",
  sent: "Sent",
  failed: "Failed",
};

const STATUS_COLORS: Record<string, string> = {
  pending_review: "bg-yellow-900/50 text-yellow-300",
  approved: "bg-green-900/50 text-green-300",
  sent: "bg-blue-900/50 text-blue-300",
  failed: "bg-red-900/50 text-red-300",
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

function safeHref(url: string | null | undefined): string | null {
  if (!url) return null;
  if (url.startsWith("http://") || url.startsWith("https://")) return url;
  return null;
}

export default function Dashboard() {
  const [tab, setTab] = useState<"leads" | "outreach">("leads");
  const [stats, setStats] = useState<Stats | null>(null);
  const [allLeads, setAllLeads] = useState<Lead[]>([]);
  const [category, setCategory] = useState("");
  const [minScore, setMinScore] = useState("");
  const [search, setSearch] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");
  const [contactFilter, setContactFilter] = useState("");
  const [isConnected, setIsConnected] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);

  // Outreach state
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [draftFilter, setDraftFilter] = useState("");
  const [editingDraft, setEditingDraft] = useState<Draft | null>(null);
  const [editSubject, setEditSubject] = useState("");
  const [editBody, setEditBody] = useState("");
  const [sendingBatch, setSendingBatch] = useState(false);
  const [sendResult, setSendResult] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/leads/stats").then(r => {
      if (!r.ok) throw new Error(`Stats: ${r.status}`);
      return r.json();
    }).then(setStats).catch(e => {
      console.error("Stats fetch failed:", e);
      setFetchError("Failed to load stats");
    });
    fetch("/api/leads?limit=600").then(r => {
      if (!r.ok) throw new Error(`Leads: ${r.status}`);
      return r.json();
    }).then(d => {
      if (d.leads) setAllLeads(d.leads);
    }).catch(e => {
      console.error("Leads fetch failed:", e);
      setFetchError("Failed to load leads");
    });
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

  const loadDrafts = useCallback(() => {
    const url = draftFilter ? `/api/outreach/drafts?status=${draftFilter}` : "/api/outreach/drafts";
    fetch(url).then(r => r.json()).then(d => {
      if (d.drafts) setDrafts(d.drafts);
    }).catch(e => console.error("Drafts fetch failed:", e));
  }, [draftFilter]);

  useEffect(() => {
    if (tab === "outreach") loadDrafts();
  }, [tab, loadDrafts]);

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

  const startEdit = (draft: Draft) => {
    setEditingDraft(draft);
    setEditSubject(draft.subject);
    setEditBody(draft.body);
  };

  const saveEdit = async () => {
    if (!editingDraft) return;
    await fetch(`/api/outreach/drafts/${editingDraft.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ subject: editSubject, body: editBody }),
    });
    setEditingDraft(null);
    loadDrafts();
  };

  const approveDraft = async (id: string) => {
    await fetch(`/api/outreach/drafts/${id}/approve`, { method: "POST" });
    loadDrafts();
  };

  const sendBatch = async () => {
    setSendingBatch(true);
    setSendResult(null);
    try {
      const r = await fetch("/api/outreach/send-batch", { method: "POST" });
      const d = await r.json();
      setSendResult(`Sent: ${d.sent}, Failed: ${d.failed}`);
      loadDrafts();
    } catch (e) {
      setSendResult("Error sending batch");
    }
    setSendingBatch(false);
  };

  const approvedCount = drafts.filter(d => d.status === "approved").length;
  const pendingCount = drafts.filter(d => d.status === "pending_review").length;

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
        {fetchError && (
          <div className="bg-red-900/50 border border-red-700 text-red-300 px-4 py-2 rounded-lg mb-4 text-sm flex justify-between items-center">
            <span>{fetchError}</span>
            <button onClick={() => setFetchError(null)} className="text-red-400 hover:text-red-300"><X className="w-4 h-4" /></button>
          </div>
        )}
        {/* Tab bar */}
        <div className="flex gap-1 mb-4 border-b border-gray-800">
          <button
            onClick={() => setTab("leads")}
            className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${tab === "leads" ? "bg-gray-800 text-yellow-400 border-b-2 border-yellow-400" : "text-gray-500 hover:text-gray-300"}`}
          >
            Leads ({allLeads.length})
          </button>
          <button
            onClick={() => setTab("outreach")}
            className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors flex items-center gap-2 ${tab === "outreach" ? "bg-gray-800 text-yellow-400 border-b-2 border-yellow-400" : "text-gray-500 hover:text-gray-300"}`}
          >
            <Mail className="w-4 h-4" />
            Outreach
            {pendingCount > 0 && <span className="bg-yellow-600 text-white text-xs rounded-full px-1.5 py-0.5">{pendingCount}</span>}
          </button>
        </div>

        {/* LEADS TAB */}
        {tab === "leads" && (
          <>
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
                  <p className="text-2xl font-bold text-blue-400">{allLeads.filter(l => l.phone).length}</p>
                </div>
                <div className="bg-gray-800 rounded-xl px-4 py-3 border border-gray-700">
                  <p className="text-xs text-gray-500 uppercase tracking-wide">With Email</p>
                  <p className="text-2xl font-bold text-yellow-400">{allLeads.filter(l => l.email && l.email.includes("@")).length}</p>
                </div>
                <div className="bg-gray-800 rounded-xl px-4 py-3 border border-gray-700">
                  <p className="text-xs text-gray-500 uppercase tracking-wide">EV Charger</p>
                  <p className="text-2xl font-bold text-yellow-400">{allLeads.filter(l => l.service_category === "ev_charger").length}</p>
                </div>
                <div className="bg-gray-800 rounded-xl px-4 py-3 border border-gray-700">
                  <p className="text-xs text-gray-500 uppercase tracking-wide">With Website</p>
                  <p className="text-2xl font-bold text-purple-400">{allLeads.filter(l => l.website && l.website.startsWith("http")).length}</p>
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

              <div className="overflow-x-auto" style={{ maxHeight: "calc(100vh - 280px)", overflowY: "auto" }}>
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
                      <tr key={l.id} className="border-b border-gray-800 hover:bg-gray-700/50 transition-colors">
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
                      {safeHref(l.source_url) ? (
                        <a href={safeHref(l.source_url)!} target="_blank" rel="noopener noreferrer"
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
                          {l.contact_name ? <span className="text-gray-300">{l.contact_name}</span> : <span className="text-gray-600">-</span>}
                        </td>
                        <td className="py-3 px-3">
                          {l.phone ? (
                            <a href={`tel:${l.phone.replace(/[^\d]/g, "")}`}
                              className="text-blue-400 hover:text-blue-300 underline underline-offset-2 decoration-blue-800/50">{l.phone}</a>
                          ) : <span className="text-gray-600">-</span>}
                        </td>
                        <td className="py-3 px-3">
                          {l.email && l.email.includes("@") ? (
                            <a href={`mailto:${l.email}`}
                              className="text-green-400 hover:text-green-300 underline underline-offset-2 decoration-green-800/50 truncate max-w-[200px] inline-block align-middle">{l.email}</a>
                          ) : <span className="text-gray-600">-</span>}
                        </td>
                    <td className="py-3 px-3 desktop-only">
                      {safeHref(l.website) ? (
                        <a href={safeHref(l.website)!} target="_blank" rel="noopener noreferrer"
                              className="text-yellow-400 hover:text-yellow-300 underline underline-offset-2 decoration-yellow-800/50 truncate max-w-[180px] inline-block align-middle">
                              {l.website.replace(/^https?:\/\//, "").replace(/\/$/, "")}
                            </a>
                          ) : <span className="text-gray-600">-</span>}
                        </td>
                        <td className="py-3 px-3 desktop-only text-gray-400">{l.zip_code || "-"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}

        {/* OUTREACH TAB */}
        {tab === "outreach" && (
          <div className="space-y-4">
            {/* Actions bar */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <select value={draftFilter} onChange={e => setDraftFilter(e.target.value)}
                  className="bg-gray-700 text-sm rounded-lg px-3 py-2 border border-gray-600 text-gray-200">
                  <option value="">All Drafts</option>
                  <option value="pending_review">Pending Review</option>
                  <option value="approved">Approved</option>
                  <option value="sent">Sent</option>
                  <option value="failed">Failed</option>
                </select>
                <span className="text-sm text-gray-500">{drafts.length} drafts</span>
              </div>
              <button
                onClick={sendBatch}
                disabled={sendingBatch || approvedCount === 0}
                className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-colors ${approvedCount > 0 && !sendingBatch ? "bg-green-600 hover:bg-green-500 text-white" : "bg-gray-700 text-gray-500 cursor-not-allowed"}`}
              >
                <Send className="w-4 h-4" />
                {sendingBatch ? "Sending..." : `Send Batch (${approvedCount})`}
              </button>
            </div>

            {sendResult && (
              <div className="bg-gray-800 rounded-lg px-4 py-2 text-sm text-gray-300 border border-gray-700">{sendResult}</div>
            )}

            {/* Edit modal */}
            {editingDraft && (
              <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
                <div className="bg-gray-800 rounded-xl border border-gray-700 w-full max-w-2xl max-h-[80vh] overflow-y-auto">
                  <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700">
                    <h3 className="font-semibold text-gray-100">Edit Draft</h3>
                    <button onClick={() => setEditingDraft(null)} className="text-gray-500 hover:text-gray-300">
                      <X className="w-5 h-5" />
                    </button>
                  </div>
                  <div className="p-4 space-y-3">
                    <div>
                      <label className="block text-xs text-gray-500 mb-1">Subject</label>
                      <input type="text" value={editSubject} onChange={e => setEditSubject(e.target.value)}
                        className="w-full bg-gray-700 text-sm rounded-lg px-3 py-2 border border-gray-600 text-gray-200" />
                    </div>
                    <div>
                      <label className="block text-xs text-gray-500 mb-1">Body</label>
                      <textarea value={editBody} onChange={e => setEditBody(e.target.value)} rows={12}
                        className="w-full bg-gray-700 text-sm rounded-lg px-3 py-2 border border-gray-600 text-gray-200 resize-none" />
                    </div>
                  </div>
                  <div className="flex justify-end gap-2 px-4 py-3 border-t border-gray-700">
                    <button onClick={() => setEditingDraft(null)}
                      className="px-4 py-2 text-sm rounded-lg border border-gray-600 text-gray-300 hover:bg-gray-700">Cancel</button>
                    <button onClick={saveEdit}
                      className="px-4 py-2 text-sm rounded-lg bg-yellow-600 hover:bg-yellow-500 text-white font-medium">Save</button>
                  </div>
                </div>
              </div>
            )}

            {/* Drafts list */}
            <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
              <div className="overflow-x-auto" style={{ maxHeight: "calc(100vh - 320px)", overflowY: "auto" }}>
                <table className="w-full text-sm">
                  <thead className="sticky top-0 bg-gray-800 z-10">
                    <tr className="text-gray-500 text-xs uppercase tracking-wide border-b border-gray-700">
                      <th className="text-left py-3 px-3">Status</th>
                      <th className="text-left py-3 px-3">Company</th>
                      <th className="text-left py-3 px-3">Email</th>
                      <th className="text-left py-3 px-3">Score</th>
                      <th className="text-left py-3 px-3">Subject</th>
                      <th className="text-left py-3 px-3">Generated</th>
                      <th className="text-left py-3 px-3">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {drafts.length === 0 && (
                      <tr><td colSpan={7} className="text-center py-16 text-gray-500">
                        No drafts yet. Run <code className="bg-gray-700 px-1 rounded">python3 scripts/generate_outreach.py</code> to generate.
                      </td></tr>
                    )}
                    {drafts.map(d => (
                      <tr key={d.id} className="border-b border-gray-800 hover:bg-gray-700/50 transition-colors">
                        <td className="py-3 px-3">
                          <span className={`inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-md ${STATUS_COLORS[d.status] || "bg-gray-700 text-gray-300"}`}>
                            {STATUS_LABELS[d.status] || d.status}
                          </span>
                        </td>
                        <td className="py-3 px-3">
                          <div className="font-medium text-gray-100">{d.company_name || "-"}</div>
                          {d.service_category && <div className="text-xs text-gray-500">{CAT_LABELS[d.service_category] || d.service_category}</div>}
                        </td>
                        <td className="py-3 px-3">
                          {d.email ? (
                            <a href={`mailto:${d.email}`} className="text-green-400 hover:text-green-300 text-sm">{d.email}</a>
                          ) : <span className="text-gray-600">-</span>}
                        </td>
                        <td className={`py-3 px-3 font-bold ${(d.score || 0) >= 60 ? "text-green-400" : (d.score || 0) >= 40 ? "text-yellow-400" : "text-gray-500"}`}>
                          {d.score ?? "-"}
                        </td>
                        <td className="py-3 px-3">
                          <div className="text-gray-300 truncate max-w-[300px]">{d.subject || "-"}</div>
                          <div className="text-xs text-gray-600 truncate max-w-[300px] mt-0.5">{(d.body || "").slice(0, 80)}...</div>
                        </td>
                        <td className="py-3 px-3 text-xs text-gray-500">
                          {d.generated_at ? new Date(d.generated_at).toLocaleDateString() : "-"}
                        </td>
                        <td className="py-3 px-3">
                          <div className="flex items-center gap-1">
                            {d.status === "pending_review" && (
                              <>
                                <button onClick={() => startEdit(d)} title="Edit"
                                  className="p-1.5 rounded-lg hover:bg-gray-700 text-gray-400 hover:text-yellow-400 transition-colors">
                                  <Edit3 className="w-4 h-4" />
                                </button>
                                <button onClick={() => approveDraft(d.id)} title="Approve"
                                  className="p-1.5 rounded-lg hover:bg-gray-700 text-gray-400 hover:text-green-400 transition-colors">
                                  <Check className="w-4 h-4" />
                                </button>
                              </>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
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
