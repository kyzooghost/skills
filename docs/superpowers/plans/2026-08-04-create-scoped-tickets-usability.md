# Create Scoped Tickets Usability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Make skills/create-scoped-tickets/SKILL.md usable by first-time readers without changing its ticket-universe, overlap, approval, or filing behavior.

**Architecture:** Keep the skill as one self-contained Markdown file. Add an orientation block, requirements, glossary, corrected Skill-tool invocation, and one neutral Seed-mode example around the existing Phase 0-5 workflow. Extend the skill's static verification commands to cover the new onboarding contract.

**Tech Stack:** Markdown, Git, rg, GitHub CLI documentation

**Design:** docs/superpowers/specs/2026-08-04-create-scoped-tickets-usability-design.md

## Global Constraints

- Modify only skills/create-scoped-tickets/SKILL.md during implementation.
- Do not add commands/create-scoped-tickets.md, a reference file, or a test file.
- Preserve the existing Phase 0-5 workflow, scope classification, batch approval gate, amendment behavior, and gh issue create filing rules.
- Use $create-scoped-tickets in the documented invocation and examples; do not leave the old slash-command invocation in the target skill.
- Keep the Agent Work Ticket template and recognized scope headings unchanged.
- Use regular hyphens instead of em dashes in all new Markdown.
- The old-invocation verification must use a non-literal, line-anchored pattern such as ^[[:space:]]*/create-[[:lower:]-]+; do not put the contiguous old slash-command string into the skill merely to test for it.
- Because this is documentation-only, validate with Markdown/static checks and diff inspection; do not invent runtime unit tests.

## File map

- Modify: skills/create-scoped-tickets/SKILL.md - the user-facing skill instructions and their static verification commands.
- Reference: docs/superpowers/specs/2026-08-04-create-scoped-tickets-usability-design.md - approved design contract.
- Reference: docs/todos/2026-07-29-create-scoped-tickets-usability.md - the five selected usability findings.
- No other implementation files, command wrappers, references, or tests are created.

---

### Task 1: Add first-time-user orientation, requirements, glossary, and invocation

**Files:**
- Modify: skills/create-scoped-tickets/SKILL.md:1-30 for frontmatter and onboarding sections.
- Modify: skills/create-scoped-tickets/SKILL.md:225-236 for Skill-tool invocation.
- Reference: docs/superpowers/specs/2026-08-04-create-scoped-tickets-usability-design.md:41-92.

- [ ] **Step 1: Capture the existing insertion and replacement anchors**

Run:

~~~bash
rg -n '^description:|^# Create Scoped Tickets|^## Inputs|^## Invocation|^/create-scoped-tickets' skills/create-scoped-tickets/SKILL.md
~~~

Expected: the command reports the current frontmatter description, the Create Scoped Tickets heading, Inputs, Invocation, and the three old slash-command lines. Use those anchors for a focused patch.

- [ ] **Step 2: Replace the trigger description and opening block**

Replace the current description line with:

~~~yaml
description: Use when the user asks to seed or extend a GitHub label-scoped ticket set from a spec.
~~~

Replace the content from the Create Scoped Tickets heading through the paragraph immediately before Inputs with this exact Markdown, preserving the existing YAML frontmatter above it:

~~~markdown
# Create Scoped Tickets

Use this skill to seed or extend a GitHub label-scoped universe of mutually-exclusive Agent Work Tickets from a technical implementation spec.

1. **Seed** - the label universe is empty. Decompose the spec into the first N tickets.
2. **Append** - the label universe already has tickets. Decompose the spec, then only draft what is not already covered. Where the spec overlaps an existing open ticket, propose amending that ticket instead of filing a duplicate.

The skill drafts tickets as text first, presents the full set for one batch approval, then files each approved new ticket via gh issue create. It never edits or closes existing issues; overlap resolutions are proposed to the user in text form.

## Fits into the workflow

