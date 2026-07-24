---
name: scoped-tickets
description: Use when creating a scope-bounded ticket in a GitHub issue-label collection, reviewing a PR against one ticket's scope, checking linked PR status coverage, synchronizing missing PR status comments, or handling Agent Work Tickets and ticket scope creep.
---

# Scoped Tickets

Three workflows operate over a collection of GitHub issues sharing one label:

1. **Create a new ticket** in the collection (Agent Work Ticket format).
2. **Review a PR** against exactly one ticket's scope.
3. **Synchronize linked PR status comments** across an issue repository and a PR repository.

Workflows A and B use exclusive, non-overlapping ticket scope and share Step 0. They classify every
out-of-scope observation as either "owned by another ticket" or
"genuine gap -> propose new ticket". Workflow C audits or adds issue comments only and does not use
the scope map or Gap rule.

## Inputs

Workflows A and B require:

- `REPO` - GitHub repository containing the ticket collection, e.g. `org/project`
- `ISSUE_TAG` - label defining the ticket universe, e.g. `synchronous-composability-demo`

Workflow-specific:

- Ticket creation: `SCOPE_STATEMENT` - one sentence stating exactly what the new ticket covers
- PR review: `PR` (number/URL) and `TICKET` (issue number the PR implements)
- PR status comments:
  - `ISSUE_REPO` - repository containing the labeled issues and receiving comments
  - `PR_REPO` - base repository containing the linked PRs

`ISSUE_REPO` and `PR_REPO` may be the same repository.

## Step 0 - Scope inventory (mandatory for Workflows A and B)

Run:

```bash
gh issue list -R <REPO> --label <ISSUE_TAG> --state open --limit 200 --json number,title,body
```

For every ticket, extract from "Scope of Work" what it OWNS ("The owner may") and what it EXCLUDES ("The owner must not"). Some tickets may use a "Not In Scope" heading instead; treat it the same. Produce a scope map: ticket number -> one-line ownership statement.

Treat every ticket's ownership as exclusive. If work appears under another ticket's "The owner may", it is out of scope here, full stop.

## Workflow A - Creating a new ticket

The new ticket covers exactly `SCOPE_STATEMENT` and nothing more.

Scoping rules:

- Every bullet under "The owner may" must trace to `SCOPE_STATEMENT`. If it cannot be traced, delete it.
- **"The owner must not" is the most important section.** Build it from the Step 0 scope map: explicitly name each ticket in the `ISSUE_TAG` universe whose scope borders this one, by issue number, so every boundary is unambiguous.
- Where this ticket depends on work owned by another unimplemented ticket, do NOT pull that work in. Specify the stub or interface to code against (name the interface and the owning ticket) and record the dependency in Background / Context.
- Definition of Done must be verifiable without any other ticket's unimplemented work (tests may use the stubs).

Write the ticket using the template below (Agent Work Ticket format).

### Ticket template

Title: `<Area> - <Concrete outcome>` (e.g. `Besu Sidecar - Builder 2PC: collapse lock-gap-lock pattern`)

Do NOT include Status, Status Flow, Required Receipt, or Due Date in the body. Status is tracked via labels/project; receipt via PRs opened.

```markdown
## Agent Work Ticket

### Request / Outcome

What needs to happen?

* <Bullet the outcomes, not a vague theme. Concrete verbs + named components.>

### Background / Context

Relevant context the owner needs to understand the task.

* <Why this exists: prior PRs, reviews, design constraints.>
* <Dependencies on other tickets: "Depends on #N (consumed via <interface/stub>); blocked by #M landing first.">

### Source Materials

Attach or link the materials needed to complete the task.

* <Specs, PRs, commits, adjacent tickets. Prefer repo-relative paths, e.g. docs/spec.md §3.7.>

### Scope of Work

The owner may:

* <Allowed work. Every bullet traces to the Request / Outcome.>

The owner must not:

* <Out-of-scope work item> (ticket #N)
* <Out-of-scope work item> (ticket #M)
* <Change shared interfaces/contracts owned elsewhere>
* <Invent semantics not in the spec/source materials>
* Take any action requiring human approval without asking first

### Definition of Done

This ticket is complete when:

* <Verifiable checks only: tests, invariants, docs. If it cannot be checked, it is not DoD.>

### Stop Conditions

Stop and ask for input if:

* Ambiguity or missing information in the spec or interfaces
* A decision requires product/protocol judgment
* An action would affect another team or repo
* There is risk of overstepping the ticket scope

### Blocking Questions

If blocked, ask only the exact question needed to continue.

* <Pre-seed only if already known; otherwise leave empty.>
```

Author checklist before finalizing:

