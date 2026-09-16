import { fetchWithBackoff, parseJobsFromHtml, writeError, StandardJobResult } from "../helpers";

interface SearchOptions {
  query?: string;
  location?: string;
  page?: number;
  limit?: number;
  format?: string;
}

export async function handleSearch(options: SearchOptions) {
  if (!options.query || options.query.trim() === "") {
    writeError("Search query is required. Provide --query or -q.", "INVALID_ARGUMENT");
  }

  const page = options.page || 1;
  const limit = options.limit || 20;
  const query = encodeURIComponent(options.query!.trim());
  const location = options.location ? `&location=${encodeURIComponent(options.location.trim())}` : "";
  
  const searchUrl = `https://jobs.techto.org/jobs?query=${query}${location}&page=${page}`;

  try {
    const html = await fetchWithBackoff(searchUrl);
    if (!html) {
      if (options.format === "json") {
        console.log(JSON.stringify({ meta: { count: 0, page, source: "jobs.techto.org" }, results: [] }, null, 2));
      } else {
        console.log("No results found.");
      }
      return;
    }

    let results = parseJobsFromHtml(html);

    // Apply client-side location filter if provided and not matched
    if (options.location) {
      const locLower = options.location.toLowerCase();
      results = results.filter(r => (r.location && r.location.toLowerCase().includes(locLower)) || true);
    }

    results = results.slice(0, limit);

    if (options.format === "table") {
      printTable(results);
    } else if (options.format === "plain") {
      printPlain(results);
    } else {
      console.log(JSON.stringify({
        meta: {
          count: results.length,
          page,
          source: "jobs.techto.org"
        },
        results
      }, null, 2));
    }
  } catch (err: any) {
    writeError(`Failed to fetch TechTO jobs: ${err.message}`, "FETCH_ERROR");
  }
}

function printTable(results: StandardJobResult[]) {
  if (results.length === 0) {
    console.log("No jobs found matching query.");
    return;
  }
  console.log("------------------------------------------------------------------------------------------------------------------------");
  console.log(`| ${"ID".padEnd(12)} | ${"TITLE".padEnd(35)} | ${"COMPANY".padEnd(20)} | ${"LOCATION".padEnd(25)} | ${"DATE".padEnd(12)} |`);
  console.log("------------------------------------------------------------------------------------------------------------------------");
  for (const r of results) {
    const id = r.id.slice(0, 12).padEnd(12);
    const title = (r.title || "").slice(0, 35).padEnd(35);
    const company = (r.company || "N/A").slice(0, 20).padEnd(20);
    const location = (r.location || "N/A").slice(0, 25).padEnd(25);
    const date = (r.date || "N/A").slice(0, 12).padEnd(12);
    console.log(`| ${id} | ${title} | ${company} | ${location} | ${date} |`);
  }
  console.log("------------------------------------------------------------------------------------------------------------------------");
}

function printPlain(results: StandardJobResult[]) {
  for (const r of results) {
    console.log(`[${r.id}] ${r.title} at ${r.company || "Unknown"} (${r.location || "N/A"})\nURL: ${r.url}\n`);
  }
}
