#!/usr/bin/env python3
"""
Send personalized outreach emails to leads.
Dry-run by default. Use --send to actually send.
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.outreach.engine import run_outreach


if __name__ == "__main__":
    dry_run = "--send" not in sys.argv
    max_leads = 50
    for i, a in enumerate(sys.argv[1:]):
        if a == "--max" and i + 1 < len(sys.argv) - 1:
            try:
                max_leads = int(sys.argv[i + 2])
            except ValueError:
                pass

    mode = "DRY RUN" if dry_run else "LIVE"
    print(f"Outreach mode: {mode} (max {max_leads} leads)")
    asyncio.run(run_outreach(dry_run=dry_run, max_leads=max_leads))