- [ ] Outcome is specific enough to implement without guessing product intent
- [ ] Sources are linked and sufficient to start
- [ ] May / must-not bounds every adjacent ticket in the `ISSUE_TAG` universe by number
- [ ] DoD is testable without other tickets' unimplemented work
- [ ] Stop conditions cover the real judgment calls

### Output (Workflow A)

1. The new ticket body, ready to paste.
2. The Step 0 scope map (so boundary decisions can be audited).
3. "Proposed new tickets" section per the Gap rule below, or "No gaps found".

Do not create the issue on GitHub unless explicitly asked; output text only.

## Workflow B - PR review scoped to a ticket

Fetch the scope contract:

```bash
gh issue view <TICKET> -R <REPO>
```

The ticket's sections are the review contract:

- "The owner may" = the only things evaluated for correctness/completeness.
- "The owner must not" = things whose ABSENCE is correct. Never ask for them.
- "Definition of Done" = the acceptance bar. Review against it, nothing more.

Classify EVERY finding before raising it:

- **(A) IN SCOPE** - within "The owner may" or violates the DoD. Raise as a normal review comment.
- **(B) OWNED BY ANOTHER TICKET** - covered by a different ticket in the Step 0 scope map. Do NOT raise as a finding. If the PR touches that area, the only valid comment is "this belongs to #N; revert/stub it here".
- **(C) GENUINE GAP** - real concern, but no ticket owns it. Do NOT ask the author to fix it. Handle per the Gap rule below.

Rules:

- Stubs, interfaces, TODOs, and hardcoded placeholders standing in for other tickets' unimplemented work are CORRECT by design. Only check the stub matches the agreed interface.
- Never comment "you should also handle/implement X" when X is another ticket's scope. Cite the ticket number instead.
- Missing tests are findings only if the ticket's DoD requires them.
- It IS in scope to flag when the PR itself exceeds the ticket (implements another ticket's work) - that is a scope violation by the PR.

### Output (Workflow B)

1. Verdict against the ticket's Definition of Done (met / not met, per item).
2. In-scope findings (category A), each with file/line references.
3. Scope violations by the PR (work belonging to other tickets, with #N).
4. "Deferred - owned by other tickets": one-liners with ticket numbers, no action requested from the author.
5. "Proposed new tickets" (category C), or "No gaps found".

## Workflow C - Synchronize linked PR status comments

Inventory both open and closed issues in `ISSUE_REPO` carrying `ISSUE_TAG`. Discover relationships
only from `CrossReferencedEvent.source` and `ConnectedEvent.subject`, and retain only PRs whose base
repository is exactly `PR_REPO`.

Eligible statuses are:

- `open` - the PR is open; drafts remain `open`
- `merged` - `mergedAt` is non-null

Ignore closed-unmerged PRs. Do not infer relationships from titles, authors, branches, labels,
changed files, or textual similarity.

An existing comment covers one PR/current-status pair only when one line unambiguously identifies the
PR by full URL, `PR_REPO#N`, or same-repository `PR #N`, and states the current status. An earlier
`open` comment does not cover a PR after it merges.

Run the deterministic helper:

```bash
python3 skills/scoped-tickets/scripts/sync_pr_status_comments.py \
  --issue-repo "$ISSUE_REPO" \
  --pr-repo "$PR_REPO" \
  --issue-tag "$ISSUE_TAG"
```

The command defaults to dry-run. Add `--apply` only when the user explicitly asks to add, write,
post, or synchronize missing comments. Requests to inspect, audit, check, or report remain dry-run.

Apply mode re-fetches the label, comments, timeline relationships, and PR states before each post.
It may add issue comments only. It must never edit or delete comments, change issue or PR metadata,
comment on PRs, comment about PRs outside `PR_REPO`, or comment about closed-unmerged PRs.

When multiple eligible PRs are missing coverage on one issue, post one comment:

```markdown
For visibility, this issue has linked PR activity:

- https://github.com/pr-owner/pr-repo/pull/17 - open
- https://github.com/pr-owner/pr-repo/pull/18 - merged
```

After apply mode, require fresh verification that every eligible issue/PR/current-status pair is
covered. Report every uncovered pair and return failure.

### Output (Workflow C)

Report labeled issues inspected, linked PR relationships, eligible `open` and `merged` counts,
already-covered pairs, ignored closed-unmerged PRs, comments planned or posted by issue, and
verification failures.

## Gap rule (Workflows A and B)

If work is required by the overall effort but owned by NO ticket in the `ISSUE_TAG` universe (including the ticket being created/reviewed):

- Do not fold it into the current ticket or ask the PR author for it.
- Draft each gap as a full new ticket using the template above, including its own "The owner must not" list citing existing ticket numbers.
- Present the drafts under a "Proposed new tickets" heading; do not file them unless explicitly asked.
