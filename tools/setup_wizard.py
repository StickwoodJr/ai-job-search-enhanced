#!/usr/bin/env python3
"""
AI Job Search - Beginner Onboarding & Environment Setup Wizard

Designed for zero-experience beginners and autonomous AI coding agents.
Verifies system dependencies, installs search portal tools, configures the
candidate profile, customizes Indeed Swarm Scraper sectors, configures
Google NotebookLM Curriculum RAG, and smoke-tests LaTeX PDF compilation.

Usage:
    python tools/setup_wizard.py                    # Full interactive guided setup
    python tools/setup_wizard.py --doctor           # Check environment dependencies only
    python tools/setup_wizard.py --install          # Install all portal search CLIs (Bun/npm)
    python tools/setup_wizard.py --configure-swarm  # Configure Indeed Swarm sectors only
    python tools/setup_wizard.py --configure-rag    # Configure NotebookLM RAG only
    python tools/setup_wizard.py --non-interactive  # Automated non-interactive validation
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / ".agents" / "skills"
PROFILE_FILE = REPO_ROOT / ".claude" / "skills" / "job-application-assistant" / "01-candidate-profile.md"
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"
CV_DIR = REPO_ROOT / "cv"
CONFIG_DIR = REPO_ROOT / "config"
SWARM_CONFIG_FILE = CONFIG_DIR / "swarm_sectors.json"
RAG_DIR = REPO_ROOT / "rag"
RAG_USER_CONFIG = RAG_DIR / "user_config.json"
DOCUMENTS_DIR = REPO_ROOT / "documents"


def print_banner():
    print("=" * 72)
    print("   🤖 AI Job Search Enhanced - Autonomous Setup & Onboarding Wizard")
    print("   The intelligent job search operating system on your local machine.")
    print("=" * 72)
    print()


def check_command(cmd: str) -> bool:
    """Check if a command-line tool is available in PATH."""
    return shutil.which(cmd) is not None


def run_doctor() -> dict:
    """Check prerequisites and report readiness."""
    print("🔍 Checking system environment...")
    results = {}

    # Python
    py_ver = sys.version_info
    py_ok = py_ver >= (3, 10)
    results["python"] = py_ok
    status_py = "✓" if py_ok else "✗"
    print(f"  [{status_py}] Python {py_ver.major}.{py_ver.minor}.{py_ver.micro} (Requires 3.10+)")

    # Bun / Node
    has_bun = check_command("bun")
    has_npm = check_command("npm")
    results["bun"] = has_bun
    results["npm"] = has_npm
    if has_bun:
        print("  [✓] Bun package manager detected")
    elif has_npm:
        print("  [✓] Node/npm package manager detected (Bun recommended for speed)")
    else:
        print("  [!] Neither Bun nor npm found. Job search CLIs require Bun (https://bun.sh)")

    # LaTeX Compilers
    has_pdflatex = check_command("pdflatex")
    has_xelatex = check_command("xelatex")
    has_lualatex = check_command("lualatex")
    results["pdflatex"] = has_pdflatex
    results["xelatex"] = has_xelatex
    results["lualatex"] = has_lualatex

    print(f"  [{'✓' if has_pdflatex else '!'}] pdflatex (Required for North American 1-Page Jake's Resume)")
    print(f"  [{'✓' if has_xelatex else '!'}] xelatex (Required for Cover Letters)")
    print(f"  [{'✓' if has_lualatex else '!'}] lualatex (Required for European 2-Page ModernCV)")

    if not (has_pdflatex or has_xelatex or has_lualatex):
        print("\n  💡 Tip: Install TeX Live, TinyTeX, or MiKTeX:")
        print("     - Debian/Ubuntu: sudo apt install texlive-latex-extra texlive-fonts-extra texlive-xetex")
        print("     - macOS: brew install --cask mactex-no-gui")
        print("     - Windows: choco install miktex")

    # Git & GitHub CLI
    has_git = check_command("git")
    has_gh = check_command("gh")
    results["git"] = has_git
    results["gh"] = has_gh
    print(f"  [{'✓' if has_git else '!'}] Git ({shutil.which('git') or 'missing'})")
    print(f"  [{'✓' if has_gh else '!'}] GitHub CLI ({shutil.which('gh') or 'optional, recommended'})")

    print()
    return results


def install_portal_tools() -> bool:
    """Install dependencies for all portal search skills in .agents/skills/*/cli/."""
    print("📦 Installing portal search tools across .agents/skills/...")
    pkg_dirs = list(SKILLS_DIR.glob("*/cli/package.json"))
    if not pkg_dirs:
        print("  No cli/package.json files found.")
        return True

    pkg_manager = "bun" if check_command("bun") else ("npm" if check_command("npm") else None)
    if not pkg_manager:
        print("  [✗] Cannot install portal tools: neither 'bun' nor 'npm' found in PATH.")
        return False

    success_count = 0
    for pkg in pkg_dirs:
        cli_dir = pkg.parent
        skill_name = cli_dir.parent.name
        print(f"  Installing dependencies for {skill_name} via {pkg_manager}...")
        try:
            cmd = [pkg_manager, "install"]
            res = subprocess.run(cmd, cwd=cli_dir, capture_output=True, text=True, timeout=120)
            if res.returncode == 0:
                print(f"    ✓ {skill_name} ready")
                success_count += 1
            else:
                print(f"    ✗ Failed installing {skill_name}: {res.stderr.strip()[:100]}")
        except Exception as e:
            print(f"    ✗ Error in {skill_name}: {e}")

    print(f"✓ Installed {success_count}/{len(pkg_dirs)} portal search tools.\n")
    return success_count == len(pkg_dirs)


