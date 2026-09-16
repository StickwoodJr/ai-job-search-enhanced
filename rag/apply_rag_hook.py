#!/usr/bin/env python3
"""
cmd-apply RAG Bridge Hook.

Integrates the RAG Experiment knowledge retrieval directly into the
cmd-apply workflow (Step 1 Fit Evaluation & Step 2 Drafting).
Takes the job posting content, triggers live verification in NotebookLM
(with NO caching), and outputs a tailored Academic Evidence Pack
that can be inserted into the candidate profile and resume.
"""

import sys
import os
import argparse
from typing import Dict, Any, Optional

# Ensure local directory is in Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import DEFAULT_NOTEBOOK_ID
from verification_engine import VerificationEngine
from bullet_generator import BulletGenerator


def generate_evidence_for_job(
    job_text: str,
    role: str = "Target Role",
    notebook_id: str = DEFAULT_NOTEBOOK_ID,
    output_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Core programmatic API for the cmd-apply workflow.
    Executes live verification against NotebookLM and generates the evidence pack.
    """
    engine = VerificationEngine(notebook_id=notebook_id)
    verification_result = engine.verify_job_requirements(
        target_role=role,
        requirements_or_job_text=job_text,
    )

    generator = BulletGenerator()
    pack_md = generator.generate_academic_evidence_pack(role, verification_result)
    latex_bullets = generator.synthesize_moderncv_bullets(verification_result["raw_answer"])

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(pack_md)

    return {
        "role": role,
        "notebook_id": notebook_id,
        "evidence_pack_md": pack_md,
        "latex_bullets": latex_bullets,
        "raw_answer": verification_result["raw_answer"],
    }


def main():
    parser = argparse.ArgumentParser(
        description="RAG Hook for cmd-apply: Extract grounded achievements and proof for a job posting"
    )
    parser.add_argument("posting", help="Path to job posting file or inline text")
    parser.add_argument("--role", default="Candidate", help="Target job role")
    parser.add_argument(
        "--output",
        default="career_evidence_pack.md",
        help="Path where the Career Evidence Pack markdown should be saved",
    )

    args = parser.parse_args()

    content = args.posting
    if os.path.exists(args.posting):
        with open(args.posting, "r", encoding="utf-8") as f:
            content = f.read()

    print(f"[*] Running live RAG verification for role: '{args.role}'...")
    print("    Querying NotebookLM knowledge base (zero caching)...")

    result = generate_evidence_for_job(
        job_text=content,
        role=args.role,
        output_path=args.output,
    )

    print(f"[+] Successfully generated Academic Evidence Pack -> {args.output}")
    print("\n--- Summary of Verified ModernCV Bullets ---")
    for b in result["latex_bullets"]:
        print(" ", b)


if __name__ == "__main__":
    main()
