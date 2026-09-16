#!/usr/bin/env python3
"""
Indeed Swarm Scraper Workflow Runner
Coordinates 3 specialized sector scraper agents across Indeed Canada:
1. systems_hardware: Linux, Systems Admin, Windows Server/AD, Service Desk, Desktop Support, Hardware & Datacenter
2. networking_noc: Cisco, Network Admin, Routing/Switching, Telecom, NOC Operations, Network Security
3. cloud_cyber: Cloud Infrastructure (AWS/Azure), DevOps, Cybersecurity, Information Security, SOC Analysis, TSA
"""

import argparse
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List

REPO_ROOT = Path(__file__).resolve().parent.parent
SECTOR_SCRIPT = REPO_ROOT / "scripts" / "scrape_indeed_sector_daemon.py"
REBUILD_SCRIPT = REPO_ROOT / "scripts" / "rebuild_tracker_and_dashboard_winter_only.py"

SECTORS = ["systems_hardware", "networking_noc", "cloud_cyber"]
procs: List[subprocess.Popen] = []

def handle_exit(signum, frame):
    print(f"\n[SWARM] Received termination signal ({signum}). Stopping all sector daemons...")
    for p in procs:
        try:
            p.terminate()
        except Exception:
            pass
    sys.exit(0)

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

def main():
    parser = argparse.ArgumentParser(description="Indeed Swarm Scraper Workflow Runner")
    parser.add_argument("-i", "--interval", type=int, default=120, help="Loop interval per sector in seconds (default: 120)")
    parser.add_argument("--hours-old", type=int, default=None, help="Max posting age in hours (default: calculated or 336)")
    parser.add_argument("--from-date", type=str, default=None, help="Scrape all postings from this ISO date onward (e.g. '2026-09-01')")
    parser.add_argument("--duration", type=int, default=None, help="Run swarm for N seconds and then exit cleanly")
    parser.add_argument("--limit", type=int, default=50, help="Results limit per query (default: 50)")
    parser.add_argument("--max-empty-cycles", type=int, default=None, help="Stop after N consecutive cycles across all sectors with 0 new postings")
    args = parser.parse_args()

    print("==================================================================")
    print(" 🚀 LAUNCHING INDEED SWARM SCRAPER (3 SECTOR WORKFLOW)")
    print("==================================================================")
    print(f"Sectors: {', '.join(SECTORS)}")
    print(f"Interval: {args.interval}s | Limit per query: {args.limit}")
    if args.from_date:
        print(f"Lookback: All postings from {args.from_date} onward")
    elif args.hours_old:
        print(f"Lookback: Last {args.hours_old} hours")
    if args.duration:
        print(f"Duration: {args.duration} seconds ({args.duration/60:.1f} minutes)")
    if args.max_empty_cycles:
        print(f"Auto-stop: Terminating after {args.max_empty_cycles} consecutive empty cycles across all sectors")
    print("==================================================================\n")

    for sector in SECTORS:
        cmd = [
            sys.executable,
            str(SECTOR_SCRIPT),
            "--sector", sector,
            "-i", str(args.interval),
            "--limit", str(args.limit),
        ]
        if args.from_date:
            cmd.extend(["--from-date", args.from_date])
        elif args.hours_old:
            cmd.extend(["--hours-old", str(args.hours_old)])

        p = subprocess.Popen(cmd)
        procs.append(p)
        print(f"[SWARM] Started sector daemon: {sector} (PID: {p.pid})")
        time.sleep(1.0)

    start_time = time.time()
    sector_cycles = {s: 0 for s in SECTORS}
    empty_streaks = {s: 0 for s in SECTORS}
    log_files = {s: REPO_ROOT / "logs" / f"scrape_indeed_{s}.log" for s in SECTORS}
    log_positions = {s: 0 for s in SECTORS}

    # Initialize log positions
    for s, log_p in log_files.items():
        if log_p.exists():
            log_positions[s] = log_p.stat().st_size

    try:
        while True:
            # Check if duration limit reached
            if args.duration and (time.time() - start_time) >= args.duration:
                print(f"\n[SWARM] Target duration ({args.duration}s) reached. Shutting down swarm...")
                break

            # Read new log lines from each sector to track cycle results
            for s, log_p in log_files.items():
                if not log_p.exists():
                    continue
                current_size = log_p.stat().st_size
                if current_size > log_positions[s]:
                    try:
                        with open(log_p, "r", encoding="utf-8", errors="ignore") as f:
                            f.seek(log_positions[s])
                            new_text = f.read()
                            log_positions[s] = f.tell()

                        for line in new_text.splitlines():
                            # Pattern: Cycle #X complete: No new postings this cycle.
                            m_empty = re.search(r"Cycle #(\d+) complete: No new postings this cycle", line)
                            if m_empty:
                                cycle_num = int(m_empty.group(1))
                                if cycle_num > sector_cycles[s]:
                                    sector_cycles[s] = cycle_num
                                    empty_streaks[s] += 1
                                    print(f"[SWARM MONITOR] Sector '{s}' completed Cycle #{cycle_num} (consecutive empty: {empty_streaks[s]})")

                            # Pattern: Cycle #X complete: Found Y new Winter Co-op(s)!
                            m_found = re.search(r"Cycle #(\d+) complete: Found (\d+) new Winter Co-op", line)
                            if m_found:
                                cycle_num = int(m_found.group(1))
                                count = int(m_found.group(2))
                                if cycle_num > sector_cycles[s]:
                                    sector_cycles[s] = cycle_num
                                    empty_streaks[s] = 0
                                    print(f"[SWARM MONITOR] Sector '{s}' completed Cycle #{cycle_num} (FOUND {count} NEW ROLES!)")
                    except Exception as e:
                        pass

            # Check if max empty cycles reached across all sectors
            if args.max_empty_cycles:
                if all(empty_streaks[s] >= args.max_empty_cycles for s in SECTORS):
                    print(f"\n[SWARM] Target reached: All 3 sectors completed {args.max_empty_cycles} consecutive cycles with 0 new postings.")
                    print(f"[SWARM] Shutting down swarm...")
                    break

            # Check if all processes still alive
            for i, p in enumerate(procs):
                ret = p.poll()
                if ret is not None:
                    print(f"[SWARM WARNING] Sector daemon {SECTORS[i]} exited with code {ret}")

            time.sleep(2)
    finally:
        for p in procs:
            try:
                p.terminate()
            except Exception:
                pass
        for p in procs:
            try:
                p.wait(timeout=5)
            except Exception:
                p.kill()

    print("\n[SWARM] Running final tracker and application dashboard rebuild...")
    try:
        subprocess.run([sys.executable, str(REBUILD_SCRIPT)], check=True)
    except Exception as e:
        print(f"Error rebuilding dashboard: {e}")

    print("[SWARM] Swarm run completed successfully.")

if __name__ == "__main__":
    main()
