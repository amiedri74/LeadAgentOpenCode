# AGENTS.md — LeadAgentOpenCode

## Project Overview
Autonomous AI lead generation system for Amy Electric (Los Angeles electrical contractor).
- **Target**: 20+ leads/month | **Current**: 293 leads (201 LADBS, 92 Google Maps)
- **Stack**: Python FastAPI, PostgreSQL 16, Redis 7, Docker, Playwright, Ollama (llama3.2:latest)
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
| `backend/app/outreach/engine.py` | Ollama email generation (curl subprocess + options.num_predict) |
| `backend/scripts/daily_workflow.py` | Main daily pipeline |
| `backend/scripts/maps_pipeline.py` | Maps-only pipeline |
| `backend/scripts/enrich_contacts.py` | Contact enrichment (with progress logging) |
| `backend/scripts/send_outreach.py` | Outreach CLI |
| `docker-compose.yml` | PostgreSQL + Redis + backend |
| `nginx/default.conf` | Reverse proxy config |
| `frontend/` | Next.js dashboard with WebSocket live feed |

## Database
- **URL**: `postgresql+asyncpg://leadagent:leadagent_secret_2026@localhost:5433/leadagent`
- **Schema**: 25 columns + 6 indices on `leads` table
- **Port**: 5433 (Docker), 5432 is system postgres (inaccessible)

## Critical Gotchas
1. **Ollama runner gets stuck** (307% CPU, 5.8GB RSS on qwen3:8b) → Switched to llama3.2:latest (3.2B, works reliably). Fix: `sudo kill -9 $(pgrep -f "ollama runner")` then wait ~15s
2. **Ollama API: use `options.num_predict` NOT `max_tokens`** — top-level `max_tokens` is ignored silently. Always nest token count/temperature in `options` dict
3. **httpx times out on Ollama** → Use `asyncio.create_subprocess_exec("curl", ...)` with 300s timeout
4. **Google Maps deduplicates by company_name only** (not name+address)
5. **LADBS dataset frozen at May 2023** — no real-time permits
6. **EPIPE errors from Playwright** are harmless stderr noise
7. **Phone format already consistent**: `(XXX) XXX-XXXX`
8. **Contact scraper email validation**: Reject emails with URL encoding (`%XX`), trailing words (`.comCall`, `.comWe`), dotfiles (`.png`, `.jpg`), and rotated/obfuscated addresses. Enrichment script now has visible progress logging per lead
9. **socket.io-client NOT used** — frontend uses native WebSocket API directly; remove socket.io-client from package.json if present

## Lead Sources & Scoring
| Source | Count | Key Fields |
|--------|-------|------------|
| LADBS | 201 | permit_number, estimated_cost, permit_type, contractor_name |
| Google Maps | 92 | company_name, phone, website, address, zip_code |

**Scoring (0-100)**: Category (30) + Urgency (20) + Zip Tier (15) + Permit Type (15) + Cost (20)
- EV Charger max: 70 | Commercial max: 60
- High-value threshold: ≥50

## Outreach
- **Model**: llama3.2:latest via Ollama (localhost:11434) — switched from qwen3:8b (kept getting stuck)
- **Method**: curl subprocess (300s timeout) with `options.num_predict` for token limits
- **Status tracking**: `extra_data.outreach` JSON field
- **Dry-run default**: `python3 scripts/send_outreach.py` | Live: add `--send`
- **Emails**: 40 with clean emails, 79 high-value (score ≥ 50)

## Systemd Daily Timer
- **Service**: `~/.config/systemd/user/leadagent-daily.service`
- **Timer**: `~/.config/systemd/user/leadagent-daily.timer` (daily ~00:19 PDT ±30min, `Persistent=true`)
- **User linger**: Enabled (`loginctl enable-linger $USER`)

## GitHub
- **Remote**: `https://github.com/amiedri74/LeadAgentOpenCode`
- Push after any significant change: `git add -A && git commit -m "..." && git push`

## Next Steps (Priority)
1. Set up SendGrid API key (`SENDGRID_API_KEY` env var) and enable live email sending (`scripts/send_outreach.py --send`)
2. Rotating residential proxies for Google Maps scraper to bypass rate limits
3. Merge dedup groups (especially Imperial Solar affiliates — 6 leads sharing same email/website, but likely separate businesses using a shared CRM)
4. Expand Maps search terms for more leads beyond current 92

## Testing
No formal test suite. Verify via:
- `python3 scripts/daily_workflow.py --maps` (end-to-end)
- Dashboard at `http://localhost:8000/dashboard`
- `curl http://localhost:8000/api/leads/stats`
- `cd frontend && npm run build` (Next.js build check)
