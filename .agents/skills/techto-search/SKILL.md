---
name: techto-search
description: >
  Use this skill to search for tech, IT, infrastructure, security, systems, and startup jobs
  on TechTO Jobs (jobs.techto.org), Canada's leading tech community job board centered in Toronto
  and across Canada. Covers Canadian tech companies, high-growth startups, and tech scaleups.
  Invoke for Toronto tech vacancies, Canadian startup hiring, and IT/systems/engineering roles.
  Trigger phrases: TechTO, TechTO jobs, Toronto tech jobs, Canadian tech startups, jobs.techto.org,
  search TechTO, tech jobs in Toronto, Toronto startup jobs.
version: 1.0.0
context: fork
allowed-tools:
  - Bash(bun run .agents/skills/techto-search/cli/src/cli.ts *)
---

# `techto-search` — TechTO Canadian Tech Job Board Search

Search open positions on **TechTO Jobs** (`jobs.techto.org`), the official job board of Canada's largest tech community connecting talent with Canadian tech innovators, high-growth startups, and enterprise tech employers.

## Commands

```bash
# Search jobs
bun run .agents/skills/techto-search/cli/src/cli.ts search -q "<query>" [options]

# View job details
bun run .agents/skills/techto-search/cli/src/cli.ts detail <id|url> [options]
```

## Search Flags

| Flag | Short | Description | Default |
|---|---|---|---|
| `--query` | `-q` | Keyword to search (role, skill, tech stack) | (required) |
| `--location` | `-l` | Location filter (e.g. `Toronto`, `Ontario`, `Remote`) | `""` |
| `--page` | `-p` | Page number (1-indexed) | `1` |
| `--limit` | | Maximum number of results to return | `20` |
| `--format` | `-f` | Output format: `json`, `table`, `plain` | `json` |

## Examples

```bash
# Search for IT and systems jobs in Toronto
bun run .agents/skills/techto-search/cli/src/cli.ts search -q "systems" -l "Toronto" --format table

# Search for security roles in Canada
bun run .agents/skills/techto-search/cli/src/cli.ts search -q "security" --format json

# Get detailed description of a TechTO posting
bun run .agents/skills/techto-search/cli/src/cli.ts detail 578956434 --format plain
```
