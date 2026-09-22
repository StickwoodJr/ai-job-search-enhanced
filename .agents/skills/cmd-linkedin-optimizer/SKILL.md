---
name: cmd-linkedin-optimizer
description: >
  Evaluates, audits, and optimizes LinkedIn profiles for technical infrastructure, systems
  administration, and engineering roles. Utilizes a dual-agent (drafter-reviewer) model
  augmented with adaptable NotebookLM RAG retrieval (source-aware domain caching) and
  automated 2026 algorithmic linting. Defaults to reviewing existing profiles by auto-discovering
  the user's LinkedIn link, with full turnkey profile generation on demand. This is a
  cross-runtime pointer skill delegating to .claude/commands/linkedin-optimizer.md. Triggers on:
  linkedin-optimizer, /linkedin-optimizer, optimize linkedin, review linkedin, linkedin profile,
  audit linkedin, linkedin review
context: fork
---

# /linkedin-optimizer — Recruiter-Optimized LinkedIn Workflow (Cross-Runtime Pointer)

This skill delegates to the canonical `/linkedin-optimizer` workflow command specification.

## Execution

1. Read `.claude/commands/linkedin-optimizer.md` and follow the workflow defined there **exactly in order**.
2. **Review Mode by Default:**
   - In Step 0, look for the user's LinkedIn URL in `01-candidate-profile.md`, `CLAUDE.md`, and `resume_master.md`.
   - Default to Review & Enhancement Mode unless the user specifies `generate` or `from scratch`.
   - If no profile URL is found, ask the user whether they want to optimize an existing profile or generate a new one.
3. **Adaptive RAG Grounding:**
   - Step 1 executes the adaptive RAG hook:
     ```bash
     python3 "RAG Experiment/linkedin_rag_hook.py" --output "linkedin_evidence_pack.md"
     ```
   - Domain introspection is source-signature cached for speed; if NotebookLM sources change, the cache invalidates automatically.
4. **Algorithmic Verification:**
   - Step 5 verifies character limits, fold truncation, and recruiter spotlight readiness:
     ```bash
     python3 tools/verify_linkedin.py "LINKEDIN_PROFILE_MASTER.md"
     ```

## Key Tool Translations for This Workflow

- `WebFetch` → `read_url_content`
- `Agent` (reviewer agent) → `invoke_subagent` — pass draft and review content inline
- `Bash(python3 "RAG Experiment/linkedin_rag_hook.py" ...)` → `run_command`
- `Bash(python3 tools/verify_linkedin.py ...)` → `run_command`
- `Read` → `view_file`
- `Write` → `write_to_file`
- `Edit` → `replace_file_content`

## Important Rules

- **Strict RAG Connection Verification:** If `linkedin_rag_hook.py` fails because ExtendLM is offline, **halt immediately**. Do not silently fall back or proceed without informing the user and getting explicit authorization.
- **Zero Blind Spots:** Dynamic domain introspection adapts to academic, corporate, or project notebooks.

- **Factual Grounding:** All claims must be verified against `01-candidate-profile.md` and evidence packs.
- **Permanent Sync:** Stage newly verified facts back into `01-candidate-profile.md` in the same turn.
