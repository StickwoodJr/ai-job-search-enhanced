#!/usr/bin/env python3
"""
Dedicated Indeed Scrape Workflow Runner
Focuses exclusively on Indeed Canada (ca.indeed.com) postings.
Deduplicates against seen_jobs.json and job_search_tracker.csv,
fetches full descriptions, assesses candidate fit, updates state,
and generates LinkedIn referral search links.
"""

import argparse
import csv
import fcntl
import json
import logging
import os
import re
import subprocess
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Workspace paths
REPO_ROOT = Path(__file__).resolve().parent.parent
VENV_PYTHON = REPO_ROOT / "mcp-servers" / "indeed-mcp" / ".venv" / "bin" / "python"

# Auto-re-exec into dedicated virtual environment if needed
if VENV_PYTHON.exists() and sys.executable != str(VENV_PYTHON):
    os.execv(str(VENV_PYTHON), [str(VENV_PYTHON)] + sys.argv)

# Import server functions
sys.path.insert(0, str(REPO_ROOT / "mcp-servers" / "indeed-mcp"))
try:
    from server import perform_search, perform_detail
except ImportError as e:
    print(f"Error importing Indeed MCP server backend: {e}", file=sys.stderr)
    sys.exit(1)

SEEN_JOBS_FILE = REPO_ROOT / "job_scraper" / "seen_jobs.json"
TRACKER_FILE = REPO_ROOT / "job_search_tracker.csv"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("scrape-indeed")


