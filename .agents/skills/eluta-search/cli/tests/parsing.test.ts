import { describe, test, expect } from "bun:test"
import {
  parseJobCards,
  parseJobDetail,
  parseTotalCount,
  extractDivAfter,
  relativeDateToDays,
  withinJobage,
} from "../src/helpers"

// Mirrors the real markup on eluta.ca/search: a data-url="spl/<slug>-<hash>"
// card marker, then title/employer/location/relative-date anchors forward of it.
function searchCard(
  id: string,
  title: string,
  company = "Acme Inc.",
  location = "Ottawa, ON",
  date = "4 days ago",
): string {
  return `<div data-url="spl/some-title-${id}?imo=12"
     class="organic-job odd">
    <h2 class="title">
        <a class="lk-job-title"
data-url="spl/some-title-${id}?imo=12"
href="#!" rel="noopener noreferrer"
title="${title}">${title}</a>
    </h2>
    <a class="employer lk-employer" href="#!"
       onclick="window.location.href='/jobs-at-acme?imo=12'"
       title="See all jobs at ${company}.">${company}</a>
    <span class="location">
        <span>${location}</span>
    </span>
    <span class="description">Some snippet...</span>
    <a class="lk lastseen" href="#!"
       onclick="enavOpenNew('cache?u=123:example.com')"
       title="See how this page looked when Eluta indexed it">${date}</a>
</div>`
}

const HASH1 = "2ddd221fe7a3392c74d10d750a72929f"
const HASH2 = "e40147a5de5e476a956e9c4a8a52007f"

describe("parseJobCards", () => {
  test("extracts id, title, company, location, date, url", () => {
    const html = searchCard(HASH1, "Product Manager", "Ciena", "Ottawa, ON", "4 days ago")
    const [card] = parseJobCards(html)
    expect(card.id).toBe(HASH1)
    expect(card.title).toBe("Product Manager")
    expect(card.company).toBe("Ciena")
    expect(card.location).toBe("Ottawa, ON")
    expect(card.date).toBe("4 days ago")
    expect(card.url).toBe(`https://www.eluta.ca/spl/job-${HASH1}`)
  })

  test("the SEO slug prefix is ignored — only the trailing hash matters", () => {
    const html = `<div data-url="spl/completely-different-words-${HASH2}?imo=12"
     class="organic-job even">
      <a class="lk-job-title" href="#!" title="Role">Role</a>
    </div>`
    const [card] = parseJobCards(html)
    expect(card.id).toBe(HASH2)
  })

  test("parses multiple cards independently; a malformed one is skipped, not fatal", () => {
    const good1 = searchCard(HASH1, "Role One")
    const broken = `<div data-url="spl/bad-notahash" class="organic-job"><h2>no title here</h2></div>`
    const good2 = searchCard(HASH2, "Role Three")
    const html = good1 + broken + good2
    const cards = parseJobCards(html)
    expect(cards.map((c) => c.id)).toEqual([HASH1, HASH2])
  })

  test("missing company/location/date yield null, not thrown errors", () => {
    const html = `<div data-url="spl/bare-${HASH1}?imo=12" class="organic-job">
      <a class="lk-job-title" href="#!" title="Bare Role">Bare Role</a>
    </div>`
    const [card] = parseJobCards(html)
    expect(card.title).toBe("Bare Role")
    expect(card.company).toBeNull()
    expect(card.location).toBeNull()
    expect(card.date).toBeNull()
  })

  test("returns empty array when no cards present", () => {
    expect(parseJobCards("<html><body>no jobs</body></html>")).toEqual([])
  })
})

describe("parseTotalCount", () => {
  test("extracts the total from the job-count element", () => {
    const html = `<div id="job-count">jobs <b>1</b> to <b>10</b> of 259</div>`
    expect(parseTotalCount(html)).toBe(259)
  })

  test("returns null when absent", () => {
    expect(parseTotalCount("<div>no count here</div>")).toBeNull()
  })
})

describe("extractDivAfter", () => {
  test("extracts content from a simple div", () => {
    const html = 'PREFIX<div class="whatever">Simple text</div>SUFFIX'
    expect(extractDivAfter(html, "PREFIX".length)).toBe("Simple text")
  })

  test("handles nested divs by tracking depth", () => {
    const html = `LABEL<div class="short-text" itemprop="description"><div class="doc-source-html">
      <p>First.</p><p>Second.</p>
    </div></div>AFTER`
    const idx = html.indexOf('<div class="short-text"')
    const result = extractDivAfter(html, idx)
    expect(result).toContain("First.")
    expect(result).toContain("Second.")
    expect(result).not.toContain("AFTER")
  })

  test("returns null when no div follows", () => {
    expect(extractDivAfter("LABEL no div here", "LABEL".length)).toBeNull()
  })
})

