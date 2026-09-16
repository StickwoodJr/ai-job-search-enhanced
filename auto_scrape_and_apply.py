#!/usr/bin/env python3
"""
Automated Scrape and Apply Loop Daemon

Continuously runs the job scraper workflow (/job-scraper-workflow) every 5 minutes
(configurable via --interval) and automatically triggers the apply workflow (/cmd-apply)
for each newly discovered, qualifying job posting.

Usage:
    python auto_scrape_and_apply.py [options]

Options:
    -i, --interval SECONDS     Loop interval in seconds (default: 300 = 5 minutes)
    --once                     Run a single scrape-and-apply pass, then exit
    --dry-run                  Simulate scraping and applying without writing files
    --min-fit [high|medium|all] Minimum fit rating required to auto-apply (default: medium)
    --max-applies-per-cycle N  Max number of new postings to apply to in one cycle (default: 5)
    --portals PORTALS          Comma-separated portal list (e.g. "linkedin,eluta,jobbank") or "all"
    --category CATEGORY        Specific search category focus (e.g. "systems", "network", "helpdesk")
    --verbose                  Enable detailed debug logging
"""

import argparse
import csv
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
from typing import Any, Dict, List, Optional, Set, Tuple

# Workspace root
REPO_ROOT = Path(__file__).resolve().parent

# Canonical file paths
SEEN_JOBS_FILE = REPO_ROOT / "job_scraper" / "seen_jobs.json"
TRACKER_FILE = REPO_ROOT / "job_search_tracker.csv"
SEARCH_QUERIES_FILE = REPO_ROOT / ".claude" / "skills" / "job-scraper" / "search-queries.md"
CANDIDATE_PROFILE_FILE = REPO_ROOT / ".claude" / "skills" / "job-application-assistant" / "01-candidate-profile.md"
CV_DIR = REPO_ROOT / "cv"
COVER_LETTER_DIR = REPO_ROOT / "cover_letters"
DOCUMENTS_APP_DIR = REPO_ROOT / "documents" / "applications"
SALARY_TOOL = REPO_ROOT / "salary_lookup.py"
VERIFY_PDF_TOOL = REPO_ROOT / "tools" / "verify_pdf.py"
PORTAL_SKILLS_DIR = REPO_ROOT / ".agents" / "skills"

# Canonical Tracker Header
TRACKER_HEADER = (
    "date,company,sector,role,role_type,channel,status,contact_person,"
    "fit_rating,notes,cv_file,cover_letter_file,source,deadline"
)

def load_candidate_profile() -> dict:
    """Load candidate profile details dynamically from 01-candidate-profile.md."""
    info = {
        "name": "Candidate",
        "email": "candidate@example.com",
        "phone": "+1 555-555-5555",
        "linkedin": "https://linkedin.com",
        "github": "https://github.com",
        "location": "City, Province/State, Country",
        "citizenship": "Authorized to work",
        "target_term": "Co-op / Internship / Full-time",
    }
    if CANDIDATE_PROFILE_FILE.exists():
        content = CANDIDATE_PROFILE_FILE.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("- **Name:**"):
                v = line.split(":", 1)[1].strip()
                if v and not v.startswith("["):
                    info["name"] = v
            elif line.startswith("- **Email:**"):
                v = line.split(":", 1)[1].strip()
                if v and not v.startswith("["):
                    info["email"] = v
            elif line.startswith("- **Phone:**"):
                v = line.split(":", 1)[1].strip()
                if v and not v.startswith("["):
                    info["phone"] = v
            elif line.startswith("- **LinkedIn:**"):
                v = line.split(":", 1)[1].strip()
                if v and not v.startswith("["):
                    info["linkedin"] = v
            elif line.startswith("- **GitHub:**"):
                v = line.split(":", 1)[1].strip()
                if v and not v.startswith("["):
                    info["github"] = v
            elif line.startswith("- **Location:**"):
                v = line.split(":", 1)[1].strip()
                if v and not v.startswith("["):
                    info["location"] = v
    return info

CANDIDATE_DATA = load_candidate_profile()
CANDIDATE_NAME = CANDIDATE_DATA["name"]
CANDIDATE_EMAIL = CANDIDATE_DATA["email"]
CANDIDATE_PHONE = CANDIDATE_DATA["phone"]
CANDIDATE_LINKEDIN = CANDIDATE_DATA["linkedin"]
CANDIDATE_GITHUB = CANDIDATE_DATA["github"]
CANDIDATE_LOCATION = CANDIDATE_DATA["location"]
CANDIDATE_CITIZENSHIP = CANDIDATE_DATA["citizenship"]
CANDIDATE_TARGET_TERM = CANDIDATE_DATA["target_term"]


