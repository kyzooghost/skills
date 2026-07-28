---
name: scoped-differential-review
description: Wraps the differential-review skill to scope its findings to a set of target tickets in a GitHub issue-label universe. Use when the user says "/scoped-differential-review" or asks to run a differential review scoped to specific tickets. Classifies every finding as IN SCOPE, OWNED BY ANOTHER TICKET, or GENUINE GAP, and proposes gap tickets. Self-contained - no reference to any other scope-ticket skill.
---

# scoped-differential-review

Wraps exactly one vendor skill - `differential-review` (unmodified) - and applies self-contained ticket-scope routing to its findings. Runs a security review on a PR via `differential-review`, then classifies every finding against a scope map built from a GitHub issue-label universe: IN SCOPE (actionable against the PR), OWNED BY ANOTHER TICKET (deferred, no PR-author action), or GENUINE GAP (propose a new ticket). Generalizes single-ticket scope routing to a set of target tickets the PR implements.

This skill is self-contained. All scope-routing logic - scope inventory, A/B/C classification, gap rule, gap-ticket template - is defined here. It does not reference or depend on any other scope-ticket skill.

## Inputs

- `PR` - URL or `owner/repo#N` of the pull request under review.
- `TICKETS` - one or more target ticket numbers in the label universe that this PR implements (e.g. `4343,4380`). Comma-separated. Required; omitting `--tickets` is an error.
- `LABEL` - the issue label defining the ticket universe (e.g. `synchronous-composability-demo`).
- `REPO` - the repository containing the labeled issues. Inferred from `TICKETS` when tickets are given as full URLs; otherwise required.

## Built-in defaults (never restated by the user)

- No-duplication check against every open ticket carrying `LABEL` in `REPO`.
- Gap routing: each finding must map to a target ticket's owned scope, another open ticket's owned scope, or a proposed new ticket - never silently introduced as new PR scope.
- No-new-scope guard: a finding that fits neither a target ticket nor an existing open ticket is a gap, not a license to expand the PR.

## Scope inventory

Run:

```bash
gh issue list -R <REPO> --label <LABEL> --state open --limit 200 --json number,title,body
```

For every ticket, extract what it OWNS ("The owner may" or equivalent) and EXCLUDES ("The owner must not" / "Not In Scope" or equivalent). Produce a scope map: ticket number -> one-line ownership statement. Treat every ticket's ownership as exclusive. If work appears under another ticket's "owner may", it is out of scope here, full stop.

Recognized scope-section headings: "The owner may", "The owner must not", "Not In Scope", "Scope of Work", "Definition of Done". If a ticket uses none of these, see Error handling.

## A/B/C finding classification

Applied to every finding from `differential-review`'s report:

- **(A) IN SCOPE** - the finding touches a target ticket's owned scope. Raise as a normal review finding against the PR.
- **(B) OWNED BY ANOTHER TICKET** - the finding touches an area owned by a different open ticket in the scope map. Do NOT raise as an actionable finding against the PR. The only valid comment is "this belongs to #N; revert/stub it here."
- **(C) GENUINE GAP** - the finding touches an area no open ticket owns. Do NOT ask the PR author to fix it. Handle per the Gap rule.
- **Uncertain mapping** - if you cannot map a finding to a scope-map entry with confidence, default to (C) GENUINE GAP and flag the uncertainty in the Scope Routing section. The batch-approval gate for gap tickets lets the user filter noise; do not interrupt the run to ask per-finding.

Stubs, interfaces, TODOs, and hardcoded placeholders standing in for other tickets' unimplemented work are CORRECT by design - only verify the stub matches the agreed interface; do not raise them as findings.

## Gap rule

Draft each category-C finding as a new ticket using the self-contained template below. Present drafts under "Proposed new tickets". Request one batch approval to file all of them via `gh issue create -R <REPO> --label <LABEL> -t "<title>" -b "<body>"`. Do not file unless approved. Capture the real number/URL of each filed ticket and substitute it back into the Scope Routing section.

## Self-contained gap-ticket template

```markdown
Title: <Area> - <Concrete outcome>

## Finding
<What the review found: defect, file/line, severity, why it matters.>

## Proposed Scope
The owner may:
* <Allowed work, traced to the finding.>

The owner must not:
* <Out-of-scope item> (ticket #N)
* <Out-of-scope item> (ticket #M)
* <Change shared interfaces owned elsewhere>

## Acceptance Criteria
This ticket is complete when:
* <Verifiable checks only: tests, invariants, docs.>
```
