# talent-com-cli

CLI for searching jobs on Talent.com's public job listings — Canada by default
(`ca.talent.com`), any other Talent.com country market via `--country`.

**Data source**: Talent.com's public, server-rendered `/jobs` (search) and `/view`
(detail) pages.
**Authentication**: None required.
**Dependencies**: None (plain `bun` + `fetch`). `bun install` is optional and only
pulls dev type defs.

## Installation

```bash
cd .agents/skills/talent-com-search/cli
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

# French-language search
bun run src/cli.ts search -q "gestionnaire de produits" --lang fr -l Ottawa --format table

# Full detail for one job
bun run src/cli.ts detail 604692603372315399 --format plain
```

See `../SKILL.md` for the full flag reference and access-rules note.

## Search flags

| Flag | Alias | Description |
|------|-------|--------------|
| `--query` | `-q` | Keywords (title / skill / role). |
| `--location` | `-l` | Free-text city/region, e.g. `"Ottawa, ON"`. |
| `--country` | | Talent.com country subdomain. Default `ca`. |
| `--lang` | | `en` \| `fr`. Default `en`. |
| `--jobage` | | Posted within N days — filtered client-side (see Notes in `SKILL.md`). |
| `--page` | | 1-indexed page (~20 results/page). |
| `--limit` | `-n` | Cap results emitted. |
| `--format` | | `json` \| `table` \| `plain`. |

At least one of `--query`/`-q` or `--location`/`-l` is required.

## Tests

```bash
bun test                # offline fixture/mock suite
LIVE=1 bun test         # adds live smoke tests against ca.talent.com
```
