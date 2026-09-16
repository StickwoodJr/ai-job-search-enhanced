import { executeBackend, formatTable, writeError, type SearchResponse, type JobCard } from "../helpers.ts"

export interface SearchOpts {
  query?: string
  location?: string
  country?: string
  jobage?: number
  limit?: number
  remote?: boolean
  format?: "json" | "table" | "plain"
}

export async function runSearch(opts: SearchOpts): Promise<number> {
  try {
    const query = opts.query || ""
    const location = opts.location || "Toronto, ON"
    const limit = opts.limit || 10
    const jobage = opts.jobage || 14
    const hoursOld = jobage * 24

    const backendArgs = [query, location, limit.toString(), hoursOld.toString()]
    const res: SearchResponse = await executeBackend("search", backendArgs)

    if (res.error) {
      writeError(res.error, res.code || "SEARCH_FAILED")
      return 1
    }

    const formattedCards = res.results.map((r: JobCard) => ({
      id: r.id,
      title: r.title,
      company: r.company,
      location: r.location,
      date: r.date,
      url: r.url,
    }))

    if (opts.format === "table") {
      process.stdout.write(formatTable(res.results) + "\n")
    } else if (opts.format === "plain") {
      res.results.forEach((r) => {
        process.stdout.write(`[${r.id}] ${r.title} @ ${r.company || "N/A"} (${r.location || "N/A"})\n`)
        process.stdout.write(`URL: ${r.url}\n`)
        if (r.description_snippet) process.stdout.write(`Summary: ${r.description_snippet}\n`)
        process.stdout.write("\n")
      })
    } else {
      process.stdout.write(
        JSON.stringify(
          {
            meta: res.meta,
            results: formattedCards,
          },
          null,
          2
        ) + "\n"
      )
    }
    return 0
  } catch (err: any) {
    writeError(err.message || String(err), "EXECUTION_ERROR")
    return 1
  }
}
