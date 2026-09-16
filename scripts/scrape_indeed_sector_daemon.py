#!/usr/bin/env python3
"""
Multi-Sector Indeed Canada Continuous Scrape Daemon
Enables running dedicated continuous scraper agents for configured sectors.
Coordinates search, atomic deduplication, and tracker/dashboard synchronization.
"""

import argparse
import fcntl
import json
import logging
import os
import re
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
VENV_PYTHON = REPO_ROOT / "mcp-servers" / "indeed-mcp" / ".venv" / "bin" / "python"

if VENV_PYTHON.exists() and sys.executable != str(VENV_PYTHON):
    os.execv(str(VENV_PYTHON), [str(VENV_PYTHON)] + sys.argv)

sys.path.insert(0, str(REPO_ROOT / "mcp-servers" / "indeed-mcp"))
try:
    from server import perform_search, perform_detail
except ImportError as e:
    print(f"Error importing Indeed MCP server backend: {e}", file=sys.stderr)
    sys.exit(1)

SEEN_JOBS_FILE = REPO_ROOT / "job_scraper" / "seen_jobs.json"
TRACKER_FILE = REPO_ROOT / "job_search_tracker.csv"
SWARM_CONFIG_FILE = REPO_ROOT / "config" / "swarm_sectors.json"
REBUILD_SCRIPT = REPO_ROOT / "scripts" / "rebuild_dashboard.py"

DEFAULT_SECTOR_QUERIES: Dict[str, List[Tuple[str, str]]] = {
    "systems_hardware": [
        ("Linux Administrator", "Toronto, ON"),
        ("Systems Administrator", "Toronto, ON"),
        ("Windows Server Active Directory", "Toronto, ON"),
        ("IT Support Specialist", "York Region, ON"),
        ("Desktop Support", "Markham, ON"),
        ("Service Desk Technician", "Toronto, ON"),
        ("Hardware Technician", "Mississauga, ON"),
        ("Datacenter Technician", "Toronto, ON"),
        ("IT Workplace Services", "Toronto, ON"),
    ],
    "networking_noc": [
        ("Network Administrator", "Toronto, ON"),
        ("Network Support Specialist", "Toronto, ON"),
        ("Cisco Network Engineer", "Toronto, ON"),
        ("NOC Analyst", "Toronto, ON"),
        ("NOC Technician", "Toronto, ON"),
        ("Telecom Technician", "Mississauga, ON"),
        ("Network Infrastructure", "Markham, ON"),
        ("Network Security Specialist", "Toronto, ON"),
    ],
    "cloud_cyber": [
        ("Cloud Infrastructure Specialist", "Toronto, ON"),
        ("Cloud Engineer", "Toronto, ON"),
        ("DevOps Engineer", "Toronto, ON"),
        ("Cybersecurity Analyst", "Toronto, ON"),
        ("Information Security Specialist", "Toronto, ON"),
        ("SOC Analyst", "Toronto, ON"),
        ("Vulnerability Analyst", "Toronto, ON"),
        ("Technical Systems Analyst", "Toronto, ON"),
    ],
}

