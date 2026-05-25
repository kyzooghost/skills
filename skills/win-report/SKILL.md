---
name: win-report
description: Discover and synthesize engineering wins from GitHub PRs/issues, Confluence, Jira, Notion, and Slack over a configurable time range. Uses exhaustive two-phase subagent architecture to paginate all sources and read all artifacts in full before synthesizing. Produces a structured markdown report of top wins with evidence, impact, and ownership. Use when the user says "/win-report", "summarize my wins", "what did I ship last month", "monthly wins report", "generate wins for performance review", or asks for a summary of their recent engineering contributions.
---

# Win Report

Discover and synthesize engineering wins into a structured report using exhaustive multi-source research.

## Invocation

- `/win-report` - last 30 days, prompts for all params
- `/win-report 2026-03-01 2026-04-01` - custom date range, prompts for rest

## Setup

### 1. Parse date range

Extract start/end dates from args (YYYY-MM-DD format). If none provided, default to last 30 days from today.

### 2. Detect available sources

Probe the environment for each source type:

| Source | Detection method |
|--------|-----------------|
| GitHub | Run `gh api /user --jq '.login'`. If succeeds, GitHub is available and username is captured. |
| Confluence | Check if `mcp__atlassian__search` tool exists. |
| Jira | Check if `mcp__atlassian__searchJiraIssuesUsingJql` tool exists. |
| Notion | Check if any `mcp__notion__*` tools exist. |
| Slack | Check if any `mcp__slack__*` tools exist. |

### 3. Collect inputs (single consolidated prompt)

Ask in one prompt:

- **GitHub org(s):** comma-separated org names to search (e.g. `CBA-General, CBA-QTN-Global-Cloud-Transformation`)
- **MCPs to use:** which detected non-GitHub sources to include (default: all available)
- **Hints (optional):** projects, launches, incidents, team/system names to weight during triage
- **Additional sources to paste (optional):** design docs, incident reports, dashboards, runbooks, postmortems

Do not ask for repo lists, Confluence spaces, Jira projects, or Slack channels. These are auto-discovered from user activity.

---

## Phase 0 - GitHub Repo Discovery

Auto-discover all repos where the user has activity in the date range.

For each org, run:
```
gh search prs --author={username} --owner={org} --merged=>{start_date} --limit 100 --json repository
```

Paginate until no more results. Deduplicate repo names across all orgs to build the full repo list.

Log: "Discovered {N} repos with activity across {M} orgs"

---

## Phase 1 - Exhaustive Discovery (parallel subagents)

Spawn one subagent per source. Each subagent's sole job: **paginate until results are exhausted** and return a complete artifact manifest. No content reading in this phase.

Each subagent prompt MUST include verbatim:
> "IMPORTANT: You must paginate until no more results are returned. Do not stop at the first page. Continue requesting the next page/cursor/offset until the API returns zero results."

### GitHub Discovery Subagent

Find all merged PRs and issues by the user across all discovered repos:

```
gh search prs --author={username} --owner={org} --merged={start_date}..{end_date} --limit 100 --json number,title,url,repository,mergedAt
```

Paginate with `--page` until empty. Repeat per org. Then find issues:

```
gh search issues --author={username} --owner={org} --created={start_date}..{end_date} --limit 100 --json number,title,url,repository,createdAt,state
```

Return manifest: `{number, title, url, repo, date, type: "pr"|"issue"}` for every result.

### Confluence Discovery Subagent

Use `mcp__atlassian__searchConfluenceUsingCql` with:
```
CQL: contributor = currentUser() AND lastmodified >= "{start_date}" AND type = page
```

Paginate with cursor until no more results. Return manifest: `{pageId, title, url, date, spaceKey}` for every page.

### Notion Discovery Subagent

Use Notion search/query tools to find all pages authored/edited by the user in the date range. Paginate until exhausted. Return manifest: `{pageId, title, url, date}` for every page.

### Slack Discovery Subagent

Use Slack search tools to find all messages from the user in the date range. Paginate until exhausted. Collect unique thread root IDs. Return manifest: `{threadId, channel, date, preview_text}` for every thread.

### Jira Discovery Subagent

Use `mcp__atlassian__searchJiraIssuesUsingJql` with:
```
JQL: (assignee = currentUser() OR reporter = currentUser()) AND updated >= "{start_date}"
```

Paginate with `startAt` until no more results (increment by `maxResults` each call). Return manifest: `{issueKey, summary, url, status, type, updated}` for every ticket.

### After Phase 1

Merge all manifests. Log total counts:
```
"Found: {N} PRs, {M} issues, {P} Confluence pages, {Q} Notion pages, {R} Slack threads, {S} Jira tickets"
```

---

## Phase 2 - Deep Reading (parallel subagents)

Take the full manifest from Phase 1. Spawn parallel subagents, each receiving a batch of ~10-15 artifacts to read in full.

Each subagent prompt MUST include verbatim:
> "IMPORTANT: Read the FULL body/content of every artifact assigned to you. Do not summarize from titles or metadata alone. Read the actual content."

### What "read in full" means per artifact type

| Type | What to read |
|------|-------------|
| PR | Body/description, review comments, linked issues mentioned in body, file change summary (additions/deletions, key files) |
| Issue | Body, all comments |
| Confluence page | Full page body via `mcp__atlassian__getConfluencePage` with `contentFormat: "markdown"` |
| Notion page | Full page body content |
| Slack thread | All messages in the thread (use thread reply APIs, not just root message) |
| Jira ticket | Description, all comments, linked issues/PRs |

### Signal extraction per artifact

For each artifact, the deep-read subagent returns:

```
### {artifact_url}
- **Type:** PR / issue / page / thread / ticket
- **What changed/discussed:** 1-3 sentences of actual content summary
- **Why it likely mattered:** impact signals found in the content
- **Complexity signals:** technical difficulty, ambiguity, cross-system, novel problem
- **Related artifacts mentioned:** links to other PRs, tickets, docs found in the content
- **Ownership signals:** "I designed", "I implemented", decision language, leadership language
```

### Batch sizing

~10-15 artifacts per subagent. For 150 artifacts total, spawn ~10-15 parallel subagents. For 50 artifacts, spawn ~4-5.

---

## Phase 3 - Triage

Convert Phase 2 signal summaries into **5-8 candidate win threads**.

### Clustering

Group related artifacts across sources into threads. A single win often spans multiple PRs, a Jira ticket, a Confluence design doc, and Slack discussions.

For each thread, write a one-line hypothesis: `What I did -> why it mattered`

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

## Phase 4 - Gap-filling questions

Single round, **8-15 questions max**. Rules:

- One question may cover multiple wins
- Prefer extracting info from artifacts over asking (Phase 2 should have captured most context)
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

## Phase 5 - Produce the win list

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

The report contains only the final polished wins - no intermediate work (candidate threads, scoring, selection rationale, discovery manifests). Those are working artifacts used during discovery and triage but excluded from the output file.

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
- **Thoroughness over speed:** This skill is designed to take longer than typical interactions. Exhaustive source reading is the point - do not shortcut pagination or skip reading artifact content.
