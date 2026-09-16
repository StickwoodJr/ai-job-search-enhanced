// Data source: Eluta.ca's public search (/search) and detail (/spl) pages.
// No authentication required. Both are server-rendered HTML. robots.txt disallows
// /search/ (trailing slash) but the actual search endpoint is /search?q=... (no
// trailing slash) — a different path string, and not disallowed. /spl is not
// disallowed either. The detail page's job-posting fields are marked up with
// schema.org/JobPosting microdata (itemprop attributes), which is what this file
// parses — far more stable than styled/hashed CSS classes.

export const BASE_URL = "https://www.eluta.ca"

export function writeError(error: string, code: string): void {
  process.stderr.write(JSON.stringify({ error, code }) + "\n")
}

const UA =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " +
  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

/** Fetch HTML with exponential backoff on 429/5xx. Returns "" on a 404. */
export async function htmlFetch(url: string): Promise<string> {
  const maxRetries = 6
  let delay = 500
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    const response = await fetch(url, {
      headers: {
        "User-Agent": UA,
        Accept: "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
      },
      redirect: "follow",
      signal: AbortSignal.timeout(15000),
    })
    if (response.status === 429 || response.status >= 500) {
      if (attempt === maxRetries) {
        throw new Error(`Request failed: ${response.status} ${response.statusText}`)
      }
      const jitter = Math.floor(Math.random() * 500)
      await new Promise((r) => setTimeout(r, delay + jitter))
      delay = Math.min(delay * 2, 8000)
      continue
    }
    if (response.status === 404) return ""
    if (!response.ok) {
      throw new Error(`Request failed: ${response.status} ${response.statusText}`)
    }
    return response.text()
  }
  throw new Error("Request failed after max retries")
}

export interface JobCard {
  id: string
  title: string
  company: string | null
  location: string | null
  date: string | null
  url: string
}

export interface JobDetail extends JobCard {
  description: string | null
  employmentType: string | null
  validThrough: string | null
  applyUrl: string | null
}

function numericEntity(cp: number): string {
  return cp >= 0 && cp <= 0x10ffff ? String.fromCodePoint(cp) : ""
}

