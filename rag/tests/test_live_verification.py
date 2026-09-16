"""
Test live per-resume verification against Gemini NotebookLM (NO CACHE).
"""

import sys
import os

# Include parent directory in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from verification_engine import VerificationEngine
from bullet_generator import BulletGenerator


def test_live_verification():
    print("[*] Running live verification test against career evidence materials...")
    sample_requirements = """
    We are seeking a Junior Infrastructure Analyst with experience in:
    - Active Directory user provisioning and PowerShell automation
    - DHCP scope reservations and DNS records
    - Cisco switch VLANs and 802.1Q trunking configuration
    - Basic Linux storage management or system administration
    """
    engine = VerificationEngine()
    print("  [*] Sending targeted verification prompt to NotebookLM (live, no cache)...")
    res = engine.verify_job_requirements(
        target_role="Junior Infrastructure Analyst",
        requirements_or_job_text=sample_requirements,
    )

    answer = res.get("raw_answer", "")
    assert answer, "Failed: Received empty response from NotebookLM"
    print(f"  [PASS] Received response ({len(answer)} chars)")

    generator = BulletGenerator()
    latex_bullets = generator.synthesize_moderncv_bullets(answer)
    assert len(latex_bullets) > 0, "Failed: No LaTeX bullets generated"
    print(f"\n  [PASS] Generated {len(latex_bullets)} ModernCV LaTeX bullets")
    for b in latex_bullets:
        print("  ", b)

    pack = generator.generate_academic_evidence_pack("Junior Infrastructure Analyst", res)
    assert "# Academic Evidence Pack" in pack
    print("\n[+] test_live_verification PASSED successfully.")


if __name__ == "__main__":
    test_live_verification()
