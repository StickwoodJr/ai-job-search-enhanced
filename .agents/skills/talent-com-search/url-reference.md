# Talent.com URL Reference

Public, unauthenticated, server-rendered HTML pages on Talent.com's country subdomains
(`ca.talent.com` by default). Investigated 2026-08 against `ca.talent.com`; the same
Next.js template and markup served `us.talent.com` in spot checks.

## robots.txt

```
GET https://ca.talent.com/robots.txt
```

Disallows: `/services/api-new/search` (the JSON API backing the search page — do not
use it), `/search-jobs/*`, `/api/v1/tracker/pixel`, `/coreg/register.php`,
`/neuvooEmailPixel`, `/cdn-cgi/rum`, `/redirect*` (per-language variants too, e.g.
`/en/redirect*`, `/fr/redirect*`), `/*.shtml`, `/invoice-report`, `/ajax/*`,
`/convert*` (per-language variants too).

Everything this skill requests — `/jobs`, `/fr/jobs`, `/view`, `/fr/view` — is allowed.
No `Crawl-delay` directive is specified.

## Search

```
GET https://ca.talent.com/jobs?k=<query>&l=<location>&p=<page>
GET https://ca.talent.com/fr/jobs?k=<query>&l=<location>&p=<page>   (French)
```

| Param | Meaning | Example |
|-------|---------|---------|
| `k` | Free-text keywords | `AI product manager` |
| `l` | Free-text location (not an internal id) | `Ottawa, ON`, `Kanata` |
| `p` | 1-indexed page | `1`, `2`, … (~20 results/page) |

**`date=` was tested and found to be a no-op.** Values tried: `today`, `3days`,
`week`, `month` — all returned HTTP 200 with unchanged, unfiltered results (including
postings 30+ days old under `date=today`). Do not rely on it; the CLI filters by
`--jobage` client-side instead, using each card's own `dateTime`.

Returns server-rendered HTML (Next.js/React; NOT client-hydrated — the job data is
present in the initial response, no JS execution needed). Each result card is
anchored by:

```
data-testid="jobcard-container-<id>"
```

Within that card's subtree (forward of the marker):

| Field | Anchor |
|-------|--------|
| title | `<h2 class="JobCard_title__…">TITLE</h2>` |
| company | `<span class="JobCard_company__…">COMPANY</span>` |
| location | `<span class="JobCard_location__…">LOCATION</span>` |
| date | `<time class="JobCard_timeText__…" dateTime="ISO_TIMESTAMP">` |

The `JobCard_*__` prefix is a CSS Module class name — stable across deploys in
practice (semantic, not a random hash), unlike the `sc-xxxxx` styled-components
classes used elsewhere on the page. Match on the prefix with a wildcard suffix
(`JobCard_title__[^"]*"`) so a hash-suffix rebuild doesn't break parsing.

There is no reliable total-result count in the static HTML (no "N jobs found" element
was found near the results list — a "300 jobs" string on the page turned out to be an
unrelated i18n string from an employer-facing banner, not the result count).

## Detail

```
GET https://ca.talent.com/view?id=<id>
GET https://ca.talent.com/fr/view?id=<id>   (French)
```

Returns a single job's full HTML. No `application/ld+json` `JobPosting` structured
data is present (search does have a `ItemList` block, but it's just an id list, no
detail fields) — everything is parsed from the visible markup:

| Field | Anchor |
|-------|--------|
| title | The page's single `<h1>` (unique — verified only one `<h1>` appears, before any related-jobs section) |
| company / location | The `<div>` immediately after `</h1>` — **note:** `</h1>` is immediately followed by a stray `</div>` closing the h1's own wrapper first, THEN the meta div opens. Skip that stray close before matching. The meta div holds three `<span>`s: company, a `•` bullet, location — filter the bullet out. |
| description | Follows the text label `Job description` (`Description du poste` in French), not a class name (labels are stable; the wrapping `sc-xxxxx` class hash is not). Extracted with depth-aware `<div>` matching (nested `<div>`s inside the description do occur). |
| salary | Follows the text label `Salary` (`Salaire` in French) — first `<span>` after it. Absent on many listings. |
| employment type | Follows the text label `Job type` (`Type de poste` in French) — a `<ul><li>` list, e.g. `Full-time`, `Remote`. |
| apply link | `<a href="/redirect?id=<id>&pid=<partner>&action=f-link">`. **robots.txt disallows `/redirect*`** — this skill reports the URL as metadata only and never fetches it. |

No deadline/expiry field was found on the detail page (Talent.com is an aggregator,
not the original poster — postings don't consistently carry an application deadline).

## Notes

- Talent.com uses styled-components (`sc-xxxxx` classes, hash changes on redeploy) for
  most of the page chrome, but CSS Modules (`JobCard_*__` prefix) for the card
  component specifically, and stable label text for the detail-page sections. Parsing
  anchors on whichever is most stable per field — see the tables above.
- HTML entities in titles/descriptions use both named (`&amp;`, `&#39;`) and numeric
  hex forms (`&#x27;`, `&#xE9;`) — decode both.
- `l=` accepts plain city text directly; no city-id resolution step like Job Bank's
  `locationparam` is needed or available.
- English and French are both served from `ca.talent.com`, distinguished only by an
  `/fr` path prefix on `/jobs`/`/view` — no separate French domain.
