import { describe, expect, test } from "bun:test"
import { runCLI, parseJSON } from "./helpers.js"

/**
 * Live tests hit the real portal, so they are opt-in: CI deliberately runs only
 * fixture/mock suites (see .github/workflows/ci.yml). Enable with LIVE=1.
 */
const live = process.env.LIVE === "1"

describe.skipIf(!live)("live endpoints", () => {
  test("search returns the contract envelope with usable results", async () => {
    const result = await runCLI(["search", "-q", "AI product manager", "-l", "Ottawa, ON", "--limit", "5"])
    const payload = parseJSON<{
      meta: { count: number; page: number; source: string; totalResults: number | null }
      results: { id: string; title: string; url: string; company: string | null }[]
    }>(result)

    expect(payload.meta.page).toBe(1)
    expect(payload.meta.source).toBe("eluta.ca")
    expect(payload.results.length).toBeGreaterThan(0)
    expect(payload.results.length).toBeLessThanOrEqual(5)

    for (const job of payload.results) {
      expect(job.id).toMatch(/^[0-9a-f]+$/)
      expect(job.title.length).toBeGreaterThan(0)
      expect(job.url).toContain("eluta.ca/spl/")
      for (const key of ["company", "location", "date"]) {
        expect(job).toHaveProperty(key)
      }
    }
  })

  test("detail returns a readable description for a live posting", async () => {
    const search = await runCLI(["search", "-q", "AI product manager", "-l", "Ottawa, ON", "--limit", "1"])
    const found = parseJSON<{ results: { id: string }[] }>(search)
    if (found.results.length === 0) return // nothing posted right now; nothing to assert

    const result = await runCLI(["detail", found.results[0].id])
    const job = parseJSON<{ id: string; title: string; description: string | null }>(result)
    expect(job.id).toBe(found.results[0].id)
    expect(job.title.length).toBeGreaterThan(0)
    if (job.description) expect(job.description).not.toContain("<div")
  })
})
