#!/usr/bin/env python3
"""
Dashboard Generator & Rebuilder for AI Job Search
Executes the canonical, full-featured application dashboard rebuilder with:
- Light / Dark theme support
- Newmarket, ON commute distance calculation & travel bands
- Multi-board filtering (Indeed, Jobs Canada, LinkedIn, Eluta, GC Jobs, Talent.com)
- Pre-sorted triage rankings and visual badges
- Automated GitHub Pages deployment
"""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CANONICAL_REBUILD = REPO_ROOT / "scripts" / "rebuild_tracker_and_dashboard_winter_only.py"

def main():
    if not CANONICAL_REBUILD.exists():
        print(f"Error: {CANONICAL_REBUILD} not found", file=sys.stderr)
        sys.exit(1)
    res = subprocess.run([sys.executable, str(CANONICAL_REBUILD)] + sys.argv[1:])
    sys.exit(res.returncode)

if __name__ == "__main__":
    main()
