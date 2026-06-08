from fastapi import APIRouter

router = APIRouter()


@router.get("/dashboard")
async def dashboard_html():
    from fastapi.responses import HTMLResponse
    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Amy Electric Lead Agent</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-900 text-gray-100">
    <div class="max-w-7xl mx-auto px-4 py-6">
        <header class="flex justify-between items-center mb-8">
            <div>
                <h1 class="text-3xl font-bold text-yellow-400">⚡ Amy Electric</h1>
                <p class="text-gray-400 text-sm">Lead Generation Agent — Los Angeles</p>
            </div>
            <div id="stats" class="flex gap-6 text-center">
                <div class="bg-gray-800 rounded-lg px-6 py-3"><div class="text-2xl font-bold" id="total-leads">-</div><div class="text-xs text-gray-400">Total Leads</div></div>
                <div class="bg-gray-800 rounded-lg px-6 py-3"><div class="text-2xl font-bold text-green-400" id="high-value">-</div><div class="text-xs text-gray-400">High Value</div></div>
                <div class="bg-gray-800 rounded-lg px-6 py-3"><div class="text-2xl font-bold text-yellow-400" id="ev-leads">-</div><div class="text-xs text-gray-400">EV Charger</div></div>
            </div>
        </header>

        <div class="grid grid-cols-1 lg:grid-cols-4 gap-6">
            <div class="lg:col-span-3">
                <div class="bg-gray-800 rounded-lg p-4">
                    <div class="flex justify-between items-center mb-4">
                        <h2 class="text-lg font-semibold">Leads</h2>
                        <div class="flex gap-2">
                            <select id="category-filter" class="bg-gray-700 text-sm rounded px-3 py-1 border border-gray-600" onchange="loadLeads()">
                                <option value="">All Categories</option>
                                <option value="ev_charger">EV Charger</option>
                                <option value="commercial_electrical">Commercial</option>
                                <option value="solar_electrical">Solar</option>
                                <option value="general_electrical">General</option>
                                <option value="generator">Generator</option>
                                <option value="lighting">Lighting</option>
                            </select>
                            <input id="score-filter" type="number" placeholder="Min score" class="bg-gray-700 text-sm rounded px-3 py-1 border border-gray-600 w-24" onchange="loadLeads()">
                        </div>
                    </div>
                    <div class="overflow-x-auto">
                        <table class="w-full text-sm">
                            <thead>
                                <tr class="text-gray-400 border-b border-gray-700">
                                    <th class="text-left py-2 px-2">Score</th>
                                    <th class="text-left py-2 px-2">Company</th>
                                    <th class="text-left py-2 px-2">Category</th>
                                    <th class="text-left py-2 px-2">Zip</th>
                                    <th class="text-left py-2 px-2">Address</th>
                                    <th class="text-left py-2 px-2">Permit</th>
                                </tr>
                            </thead>
                            <tbody id="leads-table"></tbody>
                        </table>
                    </div>
                    <div id="loading" class="text-center py-8 text-gray-500">Loading leads...</div>
                </div>
            </div>

            <div class="space-y-6">
                <div class="bg-gray-800 rounded-lg p-4">
                    <h2 class="text-lg font-semibold mb-3">Categories</h2>
                    <div id="category-chart" class="space-y-2"></div>
                </div>
                <div class="bg-gray-800 rounded-lg p-4">
                    <h2 class="text-lg font-semibold mb-3">Top EV Leads</h2>
                    <div id="ev-leads-list" class="space-y-2 text-sm"></div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const API = window.location.origin;

        async function loadStats() {
            const r = await fetch(API + '/api/leads/stats');
            const data = await r.json();
            document.getElementById('total-leads').textContent = data.total_leads;
            document.getElementById('high-value').textContent = data.high_value_leads;
            document.getElementById('ev-leads').textContent = data.by_category.ev_charger || 0;

            const cats = document.getElementById('category-chart');
            const total = data.total_leads || 1;
            const colors = {ev_charger:'yellow',commercial_electrical:'blue',general_electrical:'gray',solar_electrical:'orange',generator:'purple',lighting:'green'};
            const labels = {ev_charger:'EV Charger',commercial_electrical:'Commercial',general_electrical:'General',solar_electrical:'Solar',generator:'Generator',lighting:'Lighting'};
            cats.innerHTML = Object.entries(data.by_category)
                .sort((a,b) => b[1]-a[1])
                .map(([k,v]) => `<div><div class="flex justify-between text-xs mb-1"><span>${labels[k]||k}</span><span>${v}</span></div><div class="w-full bg-gray-700 rounded h-2"><div class="bg-${colors[k]||'blue'}-500 rounded h-2" style="width:${v/total*100}%"></div></div></div>`)
                .join('');
        }

        async function loadLeads() {
            const cat = document.getElementById('category-filter').value;
            const score = document.getElementById('score-filter').value;
            let url = API + '/api/leads?limit=50';
            if (cat) url += '&category=' + cat;
            if (score) url += '&min_score=' + score;
            
            document.getElementById('loading').style.display = 'block';
            const r = await fetch(url);
            const data = await r.json();
            document.getElementById('loading').style.display = 'none';

            const tbody = document.getElementById('leads-table');
            if (!data.leads || data.leads.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" class="text-center py-8 text-gray-500">No leads found</td></tr>';
                return;
            }
            const catLabels = {ev_charger:'EV Charger',commercial_electrical:'Commercial',general_electrical:'General',solar_electrical:'Solar',generator:'Generator',lighting:'Lighting'};
            const catColors = {ev_charger:'yellow',commercial_electrical:'blue',general_electrical:'gray',solar_electrical:'orange',generator:'purple',lighting:'green'};
            tbody.innerHTML = data.leads.map(l => {
                const scoreColor = l.score >= 60 ? 'text-green-400' : l.score >= 40 ? 'text-yellow-400' : 'text-gray-400';
                return `<tr class="border-b border-gray-700 hover:bg-gray-750">
                    <td class="py-2 px-2 font-bold ${scoreColor}">${l.score}</td>
                    <td class="py-2 px-2">${l.company_name || '-'}</td>
                    <td class="py-2 px-2"><span class="text-xs bg-${catColors[l.service_category]||'gray'}-900 text-${catColors[l.service_category]||'gray'}-300 px-2 py-0.5 rounded">${catLabels[l.service_category]||l.service_category}</span></td>
                    <td class="py-2 px-2">${l.zip_code || '-'}</td>
                    <td class="py-2 px-2 text-gray-400">${l.address || '-'}</td>
                    <td class="py-2 px-2 text-xs text-gray-500">${l.permit_type || '-'}</td>
                </tr>`;
            }).join('');
        }

        async function loadEVLeads() {
            const r = await fetch(API + '/api/leads?category=ev_charger&limit=10');
            const data = await r.json();
            const div = document.getElementById('ev-leads-list');
            if (!data.leads || data.leads.length === 0) {
                div.innerHTML = '<div class="text-gray-500">No EV leads yet</div>';
                return;
            }
            div.innerHTML = data.leads.map(l => `<div class="bg-gray-700 rounded p-2"><div class="font-medium">${l.company_name || 'Unknown'}</div><div class="text-xs text-gray-400">Zip: ${l.zip_code} · Score: ${l.score}</div></div>`).join('');
        }

        loadStats();
        loadLeads();
        loadEVLeads();
    </script>
</body>
</html>"""
    return HTMLResponse(html)
