"""
Verification Engine for RAG Experiment.

Executes live, per-resume / per-job verification queries against Gemini NotebookLM
using ExtendLM. Performs ZERO CACHING to guarantee absolute data fidelity,
freshness, and strict factual grounding against primary student coursework.
"""

from typing import Dict, Any, List, Optional
try:
    from .config import DEFAULT_NOTEBOOK_ID
    from .extendlm_bridge import ExtendLMBridge
    from .source_catalog import SourceCatalog
except ImportError:
    from config import DEFAULT_NOTEBOOK_ID
    from extendlm_bridge import ExtendLMBridge
    from source_catalog import SourceCatalog


class VerificationEngine:
    """Performs live curriculum verification for individual job specs and resumes."""

    def __init__(self, notebook_id: str = DEFAULT_NOTEBOOK_ID, bridge: Optional[ExtendLMBridge] = None):
        self.notebook_id = notebook_id
        self.bridge = bridge or ExtendLMBridge()
        self._catalog: Optional[SourceCatalog] = None

    def get_catalog(self) -> SourceCatalog:
        """Retrieves and caches the source catalog in memory for the current session."""
        if not self._catalog:
            sources = self.bridge.list_sources(self.notebook_id)
            self._catalog = SourceCatalog(sources)
        return self._catalog

    def build_verification_prompt(self, target_role: str, requirements_or_job_text: str) -> str:
        """
        Constructs a rigorous, factual verification prompt for NotebookLM.
        Audits claims against candidate source materials (certs, projects, coursework, past resumes).
        """
        prompt = f"""You are an objective Career Evidence & Verification Auditor reviewing the attached primary source documents (certifications, personal project write-ups, past resumes, code repositories, coursework, lab reports, performance reviews, or reference letters).

The candidate is preparing an application for the following role:
TARGET ROLE: {target_role}

TECHNICAL REQUIREMENTS / JOB DESCRIPTION:
{requirements_or_job_text}

INSTRUCTIONS FOR AUDITING & VERIFICATION:
1. Grounding Rule: Rely ONLY on the attached source materials. If a skill, tool, certification, or project is NOT explicitly mentioned or documented in the sources, state clearly that it is not covered. DO NOT infer or assume background that is not documented.
2. For each requirement from the job that is supported by the attached materials:
   - Identify the specific source document (e.g. certification title, project name, past role, course/lab module).
   - Extract verified outcomes, concrete tools/technologies used, metrics achieved, or responsibilities held.
   - List specific artifacts, technical syntax, frameworks, or platforms demonstrated in the sources.
3. Identify any clear gaps (requirements demanded by the job that are absent in the attached sources).

Format your response strictly under these headers:
### 1. Verified Core Competencies & Primary Evidence
(Bullet points linking each job requirement to specific sources, projects, certs, or outcomes)

### 2. Concrete Tools, Technologies & Work Products
(Bullet points listing specific tools, frameworks, languages, commands, or project deliverables verified in the sources)

### 3. Execution Context & Environments
(Details on whether work was completed in production, personal projects, enterprise environments, or coursework)

### 4. Identified Skill Gaps
(List of required skills from the job description that do not appear in the candidate's source documents)
"""
        return prompt

    def verify_job_requirements(
        self,
        target_role: str,
        requirements_or_job_text: str,
        isolate_courses: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Executes a live verification query against the notebook.
        NO CACHING is performed; every run executes against Gemini NotebookLM directly.
        """
        source_ids = None
        if isolate_courses:
            catalog = self.get_catalog()
            source_ids = catalog.get_source_ids_for_courses(isolate_courses)

        prompt = self.build_verification_prompt(target_role, requirements_or_job_text)
        raw_answer = self.bridge.ask_notebook(
            notebook_id=self.notebook_id,
            question=prompt,
            source_ids=source_ids,
        )

        return {
            "target_role": target_role,
            "notebook_id": self.notebook_id,
            "isolated_courses": isolate_courses,
            "verification_prompt": prompt,
            "raw_answer": raw_answer,
        }

    def verify_skills_list(self, skills: List[str], target_role: str = "IT Infrastructure Specialist") -> Dict[str, Any]:
        """Convenience method to verify a discrete list of technical skills."""
        joined_skills = "\n".join(f"- {s}" for s in skills)
        return self.verify_job_requirements(target_role, joined_skills)
