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


PROFILE_FILE = REPO_ROOT / ".claude" / "skills" / "job-application-assistant" / "01-candidate-profile.md"
SWARM_CONFIG_FILE = REPO_ROOT / "config" / "swarm_sectors.json"

def get_candidate_keywords() -> Tuple[List[str], List[str]]:
    """Extract candidate target roles and technical skills from profile/config."""
    roles = []
    skills = []
    if SWARM_CONFIG_FILE.exists():
        try:
            with open(SWARM_CONFIG_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
                for sec in d.get("sectors", {}).values():
                    if "name" in sec:
                        roles.append(sec["name"].lower())
                    for q in sec.get("queries", []):
                        q_text = q[0] if isinstance(q, (list, tuple)) else str(q)
                        roles.append(q_text.lower())
        except Exception:
            pass
    if PROFILE_FILE.exists():
        try:
            content = PROFILE_FILE.read_text(encoding="utf-8")
            for line in content.splitlines():
                if "Target Job Roles" in line or "**Roles:**" in line:
                    parts = re.split(r'[,;]', line)
                    roles.extend([p.strip().lower() for p in parts if p.strip() and "[" not in p])
                elif line.startswith("- **") and ":**" in line:
                    m = re.match(r"^-\s+\*\*([^*]+)\*\*:\s*(.*)", line)
                    if m and "[" not in m.group(2):
                        skills.append(m.group(1).lower())
        except Exception:
            pass
    return list(set(roles)), list(set(skills))


def evaluate_fit(title: str, description: str, winter_focus: bool = True) -> Tuple[str, bool]:
    """
    Candidate-focused triage fit rating:
    - Evaluates role title and description against candidate target roles and skills
    - Flags entry-level / co-op / internship term alignment
    - Filters unrelated physical trades or senior executive mismatch
    Returns: (fit_level, is_target_term)
    """
    text = f"{title} {description}".lower()

    # Target term identification (co-op, intern, student, or specific winter/summer terms)
    term_keywords = [
        "co-op", "coop", "intern", "internship", "student", "entry level",
        "junior", "new grad", "associate", "stage", "hiver", "winter"
    ]
    is_target_term = any(term in text for term in term_keywords)

    # Disqualifiers
    senior_patterns = [
        r"\b(senior|sr\.|lead|principal|architect|director|vp|vice president)\b",
        r"\b(7\+|8\+|10\+)\s*years\b",
    ]
    is_senior = any(re.search(p, text) for p in senior_patterns) and not is_target_term

    unrelated_trades = [
        "registered nurse",
        "licensed practical nurse",
        "forklift operator",
        "truck driver",
        "dental assistant",
        "dental hygienist",
        "plumber",
        "electrician",
        "hvac technician",
    ]
    if any(kw in text for kw in unrelated_trades) or is_senior:
        return ("low", is_target_term)

    # Candidate profile match
    cand_roles, cand_skills = get_candidate_keywords()
    title_lower = title.lower()

    if cand_roles or cand_skills:
        role_hits = [r for r in cand_roles if r in title_lower or r in text]
        skill_hits = [s for s in cand_skills if s in text]
        if role_hits and (is_target_term or skill_hits):
            return ("high", is_target_term)
        if role_hits or len(skill_hits) >= 2:
            return ("medium", is_target_term)

    # Default technical keywords for fresh installs / unconfigured profiles
    default_high_kw = [
        "software engineer", "developer", "system administrator", "systems administrator",
        "linux", "network administrator", "devops", "cloud engineer", "cybersecurity",
        "soc analyst", "data analyst", "data engineer", "it support", "service desk",
        "active directory", "cisco", "docker", "kubernetes"
    ]
    default_med_kw = [
        "technical support", "help desk", "hardware technician", "systems analyst",
        "operations technician", "network support", "it coordinator", "qa analyst"
    ]

    has_high = any(kw in text for kw in default_high_kw)
    has_med = any(kw in text for kw in default_med_kw)

    if has_high and is_target_term:
        return ("high", True)
    if has_high or (has_med and is_target_term):
        return ("medium", is_target_term)
    if has_med or is_target_term:
        return ("medium", is_target_term)

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
    else:
        loaded_queries = []
        if SWARM_CONFIG_FILE.exists():
            try:
                with open(SWARM_CONFIG_FILE, "r", encoding="utf-8") as f:
                    s_data = json.load(f)
                    default_loc = s_data.get("home_location", location)
                    for sec in s_data.get("sectors", {}).values():
                        for q in sec.get("queries", []):
                            if isinstance(q, (list, tuple)) and len(q) >= 2:
                                loaded_queries.append((str(q[0]), str(q[1])))
                            elif isinstance(q, str):
                                loaded_queries.append((q, default_loc))
            except Exception:
                pass
        if loaded_queries:
            queries = loaded_queries if broad else loaded_queries[:4]
        elif broad:
            queries = [
                ("Software Engineer", location),
                ("Junior System Administrator", location),
                ("Data Analyst", location),
                ("DevOps Engineer", location),
                ("IT Support Specialist", location),
            ]
        else:
            queries = [
                ("Software Engineer", location),
                ("Junior System Administrator", location),
                ("IT Support", location),
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
        term_tag = "[TARGET]" if j.get("is_winter") else ""
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
    target_count = sum(1 for j in evaluated_jobs if j.get("is_winter"))
    print(f"Summary: {len(evaluated_jobs)} new postings ({target_count} target matches). {skipped_count} skipped duplicates.")
    if dry_run:
        print("[DRY RUN] No changes were written to seen_jobs.json.")
    else:
        print("To apply to any posting, run: /apply <URL>")
        if target_count > 0:
            rebuild_script = REPO_ROOT / "scripts" / "rebuild_dashboard.py"
            if rebuild_script.exists():
                try:
                    logger.info("Triggering tracker & dashboard rebuild...")
                    subprocess.run([sys.executable, str(rebuild_script)], check=True)
                except Exception as e:
                    logger.error("Error rebuilding dashboard: %s", e)

    return evaluated_jobs


def main():
    parser = argparse.ArgumentParser(description="Dedicated Indeed Job Scraper Workflow")
    parser.add_argument("-q", "--query", help="Specific search query (e.g. 'Software Engineer', 'Systems Administrator')")
    parser.add_argument("-l", "--location", default="Toronto, ON", help="City or region (default: 'Toronto, ON')")
    parser.add_argument("--jobage", type=int, default=14, help="Max posting age in days (default: 14)")
    parser.add_argument("--hours-old", type=int, default=None, help="Max posting age in hours (overrides --jobage)")
    parser.add_argument("-n", "--limit", type=int, default=10, help="Results limit per query (default: 10)")
    parser.add_argument("--broad", action="store_true", help="Run broad query matrix across all configured sectors")
    parser.add_argument("--dry-run", action="store_true", help="Run without persisting new jobs to seen_jobs.json")
    parser.add_argument("--winter", "--target-term", dest="winter", action="store_true", default=True, help="Prioritize target term postings (default: True)")
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
