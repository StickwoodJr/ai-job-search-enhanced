#!/usr/bin/env python3
"""
Indeed MCP Server
Provides Indeed job search tools via the Model Context Protocol (MCP).
Optimized for local, safe, and free execution in Google Antigravity.
"""

import json
import logging
import os
import re
import sys
from typing import Any, Dict, List, Optional
import requests

# Configure logging to stderr so stdout remains clean for MCP stdio transport
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger("indeed-mcp")

try:
    from jobspy import scrape_jobs
    from jobspy.indeed.constant import api_headers
    from jobspy.util import markdown_converter
    from jobspy.model import Country
except ImportError as e:
    logger.error("Missing python-jobspy: %s", e)
    logger.error("Please run: pip install -r requirements.txt in your virtual environment")
    sys.exit(1)

# Handle both MCP 2.x (MCPServer) and MCP 1.x (FastMCP)
try:
    from mcp.server.mcpserver import MCPServer
    mcp = MCPServer(name="Indeed Job Search")
except ImportError:
    try:
        from mcp.server.fastmcp import FastMCP
        mcp = FastMCP("Indeed Job Search")
    except ImportError as e:
        logger.error("Missing mcp package: %s", e)
        sys.exit(1)


def _clean_val(val: Any) -> Any:
    """Helper to convert pandas / numpy NaN values to None / JSON friendly types."""
    if val is None:
        return None
    try:
        import pandas as pd
        if pd.isna(val):
            return None
    except Exception:
        pass
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return str(val) if not isinstance(val, (int, float, bool, list, dict)) else val


def _extract_jk(target: str) -> Optional[str]:
    """Extract a 16-character Indeed job key (jk) from URL or ID."""
    if not target:
        return None
    target = target.strip()
    # Match in-xxxxxxxxxxxxxxxx
    if target.startswith("in-"):
        target = target[3:]
    # Match jk query param: jk=xxxxxxxxxxxxxxxx
    m = re.search(r"jk=([a-f0-9]{16})", target, re.IGNORECASE)
    if m:
        return m.group(1)
    # Match 16 hex characters directly
    m2 = re.search(r"\b([a-f0-9]{16})\b", target, re.IGNORECASE)
    if m2:
        return m2.group(1)
    return target


def perform_search(
    query: str,
    location: str = "Toronto, ON",
    country: str = "canada",
    results_wanted: int = 10,
    hours_old: int = 336,
    is_remote: bool = False,
) -> Dict[str, Any]:
    """Underlying search implementation."""
    safe_results_wanted = max(1, min(results_wanted, 100))
    logger.info(
        "Searching Indeed: query='%s', location='%s', country='%s', limit=%d, hours_old=%d",
        query,
        location,
        country,
        safe_results_wanted,
        hours_old,
    )

    try:
        jobs_df = scrape_jobs(
            site_name=["indeed"],
            search_term=query,
            location=location,
            results_wanted=safe_results_wanted,
            hours_old=hours_old,
            country_indeed=country,
            is_remote=is_remote,
            description_format="markdown",
            verbose=0,
        )

        if jobs_df is None or jobs_df.empty:
            return {"meta": {"count": 0, "query": query, "location": location}, "results": []}

        results: List[Dict[str, Any]] = []
        for _, row in jobs_df.iterrows():
            job_dict = {
                "id": _clean_val(row.get("id")),
                "title": _clean_val(row.get("title")),
                "company": _clean_val(row.get("company")),
                "location": _clean_val(row.get("location")),
                "date": _clean_val(row.get("date_posted")),
                "url": _clean_val(row.get("job_url")),
                "direct_url": _clean_val(row.get("job_url_direct")),
                "salary": {
                    "min": _clean_val(row.get("min_amount")),
                    "max": _clean_val(row.get("max_amount")),
                    "currency": _clean_val(row.get("currency")),
                    "interval": _clean_val(row.get("interval")),
                },
                "is_remote": bool(row.get("is_remote")) if row.get("is_remote") is not None else False,
                "description_snippet": (
                    str(row.get("description", ""))[:300] + "..."
                    if row.get("description")
                    else None
                ),
            }
            results.append(job_dict)

        return {
            "meta": {
                "count": len(results),
                "query": query,
                "location": location,
                "country": country,
            },
            "results": results,
        }

    except Exception as e:
        logger.error("Error executing Indeed search: %s", e)
        return {
            "error": str(e),
            "code": "SEARCH_FAILED",
            "meta": {"count": 0, "query": query, "location": location},
            "results": [],
        }