1. **Seed or extend the boundary set** - [create-scoped-tickets](SKILL.md) creates or extends the labeled Agent Work Ticket universe.
2. **Scope the design and plan** - [scoped-planning](../scoped-planning/SKILL.md) consumes selected ticket numbers to scope brainstorming, plan grilling, and implementation-plan writing.
3. **Route review findings** - [scoped-differential-review](../scoped-differential-review/SKILL.md) consumes selected ticket numbers to classify PR findings against the ticket universe.
4. **Execute a completed plan** - [ship-from-plan](../ship-from-plan/SKILL.md) consumes the completed plan produced downstream and executes it through a reviewed draft PR. It does not require ticket numbers as a direct input.

The Agent Work Ticket headings are a repository-local schema. Downstream skills recognize headings such as The owner may, The owner must not, Scope of Work, Not In Scope, and Definition of Done; they use the ownership and exclusion headings to build scope boundaries, while Definition of Done remains part of the recognized ticket structure. Preserve the template's structure when creating or amending tickets.

## Requirements

Before starting, confirm:

- A GitHub repository with Issues enabled.
- The gh CLI installed and authenticated.
- Permission to read issues and create new issues.
- At least one usable label, or permission to create a missing label after confirmation.
- A readable spec source.

If a requested label does not exist, the skill reports it and asks whether to create it via gh label create; it never creates a label without confirmation.

## Glossary

- **Agent Work Ticket** - a GitHub issue with exclusive ownership, exclusions, dependencies, and verifiable completion criteria.
- **Label universe** - all open issues in the repository carrying any requested label.
- **Scope map** - the ownership and exclusion boundaries extracted from those issues.
- **Amendment proposal** - text-only suggested changes to an existing issue; this skill never applies them automatically.
~~~

Expected: the target file now explains the downstream workflow, prerequisites, and schema before Inputs; the existing Inputs section remains immediately after the new glossary.

- [ ] **Step 3: Replace the invocation block with Skill-tool syntax**

Replace the complete content from Invocation through the two existing examples with:

~~~~markdown
## Invocation

Invoke this skill with:

~~~text
$create-scoped-tickets <SPEC> --repo <OWNER/REPO> --labels <label1>[,label2,...] [--scope-hint "<one-sentence hint>"]
~~~

Examples:

~~~text
$create-scoped-tickets docs/spec.md --repo org/project --labels topic1
$create-scoped-tickets docs/spec.md --repo org/project --labels topic1,topic2 --scope-hint "only §4 (execution layer)"
~~~
~~~~

Expected: the target file contains the $create-scoped-tickets form and no contiguous old slash-command invocation.

- [ ] **Step 4: Run the focused onboarding checks**

Run:

~~~bash
rg -n '^## Fits into the workflow|^## Requirements|^## Glossary|\$create-scoped-tickets|repository-local schema' skills/create-scoped-tickets/SKILL.md
~~~

Expected: each new section and the Skill-tool invocation appears in the output.

Run:

~~~bash
if rg -n '^[[:space:]]*/create-[[:lower:]-]+' skills/create-scoped-tickets/SKILL.md; then
  exit 1
else
  echo 'No slash-command invocation remains.'
fi
~~~

Expected: the command prints No slash-command invocation remains. and exits successfully.

- [ ] **Step 5: Commit the onboarding change**

~~~bash
git add skills/create-scoped-tickets/SKILL.md
git diff --cached --check
git commit -m "docs(create-scoped-tickets): add onboarding context"
~~~

Expected: one commit modifies only skills/create-scoped-tickets/SKILL.md.

### Task 2: Add the neutral Seed-mode worked example and extend static verification

**Files:**
- Modify: skills/create-scoped-tickets/SKILL.md immediately before Phase 5 - File approved NEW drafts.
- Modify: skills/create-scoped-tickets/SKILL.md:238-258 in Verification.
- Reference: docs/superpowers/specs/2026-08-04-create-scoped-tickets-usability-design.md:94-135.

