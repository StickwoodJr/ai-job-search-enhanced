import { describe, expect, it } from "bun:test"
import { runCLI, parseJSON } from "./helpers.ts"

describe("indeed-search CLI contract", () => {
  it("shows help and exits 0", async () => {
    const res = await runCLI(["--help"])
    expect(res.exitCode).toBe(0)
    expect(res.stdout).toContain("indeed-search - Search live Indeed job listings")
  })

  it("exits 1 on invalid command with stderr JSON", async () => {
    const res = await runCLI(["invalid-cmd"])
    expect(res.exitCode).toBe(1)
    const err = JSON.parse(res.stderr)
    expect(err.code).toBe("INVALID_COMMAND")
  })

  it("exits 1 on detail without target", async () => {
    const res = await runCLI(["detail"])
    expect(res.exitCode).toBe(1)
    const err = JSON.parse(res.stderr)
    expect(err.code).toBe("MISSING_PARAM")
  })

  it("runs search and returns JSON structure with meta and results", async () => {
    const res = await runCLI(["search", "-q", "Linux", "-l", "Toronto, ON", "--limit", "1", "--format", "json"])
    expect(res.exitCode).toBe(0)
    const data = parseJSON<{ meta: any; results: any[] }>(res)
    expect(data.meta).toBeDefined()
    expect(data.meta.location).toBe("Toronto, ON")
    expect(Array.isArray(data.results)).toBe(true)
    if (data.results.length > 0) {
      const job = data.results[0]
      expect(job.id).toBeDefined()
      expect(job.title).toBeDefined()
      expect(job.url).toBeDefined()
    }
  })
})
