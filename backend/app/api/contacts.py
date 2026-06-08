from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/contacts")
async def contacts_dashboard():
    return HTMLResponse(PAGE)


PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Amy Electric — Contact Dashboard</title>
<script src="https://cdn.tailwindcss.com"></script>
<script>
tailwind.config = { theme: { extend: { colors: { gray: { 750: '#2d3748' } } } } };
</script>
<style>
  [x-cloak] { display: none !important; }
  .btn { @apply px-3 py-1.5 text-xs font-medium rounded-lg transition-colors; }
  .btn-primary { @apply bg-yellow-600 hover:bg-yellow-500 text-black; }
  .btn-outline { @apply border border-gray-600 hover:border-gray-500 text-gray-300; }
  .badge { @apply inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-md; }
  tr.contact-row { @apply border-b border-gray-800 hover:bg-gray-750/70 transition-colors cursor-pointer; }
  tr.contact-row td { @apply py-3 px-3 text-sm; }
  @media (max-width: 768px) { .desktop-only { display: none; } }
  ::-webkit-scrollbar { width: 6px; height: 6px; }
  ::-webkit-scrollbar-track { background: #1a202c; }
  ::-webkit-scrollbar-thumb { background: #4a5568; border-radius: 3px; }
</style>
</head>
<body class="bg-gray-900 text-gray-100 antialiased" x-data="app()" x-init="init()">
  <div class="min-h-screen flex flex-col">
    <header class="border-b border-gray-800 bg-gray-900/95 sticky top-0 z-50 backdrop-blur-sm">
      <div class="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <span class="text-2xl">⚡</span>
          <div>
            <h1 class="text-lg font-bold text-yellow-400">Amy Electric</h1>
            <p class="text-xs text-gray-500">Contact Dashboard</p>
          </div>
        </div>
        <div class="flex items-center gap-3">
          <span class="text-xs text-gray-500" x-text="`${leads.length} of ${total} leads`"></span>
          <span class="w-2 h-2 rounded-full" :class="online ? 'bg-green-400' : 'bg-red-400'" :title="online ? 'Live' : 'Offline'"></span>
        </div>
      </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 py-4 flex-1 w-full">
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
        <div class="bg-gray-800 rounded-xl px-4 py-3 border border-gray-700">
          <div class="text-xs text-gray-500 uppercase tracking-wide">Total</div>
          <div class="text-2xl font-bold text-white" x-text="total"></div>
        </div>
        <div class="bg-gray-800 rounded-xl px-4 py-3 border border-gray-700">
          <div class="text-xs text-gray-500 uppercase tracking-wide">With Phone</div>
          <div class="text-2xl font-bold text-blue-400" x-text="withPhone"></div>
        </div>
        <div class="bg-gray-800 rounded-xl px-4 py-3 border border-gray-700">
          <div class="text-xs text-gray-500 uppercase tracking-wide">With Email</div>
          <div class="text-2xl font-bold text-green-400" x-text="withEmail"></div>
        </div>
        <div class="bg-gray-800 rounded-xl px-4 py-3 border border-gray-700">
          <div class="text-xs text-gray-500 uppercase tracking-wide">With Website</div>
          <div class="text-2xl font-bold text-yellow-400" x-text="withWebsite"></div>
        </div>
      </div>

      <div class="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
        <div class="px-4 py-3 border-b border-gray-700 flex flex-wrap items-center gap-2">
          <div class="relative flex-1 min-w-[200px]">
            <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
            <input type="text" x-model="search" placeholder="Search name, email, phone..." class="w-full bg-gray-700 text-sm rounded-lg pl-10 pr-3 py-2 border border-gray-600 text-gray-200 placeholder-gray-500 focus:outline-none focus:border-yellow-600">
          </div>
          <select x-model="catFilter" class="bg-gray-700 text-sm rounded-lg px-3 py-2 border border-gray-600 text-gray-200">
            <option value="">All Categories</option>
            <option value="ev_charger">EV Charger</option>
            <option value="commercial_electrical">Commercial</option>
            <option value="general_electrical">General</option>
            <option value="solar_electrical">Solar</option>
            <option value="generator">Generator</option>
            <option value="lighting">Lighting</option>
          </select>
          <select x-model="sourceFilter" class="bg-gray-700 text-sm rounded-lg px-3 py-2 border border-gray-600 text-gray-200">
            <option value="">All Sources</option>
            <option value="ladbs_permit">LADBS</option>
            <option value="google_maps">Google Maps</option>
          </select>
          <select x-model="contactFilter" class="bg-gray-700 text-sm rounded-lg px-3 py-2 border border-gray-600 text-gray-200">
            <option value="">Any Contact</option>
            <option value="has_email">Has Email</option>
            <option value="has_phone">Has Phone</option>
            <option value="has_any">Has Contact Info</option>
            <option value="no_contact">No Contact</option>
          </select>
          <input type="number" x-model="minScore" placeholder="Min score" class="bg-gray-700 text-sm rounded-lg px-3 py-2 border border-gray-600 w-20 text-gray-200 placeholder-gray-500">
          <button @click="exportCSV()" class="btn btn-outline">CSV</button>
        </div>

        <div class="overflow-x-auto" style="max-height: calc(100vh - 260px); overflow-y: auto;">
          <table class="w-full text-sm">
            <thead class="sticky top-0 bg-gray-800 z-10">
              <tr class="text-gray-500 text-xs uppercase tracking-wide border-b border-gray-700">
                <th class="text-left py-3 px-3 cursor-pointer hover:text-gray-300" @click="sort='score'; dir=dir==='asc'?'desc':'asc'">Score <span x-show="sort==='score'" x-text="dir==='asc'?'▲':'▼'"></span></th>
                <th class="text-left py-3 px-3 cursor-pointer hover:text-gray-300" @click="sort='company_name'; dir=dir==='asc'?'desc':'asc'">Company</th>
                <th class="text-left py-3 px-3">Category</th>
                <th class="text-left py-3 px-3">Source</th>
                <th class="text-left py-3 px-3">Contact Name</th>
                <th class="text-left py-3 px-3">Phone</th>
                <th class="text-left py-3 px-3">Email</th>
                <th class="text-left py-3 px-3 desktop-only">Website</th>
                <th class="text-left py-3 px-3 desktop-only">Zip</th>
              </tr>
            </thead>
            <tbody>
              <template x-for="l in filtered" :key="l.id">
                <tr class="contact-row">
                  <td class="font-bold" :class="{'text-green-400': l.score>=60, 'text-yellow-400': l.score>=40 && l.score<60, 'text-gray-500': l.score<40}" x-text="l.score"></td>
                  <td>
                    <div class="font-medium text-gray-100" x-text="l.company_name || '-'"></div>
                    <div class="text-xs text-gray-600" x-text="l.address ? (l.address + (l.city ? ', ' + l.city : '')) : ''"></div>
                  </td>
                  <td>
                    <span class="badge" :class="catClass(l.service_category)" x-text="catLabel(l.service_category)"></span>
                  </td>
                  <td>
                    <span class="badge" :class="l.source==='ladbs_permit' ? 'bg-blue-900/50 text-blue-300' : 'bg-purple-900/50 text-purple-300'" x-text="l.source==='ladbs_permit' ? 'LADBS' : 'Maps'"></span>
                  </td>
                  <td>
                    <span class="text-gray-300" x-text="l.contact_name || '-'"></span>
                  </td>
                  <td>
                    <template x-if="l.phone">
                      <a :href="'tel:' + l.phone.replace(/[^\\d]/g,'')" class="text-blue-400 hover:text-blue-300 underline underline-offset-2 decoration-blue-800/50" x-text="l.phone"></a>
                    </template>
                    <template x-if="!l.phone">
                      <span class="text-gray-600">-</span>
                    </template>
                  </td>
                  <td>
                    <template x-if="l.email && l.email.includes('@')">
                      <a :href="'mailto:' + l.email" class="text-green-400 hover:text-green-300 underline underline-offset-2 decoration-green-800/50 truncate max-w-[200px] inline-block align-middle" x-text="l.email"></a>
                    </template>
                    <template x-if="!l.email || !l.email.includes('@')">
                      <span class="text-gray-600">-</span>
                    </template>
                  </td>
                  <td class="desktop-only">
                    <template x-if="l.website && l.website.startsWith('http')">
                      <a :href="l.website" target="_blank" class="text-yellow-400 hover:text-yellow-300 underline underline-offset-2 decoration-yellow-800/50 truncate max-w-[200px] inline-block align-middle" x-text="l.website.replace(/^https?:\\/\\//,'').replace(/\\/$/,'')"></a>
                    </template>
                    <template x-if="!l.website || !l.website.startsWith('http')">
                      <span class="text-gray-600">-</span>
                    </template>
                  </td>
                  <td class="desktop-only text-gray-400" x-text="l.zip_code || '-'"></td>
                </tr>
              </template>
            </tbody>
          </table>
          <div x-show="filtered.length === 0" class="text-center py-16 text-gray-500">
            <div class="text-4xl mb-3">📭</div>
            <p>No leads match your filters</p>
          </div>
        </div>
      </div>
    </main>
  </div>

<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
<script>
function app() {
  return {
    leads: [], total: 0, online: false,
    search: '', catFilter: '', sourceFilter: '', contactFilter: '', minScore: '',
    sort: 'score', dir: 'desc',
    catLabels: { ev_charger:'EV Charger', commercial_electrical:'Commercial', general_electrical:'General', solar_electrical:'Solar', generator:'Generator', lighting:'Lighting' },
    catColors: { ev_charger:'bg-yellow-900/50 text-yellow-300', commercial_electrical:'bg-blue-900/50 text-blue-300', general_electrical:'bg-gray-700 text-gray-300', solar_electrical:'bg-orange-900/50 text-orange-300', generator:'bg-purple-900/50 text-purple-300', lighting:'bg-green-900/50 text-green-300' },

    catLabel(c) { return this.catLabels[c] || c; },
    catClass(c) { return this.catColors[c] || 'bg-gray-700 text-gray-300'; },

    get withPhone() { return this.leads.filter(l => l.phone).length; },
    get withEmail() { return this.leads.filter(l => l.email && l.email.includes('@')).length; },
    get withWebsite() { return this.leads.filter(l => l.website).length; },

    get filtered() {
      let f = [...this.leads];
      if (this.search) {
        const q = this.search.toLowerCase();
        f = f.filter(l => (l.company_name||'').toLowerCase().includes(q) || (l.email||'').toLowerCase().includes(q) || (l.phone||'').toLowerCase().includes(q) || (l.contact_name||'').toLowerCase().includes(q) || (l.address||'').toLowerCase().includes(q));
      }
      if (this.catFilter) f = f.filter(l => l.service_category === this.catFilter);
      if (this.sourceFilter) f = f.filter(l => l.source === this.sourceFilter);
      if (this.minScore) f = f.filter(l => l.score >= parseInt(this.minScore));
      if (this.contactFilter === 'has_email') f = f.filter(l => l.email && l.email.includes('@'));
      if (this.contactFilter === 'has_phone') f = f.filter(l => l.phone);
      if (this.contactFilter === 'has_any') f = f.filter(l => (l.email && l.email.includes('@')) || l.phone || l.website);
      if (this.contactFilter === 'no_contact') f = f.filter(l => !(l.email && l.email.includes('@')) && !l.phone && !l.website);
      f.sort((a,b) => {
        let va = a[this.sort] || '', vb = b[this.sort] || '';
        if (this.sort === 'score') { va = Number(va); vb = Number(vb); }
        else { va = String(va).toLowerCase(); vb = String(vb).toLowerCase(); }
        return this.dir === 'asc' ? (va > vb ? 1 : -1) : (va < vb ? 1 : -1);
      });
      return f;
    },

    exportCSV() {
      const rows = this.filtered.map(l => [
        l.score, l.company_name||'', l.contact_name||'', l.phone||'', l.email||'', l.website||'',
        l.source==='ladbs_permit'?'LADBS':'Maps', this.catLabel(l.service_category), l.zip_code||'', l.address||''
      ]);
      const csv = [['Score','Company','Contact Name','Phone','Email','Website','Source','Category','Zip','Address'], ...rows]
        .map(r => r.map(v => '"' + String(v).replace(/"/g,'""') + '"').join(',')).join('\\n');
      const blob = new Blob([csv], { type: 'text/csv' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'amy_electric_leads.csv';
      a.click();
    },

    init() {
      const ws = new WebSocket((location.protocol==='https:'?'wss:':'ws:') + '//' + location.hostname + ':8000/ws');
      ws.onopen = () => { this.online = true; };
      ws.onclose = () => { this.online = false; };
      ws.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data);
          if (msg.type === 'stats') this.total = msg.payload.total_leads;
        } catch(_) {}
      };

      fetch('/api/leads?limit=300').then(r => r.json()).then(d => {
        this.leads = d.leads || [];
        this.total = d.total || this.leads.length;
      });
    }
  };
}
</script>
</body>
</html>"""
