---
name: cmd-setup
description: >
  Runs onboarding setup to collect candidate professional details and build
  profile files. Offers three paths: scan a documents folder, import a pasted CV,
  or walk through an interactive interview. This is a cross-runtime pointer skill
  that delegates to .claude/commands/setup.md. Triggers on: setup, set up profile,
  onboarding, configure profile, build profile, get started, initialize,
  set up my profile, run setup, set everything up for me, set up everything, set everything up
context: fork
---

# /setup — Profile Onboarding (Cross-Runtime Pointer)

This skill runs a **two-phase** setup. Both phases are required — do not stop after Phase 1.

## Phase 1: Environment Checks & Tool Installation

Run these commands in order and report results:

```bash
python3 tools/setup_wizard.py --doctor        # Check Python, Bun/npm, LaTeX, Git
python3 tools/setup_wizard.py --install       # Install all portal search CLIs
python3 tools/setup_wizard.py --test-latex jakes  # Smoke-test LaTeX compilation
```

After reporting a summary of the environment check, **immediately proceed to Phase 2 without waiting to be asked**.

## Phase 2: Profile Collection (Do Not Skip)

Read `.claude/commands/setup.md` and execute the full workflow defined there. This is where the candidate's personal information, career history, target roles, and search configuration are collected and written to profile files.

**Critical:** Do NOT stop after Phase 1 and list "next steps" for the user to do later. The profile conversation must happen now, as part of this single setup session.

1. Scan `documents/` first (use `list_dir` recursively).
   - If files are present → lead with **Path A** (document scan, recommended).
   - If empty → offer all three paths as described in `setup.md` Step 0.
2. Follow the chosen path through to Step 3 (file generation) and Step 4 (confirmation).
3. Only after all profile files are populated, present the final summary and suggest the first workflow to run (`/scrape-indeed`, `/apply`, etc.).

## Key Tool Translations for This Workflow

- `Glob` (scanning `documents/`) → use `list_dir` recursively + `grep_search`
- `Read` → `view_file`
- `Write` / `Edit` → `write_to_file` / `replace_file_content`
- `AskUserQuestion` → output your question as text and wait for the user's reply

## Arguments

The user's message may include context about which setup path to take:
- Mentioning "documents" or "folder" → Path A (scan documents/)
- Pasting a CV or mentioning "CV" → Path B (import pasted CV)
- No specific path → scan `documents/` and auto-select as described above

In Claude Code, user input arrives via `$ARGUMENTS`. In other runtimes,
extract the equivalent from the user's conversational message.
