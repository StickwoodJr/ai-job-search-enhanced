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

# Universal Multi-Industry Acronym Dictionary for Boolean ATS Indexing
# Covers Technology, Cloud, Finance, Healthcare, Marketing, Operations & Compliance
MULTI_INDUSTRY_ACRONYM_PAIRS = [
    # Systems, Cloud & Infrastructure
    (r"\bActive Directory\b", r"\b(AD|AD DS)\b", "Active Directory / AD DS"),
    (r"\bGroup Policy\b", r"\b(GPO|GPOs)\b", "Group Policy / GPOs"),
    (r"\bDynamic Host Configuration Protocol\b", r"\bDHCP\b", "Dynamic Host Configuration Protocol / DHCP"),
    (r"\bDomain Name System\b", r"\bDNS\b", "Domain Name System / DNS"),
    (r"\bVirtual Local Area Network(s)?\b", r"\bVLAN(s)?\b", "Virtual Local Area Network / VLANs"),
    (r"\bZone-Based Policy Firewall(s)?\b", r"\bZFW\b", "Zone-Based Policy Firewall / ZFW"),
    (r"\bNetwork Address Translation\b", r"\bNAT\b", "Network Address Translation / NAT"),
    (r"\bAccess Control List(s)?\b", r"\bACLs?\b", "Access Control Lists / ACLs"),
    (r"\bArchitecture Decision Record(s)?\b", r"\bADR(s)?\b", "Architecture Decision Records / ADRs"),
    # Software Engineering & Cloud Architecture
    (r"\bApplication Programming Interface(s)?\b", r"\bAPI(s)?\b", "Application Programming Interface / APIs"),
    (r"\bContinuous Integration\b", r"\bCI\b", "Continuous Integration / CI"),
    (r"\bContinuous Deployment\b", r"\bCD\b", "Continuous Deployment / CD"),
    (r"\bAmazon Web Services\b", r"\bAWS\b", "Amazon Web Services / AWS"),
    (r"\bSoftware Development Life Cycle\b", r"\bSDLC\b", "Software Development Life Cycle / SDLC"),
    (r"\bSingle Sign-On\b", r"\bSSO\b", "Single Sign-On / SSO"),
    (r"\bRetrieval-Augmented Generation\b", r"\bRAG\b", "Retrieval-Augmented Generation / RAG"),
    (r"\bLarge Language Model(s)?\b", r"\bLLM(s)?\b", "Large Language Models / LLMs"),
    # Finance, Accounting & Business
    (r"\bGenerally Accepted Accounting Principles\b", r"\bGAAP\b", "Generally Accepted Accounting Principles / GAAP"),
    (r"\bEarnings Before Interest, Taxes, Depreciation, and Amortization\b", r"\bEBITDA\b", "EBITDA"),
    (r"\bReturn on Investment\b", r"\bROI\b", "Return on Investment / ROI"),
    (r"\bDiscounted Cash Flow\b", r"\bDCF\b", "Discounted Cash Flow / DCF"),
    (r"\bCertified Public Accountant\b", r"\bCPA\b", "Certified Public Accountant / CPA"),
    (r"\bFinancial Planning and Analysis\b", r"\bFP&A\b", "Financial Planning and Analysis / FP&A"),
    # Healthcare, Clinical & Life Sciences
    (r"\bElectronic Medical Record(s)?\b", r"\bEMR(s)?\b", "Electronic Medical Records / EMRs"),
    (r"\bElectronic Health Record(s)?\b", r"\bEHR(s)?\b", "Electronic Health Records / EHRs"),
    (r"\bHealth Insurance Portability and Accountability Act\b", r"\bHIPAA\b", "HIPAA"),
    (r"\bBasic Life Support\b", r"\bBLS\b", "Basic Life Support / BLS"),
    (r"\bAdvanced Cardiovascular Life Support\b", r"\bACLS(?!s)\b", "Advanced Cardiovascular Life Support / ACLS"),
    # Marketing, Sales & Product
    (r"\bSearch Engine Optimization\b", r"\bSEO\b", "Search Engine Optimization / SEO"),
    (r"\bClick-Through Rate\b", r"\bCTR\b", "Click-Through Rate / CTR"),
    (r"\bCost Per Click\b", r"\bCPC\b", "Cost Per Click / CPC"),
    (r"\bCustomer Relationship Management\b", r"\bCRM\b", "Customer Relationship Management / CRM"),
    (r"\bCost Per Acquisition\b", r"\bCPA\b", "Cost Per Acquisition / CPA"),
    # Operations, Project Management & Compliance
    (r"\bProject Management Professional\b", r"\bPMP\b", "Project Management Professional / PMP"),
    (r"\bKey Performance Indicator(s)?\b", r"\bKPI(s)?\b", "Key Performance Indicators / KPIs"),
    (r"\bService Level Agreement(s)?\b", r"\bSLA(s)?\b", "Service Level Agreement / SLAs"),
    (r"\bObjectives and Key Results\b", r"\bOKRs?\b", "Objectives and Key Results / OKRs"),
    (r"\bStatement of Work\b", r"\bSOW\b", "Statement of Work / SOW"),
    (r"\bAnti-Money Laundering\b", r"\bAML\b", "Anti-Money Laundering / AML"),
    (r"\bKnow Your Customer\b", r"\bKYC\b", "Know Your Customer / KYC"),
    (r"\bGeneral Data Protection Regulation\b", r"\bGDPR\b", "General Data Protection Regulation / GDPR"),
]

