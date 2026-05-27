---
name: peer-review
description: Generate evidence-backed draft peer review answers for annual performance reviews. Sources from GitHub PRs/issues, Confluence, Jira, Notion, and Slack over the last year, plus user-pasted DM snippets from any messaging platform. Uses exhaustive two-phase subagent architecture to discover all artifacts, read them in full, then synthesize into human-sounding answers mapped 1:1 to the review form questions. Use when the user says "/peer-review", "write a peer review", "help me with performance review feedback", "peer feedback for [name]", or asks to write review answers for a colleague.
---

# Peer Review

Generate evidence-backed draft answers for peer performance review forms using exhaustive multi-source research.

## Invocation

- `/peer-review` - prompts for all params

## Setup

### 1. Collect inputs (single consolidated prompt)

Ask in one prompt:
- **Name:** Display name of the person being reviewed
- **GitHub username:** Their GitHub handle
- **Review form questions:** User pastes the actual questions from the form
- **GitHub org(s):** Comma-separated org names to search
- **DM snippets (optional):** Pasted conversation from any messaging platform (can also be provided later)
- **Hints (optional):** Projects, teams, systems to weight during discovery
- **Relationship (optional):** Default "peer" - user overrides if different (e.g., "junior I mentor")

### 2. Detect available sources

Probe the environment for each source type:

| Source | Detection method |
|--------|-----------------|
| GitHub | Run `gh api /user --jq '.login'`. If succeeds, GitHub is available and your username is captured. |
| Atlassian (Confluence + Jira) | Check if `mcp__atlassian__search` tool exists. |
| Notion | Check if any `mcp__notion__*` tools exist. |
| Slack | Check if any `mcp__slack__*` tools exist. |

### 3. Atlassian account resolution

If Atlassian source is available, resolve the person's Atlassian account ID from their name using `mcp__atlassian__lookupJiraAccountId`. Store for use in CQL/JQL queries.

### 4. Date range

Calculate: start_date = today minus 365 days (YYYY-MM-DD), end_date = today (YYYY-MM-DD).

### 5. Repo discovery

For each org, run:
```
gh search prs --author={their_username} --owner={org} --merged=>{start_date} --limit 100 --json repository
```

Paginate until no more results. Deduplicate repo names across all orgs.

Log: "Discovered {N} repos with activity across {M} orgs"

---

## Phase 1 - Exhaustive Discovery (parallel subagents)

Spawn one subagent per source. Each subagent's sole job: **paginate until results are exhausted** and return a complete artifact manifest. No content reading in this phase.

Each subagent prompt MUST include verbatim:
> "IMPORTANT: You must paginate until no more results are returned. Do not stop at the first page. Continue requesting the next page/cursor/offset until the API returns zero results."

### GitHub Discovery Subagent

Find all merged PRs and issues by the target user:

```
gh search prs --author={their_username} --owner={org} --merged={start_date}..{end_date} --limit 100 --json number,title,url,repository,mergedAt
```

Paginate with `--page` until empty. Repeat per org. Then find issues:

```
gh search issues --author={their_username} --owner={org} --created={start_date}..{end_date} --limit 100 --json number,title,url,repository,createdAt,state
```

Also find interaction PRs - PRs where you commented on theirs:
```
gh search prs --author={their_username} --owner={org} --commenter={your_username} --merged={start_date}..{end_date} --limit 100 --json number,title,url,repository,mergedAt
```

And PRs where they commented on yours:
```
gh search prs --author={your_username} --owner={org} --commenter={their_username} --merged={start_date}..{end_date} --limit 100 --json number,title,url,repository,mergedAt
```

Return manifest: `{number, title, url, repo, date, type: "pr"|"issue", interaction: bool}` for every result.

### Confluence Discovery Subagent

Use `mcp__atlassian__searchConfluenceUsingCql` with:
```
CQL: contributor = "{their_account_id}" AND lastmodified >= "{start_date}" AND type = page
```

Paginate with cursor until no more results.

Also search for shared pages (both of you contributed):
```
CQL: contributor = currentUser() AND contributor = "{their_account_id}" AND lastmodified >= "{start_date}" AND type = page
```

Return manifest: `{pageId, title, url, date, spaceKey, shared: bool}` for every page.

### Jira Discovery Subagent

Use `mcp__atlassian__searchJiraIssuesUsingJql` with:
```
JQL: (assignee = "{their_account_id}" OR reporter = "{their_account_id}") AND updated >= "{start_date}"
```

Paginate with `startAt` until no more results (increment by `maxResults` each call).

Return manifest: `{issueKey, summary, url, status, type, updated}` for every ticket.

### Notion Discovery Subagent

