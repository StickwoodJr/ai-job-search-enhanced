#!/usr/bin/env python3
"""
Dashboard Generator & Rebuilder for AI Job Search

Reads job_search_tracker.csv and generates a standalone, interactive HTML
dashboard with:
1. Multi-source board filtering (Indeed, Job Bank, TechTO, LinkedIn, Eluta, etc.)
2. Status filters (Drafted, Applied, Interview, Offer, Rejected, etc.)
3. Interactive search and sorting
4. Visual metrics and recruitment pipeline progress
5. Export & sync capability

Usage:
    python scripts/rebuild_dashboard.py [--output reports/application-dashboard.html]
"""

import argparse
import csv
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TRACKER = REPO_ROOT / "job_search_tracker.csv"
DEFAULT_OUTPUT = REPO_ROOT / "reports" / "application-dashboard.html"


def detect_board(source: str, channel: str, notes: str) -> str:
    """Detect the job board or source platform from row metadata."""
    combined = f"{source} {channel} {notes}".lower()
    if "indeed" in combined:
        return "Indeed"
    if "jobbank" in combined or "job bank" in combined or "guichet" in combined:
        return "Job Bank Canada"
    if "techto" in combined:
        return "TechTO"
    if "eluta" in combined:
        return "Eluta"
    if "gcjobs" in combined or "psjobs" in combined or "public service" in combined:
        return "GC Jobs"
    if "linkedin" in combined:
        return "LinkedIn"
    if "talent" in combined:
        return "Talent.com"
    if "freehire" in combined:
        return "Freehire"
    if "company" in combined or "direct" in combined:
        return "Company Direct"
    return "Other / Direct"


