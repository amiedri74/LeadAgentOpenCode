# Amy Electric Lead Agent — Quick Start

## Running the System

```bash
# Start infrastructure (PostgreSQL + Redis)
docker compose up -d postgres redis

# Start the backend API
cd backend && python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Open dashboard
open http://localhost:8000/dashboard
```

## Daily Automation

```bash
# Run once to scrape new leads
python3 backend/scripts/daily_workflow.py

# Or via cron (6am daily)
0 6 * * * cd /path/to/lead-agent && python3 backend/scripts/daily_workflow.py >> /var/log/lead-agent/daily.log 2>&1
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| GET `/api/health` | Health check |
| GET `/api/leads` | List leads (supports `?category=&min_score=&limit=`) |
| GET `/api/leads/stats` | Lead statistics by category |
| GET `/api/leads/{id}` | Single lead detail |
| GET `/dashboard` | Visual dashboard |

## Architecture

```
FastAPI Backend → PostgreSQL (leads, permits)
       ↕
HTML Dashboard (Tailwind + vanilla JS)
```

## Adding New Lead Sources

Add new agents in `backend/app/agents/` following the `permit_monitor.py` pattern.
