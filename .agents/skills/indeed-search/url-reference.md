# Indeed Search Endpoint Reference

## Overview

- **Service**: Indeed Job Search (`indeed.com` / `ca.indeed.com`)
- **Transport**: Model Context Protocol (MCP) `stdio` / Python `jobspy` bridge
- **Anti-Bot Mechanism**: Cloudflare Bot Management (`cf-mitigated: challenge`, HTTP 403 on standard HTTP clients).
- **Bypass Technique**: Client TLS fingerprint impersonation (`tls-client` / `curl-cffi`) mimicking Google Chrome's JA3/JA4 TLS handshake signatures.

## Endpoints and Hostnames

| Hostname | Region | Default Language |
|----------|--------|------------------|
| `ca.indeed.com` | Canada | English / French |
| `www.indeed.com` | United States / Global | English |
| `uk.indeed.com` | United Kingdom | English |
| `mcp.indeed.com` | Official Remote MCP Server | JSON-RPC 2.0 (OAuth 2.1) |

## Query Parameters and Filters

| Parameter | Type | Description |
|-----------|------|-------------|
| `q` | string | Keyword query (title, company, skills) |
| `l` | string | Location string (city, province/state, postal code) |
| `fromage` | int | Max days old (`1`, `3`, `7`, `14`) |
| `remotejob` | boolean | Remote filter |
| `jk` | string | 16-character hexadecimal job key (e.g. `0b7a690a2369b2ed`) |

## Detail URL Patterns

- Canadian viewjob: `https://ca.indeed.com/viewjob?jk=<jk>`
- Direct job redirect: `http://ca.indeed.com/job/<slug>-<jk>`
