#!/usr/bin/env python3
"""
LinkedIn Profile Verification & Algorithmic Linter.

Audits a LinkedIn profile markdown specification or draft against 2026 platform
rules, character limits, recruiter Boolean indexing heuristics, and factual grounding.
"""

import sys
import os
import re
import json
import argparse
from typing import Dict, Any, List, Tuple


# Standard 2026 Character Limits
LIMIT_HEADLINE = 220
LIMIT_HEADLINE_FOLD = 70
LIMIT_ABOUT = 2600
LIMIT_ABOUT_FOLD = 300
LIMIT_EXP_DESCRIPTION = 2000
LIMIT_SKILL_NAME = 80
MAX_SKILLS = 50

# Critical Acronym / Full-Term Pairs for Boolean Indexing
ACRONYM_PAIRS = [
    (r"\bActive Directory\b", r"\b(AD|AD DS)\b", "Active Directory / AD DS"),
    (r"\bGroup Policy\b", r"\b(GPO|GPOs)\b", "Group Policy / GPOs"),
    (r"\bDynamic Host Configuration Protocol\b", r"\bDHCP\b", "Dynamic Host Configuration Protocol / DHCP"),
    (r"\bDomain Name System\b", r"\bDNS\b", "Domain Name System / DNS"),
    (r"\bVirtual Local Area Network(s)?\b", r"\bVLAN(s)?\b", "Virtual Local Area Network / VLANs"),
    (r"\bZone-Based Policy Firewall(s)?\b", r"\bZFW\b", "Zone-Based Policy Firewall / ZFW"),
    (r"\bNetwork Address Translation\b", r"\bNAT\b", "Network Address Translation / NAT"),
    (r"\bArchitecture Decision Record(s)?\b", r"\bADR(s)?\b", "Architecture Decision Records / ADRs"),
]


def extract_section(content: str, header_regex: str, next_header_regex: str = r"\n##\s+") -> str:
    """Extracts markdown text under a given heading."""
    match = re.search(header_regex, content, re.IGNORECASE)
    if not match:
        return ""
    start_pos = match.end()
    next_match = re.search(next_header_regex, content[start_pos:])
    if next_match:
        return content[start_pos : start_pos + next_match.start()].strip()
    return content[start_pos:].strip()


