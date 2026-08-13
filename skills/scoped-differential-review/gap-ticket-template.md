# Gap Ticket Template

Use this template when drafting new tickets for (C) GENUINE GAP findings.

## Template

    Title: <Area> - <Concrete outcome>

    ## Finding

    <What the review found: defect, file/line, severity, why it matters.>

    ## Proposed Scope

    The owner may:
    * <Allowed work, traced to the finding.>

    The owner must not:
    * <Out-of-scope item> (ticket #N)
    * <Change shared interfaces owned elsewhere>

    ## Acceptance Criteria

    This ticket is complete when:
    * <Verifiable checks only: tests, invariants, docs.>

## Filing

File approved gap tickets via:

    gh issue create -R <REPO> --label <LABEL> -t "<title>" -b "<body>"

Cite adjacent ticket numbers from the scope map in the "owner must not" list so boundaries are unambiguous.

For richer ticket structure (background, dependencies, stop conditions), see the `create-scoped-tickets` skill.
