---
name: indeed-search
version: 1.0.0
description: >
  Use this skill to search for jobs on Indeed (indeed.ca / indeed.com).
  Covers every Canadian province and territory, the Greater Toronto Area (GTA),
  and international markets. Invoke for open positions, vacancies, and hiring in
  Canadian cities (Toronto, Newmarket, Markham, Mississauga, Ottawa, Vancouver, Montréal)
  or remotely. Trigger phrases: Indeed, Indeed Canada, jobs on Indeed, search Indeed,
  indeed.ca, find jobs on Indeed.
context: fork
enabled: true  # set to false to keep this portal installed but have /scrape skip it
allowed-tools: Bash(bun run .agents/skills/indeed-search/cli/src/cli.ts *)
---

# Indeed Search Skill

Search live job listings from **Indeed Canada** (`ca.indeed.com`) and Indeed global.
This skill uses the local Indeed MCP/JobSpy backend to bypass Cloudflare bot mitigation
safely, without requiring accounts, OAuth, or paid API keys.

Defaults to **Canada** (`ca.indeed.com`) and Toronto/GTA to match this candidate profile;
`--country` and `--location` switch to any other region.

## ⚠️ Etiquette and Personal Use Only

This skill uses browser TLS emulation to query public listings. Keep request volume low
(a handful of searches per run) to respect Indeed's infrastructure and avoid IP throttling.
Do not use for bulk harvesting or commercial scraping.

## When to use this skill

- Search job openings across Canada or globally by keyword and/or city
- Filter by posting recency (last 1, 3, 7, 14 days)
- Filter by remote workplace
- Get the full description, requirements, and salary for a specific job

## Commands

### Search job listings

```bash
bun run .agents/skills/indeed-search/cli/src/cli.ts search [flags]
```

Key flags:
- `--query <text>` / `-q <text>` — keywords (job title, skill, role).
- `--location <text>` / `-l <text>` — city or region (default `"Toronto, ON"`).
- `--country <cc>` — country code (default `canada`, also `usa`, `uk`).
- `--jobage <days>` — max age in days: `1`, `3`, `7`, `14` (default `14`).
- `--remote` — filter for remote positions.
- `--limit <n>` / `-n <n>` — cap total results returned (default `10`, max `30`).
- `--format json|table|plain` — default `json`.

### Fetch full job detail

```bash
bun run .agents/skills/indeed-search/cli/src/cli.ts detail <id|url> [--format json|plain]
```

`id|url` is an Indeed job ID (e.g. `in-0b7a690a2369b2ed` or `0b7a690a2369b2ed`) or a full Indeed `viewjob` URL.

## Usage examples

```bash
# Junior System Administrator roles in Toronto
bun run .agents/skills/indeed-search/cli/src/cli.ts search -q "Junior System Administrator" -l "Toronto, ON" --format table

# Cloud or Linux positions posted in the last 7 days
bun run .agents/skills/indeed-search/cli/src/cli.ts search -q "Cloud Linux" -l "York Region, ON" --jobage 7 --format table

# Remote IT Support roles
bun run .agents/skills/indeed-search/cli/src/cli.ts search -q "IT Support" --remote --format table

# Full detail for a specific posting
bun run .agents/skills/indeed-search/cli/src/cli.ts detail "https://ca.indeed.com/viewjob?jk=3cc5a0e9a92919c5" --format plain
```

## Output formats

| Format | Best for |
|--------|----------|
| `json` | Default — programmatic use, passing IDs to `detail` |
| `table` | Quick human-readable scanning |
| `plain` | Reading a single job's full description (`detail` command) |

All errors are written to **stderr** as `{ "error": "...", "code": "..." }` and the process exits with code `1`.