def smoke_test_latex(template_choice: str = "jakes") -> bool:
    """Compile a starter template to ensure the LaTeX environment functions."""
    print(f"📄 Testing LaTeX compilation with {template_choice} template...")
    if template_choice == "jakes":
        tex_file = CV_DIR / "jakes_resume_template.tex"
        compiler = "pdflatex"
    else:
        tex_file = CV_DIR / "main_example.tex"
        compiler = "lualatex"

    if not tex_file.exists():
        print(f"  [✗] Template file not found: {tex_file}")
        return False

    if not check_command(compiler):
        print(f"  [!] Compiler '{compiler}' not found in PATH; skipping smoke test.")
        return False

    try:
        res = subprocess.run(
            [compiler, "-interaction=nonstopmode", tex_file.name],
            cwd=CV_DIR,
            capture_output=True,
            text=True,
            timeout=45
        )
        # Clean up build artifacts
        stem = tex_file.stem
        for ext in [".aux", ".log", ".out", ".pdf"]:
            f = CV_DIR / f"{stem}{ext}"
            if f.exists():
                f.unlink()

        if res.returncode == 0:
            print(f"  ✓ {compiler} compiled {tex_file.name} successfully!\n")
            return True
        else:
            print(f"  [!] Compilation warning/failure: {res.stderr.strip()[:200]}\n")
            return False
    except Exception as e:
        print(f"  [!] Compilation error: {e}\n")
        return False


def configure_candidate_profile(interactive: bool = True, data: dict = None) -> dict:
    """Configure personalized candidate information."""
    print("--- Step 3: Candidate Information & Profile ---")
    if interactive:
        print("Tip: You can press Enter to accept defaults or edit later.\n")
        name = input("Your Full Name: ").strip() or "[YOUR_NAME]"
        email = input("Your Email Address: ").strip() or "[YOUR_EMAIL]"
        phone = input("Your Phone Number: ").strip() or "[YOUR_PHONE]"
        location = input("Your Location (City, Province/State, Country): ").strip() or "[YOUR_ADDRESS]"
        linkedin = input("LinkedIn Profile URL (optional): ").strip() or "[YOUR_LINKEDIN_URL]"
        github = input("GitHub Profile URL (optional): ").strip() or "[YOUR_GITHUB_URL]"
        status = input("Work Authorization / Status (e.g. Citizen, PR, Student): ").strip() or "[YOUR_EMPLOYMENT_STATUS]"
        roles = input("Target Job Roles (e.g. Systems Admin, Help Desk, Co-op): ").strip() or "[YOUR_TARGET_ROLES]"
        skills = input("Primary Technical Skills (comma-separated): ").strip() or "[YOUR_PRIMARY_SKILLS]"
    else:
        d = data or {}
        name = d.get("name", "[YOUR_NAME]")
        email = d.get("email", "[YOUR_EMAIL]")
        phone = d.get("phone", "[YOUR_PHONE]")
        location = d.get("location", "[YOUR_ADDRESS]")
        linkedin = d.get("linkedin", "[YOUR_LINKEDIN_URL]")
        github = d.get("github", "[YOUR_GITHUB_URL]")
        status = d.get("status", "[YOUR_EMPLOYMENT_STATUS]")
        roles = d.get("roles", "[YOUR_TARGET_ROLES]")
        skills = d.get("skills", "[YOUR_PRIMARY_SKILLS]")

    # Populate 01-candidate-profile.md if values were provided
    if name != "[YOUR_NAME]" and PROFILE_FILE.exists():
        content = PROFILE_FILE.read_text(encoding="utf-8")
        content = content.replace("[YOUR_NAME]", name)
        if email != "[YOUR_EMAIL]":
            content = content.replace("[YOUR_EMAIL]", email)
        if phone != "[YOUR_PHONE]":
            content = content.replace("[YOUR_PHONE]", phone)
        if location != "[YOUR_ADDRESS]":
            content = content.replace("[YOUR_ADDRESS]", location)
        if linkedin != "[YOUR_LINKEDIN_URL]":
            content = content.replace("[YOUR_LINKEDIN_URL]", linkedin)
        if github != "[YOUR_GITHUB_URL]":
            content = content.replace("[YOUR_GITHUB_URL]", github)
        if status != "[YOUR_EMPLOYMENT_STATUS]":
            content = content.replace("[YOUR_EMPLOYMENT_STATUS]", status)
        PROFILE_FILE.write_text(content, encoding="utf-8")
        print(f"  ✓ Saved candidate profile to {PROFILE_FILE}")

    return {
        "name": name,
        "email": email,
        "phone": phone,
        "location": location,
        "roles": roles,
        "skills": skills
    }


