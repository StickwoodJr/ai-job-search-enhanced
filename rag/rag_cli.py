#!/usr/bin/env python3
"""
Interactive CLI for RAG Experiment.

Enables testing, live verification against NotebookLM, source exploration,
and generation of tailored resume bullets and academic evidence packs.
"""

import argparse
import sys
import os

# Ensure local directory is in Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import DEFAULT_NOTEBOOK_ID, DEFAULT_NOTEBOOK_TITLE
from extendlm_bridge import ExtendLMBridge
from source_catalog import SourceCatalog
from verification_engine import VerificationEngine
from bullet_generator import BulletGenerator


def cmd_test(args):
    """Verifies connection to ExtendLM and access to the default notebook."""
    print("[*] Initializing ExtendLM Bridge...")
    bridge = ExtendLMBridge()
    try:
        conn, user_id = bridge.get_session_details()
        print(f"[+] Active Extension Connection: {conn}")
        print(f"[+] Active Auth User ID: {user_id}")
    except Exception as e:
        print(f"[-] Connection failed: {e}")
        sys.exit(1)

    print(f"[*] Listing sources for '{DEFAULT_NOTEBOOK_TITLE}' ({DEFAULT_NOTEBOOK_ID})...")
    try:
        sources = bridge.list_sources(DEFAULT_NOTEBOOK_ID)
        print(f"[+] Successfully loaded {len(sources)} curriculum sources.")
    except Exception as e:
        print(f"[-] Failed to retrieve sources: {e}")
        sys.exit(1)

    print("[+] All connectivity checks passed successfully!")


def cmd_catalog(args):
    """Displays the indexed curriculum sources grouped by course."""
    bridge = ExtendLMBridge()
    sources = bridge.list_sources(DEFAULT_NOTEBOOK_ID)
    catalog = SourceCatalog(sources)

    print(f"\n=======================================================")
    print(f"   Curriculum Source Catalog: {DEFAULT_NOTEBOOK_TITLE}")
    print(f"   Total Sources: {len(sources)}")
    print(f"=======================================================\n")

    for course, items in sorted(catalog.by_course.items()):
        print(f"\n--- {course} ({len(items)} files) ---")
        for item in items[: args.limit if args.limit else len(items)]:
            print(f"  • {item['title']}")
        if args.limit and len(items) > args.limit:
            print(f"    ... and {len(items) - args.limit} more")


def cmd_verify_skills(args):
    """Performs live skill verification against the notebook (no cache)."""
    skills_list = [s.strip() for s in args.skills.split(",") if s.strip()]
    if not skills_list:
        print("[-] Error: Please specify at least one skill with --skills.")
        sys.exit(1)

    print(f"[*] Executing live verification against NotebookLM for {len(skills_list)} skills...")
    print(f"    Target Role: {args.role}")
    print("    Skills:", ", ".join(skills_list))
    print("    (Live query in progress; this takes ~10-20 seconds)...")

    engine = VerificationEngine(DEFAULT_NOTEBOOK_ID)
    result = engine.verify_skills_list(skills_list, target_role=args.role)

    generator = BulletGenerator()
    pack = generator.generate_academic_evidence_pack(args.role, result)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(pack)
        print(f"\n[+] Academic Evidence Pack saved to: {args.output}\n")
    else:
        print("\n" + pack)


def cmd_verify_job(args):
    """Performs live job description verification against the notebook (no cache)."""
    job_content = ""
    if args.file:
        if not os.path.exists(args.file):
            print(f"[-] File not found: {args.file}")
            sys.exit(1)
        with open(args.file, "r", encoding="utf-8") as f:
            job_content = f.read()
    elif args.text:
        job_content = args.text
    else:
        print("[-] Error: Provide either --file or --text containing the job description.")
        sys.exit(1)

    print(f"[*] Executing live verification against NotebookLM for job posting...")
    print(f"    Target Role: {args.role}")
    print("    (Live query in progress; this takes ~10-20 seconds)...")

    engine = VerificationEngine(DEFAULT_NOTEBOOK_ID)
    result = engine.verify_job_requirements(args.role, job_content)

    generator = BulletGenerator()
    pack = generator.generate_academic_evidence_pack(args.role, result)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(pack)
        print(f"\n[+] Academic Evidence Pack saved to: {args.output}\n")
    else:
        print("\n" + pack)


def main():
    parser = argparse.ArgumentParser(
        description="RAG Experiment CLI: Query Seneca CTY NotebookLM via ExtendLM"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # test
    subparsers.add_parser("test", help="Test ExtendLM connection and notebook access")

    # catalog
    catalog_parser = subparsers.add_parser("catalog", help="List and summarize sources by course")
    catalog_parser.add_argument("--limit", type=int, default=10, help="Max items per course to show")

    # verify-skills
    skills_parser = subparsers.add_parser("verify-skills", help="Verify discrete skills against curriculum")
    skills_parser.add_argument("--skills", required=True, help="Comma-separated list of skills")
    skills_parser.add_argument("--role", default="IT Infrastructure Specialist", help="Target role title")
    skills_parser.add_argument("--output", help="Optional path to save markdown evidence pack")

    # verify-job
    job_parser = subparsers.add_parser("verify-job", help="Verify full job posting against curriculum")
    job_parser.add_argument("--file", help="Path to file containing job description")
    job_parser.add_argument("--text", help="Raw job description text")
    job_parser.add_argument("--role", default="Systems & Network Specialist", help="Target role title")
    job_parser.add_argument("--output", help="Optional path to save markdown evidence pack")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "test":
        cmd_test(args)
    elif args.command == "catalog":
        cmd_catalog(args)
    elif args.command == "verify-skills":
        cmd_verify_skills(args)
    elif args.command == "verify-job":
        cmd_verify_job(args)


if __name__ == "__main__":
    main()
