---
name: cmd-indeed-swarm-scraper
description: >
  Dedicated multi-sector Indeed Canada swarm scraper workflow. Partitions
  search operations across 3 specialized sector agents (Systems & Hardware,
  Networking & NOC, Cloud & Cyber) with atomic deduplication, curriculum filtering,
  and automatic tracker and dashboard rebuilding. This is a cross-runtime pointer
  skill delegating to .claude/commands/indeed-swarm-scraper.md. Triggers on:
  indeed swarm scraper, /indeed-swarm-scraper, swarm scrape indeed, indeed-swarm-scraper
context: fork
---

# /indeed-swarm-scraper — Multi-Sector Indeed Canada Swarm Scraper

This skill delegates to the canonical `/indeed-swarm-scraper` command specification.

## Execution

1. Read `.claude/commands/indeed-swarm-scraper.md` and follow the workflow defined there.
2. The workflow executes `scripts/scrape_indeed_swarm.py` (or launches the 3 dedicated sector daemons via `scripts/scrape_indeed_sector_daemon.py`).
3. Translates Claude Code tool names using `.agents/TOOL_GLOSSARY.md`.

## Key Tool Translations
- `Bash(python3 scripts/scrape_indeed_swarm.py ...)` → `run_command`
- `Bash(python3 scripts/scrape_indeed_sector_daemon.py ...)` → `run_command`
- `Read` → `view_file`
- `Write` / `Edit` → `write_to_file` / `replace_file_content`

## Arguments
- `--interval <seconds>`: Polling loop interval per sector (default: 120)
- `--from-date <YYYY-MM-DD>`: Starting date for posting window (e.g. `2026-09-01`)
- `--hours-old <hours>`: Max posting age in hours (default: 336)
- `--duration <seconds>`: Execution duration in seconds (e.g. `1200` for 20 minutes)
