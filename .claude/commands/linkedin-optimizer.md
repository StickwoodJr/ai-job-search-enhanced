# /linkedin-optimizer — Recruiter-Optimized LinkedIn Workflow

You are orchestrating a dual-agent (drafter-reviewer) workflow augmented with live retrieval from Google NotebookLM via ExtendLM MCP (with source-aware domain caching and primary evidence grounding).

The workflow **assumes Review Mode by default**, actively discovers the user's LinkedIn profile link from existing profile/resume files, and features an adaptive RAG pipeline that adjusts to whatever knowledge domains exist in the candidate's notebook (educational, corporate, open-source projects, or hybrid).

Follow these steps **exactly in order**. Do not skip steps.

---

## Standing Rules

1. **Write New Facts Back to Profile:** If the user confirms, corrects, or supplies a fact that is not already in `01-candidate-profile.md` — or if RAG extracts verified achievements from primary source materials — update `01-candidate-profile.md` in the same turn.
2. **Default to Review Mode:** Unless the user explicitly uses keywords like `generate`, `create new`, or `from scratch`, always execute **Review & Enhancement Mode**.
3. **Adaptive RAG Grounding:** Execute `RAG Experiment/linkedin_rag_hook.py`. Domain introspection is automatically cached based on source fingerprints. If the user adds new sources to NotebookLM, the cache automatically invalidates to capture new materials without blind spots. Substantive evidence queries execute live with zero caching.
4. **Token-Efficiency:** Pass draft and review content inline in prompts. Do not re-read files already present in working memory.

---

## Step 0: Profile Link Discovery & Mode Selection

### 0a. Mode Detection
Check the command arguments `$ARGUMENTS`:
- If arguments contain `generate`, `new`, `build`, or `from scratch` → Set `MODE = GENERATE`.
- Otherwise → Set `MODE = REVIEW` (Default).

### 0b. Profile Link Discovery (Review Mode)
In Review Mode:
1. Scan for an existing LinkedIn URL in:
   - `.claude/skills/job-application-assistant/01-candidate-profile.md`
   - `CLAUDE.md`
   - `resume_master.md`
2. **If found:**
   - Note the discovered URL (e.g., `https://www.linkedin.com/in/...`).
   - If the user provided pasted text in `$ARGUMENTS` or if a local file exists (e.g. `linkedin/existing_profile.md`), use it directly.
   - If no text was provided, inform the user:
     > "Found your profile link: `<URL>`. Proceeding with an algorithmic optimization review based on your candidate profile records. If you would like me to review specific updated text, please paste your current sections."
3. **If NOT found:**
   - Prompt the user directly:
     > "I could not find an existing LinkedIn profile link in your candidate profile or master resume. Would you like to review and optimize an existing profile (please share your LinkedIn URL or paste your profile text), or generate a complete turnkey profile from scratch?"
   - Await the user's direction before proceeding.

---

## Step 1: DRAFTER — Adaptive RAG Retrieval & Knowledge Introspection

Execute the adaptive LinkedIn RAG hook:

```bash
python3 "RAG Experiment/linkedin_rag_hook.py" --role "<TARGET_ROLE>" --output "linkedin_evidence_pack.md"
```

The hook:
1. Calls `bridge.list_sources()` via ExtendLM MCP to compute a source fingerprint.
2. Checks `RAG Experiment/cache/notebook_domain_cache.json`. If fingerprint matches, domain introspection loads in sub-seconds. If new sources were added to NotebookLM, the cache is automatically invalidated and refreshed.
3. Introspects knowledge domains: Academic (courses/labs), Corporate (metrics/systems), Technical Projects (homelabs/ADRs), Certifications.
4. Generates `linkedin_evidence_pack.md`.

> [!CAUTION]
> **MANDATORY — ExtendLM Failure Protocol (Never Proceed Silently):**
> If `linkedin_rag_hook.py` fails with an ExtendLM connection error (exit code 1), **DO NOT SILENTLY PROCEED OR DRAFT IN DEGRADED MODE.**
> 1. Immediately halt the workflow and alert the user:
>    *"ExtendLM live retrieval failed: No active ExtendLM Chrome extension connection found. The agent cannot query NotebookLM live."*
> 2. Present diagnostic instructions:
>    - Ensure Google Chrome is running with the ExtendLM extension enabled and logged into NotebookLM.
> 3. Ask the user whether they want to activate the Chrome extension and retry live retrieval, or explicitly authorize offline fallback mode (`--allow-fallback`) using local evidence files (`academic_evidence_pack.md`, `career_evidence_pack.md`).
> 4. Never proceed without user authorization.


---

