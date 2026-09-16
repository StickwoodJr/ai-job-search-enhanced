#!/usr/bin/env python3
"""
Indeed Swarm Scraper Orchestrator
Coordinates 3 parallel continuous sector-scraping worker processes across Indeed Canada:
1. Sector 1 (systems_hardware): Linux, Systems Admin, Windows Server/AD, Service Desk, Desktop Support, Hardware & Datacenter
2. Sector 2 (networking_noc): Cisco Routing/Switching, Network Admin, Telecom, NOC Operations, Network Security
3. Sector 3 (cloud_cyber): Cloud Infrastructure (AWS/Azure), DevOps, Cybersecurity, SOC Analysis, TSA

Enforces:
- Seneca CTYC curriculum only
- <= 70 km driving distance from Newmarket, ON
- Explicit Winter 2027 Co-op term
- Atomic deduplication in seen_jobs.json
- Automatic rebuild of job_search_tracker.csv and application-dashboard.html
"""

import argparse
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SECTOR_SCRIPT = REPO_ROOT / "scripts" / "scrape_indeed_sector_daemon.py"
PYTHON_BIN = REPO_ROOT / "mcp-servers" / "indeed-mcp" / ".venv" / "bin" / "python"
if not PYTHON_BIN.exists():
    PYTHON_BIN = Path(sys.executable)

SECTORS = ["systems_hardware", "networking_noc", "cloud_cyber"]
processes = []

def stop_all(signum=None, frame=None):
    print(f"\n[SWARM] Received stop signal ({signum}). Stopping all sector daemons...")
    for p in processes:
        if p.poll() is None:
            try:
                p.terminate()
            except Exception:
                pass
    time.sleep(1)
    for p in processes:
        if p.poll() is None:
            try:
                p.kill()
            except Exception:
                pass
    print("[SWARM] All sector workers stopped cleanly.")
    sys.exit(0)

signal.signal(signal.SIGINT, stop_all)
signal.signal(signal.SIGTERM, stop_all)

def main():
    parser = argparse.ArgumentParser(description="Indeed Swarm Scraper Orchestrator")
    parser.add_argument("--interval", type=int, default=120, help="Query loop interval in seconds per sector (default: 120)")
    parser.add_argument("--hours-old", type=int, default=300, help="Lookback window in hours (default: 300 / ~12.5 days back to Sept 1)")
    parser.add_argument("--duration", type=int, default=None, help="Optional duration in minutes to run before automatically stopping")
    parser.add_argument("--limit", type=int, default=10, help="Results limit per query (default: 10)")
    args = parser.parse_args()

    print("=" * 70)
    print(" INDEED SWARM SCRAPER: Multi-Sector Continuous Swarm")
    print(f" Target: Golden Stickwood (Seneca CTYC) | Commute: <= 70 km from Newmarket")
    print(f" Sectors: {', '.join(SECTORS)}")
    print(f" Recency: Last {args.hours_old} hours (From Sept 1st on) | Interval: {args.interval}s")
    if args.duration:
        print(f" Scheduled Timer: Running for {args.duration} minutes")
    print("=" * 70)

    for sector in SECTORS:
        cmd = [
            str(PYTHON_BIN),
            str(SECTOR_SCRIPT),
            "--sector", sector,
            "-i", str(args.interval),
            "--hours-old", str(args.hours_old),
            "--limit", str(args.limit),
        ]
        log_file = REPO_ROOT / "logs" / f"scrape_indeed_{sector}.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        out_f = open(log_file, "a", encoding="utf-8")
        p = subprocess.Popen(cmd, stdout=out_f, stderr=subprocess.STDOUT)
        processes.append(p)
        print(f"[*] Launched Sector Worker: {sector:<18} (PID: {p.pid}) -> {log_file.name}")

    start_time = time.time()
    max_seconds = args.duration * 60 if args.duration else None

    try:
        while True:
            # Check worker health
            alive = sum(1 for p in processes if p.poll() is None)
            if alive == 0:
                print("[SWARM] All workers finished.")
                break
            
            if max_seconds and (time.time() - start_time) >= max_seconds:
                print(f"\n[SWARM] Scheduled duration of {args.duration} minutes reached.")
                break

            time.sleep(2)
    finally:
        stop_all()

if __name__ == "__main__":
    main()
