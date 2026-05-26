# Peer Review Skill - Design Spec

## Purpose

Generate draft peer review answers for annual performance reviews. Sources evidence from GitHub, Confluence, Jira, Notion, and Slack MCPs, plus user-pasted DM snippets. Produces human-sounding 1-2 paragraph answers per review form question, with a separate evidence appendix.

## Goals

- Supportive of bonus/review rating with concrete evidence
- Surface specific, constructive growth feedback to help the person multiply their output
- Minimize user effort - exhaust data sources before asking questions
- Directly usable output mapped 1:1 to review form questions

## Invocation

```
/peer-review
```

Prompts for:
- **Name**: Display name of the person being reviewed
- **GitHub username**: Their GitHub handle
- **Review form questions**: User pastes the actual questions from the form
- **DM snippets (optional)**: Pasted conversation from any messaging platform
- **Hints (optional)**: Projects, teams, systems to weight during discovery
- **Relationship (optional)**: Default "peer" - user overrides if different (e.g., "junior I mentor")

## Phase 0 - Setup & Repo Discovery

### Detect available sources

| Source | Detection method |
|--------|-----------------|
| GitHub | `gh api /user --jq '.login'` succeeds |
| Atlassian (Confluence + Jira) | `mcp__atlassian__search` tool exists |
| Notion | Any `mcp__notion__*` tools exist |
| Slack | Any `mcp__slack__*` tools exist |

### Collect inputs (single consolidated prompt)

Ask in one prompt:
- GitHub org(s) to search
- Which detected sources to include (default: all available)
- Hints (optional)
- DM snippets to paste (optional, can also be provided later)

### Atlassian account resolution

If Confluence/Jira sources are available, resolve the person's Atlassian account ID from their name using `mcp__atlassian__lookupJiraAccountId`. Store for use in CQL/JQL queries.

### Repo discovery

For each org, find repos where the target user has activity in the last 365 days:
```
gh search prs --author={their_username} --owner={org} --merged=>{start_date} --limit 100 --json repository
```
Paginate until exhausted. Deduplicate.

## Phase 1 - Exhaustive Discovery (parallel subagents)

One subagent per source. Each paginates until results are exhausted. Returns artifact manifests only - no content reading.

Date range: last 365 days from today. Soft preference for last 6 months (applied in triage, not discovery).

Each subagent prompt includes verbatim:
> "IMPORTANT: You must paginate until no more results are returned. Do not stop at the first page. Continue requesting the next page/cursor/offset until the API returns zero results."

### GitHub Discovery Subagent

Find all merged PRs and issues by the target user:
```
gh search prs --author={their_username} --owner={org} --merged={start_date}..{end_date} --limit 100 --json number,title,url,repository,mergedAt
```
Also find PRs where the reviewer (you) commented on their PRs:
```
gh search prs --author={their_username} --owner={org} --commenter={your_username} --merged={start_date}..{end_date} --limit 100 --json number,title,url,repository,mergedAt
```
And PRs where they reviewed yours:
```
gh search prs --author={your_username} --owner={org} --commenter={their_username} --merged={start_date}..{end_date} --limit 100 --json number,title,url,repository,mergedAt
```

Return manifest: `{number, title, url, repo, date, type: "pr"|"issue", interaction: bool}`

### Confluence Discovery Subagent

```
CQL: contributor = "{their_account_id}" AND lastmodified >= "{start_date}" AND type = page
```
Paginate with cursor until exhausted.

Also search for pages where both contributed:
```
CQL: contributor = currentUser() AND contributor = "{their_account_id}" AND lastmodified >= "{start_date}" AND type = page
```

Return manifest: `{pageId, title, url, date, spaceKey, shared: bool}`

### Jira Discovery Subagent

```
JQL: (assignee = "{their_account_id}" OR reporter = "{their_account_id}") AND updated >= "{start_date}"
```
Paginate with `startAt` until exhausted.

Return manifest: `{issueKey, summary, url, status, type, updated}`

### Notion Discovery Subagent

Search for pages authored/edited by the target user in the date range. Paginate until exhausted.

Return manifest: `{pageId, title, url, date}`

### Slack Discovery Subagent

Search for messages from the target user. Paginate until exhausted. Collect unique thread root IDs.

Return manifest: `{threadId, channel, date, preview_text}`

### After Phase 1

Merge all manifests. Log total counts.

## Phase 2 - Deep Reading (parallel subagents)

Batch ~10-15 artifacts per subagent. Read full content of every artifact.

Each subagent prompt includes verbatim:
> "IMPORTANT: Read the FULL body/content of every artifact assigned to you. Do not summarize from titles or metadata alone. Read the actual content."

### What to read per artifact type

| Type | What to read |
|------|-------------|
| PR | Body/description, review comments, file change summary |
| Issue | Body, all comments |
| Confluence page | Full page body + footer/inline comments |
| Notion page | Full page body content |
| Slack thread | All messages in thread |
| Jira ticket | Description, all comments, linked issues/PRs |

### Signal extraction per artifact

