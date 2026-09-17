#!/usr/bin/env python3
"""
Update application-dashboard.html and job_search_tracker.csv with:
1. Job board filter (multi-select dropdown + quick presets for Indeed, Jobs Canada, Indeed + Jobs Canada, LinkedIn, etc.)
2. Visual board badges on each posting row
3. Tagging data-board attribute on all rows
4. Adding top Indeed postings to tracker and dashboard
"""

import csv
import re
import subprocess
from pathlib import Path
from bs4 import BeautifulSoup

REPO_ROOT = Path(__file__).resolve().parent.parent
DASHBOARD_FILE = REPO_ROOT / "reports" / "application-dashboard.html"
TRACKER_FILE = REPO_ROOT / "job_search_tracker.csv"

# Top newly discovered Indeed postings
INDEED_POSTINGS = [
    {
        "date": "2026-09-10",
        "company": "ThinkOn Incorporated (Cloud Infrastructure & Storage Operations Practice)",
        "role": "IT Network Technician (Cisco Routing, Network Infrastructure & NOC Telemetry)",
        "location": "Toronto, ON (Downtown HQ Hybrid - ~50 km from Newmarket)",
        "status": "Drafted",
        "deadline": "Rolling",
        "fit": 96,
        "ref": "1fbf02a466fc5a2a",
        "url": "https://ca.indeed.com/viewjob?jk=1fbf02a466fc5a2a",
        "cv": "cv/main_ThinkOn_Incorporated_IT_Network_Technician.pdf",
        "cl": "cover_letters/cover_ThinkOn_Incorporated_IT_Network_Technician.pdf",
        "notes": "Scraped from Indeed Canada. Cisco routing, Linux, network operations, zero-trust infrastructure.",
        "distance": 50,
        "region": "gta core",
        "overall": 88,
        "chance": 68,
        "prestige": 85,
        "pay": "30.00",
        "pay_str": "$28.00 – $32.00/hr <span style='font-size:0.75em;opacity:0.8;'>(Co-op)</span>"
    },
    {
        "date": "2026-09-10",
        "company": "Scotiabank (Velocity Enterprise Technology - Cloud Architecture Group)",
        "role": "Velocity - Cloud Engineer Internship/Co-Op - Winter 2027",
        "location": "Toronto Financial District Corporate HQ, ON (Cloud Operations Hybrid - ~50 km from Newmarket)",
        "status": "Drafted",
        "deadline": "2026-09-25",
        "fit": 95,
        "ref": "38c11930263659db",
        "url": "https://ca.indeed.com/viewjob?jk=38c11930263659db",
        "cv": "cv/main_Scotiabank_Velocity_Cloud_Engineer_Coop.pdf",
        "cl": "cover_letters/cover_Scotiabank_Velocity_Cloud_Engineer_Coop.pdf",
        "notes": "Scraped from Indeed Canada. Official 4-month Winter 2027 Co-op in cloud systems and container infrastructure.",
        "distance": 50,
        "region": "gta core",
        "overall": 92,
        "chance": 65,
        "prestige": 92,
        "pay": "32.00",
        "pay_str": "$30.00 – $34.00/hr <span style='font-size:0.75em;opacity:0.8;'>(Co-op)</span>"
    },
    {
        "date": "2026-09-10",
        "company": "Pelmorex Corp (The Weather Network - Broadcast & Infrastructure Operations)",
        "role": "IT Infrastructure Administrator (Linux Servers, Active Directory & High-Availability Systems)",
        "location": "Oakville / Halton Region Canadian HQ, ON (IT Operations Hybrid - ~75 km from Newmarket)",
        "status": "Drafted",
        "deadline": "Rolling",
        "fit": 94,
        "ref": "c3e4b78cae73e154",
        "url": "https://ca.indeed.com/viewjob?jk=c3e4b78cae73e154",
        "cv": "cv/main_Pelmorex_IT_Infrastructure_Administrator.pdf",
        "cl": "cover_letters/cover_Pelmorex_IT_Infrastructure_Administrator.pdf",
        "notes": "Scraped from Indeed Canada. High availability Linux infrastructure, server virtualization, automated backups.",
        "distance": 75,
        "region": "halton region",
        "overall": 85,
        "chance": 70,
        "prestige": 82,
        "pay": "29.00",
        "pay_str": "$27.00 – $31.00/hr"
    },
    {
        "date": "2026-09-10",
        "company": "S&C Electric Company (Power Grid & Industrial Infrastructure Systems)",
        "role": "Junior Systems Administrator (Co-op) - Winter 2027",
        "location": "Toronto, ON (North York / Etobicoke Industrial Park - ~42 km from Newmarket)",
        "status": "Drafted",
        "deadline": "Rolling",
        "fit": 96,
        "ref": "9807530635f79ca8",
        "url": "https://ca.indeed.com/viewjob?jk=9807530635f79ca8",
        "cv": "cv/main_SC_Electric_Junior_Systems_Administrator_Coop.pdf",
        "cl": "cover_letters/cover_SC_Electric_Junior_Systems_Administrator_Coop.pdf",
        "notes": "Scraped from Indeed Canada. Windows Server admin, VMware virtualization, endpoint automation, network cabling.",
        "distance": 42,
        "region": "toronto north",
        "overall": 89,
        "chance": 72,
        "prestige": 84,
        "pay": "28.00",
        "pay_str": "$26.00 – $30.00/hr <span style='font-size:0.75em;opacity:0.8;'>(Co-op)</span>"
    },
    {
        "date": "2026-09-10",
        "company": "Google Canada (Cloud Infrastructure & Global Data Center Network)",
        "role": "Data Center Technician (Server Hardware, Networking Protocols & Linux Systems)",
        "location": "Toronto, ON (Downtown Data Operations - ~50 km from Newmarket)",
        "status": "Drafted",
        "deadline": "Rolling",
        "fit": 95,
        "ref": "77d0fa34829ded8d",
        "url": "https://ca.indeed.com/viewjob?jk=77d0fa34829ded8d",
        "cv": "cv/main_Google_Data_Center_Technician.pdf",
        "cl": "cover_letters/cover_Google_Data_Center_Technician.pdf",
        "notes": "Scraped from Indeed Canada. Component-level server troubleshooting, networking protocols, Linux administration.",
        "distance": 50,
        "region": "gta core",
        "overall": 94,
        "chance": 52,
        "prestige": 98,
        "pay": "35.00",
        "pay_str": "$32.00 – $38.00/hr"
    },
    {
        "date": "2026-09-10",
        "company": "BGIS (Global Integrated Facility Management & Enterprise IT Infrastructure Practice)",
        "role": "IT Support Specialist (Enterprise Endpoints, Active Directory & Network Fleet)",
        "location": "Markham / York Region Canadian HQ, ON (IT Service Operations - ~28 km from Newmarket)",
        "status": "Drafted",
        "deadline": "Rolling",
        "fit": 95,
        "ref": "5c9a87d0e9a59b20",
        "url": "https://ca.indeed.com/viewjob?jk=5c9a87d0e9a59b20",
        "cv": "cv/main_BGIS_IT_Support_Specialist_Markham.pdf",
        "cl": "cover_letters/cover_BGIS_IT_Support_Specialist_Markham.pdf",
        "notes": "Scraped from Indeed Canada. Super close commute in Markham/York Region. AD DS, GPO, M365, VPN deployments.",
        "distance": 28,
        "region": "york region",
        "overall": 91,
        "chance": 75,
        "prestige": 85,
        "pay": "27.00",
        "pay_str": "$25.00 – $29.00/hr"
    }
]

