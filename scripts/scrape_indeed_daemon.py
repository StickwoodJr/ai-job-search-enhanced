#!/usr/bin/env python3
"""
Continuous Indeed Canada Scrape Daemon
Runs the /cmd-scrape-indeed workflow in a continuous loop until stopped.
Automatically updates job_scraper/seen_jobs.json, job_search_tracker.csv,
and rebuilds reports/application-dashboard.html.
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
LOG_FILE = REPO_ROOT / "logs" / "scrape_indeed_daemon.log"
REBUILD_SCRIPT = REPO_ROOT / "scripts" / "rebuild_dashboard.py"

# Logging setup
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("indeed-daemon")

running = True

def handle_exit(signum, frame):
    global running
    logger.info("Received termination signal (%s). Shutting down Indeed scrape daemon cleanly...", signum)
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

def evaluate_job(title: str, description: str, query: str) -> Tuple[str, bool]:
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

def run_cycle(queries: List[Tuple[str, str]], limit: int = 10, hours_old: int = 336) -> int:
    seen_urls = load_seen_urls()
    newly_found_count = 0

    for query, location in queries:
        if not running:
            break
        logger.info("Scanning Indeed: '%s' in '%s' (last %d hours)", query, location, hours_old)
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

                # Fetch full details
                detail = perform_detail(job_id, country="canada")
                desc = detail.get("description") or item.get("description_snippet") or ""

                fit_level, is_target_term = evaluate_job(title, desc, query)
                if fit_level in ("high", "medium"):
                    logger.info("🎯 DISCOVERED MATCHING JOB (%s): %s - %s (%s)", fit_level.upper(), comp, title, location)
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
                        "source": "cli",
                        "description": desc,
                    }
                    save_seen_job(job_record)
                    seen_urls.add(url)
                    newly_found_count += 1
                else:
                    # Still record in seen to avoid re-fetching details
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
                        "source": "cli",
                    })
                    seen_urls.add(url)

                time.sleep(1.0)  # Gentle throttle

        except Exception as e:
            logger.warning("Error searching '%s' in '%s': %s", query, location, e)

        time.sleep(2.0)  # Inter-query throttle

    return newly_found_count

def main():
    parser = argparse.ArgumentParser(description="Continuous Indeed Canada Scrape Daemon")
    parser.add_argument("-i", "--interval", type=int, default=120, help="Loop interval in seconds (default: 120)")
    parser.add_argument("--jobage", type=int, default=14, help="Max posting age in days (default: 14)")
    parser.add_argument("--hours-old", type=int, default=None, help="Max posting age in hours (overrides --jobage)")
    parser.add_argument("--limit", type=int, default=10, help="Results limit per query (default: 10)")
    args = parser.parse_args()

    hours_old = args.hours_old if args.hours_old is not None else (args.jobage * 24)

    queries = []
    swarm_config = REPO_ROOT / "config" / "swarm_sectors.json"
    candidate_name = "Candidate"
    if swarm_config.exists():
        try:
            with open(swarm_config, "r", encoding="utf-8") as f:
                s_data = json.load(f)
                candidate_name = s_data.get("target_candidate", "Candidate")
                default_loc = s_data.get("home_location", "Toronto, ON")
                for sec in s_data.get("sectors", {}).values():
                    for q in sec.get("queries", []):
                        if isinstance(q, (list, tuple)) and len(q) >= 2:
                            queries.append((str(q[0]), str(q[1])))
                        elif isinstance(q, str):
                            queries.append((q, default_loc))
        except Exception:
            pass

    if not queries:
        queries = [
            ("Software Engineer", "Toronto, ON"),
            ("Systems Administrator", "Toronto, ON"),
            ("Data Analyst", "Toronto, ON"),
            ("IT Support Specialist", "Toronto, ON"),
            ("Cloud Engineer", "Toronto, ON"),
        ]

    logger.info("==================================================================")
    logger.info("Starting Indeed Canada Continuous Scrape Daemon")
    logger.info("Target: %s | Interval: %d seconds | Queries: %d", candidate_name, args.interval, len(queries))
    logger.info("==================================================================")

    cycle_num = 1
    while running:
        logger.info(">>> Beginning Scrape Cycle #%d (%s) <<<", cycle_num, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        new_jobs = run_cycle(queries, limit=args.limit, hours_old=hours_old)

        if new_jobs > 0:
            logger.info("Cycle #%d complete: Found %d new posting(s)! Triggering tracker & dashboard rebuild...", cycle_num, new_jobs)
            try:
                subprocess.run([sys.executable, str(REBUILD_SCRIPT)], check=True)
                logger.info("Tracker and application dashboard successfully updated!")
            except Exception as e:
                logger.error("Error rebuilding dashboard: %s", e)
        else:
            logger.info("Cycle #%d complete: No new postings this cycle. Pipeline up-to-date.", cycle_num)

        cycle_num += 1

        # Sleep in small increments to respond immediately to stop signal
        for _ in range(args.interval):
            if not running:
                break
            time.sleep(1)

    logger.info("Indeed Canada Continuous Scrape Daemon stopped successfully.")

if __name__ == "__main__":
    main()
