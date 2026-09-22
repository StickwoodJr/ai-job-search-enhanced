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

# Agentic Pipeline Dynamic Acronym & Term Parser
# Rather than maintaining a rigid static dictionary of predetermined sectors,
# this agentic system dynamically extracts inline acronym definitions,
# verifies expanded phrases across document text, and supports agent-generated
# domain terms on the fly based on the user's specific target role and field.

STOPWORDS_ACRONYM = {
    "THE", "AND", "FOR", "NOT", "ARE", "WITH", "THAT", "THIS", "FROM", "THEY",
    "HAVE", "BEEN", "WILL", "GPA", "FAIL", "PASS", "WARN", "NONE", "NULL", "TRUE", "FALSE"
}


def extract_inline_acronym_pairs(content: str) -> List[Tuple[str, str]]:
    """
    Dynamically extracts inline acronym definitions:
    e.g. 'Active Directory Domain Services (AD DS)', 'Return on Investment (ROI)',
         'Generally Accepted Accounting Principles (GAAP)', 'Basic Life Support (BLS)'.
    """
    matches = re.findall(
        r"((?:[A-Z][a-zA-Z0-9\-]*(?:\s+(?:and|of|for|the|in|to|on|with|by|DS)\b)?\s*){1,6})\s*\(([A-Z0-9]{1,6}(?:\s+[A-Z0-9]{1,4})?)\)",
        content,
    )
    pairs = []
    seen = set()
    for full_cand, acr in matches:
        full_clean = full_cand.strip()
        if len(full_clean) > 2 and full_clean.lower() != acr.lower():
            key = (full_clean.lower(), acr)
            if key not in seen:
                seen.add(key)
                pairs.append((full_clean, acr))
    return pairs


def check_acronym_initials_in_text(acr: str, text: str) -> bool:
    """
    Checks if an acronym's letters match consecutive words spelled out anywhere in the document text.
    Allows standard prepositions/conjunctions (and, of, for, the, in, to, on, with).
    """
    if len(acr) < 2 or not acr.isalpha():
        return False
    pattern = r"\b" + r"\s+(?:and\s+|of\s+|for\s+|the\s+|in\s+|to\s+|on\s+|with\s+)?".join([re.escape(c) + r"[a-zA-Z0-9\-]+" for c in acr]) + r"\b"
    return bool(re.search(pattern, text, re.IGNORECASE))




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


