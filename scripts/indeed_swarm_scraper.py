#!/usr/bin/env python3
"""
Indeed Swarm Scraper Orchestrator
Coordinates parallel continuous sector-scraping worker processes across Indeed Canada:
Sectors and search queries are loaded dynamically from config/swarm_sectors.json.

Enforces:
- Candidate qualification matching
- Commute threshold from candidate's home location
- Atomic deduplication in seen_jobs.json
- Automatic rebuild of job_search_tracker.csv and application-dashboard.html
"""

import argparse
import json
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

SWARM_CONFIG_FILE = REPO_ROOT / "config" / "swarm_sectors.json"

def get_swarm_config():
    cfg = {
        "candidate": "Candidate",
        "home": "Toronto, ON",
        "max_km": 70,
        "sectors": ["systems_hardware", "networking_noc", "cloud_cyber"],
    }
    if SWARM_CONFIG_FILE.exists():
        try:
            with open(SWARM_CONFIG_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
                if "target_candidate" in d:
                    cfg["candidate"] = d["target_candidate"]
                if "home_location" in d:
                    cfg["home"] = d["home_location"]
                if "max_distance_km" in d:
                    cfg["max_km"] = d["max_distance_km"]
                if "sectors" in d and isinstance(d["sectors"], dict) and d["sectors"]:
                    cfg["sectors"] = list(d["sectors"].keys())
        except Exception:
            pass
    return cfg

SWARM_CFG = get_swarm_config()
SECTORS = SWARM_CFG["sectors"]
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
    parser.add_argument("--sectors", type=str, default=None, help="Comma-separated sectors to run (e.g. 'systems_hardware,cloud_cyber')")
    parser.add_argument("--interval", type=int, default=120, help="Query loop interval in seconds per sector (default: 120)")
    parser.add_argument("--hours-old", type=int, default=300, help="Lookback window in hours (default: 300)")
    parser.add_argument("--duration", type=int, default=None, help="Optional duration in minutes to run before automatically stopping")
    parser.add_argument("--limit", type=int, default=10, help="Results limit per query (default: 10)")
    args = parser.parse_args()

    active_sectors = [s.strip() for s in args.sectors.split(",")] if args.sectors else SECTORS

    print("=" * 70)
    print(" INDEED SWARM SCRAPER: Multi-Sector Continuous Swarm")
    print(f" Target: {SWARM_CFG['candidate']} | Commute: <= {SWARM_CFG['max_km']} km from {SWARM_CFG['home']}")
    print(f" Active Sectors: {', '.join(active_sectors)}")
    print(f" Recency: Last {args.hours_old} hours | Interval: {args.interval}s")
    if args.duration:
        print(f" Scheduled Timer: Running for {args.duration} minutes")
    print("=" * 70)

    for sector in active_sectors:
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