```
### {artifact_url}
- **Type:** PR / issue / page / thread / ticket
- **What they did:** 1-3 sentences of actual contribution
- **Impact signals:** why it mattered, who benefited
- **Complexity signals:** technical difficulty, ambiguity, cross-system, novel problem
- **Decision signals:** choices made, alternatives rejected, direction set
- **Interaction flag:** did the reviewer (your username) appear? How?
  - You reviewed their PR / commented
  - They reviewed your PR / commented
  - You both commented on same Confluence page
  - You both edited same Confluence page
  - Direct exchange in thread
- **Interaction detail:** if flagged, what was the nature of the interaction? (review feedback, design discussion, decision-making, knowledge sharing)
```

### DM snippet processing

If DM snippets were provided, parse as a virtual source alongside MCP data. Extract:
- Interaction patterns (help given/received, decisions made together)
- Communication style signals
- Growth signals (questions asked, areas of uncertainty)
- Wins mentioned in conversation not captured elsewhere

## Phase 3 - Triage (review-form-shaped)

### Clustering by review question

For each pasted review form question, cluster relevant artifacts into themes. A single question might draw from multiple artifact types.

Example mapping:
- "Deliver great customer & strategic outcomes" -> shipped features, customer-facing work, strategic alignment
- "Skills to improve" -> patterns of difficulty, repeated struggles, areas with less confidence

### Selection criteria

For each question, select 2-4 strongest examples:
- **Soft recency preference**: prioritize last 6 months, but include older examples if they're clearly stronger or cover a theme nothing recent does
- **Interaction-flagged artifacts weighted higher**: these are your "I observed firsthand" evidence
- **Concrete > vague**: prefer examples with measurable outcomes or clear decisions

### Growth area candidates

From evidence patterns (NOT PR mechanics), propose 1-3 candidate growth areas. Focus on:
- Decision-making patterns
- Initiative and ownership scope
- Communication effectiveness
- Cross-team influence
- Technical direction-setting
- Areas where they sought help repeatedly

## Phase 4 - Questions (~15 max)

Single round. Split roughly 1/3 scope, 2/3 feedback.

### Scope verification (~5 questions)

- "I found X, Y, Z as their main contributions this year. Am I missing anything significant?"
- "Was [specific project] primarily their work or shared?"
- "I noticed [gap] - is that accurate or did I miss a source?"

### Feedback questions (~10 questions)

These questions must be **evidence-guided prompts**, not open-ended asks. The user may not have ready answers to broad questions like "Where have they grown?" - but they DO have latent observations that the right prompt can surface. Use the discovered evidence to jog their memory and help them articulate what they already feel.

**Pattern: Present evidence, ask if it resonates, invite elaboration.**

Examples of good evidence-guided questions:
- "I noticed they went from [X behavior in older artifacts] to [Y behavior in recent artifacts]. Does that match a growth pattern you've observed? What shifted?"
- "In [specific PR/doc], they made [specific decision]. Was this typical of how they operate, or was this a step up for them?"
- "I see they were involved in [project A] and [project B] which seem cross-team. Did their involvement make those projects easier for you or others? How?"
- "Looking at [specific artifact], it seems like [situation] was tricky. How did they handle it from your perspective? Anything they could have done differently?"
- "I found [evidence of repeated pattern]. Does this connect to something you've noticed day-to-day that the artifacts wouldn't capture?"
- "For the growth question - I see strength in [area] but less evidence of [adjacent area]. Does that gap feel real? What would it look like if they developed that?"

**Anti-pattern: Do NOT ask these kinds of broad questions:**
- "What's one thing they do that makes your work easier?" (too open, user draws blank)
- "Where have you seen them grow?" (too abstract without prompting)
- "What could they improve?" (puts user on the spot without scaffolding)

Rules:
- Always anchor questions in specific evidence you found
- Help the user *discover* their answer, not produce one from scratch
- Frame growth questions around patterns you observed + ask if they resonate
- If you noticed an interaction between the user and the person, ask about that specific moment

## Phase 5 - Output

### Per review form question

1-2 paragraphs per question:
- Human-sounding, first-person "I observed..." voice
- Specific examples woven naturally into the prose
- No jargon without brief explanation
- Supportive tone for strengths
- Constructive framing for growth areas (what they could do more of, not what they did wrong)
- No inflated claims - grounded in evidence

### Evidence Appendix

Separate section at the bottom:
```markdown
## Evidence Appendix

### [Question 1 text]
- [artifact title](url) - brief note on relevance
- [artifact title](url) - brief note on relevance

### [Question 2 text]
- ...
```

### Output file

Written to `peer-review-{name}-YYYY-MM.md` in current working directory.

## Writing Rules

- First-person "I observed", "I noticed", "In my experience working with them"
- Specific over generic - name the project, the decision, the outcome
- Growth feedback framed as "what would amplify their impact" not "what they did wrong"
- No passive voice where attribution matters
- Interaction-based evidence is strongest - prefer "I saw them do X in [situation]" over "they did X"
- 1-2 paragraphs per answer - enough depth to be substantive, short enough to respect the reader's time
- Each answer should stand alone without needing the appendix

## Constraints

- **Question budget:** ~15 total (~5 scope, ~10 feedback)
- **Discovery bias:** Exhaust data sources before asking
- **Recency:** Soft preference for last 6 months, older examples still valid
- **Evidence over speculation:** Flag if an answer is thin on evidence
- **Tone:** Supportive, constructive, honest. No inflation, no harshness.
- **Thoroughness over speed:** Exhaustive source reading is the point
- **No PR-mechanics judgments:** Don't evaluate PR size, code style, etc. as growth areas - these are AI-assisted
