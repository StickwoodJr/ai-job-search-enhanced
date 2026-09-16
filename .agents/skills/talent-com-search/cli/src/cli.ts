#!/usr/bin/env bun
// Self-contained CLI for searching jobs on Talent.com's public country-subdomain
// job boards. No external CLI framework, so it runs anywhere `bun` is available
// with zero install beyond the repo clone. Defaults to Canada (ca.talent.com);
// override with --country for any other Talent.com market.

import { runSearch, type SearchOpts } from "./commands/search.js"
import { runDetail, type DetailOpts } from "./commands/detail.js"
import type { Lang } from "./helpers.js"

interface Flags {
  _: string[]
  [k: string]: string | boolean | string[]
}

function parseFlags(argv: string[]): Flags {
  const flags: Flags = { _: [] }
  const alias: Record<string, string> = { q: "query", l: "location", n: "limit" }
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i]
    if (a.startsWith("--") || a.startsWith("-")) {
      const key = alias[a.replace(/^-+/, "")] ?? a.replace(/^-+/, "")
      const next = argv[i + 1]
      if (next === undefined || next.startsWith("-")) {
        flags[key] = true
      } else {
        flags[key] = next
        i++
      }
    } else {
      ;(flags._ as string[]).push(a)
    }
  }
  return flags
}

const HELP = `talent-com-cli — search jobs on Talent.com (Canada by default; any market via --country)

USAGE
  bun run src/cli.ts search [flags]
  bun run src/cli.ts detail <id|url> [--format json|plain]

SEARCH FLAGS
  --query, -q <text>      Keywords (job title, skill, or role).
  --location, -l <text>   City/region, e.g. "Ottawa", "Toronto, ON". Free text.
  --country <cc>          Talent.com country subdomain, e.g. "ca", "us", "uk". Default "ca".
  --lang <en|fr>          English or French listings (ca.talent.com serves both). Default "en".
  --jobage <days>         Posted within N days. Filtered client-side against each
                          listing's last-updated timestamp — Talent.com's own date
                          filter parameter does not affect results. Default: all.
  --page <n>              1-indexed page (~20 results/page). Default 1.
  --limit, -n <n>         Cap results emitted (client-side).
  --format <fmt>          json (default) | table | plain.

At least one of --query or --location is recommended (an empty search browses
Talent.com's full unfiltered feed for the country).

EXAMPLES
  bun run src/cli.ts search -q "AI product manager" -l "Ottawa, ON" --format table
  bun run src/cli.ts search -q "data scientist" -l "Toronto, ON" --jobage 7 --format table
  bun run src/cli.ts search -q "gestionnaire de produits" --lang fr -l Ottawa --format table
  bun run src/cli.ts detail 604692651743716103 --format plain

Data is Talent.com's public, unauthenticated job pages (server-rendered HTML). No
login required. robots.txt allows /jobs and /view; keep volume low regardless.
`

async function main(): Promise<number> {
  const argv = process.argv.slice(2)
  const flags = parseFlags(argv)
  const cmd = (flags._ as string[])[0]

  if (!cmd || flags.help || flags.h) {
    process.stdout.write(HELP)
    return cmd ? 0 : 1
  }

  const parseIntFlag = (name: string, raw: string | boolean | string[]): number | null => {
    const val = parseInt(raw as string, 10)
    if (isNaN(val)) {
      process.stderr.write(JSON.stringify({ error: `--${name} must be a number, got "${raw}"`, code: "BAD_ARG" }) + "\n")
      return null
    }
    return val
  }

  const country = typeof flags.country === "string" ? flags.country.toLowerCase() : "ca"
  if (!/^[a-z]{2}$/.test(country)) {
    process.stderr.write(
      JSON.stringify({ error: `--country must be a 2-letter code, got "${flags.country}"`, code: "BAD_COUNTRY" }) + "\n",
    )
    return 1
  }

  const langRaw = typeof flags.lang === "string" ? flags.lang : "en"
  if (langRaw !== "en" && langRaw !== "fr") {
    process.stderr.write(JSON.stringify({ error: `--lang must be "en" or "fr", got "${langRaw}"`, code: "BAD_LANG" }) + "\n")
    return 1
  }
  const lang = langRaw as Lang

  if (cmd === "search") {
    const query = typeof flags.query === "string" ? flags.query : undefined
    const location = typeof flags.location === "string" ? flags.location : undefined
    if (!query && !location) {
      process.stderr.write(
        JSON.stringify({
          error: "search needs at least one of --query/-q or --location/-l",
          code: "NO_CRITERIA",
        }) + "\n",
      )
      return 1
    }
    const fmt = (flags.format as string) || "json"

    if (flags.jobage !== undefined) {
      if (parseIntFlag("jobage", flags.jobage) === null) return 1
    }
    if (flags.page !== undefined) {
      if (parseIntFlag("page", flags.page) === null) return 1
    }
    if (flags.limit !== undefined) {
      if (parseIntFlag("limit", flags.limit) === null) return 1
    }

    const opts: SearchOpts = {
      query,
      location,
      country,
      lang,
      jobage: flags.jobage ? parseInt(flags.jobage as string, 10) : 9999,
      page: flags.page ? Math.max(1, parseInt(flags.page as string, 10)) : 1,
      limit: flags.limit ? parseInt(flags.limit as string, 10) : undefined,
      format: (["json", "table", "plain"].includes(fmt) ? fmt : "json") as SearchOpts["format"],
    }
    return runSearch(opts)
  }

  if (cmd === "detail") {
    const id = (flags._ as string[])[1]
    if (!id) {
      process.stderr.write(JSON.stringify({ error: "detail requires an <id|url>", code: "NO_ID" }) + "\n")
      return 1
    }
    const fmt = (flags.format as string) || "json"
    const opts: DetailOpts = {
      id,
      country,
      lang,
      format: (fmt === "plain" ? "plain" : "json") as DetailOpts["format"],
    }
    return runDetail(opts)
  }

  process.stderr.write(JSON.stringify({ error: `Unknown command "${cmd}"`, code: "BAD_CMD" }) + "\n")
  return 1
}

main()
  .then((code) => process.exit(code))
  .catch((e) => {
    process.stderr.write(
      JSON.stringify({
        error: e instanceof Error ? e.message : String(e),
        code: "INTERNAL_ERROR",
      }) + "\n",
    )
    process.exit(1)
  })
