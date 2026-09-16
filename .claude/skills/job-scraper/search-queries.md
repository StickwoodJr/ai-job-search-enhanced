# Search Queries for Job Scraper

## Installed portal CLIs (primary for `/scrape`)

`/scrape` discovers every portal skill under `.agents/skills/*/SKILL.md` and runs its CLI first. Active Canadian and global CLIs configured in this repository include:
- **`linkedin-search`**: LinkedIn job listings (targeting Greater Toronto Area / Canada)
- **`indeed-search`**: Indeed Canada (`indeed.ca`) live job listings via safe local MCP/GraphQL backend
- **`eluta-search`**: Eluta.ca (crawls Canadian employer career pages directly)
- **`jobbank-ca-search`**: Job Bank Canada (Government of Canada National Job Bank)
- **`gcjobs-search`**: GC Jobs (Federal Public Service student / co-op postings)
- **`talent-com-search`**: Talent.com Canada
- **`freehire-search`**: Direct hire / remote opportunities

The `site:` query templates in this file are the **WebSearch fallback** — for portals without a CLI, company career pages, or when a CLI fails.

## Search Sites & Job Boards

Primary Canadian job boards:
- **linkedin.com/jobs** - Filter: Canada, Greater Toronto Area, Ontario
- **eluta.ca** - Employer direct postings across Canada
- **jobbank.gc.ca** - Job Bank Canada (student/youth and general IT)
- **emploisfp-psjobs.cfp-psc.gc.ca** - GC Jobs (FSWEP / Federal Co-op)
- **indeed.ca** - Indeed Canada
- **senecaworks.senecapolytechnic.ca** - Seneca Works Co-op Portal (manual paste supported in `/apply`)

## Query Categories

### Priority 1: IT Co-op & Junior Systems Administration

Matching your primary career direction for the 4-month Winter 2027 co-op term:

```
site:linkedin.com/jobs "IT Co-op" Toronto OR "York Region"
site:linkedin.com/jobs "Systems Administrator Intern" OR "Systems Administrator Co-op" Toronto
site:eluta.ca "IT Co-op" "Toronto" OR "Markham" OR "Newmarket"
site:jobbank.gc.ca "Systems Administrator" student "Ontario"
site:indeed.ca "Junior System Administrator" "Co-op" "Toronto"
```

### Priority 2: Network Operations & Cloud Infrastructure

Roles leveraging Cisco routing, Linux servers, virtualization, and zero-trust networking:

```
site:linkedin.com/jobs "Network Administrator Co-op" OR "Network Operations Intern" Toronto
site:linkedin.com/jobs "Junior Linux Administrator" OR "Linux Co-op" Toronto
site:eluta.ca "Network Technician" "Toronto" OR "Vaughan" OR "Richmond Hill"
site:indeed.ca "Cloud Infrastructure Intern" "Linux" "Toronto"
```

### Priority 3: Technical Support & Help Desk Specialist

Roles providing Tier 1/2 technical support, Active Directory, hardware/software deployment, and customer service:

```
site:linkedin.com/jobs "Help Desk Co-op" OR "IT Support Intern" "Toronto" OR "Markham"
site:eluta.ca "Technical Support Specialist" "Newmarket" OR "Aurora" OR "Markham"
site:indeed.ca "IT Support Technician" "Active Directory" "York Region"
```

### Priority 4: Government & Public Sector Student IT Roles

Federal and provincial public service student/internship streams:

```
site:jobbank.gc.ca "computer systems" student "Ontario"
site:emploisfp-psjobs.cfp-psc.gc.ca "IT" OR "systems" "student"
site:gojobs.gov.on.ca "student" "information technology"
```

## Location Filter

Commute and location boundaries:
- **Ideal (< 30 min):** Newmarket, Aurora, Richmond Hill, Markham, Vaughan, King City
- **Acceptable (30–60 min / Transit / GO):** North York, Downtown Toronto, Scarborough, Mississauga (Hybrid), Remote (Anywhere in Canada)
- **Borderline (60–90 min):** West GTA (Oakville, Burlington), East GTA (Oshawa, Whitby)
- **Too Far:** In-person roles outside Ontario / GTA requiring relocation without compensation

## Work Term Constraints

- **Work Term:** 4-month Co-op starting January 2027 (Winter 2027)
- **Availability:** Full-time (37.5–40 hours/week)
- **Work Authorization:** Canadian Citizen (No visa sponsorship needed)

## Date Filter

Only include jobs posted within the last 14 days, or with an application deadline that has not yet passed.

