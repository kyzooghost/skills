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

## Workflow

The skill runs in five phases. Phases 1-2 are preparation, phase 3 delegates to `differential-review`, phases 4-5 apply scope routing and gap handling.

### Phase 1 - Parse inputs and build scope map

1. Parse `PR`, `TICKETS` (comma-separated, one or more), `LABEL`, `REPO` (infer from ticket URLs if absent).
2. Run the scope inventory: `gh issue list -R <REPO> --label <LABEL> --state open --limit 200 --json number,title,body`.
3. For every open ticket, extract OWNED and EXCLUDED. Build the scope map: ticket number -> one-line ownership statement.
4. Fetch each target ticket in `TICKETS` via `gh issue view <N> -R <REPO>` and confirm it is OPEN and carries `LABEL`. Error and stop if a target ticket is closed, missing, or not in the label universe. A closed target ticket is not in the open universe and therefore cannot be a scope owner for this review.

### Phase 2 - Validate target-ticket scope coverage

1. For each target ticket, confirm its owned scope is non-empty and parseable. If a target ticket has no recognizable "owner may" section, stop and ask the user for the scope statement - do not guess.
2. Mark the union of target tickets' owned scope as the in-scope region for this review.

### Phase 3 - Run differential-review

1. Invoke the `differential-review` skill on `PR` exactly as documented (vendor skill, unmodified). It runs its own phases 0-6 and produces its standard markdown report.
2. Do not alter `differential-review`'s methodology, risk classification, or report structure. Treat `differential-review` as a black box that emits a findings report.

### Phase 4 - Route findings by scope

For every finding in `differential-review`'s report:

1. Map the finding's affected code/area to a scope-map entry. Cite the scope-map line (ticket number and its one-line ownership statement) used for each classification so the routing is auditable.
2. Classify:
   - **(A) IN SCOPE** - the finding touches a target ticket's owned scope. Keep it as an actionable finding against the PR.
   - **(B) OWNED BY ANOTHER TICKET** - the finding touches an area owned by a different open ticket in the scope map. Mark deferred; no action requested from the PR author. If the PR implements that area, flag it as a scope violation by the PR ("this belongs to #N; revert/stub it here").
   - **(C) GENUINE GAP** - the finding touches an area no open ticket owns. Do not ask the PR author to fix it. Draft a gap ticket.
   - **Uncertain mapping** - default to (C) GENUINE GAP and flag the uncertainty in the Scope Routing section.
3. Stubs, interfaces, TODOs, and hardcoded placeholders standing in for other tickets' unimplemented work are CORRECT by design - only verify the stub matches the agreed interface; do not raise them as findings.

### Phase 5 - Emit report and handle gaps

1. Emit `differential-review`'s full report unchanged, including its overall verdict (APPROVE/REJECT/CONDITIONAL).
2. Append a `## Scope Routing` section containing:
   - **Scope-adjusted verdict:** the skill's own verdict, computed per the Recommendation reconciliation rule below.
   - **In-scope findings (A):** each with its target-ticket assignment, severity, and file/line refs.
   - **Deferred - owned by other tickets (B):** one-liners with ticket numbers, no action requested.
   - **Scope violations by the PR:** PR work belonging to other tickets, with `#N`.
   - **Proposed new tickets (C):** full drafted ticket bodies using the self-contained template, or "No gaps found".
3. If there are proposed gap tickets, show all drafts and request one batch approval to file them. On approval, run `gh issue create -R <REPO> --label <LABEL> -t "<title>" -b "<body>"` for each, capture the real number/URL, and substitute it back into the Scope Routing section. On decline, leave the drafts in the report unfiled.
4. Never post PR comments, edit the PR, or mutate issues other than the approved gap-ticket creation. The skill's only mutations are gap-ticket creation after batch approval.

## Recommendation reconciliation

`differential-review` emits an overall verdict (APPROVE/REJECT/CONDITIONAL). The skill preserves that verdict verbatim in the report and additionally emits a **scope-adjusted verdict** at the top of the Scope Routing section. The scope-adjusted verdict is computed as follows:

- Let *blocking* = findings the vendor classified as CRITICAL or HIGH.
- Let *blocking-in-scope* = blocking findings classified here as (A) IN SCOPE.
- Let *blocking-deferred* = blocking findings classified here as (B) OWNED BY ANOTHER TICKET or as a PR-scope violation to revert.
- The scope-adjusted verdict is:
  - **APPROVE** when *blocking-in-scope* is empty and there are no PR-scope violations requiring revert.
  - **CONDITIONAL** when *blocking-in-scope* is non-empty but no single in-scope finding is CRITICAL, OR when in-scope findings require fixes that can land in this PR.
  - **REJECT** when any in-scope finding is CRITICAL, or when the PR contains unscoped work that must be reverted and the revert is non-trivial.

The scope-adjusted verdict is the actionable verdict for the PR author and reviewer. The vendor's preserved verdict remains the security authority of record; it is never softened or hidden. When the two verdicts differ, the Scope Routing section states both explicitly, e.g. "Vendor verdict: REJECT. Scope-adjusted verdict: APPROVE - all blocking findings deferred to #4350, #4351; no in-scope blocking findings remain."

Rationale: the skill's purpose is to make scope routing actionable. A bare vendor REJECT that ignores scope would defeat that purpose. Preserving the vendor verdict verbatim ensures the security authority is never masked, while the scope-adjusted verdict gives the PR author and reviewer a verdict they can act on without violating scope.