def load_seen_jobs() -> Dict[str, Any]:
    if not SEEN_JOBS_FILE.exists():
        return {"seen": {}}
    try:
        with open(SEEN_JOBS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "seen" not in data or not isinstance(data["seen"], dict):
                data["seen"] = {}
            return data
    except Exception as e:
        logger.warning("Could not parse seen_jobs.json (%s), initializing clean state", e)
        return {"seen": {}}


def save_seen_jobs(seen_data: Dict[str, Any]) -> None:
    SEEN_JOBS_FILE.parent.mkdir(parents=True, exist_ok=True)
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
            new_items = seen_data.get("seen", seen_data)
            current_data["seen"].update(new_items)
            tmp_file = SEEN_JOBS_FILE.with_suffix(".tmp")
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(current_data, f, indent=2)
            tmp_file.replace(SEEN_JOBS_FILE)
        finally:
            fcntl.flock(lock_f, fcntl.LOCK_UN)


def load_tracker_exclusions() -> Tuple[Set[Tuple[str, str]], Set[str]]:
    exclusions: Set[Tuple[str, str]] = set()
    url_exclusions: Set[str] = set()
    if not TRACKER_FILE.exists():
        return exclusions, url_exclusions
    try:
        with open(TRACKER_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                comp = (row.get("company") or row.get("Company") or "").strip().lower()
                role = (row.get("role") or row.get("Role") or "").strip().lower()
                url = (row.get("Posting URL") or row.get("posting_url") or row.get("url") or "").strip()
                if comp and role:
                    exclusions.add((comp, role))
                if url:
                    url_exclusions.add(url)
    except Exception as e:
        logger.warning("Error reading tracker file: %s", e)
    return exclusions, url_exclusions


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


def evaluate_fit(title: str, description: str, winter_focus: bool = True) -> Tuple[str, bool]:
    """
    Rapid triage fit rating for Golden Stickwood:
    - Core skills: Linux (CentOS/RHEL/Ubuntu), Windows Server (AD DS, GPO), Cisco IOS (VLANs, Routing), Homelab/Zero-Trust
    - Target: Winter 2027 Co-op / Junior Systems Administrator
    Returns: (fit_level, is_winter_coop)
    """
    # Strict schooling alignment check
    if not is_schooling_fit(title):
        return ("low", False)

    text = f"{title} {description}".lower()

    # Winter co-op identification
    winter_terms = ["winter 2027", "winter 2026", "winter co-op", "winter coop", "winter internship", "winter term", "winter analyst", "january 2027", "january -", "jan - apr", "hiver 2027", "hiver"]
    is_winter = any(term in text for term in winter_terms)
    
    # Check if purely summer-only (e.g. Summer 2027 only without 8-month or winter option)
    summer_only = ("summer 2027" in text or "summer 2026" in text or "may - aug" in text) and not is_winter and "8 month" not in text and "12 month" not in text

    # Disqualifiers
    senior_patterns = [
        r"\b(senior|sr\.|lead|principal|architect|director|vp|manager)\b",
        r"\b(5\+|7\+|8\+|10\+)\s*years\b",
    ]
    is_senior = any(re.search(p, text) for p in senior_patterns) and "co-op" not in text and "intern" not in text

    unrelated = any(
        kw in text
        for kw in [
            "registered nurse",
            "licensed practical nurse",
            "forklift operator",
            "truck driver",
            "accountant",
            "dental",
            "plumber",
            "electrician",
        ]
    )

    if unrelated or (is_senior and "student" not in text):
        return ("low", is_winter)

    if winter_focus and summer_only:
        return ("low", False)

    # High match criteria
    high_keywords = [
        "system administrator",
        "systems administrator",
        "linux administrator",
        "systems technician",
        "network administrator",
        "network technician",
        "network operations",
        "noc technician",
        "noc analyst",
        "noc operator",
        "noc",
        "cloud operations",
        "cloud infrastructure",
        "it infrastructure",
        "active directory",
        "cisco",
        "zero-trust",
        "virtualization",
        "vmware",
        "cybersecurity",
        "it security",
        "security operations",
        "soc analyst",
        "security analyst",
        "data center technician",
        "service desk",
    ]
    coop_match = any(term in text for term in ["co-op", "coop", "intern", "student"])

    has_high_kw = any(kw in text for kw in high_keywords)
    if is_winter and (has_high_kw or coop_match):
        return ("high", True)
    if has_high_kw and coop_match:
        return ("high", is_winter)
    if has_high_kw:
        return ("high" if not winter_focus or is_winter else "medium", is_winter)

    # Medium match criteria
    medium_keywords = [
        "it support",
        "help desk",
        "technical support",
        "desktop support",
        "it technician",
        "hardware technician",
        "systems analyst",
        "operations technician",
        "cloud support",
        "network support",
        "it coordinator",
    ]
    if any(kw in text for kw in medium_keywords):
        return ("high" if is_winter else "medium", is_winter)

    if is_winter:
        return ("medium", True)

    return ("low", False)


def build_referral_links(company: str, role_title: str) -> Dict[str, str]:
    safe_company = company.replace("&", " ").strip()
    words = [w for w in role_title.split() if w.lower() not in ("junior", "senior", "the", "a", "at", "in", "co-op", "intern", "-", "/")]
    role_kw = " ".join(words[:2]) if words else "Engineering"

    recruiter_q = f'"{safe_company}" recruiter'
    peer_q = f'"{safe_company}" {role_kw}'

    return {
        "recruiter_search": f"https://www.linkedin.com/search/results/people/?keywords={urllib.parse.quote(recruiter_q)}&origin=GLOBAL_SEARCH_HEADER",
        "peer_search": f"https://www.linkedin.com/search/results/people/?keywords={urllib.parse.quote(peer_q)}&origin=GLOBAL_SEARCH_HEADER",
    }


def run_indeed_workflow(
    query_override: Optional[str] = None,
    location: str = "Toronto, ON",
    jobage: int = 14,
    limit: int = 10,
    broad: bool = False,
    dry_run: bool = False,
    output_format: str = "table",
    hours_old: Optional[int] = None,
) -> None:
    logger.info("Starting dedicated Indeed scrape workflow")
    seen_state = load_seen_jobs()
    seen_dict = seen_state.get("seen", {})
    tracker_exclusions, tracker_urls = load_tracker_exclusions()

    # Pre-index seen sets for robust deduplication
    seen_urls: Set[str] = set(seen_dict.keys())
    seen_comp_roles: Set[Tuple[str, str]] = set()
    for k, v in seen_dict.items():
        if isinstance(v, dict):
            if v.get("url"):
                seen_urls.add(v["url"])
            if v.get("id"):
                seen_urls.add(v["id"])
            c = (v.get("company") or "").strip().lower()
            t = (v.get("title") or "").strip().lower()
            if c and t:
                seen_comp_roles.add((c, t))

    # Determine query list
    if query_override:
        queries = [(query_override, location)]
    elif broad:
        queries = [
            ("IT Co-op", "Toronto, ON"),
            ("Junior System Administrator", "Toronto, ON"),
            ("Linux Co-op", "Toronto, ON"),
            ("Network Administrator Co-op", "Toronto, ON"),
            ("IT Support Technician", "York Region, ON"),
            ("Cloud Infrastructure Intern", "Toronto, ON"),
            ("Systems Analyst Student", "Ontario"),
        ]
    else:
        queries = [
            ("IT Co-op", "Toronto, ON"),
            ("Junior System Administrator", "Toronto, ON"),
            ("Linux Co-op", "Toronto, ON"),
            ("IT Support Technician", "York Region, ON"),
        ]

    logger.info("Executing %d search query categories against Indeed Canada...", len(queries))

    target_hours_old = hours_old if hours_old is not None else (jobage * 24)
    discovered_jobs: List[Dict[str, Any]] = []
    skipped_count = 0

    for q_term, q_loc in queries:
        logger.info("Searching Indeed for: '%s' in '%s'", q_term, q_loc)
        is_remote_query = "remote" in q_loc.lower()
        search_res = perform_search(
            query=q_term,
            location=q_loc,
            country="canada",
            results_wanted=limit,
            hours_old=target_hours_old,
            is_remote=is_remote_query,
        )

        results = search_res.get("results", [])
        for item in results:
            url = item.get("url") or ""
            comp = (item.get("company") or "").strip()
            title = (item.get("title") or "").strip()
            job_id = item.get("id") or url

            if not comp or not title:
                continue

            # Deduplication
            is_seen = (
                url in seen_urls
                or job_id in seen_urls
                or (comp.lower(), title.lower()) in seen_comp_roles
            )
            is_tracked = (
                (comp.lower(), title.lower()) in tracker_exclusions
                or (url and url in tracker_urls)
            )

            if is_seen or is_tracked:
                skipped_count += 1
                continue

            # Check duplicates within current run pool
            if any(j["url"] == url or j["id"] == job_id for j in discovered_jobs):
                continue

            discovered_jobs.append(item)

    logger.info("Found %d new candidates (%d skipped as previously seen/applied)", len(discovered_jobs), skipped_count)

    # Process and fetch details for new candidates
    evaluated_jobs: List[Dict[str, Any]] = []
    for job in discovered_jobs:
        job_id = job.get("id") or job.get("url")
        logger.info("Fetching full details for: %s (%s)", job.get("title"), job.get("company"))
        detail = perform_detail(job_id, country="canada")
        
        desc = detail.get("description") or job.get("description_snippet") or ""
        fit, is_winter = evaluate_fit(job.get("title", ""), desc, winter_focus=True)
        apply_url = detail.get("apply_url") or job.get("url")
        date_str = detail.get("date") or job.get("date") or datetime.now(timezone.utc).strftime("%Y-%m-%d")

        job_record = {
            "id": job_id,
            "title": job.get("title"),
            "company": job.get("company"),
            "location": job.get("location"),
            "date": date_str,
            "url": job.get("url"),
            "apply_url": apply_url,
            "fit": fit,
            "is_winter": is_winter,
            "description": desc,
            "referrals": build_referral_links(job.get("company", ""), job.get("title", "")) if fit in ("high", "medium") else {},
        }
        evaluated_jobs.append(job_record)

        # Update seen dict
        seen_dict[job.get("url")] = {
            "title": job.get("title"),
            "company": job.get("company"),
            "location": job.get("location"),
            "description": desc,
            "url": job.get("url"),
            "first_seen": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "deadline": None,
            "fit": fit,
            "is_winter": is_winter,
            "status": "new",
            "portal": "indeed-search",
            "source": "cli",
        }

    if not dry_run and evaluated_jobs:
        seen_state["seen"] = seen_dict
        save_seen_jobs(seen_state)
        logger.info("Persisted %d new jobs to %s", len(evaluated_jobs), SEEN_JOBS_FILE)

    # Output Presentation
    if output_format == "json":
        print(json.dumps({"count": len(evaluated_jobs), "jobs": evaluated_jobs}, indent=2))
        return evaluated_jobs

    # Table output
    if not evaluated_jobs:
        print("\nNo new Indeed postings found. (All matching postings are already in seen_jobs or tracker).")
        return []

    print("\n" + "=" * 94)
    print(f" DEDICATED INDEED SCRAPE RESULTS: {len(evaluated_jobs)} New Posting(s)")
    print("=" * 94)
    print(f"{'FIT':<12} {'ROLE':<32} {'COMPANY':<22} {'LOCATION':<16} {'POSTED':<10}")
    print("-" * 94)
    for j in sorted(evaluated_jobs, key=lambda x: (not x.get("is_winter", False), ("high", "medium", "low").index(x["fit"]))):
        term_tag = "[WINTER]" if j.get("is_winter") else ""
        fit_badge = f"{j['fit'].upper()} {term_tag}".strip()
        role = (j["title"][:29] + "...") if len(j["title"]) > 32 else j["title"]
        comp = (j["company"][:19] + "...") if len(j["company"]) > 22 else j["company"]
        loc = (j["location"][:13] + "...") if len(j["location"]) > 16 else j["location"]
        print(f"{fit_badge:<12} {role:<32} {comp:<22} {loc:<16} {j['date']:<10}")
        print(f"  --> URL: {j['url']}")
        if j.get("referrals"):
            print(f"  --> Recruiter Outreach: {j['referrals']['recruiter_search']}")
            print(f"  --> Peer Outreach:      {j['referrals']['peer_search']}")
        print("")

    print("=" * 94)
    winter_count = sum(1 for j in evaluated_jobs if j.get("is_winter"))
    print(f"Summary: {len(evaluated_jobs)} new postings ({winter_count} explicit Winter Co-ops). {skipped_count} skipped duplicates.")
    if dry_run:
        print("[DRY RUN] No changes were written to seen_jobs.json.")
    else:
        print("To apply to any posting, run: /apply <URL>")
        if winter_count > 0:
            rebuild_script = REPO_ROOT / "scripts" / "rebuild_tracker_and_dashboard_winter_only.py"
            if rebuild_script.exists():
                try:
                    logger.info("Triggering tracker & dashboard rebuild and GitHub Pages deploy...")
                    subprocess.run([sys.executable, str(rebuild_script)], check=True)
                except Exception as e:
                    logger.error("Error rebuilding dashboard: %s", e)

    return evaluated_jobs


def main():
    parser = argparse.ArgumentParser(description="Dedicated Indeed Job Scraper Workflow")
    parser.add_argument("-q", "--query", help="Specific search query (e.g. 'Linux', 'Systems Administrator')")
    parser.add_argument("-l", "--location", default="Toronto, ON", help="City or region (default: 'Toronto, ON')")
    parser.add_argument("--jobage", type=int, default=14, help="Max posting age in days (default: 14)")
    parser.add_argument("--hours-old", type=int, default=None, help="Max posting age in hours (overrides --jobage)")
    parser.add_argument("-n", "--limit", type=int, default=10, help="Results limit per query (default: 10)")
    parser.add_argument("--broad", action="store_true", help="Run broad query matrix across IT, Network, and Cloud")
    parser.add_argument("--dry-run", action="store_true", help="Run without persisting new jobs to seen_jobs.json")
    parser.add_argument("--winter", action="store_true", default=True, help="Prioritize Winter Co-op postings (default: True)")
    parser.add_argument("--format", choices=["table", "json"], default="table", help="Output format (default: table)")
    args = parser.parse_args()

    run_indeed_workflow(
        query_override=args.query,
        location=args.location,
        jobage=args.jobage,
        limit=args.limit,
        broad=args.broad,
        dry_run=args.dry_run,
        output_format=args.format,
        hours_old=args.hours_old,
    )


if __name__ == "__main__":
    main()