def load_sector_queries() -> Dict[str, List[Tuple[str, str]]]:
    """Load sector queries from config/swarm_sectors.json or return defaults."""
    if SWARM_CONFIG_FILE.exists():
        try:
            with open(SWARM_CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                sectors = data.get("sectors", {})
                loaded = {}
                default_loc = data.get("home_location", "Toronto, ON")
                for sec_key, sec_info in sectors.items():
                    raw_queries = sec_info.get("queries", [])
                    query_list = []
                    for q in raw_queries:
                        if isinstance(q, (list, tuple)) and len(q) >= 2:
                            query_list.append((str(q[0]), str(q[1])))
                        elif isinstance(q, str):
                            query_list.append((q, default_loc))
                    if query_list:
                        loaded[sec_key] = query_list
                if loaded:
                    return loaded
        except Exception as e:
            sys.stderr.write(f"Warning: Failed to load swarm_sectors.json: {e}\n")
    return DEFAULT_SECTOR_QUERIES

SECTOR_QUERIES = load_sector_queries()

running = True

def handle_exit(signum, frame):
    global running
    sys.stderr.write(f"Received termination signal ({signum}). Shutting down sector daemon cleanly...\n")
    running = False

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

def load_seen_urls() -> Set[str]:
    if not SEEN_JOBS_FILE.exists():
        return set()
    try:
        with open(SEEN_JOBS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data.get("seen", {}).keys())
    except Exception:
        return set()

def save_seen_job(job_record: Dict[str, Any]) -> None:
    lock_file = SEEN_JOBS_FILE.with_suffix(".lock")
    with open(lock_file, "w") as lock_f:
        fcntl.flock(lock_f, fcntl.LOCK_EX)
        try:
            current_data = {"seen": {}}
            if SEEN_JOBS_FILE.exists():
                try:
                    with open(SEEN_JOBS_FILE, "r", encoding="utf-8") as f:
                        current_data = json.load(f)
                        if "seen" not in current_data or not isinstance(current_data["seen"], dict):
                            current_data["seen"] = {}
                except Exception:
                    pass
            url = job_record.get("url")
            if url:
                current_data["seen"][url] = job_record
            tmp_file = SEEN_JOBS_FILE.with_suffix(".tmp")
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(current_data, f, indent=2)
            tmp_file.replace(SEEN_JOBS_FILE)
        finally:
            fcntl.flock(lock_f, fcntl.LOCK_UN)

UNRELATED_TRADES = [
    "registered nurse", "licensed practical nurse", "forklift operator",
    "truck driver", "dental assistant", "dental hygienist", "plumber",
    "electrician", "hvac technician", "line cook", "dishwasher"
]

def evaluate_sector_job(title: str, description: str, sector_name: str, query: str) -> Tuple[str, bool]:
    """Evaluate job relevance for the specified sector and query."""
    text = f"{title} {description}".lower()
    q_lower = query.lower()

    if any(trade in text for trade in UNRELATED_TRADES):
        return "low", False

    term_keywords = ["co-op", "coop", "intern", "internship", "student", "entry level", "junior", "new grad", "associate"]
    is_target_term = any(t in text for t in term_keywords)

    query_words = [w for w in q_lower.split() if len(w) > 3 and w not in ("co-op", "intern", "student", "junior")]
    query_match = any(qw in text for qw in query_words) if query_words else True

    if query_match and is_target_term:
        return "high", True
    elif query_match:
        return "high", False
    elif is_target_term:
        return "medium", True
    else:
        return "medium", False

def run_cycle(queries: List[Tuple[str, str]], sector_name: str, limit: int = 10, hours_old: int = 336, logger: logging.Logger = None) -> int:
    seen_urls = load_seen_urls()
    newly_found_count = 0

    for query, location in queries:
        if not running:
            break
        if logger:
            logger.info("[%s] Scanning Indeed: '%s' in '%s' (last %d hours)", sector_name, query, location, hours_old)
        try:
            is_remote = "remote" in location.lower()
            res = perform_search(
                query=query,
                location=location,
                country="canada",
                results_wanted=limit,
                hours_old=hours_old,
                is_remote=is_remote,
            )
            items = res.get("results", [])
            for item in items:
                if not running:
                    break
                url = item.get("url") or ""
                comp = (item.get("company") or "").strip()
                title = (item.get("title") or "").strip()
                job_id = item.get("id") or url

                if not url or not comp or not title or url in seen_urls:
                    continue

                detail = perform_detail(job_id, country="canada")
                desc = detail.get("description") or item.get("description_snippet") or ""

                fit_level, is_target_term = evaluate_sector_job(title, desc, sector_name, query)

                if fit_level in ("high", "medium"):
                    if logger:
                        logger.info("🎯 [%s] FOUND JOB (%s): %s - %s (%s)", sector_name, fit_level.upper(), comp, title, location)
                    job_record = {
                        "title": title,
                        "company": comp,
                        "url": url,
                        "first_seen": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                        "deadline": detail.get("deadline"),
                        "fit": fit_level,
                        "is_winter": is_target_term,
                        "status": "new",
                        "portal": "indeed-search",
                        "source": f"sector_{sector_name}",
                        "description": desc,
                    }
                    save_seen_job(job_record)
                    seen_urls.add(url)
                    newly_found_count += 1
                else:
                    save_seen_job({
                        "title": title,
                        "company": comp,
                        "url": url,
                        "first_seen": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                        "deadline": None,
                        "fit": "low",
                        "is_winter": False,
                        "status": "filtered",
                        "portal": "indeed-search",
                        "source": f"sector_{sector_name}",
                    })
                    seen_urls.add(url)

                time.sleep(1.0)

        except Exception as e:
            if logger:
                logger.warning("[%s] Error searching '%s': %s", sector_name, query, e)

        time.sleep(2.0)

    return newly_found_count

def main():
    parser = argparse.ArgumentParser(description="Multi-Sector Indeed Continuous Scrape Daemon")
    parser.add_argument("--sector", required=True, help="Sector key to cover (defined in config/swarm_sectors.json or defaults)")
    parser.add_argument("-i", "--interval", type=int, default=120, help="Loop interval in seconds (default: 120)")
    parser.add_argument("--hours-old", type=int, default=336, help="Max posting age in hours (default: 336 / 14 days)")
    parser.add_argument("--from-date", type=str, default=None, help="Scrape all postings from this ISO date onward (e.g. '2026-09-01')")
    parser.add_argument("--limit", type=int, default=50, help="Results limit per query (default: 50)")
    args = parser.parse_args()

    sector_name = args.sector
    queries = SECTOR_QUERIES.get(sector_name, [])

    if args.from_date:
        start_dt = datetime.fromisoformat(args.from_date).replace(tzinfo=timezone.utc)
        now_dt = datetime.now(timezone.utc)
        hours_old = max(1, int((now_dt - start_dt).total_seconds() / 3600) + 24)
    else:
        hours_old = args.hours_old

    log_file = REPO_ROOT / "logs" / f"scrape_indeed_{sector_name}.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format=f"[%(asctime)s] [{sector_name.upper()}] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )
    logger = logging.getLogger(f"indeed-{sector_name}")

    logger.info("==================================================================")
    logger.info("Starting Sector Scraper: %s", sector_name)
    logger.info("Queries: %d | Interval: %ds | Hours Old: %d", len(queries), args.interval, hours_old)
    logger.info("==================================================================")

    cycle_num = 1
    while running:
        logger.info(">>> Sector %s: Beginning Cycle #%d <<<", sector_name, cycle_num)
        new_jobs = run_cycle(queries, sector_name=sector_name, limit=args.limit, hours_old=hours_old, logger=logger)

        if new_jobs > 0:
            logger.info("Cycle #%d complete: Found %d new posting(s)! Rebuilding tracker & dashboard...", cycle_num, new_jobs)
            try:
                subprocess.run([sys.executable, str(REBUILD_SCRIPT)], check=True)
                logger.info("Tracker and application dashboard successfully updated!")
            except Exception as e:
                logger.error("Error rebuilding dashboard: %s", e)
        else:
            logger.info("Cycle #%d complete: No new postings this cycle.", cycle_num)

        cycle_num += 1

        for _ in range(args.interval):
            if not running:
                break
            time.sleep(1)

    logger.info("Sector %s daemon stopped successfully.", sector_name)

if __name__ == "__main__":
    main()
