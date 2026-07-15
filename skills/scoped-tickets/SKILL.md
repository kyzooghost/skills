---
name: scoped-tickets
description: Create scope-bounded Agent Work Tickets and run ticket-scoped PR reviews for a GitHub issue label collection. Keeps new tickets and PR reviews inside one ticket's scope, defers adjacent work to the owning ticket, and proposes new tickets for genuine gaps. Use when creating a ticket in a labeled collection, reviewing a PR that implements a ticket, or when the user mentions scoped tickets, Agent Work Ticket, ticket scope creep, or an issue-label ticket universe.
---

# Scoped Tickets

Two workflows over a collection of GitHub issues sharing one label, where tickets have distinct, non-overlapping scope and cross-ticket dependencies are consumed via stubs/interfaces:

1. **Create a new ticket** in the collection (Agent Work Ticket format).
2. **Review a PR** against exactly one ticket's scope.

Both share Step 0 (scope inventory). Both must classify every out-of-scope observation as either "owned by another ticket" or "genuine gap -> propose new ticket".

## Inputs

Required (ask if not provided):

- `REPO` - GitHub repo, e.g. `org/project`
- `ISSUE_TAG` - the label defining the ticket universe, e.g. `synchronous-composability-demo`

Workflow-specific:

- Ticket creation: `SCOPE_STATEMENT` - one sentence stating exactly what the new ticket covers
- PR review: `PR` (number/URL) and `TICKET` (issue number the PR implements)

## Step 0 - Scope inventory (mandatory for both workflows)

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

## Gap rule (both workflows)

If work is required by the overall effort but owned by NO ticket in the `ISSUE_TAG` universe (including the ticket being created/reviewed):

- Do not fold it into the current ticket or ask the PR author for it.
- Draft each gap as a full new ticket using the template above, including its own "The owner must not" list citing existing ticket numbers.
- Present the drafts under a "Proposed new tickets" heading; do not file them unless explicitly asked.
