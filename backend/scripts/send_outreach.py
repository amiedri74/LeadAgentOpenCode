#!/usr/bin/env python3
"""
Send personalized outreach emails to leads.
Dry-run by default. Use --send to actually send.
"""
import argparse
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.outreach.engine import run_outreach


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send outreach emails to leads")
    parser.add_argument("--send", action="store_true", help="Actually send emails (default: dry-run)")
    parser.add_argument("--max", type=int, default=50, help="Max leads to process (default: 50)")
    args = parser.parse_args()

    mode = "DRY RUN" if not args.send else "LIVE"
    print(f"Outreach mode: {mode} (max {args.max} leads)")
    asyncio.run(run_outreach(dry_run=not args.send, max_leads=args.max))