## Step 2: DRAFTER — Generate Audit & Enhancement Draft (or Turnkey Profile)

Read methodology reference:
- `.claude/skills/job-application-assistant/11-linkedin-optimization.md`
- `.claude/skills/job-application-assistant/01-candidate-profile.md`
- `linkedin_evidence_pack.md`

### In Review Mode:
1. Audit the existing profile against the **0–100 Rubric** in `11-linkedin-optimization.md`:
   - **Headline SEO (20 pts):** Front-loading target role (first 70 chars), hard skills, separator.
   - **About Hook & Structure (20 pts):** First 300 chars hook, 5-block structure, contact CTA, character limit (<= 2600).
   - **Experience CAR Density (20 pts):** Action verbs, technical tool citations, quantified metrics, 5 tagged skills.
   - **Projects & Proof (15 pts):** Enterprise framing of homelab/engineering labs, Git repos, ADRs.
   - **Skills & Acronym Pairing (15 pts):** Dual acronym/full-form pairing (`AD DS`, `GPO`, `DHCP`, `VLAN`), 50 skill slots.
   - **Recruiter Spotlights (10 pts):** Open to Work, regional GTA location anchor, alumni connections.
2. Draft targeted **Before/After Upgrades** for each section with explicit rationale.

### In Generation Mode:
Draft the complete turnkey profile specification:
- Banner / Visual setup instructions
- 3–4 Headline variants tailored for recruiter SEO
- 5-block About section with immediate 300-character hook
- 3 Featured section media cards
- Experience entries with CAR bullets and 5 tagged skills each
- Projects section with enterprise framing (ADRs, post-mortems)
- Education & dedicated Courses accomplishment section
- Certifications & Honors
- Complete 50-Skill taxonomy matrix (Top 3 pinned)
- Outreach connection notes (< 300 chars) & recommendation scripts

---

## Step 3: REVIEWER — Recruiter & Algorithmic Proxy Review

Spawn a reviewer agent using the `Agent` tool (`invoke_subagent` in Antigravity). Pass the draft content inline:

```
You are a Senior Technical Talent Acquisition Partner and Enterprise IT Hiring Manager reviewing a LinkedIn profile optimization draft.

## Your Tasks
1. Audit Against Recruiter Boolean Search Filters:
   - Does the profile hit high-frequency recruiter search terms (Systems Administrator, Active Directory, AD DS, Group Policy, GPO, DHCP, DNS, Linux, Cisco, Co-op, Internship)?
   - Are full terms and acronyms paired together?
2. Audit Visible Folds:
   - Headline: Does the primary target title fit in the first 65–70 characters?
   - About: Does the first 280–300 characters provide an irresistible hook before truncation?
3. Factual Grounding Audit:
   - Verify that every metric, company name, date, course code, and technology is strictly backed by 01-candidate-profile.md, CLAUDE.md, and linkedin_evidence_pack.md.
   - Flag any unsubstantiated claims or buzzwords.
4. Produce Feedback:
   - Part A: Structured JSON edits {"section", "target_text", "replacement_text", "reason"}
   - Part B: Recruiter insights (missing skills, tone refinement, spotlight recommendations)
```

---

## Step 4: DRAFTER — Apply Revisions & Refine

Once the reviewer agent returns:
1. Apply structured JSON edits directly.
2. Incorporate narrative suggestions to strengthen recruiter search rank.
3. Ensure 100% compliance with candidate profile and verified evidence.

---

## Step 5: DRAFTER — Automated Algorithmic Linter

Run the automated verification script:

```bash
python3 tools/verify_linkedin.py "LINKEDIN_PROFILE_MASTER.md"
```
*(Or against `linkedin/profile_review_report.md`)*

Verify:
- [ ] Headline <= 220 chars (target role in first 70 chars)
- [ ] About <= 2,600 chars (hook <= 300 chars)
- [ ] Acronym/full-term pairs verified
- [ ] 50-skill taxonomy populated with top 3 pinned
- [ ] Recruiter Spotlight Score >= 85 / 100

---

## Step 6: Present Output, Stage Facts & Export

1. **Stage New Facts:** Write any newly discovered verified achievements or coursework details back into `01-candidate-profile.md`.
2. **Export Files:**
   - Review Mode: Save to `linkedin/profile_review_report.md`.
   - Generation Mode: Save to `linkedin/linkedin_profile_master.md` and copy to workspace root `LINKEDIN_PROFILE_MASTER.md`.
3. **Present Summary to User:**
   - Display the 0–100 Algorithmic Audit Scorecard.
   - Highlight key before/after upgrades.
   - Provide copy-paste ready blocks for immediate profile deployment.
