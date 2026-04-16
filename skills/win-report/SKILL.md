---
name: win-report
description: Discover and synthesize engineering wins from GitHub PRs/issues, Confluence, Jira, and Slack over a configurable time range. Produces a structured markdown report of top wins with evidence, impact, and ownership. Use when the user says "/win-report", "summarize my wins", "what did I ship last month", "monthly wins report", "generate wins for performance review", or asks for a summary of their recent engineering contributions.
---

# Win Report

Discover and synthesize engineering wins into a structured report.

## Invocation

- `/win-report` - last 30 days, prompts for sources
- `/win-report 2026-03-01 2026-04-01` - custom date range

## Setup

### 1. Parse date range

Extract start/end dates from args (YYYY-MM-DD format). If none provided, default to last 30 days from today.

### 2. Detect available artifact sources

Probe the environment for each source type:

| Source | Detection method |
|--------|-----------------|
| GitHub | Run `gh api /user --jq '.login'`. If succeeds, GitHub is available and username is captured. If fails, note unavailable - suggest `gh auth login`. |
| Confluence | Check if `mcp__atlassian__search` tool exists. |
| Jira | Check if `mcp__atlassian__searchJiraIssuesUsingJql` tool exists. |
| Slack | Check if any `mcp__slack__*` tools exist. |

### 3. Present sources and confirm with user

Display all detected sources with status (available / unavailable). Then ask in a **single consolidated prompt**:

- Which sources to use (default: all available)
- **GitHub:** repos to search (`owner/repo` or full URLs - parse URLs to `owner/repo`)
- **Confluence:** spaces or search terms to scope (optional)
- **Jira:** projects or JQL filters (optional)
- **Slack:** channels or search terms (optional)
- Any additional sources to paste (design docs, incident reports, dashboards, runbooks, postmortems)
- Optional hints: remembered wins, projects, launches, incidents, team/system names

Treat user hints as guidance, not the full answer set.

---

## Phase 0 - Artifact Discovery

Search all confirmed sources in parallel.

**GitHub** (if enabled):
```
gh pr list --repo {repo} --author {username} --state merged \
  --search "merged:>{start_date}" --limit 100 \
  --json number,title,body,mergedAt,additions,deletions,labels,url

gh issue list --repo {repo} --assignee {username} --state all \
  --search "created:>{start_date}" --limit 50 \
  --json number,title,body,state,createdAt,url
```
Run across all repos in parallel.

**Confluence** (if enabled):
- Use `mcp__atlassian__search` or `mcp__atlassian__searchConfluenceUsingCql` to find pages authored/edited by the user in the date range, scoped to specified spaces.

**Jira** (if enabled):
- Use `mcp__atlassian__searchJiraIssuesUsingJql` with JQL like `assignee = currentUser() AND updated >= "{start_date}"` scoped to specified projects.

**Slack** (if enabled):
- Search for messages from the user in specified channels within the date range.

**User-pasted content:**
- Incorporate any design docs, incident reports, dashboards provided during setup.

### Signal extraction

Scan all artifacts for candidate signals:
- Merged PRs with large/complex diffs
- Architectural changes, security fixes, performance improvements
- Infra changes, incident resolution, migrations
- Reliability improvements, tooling/framework work
- Test harness additions, automation that reduced manual work
- Changes that enabled other engineers
- Decisions that reduced operational or technical risk
- Cross-team or cross-repo coordination
- Debugging of ambiguous or high-stakes failures

For each signal, extract:
```
### Candidate signal
- **Artifact:** [PR / issue / doc / incident / ticket]
- **Source:** [GitHub / Confluence / Jira / Slack]
- **What changed:** ...
- **Why it likely mattered:** ...
- **Possible win category:** [complexity / ambiguity / risk reduction / enablement / impact]
```

Then cluster related artifacts into win threads:
```
### Win thread
- **Thread name:** ...
- **Artifacts:** [list across all sources]
- **Core change:** ...
- **Possible impact:** ...
```

Do not ask questions yet.

---

## Phase 1 - Triage

Convert discovered signals into **5-8 candidate win threads**.