def load_tracker(tracker_path: Path) -> list[dict]:
    """Read jobs from tracker CSV."""
    if not tracker_path.exists():
        return []
    jobs = []
    with open(tracker_path, mode="r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not any(row.values()):
                continue
            row["board"] = detect_board(
                row.get("source", ""),
                row.get("channel", ""),
                row.get("notes", "")
            )
            jobs.append(row)
    return jobs


def generate_html(jobs: list[dict], title: str = "AI Job Search Dashboard") -> str:
    """Generate self-contained HTML dashboard."""
    total_jobs = len(jobs)
    statuses = {}
    boards = {}

    for j in jobs:
        s = j.get("status", "Unknown").capitalize()
        statuses[s] = statuses.get(s, 0) + 1
        b = j.get("board", "Other")
        boards[b] = boards.get(b, 0) + 1

    board_options = "".join(f'<option value="{b}">{b} ({cnt})</option>' for b, cnt in sorted(boards.items()))
    status_options = "".join(f'<option value="{s}">{s} ({cnt})</option>' for s, cnt in sorted(statuses.items()))

    # Build job rows
    rows_html = []
    for j in jobs:
        status = j.get("status", "Drafted").capitalize()
        badge_class = {
            "Drafted": "badge-drafted",
            "Applied": "badge-applied",
            "Interview": "badge-interview",
            "Offer": "badge-offer",
            "Rejected": "badge-rejected",
        }.get(status, "badge-default")

        fit_rating = j.get("fit_rating", "N/A")
        cv_link = f'<a href="{j.get("cv_file", "#")}" target="_blank">CV</a>' if j.get("cv_file") else "-"
        cl_link = f'<a href="{j.get("cover_letter_file", "#")}" target="_blank">Letter</a>' if j.get("cover_letter_file") else "-"
        source_url = j.get("source", "")
        source_link = f'<a href="{source_url}" target="_blank">Link</a>' if source_url.startswith("http") else source_url

        rows_html.append(f"""
        <tr data-status="{status.lower()}" data-board="{j.get('board', '').lower()}">
            <td><strong>{j.get('company', 'Unknown')}</strong></td>
            <td>{j.get('role', 'Unknown')}</td>
            <td><span class="badge {badge_class}">{status}</span></td>
            <td><span class="badge-board">{j.get('board', 'N/A')}</span></td>
            <td>{fit_rating}</td>
            <td>{j.get('date', '')}</td>
            <td>{j.get('deadline', '')}</td>
            <td>{cv_link} / {cl_link}</td>
            <td>{source_link}</td>
        </tr>
        """)

    rows_str = "\n".join(rows_html)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        :root {{
            --bg-color: #0d1117;
            --card-bg: #161b22;
            --border-color: #30363d;
            --text-color: #c9d1d9;
            --heading-color: #58a6ff;
            --accent: #238636;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            margin: 0;
            padding: 24px;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 16px;
            margin-bottom: 24px;
        }}
        .header h1 {{ margin: 0; color: #f0f6fc; font-size: 1.8rem; }}
        .header .subtitle {{ color: #8b949e; font-size: 0.9rem; margin-top: 4px; }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}
        .metric-card {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 16px;
            text-align: center;
        }}
        .metric-card .number {{ font-size: 2rem; font-weight: bold; color: #58a6ff; }}
        .metric-card .label {{ color: #8b949e; font-size: 0.85rem; margin-top: 4px; }}
        .controls {{
            display: flex;
            gap: 12px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }}
        .controls input, .controls select {{
            background: var(--card-bg);
            color: var(--text-color);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 8px 12px;
            font-size: 0.9rem;
        }}
        .controls input {{ flex: 1; min-width: 200px; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            overflow: hidden;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
            font-size: 0.88rem;
        }}
        th {{ background: #21262d; color: #f0f6fc; }}
        tr:hover {{ background: #1f242c; }}
        .badge {{
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 600;
        }}
        .badge-drafted {{ background: #2f363d; color: #c9d1d9; }}
        .badge-applied {{ background: #1f6feb; color: #ffffff; }}
        .badge-interview {{ background: #a371f7; color: #ffffff; }}
        .badge-offer {{ background: #238636; color: #ffffff; }}
        .badge-rejected {{ background: #da3633; color: #ffffff; }}
        .badge-board {{
            background: rgba(56, 139, 253, 0.15);
            color: #58a6ff;
            border: 1px solid rgba(56, 139, 253, 0.4);
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.75rem;
        }}
        a {{ color: #58a6ff; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>{title}</h1>
            <div class="subtitle">Generated by AI Job Search on {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
        </div>
        <div style="color: #8b949e; font-size: 0.85rem;">
            Total Tracked: <strong style="color: #f0f6fc;">{total_jobs}</strong>
        </div>
    </div>

    <div class="metrics-grid">
        <div class="metric-card">
            <div class="number">{total_jobs}</div>
            <div class="label">Total Positions</div>
        </div>
        <div class="metric-card">
            <div class="number">{statuses.get('Applied', 0)}</div>
            <div class="label">Submitted</div>
        </div>
        <div class="metric-card">
            <div class="number">{statuses.get('Interview', 0)}</div>
            <div class="label">Interviews</div>
        </div>
        <div class="metric-card">
            <div class="number">{statuses.get('Offer', 0)}</div>
            <div class="label">Offers</div>
        </div>
        <div class="metric-card">
            <div class="number">{len(boards)}</div>
            <div class="label">Job Boards</div>
        </div>
    </div>

    <div class="controls">
        <input type="text" id="searchInput" placeholder="Search company, role, or keywords..." onkeyup="filterTable()">
        <select id="boardFilter" onchange="filterTable()">
            <option value="">All Job Boards</option>
            {board_options}
        </select>
        <select id="statusFilter" onchange="filterTable()">
            <option value="">All Statuses</option>
            {status_options}
        </select>
    </div>

    <table id="jobsTable">
        <thead>
            <tr>
                <th>Company</th>
                <th>Role</th>
                <th>Status</th>
                <th>Board</th>
                <th>Fit</th>
                <th>Date</th>
                <th>Deadline</th>
                <th>Docs</th>
                <th>Source</th>
            </tr>
        </thead>
        <tbody>
            {rows_str}
        </tbody>
    </table>

    <script>
        function filterTable() {{
            const search = document.getElementById('searchInput').value.toLowerCase();
            const board = document.getElementById('boardFilter').value.toLowerCase();
            const status = document.getElementById('statusFilter').value.toLowerCase();
            const rows = document.querySelectorAll('#jobsTable tbody tr');

            rows.forEach(row => {{
                const text = row.innerText.toLowerCase();
                const rowBoard = (row.getAttribute('data-board') || '').toLowerCase();
                const rowStatus = (row.getAttribute('data-status') || '').toLowerCase();

                const matchSearch = !search || text.includes(search);
                const matchBoard = !board || rowBoard === board;
                const matchStatus = !status || rowStatus === status;

                if (matchSearch && matchBoard && matchStatus) {{
                    row.style.display = '';
                }} else {{
                    row.style.display = 'none';
                }}
            }});
        }}
    </script>
</body>
</html>
"""
    return html


def main():
    parser = argparse.ArgumentParser(description="Rebuild AI Job Search HTML Dashboard")
    parser.add_argument("--tracker", type=Path, default=DEFAULT_TRACKER, help="Path to tracker CSV")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output HTML dashboard path")
    parser.add_argument("--title", type=str, default="AI Job Search Application Dashboard", help="Dashboard title")
    args = parser.parse_args()

    jobs = load_tracker(args.tracker)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    html_content = generate_html(jobs, title=args.title)
    args.output.write_text(html_content, encoding="utf-8")
    print(f"✓ Rebuilt dashboard at {args.output} with {len(jobs)} jobs.")


if __name__ == "__main__":
    main()
