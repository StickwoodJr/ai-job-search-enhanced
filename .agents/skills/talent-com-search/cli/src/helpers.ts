// Data source: Talent.com's public country-subdomain job boards (ca.talent.com by
// default). No authentication required. Search and detail are both server-rendered
// HTML (Next.js), not the JSON API under /services/api-new/search — that path is
// disallowed by robots.txt. /jobs and /view are not.
// Search returns a list of job cards; detail returns a single job's HTML. We parse
// both with regex, splitting per-card so one malformed card cannot break the rest.

export function baseUrl(country: string): string {
  return `https://${country}.talent.com`
}

export function langPrefix(lang: Lang): string {
  return lang === "fr" ? "/fr" : ""
}

export type Lang = "en" | "fr"

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
  salary: string | null
  applyUrl: string | null
}

/**
 * Convert a Unicode code point to a string. Uses `fromCodePoint` (not
 * `fromCharCode`) so supplementary-plane code points (emoji, etc.) decode
 * correctly, and drops out-of-range values instead of throwing.
 */
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
}

function stripTags(html: string): string {
  return html.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim()
}

function clean(html: string): string {
  return decodeHtmlEntities(stripTags(html))
}

/**
 * Strip tags from a description block while preserving the paragraph/line
 * breaks already inserted for <br> and block-closing tags. Plain `stripTags`
 * collapses ALL whitespace (including those `\n`s) via `\s+` -> " ", so this
 * only collapses horizontal whitespace and leaves newlines intact.
 */
function stripTagsPreserveNewlines(html: string): string {
  return html
    .replace(/<[^>]+>/g, "")
    .replace(/[ \t]+/g, " ")
    .replace(/[ \t]*\n[ \t]*/g, "\n")
    .trim()
}

/**
 * Extract the inner HTML of the first <div> found after `fromIndex`, correctly
 * handling nested <div> elements by tracking tag depth. Used to pull the job
 * description out from under a text label (e.g. "Job description") rather than
 * a class name, since Talent.com's styled-components class hashes change on
 * every deploy but the label text does not.
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

/** Find the index right after a text label (e.g. "Job description</span>"). */
function labelEnd(html: string, label: string): number | null {
  const idx = html.indexOf(`${label}</span>`)
  if (idx === -1) return null
  return idx + label.length + "</span>".length
}

/**
 * Parse the search-results page. Each card is anchored by
 * data-testid="jobcard-container-<id>"; title/company/location/date all live
 * forward of that marker within the same <article>, so chunking forward to the
 * next card marker (or a fixed cap) is safe.
 */
