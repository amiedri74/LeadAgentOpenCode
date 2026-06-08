# AGENTS.md — LeadAgentOpenCode

## Project Overview
Autonomous AI lead generation system for Amy Electric (Los Angeles electrical contractor).
- **Target**: 20+ leads/month | **Current**: 275 leads (201 LADBS permits, 74 Google Maps)
- **Stack**: Python FastAPI, PostgreSQL 16, Redis 7, Docker, Playwright, Ollama (qwen3:8b)
- **Sources**: LADBS SODA API (frozen May 2023), Google Maps (Playwright + stealth), Website contact scraping

## Quick Commands

```bash
# Start infra
docker start leadagentopencode-postgres-1 leadagentopencode-redis-1

# Start API (systemd user service)
systemd-run --user --unit=leadagent-api --working-directory=/home/amram/Downloads/LeadAgentOpenCode/backend python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --timeout-keep-alive 600

# Run full daily workflow (LADBS + Maps + Enrichment)
cd backend && python3 scripts/daily_workflow.py --maps

# Run Maps pipeline only
cd backend && python3 scripts/maps_pipeline.py 2>/dev/null

# Run contact enrichment
cd backend && python3 scripts/enrich_contacts.py

# Run outreach (dry-run / live)
cd backend && python3 scripts/send_outreach.py [--send] [--max N]

# Run dedup report
cd backend && python3 scripts/dedup_leads.py

# Check systemd timer status
systemctl --user status leadagent-daily.timer
```

## Key Files
| File | Purpose |
|------|---------|
| `backend/app/agents/permit_monitor.py` | LADBS permit scraper (SODA API) |
| `backend/app/agents/maps_scraper.py` | Google Maps scraper (Playwright + stealth) |
| `backend/app/agents/contact_scraper.py` | Website contact extractor (httpx + BS4) |
| `backend/app/scoring/engine.py` | Weighted scoring (0-100) |
| `backend/app/outreach/engine.py` | Ollama email generation (curl subprocess) |
| `backend/scripts/daily_workflow.py` | Main daily pipeline |
| `backend/scripts/maps_pipeline.py` | Maps-only pipeline |
| `backend/scripts/enrich_contacts.py` | Contact enrichment |
| `backend/scripts/send_outreach.py` | Outreach CLI |
| `docker-compose.yml` | PostgreSQL + Redis + backend |
| `nginx/default.conf` | Reverse proxy config |

## Database
- **URL**: `postgresql+asyncpg://leadagent:leadagent_secret_2026@localhost:5433/leadagent`
- **Schema**: 25 columns + 6 indices on `leads` table
- **Port**: 5433 (Docker), 5432 is system postgres (inaccessible)

## Critical Gotchas
1. **Ollama qwen3:8b runner gets stuck** (307% CPU, 5.8GB RSS) → Fix: `sudo kill -9 $(pgrep -f "ollama runner")` then wait ~10s
2. **httpx times out on Ollama** → Use `asyncio.create_subprocess_exec("curl", ...)` with 300s timeout
3. **Google Maps deduplicates by company_name only** (not name+address)
4. **LADBS dataset frozen at May 2023** — no real-time permits
5. **EPIPE errors from Playwright** are harmless stderr noise
6. **Phone format already consistent**: `(XXX) XXX-XXXX`

## Lead Sources & Scoring
| Source | Count | Key Fields |
|--------|-------|------------|
| LADBS | 201 | permit_number, estimated_cost, permit_type, contractor_name |
| Google Maps | 74 | company_name, phone, website, address, zip_code |

**Scoring (0-100)**: Category (30) + Urgency (20) + Zip Tier (15) + Permit Type (15) + Cost (20)
- EV Charger max: 70 | Commercial max: 60
- High-value threshold: ≥50

## Outreach
- **Model**: qwen3:8b via Ollama (localhost:11434)
- **Method**: curl subprocess (300s timeout) — avoids httpx timeout issues
- **Status tracking**: `extra_data.outreach` JSON field
- **Dry-run default**: `python3 scripts/send_outreach.py` | Live: add `--send`

## Systemd Daily Timer
- **Service**: `~/.config/systemd/user/leadagent-daily.service`
- **Timer**: `~/.config/systemd/user/leadagent-daily.timer` (daily ~00:19 PDT ±30min, `Persistent=true`)
- **User linger**: Enabled (`loginctl enable-linger $USER`)

## Next Steps (Priority)
1. Create AGENTS.md ✓
2. React/Next.js dashboard with WebSocket real-time feed
3. Rotating residential proxies for Google Maps scraper
4. Contact dedup merging (not just reporting)

## Testing
No formal test suite. Verify via:
- `python3 scripts/daily_workflow.py --maps` (end-to-end)
- Dashboard at `http://localhost:8000/dashboard`
- `curl http://localhost:8000/api/leads/stats`