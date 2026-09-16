# eluta-cli

CLI for searching jobs on Eluta.ca, a Canadian job search engine (the "Canada's Top
100 Employers" project).

**Data source**: Eluta.ca's public `/search` and `/spl/...` pages.
**Authentication**: None required.
**Dependencies**: None (plain `bun` + `fetch`). `bun install` is optional and only
pulls dev type defs.

## Installation

```bash
cd .agents/skills/eluta-search/cli
bun install   # optional — only installs TypeScript dev types
```

The CLI runs without any install because it has zero runtime dependencies.

## Commands

| Command | Description |
|---------|-------------|
| `search` | Search for job listings (`--query` and/or `--location` required) |
| `detail` | Fetch full detail for a single job listing |

`search` accepts `--format json|table|plain` (default `json`); `detail` accepts
`--format json|plain`. All errors are written to **stderr** as
`{ "error": "...", "code": "..." }` with exit code `1`.

## Quick examples

```bash
# AI product manager roles in Ottawa
bun run src/cli.ts search -q "AI product manager" -l "Ottawa, ON" --format table

# Data scientist roles in Toronto, last 7 days
bun run src/cli.ts search -q "data scientist" -l "Toronto, ON" --jobage 7 --format table

# Full detail for one job
bun run src/cli.ts detail 2ddd221fe7a3392c74d10d750a72929f --format plain
```

See `../SKILL.md` for the full flag reference and access-rules note.

## Search flags

| Flag | Alias | Description |
|------|-------|--------------|
| `--query` | `-q` | Keywords (title / skill / role). |
| `--location` | `-l` | Free-text city/region, e.g. `"Ottawa, ON"`. |
| `--jobage` | | Posted within N days — parsed from relative text client-side (see Notes in `SKILL.md`). |
| `--page` | | 1-indexed page (10 results/page). |
| `--limit` | `-n` | Cap results emitted. |
| `--format` | | `json` \| `table` \| `plain`. |

At least one of `--query`/`-q` or `--location`/`-l` is required.

## Tests

```bash
bun test                # offline fixture/mock suite
LIVE=1 bun test         # adds live smoke tests against eluta.ca
```
