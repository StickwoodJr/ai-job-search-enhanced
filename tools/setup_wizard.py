#!/usr/bin/env python3
"""
AI Job Search - Beginner Onboarding & Environment Setup Wizard

Designed for zero-experience beginners and autonomous AI coding agents.
Verifies system dependencies, installs search portal tools, configures the
candidate profile, and smoke-tests LaTeX PDF compilation.

Usage:
    python tools/setup_wizard.py              # Full interactive guided setup
    python tools/setup_wizard.py --doctor     # Check environment dependencies only
    python tools/setup_wizard.py --install    # Install all portal search CLIs (Bun/npm)
"""

import argparse
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


def print_banner():
    print("=" * 70)
    print("   🤖 AI Job Search - Autonomous Setup & Onboarding Wizard")
    print("   The job search operating system that runs on your local machine.")
    print("=" * 70)
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


def run_interactive_setup():
    """Guided onboarding questionnaire for beginners."""
    print_banner()
    run_doctor()

    print("--- Step 1: Portal Tools Setup ---")
    ans = input("Would you like to install all job portal search tools now? (Y/n): ").strip().lower()
    if ans in ("", "y", "yes"):
        install_portal_tools()

    print("\n--- Step 2: Choose Your Target Job Market ---")
    print("  [1] North America (Canada / US) - 1-Page Jake's Resume (pdflatex, Indeed/Job Bank/TechTO)")
    print("  [2] Europe & International      - 2-Page ModernCV (lualatex, Jobindex/LinkedIn)")
    market_choice = input("Enter choice [1 or 2] (Default: 1): ").strip()
    template = "jakes" if market_choice in ("", "1") else "moderncv"

    print(f"\nSelected template: {'1-Page North American Jake Resume' if template == 'jakes' else '2-Page ModernCV'}")
    smoke_test_latex(template)

    print("--- Step 3: Candidate Information ---")
    print("Tip: You can press Enter to skip or accept defaults and edit later.\n")
    name = input("Your Full Name: ").strip() or "[YOUR_NAME]"
    email = input("Your Email Address: ").strip() or "[YOUR_EMAIL]"
    phone = input("Your Phone Number: ").strip() or "[YOUR_PHONE]"
    location = input("Your City, Province/State, Country: ").strip() or "[YOUR_ADDRESS]"
    roles = input("Target Job Roles (e.g. Systems Admin, Help Desk, Co-op): ").strip() or "[YOUR_TARGET_ROLES]"
    skills = input("Primary Technical Skills (comma-separated): ").strip() or "[YOUR_PRIMARY_SKILLS]"

    # Populate 01-candidate-profile.md if values were provided
    if name != "[YOUR_NAME]" and PROFILE_FILE.exists():
        content = PROFILE_FILE.read_text(encoding="utf-8")
        content = content.replace("- **Name:** [YOUR_NAME]", f"- **Name:** {name}")
        content = content.replace("- **Email:** [YOUR_EMAIL]", f"- **Email:** {email}")
        content = content.replace("- **Phone:** [YOUR_PHONE]", f"- **Phone:** {phone}")
        content = content.replace("- **Location:** [YOUR_ADDRESS]", f"- **Location:** {location}")
        PROFILE_FILE.write_text(content, encoding="utf-8")
        print(f"\n✓ Saved candidate profile to {PROFILE_FILE}")

    print("\n" + "=" * 70)
    print("🎉 You are ready to search for jobs!")
    print("Just ask your AI agent (Antigravity or Claude Code):")
    print('  - "Search Indeed Canada for junior IT positions"')
    print('  - "Run /scrape-indeed to find new postings"')
    print('  - "Apply to this posting: <URL>"')
    print('  - "Prepare me for an interview at <Company>"')
    print("=" * 70 + "\n")


def main():
    parser = argparse.ArgumentParser(description="AI Job Search Beginner Setup Wizard")
    parser.add_argument("--doctor", action="store_true", help="Check system dependencies and exit")
    parser.add_argument("--install", action="store_true", help="Install all portal search tools and exit")
    parser.add_argument("--test-latex", choices=["jakes", "moderncv"], help="Smoke-test LaTeX compiler")
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

    run_interactive_setup()


if __name__ == "__main__":
    main()
