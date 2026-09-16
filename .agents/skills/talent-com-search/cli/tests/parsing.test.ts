import { describe, test, expect } from "bun:test"
import { parseJobCards, parseJobDetail, extractDivAfter, withinJobage } from "../src/helpers"

// Minimal search-card markup mirroring what ca.talent.com actually serves:
// a data-testid="jobcard-container-<id>" wrapper, then JobCard_title__/
// JobCard_company__/JobCard_location__ spans and a JobCard_timeText__ <time>
// with an ISO dateTime, all forward of the marker within the same card.
function searchCard(id: string, title: string, company = "Acme Inc.", location = "Ottawa, ON", dateIso = "2026-07-01T00:00:00Z"): string {
  return `<div data-job-id="x" data-new-id="${id}" data-rank="1" data-testid="jobcard-container-${id}" style="cursor:pointer">
    <article class="JobCard_card__TSiPB" data-testid="job-card-unified">
      <header class="JobCard_header__tgcjv">
        <div class="JobCard_heading__7POIz">
          <h2 class="JobCard_title__X32Qk">${title}</h2>
          <address class="JobCard_meta__yPOkr">
            <span class="JobCard_company__NmRol">${company}</span>
            <span class="JobCard_bullet__IlWM8">•</span>
            <span class="JobCard_location__nmTtw">${location}</span>
          </address>
        </div>
      </header>
      <div class="JobCard_body__Q46Ym"><p class="JobCard_snippet__rqX60">Snippet...</p></div>
      <footer class="JobCard_footer__LQEqk">
        <div class="JobCard_timeAndFlags__hHlJx">
          <time class="JobCard_timeText__wyyGm" dateTime="${dateIso}">Last updated: 1 day ago</time>
        </div>
      </footer>
    </article>
  </div>`
}

describe("parseJobCards", () => {
  test("extracts id, title, company, location, date, url", () => {
    const html = searchCard("123456", "Product Manager", "Ciena", "Ottawa, ON, CA", "2026-07-01T12:00:00Z")
    const [card] = parseJobCards(html, "ca", "en")
    expect(card.id).toBe("123456")
    expect(card.title).toBe("Product Manager")
    expect(card.company).toBe("Ciena")
    expect(card.location).toBe("Ottawa, ON, CA")
    expect(card.date).toBe("2026-07-01T12:00:00Z")
    expect(card.url).toBe("https://ca.talent.com/view?id=123456")
  })

  test("uses the /fr/view URL prefix when lang=fr", () => {
    const html = searchCard("999", "Gestionnaire")
    const [card] = parseJobCards(html, "ca", "fr")
    expect(card.url).toBe("https://ca.talent.com/fr/view?id=999")
  })

  test("respects --country by changing the subdomain", () => {
    const html = searchCard("999", "Manager")
    const [card] = parseJobCards(html, "us", "en")
    expect(card.url).toBe("https://us.talent.com/view?id=999")
  })

  test("decodes hex HTML entities in the title (e.g. apostrophe)", () => {
    const html = searchCard("111", "Gestionnaire de cas d&#x27;invalidit&#xE9;")
    const [card] = parseJobCards(html, "ca", "fr")
    expect(card.title).toBe("Gestionnaire de cas d'invalidité")
  })

  test("parses multiple cards independently; a malformed one is skipped, not fatal", () => {
    const good1 = searchCard("1", "Role One")
    const broken = `<div data-testid="jobcard-container-2" style="cursor:pointer"><article>no title here</article></div>`
    const good2 = searchCard("3", "Role Three")
    const html = good1 + broken + good2
    const cards = parseJobCards(html, "ca", "en")
    expect(cards.map((c) => c.id)).toEqual(["1", "3"])
  })

  test("missing company/location yield null, not thrown errors", () => {
    const html = `<div data-testid="jobcard-container-5" style="cursor:pointer">
      <h2 class="JobCard_title__X32Qk">Bare Role</h2>
    </div>`
    const [card] = parseJobCards(html, "ca", "en")
    expect(card.title).toBe("Bare Role")
    expect(card.company).toBeNull()
    expect(card.location).toBeNull()
    expect(card.date).toBeNull()
  })

  test("returns empty array when no cards present", () => {
    expect(parseJobCards("<html><body>no jobs</body></html>", "ca", "en")).toEqual([])
  })
})

describe("extractDivAfter", () => {
  test("extracts content from a simple div", () => {
    const html = 'PREFIX<div class="whatever">Simple text</div>SUFFIX'
    expect(extractDivAfter(html, "PREFIX".length)).toBe("Simple text")
  })

  test("handles nested divs by tracking depth", () => {
    const html = `LABEL<div class="x">
      <div>Requirements:</div>
      <ul><li>Skill A</li></ul>
      <p>We are...</p>
    </div>AFTER`
    const result = extractDivAfter(html, "LABEL".length)
    expect(result).toContain("Requirements:")
    expect(result).toContain("Skill A")
    expect(result).toContain("We are...")
    expect(result).not.toContain("AFTER")
  })

  test("returns null when no div follows", () => {
    expect(extractDivAfter("LABEL no div here", "LABEL".length)).toBeNull()
  })
})