For each, write a one-line hypothesis: `What I did -> why it mattered`

Example: `Refactored Helm deployment templates across 7 services -> reduced config drift and lowered deployment failure risk.`

### Select top 3

Score each candidate:
- **+2** architectural impact
- **+2** cross-team leverage
- **+2** risk reduction
- **+1** technical complexity
- **+1** artifact richness
- **+1** durable enablement for others

Override score if a lower-scoring item is clearly more promotion-relevant.

Selection preferences:
- Concrete shipments > maintenance activity
- Decisions > participation
- Outcomes > effort
- Durable leverage > one-off busywork

Keep an artifact-poor candidate only if clearly stronger than better-evidenced alternatives.

---

## Phase 2 - Gap-filling questions

Single round, **8-15 questions max**. Rules:

- One question may cover multiple wins
- Prefer extracting info from artifacts over asking
- Do not ask for context the artifacts already show
- If metrics are missing, ask for proxies:
  - Before vs after time, incident count, failure rate
  - Adoption count, latency, dollars saved
  - Toil reduced, review load reduced
  - Number of teams or services affected
- If a key decision mattered, ask what alternatives were considered and what risk was avoided
- If ownership is blurred, ask for exact scope boundaries

Do not ask low-leverage biography questions.

---

## Phase 3 - Produce the win list

Output the **top 3 wins**. Each win must use this exact template:

```markdown
## TITLE
Short and outsider-readable.

**What I shipped/solved:**
1-2 punchy sentences.

**Why it mattered:**
State the stakes and who benefited.

**Why it was difficult:**
Optional. Include only if it clarifies technical difficulty, ambiguity, or non-obvious judgment.

**Impact (current):**
Metrics or strong proxies. Include baseline where possible.

**My ownership:**
Use explicit "I" language. Clarify collaborator boundaries where relevant.

**Evidence / artifacts:**
- PRs, docs, dashboards, incidents, demos, tickets
- Links or [LINK] placeholders

**Missing evidence:**
Optional. Call out screenshots, adoption numbers, before-state, or metrics still needed.

**Notes to self (confirm later):**
Short bullets only.
```

After the wins, include a summary table:

```markdown
## Summary

| Win | Core Signal | Impact Proxy |
| --- | --- | --- |
| {Win 1 short name} | {e.g. Pioneer, risk reduction, architectural judgment} | {e.g. 4h -> 10min x 20 squads} |
| ... | ... | ... |
```

---

## Bonus Phase - Public artifact idea

If any win contains a rare or subtle technical lesson, propose **one** public artifact idea:
- X thread outline, short post idea, engineering note, or talk outline

Use an even stricter, more compressed style than the win entries.

---

## Output

Write the full report to `wins-YYYY-MM.md` in the current working directory.

The report contains only the final polished wins - no intermediate work (candidate threads, scoring, selection rationale). Those are working artifacts used during discovery and triage but excluded from the output file.

Include in this order:
1. Title header: `# Win List - {Month} {Year}`
2. Final win list (full template for each, numbered as "Win 1", "Win 2", etc.)
3. Summary table mapping each win to its core signal and impact proxy
4. Optional public artifact idea

---

## Writing rules

Target reader: skeptical, time-poor outsider with no context on the engineering team.

- Every sentence must earn its place; each introduces a new concept
- Cut fluff aggressively
- No team-internal jargon unless briefly explained
- No inflated claims
- No passive voice where ownership matters
- Do not accept "we" as contribution - force explicit "I did X" ownership boundaries
- Prefer "I designed", "I implemented", "I debugged", "I decided", "I automated", "I de-risked"
- Never use "supported", "helped with", "involved in" unless truly the best description
- Each win should stand on its own without external context

## Constraints

- **Question budget:** 8-15 total questions across all phases
- **Discovery bias:** Prefer extracting info from artifacts before asking
- **Evidence requirement:** Prefer wins with artifacts. Flag weak/missing evidence clearly.
- **Progress over perfection:** Use placeholders and "Notes to self" rather than blocking on missing details
- **Tone:** Direct but supportive. No harsh scoring. No gotchas.