# Legacy alias for backward compatibility
ACRONYM_PAIRS = MULTI_INDUSTRY_ACRONYM_PAIRS



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
    """
    Verifies that both acronyms and full terms appear to maximize Boolean search hits across any domain.
    1. Detects inline paired definitions: 'Full Term (ACRONYM)'.
    2. Cross-references against multi-industry dictionary of standard domain pairs.
    """
    inline_raw = re.findall(r"\b([A-Za-z][A-Za-z0-9\s\-/]{2,45})\s+\(([A-Z0-9]{2,8})\)", content)
    # Deduplicate inline pairs
    seen_inline = set()
    inline_pairs = []
    for term, acr in inline_raw:
        pair_key = (term.strip().lower(), acr.strip().upper())
        if pair_key not in seen_inline:
            seen_inline.add(pair_key)
            inline_pairs.append((term.strip(), acr.strip()))

    pair_results = []
    matched_count = 0
    relevant_terms = 0

    # Check multi-industry catalog for terms relevant to this candidate
    for full_regex, acr_regex, label in MULTI_INDUSTRY_ACRONYM_PAIRS:
        has_full = bool(re.search(full_regex, content, re.IGNORECASE))
        has_acr = bool(re.search(acr_regex, content)) or (bool(re.search(acr_regex, content, re.IGNORECASE)) and "ACLS" not in acr_regex)

        # Only evaluate pairs where the candidate actually works in that area (at least one term mentioned)
        if has_full or has_acr:
            relevant_terms += 1
            passed = has_full and has_acr
            if passed:
                matched_count += 1
            pair_results.append({
                "term": label,
                "has_full_term": has_full,
                "has_acronym": has_acr,
                "both_present": passed,
            })

    total_verified = max(matched_count, len(inline_pairs))

    return {
        "matched_pairs": matched_count,
        "total_checked": relevant_terms,
        "inline_discovered_count": len(inline_pairs),
        "inline_pairs": inline_pairs[:10],
        "total_verified_pairs": total_verified,
        "details": pair_results,
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
        r"\b(open to work|available for|seeking|immediate availability|open to opportunities|work term|available [a-z]+)\b",
        content,
        re.IGNORECASE,
    ))
    if has_avail:
        score += 25
        checks.append(("Availability / Open to Work signal present", True, 25))
    else:
        checks.append(("Availability / Open to Work signal missing", False, 0))

    # 2. Target Role & Seniority Anchoring (25 pts)
    # Supports both early-career dual terms (Co-op/Internship) and professional roles (Engineer, Manager, Analyst, Specialist, etc.)
    has_coop = bool(re.search(r"\bco-?op\b", content, re.IGNORECASE))
    has_intern = bool(re.search(r"\bintern(ship)?\b", content, re.IGNORECASE))
    has_role_title = bool(re.search(
        r"\b(engineer|administrator|analyst|specialist|developer|manager|director|lead|consultant|technician|nurse|architect|coordinator|scientist|officer|practitioner|accountant|strategist)\b",
        content,
        re.IGNORECASE,
    ))

    if (has_coop and has_intern) or (has_role_title and (has_coop or has_intern or "senior" in content.lower() or "lead" in content.lower() or "specialist" in content.lower() or "analyst" in content.lower() or "engineer" in content.lower())):
        score += 25
        if has_coop and has_intern:
            checks.append(("Target role & dual 'Co-op'/'Internship' terminology aligned", True, 25))
        else:
            checks.append(("Target role & professional seniority positioning defined", True, 25))
    elif has_role_title or has_coop or has_intern:
        score += 15
        checks.append(("Target role keywords present (partial seniority alignment)", True, 15))
    else:
        checks.append(("Target role & seniority positioning missing", False, 0))

    # 3. Quantified metrics in experience & projects (25 pts)
    # Matches currency ($), percentages (%), counts/volumes (10+, 100k, 4.0 GPA, numbers)
    metrics = re.findall(r"(\$[\d,]+(?:\.\d+)?|\b\d+%\b|\b\d+\+\b|\b\d+(?:k|M|B)\b|\b\d{2,}\b|\b\d\.\d\b)", content)
    if len(metrics) >= 4:
        score += 25
        checks.append((f"High metric density ({len(metrics)} quantifiable markers found)", True, 25))
    elif len(metrics) >= 2:
        score += 15
        checks.append((f"Moderate metric density ({len(metrics)} markers found)", True, 15))
    else:
        checks.append(("Low quantifiable metric presence", False, 0))

    # 4. Regional or Metropolitan Search Radius Positioning (25 pts)
    # Matches metropolitan areas, cities, provinces/states, countries, or Remote/Hybrid
    has_location = bool(re.search(
        r"\b(based in|location:|greater\s+[a-z]+|[a-z]+,\s*[a-z]{2}\b|remote|hybrid|metro|gta|area|toronto|new\s*york|chicago|london|vancouver|montreal|ottawa|calgary|seattle|san\s*francisco|boston|austin|berlin|copenhagen|denmark|ontario|california|texas|alberta|quebec|british\s*columbia)\b",
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
    if p.get("total_checked", 0) > 0:
        print(f"       {p['matched_pairs']} of {p['total_checked']} domain terms have both full-form and acronym present.")
        for detail in p["details"]:
            flag = "✓" if detail["both_present"] else "✗"
            advice = "" if detail["both_present"] else " (Add matching full-form/acronym for Boolean ATS)"
            print(f"       [{flag}] {detail['term']}{advice}")
    if p.get("inline_discovered_count", 0) > 0:
        print(f"       [✓] {p['inline_discovered_count']} inline 'Full Term (ACRONYM)' pairings detected.")
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
