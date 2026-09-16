#!/usr/bin/env python3
"""
Continuous Indeed Canada Scrape Daemon
Runs the /cmd-scrape-indeed workflow in a continuous loop until stopped.
Specifically targets Winter 2027 Co-op opportunities across the GTA and Ontario.
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
REBUILD_SCRIPT = REPO_ROOT / "scripts" / "rebuild_tracker_and_dashboard_winter_only.py"

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

# Schooling filter: Exclusively keep roles aligned with Seneca Polytechnic Computer Systems Technology (CTYC)
DISQUALIFIED_PATTERNS = [
    # Software Engineering / Developer / Blockchain
    r'\bsoftware\b', r'\bdeveloper\b', r'\bdevelopment\b', r'\bprogrammer\b', r'\bprogramming\b',
    r'\bfull[- ]?stack\b', r'\bfrontend\b', r'\bfront-end\b', r'\bbackend\b', r'\bback-end\b',
    r'\bblockchain\b', r'\bweb dev\b', r'\bmobile dev\b', r'\bapp dev\b', r'\bios dev\b',
    r'\bandroid dev\b', r'\bqa automation\b', r'\bquality engineer\b', r'\btest automation\b',
    r'\btest engineer\b', r'\bqa engineer\b', r'\bqa analyst\b', r'\bquality assurance\b',
    r'\bdesign engineer\b',

    # AI / Machine Learning / Data Science / Analytics / BI / Analytics Engineering
    r'\bai\b', r'\bml\b', r'\bai/ml\b', r'machine learning', r'deep learning',
    r'artificial intelligence', r'data scientist', r'data science', r'data analytics',
    r'data analyst', r'data engineer', r'data engineering', r'analytics engineer',
    r'analytics engineering', r'business intelligence', r'\bbi\b', r'power bi', r'tableau',
    r'insights', r'market research', r'reporting analyst', r'analytics', r'statistician',
    r'quantitative', r'data governance', r'generative',

    # Business Analysis / Process Analysis / Business Admin / General Commerce / Management
    r'business analyst', r'business information analyst', r'business system analyst',
    r'process analyst', r'process support', r'process and change', r'business admin',
    r'business administration', r'general commerce', r'commerce', r'business management',
    r'business planning', r'strategy', r'strategic', r'transformation', r'practice management',
    r'project management', r'product management', r'project coordinator', r'product manager',
    r'project manager', r'scrum', r'agile', r'delivery & execution', r'product delivery',
    r'product information', r'proposal', r'change management', r'operations analyst',
    r'administration and operations', r'internal administration', r'administration & support',
    r'business technology', r'governance & control', r'governance co-op', r'corporate reliability',
    r'enterprise architecture',

    # Finance / Banking / Accounting / Audit / Risk / Insurance
    r'accounting', r'accountant', r'audit', r'auditor', r'tax', r'payroll',
    r'finance', r'financial', r'fund management', r'treasury', r'underwriting',
    r'actuarial', r'derivative', r'credit', r'equity', r'capital markets',
    r'transaction banking', r'commercial banking', r'banking', r'investing',
    r'investment', r'investments', r'wealth', r'broker', r'trader', r'trading',
    r'trade desk', r'product control', r'portfolio', r'm&a', r'mergers',
    r'hedging', r'venture capital', r'risk', r'regulatory', r'compliance',
    r'aml', r'control testing', r'liquidity', r'expense management', r'deposits',
    r'money movement', r'compensation', r'shareholder', r'intra-group',
    r'real estate', r'account manager', r'national accounts', r'working capital',
    r'payments modernization', r'one td',

    # Sales / Marketing / HR / Creative / Communications / UX
    r'sales', r'marketing', r'communications', r'creative', r'content', r'copywriter',
    r'social media', r'human resources', r'\bhr\b', r'talent acquisition', r'recruiter',
    r'recruiting', r'public relations', r'shopper', r'merchandising', r'customer service',
    r'contact center', r'client management', r'colleague', r'employee experience',
    r'member experience', r'workforce', r'ux researcher', r'ux/product', r'product design',
    r'campus programs', r'discovery', r'analyst relations', r'innovation partner',

    # Supply Chain / Logistics / Non-IT Operations & Trades & Engineering
    r'supply chain', r'procurement', r'buyer', r'sourcing', r'replenishment',
    r'warehouse', r'logistics', r'production group leader', r'production supervisor',
    r'production engineering', r'manufacturing', r'lean performance', r'operations delivery',
    r'branch operations', r'esg', r'sustainability', r'network flow', r'civil',
    r'construction', r'structural', r'mechatronic', r'mechanical', r'electrical engineering',
    r'electrical/computer', r'power systems', r'cad design', r'paper mill',
    r'battery degradation', r'design co-op', r'design technologist', r'product engineering',
    r'water & wastewater', r'tailings', r'geotech', r'metallurg', r'piping',
    r'architect', r'interior', r'environmental', r'agricultural', r'agriculture',
    r'oncology', r'health & safety', r'safety assistant', r'qa inspector',
    r'case mix', r'nurse', r'nursing', r'medical', r'dental', r'pharmacy',
    r'quality engineering', r'engineering - durham',
]

IT_POSITIVE_PATTERNS = [
    r'\bsystems?\b', r'\blinux\b', r'\bwindows\b', r'\bnetworks?\b', r'\bnetworking\b',
    r'\binfrastructure\b', r'\bcloud\b', r'\bdevops\b', r'cyber', r'security',
    r'\bservice desk\b', r'\bhelpdesk\b', r'\bhelp desk\b', r'\bdesktop\b', r'\btechnician\b',
    r'\btechnical\b', r'\btechnology\b', r'\bit\b', r'\binformation technology\b',
    r'\bcomputer\b', r'\bhardware\b', r'\bdatacenter\b', r'\bdata center\b',
    r'\btelecom\b', r'\bsoc\b', r'\bnoc\b', r'\badmin\b', r'\badministrator\b',
    r'\bdatabase\b', r'\basset management\b', r'\bmicrosoft 365\b', r'\bm365\b', r'\bcisco\b',
]

def is_schooling_fit(role_title: str) -> bool:
    t = role_title.lower()
    for pat in DISQUALIFIED_PATTERNS:
        if re.search(pat, t, re.IGNORECASE):
            if pat in ('risk', 'regulatory', 'compliance') and ('cyber' in t or 'security' in t):
                continue
            if pat in ('capital markets', 'banking', 'equity', 'wealth') and any(k in t for k in ['devops', 'cloud', 'cyber', 'security', 'systems', 'infrastructure']):
                continue
            return False
    return any(re.search(pat, t, re.IGNORECASE) for pat in IT_POSITIVE_PATTERNS)

def is_explicit_winter_coop(company: str, role: str, text_blob: str) -> bool:
    combined = f"{company} {role} {text_blob}".lower()
    winter_terms = [
        "winter 2027", "2027 winter", "winter 2026", "2026 winter", "winter co-op", "winter coop",
        "winter internship", "winter term", "winter student", "winter- student",
        "winter technology", "winter intern", "co-op winter", "coop winter",
        "internship winter", "hiver 2027", "2027 hiver", "stage hiver",
        "january 2027", "janvier 2027", "jan 2027", "jan - apr",
        "january - april"
    ]
    has_winter = any(w in combined for w in winter_terms)
    is_summer_only = (
        ("summer 2027" in combined or "summer 2026" in combined or "may - aug" in combined)
        and not has_winter
        and "8 month" not in combined
        and "12 month" not in combined
    )
    return has_winter and not is_summer_only

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

                if is_explicit_winter_coop(comp, title, desc) and is_schooling_fit(title):
                    logger.info("🎯 DISCOVERED EXPLICIT WINTER CO-OP (CTYC FIT): %s - %s (%s)", comp, title, location)
                    job_record = {
                        "title": title,
                        "company": comp,
                        "url": url,
                        "first_seen": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                        "deadline": detail.get("deadline"),
                        "fit": "high",
                        "is_winter": True,
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

    queries = [
        ("Linux Co-op Winter 2027", "Toronto, ON"),
        ("Systems Administrator Co-op Winter 2027", "Toronto, ON"),
        ("Network Administrator Co-op Winter 2027", "Toronto, ON"),
        ("IT Support Co-op Winter 2027", "Toronto, ON"),
        ("Cloud Infrastructure Co-op Winter 2027", "Toronto, ON"),
        ("Cyber Security Co-op Winter 2027", "Toronto, ON"),
        ("Service Desk Technician Co-op Winter 2027", "Toronto, ON"),
        ("Desktop Support Co-op Winter 2027", "York Region, ON"),
        ("IT Operations Co-op Winter 2027", "Markham, ON"),
        ("Technical Systems Analyst Co-op Winter 2027", "Toronto, ON"),
        ("Windows Server Active Directory Co-op Winter 2027", "Toronto, ON"),
        ("Hardware Technician Co-op Winter 2027", "Mississauga, ON"),
    ]

    logger.info("==================================================================")
    logger.info("Starting Indeed Canada Continuous Scrape Daemon (Winter 2027 Focus)")
    logger.info("Target: Golden Stickwood | Interval: %d seconds | Queries: %d", args.interval, len(queries))
    logger.info("==================================================================")

    cycle_num = 1
    while running:
        logger.info(">>> Beginning Scrape Cycle #%d (%s) <<<", cycle_num, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        new_jobs = run_cycle(queries, limit=args.limit, hours_old=hours_old)

        if new_jobs > 0:
            logger.info("Cycle #%d complete: Found %d new explicit Winter Co-op(s)! Triggering tracker & dashboard rebuild...", cycle_num, new_jobs)
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
