import { handleSearch } from "./commands/search";
import { handleDetail } from "./commands/detail";
import { writeError } from "./helpers";

const args = process.argv.slice(2);
if (args.length === 0 || args[0] === "--help" || args[0] === "-h") {
  printHelp();
  process.exit(0);
}

const command = args[0];

if (command === "search") {
  let query = "";
  let location = "";
  let page = 1;
  let limit = 20;
  let format = "json";

  for (let i = 1; i < args.length; i++) {
    const arg = args[i];
    if (arg === "-q" || arg === "--query") {
      query = args[++i] || "";
    } else if (arg === "-l" || arg === "--location") {
      location = args[++i] || "";
    } else if (arg === "-p" || arg === "--page") {
      page = parseInt(args[++i] || "1", 10);
    } else if (arg === "--limit") {
      limit = parseInt(args[++i] || "20", 10);
    } else if (arg === "-f" || arg === "--format") {
      format = args[++i] || "json";
    }
  }

  handleSearch({ query, location, page, limit, format });
} else if (command === "detail") {
  const target = args[1];
  let format = "json";
  for (let i = 2; i < args.length; i++) {
    if (args[i] === "-f" || args[i] === "--format") {
      format = args[++i] || "json";
    }
  }
  handleDetail(target, format);
} else {
  writeError(`Unknown command: ${command}. Use 'search' or 'detail'.`, "UNKNOWN_COMMAND");
}

function printHelp() {
  console.log(`
techto-search - Search tech jobs on TechTO Jobs (jobs.techto.org)

Usage:
  bun run src/cli.ts search -q "<query>" [options]
  bun run src/cli.ts detail <id|url> [options]

Commands:
  search                  Search job listings
  detail                  Get full job posting description

Search Options:
  -q, --query <string>    Search keyword (required)
  -l, --location <string> Location filter (e.g. Toronto)
  -p, --page <number>     Page number (default: 1)
  --limit <number>        Max results to return (default: 20)
  -f, --format <format>   Output format: json, table, plain (default: json)
`);
}
