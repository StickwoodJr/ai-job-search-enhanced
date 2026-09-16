---
name: cmd-scrape-indeed
description: >
  Dedicated job scraping workflow focused exclusively on Indeed Canada (indeed.ca).
  Discovers new postings, dedupes against tracker and seen jobs, fetches full details,
  evaluates profile fit, and generates referral outreach links. This is a cross-runtime
  pointer skill that delegates to .claude/commands/scrape-indeed.md. Triggers on:
  scrape indeed, indeed scrape, search indeed for postings, find indeed jobs,
  /scrape-indeed, indeed job search
context: fork
---

# /scrape-indeed — Dedicated Indeed Job Scraper (Cross-Runtime Pointer)

This skill delegates to the canonical `/scrape-indeed` command specification.

## Execution

1. Read `.claude/commands/scrape-indeed.md` and follow the workflow defined there.
2. The workflow executes the `indeed-search` CLI in `.agents/skills/indeed-search/cli/src/cli.ts` (or the `scripts/scrape_indeed.py` runner), and checks state in `job_scraper/seen_jobs.json` and `job_search_tracker.csv`.
3. Candidate fit is scored against the profile in `CLAUDE.md`.
4. Translate Claude Code tool names using `.agents/TOOL_GLOSSARY.md`.

## Key Tool Translations for This Workflow

- `Bash(bun run .agents/skills/indeed-search/cli/src/cli.ts ...)` → `run_command`
- `Bash(python scripts/scrape_indeed.py ...)` → `run_command`
- `Read` → `view_file`
- `Write` / `Edit` → `write_to_file` / `replace_file_content`

## Arguments

The user's message may include:
- A specific query focus (e.g. `"scrape indeed for Linux roles"` or `"scrape indeed co-op"`)
- `--broad` to run across all IT, Systems, Network, and Cloud categories
- `--jobage <days>` to filter by posting age (default: 14)
- `--limit <n>` max results per query (default: 10)