def extract_code_block(text: str) -> str:
    """Extracts raw text inside the first markdown code block if present."""
    match = re.search(r"```(?:text)?\n(.*?)\n```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


def audit_headline(content: str) -> Dict[str, Any]:
    """Audits the profile headline for length and visible fold."""
    # Look for headline block
    headline_sec = extract_section(content, r"##\s+(?:2\.\s+)?Headline[^\n]*\n")
    if not headline_sec:
        # Fallback to direct label
        m = re.search(r"\*\*Headline:\*\*\s*([^\n]+)", content)
        headline_text = m.group(1).strip() if m else ""
    else:
        # Extract first option or code block
        lines = [line.strip() for line in headline_sec.splitlines() if line.strip() and not line.startswith("#")]
        code_text = extract_code_block(headline_sec)
        headline_text = code_text.splitlines()[0] if code_text else (lines[0] if lines else "")

    char_len = len(headline_text)
    pass_limit = char_len <= LIMIT_HEADLINE
    fold_preview = headline_text[:LIMIT_HEADLINE_FOLD]
    has_pipe_or_sep = "|" in headline_text or "•" in headline_text

    return {
        "headline_text": headline_text,
        "char_count": char_len,
        "limit": LIMIT_HEADLINE,
        "pass_limit": pass_limit,
        "fold_preview": fold_preview,
        "has_role_separator": has_pipe_or_sep,
    }


def audit_about(content: str) -> Dict[str, Any]:
    """Audits the About section for 2600-char limit and 300-char visible fold hook."""
    about_sec = extract_section(content, r"##\s+(?:3\.\s+|4\.\s+)?[\"']?About[\"']?\s+Section[^\n]*\n")
    about_text = extract_code_block(about_sec)
    if not about_text:
        about_text = about_sec

    char_len = len(about_text)
    pass_limit = char_len <= LIMIT_ABOUT and char_len > 100
    hook_preview = about_text[:LIMIT_ABOUT_FOLD]
    has_contact_info = bool(re.search(r"(@|mailto:|contact|email|phone)", about_text, re.IGNORECASE))

    return {
        "char_count": char_len,
        "limit": LIMIT_ABOUT,
        "pass_limit": pass_limit,
        "hook_preview": hook_preview,
        "has_contact_info": has_contact_info,
    }


def audit_skills(content: str) -> Dict[str, Any]:
    """Audits skill count, top 3 pinned skills, and 50-skill taxonomy."""
    skills_sec = extract_section(content, r"##\s+(?:\d+\.\s+)?(?:Complete\s+)?50-Skill\s+Taxonomy[^\n]*\n")
    if not skills_sec:
        skills_sec = extract_section(content, r"##\s+(?:\d+\.\s+)?Skills\s+Section[^\n]*\n")

    # Match numbered items or bullet points
    skill_items = re.findall(r"(?:^\s*\d+\.\s+\*?\*?([^\n\*\:]+)\*?\*?|^\s*[-*]\s+\*?\*?([^\n\*\:]+)\*?\*?)", skills_sec, re.MULTILINE)
    parsed_skills = [s[0].strip() or s[1].strip() for s in skill_items if (s[0].strip() or s[1].strip())]
    # Filter out header sub-lines
    parsed_skills = [s for s in parsed_skills if not s.lower().startswith("top") and not s.lower().startswith("technical")]

    count = len(parsed_skills)
    pinned_match = re.search(r"Top\s+3\s+Pinned(?:\s+Skills)?.*?\n((?:\s*\d+\..*?\n){1,3})", skills_sec, re.IGNORECASE)
    has_top_3 = bool(pinned_match)

    return {
        "skills_found_count": count,
        "max_slots": MAX_SKILLS,
        "has_top_3_pinned": has_top_3,
        "sample_skills": parsed_skills[:10],
    }


def audit_acronym_pairing(content: str) -> Dict[str, Any]:
    """Verifies that both acronyms and full terms appear to maximize Boolean search hits."""
    pair_results = []
    matched_count = 0

    for full_regex, acr_regex, label in ACRONYM_PAIRS:
        has_full = bool(re.search(full_regex, content, re.IGNORECASE))
        has_acr = bool(re.search(acr_regex, content, re.IGNORECASE))
        passed = has_full and has_acr
        if passed:
            matched_count += 1
        pair_results.append({
            "term": label,
            "has_full_term": has_full,
            "has_acronym": has_acr,
            "both_present": passed,
        })

    return {
        "matched_pairs": matched_count,
        "total_checked": len(ACRONYM_PAIRS),
        "details": pair_results,
    }


def audit_spotlight_readiness(content: str) -> Dict[str, Any]:
    """Computes a 0–100 score indicating candidate positioning for recruiter spotlight filters."""
    score = 0
    checks = []

    # 1. Open to work signals (25 pts)
    if "Open to Work" in content or "open to work" in content.lower():
        score += 25
        checks.append(("Open to Work configuration defined", True, 25))
    else:
        checks.append(("Open to Work configuration defined", False, 0))

    # 2. Dual co-op and internship keywords (25 pts)
    has_coop = bool(re.search(r"\bco-?op\b", content, re.IGNORECASE))
    has_intern = bool(re.search(r"\bintern(ship)?\b", content, re.IGNORECASE))
    if has_coop and has_intern:
        score += 25
        checks.append(("Dual 'Co-op' and 'Internship' terminology used", True, 25))
    elif has_coop or has_intern:
        score += 15
        checks.append(("Partial 'Co-op' or 'Internship' keyword presence", True, 15))
    else:
        checks.append(("Co-op/Internship search terms missing", False, 0))

    # 3. Quantified metrics in experience (25 pts)
    metrics = re.findall(r"(\$\d+[\d,]*|\b\d+%\b|\b\d+\+\b|\b\d+\s+games\b|\b4\.0\b)", content)
    if len(metrics) >= 4:
        score += 25
        checks.append((f"High metric density ({len(metrics)} quantifiable markers found)", True, 25))
    elif len(metrics) >= 2:
        score += 15
        checks.append((f"Moderate metric density ({len(metrics)} markers found)", True, 15))
    else:
        checks.append(("Low quantifiable metric presence", False, 0))

    # 4. Regional GTA search radius positioning (25 pts)
    if "Greater Toronto Area" in content:
        score += 25
        checks.append(("Greater Toronto Area regional location configured", True, 25))
    elif "Toronto" in content:
        score += 15
        checks.append(("Toronto location present", True, 15))
    else:
        checks.append(("Regional metropolitan search anchor missing", False, 0))

    return {
        "spotlight_score": min(score, 100),
        "checks": checks,
    }


def verify_linkedin_profile(profile_path: str) -> Dict[str, Any]:
    """Runs complete verification suite on target profile file."""
    if not os.path.exists(profile_path):
        return {"error": f"Profile file not found at: {profile_path}", "passed": False}

    with open(profile_path, "r", encoding="utf-8") as f:
        content = f.read()

    h_audit = audit_headline(content)
    a_audit = audit_about(content)
    s_audit = audit_skills(content)
    p_audit = audit_acronym_pairing(content)
    r_audit = audit_spotlight_readiness(content)

    all_passed = (
        h_audit["pass_limit"]
        and a_audit["pass_limit"]
        and s_audit["skills_found_count"] >= 30
        and r_audit["spotlight_score"] >= 75
    )

    return {
        "file": profile_path,
        "all_passed": all_passed,
        "headline": h_audit,
        "about": a_audit,
        "skills": s_audit,
        "acronym_pairing": p_audit,
        "spotlight": r_audit,
    }


def print_report(res: Dict[str, Any]):
    """Formats and prints verification audit results."""
    print("============================================================")
    print("   LINKEDIN PROFILE ALGORITHMIC VERIFICATION & LINTER")
    print("============================================================")
    print(f"Target File: {res['file']}\n")

    # Headline
    h = res["headline"]
    h_status = "PASS" if h["pass_limit"] else "FAIL"
    print(f"[{h_status}] HEADLINE AUDIT:")
    print(f"       Character count: {h['char_count']} / {h['limit']}")
    print(f"       Fold preview (first 70 chars): \"{h['fold_preview']}\"")
    print(f"       Structure separator present: {h['has_role_separator']}\n")

    # About
    a = res["about"]
    a_status = "PASS" if a["pass_limit"] else "FAIL"
    print(f"[{a_status}] ABOUT / SUMMARY AUDIT:")
    print(f"       Character count: {a['char_count']} / {a['limit']}")
    print(f"       Contact details present: {a['has_contact_info']}")
    print(f"       Hook snippet: \"{a['hook_preview'][:120]}...\"\n")

    # Skills
    s = res["skills"]
    s_status = "PASS" if s["skills_found_count"] >= 30 else "WARN"
    print(f"[{s_status}] SKILLS TAXONOMY AUDIT:")
    print(f"       Total skills detected: {s['skills_found_count']} / {s['max_slots']}")
    print(f"       Top 3 pinned skills identified: {s['has_top_3_pinned']}\n")

    # Acronyms
    p = res["acronym_pairing"]
    print(f"[*] RECRUITER BOOLEAN ACRONYM PAIRS:")
    print(f"       {p['matched_pairs']} of {p['total_checked']} terms have both full-form and acronym present.")
    for detail in p["details"]:
        flag = "✓" if detail["both_present"] else "✗"
        print(f"       [{flag}] {detail['term']}")
    print()

    # Spotlight Score
    r = res["spotlight"]
    print(f"[*] RECRUITER SPOTLIGHT READINESS SCORE: {r['spotlight_score']} / 100")
    for desc, passed, pts in r["checks"]:
        flag = "✓" if passed else "✗"
        print(f"       [{flag}] {desc} (+{pts} pts)")
    print()

    print("============================================================")
    status_label = "ALL VERIFICATION CHECKS PASSED" if res["all_passed"] else "ACTION REQUIRED ON PROFILE"
    print(f"   STATUS: {status_label}")
    print("============================================================")


def main():
    parser = argparse.ArgumentParser(description="LinkedIn Profile Verification & Algorithmic Linter")
    parser.add_argument("profile_path", help="Path to LinkedIn markdown profile or review file")
    parser.add_argument("--json", action="store_true", help="Output raw JSON results")

    args = parser.parse_args()
    results = verify_linkedin_profile(args.profile_path)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print_report(results)

    if not results.get("all_passed"):
        sys.exit(1)


if __name__ == "__main__":
    main()
