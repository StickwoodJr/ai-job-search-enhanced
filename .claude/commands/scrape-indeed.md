# /scrape-indeed - Dedicated Indeed Job Scraper

You are executing a focused, dedicated job scrape pass exclusively on **Indeed Canada** (`ca.indeed.com`) for the candidate.

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
- A search term or role focus (e.g. `/scrape-indeed "Software Engineer"`, `/scrape-indeed "Systems Administrator"`, `/scrape-indeed co-op`)
- `--broad` to run all configured query categories from `config/swarm_sectors.json`
- `--jobage <days>` to filter by posting recency (1, 3, 7, 14 days; default: 14)
- `--limit <n>` max results per query category (default: 10, max: 30)

Follow these steps **in order**.

---

## Step 0: Load State

1. Read `job_scraper/seen_jobs.json` (create with `{"seen": {}}` if missing).
2. Read `job_search_tracker.csv` to extract already-applied companies and roles into an exclusion set.
3. Read candidate profile basics from `CLAUDE.md` and `01-candidate-profile.md`:
   - Name & Location
   - Target Roles & Primary Skills
   - Target Employment Status & Commute Constraints

---

## Step 1: Search Indeed

Identify the queries to run:
- **If user specified a focus keyword** (e.g. "Software Engineer"):
  Run that targeted query with candidate's location.
- **If `--broad` is specified or by default**:
  Run the prioritized query set loaded from `config/swarm_sectors.json` or candidate profile targets.

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

Evaluate each new posting against candidate profile qualifications:
- **High match**:
  - Aligns closely with candidate's target roles and core skills.
  - Aligns with target experience level (co-op, entry-level, or professional).
  - Located within candidate's commute boundaries or remote.
- **Medium match**:
  - Adjacent roles or technical domains where candidate has strong transferable competencies.
- **Low match**:
  - Seniority mismatch (e.g. senior/director roles requiring 7+ years when candidate seeks entry/co-op).
  - Requires completely different technical domains outside candidate profile.
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
