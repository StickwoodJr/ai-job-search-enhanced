"""
Source Catalog and Evidence Mapping for Personal Knowledge RAG.

Indexes and categorizes documents in the candidate's NotebookLM knowledge base into:
- Certifications: Professional credentials, vendor certifications, exam completions
- Projects: Personal projects, open-source repositories, architectural designs
- Coursework: Syllabi, academic coursework, lab reports, transcripts
- Experience: Past resumes, performance reviews, achievements
- References: Letters of recommendation, testimonials
"""

from typing import Dict, List, Any, Optional

CATEGORY_KEYWORDS = {
    "Certifications": [
        "cert", "certification", "credential", "license", "badge", "aws",
        "azure", "comptia", "cisco", "ccna", "gcp", "pmp", "cissp", "ceh"
    ],
    "Projects": [
        "project", "repo", "github", "application", "homelab", "code",
        "design", "portfolio", "capstone", "implementation", "architecture"
    ],
    "Coursework": [
        "course", "syllabus", "lab", "assignment", "lecture", "homework",
        "semester", "exam", "quiz", "polytechnic", "university", "college", "diploma", "degree"
    ],
    "Experience": [
        "resume", "cv", "experience", "review", "performance", "achievement",
        "appraisal", "work history", "job"
    ],
    "References": [
        "reference", "recommendation", "letter", "testimonial", "eval"
    ]
}


def classify_source(title: str) -> str:
    """Assigns a broad category to a source document title based on keywords."""
    t_lower = title.lower()

    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in t_lower for kw in keywords):
            return category

    return "General Evidence"


class SourceCatalog:
    """Represents the indexed collection of sources in a candidate's notebook."""

    def __init__(self, raw_sources: List[Dict[str, Any]]):
        self.raw_sources = raw_sources
        self.by_category: Dict[str, List[Dict[str, Any]]] = {}
        self.by_course: Dict[str, List[Dict[str, Any]]] = {}
        self._index()

    def _index(self):
        for s in self.raw_sources:
            title = s.get("title") or s.get("name") or "Untitled Document"
            cat = classify_source(title)
            self.by_category.setdefault(cat, []).append(s)
            self.by_course.setdefault(cat, []).append(s)

    def get_sources_for_category(self, category: str) -> List[Dict[str, Any]]:
        return self.by_category.get(category, [])

    def get_source_ids_for_courses(self, categories_or_courses: List[str]) -> List[str]:
        source_ids = []
        for cat in categories_or_courses:
            for item in self.by_category.get(cat, []):
                sid = item.get("id") or item.get("source_id")
                if sid:
                    source_ids.append(sid)
        return source_ids