def audit_acronym_pairing(content: str, domain_terms: List[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Verifies that acronyms and full terms are paired to maximize Boolean ATS search hits.
    In this agentic pipeline, acronyms and terms are evaluated dynamically:
    1. Extracts all inline paired definitions: 'Full Term (ACRONYM)'.
    2. Identifies uppercase candidate acronyms and checks if their initials match expanded phrases in text.
    3. If agent-generated domain terms are supplied (e.g. from the Drafter/Reviewer agent),
       verifies that both the full form and acronym appear in the profile.
    """
    inline_pairs = extract_inline_acronym_pairs(content)
    inline_acrs = {acr for _, acr in inline_pairs}

    # Discover candidate uppercase acronyms (2 to 6 capital letters)
    raw_acrs = set(re.findall(r"\b[A-Z]{2,6}\b", content)) - STOPWORDS_ACRONYM

    paired_acronyms = []
    unpaired_acronyms = []
    for acr in sorted(raw_acrs):
        if acr in inline_acrs:
            paired_acronyms.append((acr, "inline definition"))
        elif check_acronym_initials_in_text(acr, content):
            paired_acronyms.append((acr, "expanded phrase in text"))
        else:
            unpaired_acronyms.append(acr)

    # Agent-supplied domain terms (if generated dynamically on the fly by the agent pipeline)
    agent_terms_results = []
    if domain_terms:
        for item in domain_terms:
            full = item.get("full_term", "")
            acr = item.get("acronym", "")
            label = item.get("label", f"{full} / {acr}" if full and acr else (full or acr))
            has_full = bool(re.search(r"\b" + re.escape(full) + r"\b", content, re.IGNORECASE)) if full else False
            has_acr = bool(re.search(r"\b" + re.escape(acr) + r"\b", content)) if acr else False
            if has_full or has_acr:
                agent_terms_results.append({
                    "term": label,
                    "has_full_term": has_full,
                    "has_acronym": has_acr,
                    "both_present": has_full and has_acr,
                })

    matched_agent = sum(1 for r in agent_terms_results if r["both_present"])
    total_agent = len(agent_terms_results)

    total_verified = len(inline_pairs) + len(paired_acronyms) + matched_agent

    return {
        "inline_discovered_count": len(inline_pairs),
        "inline_pairs": inline_pairs,
        "paired_acronyms": paired_acronyms,
        "unpaired_acronyms": unpaired_acronyms,
        "agent_terms_checked": total_agent,
        "agent_terms_matched": matched_agent,
        "agent_terms_details": agent_terms_results,
        "total_verified_pairs": total_verified,
        "passed": len(inline_pairs) >= 3 or matched_agent >= 1 or len(paired_acronyms) >= 3,
    }


def audit_spotlight_readiness(content: str) -> Dict[str, Any]:
    """
    Computes a 0–100 score indicating candidate positioning for recruiter spotlight filters
    across any profession, industry, or seniority level.
    """
    score = 0
    checks = []

    # 1. Open to work & availability signals (25 pts)
    has_avail = bool(re.search(
        r"\b(open to work|available for|seeking|immediate availability|open to opportunities|work term|looking for|available [a-z]+)\b",
        content,
        re.IGNORECASE,
    ))
    if has_avail:
        score += 25
        checks.append(("Availability / Open to Work signal present", True, 25))
    else:
        checks.append(("Availability / Open to Work signal missing", False, 0))

    # 2. Target Role & Seniority Anchoring (25 pts)
    headline_info = audit_headline(content)
    headline_text = headline_info.get("headline_text", "")
    has_separator = headline_info.get("has_role_separator", False)

    has_coop = bool(re.search(r"\bco-?op\b", content, re.IGNORECASE))
    has_intern = bool(re.search(r"\bintern(ship)?\b", content, re.IGNORECASE))

    # In professional LinkedIn profiles, headline frontloads the target role before the separator
    has_title_in_headline = bool(headline_text and has_separator and len(headline_text.split("|")[0].split("•")[0].strip()) >= 3)
    has_seniority_signal = bool(re.search(
        r"\b(student|co-?op|intern(ship)?|junior|entry[- ]level|associate|senior|lead|principal|director|manager|specialist|consultant|officer|practitioner|head|analyst|engineer)\b",
        content,
        re.IGNORECASE,
    ))

    if (has_coop and has_intern) or (has_title_in_headline and has_seniority_signal):
        score += 25
        if has_coop and has_intern:
            checks.append(("Target role & dual 'Co-op'/'Internship' terminology aligned", True, 25))
        else:
            checks.append(("Target role & seniority positioning defined in headline", True, 25))
    elif has_title_in_headline or has_seniority_signal or has_coop or has_intern:
        score += 15
        checks.append(("Target role keywords present (partial seniority alignment)", True, 15))
    else:
        checks.append(("Target role & seniority positioning missing", False, 0))

    # 3. Quantified metrics in experience & projects (25 pts)
    # Matches currency ($), percentages (%), counts/volumes (10+, 100k, 4.0 GPA, numbers)
    metrics = re.findall(r"(\$[\d,]+(?:\.\d+)?(?:k|M|B)?|\b\d+%|\d+\+|\b\d+(?:k|M|B)\b|\b\d{2,}\b|\b\d\.\d\b)", content)
    if len(metrics) >= 4:
        score += 25
        checks.append((f"High metric density ({len(metrics)} quantifiable markers found)", True, 25))
    elif len(metrics) >= 2:
        score += 15
        checks.append((f"Moderate metric density ({len(metrics)} markers found)", True, 15))
    else:
        checks.append(("Low quantifiable metric presence", False, 0))

    # 4. Regional or Metropolitan Search Radius Positioning (25 pts)
    # Matches geographic indicators (based in, location, city/province/country patterns, remote, hybrid, metro, area)
    has_location = bool(re.search(
        r"\b(based in|location:|located in|residing in|remote|hybrid|greater\s+[a-z]+|[a-zA-Z\s]+,\s*[a-zA-Z]{2,15}\b|metro\b|\barea\b|city\b|region\b|nationwide|worldwide)\b",
        content,
        re.IGNORECASE,
    ))
    if has_location:
        score += 25
        checks.append(("Geographic / metropolitan search anchor configured", True, 25))
    else:
        checks.append(("Geographic search anchor missing", False, 0))

    return {
        "spotlight_score": min(score, 100),
        "checks": checks,
    }


def verify_linkedin_profile(profile_path: str, domain_terms: List[Dict[str, str]] = None) -> Dict[str, Any]:
    """Runs complete verification suite on target profile file."""
    if not os.path.exists(profile_path):
        return {"error": f"Profile file not found at: {profile_path}", "passed": False}

    with open(profile_path, "r", encoding="utf-8") as f:
        content = f.read()

    # If domain_terms not provided explicitly, look for agent-generated domain_terms.json
    if domain_terms is None:
        cand_dir = os.path.dirname(os.path.abspath(profile_path))
        for cand_path in [os.path.join(cand_dir, "domain_terms.json"), "linkedin/domain_terms.json"]:
            if os.path.exists(cand_path):
                try:
                    with open(cand_path, "r", encoding="utf-8") as tf:
                        loaded = json.load(tf)
                        domain_terms = loaded if isinstance(loaded, list) else loaded.get("terms", [])
                    break
                except Exception:
                    pass

    h_audit = audit_headline(content)
    a_audit = audit_about(content)
    s_audit = audit_skills(content)
    p_audit = audit_acronym_pairing(content, domain_terms=domain_terms)
    r_audit = audit_spotlight_readiness(content)

    all_passed = (
        h_audit["pass_limit"]
        and a_audit["pass_limit"]
        and s_audit["skills_found_count"] >= 30
        and r_audit["spotlight_score"] >= 75
        and p_audit["passed"]
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
    print(f"[*] RECRUITER BOOLEAN ACRONYM PAIRS (AGENTIC DYNAMIC AUDIT):")
    if p.get("inline_discovered_count", 0) > 0:
        print(f"       [✓] {p['inline_discovered_count']} dynamic inline 'Full Term (ACRONYM)' pairings detected:")
        for full, acr in p["inline_pairs"][:8]:
            print(f"           • {full} ({acr})")
        if len(p["inline_pairs"]) > 8:
            print(f"           ... and {len(p['inline_pairs']) - 8} more.")
    if p.get("paired_acronyms"):
        text_matches = [a for a, reason in p["paired_acronyms"] if reason == "expanded phrase in text"]
        if text_matches:
            print(f"       [✓] {len(text_matches)} acronyms matched with expanded phrases in text: {', '.join(text_matches[:10])}")
    if p.get("agent_terms_checked", 0) > 0:
        print(f"       Agent-Generated Terms: {p['agent_terms_matched']} of {p['agent_terms_checked']} paired.")
        for detail in p["agent_terms_details"]:
            flag = "✓" if detail["both_present"] else "✗"
            advice = "" if detail["both_present"] else " (Add matching full-form/acronym for Boolean ATS)"
            print(f"           [{flag}] {detail['term']}{advice}")
    if p.get("unpaired_acronyms"):
        print(f"       [i] Note: {len(p['unpaired_acronyms'])} standalone acronyms without full phrase in text (optional ATS enrichment):")
        print(f"           {', '.join(p['unpaired_acronyms'][:8])}")
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
    parser.add_argument("--domain-terms", help="Optional path to JSON file with agent-generated domain terms")

    args = parser.parse_args()

    domain_terms = None
    if args.domain_terms:
        if os.path.exists(args.domain_terms):
            with open(args.domain_terms, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                domain_terms = loaded if isinstance(loaded, list) else loaded.get("terms", [])
        else:
            try:
                domain_terms = json.loads(args.domain_terms)
            except Exception:
                pass

    results = verify_linkedin_profile(args.profile_path, domain_terms=domain_terms)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print_report(results)

    if not results.get("all_passed"):
        sys.exit(1)


if __name__ == "__main__":
    main()
