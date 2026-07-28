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

## Error handling and edge cases

### Input errors

- A target ticket is not in the `LABEL` universe -> stop, report which ticket, ask the user to confirm the label or the ticket number.
- `REPO` cannot be inferred and was not supplied -> stop, ask for `REPO`.
- `gh issue list` returns zero open tickets carrying `LABEL` -> stop, ask the user to confirm the label; an empty universe means scope routing has no boundary to enforce.
- A target ticket has no recognizable "owner may" / scope section -> stop, ask the user for the scope statement. Never infer scope from a ticket title alone.
- `--tickets` omitted -> stop, ask for `--tickets`. Target tickets are explicit; the skill does not infer them from PR links.

### Scope-map ambiguity

- A finding touches an area that two target tickets both appear to own -> treat as IN SCOPE (A) but flag the overlap in the Scope Routing section with both ticket numbers, so the user can resolve the boundary. Do not silently pick one.
- A finding touches an area owned by a target ticket AND another open ticket -> IN SCOPE (A) for the target ticket; note the adjacent ownership in the deferred section for visibility.
- The scope map cannot be built because tickets use non-standard headings -> stop, report which tickets are unparseable, ask the user to confirm the heading convention or supply scope statements.

### Gap-ticket creation

- Batch approval declined -> leave drafts in the report, unfiled. Do not file a subset without re-confirmation.
- `gh issue create` fails for one ticket in the batch -> report the error, stop, do not file the remaining tickets, do not post a partial result. Already-filed tickets in the batch remain filed; report their numbers.
- A drafted gap ticket's "owner must not" list cannot cite adjacent tickets because the scope map is empty -> file with an empty "owner must not" list and flag the gap in the report.
- A gap finding duplicates an existing open ticket the scope map missed (e.g. a ticket without the label) -> do not file; note in the report that the finding may be covered by `<URL>` and ask the user to confirm.

### PR-scope violations

- The PR implements work owned by another open ticket -> flag as a scope violation (category B variant). Do not ask the PR author to complete that work; the only valid recommendation is "revert/stub the work belonging to #N."
- The PR implements work owned by NO ticket -> flag as a scope violation with no ticket to cite. Treat as a category-C gap AND a PR-scope violation; propose a gap ticket and recommend reverting the unscoped work from the PR.
- The PR implements none of the target tickets' scope -> report "PR does not implement any target ticket's scope" at the top of the Scope Routing section; route findings as (B) or (C) accordingly.

### differential-review failures

- `differential-review` errors or emits no report -> stop, surface the vendor skill's error, do not produce a Scope Routing section (there is nothing to route).

### No mutations beyond gap tickets

- The skill never posts PR review comments, edits the PR, changes labels on existing issues, or closes issues. The only GitHub mutation is `gh issue create` for approved gap tickets.

## Invocation

```
/scoped-differential-review <PR-URL> --tickets 4380,4343 --label synchronous-composability-demo --repo Consensys/zkevm-monorepo
```

`--repo` is optional when tickets are given as full URLs (inferred). All of the following from the original verbose prompt become built-in defaults, never restated:

- "ensuring that review scope remains within #4380 and #4343" -> `--tickets 4380,4343`
- "does not duplicate scope for other open tickets in repo:... label:..." -> `--label` + built-in no-duplication default
- "For new findings, carefully consider whether they should be covered in #4343 or #4380 scope, or another available open ticket, or we should create a whole new ticket" -> built-in A/B/C classification + gap rule
- "Please be careful not to introduce entirely new scope for this PR with your review findings" -> built-in no-new-scope guard

## Verification

Since this is a Markdown skill wrapping a vendor skill, verification is static checks plus scenario exercises against this SKILL.md.

### Static checks

```bash
# Self-check: this file must not reference the sibling scope-ticket skill
rg -n 'scoped[-_]tickets' skills/scoped-differential-review/SKILL.md
# Expected: no output

# differential-review is referenced as the wrapped skill
rg -n 'differential-review' skills/scoped-differential-review/SKILL.md
# Expected: matches in the wrapper description and Phase 3

# Self-contained scope-routing concepts are all defined
rg -n 'Scope inventory|IN SCOPE|OWNED BY ANOTHER TICKET|GENUINE GAP|Gap rule|Proposed new tickets' skills/scoped-differential-review/SKILL.md
# Expected: matches in workflow and classification sections

# No em-dash (per workspace rule)
rg -n $'\u2014' skills/scoped-differential-review/SKILL.md
# Expected: no output
```

### Scenario exercises

1. **Single target ticket, all findings in scope** - PR implements `#4343`; every `differential-review` finding touches `#4343`'s owned scope. Output: full report + Scope Routing with all findings as (A), no deferred, no gaps, no mutations.
2. **Multi target tickets, findings split across them** - PR implements `#4343` and `#4380`; findings split between both owned scopes. Output: each finding assigned to its target ticket; no duplication; no gaps.
3. **Finding owned by another open ticket** - A finding touches an area owned by `#4350` (not a target). Output: finding marked (B), deferred with `#4350`, no action requested from the PR author.
4. **PR implements another ticket's work** - The PR contains code that implements `#4350`'s scope. Output: scope violation flagged - "revert/stub the work belonging to #4350." No request to complete it.
5. **Genuine gap, batch approval granted** - A finding touches an area no open ticket owns. Output: gap ticket drafted using the self-contained template with adjacent tickets cited in "owner must not." User approves the batch. Skill runs `gh issue create` for each, captures real numbers, substitutes them into the Scope Routing section.
6. **Genuine gap, batch approval declined** - Same as (5) but user declines. Output: drafts remain in the report unfiled; no `gh issue create` calls; no partial filing.
7. **`gh issue create` fails mid-batch** - Two gap tickets approved; the first files successfully, the second errors. Output: report the error, stop, do not file remaining, report the first ticket's real number, leave the second as a draft.
8. **Empty label universe** - `gh issue list --label <LABEL>` returns zero tickets. Output: stop, ask the user to confirm the label.
9. **Target ticket not in the label universe** - `#4343` does not carry `LABEL`. Output: stop, report which ticket, ask the user to confirm.
10. **Target ticket has no parseable scope section** - `#4343` has no "owner may" / equivalent. Output: stop, ask the user for the scope statement; do not guess.
11. **Two target tickets both appear to own the same area** - Finding overlaps `#4343` and `#4380`. Output: treat as (A) IN SCOPE, flag the overlap with both ticket numbers in the Scope Routing section, ask the user to resolve the boundary.
12. **differential-review emits no report** - The vendor skill errors. Output: surface the error, do not produce a Scope Routing section.
13. **Vendor verdict conflicts with scope-adjusted verdict** - Vendor says REJECT due to two CRITICAL findings; both are classified (B) OWNED BY ANOTHER TICKET. Output: preserve vendor verdict "REJECT" verbatim in the report; emit scope-adjusted verdict "APPROVE - all blocking findings deferred to #N, #M; no in-scope blocking findings remain" at the top of the Scope Routing section; state both explicitly.
