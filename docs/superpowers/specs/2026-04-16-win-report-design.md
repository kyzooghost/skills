# Win Report Skill - Design Spec

## Overview

A skill that discovers and synthesizes engineering wins from multiple artifact sources (GitHub, Confluence, Slack, etc.) over a configurable time range, producing a structured markdown report.

## Decisions

- **Single SKILL.md** - no references/ or scripts/ split. Content compresses to ~300-400 lines.
- **Multi-source discovery** - GitHub (gh CLI), Confluence (Atlassian MCP), Slack MCP, plus user-pasted content. Sources detected and confirmed with user before discovery begins.
- **No hardcoded identifying info** - username resolved at runtime via `gh api /user`, repos and other sources provided by user.
- **Configurable date range** - defaults to last 30 days, accepts custom dates as args.
- **Output to file** - writes `wins-YYYY-MM.md` in current directory.

## Skill Identity

- **Name:** `win-report`
- **Triggers:** "/win-report", "summarize my wins", "what did I ship last month", "monthly wins report", "generate wins for performance review"
- **Args:** Optional `<start-date> <end-date>` in ISO format. Defaults to last 30 days.

## Flow

### Setup (before phases)

1. **Parse date range** from args or default to last 30 days.

2. **Detect available artifact sources** by probing the environment:
   - **GitHub:** Run `gh api /user --jq '.login'`. If authenticated, GitHub is available. If not, note as unavailable (suggest `gh auth login`).
   - **Confluence:** Check if Atlassian MCP tools are available (e.g. `mcp__atlassian__search`). If present, Confluence is available.
   - **Slack:** Check if Slack MCP tools are available. If present, Slack is available.
   - **Jira:** Check if Atlassian MCP tools include Jira search (`mcp__atlassian__searchJiraIssuesUsingJql`). If present, Jira is available.

3. **Present artifact sources to user for confirmation.** List all detected sources with their status (available/unavailable), then ask:
   - Which sources to use (default: all available)
   - For GitHub: which repos to search (accept `owner/repo` or full URLs)
   - For Confluence: which spaces or search terms to scope to (optional)
   - For Jira: which projects or JQL filters to scope to (optional)
   - For Slack: which channels or search terms (optional)
   - Whether they want to add any other sources (e.g. paste design docs, incident reports, dashboards)
   - Optional hints (remembered wins, projects, launches, incidents)

   This is a single consolidated prompt - not multiple rounds.

### Phase 0 - Artifact Discovery

Search all confirmed sources in parallel where possible.

**GitHub** (if enabled):
- PRs authored: `gh pr list --repo {repo} --author {username} --state merged --search "merged:>{start_date}" --limit 100 --json number,title,body,mergedAt,additions,deletions,labels,url`
- Issues assigned: `gh issue list --repo {repo} --assignee {username} --state all --search "created:>{start_date}" --limit 50 --json number,title,body,state,createdAt,url`
- Run in parallel across all repos.

**Confluence** (if enabled):
- Use `mcp__atlassian__search` or `mcp__atlassian__searchConfluenceUsingCql` to find pages authored/edited by the user in the date range, scoped to specified spaces.

**Jira** (if enabled):
- Use `mcp__atlassian__searchJiraIssuesUsingJql` with JQL like `assignee = currentUser() AND updated >= "{start_date}"` scoped to specified projects.

**Slack** (if enabled):
- Search for messages from the user in specified channels within the date range.

**User-pasted content:**
- Incorporate any design docs, incident reports, dashboards, or other artifacts the user provided during setup.

Extract candidate signals looking for:
- Large/complex diffs, architectural changes, security fixes, performance improvements
- Infra changes, incident resolution, migrations, reliability improvements
- Tooling/framework work, test harness additions, automation
- Cross-team coordination, debugging of ambiguous failures

Format as candidate signals, then cluster into win threads.

### Phase 1 - Triage

Convert to 5-8 candidate win threads. Each gets a one-line hypothesis: `What I did -> why it mattered`.

Select top 3 using ranking heuristic:
- +2 architectural impact, +2 cross-team leverage, +2 risk reduction
- +1 technical complexity, +1 artifact richness, +1 durable enablement
- Override score if a lower-scoring item is clearly more promotion-relevant

Selection preferences: concrete shipments > maintenance, decisions > participation, outcomes > effort, durable leverage > one-off busywork.

### Phase 2 - Gap-filling question round

Single round, 8-15 questions max. Rules:
- One question may cover multiple wins
- Ask for metric proxies before giving up (before/after time, incident count, failure rate, adoption, latency, dollars saved, toil reduced)
- Ask about alternatives considered and risk avoided for key decisions
- Ask for exact scope boundaries where ownership is blurred
- Do not ask for info artifacts already show

### Phase 3 - Produce win list

Top 3 wins using this template:

```
## TITLE

**What I shipped/solved:** 1-2 punchy sentences.
**Why it mattered:** Stakes and who benefited.
**Why it was difficult:** Optional. Technical difficulty, ambiguity, or non-obvious judgment.
**Impact (current):** Metrics or strong proxies with baseline.
**My ownership:** Explicit "I" language. Clarify collaborator boundaries.
**Evidence / artifacts:** PRs, docs, dashboards, incidents, links or [LINK] placeholders.
**Missing evidence:** Optional. Screenshots, adoption numbers, before-state, metrics still needed.
**Notes to self (confirm later):** Short bullets only.
```

### Bonus Phase - Public artifact idea

If any win contains a rare technical lesson, propose one public artifact idea (X thread, short post, engineering note, talk outline).

## Output

Write to `wins-YYYY-MM.md` in current working directory.

## Writing rules for final output

- Optimize for skeptical, time-poor outsider with no team context
- No jargon without brief explanation
- No inflated claims, no passive voice where ownership matters
- No "supported", "helped with", "involved in" - prefer "I designed", "I implemented", "I debugged"
- Every sentence must earn its place, each introducing a new concept
- Do not accept "we" as contribution - force explicit "I did X" ownership

## Constraints

- Question budget: 8-15 total across all phases
- Prefer artifact extraction over asking the user
- Flag weak/missing evidence clearly
- Use placeholders and "Notes to self" over blocking on missing details
- Direct but supportive tone
