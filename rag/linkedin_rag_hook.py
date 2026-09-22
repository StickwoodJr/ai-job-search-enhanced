#!/usr/bin/env python3
"""
Adaptive LinkedIn RAG Bridge Hook.

Integrates NotebookLM knowledge retrieval into the /linkedin-optimizer workflow.
Features:
1. Dynamic Domain Introspection (Academic, Corporate, Projects, Certifications).
2. Source-Aware Cache Invalidation: Computes a SHA-256 fingerprint of attached sources
   via `bridge.list_sources(notebook_id)`. If sources change, automatically invalidates
   and refreshes the domain cache.
3. Adaptive Evidence Pack Synthesis: Generates a tailored `linkedin_evidence_pack.md`
   reflecting whatever knowledge domains exist in the candidate's notebook.
4. Resilient Fallback: Seamlessly falls back to local verified evidence packs if
   ExtendLM MCP is temporarily disconnected.
"""

import sys
import os
import json
import hashlib
import argparse
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

# Ensure local directory and tools directory are in Python path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

try:
    from config import DEFAULT_NOTEBOOK_ID
    from extendlm_bridge import ExtendLMBridge
except ImportError:
    from .config import DEFAULT_NOTEBOOK_ID
    from .extendlm_bridge import ExtendLMBridge

try:
    from check_extendlm import ensure_extendlm_ready
except ImportError:
    def ensure_extendlm_ready(halt_on_error: bool = True) -> bool:
        return True


CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
DOMAIN_CACHE_FILE = os.path.join(CACHE_DIR, "notebook_domain_cache.json")


def compute_source_fingerprint(sources: List[Dict[str, Any]]) -> Tuple[int, str]:
    """Generates a stable fingerprint from the list of attached notebook sources."""
    count = len(sources)
    # Sort identifiers to produce a deterministic hash
    identifiers = []
    for s in sources:
        s_id = str(s.get("id") or s.get("source_id") or s.get("title") or "")
        s_title = str(s.get("title") or "")
        identifiers.append(f"{s_id}:{s_title}")
    identifiers.sort()
    
    hash_val = hashlib.sha256(";".join(identifiers).encode("utf-8")).hexdigest()
    return count, hash_val


