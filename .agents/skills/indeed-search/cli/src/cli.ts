#!/usr/bin/env bun
import { writeError } from "./helpers.ts"
import { runSearch } from "./commands/search.ts"
import { runDetail } from "./commands/detail.ts"

function printHelp(): void {
  console.log(`indeed-search - Search live Indeed job listings

Usage:
  indeed-search search [flags]
  indeed-search detail <id|url> [flags]

Search flags:
  -q, --query <text>        Keyword search (title, skill, role)
  -l, --location <text>     City or region (default: "Toronto, ON")
      --country <cc>        Country code (default: "canada")
      --jobage <days>       Max posting age in days (default: 14)
      --remote              Filter for remote roles only
  -n, --limit <n>           Result limit (default: 10, max: 30)
      --format <fmt>        Output format: json (default) | table | plain

Detail flags:
      --country <cc>        Country code (default: "canada")
      --format <fmt>        Output format: json (default) | plain

Examples:
  indeed-search search -q "Linux System Administrator" -l "Toronto, ON"
  indeed-search search -q "Cloud" --remote --format table
  indeed-search detail "https://ca.indeed.com/viewjob?jk=3cc5a0e9a92919c5"
`)
}

async function main(): Promise<void> {
  const args = process.argv.slice(2)
  if (args.length === 0 || args.includes("--help") || args.includes("-h")) {
    printHelp()
    process.exit(0)
  }

  const command = args[0]
  if (command !== "search" && command !== "detail") {
    writeError(`Unknown command '${command}'. Use 'search' or 'detail'.`, "INVALID_COMMAND")
    process.exit(1)
  }

  if (command === "search") {
    let query = ""
    let location = "Toronto, ON"
    let country = "canada"
    let jobage = 14
    let limit = 10
    let remote = false
    let format: "json" | "table" | "plain" = "json"

    for (let i = 1; i < args.length; i++) {
      const arg = args[i]
      if (arg === "-q" || arg === "--query") {
        query = args[++i] || ""
      } else if (arg === "-l" || arg === "--location") {
        location = args[++i] || location
      } else if (arg === "--country") {
        country = args[++i] || country
      } else if (arg === "--jobage") {
        const val = parseInt(args[++i], 10)
        if (!isNaN(val)) jobage = val
      } else if (arg === "-n" || arg === "--limit") {
        const val = parseInt(args[++i], 10)
        if (!isNaN(val)) limit = val
      } else if (arg === "--remote") {
        remote = true
      } else if (arg === "--format") {
        const f = args[++i]
        if (f === "json" || f === "table" || f === "plain") format = f
      }
    }

    if (!query && !location) {
      writeError("At least one of --query (-q) or --location (-l) is required.", "MISSING_PARAM")
      process.exit(1)
    }

    const code = await runSearch({ query, location, country, jobage, limit, remote, format })
    process.exit(code)
  } else if (command === "detail") {
    let target = ""
    let format: "json" | "plain" = "json"
    let country = "canada"

    for (let i = 1; i < args.length; i++) {
      const arg = args[i]
      if (arg === "--format") {
        const f = args[++i]
        if (f === "json" || f === "plain") format = f
      } else if (arg === "--country") {
        country = args[++i] || country
      } else if (!target && !arg.startsWith("-")) {
        target = arg
      }
    }

    if (!target) {
      writeError("Missing required job id or URL for detail command.", "MISSING_PARAM")
      process.exit(1)
    }

    const code = await runDetail({ target, format, country })
    process.exit(code)
  }
}

main().catch((err) => {
  writeError(err.message || String(err), "UNHANDLED_ERROR")
  process.exit(1)
})
