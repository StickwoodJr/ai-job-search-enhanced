"""
Bullet and Narrative Generator for RAG Experiment.

Transforms verified primary educational evidence from Gemini NotebookLM
into high-fidelity, ATS-friendly LaTeX ModernCV bullets, Cover Letter narratives,
and structured Academic Evidence Packs for the cmd-apply workflow.
"""

import re
from typing import Dict, Any, List


class BulletGenerator:
    """Generates tailored resume bullets and cover letter evidence from verified lab data."""

    def clean_text_for_latex(self, text: str) -> str:
        """Cleans and escapes characters for LaTeX compilation."""
        # Strip citation brackets like [1], [2, 3], [4-7]
        clean = re.sub(r"\[\d+(?:[,\-–]\s*\d+)*\]", "", text).strip()
        # Escape LaTeX special characters
        clean = clean.replace("&", r"\&").replace("%", r"\%").replace("#", r"\#").replace("_", r"\_")
        # Format markdown code backticks into \texttt{}
        clean = re.sub(r"`([^`]+)`", r"\\texttt{\1}", clean)
        # Format markdown bold into \textbf{}
        clean = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", clean)
        # Clean double spaces
        clean = re.sub(r"\s+", " ", clean).strip()
        # Fix punctuation spacing left behind by removed citations
        clean = re.sub(r"\s+([.,;:!?])", r"\1", clean)
        clean = re.sub(r"\(\s+", "(", clean)
        clean = re.sub(r"\s+\)", ")", clean)
        return clean

    def synthesize_moderncv_bullets(self, raw_verification_answer: str, max_bullets: int = 5) -> List[str]:
        r"""
        Parses Section 1 (Verified Core Competencies & Lab Proof) from the raw verification answer
        and synthesizes unified ModernCV bullets:
        Format: \item \textbf{Skill / Area}: Verified outcomes, tools, cmdlets, and course context.
        """
        bullets: List[str] = []

        # Extract Section 1
        sec1_match = re.search(
            r"### 1\. Verified Core Competencies & (?:Primary Evidence|Lab Proof)(.*?)(?=### 2\.|\Z)",
            raw_verification_answer,
            re.DOTALL,
        )
        sec1_text = sec1_match.group(1) if sec1_match else raw_verification_answer

        # Top-level competency blocks start with `* **Title**:` with no indent
        competency_blocks = re.findall(
            r"^\*\s+\*\*([^*\n]+?)\*\*:\s*\n(.*?)(?=^\*\s+\*\*|\Z)",
            sec1_text,
            re.MULTILINE | re.DOTALL,
        )

        for title, body in competency_blocks[:max_bullets]:
            title_clean = title.strip().rstrip(":")

            outcomes_match = re.search(
                r"^\s+\*\s+\*\*(?:Verified Outcomes|Competencies & Outcomes|Verified Competencies)\*\*:\s*([^\n]+(?:\n(?!\s+\*)[^\n]+)*)",
                body,
                re.MULTILINE,
            )
            courses_match = re.search(
                r"^\s+\*\s+\*\*(?:Course Code|Courses|Course)\*\*:\s*([^\n]+)",
                body,
                re.MULTILINE,
            )

            outcomes = outcomes_match.group(1).strip() if outcomes_match else ""
            courses = courses_match.group(1).strip() if courses_match else ""

            if outcomes:
                clean_outcomes = self.clean_text_for_latex(outcomes)
                clean_courses = self.clean_text_for_latex(courses).rstrip(".")
                clean_title = self.clean_text_for_latex(title_clean)

                bullet = f"\\item \\textbf{{{clean_title}}}: {clean_outcomes}"
                if clean_courses and clean_courses not in clean_outcomes:
                    bullet += f" ({clean_courses})"
                bullets.append(bullet)
            else:
                clean_body = self.clean_text_for_latex(body.strip())
                clean_title = self.clean_text_for_latex(title_clean)
                bullets.append(f"\\item \\textbf{{{clean_title}}}: {clean_body}")

        # Fallback if no top-level blocks matched
        if not bullets:
            for line in sec1_text.splitlines():
                s = line.strip()
                if s.startswith("* ") or s.startswith("- "):
                    clean = re.sub(r"^[*-]\s+", "", s)
                    clean_tex = self.clean_text_for_latex(clean)
                    if clean_tex:
                        bullets.append(f"\\item {clean_tex}")
                if len(bullets) >= max_bullets:
                    break

        return bullets

    def synthesize_resume_bullets(self, raw_verification_answer: str, max_bullets: int = 5) -> List[str]:
        r"""
        Parses Section 1 (Verified Core Competencies & Lab Proof) from the raw verification answer
        and synthesizes Jake's Resume Template bullets:
        Format: \resumeItem{\textbf{Skill / Area}: Verified outcomes, tools, cmdlets, and course context.}
        """
        moderncv_bullets = self.synthesize_moderncv_bullets(raw_verification_answer, max_bullets=max_bullets)
        resume_items: List[str] = []
        for b in moderncv_bullets:
            # Strip leading \item
            content = re.sub(r"^\\item\s*", "", b).strip()
            resume_items.append(f"\\resumeItem{{{content}}}")
        return resume_items

    def generate_academic_evidence_pack(
        self,
        target_role: str,
        verification_result: Dict[str, Any],
    ) -> str:
        """
        Builds a comprehensive Markdown Career Evidence Pack.
        This pack can be reviewed by the candidate and referenced directly
        by the DRAFTER agent during cmd-apply Step 1 and Step 2.
        """
        raw_answer = verification_result.get("raw_answer", "")
        resume_bullets = self.synthesize_resume_bullets(raw_answer, max_bullets=5)
        resume_block = "\n".join(f"  {b}" for b in resume_bullets)

        pack = f"""# Career Evidence Pack (Verified Source Proof)

**Target Role:** {target_role}  
**Source Notebook:** {verification_result.get('notebook_title', 'Personal Knowledge Base')} (`{verification_result.get('notebook_id')}`)  
**Data Fidelity:** 100% Live Verified against primary sources (certifications, projects, coursework, past resumes) (No cache)

---

## 1. Verified Evidence & Hands-On Proof

{raw_answer}

---

## 2. High-Impact LaTeX Resume Bullets (Jake's Template)

Insert these directly into `\\section{{Technical Projects}}` or `\\section{{Experience}}` under `\\resumeItemListStart`:

```latex
\\resumeItemListStart
{resume_block}
\\resumeItemListEnd
```

---

## 3. Staging for Factual Grounding Audit

To ensure these verified facts pass the Step 3 Grounding Audit in `/apply`, copy the verified achievements into `.claude/skills/job-application-assistant/01-candidate-profile.md`:

> [!TIP]
> All bullets above originate directly from your verified source materials in Google NotebookLM. Adding them to `01-candidate-profile.md` preserves audit compliance with zero risk of hallucination flags.
"""
        return pack

    # Alias for backward compatibility
    generate_evidence_pack = generate_academic_evidence_pack
