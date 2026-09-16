---
name: talent-com-search
version: 1.0.0
description: >
  Use this skill to search for jobs on Talent.com (talent.com), a global job
  aggregator. Defaults to Canada (ca.talent.com) — covers every province and
  territory, every sector, English and French. Also usable for any other
  Talent.com country market via --country. Invoke for open positions,
  vacancies, and hiring in Canadian cities (Ottawa, Toronto, Vancouver,
  Montréal, Calgary, Kanata, Nepean, Gatineau) or nationwide. Trigger phrases:
  Talent.com, jobs on Talent.com, job aggregator, search Talent.com, emplois
  au Canada, offres d'emploi, recherche d'emploi, postes vacants.
context: fork
enabled: true  # set to false to keep this portal installed but have /scrape skip it
allowed-tools: Bash(bun run .agents/skills/talent-com-search/cli/src/cli.ts *)
---

# Talent.com Search Skill

Search live job listings from **Talent.com** (`talent.com`), a global job aggregator
that mirrors postings pulled from employer career sites, applicant tracking systems,
and other boards. No authentication, no API key, and **zero runtime dependencies** —
it runs with just `bun`.

Defaults to `ca.talent.com` (Canada) to match this fork; `--country` switches to any
other Talent.com market (e.g. `us`, `uk`).

## Access and etiquette

`talent.com/robots.txt` allows the `/jobs` (search) and `/view` (detail) paths this
skill uses. It disallows `/search-jobs/*`, `/services/api-new/search` (the underlying
JSON API — the CLI deliberately parses the server-rendered HTML page instead),
`/redirect*` (the apply-tracking link), `/convert*`, and `/ajax/*`. This skill never
requests any of those disallowed paths — `detail`'s `applyUrl` is returned as metadata
only, never fetched. No public terms-of-service page prohibiting this was found; keep
volume reasonable regardless (a handful of requests per session, not a crawl).

## When to use this skill

- Search job openings across Canada (or any Talent.com market) by keyword and/or city
- Filter by how recently a listing was last updated
- Search in French against the `/fr` path
- Get the full description, salary, and employment type for a specific listing

## Commands

### Search job listings

```bash
bun run .agents/skills/talent-com-search/cli/src/cli.ts search [flags]
```

Key flags:
- `--query <text>` / `-q <text>` — keywords (job title, skill, role).
- `--location <text>` / `-l <text>` — free-text city/region, e.g. `"Ottawa, ON"`. Not
  resolved against an internal id (unlike Job Bank) — pass whatever text you'd type
  into Talent.com's own search box.
- At least one of `--query` or `--location` is required.
- `--country <cc>` — Talent.com country subdomain. Default `ca`.
- `--lang en|fr` — English or French listings. Default `en`.
- `--jobage <days>` — posted within N days. **Filtered client-side** against each
  listing's last-updated timestamp (see Notes — Talent.com's own date parameter is a
  no-op).
- `--page <n>` — page number (1-indexed, ~20 results per page).
- `--limit <n>` / `-n <n>` — cap results emitted (client-side).
- `--format json|table|plain` — default `json`.

### Fetch full job detail

```bash
bun run .agents/skills/talent-com-search/cli/src/cli.ts detail <id|url> [--country cc] [--lang en|fr] [--format json|plain]
```

`id` is the numeric posting id from `search` results (e.g. `604692603372315399`); a
full `/view?id=...` URL (either language prefix) also works. Returns the description,
salary (when listed), employment type, and the apply link (a Talent.com redirect —
not followed, only reported).

## Usage examples

```bash
# AI product manager roles in Ottawa
bun run .agents/skills/talent-com-search/cli/src/cli.ts search -q "AI product manager" -l "Ottawa, ON" --format table

# Data scientist roles in Toronto, updated in the last 7 days
bun run .agents/skills/talent-com-search/cli/src/cli.ts search -q "data scientist" -l "Toronto, ON" --jobage 7 --format table

# French-language search
bun run .agents/skills/talent-com-search/cli/src/cli.ts search -q "gestionnaire de produits" --lang fr -l Ottawa --format table

# Any other Talent.com market
bun run .agents/skills/talent-com-search/cli/src/cli.ts search -q "product manager" -l "Seattle, WA" --country us --format table

# Full details for one listing
bun run .agents/skills/talent-com-search/cli/src/cli.ts detail 604692603372315399 --format plain
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
  "meta": { "count": 5, "page": 1, "location": "Ottawa, ON", "country": "ca",
            "lang": "en", "source": "ca.talent.com" },
  "results": [ { "id": "...", "title": "...", "company": "...", "location": "...",
                 "date": "2026-06-26T02:10:10Z", "url": "..." } ]
}
```

All errors are written to **stderr** as `{ "error": "...", "code": "..." }` and the
process exits with code `1`.

## Notes

- **`--jobage` is a client-side filter, not a portal parameter.** Talent.com's search
  page accepts a `date=` query parameter, but it was verified live to have no effect
  on results — a request with `date=today` still returned postings 30+ days old. The
  CLI instead parses each card's `dateTime` attribute (an ISO timestamp of when the
  listing was last updated by Talent.com's aggregator, not necessarily the original
  posting date) and filters locally.
- **No reliable total-results count.** Unlike Job Bank, Talent.com's search page does
  not expose a trustworthy "N jobs found" figure in the static HTML — `meta.count` is
  the number of results returned on this page, not a portal-wide total.
- **`--location` is free text**, not resolved to an internal id — Talent.com's own `l`
  query parameter accepts plain city names directly.
- Page size is approximately 20 results; not guaranteed exact (occasional sponsored
  slots shift the count by one).
- Company/location are occasionally blank on the search card itself (anonymized
  recruiter postings) — `detail` usually fills them in.
- Talent.com's markup is React (Next.js) with styled-components class-name hashes that
  can change on redeploy. Parsing anchors on stable signals where possible — CSS
  module prefixes (`JobCard_title__`, etc.) on the search page, and text labels
  ("Job description", "Salary", "Job type") rather than hashed classes on the detail
  page. See `url-reference.md` for the exact anchors to repair if the site changes.
