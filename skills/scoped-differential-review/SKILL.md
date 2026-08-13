---
name: scoped-differential-review
description: Wraps a vendored differential-review skill and routes its findings against a GitHub issue-label universe. Classifies each finding as IN SCOPE, OWNED BY ANOTHER TICKET, or GENUINE GAP. Proposes gap tickets for unowned findings. Use when running a scope-bounded security review of a PR.
---

# Scoped Differential Review

Runs a vendored security review skill on a PR, then classifies every finding against a scope map built from a GitHub issue-label universe. Findings route to target tickets, defer to other tickets, or become proposed gap tickets.

## Prerequisites

- `gh` CLI authenticated with read/write access to the target repository's issues.

## Inputs

- `PR` - URL or `owner/repo#N` of the pull request under review.
- `--tickets` - one or more target ticket numbers this PR implements (comma-separated, e.g. `42,43`). Required.
- `--label` - the issue label defining the ticket universe (e.g. `my-feature`). Required.
- `--repo` - the repository containing the labeled issues. Inferred from `PR` when possible; required otherwise.

## Workflow

Five phases. Phases 1-2 prepare the scope map, phase 3 delegates to the vendored review skill, phases 4-5 route findings and handle gaps.

### Phase 1 - Parse inputs and build scope map

1. Parse `PR`, `--tickets`, `--label`, `--repo`.
2. Fetch all open tickets in the label universe:

       gh issue list -R <REPO> --label <LABEL> --state open --limit 200 --json number,title,body

3. For every ticket, comprehend the full body and extract what it OWNS and what it EXCLUDES. Use any available signal: headings, acceptance criteria, task lists, descriptions, "out of scope" language, title. See [scope-routing.md](scope-routing.md) for the full extraction and classification rules.
4. Build the scope map: ticket number -> OWNS / EXCLUDES.
5. If a ticket is too vague to extract any ownership, mark it "unparseable" in the scope map. Continue with the rest.

### Phase 2 - Validate target tickets

1. For each ticket in `--tickets`, fetch via `gh issue view <N> -R <REPO>`.
2. Confirm it is OPEN and carries `--label`. Stop if any target is closed, missing, or unlabeled.
3. Confirm at least one target ticket has a parseable ownership boundary. If all are unparseable, stop and report the error.

### Phase 3 - Run differential-review

1. Read and follow `vendor/differential-review/skills/differential-review/SKILL.md`. The vendored skill runs its own methodology unmodified and produces a findings report.
2. The adversarial modeler agent definition is at `vendor/differential-review/agents/adversarial-modeler.md`. Reference it for high-risk findings as the vendor skill directs.
3. Do not alter the vendor skill's methodology, risk classification, or report structure.

### Phase 4 - Route findings by scope

For every finding in the vendor's report, apply the A/B/C classification from [scope-routing.md](scope-routing.md):

1. Map the finding to a scope-map entry. Cite the ticket number and ownership statement used.
2. Classify as (A) IN SCOPE, (B) OWNED BY ANOTHER TICKET, or (C) GENUINE GAP.
3. Stubs and TODOs standing in for other tickets' work are correct by design. Verify the stub matches the interface; do not raise as findings.

### Phase 5 - Emit report and handle gaps

1. Emit the vendor's full report unchanged, including its verdict.
2. Append a `## Scope Routing` section containing:
   - **Scope Map** - the extracted scope map for auditability.
   - **Scope-adjusted verdict** - computed per the reconciliation rules in [scope-routing.md](scope-routing.md).
   - **In-scope findings (A)** - each with target-ticket assignment, severity, file/line.
   - **Deferred - owned by other tickets (B)** - one-liners with ticket numbers.
   - **Scope violations** - PR work belonging to other tickets or no ticket.
   - **Proposed new tickets (C)** - full drafted ticket bodies using [gap-ticket-template.md](gap-ticket-template.md), or "No gaps found."
3. If gap tickets are proposed, request one batch approval. On approval, file each via `gh issue create -R <REPO> --label <LABEL> -t "<title>" -b "<body>"`, capture real numbers, substitute back into the report. On decline, leave drafts unfiled.

## Invocation

```
/scoped-differential-review <PR-URL> --tickets 42,43 --label my-feature --repo org/project
```

`--repo` is optional when inferable from the PR URL. All scope-routing guarantees (no-duplication, no-new-scope, gap routing) are built-in defaults.

## Error handling

- `--tickets` omitted -> stop, ask for target tickets.
- Target ticket not in label universe -> stop, report which ticket, ask to confirm.
- Empty label universe (zero open tickets with `--label`) -> stop, ask to confirm the label.
- All target tickets unparseable -> stop, report the error.
- `differential-review` errors or emits no report -> stop, surface the error.
- `gh issue create` fails mid-batch -> report error, stop. Already-filed tickets remain; report their numbers.

## Mutations

The skill's only GitHub mutation is `gh issue create` for approved gap tickets. It never posts PR comments, edits existing issues, changes labels, or closes issues.
