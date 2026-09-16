# Eluta.ca URL Reference

Public, unauthenticated, server-rendered HTML pages on `www.eluta.ca`. Investigated
2026-08.

## robots.txt

```
GET https://www.eluta.ca/robots.txt
```

Disallows: `/asp/`, `/cache?`, `/cache/`, `/notification_search`, `/notify?`, `/rss?`,
`/sandbox?`, `/search/` (trailing slash), `/static/`, `/system/`. A separate block
fully disallows several crawler user-agents (`ia_archiver`, `OmniExplorer_Bot`, image
bots) regardless of path.

**`/search/` vs `/search`:** robots.txt disallows the path `/search/` (with a trailing
slash — matches e.g. `/search/results`). The actual search endpoint this site's own
homepage search form submits to is `/search?q=...` — no trailing slash, a distinct
path string that the `Disallow: /search/` rule does not match. Verified live: `GET
/search?q=...` returns 200 with normal results.

`/spl/...` (detail pages) is not disallowed.

## Search

```
GET https://www.eluta.ca/search?q=<query>&l=<location>&pg=<page>
```

| Param | Meaning | Example |
|-------|---------|---------|
| `q` | Free-text keywords | `AI product manager` |
| `l` | Free-text location | `Ottawa, ON` |
| `pg` | 1-indexed page | `1`, `2`, … (10 results/page) |

The site's own "next page" link bakes extra tokens into `q` (geocoded lat/long,
`sort:rank`, a re-quoted `location:"..."`) to carry the location filter forward
across pages — but a plain `q=<query>&l=<location>&pg=<n>` request works identically
without any of that; verified by comparing `job-count` and result ids between a
manually constructed `pg=2` request and the site's own generated next-page link.

Total result count: `<div id="job-count">jobs <b>1</b> to <b>10</b> of 259</div>` —
the trailing number (259 here) is plain text, not wrapped in a tag.

Each result card is anchored by:

```
<div data-url="spl/<seo-slug>-<32-char-hex-hash>?imo=12" class="organic-job ...">
```

Within that card:

| Field | Anchor |
|-------|--------|
| id | The 32-char hex hash suffix of the `data-url` slug |
| title | `<a class="lk-job-title" ...>TITLE</a>` (inner text; `href="#!"`, real navigation is client-side JS — not needed, see Detail) |
| company | `<a class="employer lk-employer" ...>COMPANY</a>` (inner text) |
| location | `<span class="location"><span>LOCATION</span></span>` |
| date | `<a class="lk lastseen" ...>RELATIVE_TEXT</a>` — relative text only ("4 days ago", "Today", "2 hours ago", "30+ days ago"), no ISO timestamp on the search page |

Sponsored/ad slots (`above-results-container`) use different markup and are not
matched by the `organic-job` anchor — only organic results are returned.

## Detail

```
GET https://www.eluta.ca/spl/<any-slug>-<id>
GET https://www.eluta.ca/spl/<any-slug>-<id>?imo=12   (also works; imo is not required)
```

**The SEO slug prefix is decorative and ignored by the server** — only the trailing
hash routes the request. Verified: `/spl/x-2ddd221fe7a3392c74d10d750a72929f` (a
deliberately wrong slug) returns the correct posting; `/spl/2ddd221fe7a3392c74d10d750a72929f`
(hash with no slug/dash prefix at all) 404s — a dash before the hash is required, but
what precedes it is not checked. This CLI constructs `/spl/job-<id>`.

The detail page marks up the posting with `schema.org/JobPosting` microdata
(`itemprop` attributes) — more stable than the search page's CSS classes:

| Field | Anchor |
|-------|--------|
| title | `<h1 class="job-title" itemprop="title">...<span>TITLE</span>...</h1>` |
| company | `<span itemprop="name">COMPANY</span>` inside the `itemprop="hiringOrganization"` block (unique per page — verified only one `itemprop="name"` appears) |
| location | `<span itemprop="jobLocation">` block's nested `addressLocality` + `addressRegion` `<meta>` tags — **not** the employer's own separate, more detailed `itemprop="address"`/`PostalAddress` block that appears earlier on the page (street address, postal code, geo coordinates of the employer's registered office, which may differ from the job's actual location) |
| datePosted | `<meta itemprop="datePosted" content="ISO_TIMESTAMP" />` |
| validThrough | `<meta itemprop="validThrough" content="ISO_TIMESTAMP" />` — the posting's expiry/deadline |
| employmentType | `<meta itemprop="employmentType" content="FULL_TIME" />` (schema.org enum values: `FULL_TIME`, `PART_TIME`, `CONTRACTOR`, etc.) |
| description | `<div class="short-text" itemprop="description"><div class="doc-source-html">...</div></div>` — proper `<p>`/`<ul><li>` structure; extracted with depth-aware `<div>` matching |
| **real external posting URL** | `<meta itemprop="identifier" content="https://...">` — the original ATS/employer URL (e.g. `job-boards.greenhouse.io/...`). **This is what `detail`'s `applyUrl` reads — no redirect is ever followed.** |

All of the above `itemprop` anchors were verified to appear exactly once per detail
page (no ambiguity with e.g. related-jobs sections).

### The apply/redirect links that this skill avoids

Both the search card ("N days ago" link, via `onclick="enavOpenNew('cache?u=<id>:<host>')"`)
and the detail page's title link (`onclick="enavOpenNew('/direct/i?i=<hash>&imo=12')"`)
route through Eluta's own click-tracking redirect. `/cache?` is explicitly disallowed
by robots.txt; `/direct/i` is not disallowed but is unnecessary — the detail page's
`itemprop="identifier"` meta tag already contains the real destination URL directly,
so this skill reads that instead of ever requesting either redirect.

## Notes

- HTML entities include both the basic set (`&amp;`, `&lt;`, `&quot;`, `&#39;`) and
  typographic ones not covered by a minimal decoder — `&mdash;`, `&ndash;`, `&rsquo;`,
  `&lsquo;`, `&rdquo;`, `&ldquo;`, `&hellip;`, `&bull;`, `&copy;` were all observed in
  live description text and must be decoded.
- No French-language path (`/fr/...` or a `fr.eluta.ca` subdomain) was found;
  `fr.eluta.ca` does not resolve. English-only.
- No CAPTCHA or bot-wall was encountered in testing (contrast with
  `gojobs.gov.on.ca`, which blocks all automated requests with a Radware/hCaptcha
  challenge even on its homepage — that portal was investigated and abandoned for
  this reason, not built).