Use Notion search/query tools to find all pages authored/edited by the target user in the date range. Paginate until exhausted.

Return manifest: `{pageId, title, url, date}` for every page.

### Slack Discovery Subagent

Use Slack search tools to find messages from the target user in the date range. Paginate until exhausted. Collect unique thread root IDs.

Return manifest: `{threadId, channel, date, preview_text}` for every thread.

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
| PR | Body/description, review comments, file change summary (additions/deletions, key files) |
| Issue | Body, all comments |
| Confluence page | Full page body via `mcp__atlassian__getConfluencePage` with `contentFormat: "markdown"`, plus footer/inline comments |
| Notion page | Full page body content |
| Slack thread | All messages in the thread (use thread reply APIs, not just root message) |
| Jira ticket | Description, all comments, linked issues/PRs |

### Signal extraction per artifact

For each artifact, the deep-read subagent returns:

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

### Batch sizing

~10-15 artifacts per subagent. For 150 artifacts total, spawn ~10-15 parallel subagents. For 50 artifacts, spawn ~4-5.

---

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

From evidence patterns (NOT PR mechanics - do not evaluate PR size, code style, commit frequency, or similar AI-assisted artifacts), propose 1-3 candidate growth areas. Focus on:
- Decision-making patterns
- Initiative and ownership scope
- Communication effectiveness
- Cross-team influence
- Technical direction-setting
- Areas where they sought help repeatedly

---

## Phase 4 - Gap-filling questions

Single round, **~15 questions max**. Split roughly 1/3 scope, 2/3 feedback.

### Scope verification (~5 questions)

- "I found X, Y, Z as their main contributions this year. Am I missing anything significant?"
- "Was [specific project] primarily their work or shared?"
- "I noticed [gap in area] - is that accurate or did I miss a source?"

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
- Do not ask for context the artifacts already show

---

## Phase 5 - Produce the review answers

Output one answer per review form question.

### Per review form question

1-2 paragraphs per question:
- Human-sounding, first-person "I observed..." voice
- Specific examples woven naturally into the prose
- No jargon without brief explanation
- Supportive tone for strengths
- Constructive framing for growth areas (what they could do more of, not what they did wrong)
- No inflated claims - grounded in evidence

### Evidence Appendix

After all answers, include a separate section:

```markdown
## Evidence Appendix

### [Question 1 text]
- [artifact title](url) - brief note on relevance
- [artifact title](url) - brief note on relevance

### [Question 2 text]
- ...
```

---

## Output

Write the full review to `peer-review-{name}-YYYY-MM.md` in the current working directory.

Include in this order:
1. Title header: `# Peer Review - {Name} - {Month} {Year}`
2. Answers per review form question (full prose)
3. Evidence Appendix

---

## Writing rules

Target reader: the person being reviewed and their manager.

- First-person "I observed", "I noticed", "In my experience working with them"
- Specific over generic - name the project, the decision, the outcome
- Growth feedback framed as "what would amplify their impact" not "what they did wrong"
- No passive voice where attribution matters
- Interaction-based evidence is strongest - prefer "I saw them do X in [situation]" over "they did X"
- 1-2 paragraphs per answer - enough depth to be substantive, short enough to respect the reader's time
- Each answer should stand alone without needing the appendix
- No jargon without brief explanation
- No inflated claims - grounded in evidence
- Supportive tone for strengths, constructive framing for growth areas
- **Never reference specific hours worked** (e.g., "stayed until midnight", "worked weekends"). Frame dedication as "sustained focus", "persistence", or "availability" - specific hours can read as a work-life balance concern rather than a compliment.
- **Be concise** - aim for density over length. If 2 paragraphs can carry the same content as 3, use 2. Every sentence should earn its place.
- **Write for an engineering manager, not an engineer** - describe impact and outcomes at a level a non-practitioner can follow. Avoid laundry lists of technologies. Instead of "Helm chart archetypes, Argo Rollouts, per-app vault isolation, Istio egress centralization", write "deployment automation, secret management, networking, and safe rollout strategies". The Evidence Appendix is where technical specifics live.

## Constraints

- **Question budget:** ~15 total (~5 scope, ~10 feedback)
- **Discovery bias:** Exhaust data sources before asking
- **Recency:** Soft preference for last 6 months, older examples still valid
- **Evidence over speculation:** Flag if an answer is thin on evidence
- **Tone:** Supportive, constructive, honest. No inflation, no harshness.
- **Thoroughness over speed:** Exhaustive source reading is the point - do not shortcut pagination or skip reading artifact content.
- **No PR-mechanics judgments:** Do not evaluate PR size, code style, commit frequency, or similar as growth areas - these are AI-assisted.