def load_domain_cache() -> Dict[str, Any]:
    """Loads cached domain introspection records."""
    if os.path.exists(DOMAIN_CACHE_FILE):
        try:
            with open(DOMAIN_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_domain_cache(cache: Dict[str, Any]) -> None:
    """Persists domain introspection records."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(DOMAIN_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)


def introspect_notebook_domains(
    bridge: ExtendLMBridge,
    notebook_id: str,
    sources: List[Dict[str, Any]],
    force_refresh: bool = False,
) -> Dict[str, Any]:
    """
    Classifies the knowledge domains in the notebook.
    Uses source-aware cache invalidation: if source count or hash changes, re-introspects.
    """
    source_count, source_hash = compute_source_fingerprint(sources)
    cache = load_domain_cache()
    cached_entry = cache.get(notebook_id)

    if (
        not force_refresh
        and cached_entry
        and cached_entry.get("source_count") == source_count
        and cached_entry.get("source_hash") == source_hash
    ):
        print(f"[*] Domain Introspection Cache HIT for notebook {notebook_id} ({source_count} sources)")
        return cached_entry

    print(f"[*] Running live domain introspection (source count: {source_count}, refresh: {force_refresh})...")
    
    # Introspection query across standard candidate knowledge domains
    introspection_prompt = (
        "Analyze all attached sources in this notebook. Identify and categorize the primary knowledge "
        "domains represented (e.g., Academic/Coursework, Corporate/Professional Employment, "
        "Technical/Homelab Projects, Industry Certifications). "
        "For each domain present, provide: "
        "1) Domain name and estimated prominence (high, medium, low). "
        "2) Key organizations, institutions, or company names mentioned. "
        "3) Primary technical toolchains, platforms, cmdlets, and protocols verified. "
        "4) Key quantitative metrics, grades, or project outcomes."
    )

    try:
        raw_answer = bridge.ask_notebook(notebook_id=notebook_id, question=introspection_prompt)
    except Exception as e:
        print(f"[!] Warning: ExtendLM introspection failed: {e}")
        raw_answer = "Fallback: Academic coursework and systems administration projects."

    entry = {
        "notebook_id": notebook_id,
        "source_count": source_count,
        "source_hash": source_hash,
        "source_titles": [s.get("title", "Untitled") for s in sources[:20]],
        "raw_introspection": raw_answer,
        "introspected_at": datetime.now(timezone.utc).isoformat(),
    }

    cache[notebook_id] = entry
    save_domain_cache(cache)
    print(f"[+] Successfully cached domain introspection for notebook {notebook_id}")
    return entry


def query_profile_evidence(
    bridge: ExtendLMBridge,
    notebook_id: str,
    target_role: str = "IT Systems Administrator",
) -> str:
    """Executes live, zero-cached evidence extraction tailored for LinkedIn profile sections."""
    profile_evidence_prompt = f"""
Target Role: {target_role}

Please extract verified primary evidence from the notebook to populate an optimized LinkedIn profile for this target role.
Extract the following exact details:

1. TOP 50 DOMAIN SKILLS & KEYWORDS:
List all specific tools, platforms, frameworks, methodologies, software, regulations, protocols, and competencies documented in the sources (relevant to {target_role}). Include exact tool names, platforms, industry standards, and technical/domain terminology.

2. ACCOMPLISHMENT & EXPERIENCE BULLETS (CAR/STAR FORMAT):
For every role, project, or major deliverable, extract:
- Context & Challenge: The environment, scope, budget, scale, team, or problem addressed.
- Action: Exact methodologies, software, tools, strategies, configurations, or leadership applied.
- Result / Metric: Quantifiable outcomes, efficiency gains, revenue, project outcomes, grades, uptime, or KPI achievements.

3. PROJECTS & STRATEGIC DELIVERABLES:
Extract details of major project deliveries, architecture decisions, research reports, case studies, portfolios, client accounts, or technical setups.

4. CREDENTIALS, EDUCATION & CERTIFICATIONS:
Extract verified degrees, licenses, certifications, coursework, academic honors, or regulatory credentials.
"""
    print(f"[*] Executing live evidence extraction for role: '{target_role}' (zero caching)...")
    return bridge.ask_notebook(notebook_id=notebook_id, question=profile_evidence_prompt)


def build_fallback_evidence_pack(target_role: str) -> str:
    """Constructs an evidence pack using verified local artifacts when ExtendLM is offline."""
    print("[*] Utilizing local verified evidence packs as fallback baseline...")
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    academic_path = os.path.join(base_dir, "academic_evidence_pack.md")
    career_path = os.path.join(base_dir, "career_evidence_pack.md")

    academic_content = ""
    career_content = ""
    if os.path.exists(academic_path):
        with open(academic_path, "r", encoding="utf-8") as f:
            academic_content = f.read()
    if os.path.exists(career_path):
        with open(career_path, "r", encoding="utf-8") as f:
            career_content = f.read()

    return f"""# LinkedIn Evidence Pack (Grounding Snapshot)
**Target Role:** {target_role}
**Extraction Mode:** Verified Primary Local Evidence Fallback
**Timestamp:** {datetime.now(timezone.utc).isoformat()}

---

## 1. Verified Career & Professional Experience Evidence
{career_content if career_content else "Refer to CLAUDE.md and candidate profile."}

---

## 2. Verified Academic & Coursework Evidence
{academic_content if academic_content else "Refer to academic evidence pack."}
"""


def generate_linkedin_evidence(
    role: str = "IT Systems Administrator",
    notebook_id: str = DEFAULT_NOTEBOOK_ID,
    output_path: Optional[str] = None,
    force_refresh_domains: bool = False,
    allow_fallback: bool = False,
) -> Dict[str, Any]:
    """Main programmatic entrypoint for the /linkedin-optimizer workflow."""
    if not allow_fallback:
        try:
            ensure_extendlm_ready(halt_on_error=True)
        except Exception as e:
            sys.exit(1)

    bridge = ExtendLMBridge()
    evidence_text = ""

    introspection_data: Dict[str, Any] = {}

    try:
        sources = bridge.list_sources(notebook_id)
        introspection_data = introspect_notebook_domains(
            bridge=bridge,
            notebook_id=notebook_id,
            sources=sources,
            force_refresh=force_refresh_domains,
        )
        raw_evidence = query_profile_evidence(
            bridge=bridge,
            notebook_id=notebook_id,
            target_role=role,
        )
        evidence_text = f"""# LinkedIn Adaptive Evidence Pack
**Target Role:** {role}
**Notebook ID:** {notebook_id}
**Source Count:** {len(sources)}
**Generated At:** {datetime.now(timezone.utc).isoformat()}

---

## 1. Knowledge Domain Introspection Profile
{introspection_data.get("raw_introspection", "Standard domains detected.")}

---

## 2. Verified Primary Source Grounding (Zero Caching)
{raw_evidence}
"""
    except Exception as e:
        if not allow_fallback:
            print("\n" + "=" * 72)
            print("[ERROR] ExtendLM Live RAG Retrieval Failed!")
            print(f"Detail: {e}")
            print("\nThe agent cannot query Google NotebookLM because the ExtendLM browser")
            print("bridge is offline. Your profile cannot be live-grounded against NotebookLM.")
            print("\nAction Required:")
            print("  1. Launch Google Chrome.")
            print("  2. Ensure the ExtendLM extension is active, connected, and authenticated.")
            print("  3. Ensure your target notebook is accessible.")
            print("\nIf you explicitly want to bypass live RAG and use local verified evidence,")
            print("re-run with the flag: --allow-fallback")
            print("=" * 72 + "\n")
            raise RuntimeError(f"ExtendLM live RAG retrieval failed: {e}")
        else:
            print(f"[!] Warning: ExtendLM offline ({e}). Utilizing local verified evidence packs (--allow-fallback was set).")
            evidence_text = build_fallback_evidence_pack(target_role=role)

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(evidence_text)
        print(f"[+] Saved LinkedIn Evidence Pack -> {output_path}")

    return {
        "role": role,
        "notebook_id": notebook_id,
        "evidence_pack_md": evidence_text,
        "introspection": introspection_data,
    }


def main():
    parser = argparse.ArgumentParser(description="Adaptive LinkedIn RAG Bridge Hook")
    parser.add_argument("--role", default="IT Systems Administrator", help="Target job role")
    parser.add_argument("--notebook-id", default=DEFAULT_NOTEBOOK_ID, help="Google NotebookLM ID")
    parser.add_argument(
        "--output",
        default="linkedin_evidence_pack.md",
        help="Path where the output evidence pack markdown will be saved",
    )
    parser.add_argument(
        "--refresh-domains",
        action="store_true",
        help="Force re-introspection of notebook knowledge domains regardless of cache",
    )
    parser.add_argument(
        "--allow-fallback",
        action="store_true",
        help="Explicitly allow fallback to local verified evidence packs if ExtendLM is disconnected",
    )

    args = parser.parse_args()
    try:
        generate_linkedin_evidence(
            role=args.role,
            notebook_id=args.notebook_id,
            output_path=args.output,
            force_refresh_domains=args.refresh_domains,
            allow_fallback=args.allow_fallback,
        )
    except Exception as err:
        sys.exit(1)



if __name__ == "__main__":
    main()
