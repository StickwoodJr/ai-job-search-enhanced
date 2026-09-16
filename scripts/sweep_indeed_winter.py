#!/usr/bin/env python3
"""
Continuous Winter 2027 Indeed Scrape Sweep Runner
Executes deep-query scanning on Indeed Canada for Cisco Networking,
NOC Operations, Hardware Infrastructure, and Cybersecurity Winter 2027 Co-ops.
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parent.parent
VENV_PYTHON = REPO_ROOT / "mcp-servers" / "indeed-mcp" / ".venv" / "bin" / "python"

if VENV_PYTHON.exists() and sys.executable != str(VENV_PYTHON):
    os.execv(str(VENV_PYTHON), [str(VENV_PYTHON)] + sys.argv)

sys.path.insert(0, str(REPO_ROOT))
from scripts.scrape_indeed import run_indeed_workflow

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("winter-sweep")

TARGET_QUERIES = [
    ("Cisco Network Co-op", "Toronto, ON"),
    ("NOC Analyst Winter 2027", "Toronto, ON"),
    ("Network Security Co-op Winter", "Toronto, ON"),
    ("SOC Analyst Intern Winter 2027", "Toronto, ON"),
    ("Telecom Technician Co-op", "Mississauga, ON"),
    ("IT Infrastructure Co-op Winter 2027", "Markham, ON"),
    ("Hardware Support Co-op Winter", "York Region, ON"),
]


def run_sweep_cycle(cycle_num: int = 1) -> List[Dict[str, Any]]:
    logger.info("=== Starting Winter 2027 Scrape Cycle #%d (%d queries) ===", cycle_num, len(TARGET_QUERIES))
    new_winter_jobs: List[Dict[str, Any]] = []
    total_new = 0

    for query, location in TARGET_QUERIES:
        logger.info("Running query: '%s' in '%s'", query, location)
        try:
            results = run_indeed_workflow(
                query_override=query,
                location=location,
                limit=10,
                jobage=14,
                output_format="table",
            )
            if results:
                total_new += len(results)
                for j in results:
                    if j.get("is_winter"):
                        new_winter_jobs.append(j)
        except Exception as e:
            logger.error("Error executing query '%s': %s", query, e)

    logger.info(
        "Cycle #%d completed: %d total new postings discovered (%d explicit Winter 2027 Co-ops)",
        cycle_num,
        total_new,
        len(new_winter_jobs),
    )
    return new_winter_jobs


def main():
    parser = argparse.ArgumentParser(description="Winter 2027 Continuous Sweep Runner")
    parser.add_argument("--once", action="store_true", help="Run a single cycle and exit")
    parser.add_argument("--interval", type=int, default=90, help="Pause seconds between cycles (default: 90)")
    args = parser.parse_args()

    cycle = 1
    while True:
        discovered_winter = run_sweep_cycle(cycle)
        if discovered_winter:
            print(f"\n[ALERT] Cycle #{cycle} discovered {len(discovered_winter)} new Winter 2027 Co-op(s)!")
            for j in discovered_winter:
                print(f" - {j.get('title')} at {j.get('company')} ({j.get('location')}) -> {j.get('url')}")

            rebuild_script = REPO_ROOT / "scripts" / "rebuild_tracker_and_dashboard_winter_only.py"
            if rebuild_script.exists():
                try:
                    logger.info("Triggering tracker & dashboard rebuild and GitHub Pages auto-deploy...")
                    subprocess.run([sys.executable, str(rebuild_script)], check=True)
                except Exception as e:
                    logger.error("Error rebuilding dashboard: %s", e)

        if args.once:
            break

        logger.info("Pausing %d seconds before next sweep cycle...", args.interval)
        time.sleep(args.interval)
        cycle += 1


if __name__ == "__main__":
    main()