- [ ] **Step 1: Insert the worked example after the Phase 4 approval rules**

Insert the following complete illustrative section immediately after the paragraph stating that amendment proposals are never filed and before Phase 5 - File approved NEW drafts:

~~~~markdown
### Worked example - Seed mode

This example is illustrative only. It shows the Phase 4 output and approval gate; it does not call gh issue create.

**Input:**

~~~text
SPEC: docs/report-export-spec.md
REPO: acme/reporting
LABELS: agent-work-ticket
Universe: zero open tickets with that label
~~~

**Spec excerpt:**

- §1 Export endpoint - add POST /reports/exports, validate the request, and return an export job identifier.
- §2 Export audit event - record an ExportRequested audit event after an export request is accepted. Consume the accepted-request hook exposed by [draft #A].

**Universe snapshot:** agent-work-ticket, acme/reporting, Seed mode, zero existing tickets.

**Coverage map:** docs/report-export-spec.md §1 -> [draft #A]; docs/report-export-spec.md §2 -> [draft #B]. [draft #B] depends on the accepted-request hook from [draft #A].

#### [draft #A] Reports API - create export jobs

## Agent Work Ticket

### Request / Outcome

* Add POST /reports/exports for validated report-export requests.
* Return an export job identifier after an accepted request.
* Expose an accepted-request hook stub for the audit consumer owned by [draft #B].

### Background / Context

* This is the first ticket in the dependency order for the Seed-mode example.
* [draft #B] consumes the accepted-request hook; this ticket owns only the hook boundary and endpoint behavior.

### Source Materials

* docs/report-export-spec.md §1

### Scope of Work

The owner may:

* Implement request validation and job-identifier creation for POST /reports/exports.
* Define the accepted-request hook stub consumed by [draft #B].
* Add endpoint tests for accepted and rejected requests.

The owner must not:

* Implement ExportRequested audit-event persistence or consumption ([draft #B]).
* Change unrelated report endpoints.
* Change the audit-event contract after [draft #B] begins consuming the hook.
* Invent semantics not in docs/report-export-spec.md §1.
* Take any action requiring human approval without asking first.

### Definition of Done

This ticket is complete when:

* Valid requests return a job identifier and invalid requests are rejected by tests.
* The accepted-request hook stub is named and callable by a test double.
* Endpoint tests pass without requiring the audit-event implementation.

### Stop Conditions

Stop and ask for input if:

* The spec does not define request validation or job-identifier behavior.
* The accepted-request hook cannot be exposed without changing a shared contract.
* The work would affect another repository or team.

### Blocking Questions

If blocked, ask only the exact question needed to continue.

* None known for this example.

#### [draft #B] Audit Trail - record export requests

## Agent Work Ticket

### Request / Outcome

* Consume the accepted-request hook from [draft #A].
* Record an ExportRequested audit event after an export request is accepted.
* Add tests proving the event is recorded once per accepted request.

### Background / Context

* Depends on [draft #A], consumed through its accepted-request hook stub.
* This ticket owns audit-event consumption and persistence, not endpoint behavior.

### Source Materials

* docs/report-export-spec.md §2
* [draft #A] Reports API - create export jobs

### Scope of Work

The owner may:

* Implement the ExportRequested audit-event consumer and persistence behavior.
* Add tests using the accepted-request hook stub from [draft #A].

The owner must not:

* Implement POST /reports/exports or request validation ([draft #A]).
* Change the accepted-request hook contract owned by [draft #A].
* Change unrelated audit-event types.
* Invent semantics not in docs/report-export-spec.md §2.
* Take any action requiring human approval without asking first.

### Definition of Done

This ticket is complete when:

* An accepted-request hook call records exactly one ExportRequested event.
* Tests pass with a stubbed hook producer; the endpoint implementation is not required.
* Rejected requests do not produce the event in the consumer tests.

### Stop Conditions

Stop and ask for input if:

* The spec does not define when an export request is accepted.
* The hook stub from [draft #A] is missing or incompatible.
* The work would change the endpoint contract or affect another repository.

### Blocking Questions

If blocked, ask only the exact question needed to continue.

* None known for this example.

**Batch approval:** Approve all, Approve subset (name the drafts), or Revise.
~~~~

Expected: the example demonstrates a coverage map, dependency order, two disjoint complete ticket bodies, a testable stub boundary, and the existing three-way approval gate. It contains no filing command.

- [ ] **Step 2: Extend the documented verification commands**

Replace the existing no-em-dash search with the escaped form rg -n $'\u2014' so the verification command does not match its own source.

After the existing gh issue list|gh issue create check in Verification, add:

~~~bash
# Onboarding sections and Skill-tool invocation are present
rg -n '^## Fits into the workflow|^## Requirements|^## Glossary|^### Worked example - Seed mode|\$create-scoped-tickets' skills/create-scoped-tickets/SKILL.md
# Expected: one or more matches for every pattern

# The old slash-command form is absent; the regex is intentionally non-literal
if rg -n '^[[:space:]]*/create-[[:lower:]-]+' skills/create-scoped-tickets/SKILL.md; then
  exit 1
else
  echo 'No slash-command invocation remains.'
fi
# Expected: no rg matches
~~~

Expected: the Verification section checks the five usability additions without reintroducing the forbidden old invocation string.

- [ ] **Step 3: Commit the worked example and checks**

~~~bash
git add skills/create-scoped-tickets/SKILL.md
git diff --cached --check
git commit -m "docs(create-scoped-tickets): add seed workflow example"
~~~

Expected: one commit modifies only skills/create-scoped-tickets/SKILL.md.

### Task 3: Run the complete documentation verification gate

**Files:**
- Inspect: skills/create-scoped-tickets/SKILL.md.
- Inspect: docs/todos/2026-07-29-create-scoped-tickets-usability.md.
- Inspect: docs/superpowers/specs/2026-08-04-create-scoped-tickets-usability-design.md.

- [ ] **Step 1: Verify Markdown whitespace and forbidden characters**

Run:

~~~bash
git diff --check
rg -n $'\u2014' skills/create-scoped-tickets/SKILL.md
~~~

Expected: git diff --check exits successfully and the em-dash search prints no output.

- [ ] **Step 2: Verify the original skill contract remains present**

Run:

~~~bash
rg -n '## Inputs|## Built-in defaults|## Workflow|### Phase 0|### Phase 1|### Phase 2|### Phase 3|### Phase 4|### Phase 5|## Author checklist|## Error handling|## Invocation|## Verification' skills/create-scoped-tickets/SKILL.md
rg -n 'gh issue list|gh issue create' skills/create-scoped-tickets/SKILL.md
rg -n 'Workflow B|Workflow C|sync_pr_status_comments|PR review scoped|status comments' skills/create-scoped-tickets/SKILL.md
~~~

Expected: the core-section and GitHub-command searches produce matches; the stale-reference search produces no output.

- [ ] **Step 3: Review the diff against the approved design**

Run:

~~~bash
git diff HEAD~2..HEAD -- skills/create-scoped-tickets/SKILL.md
git status --short
~~~

Expected: the diff is limited to the target skill, the Phase 0-5 workflow remains intact, the five selected usability findings are addressed, and no unrelated file is modified. The working tree is clean after any implementation commit.

- [ ] **Step 4: Do not create a no-op verification commit**

If all checks pass and the diff review finds no issue, leave the two implementation commits as the final implementation history. There is no code or test artifact that requires a third commit.

## Handoff

After Task 3, the skill edit is ready for the normal review or pull-request workflow. The implementation remains a documentation-only change; no GitHub issue is created by these tasks.
