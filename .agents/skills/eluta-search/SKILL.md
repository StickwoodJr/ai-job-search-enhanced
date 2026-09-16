---
name: eluta-search
version: 1.0.0
description: >
  Use this skill to search for jobs on Eluta.ca, a Canadian job search engine
  known for the "Canada's Top 100 Employers" project. Covers every province
  and territory and every sector. Invoke for open positions, vacancies, and
  hiring in Canadian cities (Ottawa, Toronto, Vancouver, Montréal, Calgary,
  Kanata, Nepean, Oakville, Markham). Trigger phrases: Eluta, Eluta.ca, jobs
  on Eluta, Top 100 Employers, search Eluta, Canadian job search engine.
context: fork
enabled: true  # set to false to keep this portal installed but have /scrape skip it
allowed-tools: Bash(bun run .agents/skills/eluta-search/cli/src/cli.ts *)
---

# Eluta.ca Search Skill

Search live job listings from **Eluta.ca**, a Canadian job search engine that indexes
postings from employer career sites and applicant tracking systems, and runs the
"Canada's Top 100 Employers" project. No authentication, no API key, and **zero
runtime dependencies** — it runs with just `bun`.

## Access and etiquette

`eluta.ca/robots.txt` disallows `/search/` (with a trailing slash), `/cache?`,
`/cache/`, `/asp/`, `/static/`, `/system/`, and a few other paths. **This skill never
requests any of those** — the actual search endpoint is `/search?q=...` (no trailing
slash, a different path string from the disallowed one), and the detail page is
`/spl/...`, neither of which is disallowed. The site also exposes a `/direct/i?...`
and a `/cache?u=...` redirect for the "apply" click-through; this skill never follows
either — see Notes for how the real external posting URL is obtained instead. No
public terms-of-service page prohibiting automated access was found; keep volume
reasonable regardless (a handful of requests per session, not a crawl).

## When to use this skill

- Search job openings across Canada by keyword and/or city
- Filter by how recently a listing was posted
- Get the full description, employment type, posting date, expiry date, and the real
  (non-aggregator) external posting URL for a specific listing

## Commands

### Search job listings

```bash
bun run .agents/skills/eluta-search/cli/src/cli.ts search [flags]
```

Key flags:
- `--query <text>` / `-q <text>` — keywords (job title, skill, role).
- `--location <text>` / `-l <text>` — free-text city/region, e.g. `"Ottawa, ON"`.
- At least one of `--query` or `--location` is required.
- `--jobage <days>` — posted within N days. **Filtered client-side** (see Notes —
  Eluta's search cards only carry relative text like "4 days ago", not an exact
  timestamp).
- `--page <n>` — page number (1-indexed, 10 results per page).
- `--limit <n>` / `-n <n>` — cap results emitted (client-side).
- `--format json|table|plain` — default `json`.

### Fetch full job detail

```bash
bun run .agents/skills/eluta-search/cli/src/cli.ts detail <id|url> [--format json|plain]
```

`id` is the 32-character hex job id from `search` results (e.g.
`2ddd221fe7a3392c74d10d750a72929f`); a full `/spl/...` detail URL also works. Returns
the description, employment type, posting date, expiry date (`validThrough`), and the
real external posting URL where available (see Notes).

## Usage examples

```bash
# AI product manager roles in Ottawa
bun run .agents/skills/eluta-search/cli/src/cli.ts search -q "AI product manager" -l "Ottawa, ON" --format table

# Data scientist roles in Toronto, posted in the last 7 days
bun run .agents/skills/eluta-search/cli/src/cli.ts search -q "data scientist" -l "Toronto, ON" --jobage 7 --format table

# Business architect roles nationwide
bun run .agents/skills/eluta-search/cli/src/cli.ts search -q "business architect" --format table

# Full details for one listing
bun run .agents/skills/eluta-search/cli/src/cli.ts detail 2ddd221fe7a3392c74d10d750a72929f --format plain
```

## Output formats

| Format | Best for |
|--------|----------|
| `json` | Default — programmatic use, passing IDs to `detail` |
| `table` | Quick human-readable scanning |
| `plain` | Reading a single job's full detail (`detail` command) |

Search JSON follows the repo's portal contract:

```json
{
  "meta": { "count": 5, "page": 1, "pageSize": 10, "totalResults": 259,
            "location": "Ottawa, ON", "source": "eluta.ca" },
  "results": [ { "id": "2ddd221fe7a3392c74d10d750a72929f", "title": "...",
                 "company": "...", "location": "Ottawa, ON",
                 "date": "4 days ago", "url": "..." } ]
}
```

All errors are written to **stderr** as `{ "error": "...", "code": "..." }` and the
process exits with code `1`.

## Notes

- **`--jobage` is a client-side filter parsed from relative text**, not an exact
  timestamp — Eluta's search cards only show "Today", "Yesterday", "N hours/minutes
  ago", "N days ago", or "N+ days ago" (capped display, e.g. "30+"). The CLI converts
  this to an approximate day count; "N+" is treated as exactly N (conservative — a
  30+-day-old posting is excluded by `--jobage 7`, correctly, but two postings both
  showing "30+ days ago" can't be distinguished by exact age). `detail` on a specific
  posting does return an exact `datePosted` ISO timestamp.
- **The job id is a 32-character hex hash**, not sequential. Eluta's own detail URLs
  embed a decorative SEO slug before the hash (e.g.
  `/spl/senior-product-manager-2ddd221fe7a3392c74d10d750a72929f`) — the slug is
  ignored by the server, so this CLI constructs URLs as `/spl/job-<id>` directly.
- **The real external posting URL is in the detail page's microdata**, not something
  this CLI follows a redirect to get. Eluta's own "apply" link on both the search card
  and detail page routes through `/cache?u=...` or `/direct/i?...` (disallowed /
  best avoided respectively). The detail page instead carries a
  `<meta itemprop="identifier" content="...">` tag with the actual originating URL
  (e.g. a `job-boards.greenhouse.io` link) — `detail`'s `applyUrl` field reads this
  directly, with no redirect ever fetched. It is `null` when Eluta doesn't have one on
  file.
- Detail-page fields are parsed from `schema.org/JobPosting` microdata
  (`itemprop="title"`, `"hiringOrganization"`, `"datePosted"`, `"validThrough"`,
  `"employmentType"`, `"jobLocation"`, `"description"`, `"identifier"`) rather than
  CSS classes — more stable against a redesign than the search-results page's classed
  markup.
- Page size is fixed at 10 results per page; `meta.totalResults` gives the
  portal-wide total from the page's own "jobs 1 to 10 of N" counter.
- No French-language path was found for Eluta.ca (unlike Job Bank/GC Jobs/Talent.com)
  — this skill is English-only.
