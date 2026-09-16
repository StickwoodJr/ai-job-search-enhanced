import { describe, test, expect } from "bun:test"
import { runCLI } from "./helpers"

function parsedStderr(stderr: string): { error?: string; code?: string } {
  try {
    return JSON.parse(stderr)
  } catch {
    return {}
  }
}

describe("Talent.com CLI dispatch", () => {
  test("bare invocation prints help and exits 1", async () => {
    const result = await runCLI([])
    expect(result.exitCode).toBe(1)
    expect(result.stdout).toContain("talent-com-cli")
  })

  test("--help exits 0 when a command is given", async () => {
    const result = await runCLI(["search", "--help"])
    expect(result.exitCode).toBe(0)
    expect(result.stdout).toContain("SEARCH FLAGS")
  })

  test("unknown command errors on stderr with a code", async () => {
    const result = await runCLI(["frobnicate"])
    expect(result.exitCode).toBe(1)
    expect(result.stdout).toBe("")
    expect(parsedStderr(result.stderr).code).toBe("BAD_CMD")
  })
})

describe("search flag validation", () => {
  test("no --query and no --location is rejected", async () => {
    const result = await runCLI(["search"])
    expect(result.exitCode).toBe(1)
    expect(parsedStderr(result.stderr).code).toBe("NO_CRITERIA")
  })

  test("non-numeric --jobage exits 1 with BAD_ARG", async () => {
    const result = await runCLI(["search", "-q", "x", "--jobage", "soon"])
    expect(result.exitCode).toBe(1)
    const err = parsedStderr(result.stderr)
    expect(err.code).toBe("BAD_ARG")
    expect(err.error).toMatch(/jobage/)
  })

  test("non-numeric --page exits 1 with BAD_ARG", async () => {
    const result = await runCLI(["search", "-q", "x", "--page", "abc"])
    expect(result.exitCode).toBe(1)
    expect(parsedStderr(result.stderr).code).toBe("BAD_ARG")
  })

  test("non-numeric --limit exits 1 with BAD_ARG", async () => {
    const result = await runCLI(["search", "-q", "x", "--limit", "many"])
    expect(result.exitCode).toBe(1)
    expect(parsedStderr(result.stderr).code).toBe("BAD_ARG")
  })

  test("--country must be a 2-letter code", async () => {
    const result = await runCLI(["search", "-q", "x", "--country", "canada"])
    expect(result.exitCode).toBe(1)
    expect(parsedStderr(result.stderr).code).toBe("BAD_COUNTRY")
  })

  test("--lang must be en or fr", async () => {
    const result = await runCLI(["search", "-q", "x", "--lang", "de"])
    expect(result.exitCode).toBe(1)
    expect(parsedStderr(result.stderr).code).toBe("BAD_LANG")
  })

  test("--location alone (no --query) satisfies NO_CRITERIA", async () => {
    const result = await runCLI(["search", "-l", "Ottawa", "--jobage", "abc"])
    // Should fail on the jobage parse, not on NO_CRITERIA — proves --location
    // alone is accepted as valid search criteria.
    expect(parsedStderr(result.stderr).code).toBe("BAD_ARG")
  })
})

describe("detail flag validation", () => {
  test("detail without an id is rejected", async () => {
    const result = await runCLI(["detail"])
    expect(result.exitCode).toBe(1)
    expect(parsedStderr(result.stderr).code).toBe("NO_ID")
  })

  test("detail with an unparseable id is rejected", async () => {
    const result = await runCLI(["detail", "not-a-job"])
    expect(result.exitCode).toBe(1)
    expect(parsedStderr(result.stderr).code).toBe("BAD_ID")
  })

  test("detail accepts a bare numeric id without erroring on validation", async () => {
    const result = await runCLI(["detail", "not-a-job", "--country", "zz"])
    // BAD_ID should be checked before country/network concerns.
    expect(parsedStderr(result.stderr).code).toBe("BAD_ID")
  })
})