export function decodeHtmlEntities(text: string): string {
  return text
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&apos;/g, "'")
    .replace(/&#(\d+);/g, (_, dec) => numericEntity(parseInt(dec, 10)))
    .replace(/&#[xX]([0-9a-fA-F]+);/g, (_, hex) => numericEntity(parseInt(hex, 16)))
    .replace(/&nbsp;/g, " ")
    .replace(/&mdash;/g, "—")
    .replace(/&ndash;/g, "–")
    .replace(/&rsquo;/g, "’")
    .replace(/&lsquo;/g, "‘")
    .replace(/&rdquo;/g, "”")
    .replace(/&ldquo;/g, "“")
    .replace(/&hellip;/g, "…")
    .replace(/&bull;/g, "•")
    .replace(/&copy;/g, "©")
    .replace(/&reg;/g, "®")
    .replace(/&trade;/g, "™")
}

function stripTags(html: string): string {
  return html.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim()
}

function clean(html: string): string {
  return decodeHtmlEntities(stripTags(html))
}

/** Like stripTags, but preserves newlines already inserted for <br>/block-closing
 * tags instead of collapsing them via a blanket `\s+` -> " ". */
function stripTagsPreserveNewlines(html: string): string {
  return html
    .replace(/<[^>]+>/g, "")
    .replace(/[ \t]+/g, " ")
    .replace(/[ \t]*\n[ \t]*/g, "\n")
    .trim()
}

/**
 * Extract the inner HTML of the <div> starting at `fromIndex`, correctly handling
 * nested <div> elements by tracking tag depth.
 */
export function extractDivAfter(html: string, fromIndex: number): string | null {
  const openRe = /<div[^>]*>/
  const rest = html.slice(fromIndex)
  const open = openRe.exec(rest)
  if (!open) return null

  let i = (open.index ?? 0) + open[0].length
  let depth = 1

  while (depth > 0 && i < rest.length) {
    const nextOpen = rest.indexOf("<div", i)
    const nextClose = rest.indexOf("</div>", i)

    if (nextClose === -1) return null

    if (nextOpen !== -1 && nextOpen < nextClose) {
      depth++
      i = nextOpen + 4
    } else {
      depth--
      i = nextClose + 6
    }
  }

  return rest.slice((open.index ?? 0) + open[0].length, i - 6)
}

/** Total result count from "jobs <b>1</b> to <b>10</b> of 259". */
export function parseTotalCount(html: string): number | null {
  const m = html.match(/jobs <b>\d+<\/b> to <b>\d+<\/b> of (\d+)/)
  return m ? parseInt(m[1], 10) : null
}

/**
 * Parse the search-results page. Each card is anchored by
 * `<div data-url="spl/<slug>-<hash>" class="organic-job ...">`; the trailing
 * 32-char hex hash in the slug is the stable job id (also usable standalone to
 * build a detail URL — the SEO slug prefix is decorative, ignored by the server).
 */
export function parseJobCards(html: string): JobCard[] {
  const results: JobCard[] = []
  const markerRe = /<div data-url="spl\/([^"?]+)(?:\?[^"]*)?"\s*\n?\s*class="organic-job/g
  const markers: { slug: string; idx: number }[] = []
  let m: RegExpExecArray | null
  while ((m = markerRe.exec(html)) !== null) {
    markers.push({ slug: m[1], idx: m.index })
  }

  for (let i = 0; i < markers.length; i++) {
    const { slug, idx } = markers[i]
    const idMatch = slug.match(/-([0-9a-f]{20,40})$/)
    if (!idMatch) continue
    const id = idMatch[1]

    const end = i + 1 < markers.length ? markers[i + 1].idx : Math.min(html.length, idx + 6000)
    const chunk = html.slice(idx, end)

    const titleMatch = chunk.match(/<a class="lk-job-title"[\s\S]*?>([^<]*)<\/a>/)
    const title = titleMatch ? clean(titleMatch[1]) : ""
    if (!title) continue

    const companyMatch = chunk.match(/<a class="employer lk-employer"[^>]*>([^<]*)<\/a>/)
    const company = companyMatch ? clean(companyMatch[1]) || null : null

    const locationMatch = chunk.match(/<span class="location">\s*<span>([^<]*)<\/span>/)
    const location = locationMatch ? clean(locationMatch[1]) || null : null

    const dateMatch = chunk.match(/<a class="lk lastseen"[^>]*>([^<]*)<\/a>/)
    const date = dateMatch ? clean(dateMatch[1]) || null : null

    results.push({
      id,
      title,
      company,
      location,
      date,
      url: `${BASE_URL}/spl/job-${id}`,
    })
  }

  return results
}

function metaContent(html: string, itemprop: string): string | null {
  const m = html.match(new RegExp(`<meta itemprop="${itemprop}"[\\s\\S]*?content="([^"]*)"`))
  return m ? decodeHtmlEntities(m[1]) : null
}

/** Parse the single-job detail page (schema.org/JobPosting microdata). */
export function parseJobDetail(html: string, id: string): JobDetail {
  const titleMatch = html.match(/<h1 class="job-title"[\s\S]*?<span>([^<]*)<\/span>/)
  const title = titleMatch ? clean(titleMatch[1]) : "(untitled)"

  const companyMatch = html.match(/<span itemprop="name">([^<]*)<\/span>/)
  const company = companyMatch ? clean(companyMatch[1]) || null : null

  // The simple jobLocation block (distinct from the employer's own detailed
  // PostalAddress block) — city + region only.
  let location: string | null = null
  const jobLocIdx = html.indexOf('itemprop="jobLocation"')
  if (jobLocIdx !== -1) {
    const nearby = html.slice(jobLocIdx, jobLocIdx + 600)
    const locality = nearby.match(/itemprop="addressLocality"\s+content="([^"]*)"/)
    const region = nearby.match(/itemprop="addressRegion"\s+content="([^"]*)"/)
    const parts = [locality?.[1], region?.[1]].filter(Boolean).map((s) => decodeHtmlEntities(s as string))
    location = parts.length ? parts.join(", ") : null
  }

  const date = metaContent(html, "datePosted")
  const validThrough = metaContent(html, "validThrough")
  const employmentType = metaContent(html, "employmentType")
  const applyUrl = metaContent(html, "identifier")

  let description: string | null = null
  const descMarker = html.match(/<div class="short-text"\s+itemprop="description">/)
  if (descMarker) {
    const descHtml = extractDivAfter(html, descMarker.index ?? 0)
    if (descHtml) {
      const withBreaks = descHtml
        .replace(/<\s*br\s*\/?>/gi, "\n")
        .replace(/<\/(p|li|ul|ol|div|h\d)>/gi, "\n")
      description =
        decodeHtmlEntities(stripTagsPreserveNewlines(withBreaks)).replace(/\n{3,}/g, "\n\n").trim() || null
    }
  }

  return {
    id,
    title,
    company,
    location,
    date,
    url: `${BASE_URL}/spl/job-${id}`,
    description,
    employmentType,
    validThrough,
    applyUrl,
  }
}

/** Eluta's search cards only carry a relative-text date ("4 days ago", "Today",
 * "2 hours ago", "30+ days ago") — no ISO timestamp until the detail page.
 * Parsed to an approximate day count for client-side --jobage filtering.
 * Unrecognized text (e.g. a future format change) returns null and always
 * passes the filter. */
export function relativeDateToDays(text: string | null): number | null {
  if (!text) return null
  const t = text.trim().toLowerCase()
  if (t === "today") return 0
  if (t === "yesterday") return 1
  if (/^\d+\+?\s*(minutes?|hours?)\s*ago$/.test(t)) return 0
  const m = t.match(/^(\d+)\+?\s*days?\s*ago$/)
  return m ? parseInt(m[1], 10) : null
}

export function withinJobage(date: string | null, days: number): boolean {
  if (!days || days >= 9999) return true
  const age = relativeDateToDays(date)
  if (age === null) return true
  return age <= days
}