def perform_detail(job_id_or_url: str, country: str = "canada") -> Dict[str, Any]:
    """Underlying detail lookup implementation using Indeed GraphQL API."""
    logger.info("Fetching job details for: %s", job_id_or_url)
    jk = _extract_jk(job_id_or_url)
    if not jk:
        return {"error": "Invalid job identifier or URL", "code": "INVALID_ID"}

    try:
        co_code = "CA" if country.lower() in ("canada", "ca") else "US"
        headers = api_headers.copy()
        headers["indeed-co"] = co_code

        gql_query = """
        query GetJobDetail {
            jobData(jobKeys: ["%s"]) {
                results {
                    job {
                        key
                        title
                        datePublished
                        dateOnIndeed
                        description {
                            html
                        }
                        employer {
                            name
                            relativeCompanyPageUrl
                        }
                        location {
                            formatted {
                                short
                                long
                            }
                            city
                            admin1Code
                            countryCode
                        }
                        compensation {
                            baseSalary {
                                unitOfWork
                                range {
                                    ... on Range {
                                        min
                                        max
                                    }
                                }
                            }
                            currencyCode
                        }
                        recruit {
                            viewJobUrl
                            detailedSalary
                            workSchedule
                        }
                    }
                }
            }
        }
        """ % jk

        res = requests.post(
            "https://apis.indeed.com/graphql",
            json={"query": gql_query},
            headers=headers,
            timeout=10,
        )

        if not res.ok:
            return {
                "error": f"Indeed API returned HTTP {res.status_code}",
                "code": "UPSTREAM_ERROR",
            }

        data = res.json()
        results = data.get("data", {}).get("jobData", {}).get("results", [])
        if not results or not results[0].get("job"):
            return {"error": f"Job posting '{jk}' not found or expired", "code": "NOT_FOUND"}

        job = results[0]["job"]
        employer = job.get("employer") or {}
        location_obj = job.get("location") or {}
        formatted_loc = location_obj.get("formatted") or {}
        loc_str = formatted_loc.get("long") or formatted_loc.get("short") or location_obj.get("city")

        comp = job.get("compensation") or {}
        base_salary = comp.get("baseSalary") or {}
        sal_range = base_salary.get("range") or {}

        recruit = job.get("recruit") or {}
        desc_html = (job.get("description") or {}).get("html") or ""
        desc_md = markdown_converter(desc_html) if desc_html else None

        raw_date = job.get("datePublished") or job.get("dateOnIndeed")
        formatted_date = None
        if raw_date:
            try:
                if isinstance(raw_date, (int, float)):
                    from datetime import datetime, timezone
                    formatted_date = datetime.fromtimestamp(raw_date / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
                else:
                    formatted_date = str(raw_date)[:10]
            except Exception:
                formatted_date = str(raw_date)

        domain = "ca.indeed.com" if co_code == "CA" else "www.indeed.com"
        job_url = f"https://{domain}/viewjob?jk={jk}"
        apply_url = recruit.get("viewJobUrl") or job_url

        return {
            "id": f"in-{jk}",
            "title": job.get("title"),
            "company": employer.get("name"),
            "location": loc_str,
            "date": formatted_date,
            "url": job_url,
            "apply_url": apply_url,
            "salary": {
                "min": sal_range.get("min"),
                "max": sal_range.get("max"),
                "currency": comp.get("currencyCode"),
                "interval": base_salary.get("unitOfWork"),
            },
            "work_schedule": recruit.get("workSchedule"),
            "description": desc_md,
        }

    except Exception as e:
        logger.error("Error fetching job details: %s", e)
        return {"error": str(e), "code": "DETAIL_FETCH_FAILED"}


@mcp.tool()
def indeed_search_jobs(
    query: str,
    location: str = "Toronto, ON",
    country: str = "canada",
    results_wanted: int = 10,
    hours_old: int = 336,
    is_remote: bool = False,
) -> str:
    """
    Search live job listings on Indeed without authentication.

    Parameters:
    - query: Job title, keywords, or skills (e.g. 'Junior System Administrator', 'Linux')
    - location: City or region (e.g. 'Toronto, ON', 'York Region, ON', 'Remote')
    - country: Indeed country code (default 'canada', also 'usa', 'uk', etc.)
    - results_wanted: Max number of results to return (capped at 30 for safety)
    - hours_old: Max age of postings in hours (e.g. 72 for 3 days, 336 for 14 days)
    - is_remote: Whether to filter for remote positions
    """
    res = perform_search(
        query=query,
        location=location,
        country=country,
        results_wanted=results_wanted,
        hours_old=hours_old,
        is_remote=is_remote,
    )
    return json.dumps(res, indent=2)


@mcp.tool()
def indeed_get_job_details(job_id_or_url: str, country: str = "canada") -> str:
    """
    Fetch the full posting details for a specific Indeed job by its ID or posting URL.

    Parameters:
    - job_id_or_url: The Indeed job ID (e.g. from search results) or full Indeed job posting URL
    - country: Indeed country code (default 'canada')
    """
    res = perform_detail(job_id_or_url=job_id_or_url, country=country)
    return json.dumps(res, indent=2)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "search":
        q = sys.argv[2] if len(sys.argv) > 2 else "Software"
        loc = sys.argv[3] if len(sys.argv) > 3 else "Toronto, ON"
        limit = int(sys.argv[4]) if len(sys.argv) > 4 else 5
        print(json.dumps(perform_search(query=q, location=loc, results_wanted=limit), indent=2))
    elif len(sys.argv) > 1 and sys.argv[1] == "detail":
        target = sys.argv[2] if len(sys.argv) > 2 else ""
        print(json.dumps(perform_detail(target), indent=2))
    else:
        # Run stdio MCP server
        mcp.run(transport="stdio")
