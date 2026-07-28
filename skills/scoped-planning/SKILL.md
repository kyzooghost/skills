---
name: scoped-planning
description: Per-stage scope-check overlay across the planning lifecycle. Wraps brainstorming, grill-plan, and writing-plans as black boxes and applies post-hoc scope guardrails at each stage's natural checkpoint against a scope map built from a GitHub issue-label universe. Use when the user says "/scoped-planning" or asks to scope a planning stage to specific tickets. Classifies every overscoped artifact point as IN SCOPE, OWNED BY ANOTHER TICKET, or GENUINE GAP, and proposes gap tickets. Self-contained - no reference to any other scope-ticket skill.
---

# scoped-planning

A per-stage scope-check overlay across the planning lifecycle (`/brainstorming` -> `/grill-plan` -> `/writing-plans`). Each stage is invoked separately as `scoped-planning /<wrapped-skill>`, wrapping that stage's base skill as a black box. The wrapped skill runs to its natural checkpoint (brainstorming's user-review gate, grill-plan's handoff, writing-plans' execution-handoff); scope-check guardrails are then applied post-hoc, before the artifact is handed off. The deliverable is the wrapped skill's normal output (spec / grilled plan / task plan), kept scope-clean - not a separate verdict report.

This skill is self-contained. All scope-routing logic - scope inventory, IN/OWNED/GAP classification, gap rule, gap-ticket template - is defined here. It does not reference or depend on any other scope-ticket skill.

## Inputs

- `--tickets <N,M,...>` - one or more target ticket numbers in the label universe that this planning effort implements (e.g. `4343,4380`). Comma-separated. Required; omitting `--tickets` is an error except in bootstrap mode.
- `--label <label>` - the issue label defining the ticket universe. Default: `agent-work-ticket`.
- `<wrapped-skill>` - the base skill to wrap: one of `/brainstorming`, `/grill-plan`, `/writing-plans`. This token selects the overlay mode; no separate `--mode` flag.
- The wrapped skill's own inputs (idea/spec, plan draft, etc.) are passed through unchanged.

`--repo` is required when `--tickets` are bare numbers; inferred from the git remote otherwise.

## Built-in defaults (never restated by the user)

- No-duplication check against every open ticket carrying `--label` in the repo.
- Gap routing: every overscoped artifact point must map to a target ticket's owned scope, another open ticket's owned scope, or a proposed new ticket - never silently introduced as new scope.
- No-new-scope guard: an artifact point that fits neither a target ticket nor an existing open ticket is a gap, not a license to expand the plan.
- Post-hoc guardrails: the wrapped skill runs uninterrupted to its natural checkpoint; scope-checks apply after, before handoff.

## Scope inventory

Run:

```bash
gh issue list -R <REPO> --label <LABEL> --state open --limit 200 --json number,title,body
```

For every ticket, extract what it OWNS ("The owner may" / "Scope of Work" or equivalent) and EXCLUDES ("The owner must not" / "Not In Scope" or equivalent). Produce a scope map: ticket number -> one-line ownership statement. Treat every ticket's ownership as exclusive. If work appears under another ticket's "owner may", it is out of scope here, full stop.

The authoritative set of recognized scope-section headings is: "The owner may", "The owner must not", "Not In Scope", "Scope of Work", "Definition of Done". If a ticket uses none of these, see Error handling.

## IN/OWNED/GAP classification

Applied to every overscoped point of the wrapped skill's artifact (a spec section, an unresolved decision, a task line) at the stage's natural checkpoint:

- **IN SCOPE** - the point touches the union of the target tickets' owned scope. Silent pass; emit the artifact as the base skill would.
- **OWNED BY ANOTHER TICKET** - the point touches an area owned by a different open ticket in the scope map. Flag inline at the point of collision; name the owning ticket. Ask the user to narrow the artifact, reassign, or explicitly accept the cross-ticket work before handoff.
- **GENUINE GAP** - the point touches an area no open ticket owns. Flag inline at the unowned work. **Stop and ask**: (i) create a gap ticket now (embedded template) or (ii) narrow the artifact to drop the gap.
- **Uncertain mapping** - if you cannot map a point to a scope-map entry with confidence, default to GENUINE GAP and flag the uncertainty inline. The approval gate for gap tickets lets the user filter noise; do not interrupt the stage to ask per-point.

Stubs, interfaces, TODOs, and hardcoded placeholders standing in for other tickets' unimplemented work are CORRECT by design - only verify the stub matches the agreed interface; do not flag them as overscope.

## Gap rule

Draft each GENUINE GAP as a new ticket using the self-contained Agent Work Ticket template below. Present drafts under "Proposed new tickets". Request approval to file each via `gh issue create -R <REPO> --label <LABEL> -t "<title>" -b "<body>"`. Do not file unless approved. Capture the real number/URL of each filed ticket and surface it back to the user.

## Self-contained gap-ticket template

Title: `<Area> - <Concrete outcome>`. Do NOT include Status, Status Flow, Required Receipt, or Due Date in the body.

```markdown
## Agent Work Ticket

### Request / Outcome

What needs to happen?

* <Concrete outcomes, not a vague theme. Concrete verbs + named components.>

### Background / Context

* <Why this exists: prior PRs, reviews, design constraints.>
* <Dependencies on other tickets: "Depends on #N (consumed via <interface/stub>); blocked by #M landing first.">

### Source Materials

* <Specs, PRs, commits, adjacent tickets. Prefer repo-relative paths.>

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

* <Verifiable checks only: tests, invariants, docs.>

### Stop Conditions

Stop and ask for input if:

* Ambiguity or missing information in the spec or interfaces
* A decision requires product/protocol judgment
* An action would affect another team or repo
* There is risk of overstepping the ticket scope

### Blocking Questions

* <Pre-seed only if already known; otherwise leave empty.>
```

The "owner must not" list cites adjacent ticket numbers from the scope map so every boundary is unambiguous.
