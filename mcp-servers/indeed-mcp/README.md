# Indeed MCP Server (Local Stdio)

A fast, zero-credential, and safe Model Context Protocol (MCP) server for searching Indeed and fetching job posting details.

Designed specifically for **Google Antigravity** and local agentic environments.

## Features

- **100% Free**: No paid proxies, API keys, or accounts required.
- **Bypasses Cloudflare**: Employs client TLS fingerprint emulation (via `jobspy` / `tls-client`) to query Indeed Canada (`ca.indeed.com`) and Indeed global safely.
- **Safe & Polite Defaults**: Caps maximum results at 30 to avoid IP throttling, applies clean timeout handling, and formats output into clean JSON.
- **Native Antigravity Integration**: Runs as a standard `stdio` MCP server configured in `~/.gemini/config/mcp_config.json`.

## Tools Provided

### 1. `indeed_search_jobs`
Search live Indeed job listings.

**Parameters:**
- `query` (string, required): Job title, keywords, or skills (e.g. `"Junior System Administrator"`, `"Linux"`).
- `location` (string, optional, default `"Toronto, ON"`): City or region.
- `country` (string, optional, default `"canada"`): Country code (`"canada"`, `"usa"`, `"uk"`, etc.).
- `results_wanted` (integer, optional, default `10`): Number of results to return (max 30).
- `hours_old` (integer, optional, default `336` / 14 days): Maximum age of postings in hours.
- `is_remote` (boolean, optional, default `false`): Filter for remote positions.

**Returns:**
JSON object with `meta` information and an array of `results` containing:
- `id`: Unique Indeed job ID
- `title`: Position title
- `company`: Company name
- `location`: Job location
- `date`: Posting date
- `url`: Direct Indeed job posting link
- `salary`: Salary range and currency (if provided by employer)
- `description_snippet`: Brief preview of the role

### 2. `indeed_get_job_details`
Retrieve comprehensive job description and requirements.

**Parameters:**
- `job_id_or_url` (string, required): The job ID or full Indeed viewjob URL.
- `country` (string, optional, default `"canada"`): Country code.

**Returns:**
Full job posting JSON including markdown job description, salary, company, and application link.

## Configuration in Antigravity

In `~/.gemini/config/mcp_config.json`:

```json
{
  "mcpServers": {
    "indeed-mcp-server": {
      "command": "/home/gstickwood/gemini-projects/AI Job Search/mcp-servers/indeed-mcp/.venv/bin/python",
      "args": [
        "/home/gstickwood/gemini-projects/AI Job Search/mcp-servers/indeed-mcp/server.py"
      ]
    }
  }
}
```

## Standalone Testing

Run a test query via CLI mode:
```bash
mcp-servers/indeed-mcp/.venv/bin/python mcp-servers/indeed-mcp/server.py search "System Administrator" "Toronto, ON" 5
```

Fetch details for a job ID or URL:
```bash
mcp-servers/indeed-mcp/.venv/bin/python mcp-servers/indeed-mcp/server.py detail "https://ca.indeed.com/viewjob?jk=<id>"
```
