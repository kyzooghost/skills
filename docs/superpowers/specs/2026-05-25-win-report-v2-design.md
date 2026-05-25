# Win Report v2 - Exhaustive Subagent Architecture

## Problem

The current win-report skill does shallow discovery:
- Finds pages/threads but doesn't read their full content
- Stops at first page of results (~10 Slack threads, ~100 PRs per repo) instead of paginating through all
- User has to manually point out wins the skill could have found from available sources

## Goal

Make the skill exhaustively search and deeply read all available sources before synthesizing wins. The user should never have to say "you missed this - it was right there."

## Input Model

### Invocation

```
/win-report                          # prompts for all params
/win-report 2026-04-01 2026-05-01   # custom date range, prompts for rest
```

### Required inputs (single consolidated prompt)

| Input | Description | Default |
|-------|-------------|---------|
| `github_user` | GitHub username | Auto-detected via `gh api /user --jq '.login'` |
| `github_org` | GitHub org(s) to search (comma-separated if multiple) | Prompted |
| `date_range` | Start/end dates (YYYY-MM-DD) | Last 30 days |
| `mcps` | Which non-GitHub MCPs to use | Auto-detected from available tools (Atlassian, Notion, Slack) |
| `hints` | Projects, launches, incidents, team names to weight | Optional |

### Removed from input

- Manual repo lists (auto-discovered from org activity)
- Confluence space scoping (searches all spaces user has activity in)
- Jira project scoping (searches all projects user has activity in)
- Slack channel scoping (searches all messages from user)

### GitHub repo auto-discovery

Uses GitHub search API to find all repos in each org where the user has merged PRs or commits in the date range. No manual listing required. Runs per org if multiple orgs specified.

```
gh search prs --author={user} --owner={org} --merged=>{start_date} --limit 100 --json repository
```

Deduplicate repo names from results across all orgs to build the repo list.

## Architecture: Two-Phase Subagents

### Phase 1 - Exhaustive Discovery (parallel subagents)

Each subagent's sole job: paginate until results are exhausted, return a complete artifact manifest.

| Subagent | What it finds | Pagination strategy |
|----------|---------------|-------------------|
| GitHub Discovery | All merged PRs + issues by user across all repos in all specified orgs within date range | `gh search prs --author={user} --owner={org} --merged=>{start}..{end} --limit 100` per org, paginate until empty. Then issues. |
| Confluence Discovery | All pages authored/edited by user in date range | CQL: `contributor = currentUser() AND lastmodified >= "{start}"`, paginate with cursor until no more results |
| Notion Discovery | All pages authored/edited by user in date range | Search API with pagination until exhausted |
| Slack Discovery | All messages from user in date range | Search with pagination, collecting thread root IDs |
| Jira Discovery | All tickets assigned/reported/commented by user in date range | JQL with `startAt` pagination until exhausted |

Each subagent returns a manifest:
```
{id, title, url, date, type, source}
```

for every artifact found. No content reading in this phase.

After Phase 1 completes, log: "Found {N} PRs, {M} pages, {K} threads, {J} tickets"

### Phase 2 - Deep Reading (parallel subagents)

Take the full manifest from Phase 1. Spawn subagents that each receive a batch of ~10-15 artifacts to read in full.

"Read in full" means:
- **PR:** body, review comments, linked issues, file change summary (additions/deletions, key files changed)
- **Confluence page:** full page body content via `getConfluencePage`
- **Notion page:** full page body content
- **Slack thread:** all messages in the thread (not just root message)
- **Jira ticket:** description, all comments, linked issues/PRs

Each deep-read subagent returns structured signal summaries:
```
{
  artifact_url,
  what_changed,
  why_it_likely_mattered,
  complexity_signals,
  related_artifacts_mentioned
}
```

Batch sizing: ~10-15 artifacts per subagent. For 150 artifacts total, that's ~10-15 parallel deep-read subagents.

### Phase 3 - Synthesis (main agent)

Main agent receives all signal summaries from Phase 2, then proceeds with existing triage/synthesis flow:

1. Cluster related signals into 5-8 candidate win threads
2. Score each candidate (architectural impact +2, cross-team leverage +2, risk reduction +2, technical complexity +1, artifact richness +1, durable enablement +1)
3. Select top 3
4. Ask 8-15 gap-filling questions (single round)
5. Produce final report

## Guardrails

- **No early termination:** Discovery agents MUST paginate until results are exhausted. Subagent prompts explicitly state "do not stop at first page - paginate until no more results are returned."
- **Deep-read completeness:** Every artifact in the manifest gets read in full. No sampling, no relevance filtering before reading.
- **Manifest logging:** After Phase 1, display total artifact count to the user so they can see scope.
- **Explicit subagent instructions:** Each subagent prompt includes verbatim: "paginate until no more results" and "read the full body content, not just metadata."
- **Timeout tolerance:** This process takes longer than a typical interaction. The skill notes this is expected.

## What Stays the Same

- Output format: win template, summary table, public artifact idea
- Triage scoring system
- Gap-filling question phase (8-15 questions max)
- Writing rules (skeptical outsider audience, "I" language, no fluff, no jargon)
- Top 3 wins selection with override for promotion-relevance
- Output file: `wins-YYYY-MM.md` in current working directory
- Selection preferences: concrete shipments > maintenance, decisions > participation, outcomes > effort, durable leverage > one-off work

## What Changes

| Aspect | Before | After |
|--------|--------|-------|
| Input | Manual repo list, space/project/channel scoping | `github_user` + `github_org` + which MCPs. Auto-discover repos. |
| Discovery | Single pass, limited results, no pagination | Exhaustive pagination per source until empty |
| Reading depth | PR JSON fields only (title, body, dates) | Full PR body + comments + linked issues |
| Confluence/Notion | Search result metadata | Full page body read for every page found |
| Slack | ~10 results, surface-level | All threads paginated, full thread content read |
| Architecture | Single agent, sequential | Two-phase parallel subagents: discovery then deep-read |
| Subagent instructions | Implicit | Explicit: "paginate until exhausted", "read full content" |

## SKILL.md Structure (after rewrite)

1. **Invocation** - same format, simplified
2. **Setup** - parse dates, detect MCPs, single prompt for inputs
3. **Phase 0: Repo Discovery** - GitHub search for active repos
4. **Phase 1: Exhaustive Discovery** - parallel subagents, one per source, paginate until empty
5. **Phase 2: Deep Reading** - parallel subagents, batches of 10-15 artifacts, read full content
6. **Phase 3: Triage** - cluster, score, select top 3 (unchanged logic)
7. **Phase 4: Gap-filling** - 8-15 questions (unchanged)
8. **Phase 5: Produce report** - same template, same writing rules
9. **Bonus: Public artifact idea** - unchanged
10. **Output** - same file format and location