export function parseJobCards(html: string, country: string, lang: Lang): JobCard[] {
  const results: JobCard[] = []
  const markerRe = /data-testid="jobcard-container-(\d+)"/g
  const markers: { id: string; idx: number }[] = []
  let m: RegExpExecArray | null
  while ((m = markerRe.exec(html)) !== null) {
    markers.push({ id: m[1], idx: m.index })
  }

  for (let i = 0; i < markers.length; i++) {
    const { id, idx } = markers[i]
    const end = i + 1 < markers.length ? markers[i + 1].idx : Math.min(html.length, idx + 8000)
    const chunk = html.slice(idx, end)

    const titleMatch = chunk.match(/JobCard_title__[^"]*">([^<]+)<\/h2>/)
    if (!titleMatch) continue
    const title = clean(titleMatch[1])
    if (!title) continue

    const companyMatch = chunk.match(/JobCard_company__[^"]*">([^<]*)<\/span>/)
    const company = companyMatch ? clean(companyMatch[1]) || null : null

    const locationMatch = chunk.match(/JobCard_location__[^"]*">([^<]*)<\/span>/)
    const location = locationMatch ? clean(locationMatch[1]) || null : null

    const dateMatch = chunk.match(/JobCard_timeText__[^"]*"\s+dateTime="([^"]+)"/)
    const date = dateMatch ? dateMatch[1] : null

    results.push({
      id,
      title,
      company,
      location,
      date,
      url: `${baseUrl(country)}${langPrefix(lang)}/view?id=${id}`,
    })
  }

  return results
}

/** Parse the single-job detail page. */
export function parseJobDetail(html: string, id: string, country: string, lang: Lang): JobDetail {
  const h1 = html.match(/<h1[^>]*>([^<]+)<\/h1>/)
  const title = h1 ? clean(h1[1]) : "(untitled)"

  // The company/location meta line is the sibling <div> after </h1> — but
  // </h1> is immediately followed by a stray </div> closing the h1's own
  // wrapper first (verified against live pages), so that's skipped before
  // matching the meta div. It holds three <span>s: company, a "•" bullet,
  // and location. Filter the bullet out.
  let company: string | null = null
  let location: string | null = null
  if (h1) {
    const afterH1 = html.slice((h1.index ?? 0) + h1[0].length)
    const metaDiv = afterH1.match(/^\s*(?:<\/div>\s*)?<div[^>]*>([\s\S]*?)<\/div>/)
    if (metaDiv) {
      const spans = [...metaDiv[1].matchAll(/<span[^>]*>([^<]*)<\/span>/g)]
        .map((s) => clean(s[1]))
        .filter((s) => s && s !== "•")
      company = spans[0] || null
      location = spans[1] || null
    }
  }

  let description: string | null = null
  const descLabelEnd = labelEnd(html, "Job description") ?? labelEnd(html, "Description du poste")
  if (descLabelEnd !== null) {
    const descHtml = extractDivAfter(html, descLabelEnd)
    if (descHtml) {
      const withBreaks = descHtml
        .replace(/<\s*br\s*\/?>/gi, "\n")
        .replace(/<\/(p|li|ul|ol|div|h\d)>/gi, "\n")
      description =
        decodeHtmlEntities(stripTagsPreserveNewlines(withBreaks)).replace(/\n{3,}/g, "\n\n").trim() || null
    }
  }

  let salary: string | null = null
  const salaryLabelEnd = labelEnd(html, "Salary") ?? labelEnd(html, "Salaire")
  if (salaryLabelEnd !== null) {
    const after = html.slice(salaryLabelEnd)
    const span = after.match(/<span[^>]*>([^<]*)<\/span>/)
    salary = span ? clean(span[1]) || null : null
  }

  let employmentType: string | null = null
  const typeLabelEnd = labelEnd(html, "Job type") ?? labelEnd(html, "Type de poste")
  if (typeLabelEnd !== null) {
    const after = html.slice(typeLabelEnd)
    const ul = after.match(/<ul[^>]*>([\s\S]*?)<\/ul>/)
    if (ul) {
      const items = [...ul[1].matchAll(/<li[^>]*>([^<]*)<\/li>/g)].map((li) => clean(li[1])).filter(Boolean)
      employmentType = items.length ? items.join(", ") : null
    }
  }

  // Apply link goes through /redirect, which robots.txt disallows crawling —
  // record it as metadata only, never fetch it.
  const applyMatch = html.match(/href="(\/redirect\?id=\d+[^"]*)"/)
  const applyUrl = applyMatch ? `${baseUrl(country)}${decodeHtmlEntities(applyMatch[1])}` : null

  return {
    id,
    title,
    company,
    location,
    date: null,
    url: `${baseUrl(country)}${langPrefix(lang)}/view?id=${id}`,
    description,
    employmentType,
    salary,
    applyUrl,
  }
}

/** Client-side jobage filter: Talent.com's `date=` query param is a documented
 * no-op (verified against live results), so recency filtering happens locally
 * against each card's `dateTime` attribute. */
export function withinJobage(dateIso: string | null, days: number): boolean {
  if (!dateIso || !days || days >= 9999) return true
  const cutoff = Date.parse(dateIso)
  if (isNaN(cutoff)) return true
  const ageMs = Date.now() - cutoff
  return ageMs <= days * 86400000
}
