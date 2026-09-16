import {
  baseUrl,
  htmlFetch,
  langPrefix,
  parseJobCards,
  withinJobage,
  writeError,
  type JobCard,
  type Lang,
} from "../helpers.js"

export interface SearchOpts {
  query?: string
  location?: string
  country: string
  lang: Lang
  jobage: number
  page: number
  limit?: number
  format: "json" | "table" | "plain"
}

export function buildSearchUrl(opts: SearchOpts): string {
  const params = new URLSearchParams()
  if (opts.query) params.set("k", opts.query)
  if (opts.location) params.set("l", opts.location)
  params.set("p", String(opts.page))
  return `${baseUrl(opts.country)}${langPrefix(opts.lang)}/jobs?${params.toString()}`
}

function renderTable(cards: JobCard[]): string {
  if (cards.length === 0) return "No results."
  const header =
    "ID".padEnd(20) +
    " " +
    "TITLE".padEnd(42) +
    " " +
    "COMPANY".padEnd(26) +
    " " +
    "LOCATION".padEnd(24) +
    " DATE"
  const rows = cards.map((c) =>
    [
      c.id.padEnd(20),
      (c.title || "").slice(0, 42).padEnd(42),
      (c.company || "—").slice(0, 26).padEnd(26),
      (c.location || "—").slice(0, 24).padEnd(24),
      c.date || "—",
    ].join(" "),
  )
  return [header, "-".repeat(header.length), ...rows].join("\n")
}

function renderPlain(cards: JobCard[]): string {
  if (cards.length === 0) return "No results."
  return cards
    .map((c) =>
      [
        c.title,
        `  ${c.company || "—"} · ${c.location || "—"} · ${c.date || "—"}`,
        `  id: ${c.id}`,
        `  ${c.url}`,
      ].join("\n"),
    )
    .join("\n\n")
}

export async function runSearch(opts: SearchOpts): Promise<number> {
  try {
    const html = await htmlFetch(buildSearchUrl(opts))
    let cards = parseJobCards(html, opts.country, opts.lang)
    if (opts.jobage && opts.jobage < 9999) {
      cards = cards.filter((c) => withinJobage(c.date, opts.jobage))
    }
    if (opts.limit !== undefined && opts.limit >= 0) cards = cards.slice(0, opts.limit)

    if (opts.format === "table") {
      process.stdout.write(renderTable(cards) + "\n")
    } else if (opts.format === "plain") {
      process.stdout.write(renderPlain(cards) + "\n")
    } else {
      process.stdout.write(
        JSON.stringify(
          {
            meta: {
              count: cards.length,
              page: opts.page,
              location: opts.location ?? null,
              country: opts.country,
              lang: opts.lang,
              source: `${opts.country}.talent.com`,
            },
            results: cards,
          },
          null,
          2,
        ) + "\n",
      )
    }
    return 0
  } catch (e) {
    writeError(e instanceof Error ? e.message : String(e), "SEARCH_FAILED")
    return 1
  }
}
