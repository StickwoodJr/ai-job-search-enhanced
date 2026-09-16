# /scrape-indeed - Dedicated Indeed Job Scraper

You are executing a focused, dedicated job scrape pass exclusively on **Indeed Canada** (`ca.indeed.com`) for Golden Stickwood.

Unlike the multi-portal `/scrape` command, `/scrape-indeed` targets Indeed's live listings directly via the local `indeed-search` skill / MCP backend. It discovers newly posted positions, checks them against `job_scraper/seen_jobs.json` and `job_search_tracker.csv`, fetches complete posting details, evaluates candidate fit (High / Medium / Low), persists new matches, and generates referral outreach links.

---

## Invocation & Arguments

The user triggers this command by saying:
- `/scrape-indeed`
- `scrape indeed`
- `indeed scrape`
- `search indeed for postings`
- `find indeed jobs`

`$ARGUMENTS` may contain:
- A search term or role focus (e.g. `/scrape-indeed "Linux"`, `/scrape-indeed "Help Desk"`, `/scrape-indeed co-op`)
- `--broad` to run all priority query categories across systems, cloud, and network engineering
- `--jobage <days>` to filter by posting recency (1, 3, 7, 14 days; default: 14)
- `--limit <n>` max results per query category (default: 10, max: 30)

Follow these steps **in order**.

---

## Step 0: Load State

1. Read `job_scraper/seen_jobs.json` (create with `{"seen": {}}` if missing).
2. Read `job_search_tracker.csv` to extract already-applied companies and roles into an exclusion set.
3. Read candidate profile basics from `CLAUDE.md`:
   - Name: Golden Stickwood
   - Location: Newmarket/Toronto, ON (Commute: GTA & York Region; Open to On-site, Hybrid, Remote)
   - Focus: Winter 2027 Co-op (Systems Administration, Linux, Active Directory, Cisco Networking, Zero-Trust Homelab)

---

## Step 1: Search Indeed

Identify the queries to run:
- **If user specified a focus keyword** (e.g. "Linux"):
  Run that targeted query with location `"Toronto, ON"`.
- **If `--broad` is specified or by default**:
  Run the prioritized query set tailored for Golden Stickwood:
  1. `"IT Co-op"` (Location: `"Toronto, ON"`)
  2. `"Junior System Administrator"` (Location: `"Toronto, ON"`)
  3. `"Linux Co-op"` (Location: `"Toronto, ON"`)
  4. `"Network Administrator Co-op"` (Location: `"Toronto, ON"`)
  5. `"IT Support Technician"` (Location: `"York Region, ON"`)

Execute each search using the `indeed-search` CLI:
```bash
bun run .agents/skills/indeed-search/cli/src/cli.ts search -q "<query>" -l "<location>" --jobage <days> --limit <n> --format json
```

Collect all returned job items into a candidate pool.

---

## Step 2: Deduplicate & Fetch Detail

For each discovered posting:
1. **Deduplication Check**:
   - Check if the job URL, ID (`in-<jk>`), or `company` + `title` combination exists in `job_scraper/seen_jobs.json`.
   - Check if `company` and `role` are already present in `job_search_tracker.csv`.
   - If already present, skip to avoid duplicate processing.

2. **Fetch Detail**:
   For each new candidate, fetch full requirements and description using the CLI `detail` command:
   ```bash
   bun run .agents/skills/indeed-search/cli/src/cli.ts detail "<id_or_url>" --format json
   ```
   Extract:
   - Full job description & minimum qualifications
   - Application deadline (if specified)
   - Direct employer application link (`direct_url` or `apply_url`)
   - Salary range (if provided)

---

## Step 3: Quick Fit Assessment

Evaluate each new posting against Golden Stickwood's qualifications:
- **High match**:
  - Requires Linux system administration (RHEL/CentOS/Ubuntu), Windows Server / Active Directory, Cisco IOS networking, or IT Infrastructure Support.
  - Aligns with student/co-op or junior level (0-2 years experience).
  - Located within the GTA / York Region or Remote.
- **Medium match**:
  - General IT helpdesk, technical support, hardware rollout, or software QA with relevant system exposure.
  - Requires slightly adjacent skills (e.g. Azure, AWS, PowerShell) where candidate has fundamental transferability.
- **Low match**:
  - Senior roles requiring 5+ years of full-time experience.
  - Requires skills not in candidate profile (e.g. senior software engineering, C++, SAP, proprietary mainframe).
  - Out of geographic scope without remote option.

---

## Step 4: Persist to Seen Jobs

Add all newly evaluated postings to `job_scraper/seen_jobs.json` under `"seen"`:

```json
{
  "seen": {
    "https://ca.indeed.com/viewjob?jk=<jk>": {
      "title": "<Job Title>",
      "company": "<Company Name>",
      "url": "https://ca.indeed.com/viewjob?jk=<jk>",
      "first_seen": "YYYY-MM-DD",
      "deadline": "YYYY-MM-DD" or null,
      "fit": "high" | "medium" | "low",
      "status": "new",
      "portal": "indeed-search",
      "source": "cli"
    }
  }
}
```

Save the file cleanly formatted with 2-space indentation.

---

## Step 5: Present Results & Referral Links

Present a structured summary table to the user:

### New Indeed Postings

| Fit | Role | Company | Location | Date Posted | Direct Apply / Link |
|-----|------|---------|----------|-------------|---------------------|
| **High** | Junior System Administrator | Example Corp | Toronto, ON | 2026-09-10 | [Indeed Link](https://ca.indeed.com/viewjob?jk=...) |

For every **High** and **Medium** fit job, provide two pre-built LinkedIn referral links:
1. **Recruiter Search**: `https://www.linkedin.com/search/results/people/?keywords=<Company>+recruiter`
2. **Team / Peer Search**: `https://www.linkedin.com/search/results/people/?keywords=<Company>+<Role Keyword>`

Highlight key takeaways:
- Number of new postings discovered vs. skipped duplicates.
- Recommended next steps (e.g. *"Run `/apply <url>` to draft tailored LaTeX CV and cover letter"* or *"Run `/rank` to batch-score across the entire pipeline"*).
