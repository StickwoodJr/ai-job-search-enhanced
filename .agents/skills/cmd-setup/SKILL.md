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

After reporting a summary of the environment check, the agent MUST immediately transition into profile setup. The correct next action is:

1. Use `list_dir` on `documents/` to see if the user has dropped any files there.
2. Then say something like:

   > "Environment is all set ✅. Now let's build your candidate profile — this is what personalizes every resume and cover letter the agent writes for you.
   >
   > I can see [N files / no files] in your `documents/` folder.
   > [If files exist:] I'll read those now and use them to build your profile — this is the recommended path.
   > [If empty:] No documents yet, no problem. I can either walk you through a quick interview to capture your background, or you can paste your CV directly here."

3. Then immediately begin the profile collection workflow from `.claude/commands/setup.md` Step 0, picking the right path automatically based on what's in `documents/`.

**This transition is not optional and does not require the user to ask again.** Do NOT list "next steps" and stop. Do NOT say "ask me to set up my profile later." Continue the conversation now.

## Phase 2: Profile Collection

Read `.claude/commands/setup.md` and execute the full workflow. This collects the candidate's personal information, career history, target roles, search configuration, swarm sector setup, and RAG notebook connection — all in one session.

1. Scan `documents/` first (`list_dir` recursively).
   - Files present → lead with **Path A** (document scan).
   - Empty → offer all three paths (A / B / C) as in `setup.md` Step 0.
2. Follow the chosen path through Step 3 (file generation) and Step 4 (confirmation).
3. Only after profile files are fully written, present the final "Setup complete!" summary and suggest first workflows.

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
