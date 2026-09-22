"""Unit tests for tools/verify_linkedin.py."""

import json
import tempfile
from pathlib import Path
import pytest

from tools.verify_linkedin import (
    audit_headline,
    audit_about,
    audit_skills,
    extract_inline_acronym_pairs,
    check_acronym_initials_in_text,
    audit_acronym_pairing,
    audit_spotlight_readiness,
    verify_linkedin_profile,
)


def test_headline_audit():
    valid = "IT Systems Administrator Co-op | Active Directory, Linux, Cisco | 4.0 GPA Seneca"
    res = audit_headline(f"## 2. Headline\n```text\n{valid}\n```")
    assert res["pass_limit"] is True
    assert res["has_role_separator"] is True
    assert len(res["fold_preview"]) <= 70

    too_long = "X" * 250
    res_long = audit_headline(f"**Headline:** {too_long}")
    assert res_long["pass_limit"] is False


def test_about_audit():
    about_text = (
        "## About Section\n"
        "Computer Systems Technology student seeking a Winter 2027 Co-op work term.\n"
        "I specialize in enterprise directory services and Linux administration.\n"
        "Contact: candidate@example.com | Phone: 555-1234\n"
        + ("Additional career details and accomplishments.\n" * 5)
    )
    res = audit_about(about_text)
    assert res["pass_limit"] is True
    assert res["has_contact_info"] is True
    assert len(res["hook_preview"]) <= 300


def test_extract_inline_acronym_pairs():
    sample_text = (
        "Configured Active Directory Domain Services (AD DS) and Dynamic Host Configuration Protocol (DHCP). "
        "Strict adherence to Generally Accepted Accounting Principles (GAAP). "
        "Certified in Basic Life Support (BLS) and Pediatric Advanced Life Support (PALS). "
        "Measured Return on Investment (ROI) and Click-Through Rate (CTR)."
    )
    pairs = extract_inline_acronym_pairs(sample_text)
    pair_dict = {acr: full for full, acr in pairs}

    assert "AD DS" in pair_dict
    assert "DHCP" in pair_dict
    assert "GAAP" in pair_dict
    assert "BLS" in pair_dict
    assert "PALS" in pair_dict
    assert "ROI" in pair_dict
    assert "CTR" in pair_dict


def test_check_acronym_initials_in_text():
    text = "We deployed Virtual Local Area Networks across switches and monitored VLAN performance."
    assert check_acronym_initials_in_text("VLAN", text) is True
    assert check_acronym_initials_in_text("AWS", text) is False


def test_dynamic_agent_terms():
    content = "The candidate has experience with Amazon Web Services and holds an active AWS Solutions Architect badge."
    agent_terms = [{"full_term": "Amazon Web Services", "acronym": "AWS", "label": "AWS"}]
    res = audit_acronym_pairing(content, domain_terms=agent_terms)
    assert res["agent_terms_matched"] == 1
    assert res["passed"] is True


def test_spotlight_readiness_multi_sector():
    # Tech profile
    tech_profile = """
    ## Headline
    Systems Administrator Co-op / Intern | Linux, Azure, Cisco | Toronto, ON
    ## About
    Seeking Winter 2027 IT Co-op roles. Available for immediate placement.
    Automated 150+ user onboarding tasks, saving 12 hours weekly ($25k value).
    Contact: tech@example.com
    """
    tech_res = audit_spotlight_readiness(tech_profile)
    assert tech_res["spotlight_score"] >= 80

    # Finance profile
    finance_profile = """
    ## Headline
    Senior Financial Analyst | FP&A, Valuation & M&A | CPA | Greater Toronto Area
    ## About
    Senior Financial Analyst available for corporate finance opportunities.
    Managed $45M in assets, improving EBITDA by 14% and delivering 300+ financial forecast reports.
    Contact: finance@example.com
    """
    finance_res = audit_spotlight_readiness(finance_profile)
    assert finance_res["spotlight_score"] >= 80


def test_verify_linkedin_profile_end_to_end():
    profile_content = """# LinkedIn Profile Specification

## 2. Headline
```text
Systems Administrator Co-op / Intern | Active Directory (AD DS), Linux, Cisco | Seneca CTY 4.0 GPA
```

## 3. About Section
```text
Computer Systems Technology student seeking a Winter 2027 Co-op or Internship work term in IT Systems Administration.
Experienced in Active Directory Domain Services (AD DS), Dynamic Host Configuration Protocol (DHCP), and Virtual Local Area Networks (VLAN).
Automated 200+ user onboarding routines and deployed 5 production-grade homelab virtual machines with 99.9% uptime.
Based in Greater Toronto Area, Ontario.
Contact: student@example.com | +1 (647) 555-0199
```

## 50-Skill Taxonomy
### Top 3 Pinned
1. Active Directory
2. System Administration
3. Linux Server Administration

### Technical Skills
""" + "\n".join([f"- Skill Item {i}" for i in range(1, 35)])

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(profile_content)
        temp_path = f.name

    try:
        res = verify_linkedin_profile(temp_path)
        assert res["all_passed"] is True
        assert res["headline"]["pass_limit"] is True
        assert res["about"]["pass_limit"] is True
        assert res["skills"]["skills_found_count"] >= 30
        assert res["acronym_pairing"]["passed"] is True
        assert res["spotlight"]["spotlight_score"] >= 75
    finally:
        Path(temp_path).unlink(missing_ok=True)