describe("parseJobDetail", () => {
  function detailHtml(title: string, company: string, descriptionInner: string): string {
    return `<h1 class="job-title" itemprop="title" title="...">
    <a href="#" onclick="enavOpenNew('/direct/i?i=42&imo=12')">
        <span>${title}</span>
    </a>
</h1>
<h5 class="employer-name" itemprop="hiringOrganization" itemscope itemtype="http://schema.org/Organization">
    <a href="#" onclick="enavOpenNew('https://www.eluta.ca/jobs-at-acme')" title="...">
        <span itemprop="name">${company}</span>
    </a>
</h5>
<meta itemprop="identifier"
    content="https://jobs.example.com/careers/42" />
<meta itemprop="datePosted"
    content="2026-07-30T02:57:58" />
<meta itemprop="validThrough"
    content="2026-09-03T00:00:00" />
<meta itemprop="employmentType"
    content="FULL_TIME" />
<span itemprop="jobLocation" itemscope="itemscope" itemtype="http://schema.org/Place">
    <span itemprop="address" itemscope="itemscope" itemtype="http://schema.org/PostalAddress">
        <meta
    itemprop="addressLocality" content="Ottawa" />
        <meta itemprop="addressRegion" content="ON" />
    </span>
</span>
<div class="short-text" itemprop="description"><div class="doc-source-html">
${descriptionInner}
</div></div>`
  }

  test("extracts title, company, location from microdata", () => {
    const html = detailHtml("Product Manager", "Acme Inc.", "<p>We build things.</p>")
    const job = parseJobDetail(html, "42")
    expect(job.title).toBe("Product Manager")
    expect(job.company).toBe("Acme Inc.")
    expect(job.location).toBe("Ottawa, ON")
  })

  test("extracts datePosted, validThrough, employmentType, and the real external apply URL", () => {
    const html = detailHtml("Role", "Co", "<p>Desc.</p>")
    const job = parseJobDetail(html, "42")
    expect(job.date).toBe("2026-07-30T02:57:58")
    expect(job.validThrough).toBe("2026-09-03T00:00:00")
    expect(job.employmentType).toBe("FULL_TIME")
    expect(job.applyUrl).toBe("https://jobs.example.com/careers/42")
  })

  test("extracts description text without leftover markup, preserving paragraph breaks", () => {
    const html = detailHtml("Role", "Co", "<p>First paragraph.</p><p>Second paragraph.</p>")
    const job = parseJobDetail(html, "42")
    expect(job.description).toContain("First paragraph.\nSecond paragraph.")
    expect(job.description).not.toContain("<p>")
    expect(job.description).not.toContain("<div")
  })

  test("decodes named entities beyond the basic five — live-fetch regression", () => {
    // Eluta descriptions use &mdash;/&rsquo; etc.; the base decodeHtmlEntities
    // set only covered &amp;/&lt;/&gt;/&quot;/&#39; before this was found live.
    const html = detailHtml("Role", "Co", "<p>Long&mdash;term vision, the team&rsquo;s goal.</p>")
    const job = parseJobDetail(html, "42")
    expect(job.description).toContain("Long—term vision, the team’s goal.")
  })

  test("falls back to null fields when microdata is absent", () => {
    const html = `<h1 class="job-title"><span>Bare Role</span></h1>`
    const job = parseJobDetail(html, "7")
    expect(job.title).toBe("Bare Role")
    expect(job.company).toBeNull()
    expect(job.location).toBeNull()
    expect(job.date).toBeNull()
    expect(job.validThrough).toBeNull()
    expect(job.employmentType).toBeNull()
    expect(job.applyUrl).toBeNull()
    expect(job.description).toBeNull()
  })
})

describe("relativeDateToDays", () => {
  test("today is 0", () => expect(relativeDateToDays("Today")).toBe(0))
  test("yesterday is 1", () => expect(relativeDateToDays("Yesterday")).toBe(1))
  test("'4 days ago' is 4", () => expect(relativeDateToDays("4 days ago")).toBe(4))
  test("'2 hours ago' is 0 — live-fetch regression", () => expect(relativeDateToDays("2 hours ago")).toBe(0))
  test("'45 minutes ago' is 0", () => expect(relativeDateToDays("45 minutes ago")).toBe(0))
  test("'30+ days ago' is 30", () => expect(relativeDateToDays("30+ days ago")).toBe(30))
  test("unrecognized text is null", () => expect(relativeDateToDays("last week")).toBeNull())
  test("null input is null", () => expect(relativeDateToDays(null)).toBeNull())
})

describe("withinJobage", () => {
  test("no filter (9999) always passes", () => expect(withinJobage("30+ days ago", 9999)).toBe(true))
  test("null date always passes", () => expect(withinJobage(null, 7)).toBe(true))
  test("within the window passes", () => expect(withinJobage("2 days ago", 7)).toBe(true))
  test("outside the window is excluded", () => expect(withinJobage("30+ days ago", 7)).toBe(false))
})