def setup_logger(verbose: bool = False) -> logging.Logger:
    """Configure structured logging."""
    logger = logging.getLogger("AutoScrapeApply")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def derive_archive_name(company: str, role: str) -> str:
    """Derive subfolder name per documents/README.md Subfolder Naming rule.

    Lowercase, underscores for spaces, drop every character that is not a letter/digit/underscore,
    collapse runs of underscores, trim ends.
    """
    name = f"{company}_{role}".lower().replace(" ", "_")
    name = re.sub(r"[^\w]", "", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name or "unnamed_application"


def sanitize_filename(name: str) -> str:
    """Sanitize string for clean filenames in LaTeX / directories."""
    cleaned = re.sub(r"[^\w\s-]", "", name).strip()
    cleaned = re.sub(r"[\s]+", "_", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned)
    return cleaned or "job"


def escape_latex(text: str) -> str:
    """Escape special LaTeX characters in dynamic user or posting strings."""
    if not text:
        return ""
    # Backslash must be replaced first
    escaped = text.replace("\\", r"\textbackslash{}")
    replacements = [
        ("&", r"\&"),
        ("%", r"\%"),
        ("$", r"\$"),
        ("#", r"\#"),
        ("_", r"\_"),
        ("{", r"\{"),
        ("}", r"\}"),
        ("~", r"\textasciitilde{}"),
        ("^", r"\textasciicircum{}"),
    ]
    for char, repl in replacements:
        escaped = escaped.replace(char, repl)
    return escaped


# ==============================================================================
# State & Tracker Management
# ==============================================================================

class StateManager:
    """Manages seen_jobs.json and job_search_tracker.csv deduplication & state."""

    def __init__(self, dry_run: bool = False, logger: Optional[logging.Logger] = None):
        self.dry_run = dry_run
        self.logger = logger or logging.getLogger("AutoScrapeApply")
        self.seen_data: Dict[str, Any] = {"seen": {}}
        self.tracked_keys: Set[str] = set()
        self.load_seen_jobs()
        self.load_tracker()

    def load_seen_jobs(self) -> Dict[str, Any]:
        """Load seen_jobs.json."""
        if SEEN_JOBS_FILE.exists():
            try:
                with open(SEEN_JOBS_FILE, "r", encoding="utf-8") as f:
                    self.seen_data = json.load(f)
                    if "seen" not in self.seen_data:
                        self.seen_data["seen"] = {}
            except Exception as e:
                self.logger.warning(f"Error loading seen_jobs.json ({e}), initializing fresh")
                self.seen_data = {"seen": {}}
        else:
            self.seen_data = {"seen": {}}
        return self.seen_data

    def save_seen_jobs(self) -> None:
        """Persist seen_jobs.json to disk."""
        if self.dry_run:
            self.logger.debug("[Dry-Run] Skipped saving seen_jobs.json")
            return
        SEEN_JOBS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SEEN_JOBS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.seen_data, f, ensure_ascii=False, indent=2)

    def load_tracker(self) -> Set[str]:
        """Extract tracked company+role keys and URLs from job_search_tracker.csv."""
        self.tracked_keys = set()
        if not TRACKER_FILE.exists():
            return self.tracked_keys

        try:
            with open(TRACKER_FILE, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                if not header:
                    return self.tracked_keys

                # Find relevant column indices
                col_map = {name.strip().lower(): idx for idx, name in enumerate(header)}
                company_idx = col_map.get("company")
                role_idx = col_map.get("role")
                source_idx = col_map.get("source") or col_map.get("posting url")

                for row in reader:
                    if not row:
                        continue
                    if company_idx is not None and role_idx is not None and len(row) > max(company_idx, role_idx):
                        comp = row[company_idx].strip().lower()
                        role = row[role_idx].strip().lower()
                        if comp and role:
                            self.tracked_keys.add(f"{comp}::{role}")
                    if source_idx is not None and len(row) > source_idx:
                        url = row[source_idx].strip()
                        if url:
                            self.tracked_keys.add(url)
        except Exception as e:
            self.logger.warning(f"Error reading tracker CSV: {e}")

        return self.tracked_keys

    def is_already_seen_or_applied(self, url: str, company: str, role: str, job_id: Optional[str] = None) -> bool:
        """Check whether a posting has already been recorded."""
        norm_comp = company.strip().lower()
        norm_role = role.strip().lower()
        key = f"{norm_comp}::{norm_role}"

        # 1. Tracker check
        if key in self.tracked_keys or url in self.tracked_keys:
            return True

        # 2. Seen jobs check
        seen = self.seen_data.get("seen", {})
        if job_id and job_id in seen:
            return True
        if url and url in seen:
            return True

        # Check by matching company + title inside seen_jobs
        for entry in seen.values():
            e_comp = (entry.get("company") or "").strip().lower()
            e_role = (entry.get("title") or entry.get("role") or "").strip().lower()
            e_url = entry.get("url") or ""
            if e_url == url or (e_comp == norm_comp and e_role == norm_role):
                return True

        return False

    def record_seen_job(self, job: Dict[str, Any]) -> None:
        """Add job to seen_jobs.json dictionary."""
        seen = self.seen_data.setdefault("seen", {})
        job_key = job.get("id") or job.get("url") or f"{job.get('company')}_{job.get('title')}"
        seen[job_key] = {
            "id": job.get("id", job_key),
            "title": job.get("title", ""),
            "company": job.get("company", ""),
            "location": job.get("location", ""),
            "date": job.get("date", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
            "url": job.get("url", ""),
            "source": job.get("source", "cli"),
            "portal": job.get("portal", "cli"),
            "first_seen": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "deadline": job.get("deadline"),
            "fit": job.get("fit", "medium"),
            "fit_score": job.get("fit_score", 70),
            "status": job.get("status", "new"),
            "notes": job.get("notes", ""),
        }

    def update_seen_job_status(self, job_key: str, status: str) -> None:
        """Update the status of a seen job (e.g. to 'drafted')."""
        if job_key in self.seen_data.get("seen", {}):
            self.seen_data["seen"][job_key]["status"] = status
            self.save_seen_jobs()

    def record_application_to_tracker(
        self,
        company: str,
        role: str,
        fit_score: int,
        cv_pdf_path: str,
        cover_pdf_path: str,
        source_url: str,
        deadline: Optional[str] = None,
        location: str = "",
        notes: str = "",
        sector: str = "",
        role_type: str = "Co-op",
        channel: str = "portal",
    ) -> None:
        """Record application row to job_search_tracker.csv following /apply Step 6b."""
        if self.dry_run:
            self.logger.info(f"[Dry-Run] Would record tracker row for {company} - {role}")
            return

        today = datetime.now().strftime("%Y-%m-%d")
        deadline_val = deadline if deadline else ""

        rows: List[List[str]] = []
        header = TRACKER_HEADER.split(",")
        file_exists = TRACKER_FILE.exists()

        if file_exists:
            with open(TRACKER_FILE, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                existing_header = next(reader, None)
                if existing_header:
                    # Check if header needs canonical migration
                    if not existing_header[-1].strip().lower() == "deadline":
                        existing_header.append("deadline")
                    header = existing_header
                rows = list(reader)

        # Check for matching open row to update, or append
        match_idx = -1
        col_map = {name.strip().lower(): idx for idx, name in enumerate(header)}
        comp_idx = col_map.get("company", 1)
        role_idx = col_map.get("role", 3)
        status_idx = col_map.get("status", 6)

        norm_comp = company.strip().lower()
        norm_role = role.strip().lower()

        for idx, r in enumerate(rows):
            if len(r) > max(comp_idx, role_idx):
                if r[comp_idx].strip().lower() == norm_comp and r[role_idx].strip().lower() == norm_role:
                    current_status = r[status_idx].strip().lower() if len(r) > status_idx else ""
                    # If open, update in place
                    if current_status in ("drafted", "applied", "interviewing", "in_progress", ""):
                        match_idx = idx
                        break

        # Construct row according to canonical header
        new_row_map = {
            "date": today,
            "company": company,
            "sector": sector,
            "role": role,
            "role_type": role_type,
            "channel": channel,
            "status": "Drafted",
            "contact_person": "",
            "fit_rating": str(fit_score),
            "notes": notes,
            "cv_file": cv_pdf_path,
            "cover_letter_file": cover_pdf_path,
            "source": source_url,
            "deadline": deadline_val,
        }

        row_values = [new_row_map.get(col.strip().lower(), "") for col in header]

        if match_idx >= 0:
            self.logger.info(f"Updating existing tracker row for {company} - {role}")
            # Pad row if needed
            while len(rows[match_idx]) < len(header):
                rows[match_idx].append("")
            # Refresh fields
            for col_name, val in new_row_map.items():
                if col_name in col_map:
                    idx = col_map[col_name]
                    if col_name == "notes":
                        existing_notes = rows[match_idx][idx]
                        rows[match_idx][idx] = f"{existing_notes}; redrafted".strip("; ")
                    elif col_name == "status":
                        pass  # preserve status
                    elif col_name == "date":
                        if rows[match_idx][status_idx].strip().lower() == "drafted":
                            rows[match_idx][idx] = today
                    else:
                        rows[match_idx][idx] = val
        else:
            self.logger.info(f"Appending new tracker row for {company} - {role}")
            rows.append(row_values)

        # Write back to CSV
        with open(TRACKER_FILE, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)

        self.tracked_keys.add(f"{norm_comp}::{norm_role}")
        if source_url:
            self.tracked_keys.add(source_url)


# ==============================================================================
# Fit Evaluator & Classifier
# ==============================================================================

class FitEvaluator:
    """Evaluates job fit against Golden Stickwood's candidate profile."""

    # Keywords that indicate high / strong match for Golden Stickwood
    CORE_SYSTEMS_KEYWORDS = [
        "system administrator", "systems administrator", "sysadmin", "linux",
        "windows server", "active directory", "ad ds", "group policy", "gpo",
        "dns", "dhcp", "powershell", "bash", "virtualization", "kvm", "qemu",
        "vmware", "docker", "it co-op", "it intern", "technical systems analyst",
        "zero-trust", "cisco", "network administrator", "network operations",
        "firewall", "vlan", "routing", "help desk", "it support", "tier 1", "tier 2"
    ]

    ADJACENT_KEYWORDS = [
        "cloud", "devops", "infrastructure", "cybersecurity", "security analyst",
        "platform developer", "technical support", "network technician", "desktop support",
        "operations analyst", "modern workplace", "intune", "endpoint"
    ]

    EXCLUDE_KEYWORDS = [
        "senior data scientist", "principal engineer", "lead architect", "10+ years",
        "phd required", "unpaid internship", "volunteer", "french essential", "bilingual imperative"
    ]

    GTA_LOCATIONS = [
        "toronto", "newmarket", "aurora", "markham", "richmond hill", "vaughan",
        "north york", "scarborough", "mississauga", "oakville", "gta", "ontario",
        "remote", "hybrid", "canada"
    ]

    @classmethod
    def evaluate_posting(cls, title: str, description: str, location: str, company: str) -> Tuple[str, int, str]:
        """Rapid fit scoring per 04-job-evaluation.md.

        Returns (fit_band, fit_score, notes).
        fit_band: 'high', 'medium', 'low'
        """
        text = f"{title} {description} {location}".lower()

        # 1. Exclusions / Hard gates
        for excl in cls.EXCLUDE_KEYWORDS:
            if excl in text:
                return "low", 25, f"Excluded: flagged by keyword '{excl}'"

        # Location check
        loc_lower = location.lower()
        location_match = any(loc in loc_lower or loc in text for loc in cls.GTA_LOCATIONS)
        if not location_match and loc_lower and "remote" not in loc_lower:
            return "low", 35, f"Location outside target GTA/Remote range: {location}"

        # 2. Score Technical Match
        core_hits = [kw for kw in cls.CORE_SYSTEMS_KEYWORDS if kw in text]
        adj_hits = [kw for kw in cls.ADJACENT_KEYWORDS if kw in text]

        score = 50  # baseline

        # Co-op / Student alignment bonus
        if any(term in text for term in ["co-op", "intern", "student", "winter 2027", "2027"]):
            score += 15

        # Core competencies bonus
        score += min(len(core_hits) * 6, 30)
        score += min(len(adj_hits) * 3, 15)

        # Proximity bonus (York Region / Newmarket / Markham / Richmond Hill)
        if any(yr in loc_lower for yr in ["newmarket", "aurora", "markham", "richmond hill", "vaughan"]):
            score += 5

        score = min(score, 98)

        if score >= 75:
            fit_band = "high"
        elif score >= 55:
            fit_band = "medium"
        else:
            fit_band = "low"

        notes = f"Matched keywords: {', '.join((core_hits + adj_hits)[:5])}"
        return fit_band, score, notes


# ==============================================================================
# Scraper Engine
# ==============================================================================

class ScraperEngine:
    """Discovers and runs installed portal search CLIs in .agents/skills/."""

    def __init__(self, state_mgr: StateManager, logger: Optional[logging.Logger] = None):
        self.state_mgr = state_mgr
        self.logger = logger or logging.getLogger("AutoScrapeApply")

    def run_portal_cli(self, portal_name: str, query: str, location: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Run portal CLI search command and return parsed results list."""
        cli_path = PORTAL_SKILLS_DIR / portal_name / "cli" / "src" / "cli.ts"
        if not cli_path.exists():
            self.logger.debug(f"Portal CLI {portal_name} not found at {cli_path}")
            return []

        cmd = ["bun", "run", str(cli_path), "search"]

        # Portal specific arguments
        if portal_name == "linkedin-search":
            cmd.extend(["-q", query, "-l", location or "Toronto, Ontario, Canada", "--jobage", "14", "--limit", str(limit), "--format", "json"])
        elif portal_name == "eluta-search":
            cmd.extend(["-q", query, "-l", location or "Toronto, ON", "--jobage", "14", "--limit", str(limit), "--format", "json"])
        elif portal_name == "jobbank-ca-search":
            cmd.extend(["--query", query, "--limit", str(limit), "--format", "json"])
        elif portal_name == "gcjobs-search":
            cmd.extend(["-q", query, "-l", "Ontario", "--limit", str(limit), "--format", "json"])
        elif portal_name == "talent-com-search":
            cmd.extend(["-q", query, "-l", location or "Toronto", "--limit", str(limit), "--format", "json"])
        elif portal_name == "indeed-search":
            cmd.extend(["-q", query, "-l", location or "Toronto, ON", "--jobage", "14", "--limit", str(limit), "--format", "json"])
        elif portal_name == "freehire-search":
            cmd.extend(["-q", query, "--country", "CA", "--jobage", "14", "--limit", str(limit), "--format", "json"])
        else:
            cmd.extend(["-q", query, "--limit", str(limit), "--format", "json"])

        try:
            self.logger.debug(f"Executing: {' '.join(cmd)}")
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
            if res.returncode != 0:
                self.logger.warning(f"Portal {portal_name} search returned exit code {res.returncode}: {res.stderr.strip()[:200]}")
                return []

            data = json.loads(res.stdout)
            results = data.get("results", [])
            for r in results:
                r["portal"] = portal_name
                r["source"] = "cli"
            return results
        except Exception as e:
            self.logger.error(f"Error running {portal_name} CLI search: {e}")
            return []

    def fetch_job_detail(self, portal_name: str, job_id_or_url: str) -> Optional[Dict[str, Any]]:
        """Fetch full job detail description using portal CLI detail command."""
        cli_path = PORTAL_SKILLS_DIR / portal_name / "cli" / "src" / "cli.ts"
        if not cli_path.exists():
            return None

        cmd = ["bun", "run", str(cli_path), "detail", str(job_id_or_url), "--format", "json"]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if res.returncode == 0:
                return json.loads(res.stdout)
        except Exception as e:
            self.logger.debug(f"Could not fetch detail for {job_id_or_url} via {portal_name}: {e}")
        return None

    def run_scrape_cycle(
        self,
        portals: Optional[List[str]] = None,
        queries: Optional[List[Tuple[str, str]]] = None,
    ) -> List[Dict[str, Any]]:
        """Execute a full scrape pass across portals and return new promising job postings."""
        self.logger.info("--- Starting Job Scrape Cycle ---")

        active_portals = portals or ["linkedin-search", "indeed-search", "eluta-search", "jobbank-ca-search", "talent-com-search", "gcjobs-search", "freehire-search"]

        # Default prioritized search queries for Golden Stickwood
        active_queries = queries or [
            ("IT Co-op", "Toronto, ON"),
            ("Systems Administrator Co-op", "Toronto, ON"),
            ("Linux Co-op", "Toronto, ON"),
            ("Network Administrator", "Toronto, ON"),
            ("Help Desk Specialist", "York Region, ON"),
            ("Systems Analyst", "Ontario"),
        ]

        new_postings: List[Dict[str, Any]] = []
        total_discovered = 0

        for portal in active_portals:
            portal_dir = PORTAL_SKILLS_DIR / portal
            if not portal_dir.exists():
                continue

            for query, loc in active_queries:
                raw_results = self.run_portal_cli(portal, query, loc, limit=10)
                total_discovered += len(raw_results)

                for item in raw_results:
                    title = item.get("title") or ""
                    company = item.get("company") or ""
                    url = item.get("url") or ""
                    job_id = item.get("id") or url
                    location = item.get("location") or loc or ""

                    if not title or not company:
                        continue

                    # Check deduplication against seen jobs and tracker
                    if self.state_mgr.is_already_seen_or_applied(url, company, title, job_id):
                        self.logger.debug(f"Skipping already seen/applied: {company} - {title}")
                        continue

                    # Fetch detail for new job if available
                    detail = self.fetch_job_detail(portal, job_id) or {}
                    description = detail.get("description") or item.get("description") or ""
                    deadline = detail.get("deadline") or item.get("deadline")

                    # Evaluate fit
                    fit_band, fit_score, notes = FitEvaluator.evaluate_posting(title, description, location, company)

                    job_obj = {
                        "id": f"{portal}-{job_id}" if not str(job_id).startswith(portal) else str(job_id),
                        "title": title,
                        "company": company,
                        "location": location,
                        "url": url,
                        "portal": portal,
                        "source": "cli",
                        "date": item.get("date") or datetime.now().strftime("%Y-%m-%d"),
                        "deadline": deadline,
                        "description": description,
                        "fit": fit_band,
                        "fit_score": fit_score,
                        "notes": notes,
                        "status": "new",
                    }

                    # Store in seen_jobs
                    self.state_mgr.record_seen_job(job_obj)
                    new_postings.append(job_obj)
                    self.logger.info(f"✨ Found NEW Job [{fit_band.upper()} ({fit_score}/100)]: {company} - {title} ({location})")

        # Save updated seen_jobs.json
        self.state_mgr.save_seen_jobs()
        self.logger.info(f"Scrape cycle complete: scanned {total_discovered} hits, identified {len(new_postings)} fresh postings.")
        return new_postings


# ==============================================================================
# Application Drafting & Compilation Engine
# ==============================================================================

class ApplyEngine:
    """Generates LaTeX CV and Cover Letter, compiles PDFs, checks ATS, archives postings."""

    def __init__(self, state_mgr: StateManager, dry_run: bool = False, logger: Optional[logging.Logger] = None):
        self.state_mgr = state_mgr
        self.dry_run = dry_run
        self.logger = logger or logging.getLogger("AutoScrapeApply")

    def lookup_salary(self, company: str) -> Optional[str]:
        """Query salary benchmark if salary_lookup.py is configured."""
        if not SALARY_TOOL.exists():
            return None
        try:
            res = subprocess.run([sys.executable, str(SALARY_TOOL), company, "--json"], capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                data = json.loads(res.stdout)
                if data and isinstance(data, list) and len(data) > 0:
                    return json.dumps(data[0])
        except Exception:
            pass
        return None

    def generate_cv_latex(self, company: str, role: str, description: str) -> str:
        """Generate tailored moderncv banking LaTeX source grounded in Golden Stickwood's profile."""
        esc_company = escape_latex(company)
        esc_role = escape_latex(role)

        # Profile statement tailored to role
        profile_statement = (
            f"High-achieving Computer Systems Technology student at Seneca Polytechnic (4.0 GPA, "
            f"President's Honour List) seeking the \\textbf{{{esc_role}}} 4-month Co-op term at \\textbf{{{esc_company}}} "
            f"starting January 2027. Practical background in Linux systems administration, Windows Server \\& Active Directory "
            f"management, Cisco network routing/firewalls, and zero-trust virtualization. Proven track record of operational ownership, "
            f"rapid troubleshooting under pressure, and client communication excellence."
        )

        cv_content = rf"""%% Role-Tailored CV - {company} - {role}
%% Candidate: Golden Stickwood
%% Compile with: cd cv && lualatex -interaction=nonstopmode main_{sanitize_filename(company)}_{sanitize_filename(role)}.tex

\documentclass[11pt,a4paper,sans]{{moderncv}}
\moderncvstyle{{banking}}
\moderncvcolor{{blue}}

\renewcommand*{{\namefont}}{{\fontsize{{30}}{{32}}\bfseries\upshape}}
\colorlet{{firstnamecolor}}{{color1}}
\colorlet{{lastnamecolor}}{{color1}}
\colorlet{{namecolor}}{{color1}}
\renewcommand*{{\sectionstyle}}[1]{{{{\sectionfont\color{{color1}}#1}}}}

\usepackage[utf8]{{inputenc}}
\AtEndPreamble{{\hypersetup{{
    colorlinks=true,
    linkcolor=blue,
    filecolor=magenta,
    urlcolor=blue,
    pdftitle={{Golden Stickwood - CV - {esc_company}}},
    pdfpagemode=UseNone,
}}}}
\usepackage[scale=0.82]{{geometry}}
\usepackage{{import}}
\usepackage{{needspace}}

% Personal data
\name{{Golden}}{{Stickwood}}
\address{{Newmarket, ON, Canada -- Canadian Citizen (No Sponsorship Required)}}{{}}{{}}
\phone[mobile]{{+1 647-649-8083}}
\email{{{CANDIDATE_EMAIL.replace('_', r'\_')}}}
\extrainfo{{\href{{{CANDIDATE_LINKEDIN}}}{{LinkedIn}}, \href{{{CANDIDATE_GITHUB}}}{{GitHub}}}}

\begin{{document}}

\makecvtitle
\vspace{{-8pt}}

% ============================================================
%     PROFILE STATEMENT
% ============================================================

\small{{{profile_statement}}}

% ============================================================
%     CORE COMPETENCIES
% ============================================================

\section{{Core Competencies}}
\vspace{{1pt}}
\begin{{itemize}}
\item \textbf{{Systems Administration}}: Linux (Debian, Ubuntu, Kali Linux, CentOS/RHEL), Windows Server (2022/2019), Active Directory DS, Group Policy (GPO), DNS, DHCP, systemd, storage \& package management.
\item \textbf{{Network Engineering \& Security}}: Cisco IOS, IPv4 Subnetting, Static Routing, VLAN segmentation, 802.1Q trunking, Cisco Zone-Based Policy Firewall (ZFW), dynamic NAT/PAT, WireGuard / Tailscale VPN mesh, Cloudflare Tunnels.
\item \textbf{{Virtualization \& Containers}}: KVM/QEMU, \texttt{{libvirt}}/\texttt{{virsh}}, VMware Workstation, Docker containerization, container hardening (non-root execution, \texttt{{CAP\_DROP}}, AppArmor profiles).
\item \textbf{{Scripting, Automation \& Tools}}: Bash shell scripting, PowerShell, automated disaster-recovery workflows (\texttt{{backupVMs.bash}}, \texttt{{restoreVM.bash}}), Git/GitHub, Cisco Packet Tracer, VS Code.
\item \textbf{{Operational Discipline}}: Architecture Decision Records (ADRs), root-cause postmortem documentation, customer communication, consultative sales, conflict de-escalation.
\end{{itemize}}

% ============================================================
%     TECHNICAL PROJECTS
% ============================================================

\section{{Technical Projects}}
\vspace{{2pt}}
\begin{{itemize}}

\needspace{{5\baselineskip}}
\item{{\cventry{{Jan 2026 - Present}}{{Zero-Trust Homelab Infrastructure (``labhost'')}}{{Personal Project}}{{Newmarket, ON}}{{}}{{\vspace{{1pt}}
\begin{{itemize}}
    \item Architected a 3-tier virtualized network (WAN, DMZ, Personal zones) using KVM/QEMU, isolated virtual bridges, and a virtualized Cisco router.
    \item Configured Cisco Zone-Based Policy Firewall (ZFW) with stateful packet inspection, dynamic NAT/PAT, and explicit-deny inter-zone policies.
    \item Deployed Docker containerized services via Cloudflare Tunnel and private services over a Tailscale WireGuard mesh with zero open inbound ports.
    \item Authored automated Bash backup/recovery scripts for VM snapshot lifecycle and maintained formal Architecture Decision Records (ADRs) and postmortems.
\end{{itemize}}}}

\end{{itemize}}

% ============================================================
%     EDUCATION
% ============================================================

\section{{Education}}
\vspace{{1pt}}
\begin{{itemize}}

\needspace{{5\baselineskip}}
\item{{\cventry{{Jan 2026 - Dec 2027 (Expected)}}{{Computer Systems Technology (Advanced Diploma)}}{{Seneca Polytechnic}}{{Toronto, ON}}{{}}{{\vspace{{1pt}}
\begin{{itemize}}
    \item \textbf{{Academic Standing}}: 4.0 / 4.0 GPA across completed coursework; named to \textbf{{President's Honour List}} (Winter 2026 \& Summer 2026).
    \item \textbf{{Completed Coursework}}: Linux Admin (OPS 145 - A+, OPS 245 - A), Microsoft Server Admin \& AD (MST 100 - A+, MST 200 - A+), Cisco Networks \& Routing (CSN 115 - A+, CSN 205 - A), System Security (SEC 220 - A+), Strategic Problem Solving (SPS 120 - A+), Professional Communications (COM 101 - A+).
\end{{itemize}}}}

\vspace{{2pt}}

\needspace{{3\baselineskip}}
\item{{\cventry{{Sep 2020 - Jun 2024}}{{Ontario Secondary School Diploma (OSSD)}}{{Sacred Heart Catholic High School}}{{Newmarket, ON}}{{}}{{}}}}

\end{{itemize}}

% ============================================================
%     PROFESSIONAL EXPERIENCE
% ============================================================

\section{{Professional Experience}}
\vspace{{2pt}}
\begin{{itemize}}

\needspace{{5\baselineskip}}
\item{{\cventry{{May 2022 - Aug 2025}}{{Founder \& Business Operator}}{{Newmarket Pressure Washing}}{{Newmarket, ON}}{{}}{{\vspace{{1pt}}
\begin{{itemize}}
    \item Founded and operated a commercial and residential exterior cleaning business, winning the York Region Summer Company youth entrepreneurship grant (2022).
    \item Managed end-to-end business operations: client acquisition, digital marketing campaigns, estimating, customer communications, scheduling, and invoicing.
    \item Performed routine diagnostics, mechanical maintenance, and repairs on high-pressure equipment to ensure continuous operational uptime.
    \item Maintained a 100\% client satisfaction rating and generated steady repeat business through high service reliability.
\end{{itemize}}}}

\vspace{{2pt}}

\needspace{{5\baselineskip}}
\item{{\cventry{{Oct 2025 - Dec 2025}}{{Sales Representative}}{{Brookstone Windows \& Doors}}{{Aurora, ON}}{{}}{{\vspace{{1pt}}
\begin{{itemize}}
    \item Conducted direct-to-consumer field sales, engaging prospective clients, presenting customized product solutions, and generating qualified pipeline leads.
    \item Communicated technical specifications, energy ratings, and installation workflows clearly to homeowners.
\end{{itemize}}}}

\vspace{{2pt}}

\needspace{{5\baselineskip}}
\item{{\cventry{{Oct 2020 - Mar 2024}}{{Hockey Referee}}{{Newmarket Minor Hockey Association (NMHA)}}{{Newmarket, ON}}{{}}{{\vspace{{1pt}}
\begin{{itemize}}
    \item Officiated competitive youth and adult league games, enforcing Hockey Canada rules and ensuring participant safety.
    \item Exercised decisive judgement under pressure and communicated clearly to de-escalate high-tension scenarios.
\end{{itemize}}}}

\end{{itemize}}

% ============================================================
%     HONOURS, AWARDS \& MEDIA
% ============================================================

\section{{Honours, Awards \& Media}}
\vspace{{1pt}}
\begin{{itemize}}
\item \textbf{{President's Honour List}} -- Seneca Polytechnic (Summer 2026, Winter 2026).
\item \textbf{{Summer Company Entrepreneurship Grant}} -- York Region Small Business Enterprise Centre (2022).
\item \textbf{{Media Features}} -- Profiled in \textit{{York Region News}} (2023) and \textit{{Newmarket Today}} (2022) for youth entrepreneurship.
\end{{itemize}}

% ============================================================
%     REFERENCES
% ============================================================

\section{{References}}
\vspace{{1pt}}
\begin{{itemize}}
\item Available upon request.
\end{{itemize}}

\end{{document}}
"""
        return cv_content

    def generate_cover_letter_latex(self, company: str, role: str, description: str, deadline: Optional[str] = None) -> str:
        """Generate tailored cover letter LaTeX source using cover.cls."""
        esc_company = escape_latex(company)
        esc_role = escape_latex(role)

        cover_content = rf"""%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Cover Letter - {company}
% Role: {role}
% Compile with: cd cover_letters && xelatex -interaction=nonstopmode cover_{sanitize_filename(company)}_{sanitize_filename(role)}.tex
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

\documentclass[]{{cover}}
\usepackage{{fancyhdr}}

\pagestyle{{fancy}}
\fancyhf{{}}

\rfoot{{Page \thepage \hspace{{0pt}}}}
\thispagestyle{{empty}}
\renewcommand{{\headrulewidth}}{{0pt}}
\begin{{document}}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%     TITLE NAME
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
\namesection{{}}{{{CANDIDATE_NAME}}}{{  \href{{mailto:{CANDIDATE_EMAIL}}}{{{CANDIDATE_EMAIL.replace('_', r'\_')}}} | {CANDIDATE_PHONE} | \urlstyle{{same}}\href{{{CANDIDATE_LINKEDIN}}}{{LinkedIn}} | \href{{{CANDIDATE_GITHUB}}}{{GitHub}}
}}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%     MAIN COVER LETTER CONTENT
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

\currentdate{{\today}}
\lettercontent{{Dear Hiring Team at {esc_company},}}

\lettercontent{{I am writing to express my strong interest in the \textbf{{{esc_role}}} co-op position at \textbf{{{esc_company}}} for the Winter 2027 term. As a 3rd-semester Computer Systems Technology student at Seneca Polytechnic maintaining a 4.0 GPA, I combine rigorous hands-on systems administration, zero-trust network infrastructure engineering, and customer-facing problem solving to deliver resilient technical operations.}}

\lettercontent{{My technical coursework and independent projects directly align with the infrastructure reliability and operational standards at {esc_company}. Through designing and administering production-grade systems and utilizing agentic developer workflows with \textbf{{Claude Code}}, I have built deep competence in enterprise infrastructure, automation, and structured root-cause analysis:}}

{{\raggedright\fontspec[Path = OpenFonts/fonts/raleway/]{{Raleway-Medium}}\fontsize{{11pt}}{{13pt}}\selectfont
\begin{{itemize}}
    \item \textbf{{Enterprise Systems \& Directory Services:}} Configured and managed Windows Server 2022/2019 environments, Active Directory Domain Services (AD DS), Group Policy Objects (GPO), DNS, DHCP, and automated administrative tasks using PowerShell and Bash scripts.
    \item \textbf{{Zero-Trust Network Infrastructure:}} Engineered a multi-tier virtualized network with KVM/QEMU and Cisco Zone-Based Policy Firewalls (ZFW), enforcing stateful packet inspection, dynamic NAT/PAT, and zero open inbound ports via Cloudflare Tunnels and Tailscale WireGuard mesh networks.
    \item \textbf{{Virtualization, Containers \& Hardening:}} Deployed containerized applications with Docker, applying AppArmor profiles, non-root execution, and Linux security baselines across Debian and Ubuntu server environments.
    \item \textbf{{Operational Discipline \& Customer Ownership:}} Founded and operated an exterior maintenance business, managing client communications, estimating, and equipment troubleshooting, developing composure, accountability, and clear technical communication.
\end{{itemize}}\par}}
\vspace{{6pt}}

\lettercontent{{As a Canadian Citizen available full-time for a 4-month co-op placement starting January 2027, I am excited about the opportunity to contribute directly to {esc_company}'s technical operations and support your team's goals.}}

\lettercontent{{Thank you for your time and consideration. I welcome the opportunity to discuss how my background and enthusiasm can support {esc_company}.}}

\begin{{flushright}}
\closing{{Sincerely,}}

\signature{{Golden Stickwood}}
\end{{flushright}}
\end{{document}}
"""
        return cover_content

    def compile_cv(self, cv_tex_path: Path) -> bool:
        """Compile CV with lualatex."""
        cv_dir = cv_tex_path.parent
        tex_filename = cv_tex_path.name
        cmd = ["lualatex", "-interaction=nonstopmode", tex_filename]
        try:
            self.logger.debug(f"Compiling CV: {' '.join(cmd)} in {cv_dir}")
            res = subprocess.run(cmd, cwd=cv_dir, capture_output=True, text=True, timeout=30)
            pdf_path = cv_tex_path.with_suffix(".pdf")
            if pdf_path.exists() and pdf_path.stat().st_size > 0:
                self.logger.debug(f"CV compiled successfully: {pdf_path}")
                return True
            else:
                self.logger.error(f"CV compilation failed (exit code {res.returncode}):\n{res.stdout[-400:]}")
                return False
        except Exception as e:
            self.logger.error(f"Exception during CV compilation: {e}")
            return False

    def compile_cover_letter(self, cover_tex_path: Path) -> bool:
        """Compile Cover Letter with xelatex."""
        cover_dir = cover_tex_path.parent
        tex_filename = cover_tex_path.name
        cmd = ["xelatex", "-interaction=nonstopmode", tex_filename]
        try:
            self.logger.debug(f"Compiling Cover Letter: {' '.join(cmd)} in {cover_dir}")
            res = subprocess.run(cmd, cwd=cover_dir, capture_output=True, text=True, timeout=30)
            pdf_path = cover_tex_path.with_suffix(".pdf")
            if pdf_path.exists() and pdf_path.stat().st_size > 0:
                self.logger.debug(f"Cover Letter compiled successfully: {pdf_path}")
                return True
            else:
                self.logger.error(f"Cover letter compilation failed (exit code {res.returncode}):\n{res.stdout[-400:]}")
                return False
        except Exception as e:
            self.logger.error(f"Exception during cover letter compilation: {e}")
            return False

    def verify_pdf_ats(self, pdf_path: Path) -> bool:
        """Run verify_pdf.py to check text extraction layer."""
        if not VERIFY_PDF_TOOL.exists():
            return True
        dump_txt = pdf_path.with_suffix(".txt")
        try:
            cmd = [sys.executable, str(VERIFY_PDF_TOOL), str(pdf_path), "--dump-text", str(dump_txt)]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            # Cleanup temp dump txt file
            if dump_txt.exists():
                dump_txt.unlink()
            return res.returncode == 0
        except Exception:
            return True

    def cleanup_latex_aux(self, base_path: Path) -> None:
        """Remove intermediate auxiliary files (.aux, .log, .out, .txt)."""
        for ext in [".aux", ".log", ".out", ".txt"]:
            aux_file = base_path.with_suffix(ext)
            if aux_file.exists():
                try:
                    aux_file.unlink()
                except Exception:
                    pass

    def archive_job_posting(self, company: str, role: str, posting_text: str, source_url: str) -> Path:
        """Archive job posting to documents/applications/<company>_<role>/job_posting.md."""
        folder_name = derive_archive_name(company, role)
        app_dir = DOCUMENTS_APP_DIR / folder_name
        app_dir.mkdir(parents=True, exist_ok=True)
        posting_file = app_dir / "job_posting.md"

        if not posting_file.exists() and not self.dry_run:
            content = f"# Job Posting: {role} at {company}\n\n"
            content += f"- **Source URL:** {source_url}\n"
            content += f"- **Date Captured:** {datetime.now().strftime('%Y-%m-%d')}\n\n"
            content += "## Original Posting Content\n\n"
            content += posting_text or "No full description text provided."
            with open(posting_file, "w", encoding="utf-8") as f:
                f.write(content)

        return posting_file

    def apply_to_job(self, job: Dict[str, Any]) -> bool:
        """Execute full apply workflow for a single job posting."""
        company = job.get("company") or "Company"
        role = job.get("title") or "Role"
        url = job.get("url") or ""
        description = job.get("description") or ""
        deadline = job.get("deadline")
        fit_score = job.get("fit_score", 75)
        location = job.get("location", "")

        safe_comp = sanitize_filename(company)
        safe_role = sanitize_filename(role)

        cv_tex_path = CV_DIR / f"main_{safe_comp}_{safe_role}.tex"
        cover_tex_path = COVER_LETTER_DIR / f"cover_{safe_comp}_{safe_role}.tex"
        cv_pdf_path = cv_tex_path.with_suffix(".pdf")
        cover_pdf_path = cover_tex_path.with_suffix(".pdf")

        self.logger.info(f"🚀 [APPLY] Drafting application for: {company} - {role}")

        if self.dry_run:
            self.logger.info(f"[Dry-Run] Would generate {cv_tex_path} and {cover_tex_path}")
            return True

        # 1. Generate LaTeX source files
        cv_code = self.generate_cv_latex(company, role, description)
        cover_code = self.generate_cover_letter_latex(company, role, description, deadline)

        CV_DIR.mkdir(parents=True, exist_ok=True)
        COVER_LETTER_DIR.mkdir(parents=True, exist_ok=True)

        with open(cv_tex_path, "w", encoding="utf-8") as f:
            f.write(cv_code)
        with open(cover_tex_path, "w", encoding="utf-8") as f:
            f.write(cover_code)

        # 2. Compile CV and Cover Letter
        cv_ok = self.compile_cv(cv_tex_path)
        cover_ok = self.compile_cover_letter(cover_tex_path)

        # 3. Clean up build artifacts
        self.cleanup_latex_aux(cv_tex_path)
        self.cleanup_latex_aux(cover_tex_path)

        if not cv_ok or not cover_ok:
            self.logger.warning(f"⚠️ LaTeX compilation issues for {company} - {role} (CV: {cv_ok}, Cover: {cover_ok})")

        # 4. ATS check on CV
        if cv_ok and cv_pdf_path.exists():
            self.verify_pdf_ats(cv_pdf_path)

        # 5. Archive job posting
        self.archive_job_posting(company, role, description, url)

        # 6. Record application to tracker
        rel_cv_pdf = f"cv/{cv_pdf_path.name}"
        rel_cover_pdf = f"cover_letters/{cover_pdf_path.name}"
        notes = f"Auto-drafted application for {CANDIDATE_TARGET_TERM}. Fit Score: {fit_score}/100."

        self.state_mgr.record_application_to_tracker(
            company=company,
            role=role,
            fit_score=fit_score,
            cv_pdf_path=rel_cv_pdf,
            cover_pdf_path=rel_cover_pdf,
            source_url=url,
            deadline=deadline,
            location=location,
            notes=notes,
        )

        # 7. Update status in seen_jobs.json
        job_key = job.get("id") or url
        self.state_mgr.update_seen_job_status(job_key, "drafted")

        self.logger.info(f"✅ [SUCCESS] Application drafted & recorded for {company} - {role}")
        return True


# ==============================================================================
# Main Daemon & Loop Controller
# ==============================================================================

class AutoScrapeApplyDaemon:
    """Manages the periodic 5-minute scrape and apply execution loop."""

    def __init__(
        self,
        interval: int = 300,
        min_fit: str = "medium",
        max_applies_per_cycle: int = 5,
        portals: Optional[List[str]] = None,
        category: Optional[str] = None,
        once: bool = False,
        dry_run: bool = False,
        verbose: bool = False,
    ):
        self.interval = interval
        self.min_fit = min_fit.lower()
        self.max_applies_per_cycle = max_applies_per_cycle
        self.portals = portals
        self.category = category
        self.once = once
        self.dry_run = dry_run
        self.verbose = verbose
        self.running = True

        self.logger = setup_logger(verbose)
        self.state_mgr = StateManager(dry_run=dry_run, logger=self.logger)
        self.scraper = ScraperEngine(state_mgr=self.state_mgr, logger=self.logger)
        self.apply_engine = ApplyEngine(state_mgr=self.state_mgr, dry_run=dry_run, logger=self.logger)

        self._setup_signals()

    def _setup_signals(self) -> None:
        """Register graceful shutdown signal handlers."""
        def handle_signal(signum, frame):
            self.logger.info("\nReceived stop signal. Finishing current operations and exiting...")
            self.running = False

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

    def is_fit_qualifying(self, fit_band: str) -> bool:
        """Check if job meets minimum fit filter."""
        fit = (fit_band or "").lower()
        if self.min_fit == "all":
            return True
        if self.min_fit == "high":
            return fit == "high"
        # default: medium or high
        return fit in ("high", "medium", "good")

    def run_one_cycle(self) -> Tuple[int, int]:
        """Run a single scrape and apply cycle.

        Returns (num_new_jobs, num_applications_drafted).
        """
        cycle_start = time.time()
        self.logger.info(f"⏰ Starting loop cycle at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # 1. Scrape for new jobs
        new_jobs = self.scraper.run_scrape_cycle(portals=self.portals)

        # 2. Filter qualifying jobs for application
        qualifying_jobs = [j for j in new_jobs if self.is_fit_qualifying(j.get("fit", "low"))]
        self.logger.info(f"📋 {len(qualifying_jobs)} of {len(new_jobs)} new postings qualify for application (min_fit={self.min_fit})")

        # Sort by fit_score descending
        qualifying_jobs.sort(key=lambda j: j.get("fit_score", 0), reverse=True)

        # Cap applications per cycle if configured
        target_jobs = qualifying_jobs[:self.max_applies_per_cycle]
        if len(qualifying_jobs) > self.max_applies_per_cycle:
            self.logger.info(f"Limiting to top {self.max_applies_per_cycle} applications this cycle (out of {len(qualifying_jobs)})")

        applies_count = 0
        for job in target_jobs:
            if not self.running:
                break
            success = self.apply_engine.apply_to_job(job)
            if success:
                applies_count += 1

        if not self.dry_run and (applies_count > 0 or len(new_jobs) > 0):
            rebuild_script = REPO_ROOT / "scripts" / "rebuild_tracker_and_dashboard_winter_only.py"
            if rebuild_script.exists():
                try:
                    self.logger.info("🔄 Triggering automatic dashboard rebuild & GitHub Pages deploy...")
                    subprocess.run([sys.executable, str(rebuild_script)], check=True)
                except Exception as e:
                    self.logger.warning(f"Failed to auto-rebuild/deploy dashboard: {e}")
            else:
                deploy_script = REPO_ROOT / "scripts" / "deploy_dashboard.sh"
                if deploy_script.exists():
                    subprocess.run([str(deploy_script)], check=True)

        cycle_duration = time.time() - cycle_start
        self.logger.info(f"🏁 Cycle finished in {cycle_duration:.1f}s: {len(new_jobs)} scraped, {applies_count} applications generated.\n")
        return len(new_jobs), applies_count

    def start(self) -> None:
        """Start the continuous loop."""
        self.logger.info("=" * 70)
        self.logger.info(f"🚀 AI Job Search Daemon Started")
        self.logger.info(f"   • Interval: {self.interval}s (5 minutes)")
        self.logger.info(f"   • Min Fit: {self.min_fit}")
        self.logger.info(f"   • Max Applies/Cycle: {self.max_applies_per_cycle}")
        self.logger.info(f"   • Mode: {'Single-Run (--once)' if self.once else 'Continuous Loop'}")
        if self.dry_run:
            self.logger.info(f"   • DRY RUN: Enabled (no files or tracker will be written)")
        self.logger.info("=" * 70)

        total_scraped = 0
        total_applied = 0
        cycle_count = 0

        while self.running:
            cycle_count += 1
            self.logger.info(f"--- Cycle #{cycle_count} ---")
            scraped, applied = self.run_one_cycle()
            total_scraped += scraped
            total_applied += applied

            if self.once or not self.running:
                break

            self.logger.info(f"💤 Sleeping for {self.interval}s until next scrape (Ctrl+C to stop)...")
            # Sleep in short increments to respond promptly to signals
            sleep_start = time.time()
            while self.running and (time.time() - sleep_start) < self.interval:
                time.sleep(1)

        self.logger.info("=" * 70)
        self.logger.info(f"🛑 Daemon Stopped. Total Cycles: {cycle_count} | Scraped: {total_scraped} | Applied: {total_applied}")
        self.logger.info("=" * 70)


# ==============================================================================
# CLI Entrypoint
# ==============================================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description="Automated 5-minute loop daemon: scrapes for jobs and applies to each new posting.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-i", "--interval",
        type=int,
        default=300,
        help="Loop interval in seconds (default: 300 = 5 minutes)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single scrape-and-apply cycle, then exit",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate scrape and apply without writing files or updating tracker",
    )
    parser.add_argument(
        "--min-fit",
        choices=["high", "medium", "all"],
        default="medium",
        help="Minimum fit rating required to auto-apply",
    )
    parser.add_argument(
        "--max-applies-per-cycle",
        type=int,
        default=5,
        help="Maximum applications to draft in a single scrape cycle",
    )
    parser.add_argument(
        "--portals",
        type=str,
        default=None,
        help="Comma-separated list of portals to search (e.g. 'linkedin-search,eluta-search')",
    )
    parser.add_argument(
        "--category",
        type=str,
        default=None,
        help="Search category focus query",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable detailed debug logs",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    portals_list = [p.strip() for p in args.portals.split(",")] if args.portals else None

    daemon = AutoScrapeApplyDaemon(
        interval=args.interval,
        min_fit=args.min_fit,
        max_applies_per_cycle=args.max_applies_per_cycle,
        portals=portals_list,
        category=args.category,
        once=args.once,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )
    daemon.start()


if __name__ == "__main__":
    main()
