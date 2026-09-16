# Search Queries for Job Scraper

## Installed portal CLIs (primary for `/scrape`)

`/scrape` discovers every portal skill under `.agents/skills/*/SKILL.md` and runs its CLI first. Active Canadian and global CLIs configured in this repository include:
- **`linkedin-search`**: LinkedIn job listings (targeting your configured location / remote)
- **`indeed-search`**: Indeed Canada (`indeed.ca`) live job listings via safe local MCP/GraphQL backend
- **`eluta-search`**: Eluta.ca (crawls employer career pages directly)
- **`jobbank-ca-search`**: Job Bank Canada (Government of Canada National Job Bank)
- **`gcjobs-search`**: GC Jobs (Federal Public Service student / entry-level postings)
- **`talent-com-search`**: Talent.com Canada
- **`freehire-search`**: Direct hire / remote tech opportunities

The `site:` query templates in this file are the **WebSearch fallback** — for portals without a CLI, company career pages, or when a CLI fails.

## Search Sites & Job Boards

Primary job boards:
- **linkedin.com/jobs** - Filter: Canada, Greater Toronto Area, Ontario, or your region
- **eluta.ca** - Employer direct postings across Canada
- **jobbank.gc.ca** - Job Bank Canada
- **emploisfp-psjobs.cfp-psc.gc.ca** - GC Jobs (FSWEP / Federal Co-op / Public Service)
- **indeed.ca** - Indeed Canada
- **Company / Institutional career portals** (e.g. Workday, Greenhouse, Lever, Taleo)

## Query Categories

Queries are tailored to the candidate's target roles and sectors configured in `CLAUDE.md`, `01-candidate-profile.md`, and `config/swarm_sectors.json`.

### Priority 1: Primary Target Roles

Matching your primary career direction and target roles:

```
site:linkedin.com/jobs "[YOUR_TARGET_ROLE_1]" "[YOUR_CITY]"
site:linkedin.com/jobs "[YOUR_TARGET_ROLE_2]" "[YOUR_CITY]"
site:eluta.ca "[YOUR_TARGET_ROLE_1]" "[YOUR_CITY]"
site:jobbank.gc.ca "[YOUR_TARGET_ROLE_1]" "[YOUR_PROVINCE]"
site:indeed.ca "[YOUR_TARGET_ROLE_1]" "[YOUR_CITY]"
```

### Priority 2: Adjacent & Emerging Competencies

Roles leveraging your adjacent technical skills and toolchain competencies:

```
site:linkedin.com/jobs "[ADJACENT_ROLE_1]" "[YOUR_CITY]"
site:linkedin.com/jobs "[ADJACENT_ROLE_2]" "[YOUR_CITY]"
site:eluta.ca "[ADJACENT_ROLE_1]" "[YOUR_REGION]"
site:indeed.ca "[ADJACENT_ROLE_1]" "[YOUR_CITY]"
```

### Priority 3: Technical Support & Entry / Junior Opportunities

Foundational and operational roles matching your core hands-on technical skills:

```
site:linkedin.com/jobs "[ENTRY_OR_SUPPORT_ROLE]" "[YOUR_CITY]"
site:eluta.ca "[ENTRY_OR_SUPPORT_ROLE]" "[YOUR_REGION]"
site:indeed.ca "[ENTRY_OR_SUPPORT_ROLE]" "[YOUR_CITY]"
```

### Priority 4: Government & Public Sector Programs

Federal, provincial, and municipal public service student/entry streams:

```
site:jobbank.gc.ca "[PRIMARY_KEYWORD]" student "[YOUR_PROVINCE]"
site:emploisfp-psjobs.cfp-psc.gc.ca "[PRIMARY_KEYWORD]" "student"
site:gojobs.gov.on.ca "student" "[PRIMARY_KEYWORD]"
```

## Location Filter

Commute and location boundaries configured in your profile:
- **Ideal (< 30 min):** [YOUR_PRIMARY_MUNICIPALITY_OR_NEIGHBORHOODS]
- **Acceptable (30–60 min / Transit):** [YOUR_METROPOLITAN_AREA], Remote (Anywhere in Canada / Domestic)
- **Borderline (60–90 min):** [EXTENDED_COMMUTE_ZONE]
- **Out of Range:** Roles requiring unassisted relocation outside target region

## Work Term Constraints

- **Target Term:** [YOUR_TARGET_TERM] (e.g. Co-op / Internship / Full-time / Part-time)
- **Availability:** [YOUR_AVAILABILITY] (e.g. Full-time 37.5–40 hrs/week)
- **Work Authorization:** [YOUR_WORK_AUTHORIZATION] (e.g. Citizen / Permanent Resident / Work Permit)

## Date Filter

Only include jobs posted within the last 14 days, or with an application deadline that has not yet passed.