describe("parseJobDetail", () => {
  // Mirrors the real page structure: </h1> is immediately followed by a stray
  // </div> closing the h1's own wrapper, THEN the company/location meta div
  // opens — a live-fetch regression (see "skips the stray </div>..." below).
  function detailHtml(title: string, company: string, location: string, descriptionInner: string): string {
    return `<h1 class="sc-abc">${title}</h1></div><div class="sc-meta"><span class="sc-a">${company}</span><span class="sc-b">•</span><span class="sc-c">${location}</span></div>
    <div class="sc-labels"><span>Salary</span></div><div class="sc-val"><span>CA$100,000.00 yearly</span></div>
    <div class="sc-labels"><span>Job type</span></div><ul><li>Full-time</li><li>Remote</li></ul>
    <span>Job description</span><div class="sc-desc"><p>${descriptionInner}</p></div>
    <a href="/redirect?id=42&pid=abc&action=f-link">Apply</a>`
  }

  test("extracts title, company, location", () => {
    const html = detailHtml("Product Line Manager", "Ciena Communications, Inc.", "Ottawa, ON", "We build things.")
    const job = parseJobDetail(html, "42", "ca", "en")
    expect(job.title).toBe("Product Line Manager")
    expect(job.company).toBe("Ciena Communications, Inc.")
    expect(job.location).toBe("Ottawa, ON")
  })

  test("skips the stray </div> between </h1> and the meta div — live-fetch regression", () => {
    // Without accounting for the stray </div>, the meta-div regex matches an
    // empty/wrong div and company/location silently come back null.
    const html = `<h1>Role</h1></div><div class="sc-meta"><span>Real Co</span><span>•</span><span>Real City</span></div>`
    const job = parseJobDetail(html, "1", "ca", "en")
    expect(job.company).toBe("Real Co")
    expect(job.location).toBe("Real City")
  })

  test("extracts description text without leftover markup", () => {
    const html = detailHtml("Role", "Co", "Loc", "Build great <strong>products</strong>.")
    const job = parseJobDetail(html, "42", "ca", "en")
    expect(job.description).toContain("Build great")
    expect(job.description).toContain("products")
    expect(job.description).not.toContain("<strong>")
    expect(job.description).not.toContain("<div")
  })

  test("preserves paragraph breaks between <p> blocks as newlines — live-fetch regression", () => {
    // Plain stripTags collapses ALL whitespace (\s+ -> " "), which would
    // silently flatten every description into one wall of text.
    const html = `<h1>Role</h1></div><div class="sc-meta"><span>Co</span><span>•</span><span>Loc</span></div>
      <span>Job description</span><div class="sc-desc"><p>First paragraph.</p><p>Second paragraph.</p><ul><li>Point A</li><li>Point B</li></ul></div>`
    const job = parseJobDetail(html, "1", "ca", "en")
    expect(job.description).toContain("First paragraph.\nSecond paragraph.")
    expect(job.description).toContain("Point A\nPoint B")
  })

  test("extracts salary and employment type", () => {
    const html = detailHtml("Role", "Co", "Loc", "Desc")
    const job = parseJobDetail(html, "42", "ca", "en")
    expect(job.salary).toBe("CA$100,000.00 yearly")
    expect(job.employmentType).toBe("Full-time, Remote")
  })

  test("records the apply URL as metadata without following the /redirect link", () => {
    const html = detailHtml("Role", "Co", "Loc", "Desc")
    const job = parseJobDetail(html, "42", "ca", "en")
    expect(job.applyUrl).toBe("https://ca.talent.com/redirect?id=42&pid=abc&action=f-link")
  })

  test("falls back to null fields when sections are absent", () => {
    const html = `<h1>Bare Role</h1>`
    const job = parseJobDetail(html, "7", "ca", "en")
    expect(job.title).toBe("Bare Role")
    expect(job.company).toBeNull()
    expect(job.salary).toBeNull()
    expect(job.employmentType).toBeNull()
    expect(job.description).toBeNull()
    expect(job.applyUrl).toBeNull()
  })
})

describe("withinJobage", () => {
  test("no jobage filter (9999) always passes", () => {
    expect(withinJobage("2020-01-01T00:00:00Z", 9999)).toBe(true)
  })

  test("null date always passes (nothing to filter on)", () => {
    expect(withinJobage(null, 7)).toBe(true)
  })

  test("a date within the window passes", () => {
    const recent = new Date(Date.now() - 2 * 86400000).toISOString()
    expect(withinJobage(recent, 7)).toBe(true)
  })

  test("a date outside the window is excluded", () => {
    const old = new Date(Date.now() - 30 * 86400000).toISOString()
    expect(withinJobage(old, 7)).toBe(false)
  })
})