def configure_swarm_sectors(interactive: bool = True, location: str = None, candidate_name: str = None):
    """Configure sectors, queries, and commute radius for Indeed Swarm Scraper."""
    print("\n--- Step 4: Indeed Multi-Sector Swarm Scraper Setup ---")
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    default_config = {
        "target_candidate": candidate_name or "[YOUR_NAME]",
        "home_location": location or "Toronto, ON",
        "max_distance_km": 50,
        "target_term": "Co-op / Internship / Entry-level / Full-time",
        "sectors": {
            "systems_hardware": {
                "name": "Systems & IT Support",
                "description": "Linux, Systems Administration, Windows Server, Active Directory, Service Desk, Desktop Support",
                "queries": [
                    ["Linux Administrator", location or "Toronto, ON"],
                    ["Systems Administrator", location or "Toronto, ON"],
                    ["Windows Server Active Directory", location or "Toronto, ON"],
                    ["IT Support Specialist", location or "Toronto, ON"],
                    ["Desktop Support", location or "Toronto, ON"],
                    ["Service Desk Technician", location or "Toronto, ON"],
                    ["Datacenter Operations", location or "Toronto, ON"]
                ]
            },
            "networking_noc": {
                "name": "Networking & NOC",
                "description": "Cisco Routing & Switching, Network Administration, NOC Operations, Network Security, Firewalls",
                "queries": [
                    ["Network Administrator", location or "Toronto, ON"],
                    ["Network Support Specialist", location or "Toronto, ON"],
                    ["Cisco Network Engineer", location or "Toronto, ON"],
                    ["NOC Analyst", location or "Toronto, ON"],
                    ["NOC Technician", location or "Toronto, ON"],
                    ["Telecom Technician", location or "Toronto, ON"],
                    ["Network Security Specialist", location or "Toronto, ON"]
                ]
            },
            "cloud_cyber": {
                "name": "Cloud & Cybersecurity",
                "description": "Cloud Infrastructure (AWS/Azure), DevOps, Docker, Cybersecurity, SOC Analyst, Information Security",
                "queries": [
                    ["Cloud Infrastructure Specialist", location or "Toronto, ON"],
                    ["Cloud Engineer", location or "Toronto, ON"],
                    ["DevOps Engineer", location or "Toronto, ON"],
                    ["Cybersecurity Analyst", location or "Toronto, ON"],
                    ["Information Security Specialist", location or "Toronto, ON"],
                    ["SOC Analyst", location or "Toronto, ON"]
                ]
            }
        }
    }

    if not interactive:
        with open(SWARM_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=2)
        print(f"  ✓ Initialized default swarm configuration at {SWARM_CONFIG_FILE}")
        return default_config

    loc_input = input(f"Target Job Search Location (Default: {location or 'Toronto, ON'}): ").strip()
    target_loc = loc_input or location or "Toronto, ON"

    dist_input = input("Max commute distance in km (Default: 50): ").strip()
    try:
        max_dist = int(dist_input) if dist_input else 50
    except ValueError:
        max_dist = 50

    print("\nDefault Swarm Sectors:")
    print("  1. Systems & IT Support (Linux, Sysadmin, Active Directory, IT Support)")
    print("  2. Networking & NOC (Cisco, Routing/Switching, NOC Analyst, Telecom)")
    print("  3. Cloud & Cybersecurity (AWS, Azure, DevOps, SOC Analyst, Cyber)")

    choice = input("\nKeep default tech sectors updated for your city? (Y/n / [C]ustom): ").strip().lower()

    if choice in ("c", "custom"):
        sectors = {}
        print("\nEnter custom sectors (1 to 4 sectors). Press Enter when done.")
        for idx in range(1, 5):
            s_name = input(f"Sector {idx} Name (or Enter to finish): ").strip()
            if not s_name:
                break
            s_key = re.sub(r'[^a-zA-Z0-9_]', '_', s_name.lower())
            queries_str = input(f"  Search queries for '{s_name}' (comma-separated): ").strip()
            q_list = [q.strip() for q in queries_str.split(",") if q.strip()]
            if not q_list:
                q_list = [s_name]
            sectors[s_key] = {
                "name": s_name,
                "description": f"Custom sector targeting {s_name}",
                "queries": [[q, target_loc] for q in q_list]
            }
        if sectors:
            default_config["sectors"] = sectors

    # Update locations in queries
    for sector in default_config["sectors"].values():
        for q in sector.get("queries", []):
            if len(q) > 1:
                q[1] = target_loc

    default_config["home_location"] = target_loc
    default_config["max_distance_km"] = max_dist
    if candidate_name and candidate_name != "[YOUR_NAME]":
        default_config["target_candidate"] = candidate_name

    with open(SWARM_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(default_config, f, indent=2)

    print(f"  ✓ Saved customized swarm sectors to {SWARM_CONFIG_FILE}\n")
    return default_config


def configure_rag_notebook(interactive: bool = True):
    """Guide user through Educational Curriculum RAG with Google NotebookLM."""
    print("--- Step 5: Educational Curriculum RAG Setup (NotebookLM) ---")
    print("Curriculum RAG grounds your CV bullets in verifiable lab reports, course syllabi,")
    print("and transcripts using Google NotebookLM with zero hallucination.\n")

    RAG_DIR.mkdir(parents=True, exist_ok=True)
    cfg = {
        "enabled": True,
        "default_notebook_id": "e32153b2-e906-4762-a8c3-8b96fbf093b4",
        "default_notebook_title": "Educational Coursework & Labs",
        "additional_notebooks": {}
    }

    if not interactive:
        if not RAG_USER_CONFIG.exists():
            with open(RAG_USER_CONFIG, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
            print(f"  ✓ Initialized default RAG config at {RAG_USER_CONFIG}")
        return cfg

    ans = input("Would you like to configure NotebookLM Curriculum RAG now? (Y/n): ").strip().lower()
    if ans in ("n", "no"):
        print("  Curriculum RAG setup skipped. You can configure it anytime with:")
        print("    python rag/notebook_manager.py\n")
        return cfg

    print("\nOptions for NotebookLM setup:")
    print("  [1] Enter an existing Google NotebookLM Notebook ID")
    print("  [2] Scan documents/ folder for syllabi & labs to create a new notebook")
    print("  [3] Discover notebooks via ExtendLM MCP")
    print("  [4] Skip for now")
    rag_choice = input("Enter choice [1, 2, 3, or 4] (Default: 1): ").strip()

    if rag_choice in ("", "1"):
        nb_id = input("Enter your NotebookLM Notebook ID (from URL notebooklm.google.com/notebook/<ID>): ").strip()
        if nb_id:
            title = input("Notebook Title (Default: 'Educational Coursework & Labs'): ").strip() or "Educational Coursework & Labs"
            cfg["default_notebook_id"] = nb_id
            cfg["default_notebook_title"] = title
            with open(RAG_USER_CONFIG, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
            print(f"  ✓ Active RAG notebook configured: '{title}' ({nb_id})\n")
    elif rag_choice == "2":
        try:
            sys.path.insert(0, str(RAG_DIR))
            import notebook_manager
            notebook_manager.cmd_scan_documents()
        except Exception as e:
            print(f"  [!] Scan error: {e}")
        nb_id = input("\nOnce created, enter your Notebook ID (or press Enter to configure later): ").strip()
        if nb_id:
            title = input("Notebook Title (Default: 'Degree Coursework & Labs'): ").strip() or "Degree Coursework & Labs"
            cfg["default_notebook_id"] = nb_id
            cfg["default_notebook_title"] = title
            with open(RAG_USER_CONFIG, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
            print(f"  ✓ Active RAG notebook configured: '{title}' ({nb_id})\n")
    elif rag_choice == "3":
        try:
            sys.path.insert(0, str(RAG_DIR))
            import notebook_manager
            notebook_manager.cmd_list()
        except Exception as e:
            print(f"  [!] ExtendLM discovery note: {e}")
        nb_id = input("\nEnter chosen Notebook ID (or press Enter to skip): ").strip()
        if nb_id:
            title = input("Notebook Title: ").strip() or "Educational Coursework & Labs"
            cfg["default_notebook_id"] = nb_id
            cfg["default_notebook_title"] = title
            with open(RAG_USER_CONFIG, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
            print(f"  ✓ Active RAG notebook configured: '{title}' ({nb_id})\n")

    return cfg


def run_interactive_setup():
    """Guided onboarding questionnaire for beginners."""
    print_banner()
    run_doctor()

    print("--- Step 1: Portal Tools Setup ---")
    ans = input("Would you like to install all job portal search tools now? (Y/n): ").strip().lower()
    if ans in ("", "y", "yes"):
        install_portal_tools()

    print("\n--- Step 2: Choose Your Target Job Market & Resume ---")
    print("  [1] North America (Canada / US) - 1-Page Jake's Resume (pdflatex, Indeed/Job Bank/TechTO)")
    print("  [2] Europe & International      - 2-Page ModernCV (lualatex, Jobindex/LinkedIn)")
    market_choice = input("Enter choice [1 or 2] (Default: 1): ").strip()
    template = "jakes" if market_choice in ("", "1") else "moderncv"

    print(f"\nSelected template: {'1-Page North American Jake Resume' if template == 'jakes' else '2-Page ModernCV'}")
    smoke_test_latex(template)

    profile_data = configure_candidate_profile(interactive=True)

    loc = profile_data.get("location")
    if loc == "[YOUR_ADDRESS]":
        loc = "Toronto, ON"
    name = profile_data.get("name")
    configure_swarm_sectors(interactive=True, location=loc, candidate_name=name)

    configure_rag_notebook(interactive=True)

    print("=" * 72)
    print("🎉 You are completely set up and ready to search!")
    print()
    print("Available Workflows:")
    print('  1. Multi-Sector Swarm:   Run /indeed-swarm-scraper for 3 parallel sector searches')
    print('  2. Targeted Indeed:      Run /scrape-indeed to search specific roles & deduplicate')
    print('  3. Coursework RAG Apply: Run /rag-apply <job_url> for tailored CV with lab proof')
    print('  4. Standard ATS Apply:   Run /apply <job_url> for standard resume & cover letter')
    print('  5. Interview Prep:       Run /interview <company> for STAR story prep & mock QA')
    print('  6. Visual Dashboard:     Run /html-report to review your pipeline offline')
    print("=" * 72 + "\n")


def main():
    parser = argparse.ArgumentParser(description="AI Job Search Enhanced Beginner Setup Wizard")
    parser.add_argument("--doctor", action="store_true", help="Check system dependencies and exit")
    parser.add_argument("--install", action="store_true", help="Install all portal search tools and exit")
    parser.add_argument("--test-latex", choices=["jakes", "moderncv"], help="Smoke-test LaTeX compiler")
    parser.add_argument("--configure-profile", action="store_true", help="Configure candidate profile only")
    parser.add_argument("--configure-swarm", action="store_true", help="Configure Indeed Swarm sectors only")
    parser.add_argument("--configure-rag", action="store_true", help="Configure NotebookLM RAG only")
    parser.add_argument("--non-interactive", action="store_true", help="Run automated setup without prompting")
    args = parser.parse_args()

    if args.doctor:
        print_banner()
        run_doctor()
        return

    if args.install:
        print_banner()
        install_portal_tools()
        return

    if args.test_latex:
        smoke_test_latex(args.test_latex)
        return

    if args.configure_profile:
        configure_candidate_profile(interactive=True)
        return

    if args.configure_swarm:
        configure_swarm_sectors(interactive=True)
        return

    if args.configure_rag:
        configure_rag_notebook(interactive=True)
        return

    if args.non_interactive:
        print_banner()
        run_doctor()
        configure_swarm_sectors(interactive=False)
        configure_rag_notebook(interactive=False)
        print("✓ Non-interactive setup complete.")
        return

    run_interactive_setup()


if __name__ == "__main__":
    main()