def update_tracker():
    print(f"Reading tracker from {TRACKER_FILE}...")
    existing_urls = set()
    rows = []
    with open(TRACKER_FILE, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows.append(header)
        for r in reader:
            rows.append(r)
            if len(r) >= 9:
                existing_urls.add(r[8].strip())

    added_count = 0
    for p in INDEED_POSTINGS:
        if p["url"] not in existing_urls:
            new_row = [
                p["date"],
                p["company"],
                p["role"],
                p["location"],
                p["status"],
                p["deadline"],
                str(p["fit"]),
                p["ref"],
                p["url"],
                p["cv"],
                p["cl"],
                p["notes"]
            ]
            rows.append(new_row)
            existing_urls.add(p["url"])
            added_count += 1

    with open(TRACKER_FILE, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    print(f"Added {added_count} Indeed postings to {TRACKER_FILE}. Total rows: {len(rows)-1}")

def get_board_info(url):
    url_lower = (url or "").lower()
    if "indeed" in url_lower:
        return "indeed", "Indeed", "badge-indeed"
    if "jobbank" in url_lower or "guichet" in url_lower or "jobs.gc.ca" in url_lower:
        return "jobbank", "Jobs Canada", "badge-jobbank"
    if "linkedin" in url_lower:
        return "linkedin", "LinkedIn", "badge-linkedin"
    if "talent.com" in url_lower:
        return "talent", "Talent.com", "badge-talent"
    if "eluta" in url_lower:
        return "eluta", "Eluta", "badge-eluta"
    if "emploisfp" in url_lower or "canada.ca" in url_lower or "cfp-psc" in url_lower:
        return "gcjobs", "GC Jobs", "badge-gcjobs"
    if "techto" in url_lower:
        return "techto", "TechTO", "badge-techto"
    return "direct", "Direct", "badge-direct"

def update_dashboard():
    print(f"Updating HTML dashboard at {DASHBOARD_FILE}...")
    html = DASHBOARD_FILE.read_text(encoding="utf-8")

    # 1. Add CSS for board filter & badges
    board_css = """
/* Job Board Multi-Select & Badges */
.board-filter-wrapper {
  position: relative;
  flex: 1;
  min-width: 200px;
}

.board-select-btn {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 9px 14px;
  background: var(--card-bg);
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  outline: none;
  text-align: left;
}
.board-select-btn:hover, .board-select-btn.active {
  border-color: var(--status-active);
}

.board-menu {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  min-width: 290px;
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  box-shadow: 0 10px 25px rgba(0,0,0,0.15);
  z-index: 100;
  padding: 8px 0;
  display: block;
}
.board-menu.hidden {
  display: none;
}

.board-menu-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 14px 8px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 6px;
}
.board-menu-title {
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.board-menu-actions {
  display: flex;
  gap: 8px;
}
.board-action-btn {
  background: none;
  border: none;
  color: var(--status-active);
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 4px;
}
.board-action-btn:hover {
  text-decoration: underline;
}

.board-menu-items {
  max-height: 280px;
  overflow-y: auto;
  padding: 2px 6px;
}
.board-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.85rem;
  user-select: none;
}
.board-item:hover {
  background: var(--row-hover);
}
.board-item input[type="checkbox"] {
  accent-color: var(--status-active);
  cursor: pointer;
  width: 15px;
  height: 15px;
}
.board-item-label {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.board-count {
  font-size: 0.78rem;
  color: var(--text-muted);
  margin-left: auto;
  margin-right: 6px;
}
.board-only-btn {
  font-size: 0.72rem;
  color: var(--text-muted);
  background: var(--row-alt);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 1px 5px;
  cursor: pointer;
  opacity: 0.7;
}
.board-only-btn:hover {
  opacity: 1;
  color: var(--status-active);
  border-color: var(--status-active);
}

/* Quick Filter Chips */
.board-quick-chips {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
  padding: 4px 0;
}
.chips-label {
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-right: 2px;
}
.quick-chip {
  background: var(--card-bg);
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 5px 12px;
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.03);
}
.quick-chip:hover {
  border-color: var(--status-active);
  color: var(--status-active);
}
.quick-chip.active {
  background: var(--badge-active-bg);
  color: var(--badge-active-text);
  border-color: var(--status-active);
}

/* Board Badges in Table */
.board-badge {
  display: inline-block;
  padding: 2px 7px;
  border-radius: 4px;
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  margin-right: 6px;
  vertical-align: middle;
}
.badge-indeed { background: #e0e7ff; color: #3730a3; border: 1px solid #c7d2fe; }
.badge-jobbank { background: #ffe4e6; color: #9f1239; border: 1px solid #fecdd3; }
.badge-linkedin { background: #e0f2fe; color: #075985; border: 1px solid #bae6fd; }
.badge-talent { background: #dcfce7; color: #166534; border: 1px solid #bbf7d0; }
.badge-eluta { background: #fef3c7; color: #92400e; border: 1px solid #fde68a; }
.badge-gcjobs { background: #fee2e2; color: #991b1b; border: 1px solid #fecaca; }
.badge-direct { background: #f1f5f9; color: #475569; border: 1px solid #e2e8f0; }

[data-theme="dark"] .badge-indeed { background: #312e81; color: #c7d2fe; border-color: #4338ca; }
[data-theme="dark"] .badge-jobbank { background: #881337; color: #fecdd3; border-color: #9f1239; }
[data-theme="dark"] .badge-linkedin { background: #0c4a6e; color: #bae6fd; border-color: #0369a1; }
[data-theme="dark"] .badge-talent { background: #14532d; color: #bbf7d0; border-color: #16a34a; }
[data-theme="dark"] .badge-eluta { background: #78350f; color: #fde68a; border-color: #b45309; }
[data-theme="dark"] .badge-gcjobs { background: #7f1d1d; color: #fecaca; border-color: #991b1b; }
[data-theme="dark"] .badge-direct { background: #1e293b; color: #cbd5e1; border-color: #334155; }
"""

    # Inject CSS before </style>
    if "/* Job Board Multi-Select & Badges */" not in html:
        html = html.replace("</style>", f"{board_css}\n</style>")

    # 2. Tag every existing <tr> with data-board and board badge
    soup = BeautifulSoup(html, "html.parser")

    board_counts = {}
    rows = soup.find_all("tr", attrs={"data-index": True})
    for r in rows:
        link = r.find("a", class_="posting")
        href = link["href"] if link and link.get("href") else ""
        board_id, board_name, badge_class = get_board_info(href)
        r["data-board"] = board_id
        board_counts[board_id] = board_counts.get(board_id, 0) + 1

        # Check if badge already injected
        cell_actions = r.find("td", class_="cell-actions")
        if cell_actions and not cell_actions.find("span", class_="board-badge"):
            badge_span = soup.new_tag("span", **{"class": f"board-badge {badge_class}"})
            badge_span.string = board_name
            cell_actions.insert(0, " ")
            cell_actions.insert(0, badge_span)

    # 3. Add Indeed rows to table-body if not present
    tbody = soup.find("tbody", id="table-body")
    existing_urls = {r.find("a", class_="posting")["href"] for r in rows if r.find("a", class_="posting")}
    
    current_index = len(rows)
    for p in INDEED_POSTINGS:
        if p["url"] in existing_urls:
            continue
        board_id = "indeed"
        board_counts[board_id] = board_counts.get(board_id, 0) + 1

        row_tr = soup.new_tag("tr", **{
            "data-index": str(current_index),
            "data-distance": str(p["distance"]),
            "data-region": p["region"],
            "data-overall": str(p["overall"]),
            "data-fit": str(p["fit"]),
            "data-chance": str(p["chance"]),
            "data-prestige": str(p["prestige"]),
            "data-pay": p["pay"],
            "data-date": p["date"],
            "data-company": p["company"].lower(),
            "data-status": p["status"],
            "data-board": board_id,
        })

        prox_class = "prox-gta" if p["region"] == "gta core" else ("prox-york" if p["region"] == "york region" else "prox-toronto-north")
        prox_label = "GTA Core" if p["region"] == "gta core" else ("York Region" if p["region"] == "york region" else "Toronto North")

        row_html = f"""
          <td class="cell-date">{p["date"]}</td>
          <td class="cell-company"><strong>{p["company"]}</strong></td>
          <td class="cell-distance"><span class="badge-proximity {prox_class}" title="{p["location"]}"><strong>~{p["distance"]} km</strong> <span class="prox-label">{prox_label}</span></span></td>
          <td class="cell-overall"><span class="badge-overall overall-a"><strong>{p["overall"]}</strong> <span class="overall-grade-tag">A-Tier</span></span></td>
          <td class="cell-prestige"><span class="badge-prestige prestige-tier1">★★★★★ <span class="prestige-tier-text">Tier 1</span></span></td>
          <td class="cell-chance"><span class="badge-chance chance-high">{p["chance"]}% <span class="chance-label-text">(High)</span></span></td>
          <td class="cell-role">{p["role"]}</td>
          <td class="cell-location">{p["location"]}</td>
          <td class="cell-fit"><span class="fit-score">{p["fit"]}%</span></td>
          <td class="cell-pay"><span class="pay-tag">{p["pay_str"]}</span></td>
          <td class="cell-status"><span class="badge badge-drafted">{p["status"]}</span></td>
          <td class="cell-deadline">{p["deadline"]}</td>
          <td class="cell-actions"><span class="board-badge badge-indeed">Indeed</span> <a class="link-btn posting" href="{p["url"]}" target="_blank">Posting</a> &bull; <a class="link-btn cv" href="../{p["cv"]}" target="_blank">CV</a> &bull; <a class="link-btn cl" href="../{p["cl"]}" target="_blank">Cover Letter</a></td>
        """
        row_tr.append(BeautifulSoup(row_html, "html.parser"))
        tbody.insert(0, row_tr)
        current_index += 1

    # Update total count
    total_listings = len(tbody.find_all("tr", attrs={"data-index": True}))
    stat_total_num = soup.find("div", class_="stat-card total")
    if stat_total_num:
        num_el = stat_total_num.find("div", class_="stat-num")
        if num_el: num_el.string = str(total_listings)

    stat_draft_num = soup.find("div", class_="stat-card", attrs={"style": lambda s: s and "status-draft" in s})
    # or first stat-card after total
    stat_cards = soup.find_all("div", class_="stat-card")
    if len(stat_cards) > 1:
        stat_cards[1].find("div", class_="stat-num").string = str(total_listings)

    html_str = str(soup)

    # 4. Insert Job Board Multi-Select into table-controls
    board_control_html = """
      <div class="board-filter-wrapper" id="board-filter-wrapper">
        <button type="button" id="board-select-btn" class="board-select-btn" title="Filter by job posting source board">
          <span id="board-btn-text">🌐 Job Boards (All)</span>
          <span>▾</span>
        </button>
        <div id="board-menu" class="board-menu hidden">
          <div class="board-menu-header">
            <span class="board-menu-title">Select Job Boards</span>
            <div class="board-menu-actions">
              <button type="button" id="board-all-btn" class="board-action-btn">All</button>
              <button type="button" id="board-none-btn" class="board-action-btn">None</button>
            </div>
          </div>
          <div class="board-menu-items">
            <label class="board-item">
              <input type="checkbox" class="board-checkbox" value="indeed" checked>
              <div class="board-item-label">
                <span><span class="board-badge badge-indeed">Indeed</span> Indeed Canada</span>
                <span class="board-count" id="count-indeed">({indeed_count})</span>
              </div>
              <button type="button" class="board-only-btn" data-board="indeed" title="Show only Indeed">only</button>
            </label>
            <label class="board-item">
              <input type="checkbox" class="board-checkbox" value="jobbank" checked>
              <div class="board-item-label">
                <span><span class="board-badge badge-jobbank">Jobs Canada</span> Job Bank</span>
                <span class="board-count" id="count-jobbank">({jobbank_count})</span>
              </div>
              <button type="button" class="board-only-btn" data-board="jobbank" title="Show only Job Bank / Jobs Canada">only</button>
            </label>
            <label class="board-item">
              <input type="checkbox" class="board-checkbox" value="linkedin" checked>
              <div class="board-item-label">
                <span><span class="board-badge badge-linkedin">LinkedIn</span> LinkedIn Jobs</span>
                <span class="board-count" id="count-linkedin">({linkedin_count})</span>
              </div>
              <button type="button" class="board-only-btn" data-board="linkedin" title="Show only LinkedIn">only</button>
            </label>
            <label class="board-item">
              <input type="checkbox" class="board-checkbox" value="talent" checked>
              <div class="board-item-label">
                <span><span class="board-badge badge-talent">Talent.com</span> Talent.com</span>
                <span class="board-count" id="count-talent">({talent_count})</span>
              </div>
              <button type="button" class="board-only-btn" data-board="talent" title="Show only Talent.com">only</button>
            </label>
            <label class="board-item">
              <input type="checkbox" class="board-checkbox" value="eluta" checked>
              <div class="board-item-label">
                <span><span class="board-badge badge-eluta">Eluta</span> Eluta.ca</span>
                <span class="board-count" id="count-eluta">({eluta_count})</span>
              </div>
              <button type="button" class="board-only-btn" data-board="eluta" title="Show only Eluta">only</button>
            </label>
            <label class="board-item">
              <input type="checkbox" class="board-checkbox" value="gcjobs" checked>
              <div class="board-item-label">
                <span><span class="board-badge badge-gcjobs">GC Jobs</span> Federal Jobs</span>
                <span class="board-count" id="count-gcjobs">(0)</span>
              </div>
              <button type="button" class="board-only-btn" data-board="gcjobs" title="Show only GC Jobs">only</button>
            </label>
            <label class="board-item">
              <input type="checkbox" class="board-checkbox" value="direct" checked>
              <div class="board-item-label">
                <span><span class="board-badge badge-direct">Direct</span> Employer Direct</span>
                <span class="board-count" id="count-direct">({direct_count})</span>
              </div>
              <button type="button" class="board-only-btn" data-board="direct" title="Show only Direct">only</button>
            </label>
          </div>
        </div>
      </div>
    """.format(
        indeed_count=board_counts.get("indeed", 6),
        jobbank_count=board_counts.get("jobbank", 3),
        linkedin_count=board_counts.get("linkedin", 238),
        talent_count=board_counts.get("talent", 51),
        eluta_count=board_counts.get("eluta", 8),
        direct_count=board_counts.get("direct", 1),
    )

    quick_chips_html = """
    <div class="board-quick-chips">
      <span class="chips-label">Board Presets:</span>
      <button type="button" class="quick-chip active" data-preset="all">🌐 All Boards</button>
      <button type="button" class="quick-chip" data-preset="indeed"><span class="board-badge badge-indeed" style="margin-right:2px;">Indeed</span> Indeed Canada</button>
      <button type="button" class="quick-chip" data-preset="jobbank"><span class="board-badge badge-jobbank" style="margin-right:2px;">Jobs Canada</span> Job Bank</button>
      <button type="button" class="quick-chip" data-preset="indeed-jobbank">🎯 Indeed + Jobs Canada</button>
      <button type="button" class="quick-chip" data-preset="linkedin"><span class="board-badge badge-linkedin" style="margin-right:2px;">LinkedIn</span> LinkedIn</button>
      <button type="button" class="quick-chip" data-preset="talent"><span class="board-badge badge-talent" style="margin-right:2px;">Talent</span> Talent.com</button>
      <button type="button" class="quick-chip" data-preset="eluta"><span class="board-badge badge-eluta" style="margin-right:2px;">Eluta</span> Eluta</button>
    </div>
    """

    if 'id="board-filter-wrapper"' not in html_str:
        # Place board_control_html after id="region-filter"
        target = '</select>\n      <select class="sort-select" id="sort-select">'
        if target in html_str:
            html_str = html_str.replace(target, f'</select>\n{board_control_html}\n      <select class="sort-select" id="sort-select">')
        else:
            # alternative
            html_str = re.sub(r'(id="region-filter"[^>]*>[\s\S]*?</select>)', r'\1\n' + board_control_html, html_str)

    if 'class="board-quick-chips"' not in html_str:
        # Place quick_chips_html right after class="table-controls" closing </div>
        html_str = re.sub(r'(</div>\s*<div class="table-stats-bar">)', r'</div>\n' + quick_chips_html + r'\n    <div class="table-stats-bar">', html_str)

    # 5. Update JavaScript filterAndSort logic
    updated_js = """
// Table Filtering and Sorting
const searchBox = document.getElementById('search-box');
const statusFilter = document.getElementById('status-filter');
const regionFilter = document.getElementById('region-filter');
const sortSelect = document.getElementById('sort-select');
const tbody = document.getElementById('table-body');
const showingCount = document.getElementById('showing-count');
const ths = document.querySelectorAll('th[data-col]');

// Job Board Multi-Select Elements
const boardSelectBtn = document.getElementById('board-select-btn');
const boardBtnText = document.getElementById('board-btn-text');
const boardMenu = document.getElementById('board-menu');
const boardCheckboxes = document.querySelectorAll('.board-checkbox');
const boardAllBtn = document.getElementById('board-all-btn');
const boardNoneBtn = document.getElementById('board-none-btn');
const quickChips = document.querySelectorAll('.quick-chip[data-preset]');
const sortChips = document.querySelectorAll('.sort-chip');

let currentSortCol = 'distance';
let currentSortDir = 'asc';

// Board selection state
const allBoardValues = ['indeed', 'jobbank', 'linkedin', 'talent', 'eluta', 'gcjobs', 'techto', 'direct'];
let selectedBoards = new Set(allBoardValues);

const savedBoards = localStorage.getItem('dashboard_boards');
if (savedBoards) {
  try {
    const parsed = JSON.parse(savedBoards);
    if (Array.isArray(parsed) && parsed.length > 0) {
      selectedBoards = new Set(parsed);
      boardCheckboxes.forEach(cb => {
        cb.checked = selectedBoards.has(cb.value);
      });
    }
  } catch (e) {}
}

function updateBoardButtonText() {
  if (!boardBtnText) return;
  if (selectedBoards.size === allBoardValues.length || selectedBoards.size === 0) {
    boardBtnText.textContent = '🌐 Job Boards (All)';
  } else if (selectedBoards.size === 1) {
    const b = Array.from(selectedBoards)[0];
    const nameMap = { indeed: 'Indeed', jobbank: 'Jobs Canada', linkedin: 'LinkedIn', talent: 'Talent.com', eluta: 'Eluta', gcjobs: 'GC Jobs', direct: 'Direct' };
    boardBtnText.textContent = `🎯 Board: ${nameMap[b] || b}`;
  } else {
    boardBtnText.textContent = `🎯 Boards (${selectedBoards.size} selected)`;
  }
}

function updateQuickChipActive() {
  quickChips.forEach(chip => {
    const preset = chip.getAttribute('data-preset');
    let isActive = false;
    if (preset === 'all' && selectedBoards.size === allBoardValues.length) {
      isActive = true;
    } else if (preset === 'indeed' && selectedBoards.size === 1 && selectedBoards.has('indeed')) {
      isActive = true;
    } else if (preset === 'jobbank' && selectedBoards.size === 1 && selectedBoards.has('jobbank')) {
      isActive = true;
    } else if (preset === 'indeed-jobbank' && selectedBoards.size === 2 && selectedBoards.has('indeed') && selectedBoards.has('jobbank')) {
      isActive = true;
    } else if (preset === 'linkedin' && selectedBoards.size === 1 && selectedBoards.has('linkedin')) {
      isActive = true;
    } else if (preset === 'talent' && selectedBoards.size === 1 && selectedBoards.has('talent')) {
      isActive = true;
    } else if (preset === 'eluta' && selectedBoards.size === 1 && selectedBoards.has('eluta')) {
      isActive = true;
    }
    chip.classList.toggle('active', isActive);
  });
}

function updateSortChipActive() {
  const current = `${currentSortCol}-${currentSortDir}`;
  sortChips.forEach(chip => {
    chip.classList.toggle('active', chip.getAttribute('data-sort') === current);
  });
}

// Toggle board menu popup
if (boardSelectBtn && boardMenu) {
  boardSelectBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    boardMenu.classList.toggle('hidden');
    boardSelectBtn.classList.toggle('active', !boardMenu.classList.contains('hidden'));
  });

  document.addEventListener('click', (e) => {
    if (!document.getElementById('board-filter-wrapper')?.contains(e.target)) {
      boardMenu.classList.add('hidden');
      boardSelectBtn.classList.remove('active');
    }
  });
}

// Board Checkbox event handlers
boardCheckboxes.forEach(cb => {
  cb.addEventListener('change', () => {
    if (cb.checked) {
      selectedBoards.add(cb.value);
    } else {
      selectedBoards.delete(cb.value);
    }
    if (selectedBoards.size === 0) {
      // If user unchecks all, default to all to avoid empty confusion
      selectedBoards = new Set(allBoardValues);
      boardCheckboxes.forEach(c => c.checked = true);
    }
    saveAndApplyBoardFilter();
  });
});

boardAllBtn?.addEventListener('click', () => {
  selectedBoards = new Set(allBoardValues);
  boardCheckboxes.forEach(cb => cb.checked = true);
  saveAndApplyBoardFilter();
});

boardNoneBtn?.addEventListener('click', () => {
  // Clear to only indeed
  selectedBoards = new Set(['indeed']);
  boardCheckboxes.forEach(cb => cb.checked = cb.value === 'indeed');
  saveAndApplyBoardFilter();
});

boardOnlyBtns.forEach(btn => {
  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    const target = btn.getAttribute('data-board');
    selectedBoards = new Set([target]);
    boardCheckboxes.forEach(cb => cb.checked = cb.value === target);
    saveAndApplyBoardFilter();
  });
});

quickChips.forEach(chip => {
  chip.addEventListener('click', () => {
    const preset = chip.getAttribute('data-preset');
    if (preset === 'all') {
      selectedBoards = new Set(allBoardValues);
    } else if (preset === 'indeed') {
      selectedBoards = new Set(['indeed']);
    } else if (preset === 'jobbank') {
      selectedBoards = new Set(['jobbank']);
    } else if (preset === 'indeed-jobbank') {
      selectedBoards = new Set(['indeed', 'jobbank']);
    } else if (preset === 'linkedin') {
      selectedBoards = new Set(['linkedin']);
    } else if (preset === 'talent') {
      selectedBoards = new Set(['talent']);
    } else if (preset === 'eluta') {
      selectedBoards = new Set(['eluta']);
    }
    boardCheckboxes.forEach(cb => cb.checked = selectedBoards.has(cb.value));
    saveAndApplyBoardFilter();
  });
});

sortChips.forEach(chip => {
  chip.addEventListener('click', () => {
    const sortVal = chip.getAttribute('data-sort');
    if (!sortVal) return;
    const parts = sortVal.split('-');
    currentSortCol = parts[0] || 'distance';
    currentSortDir = parts[1] || 'asc';
    if (sortSelect && sortSelect.querySelector(`option[value="${sortVal}"]`)) {
      sortSelect.value = sortVal;
    }
    updateSortChipActive();
    filterAndSort();
  });
});

function saveAndApplyBoardFilter() {
  localStorage.setItem('dashboard_boards', JSON.stringify(Array.from(selectedBoards)));
  updateBoardButtonText();
  updateQuickChipActive();
  filterAndSort();
}

function getRows() {
  return Array.from(tbody.querySelectorAll('tr'));
}

function getRowBoard(row) {
  let b = row.getAttribute('data-board');
  if (b) return b;
  const href = (row.querySelector('a.posting')?.getAttribute('href') || '').toLowerCase();
  if (href.includes('indeed')) return 'indeed';
  if (href.includes('jobbank') || href.includes('guichet') || href.includes('jobs.gc.ca')) return 'jobbank';
  if (href.includes('linkedin')) return 'linkedin';
  if (href.includes('talent.com')) return 'talent';
  if (href.includes('eluta')) return 'eluta';
  if (href.includes('emploisfp') || href.includes('canada.ca') || href.includes('cfp-psc')) return 'gcjobs';
  if (href.includes('techto')) return 'techto';
  return 'direct';
}

function filterAndSort() {
  const query = searchBox.value.toLowerCase().trim();
  const status = statusFilter.value;
  const region = regionFilter.value.toLowerCase();
  
  localStorage.setItem('dashboard_search', searchBox.value);
  localStorage.setItem('dashboard_status', status);
  localStorage.setItem('dashboard_region', regionFilter.value);
  localStorage.setItem('dashboard_sort', `${currentSortCol}-${currentSortDir}`);

  const allRows = getRows();
  let visibleCount = 0;

  allRows.forEach(row => {
    const rowText = row.innerText.toLowerCase();
    const rowStatus = row.getAttribute('data-status');
    const rowRegion = (row.getAttribute('data-region') || '').toLowerCase();
    const rowBoard = getRowBoard(row);
    
    const matchesQuery = !query || rowText.includes(query);
    const matchesStatus = status === 'ALL' || 
      (rowStatus && rowStatus.toLowerCase() === status.toLowerCase()) || 
      (status === 'Rejected/Closed' && (rowStatus === 'Closed' || rowStatus === 'Rejected'));
    const matchesRegion = region === 'all' || rowRegion.includes(region);
    const matchesBoard = selectedBoards.has(rowBoard);

    if (matchesQuery && matchesStatus && matchesRegion && matchesBoard) {
      row.style.display = '';
      visibleCount++;
    } else {
      row.style.display = 'none';
    }
  });

  showingCount.textContent = `Showing ${visibleCount} of ${allRows.length} listings`;

  // Sort visible rows
  allRows.sort((a, b) => {
    let diff = 0;
    if (currentSortCol === 'distance') {
      const valA = parseFloat(a.getAttribute('data-distance') || 0);
      const valB = parseFloat(b.getAttribute('data-distance') || 0);
      diff = currentSortDir === 'asc' ? (valA - valB) : (valB - valA);
    } else if (currentSortCol === 'fit') {
      const valA = parseInt(a.getAttribute('data-fit') || 0);
      const valB = parseInt(b.getAttribute('data-fit') || 0);
      diff = currentSortDir === 'asc' ? (valA - valB) : (valB - valA);
    } else if (currentSortCol === 'overall') {
      const valA = parseInt(a.getAttribute('data-overall') || 0);
      const valB = parseInt(b.getAttribute('data-overall') || 0);
      diff = currentSortDir === 'asc' ? (valA - valB) : (valB - valA);
    } else if (currentSortCol === 'chance') {
      const valA = parseInt(a.getAttribute('data-chance') || 0);
      const valB = parseInt(b.getAttribute('data-chance') || 0);
      diff = currentSortDir === 'asc' ? (valA - valB) : (valB - valA);
    } else if (currentSortCol === 'prestige') {
      const valA = parseInt(a.getAttribute('data-prestige') || 0);
      const valB = parseInt(b.getAttribute('data-prestige') || 0);
      diff = currentSortDir === 'asc' ? (valA - valB) : (valB - valA);
    } else if (currentSortCol === 'pay') {
      const valA = parseFloat(a.getAttribute('data-pay') || 0);
      const valB = parseFloat(b.getAttribute('data-pay') || 0);
      diff = currentSortDir === 'asc' ? (valA - valB) : (valB - valA);
    } else if (currentSortCol === 'date') {
      const valA = a.getAttribute('data-date') || '';
      const valB = b.getAttribute('data-date') || '';
      diff = currentSortDir === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
    } else if (currentSortCol === 'company') {
      const valA = (a.getAttribute('data-company') || '').toLowerCase();
      const valB = (b.getAttribute('data-company') || '').toLowerCase();
      diff = currentSortDir === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
    } else if (currentSortCol === 'role') {
      const valA = (a.getAttribute('data-role') || '').toLowerCase();
      const valB = (b.getAttribute('data-role') || '').toLowerCase();
      diff = currentSortDir === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
    } else if (currentSortCol === 'location') {
      const valA = a.querySelector('.cell-location')?.innerText.trim().toLowerCase() || '';
      const valB = b.querySelector('.cell-location')?.innerText.trim().toLowerCase() || '';
      diff = currentSortDir === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
    } else if (currentSortCol === 'status') {
      const valA = (a.getAttribute('data-status') || '').toLowerCase();
      const valB = (b.getAttribute('data-status') || '').toLowerCase();
      diff = currentSortDir === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
    } else if (currentSortCol === 'deadline') {
      const valA = a.querySelector('.cell-deadline')?.innerText.trim().toLowerCase() || '';
      const valB = b.querySelector('.cell-deadline')?.innerText.trim().toLowerCase() || '';
      diff = currentSortDir === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
    } else {
      const valA = a.getAttribute(`data-${currentSortCol}`) || '';
      const valB = b.getAttribute(`data-${currentSortCol}`) || '';
      diff = currentSortDir === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
    }

    if (diff !== 0) return diff;

    // Robust tie-breakers when values match (e.g. same distance):
    // 1. Overall score descending
    const ovA = parseInt(a.getAttribute('data-overall') || 0);
    const ovB = parseInt(b.getAttribute('data-overall') || 0);
    if (ovA !== ovB) return ovB - ovA;

    // 2. Fit score descending
    const fitA = parseInt(a.getAttribute('data-fit') || 0);
    const fitB = parseInt(b.getAttribute('data-fit') || 0);
    if (fitA !== fitB) return fitB - fitA;

    // 3. Company name A-Z
    const compA = a.getAttribute('data-company') || '';
    const compB = b.getAttribute('data-company') || '';
    return compA.localeCompare(compB);
  });

  allRows.forEach(row => tbody.appendChild(row));

  // Update headers
  ths.forEach(th => {
    const col = th.getAttribute('data-col');
    const icon = th.querySelector('.sort-icon');
    if (col === currentSortCol) {
      th.classList.add('active-sort');
      if (icon) icon.textContent = currentSortDir === 'asc' ? '↑' : '↓';
    } else {
      th.classList.remove('active-sort');
      if (icon) icon.textContent = '↕';
    }
  });
}

// Event Listeners for Filters & Sorting Controls
if (sortSelect) {
  sortSelect.addEventListener('change', () => {
    const val = sortSelect.value;
    const parts = val.split('-');
    currentSortCol = parts[0] || 'distance';
    currentSortDir = parts[1] || 'asc';
    updateSortChipActive();
    filterAndSort();
  });
}

ths.forEach(th => {
  th.addEventListener('click', () => {
    const col = th.getAttribute('data-col');
    if (!col) return;
    if (currentSortCol === col) {
      currentSortDir = (currentSortDir === 'asc') ? 'desc' : 'asc';
    } else {
      currentSortCol = col;
      currentSortDir = ['overall', 'fit', 'chance', 'prestige', 'pay', 'date'].includes(col) ? 'desc' : 'asc';
    }
    const matchingOption = `${currentSortCol}-${currentSortDir}`;
    if (sortSelect && sortSelect.querySelector(`option[value="${matchingOption}"]`)) {
      sortSelect.value = matchingOption;
    }
    updateSortChipActive();
    filterAndSort();
  });
});

if (searchBox) {
  searchBox.addEventListener('input', () => {
    filterAndSort();
  });
}

if (statusFilter) {
  statusFilter.addEventListener('change', () => {
    filterAndSort();
  });
}

if (regionFilter) {
  regionFilter.addEventListener('change', () => {
    filterAndSort();
  });
}

// Restore saved settings
const savedSearch = localStorage.getItem('dashboard_search');
if (savedSearch && searchBox) searchBox.value = savedSearch;

const savedStatus = localStorage.getItem('dashboard_status');
if (savedStatus && statusFilter) statusFilter.value = savedStatus;

const savedRegion = localStorage.getItem('dashboard_region');
if (savedRegion && regionFilter) regionFilter.value = savedRegion;

const savedSort = localStorage.getItem('dashboard_sort');
if (savedSort) {
  const [sCol, sDir] = savedSort.split('-');
  if (sCol && sDir) {
    currentSortCol = sCol;
    currentSortDir = sDir;
    if (sortSelect && sortSelect.querySelector(`option[value="${savedSort}"]`)) {
      sortSelect.value = savedSort;
    }
  }
}
"""

    # Replace the existing JS block from // Table Filtering and Sorting down to // Update headers block
    old_js_start = "// Table Filtering and Sorting"
    old_js_end = "filterAndSort();\n\n// Silent Background Auto-Refresh"
    
    if old_js_start in html_str:
        idx_start = html_str.find(old_js_start)
        idx_end = html_str.find(old_js_end)
        if idx_start != -1 and idx_end != -1:
            html_str = html_str[:idx_start] + updated_js + "\n\nupdateBoardButtonText();\nupdateQuickChipActive();\nupdateSortChipActive();\nfilterAndSort();\n\n// Silent Background Auto-Refresh" + html_str[idx_end + len(old_js_end):]

    DASHBOARD_FILE.write_text(html_str, encoding="utf-8")
    print(f"Successfully updated {DASHBOARD_FILE}!")

    # Automatically deploy to GitHub Pages
    deploy_script = REPO_ROOT / "scripts" / "deploy_dashboard.sh"
    if deploy_script.exists():
        try:
            subprocess.run([str(deploy_script)], check=True)
        except Exception as e:
            print(f"Warning: Failed to auto-deploy dashboard: {e}")

if __name__ == "__main__":
    update_tracker()
    update_dashboard()
