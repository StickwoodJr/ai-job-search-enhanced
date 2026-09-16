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
        Demands exact lab titles, commands, protocols, and environments.
        """
        prompt = f"""You are an elite Technical Systems Auditor reviewing the attached primary student coursework materials, lab submissions, PowerPoint decks, and practical assignments from Seneca Polytechnic's Computer Systems Technology (CTYC) curriculum.

The candidate is preparing an individual application for the following role:
TARGET ROLE: {target_role}

TECHNICAL REQUIREMENTS / JOB DESCRIPTION:
{requirements_or_job_text}

INSTRUCTIONS FOR AUDITING & VERIFICATION:
1. Grounding Rule: Rely ONLY on the attached source materials. If a skill, tool, or protocol is NOT explicitly mentioned or practiced in the sources, state clearly that it is not covered. DO NOT infer or assume tools that are not documented.
2. For each requirement from the job that is supported by the course materials:
   - Identify the exact Course Code (e.g., OPS145, OPS245, MST100, MST200, CSN115, CSN205, SEC220).
   - Identify the specific Lab, Assignment, or Project name (e.g., "Lab 8 - Creating Users with PS", "CSN205 Assignment 2 OSPFv2", "wk10p1.txt").
   - List the exact CLI commands, PowerShell cmdlets, configuration parameters, or protocols executed (e.g., `New-ADUser`, `Add-Computer`, 802.1Q trunking, single-area OSPFv2, systemd service units, LVM).
   - Detail the execution environment (e.g., Physical Cisco rack, Packet Tracer, Azure DevTest Labs, local virtual machine, CentOS/RHEL, Windows Server 2022).
3. Identify any clear gaps (technologies demanded by the job that are absent in these semesters).

Format your response strictly under these headers:
### 1. Verified Core Competencies & Lab Proof
(Bullet points linking each job requirement to specific course labs, environments, and outcomes)

### 2. Concrete Commands, Cmdlets & Configuration Syntax Executed
(Bullet points listing specific CLI commands, scripts, or configuration commands Golden ran in labs)

### 3. Practical Infrastructure & Platforms Used
(Details on whether work was done on physical hardware, virtualized topologies, or cloud environments)

### 4. Identified Curriculum Gaps
(List of required skills from the job description that do not appear in Semesters 1 and 2 materials)
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
