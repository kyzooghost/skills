# Scope Routing

Classification logic for routing `differential-review` findings against a ticket-scope map.

## Heuristic scope parsing

For every ticket in the label universe:

1. Read the full ticket body.
2. Extract two lists:
   - **OWNED**: work this ticket is responsible for delivering.
   - **EXCLUDED**: work explicitly out of scope for this ticket.
3. Infer from any available signal: acceptance criteria, task lists, headings, "out of scope" language, description, title.
4. If a ticket is too vague to extract any ownership boundary, mark as "unparseable" in the scope map. Note in the report. Continue with remaining tickets.
5. If ALL target tickets are unparseable, stop and report the error. At least one target ticket must have a parseable ownership boundary to route findings against.

## Scope map display

After extraction, emit the scope map in the report without pausing for confirmation:

    ## Scope Map
    - #42: OWNS "payment retry logic for idempotent endpoints"
           EXCLUDES "webhook delivery (owned by #43)"
    - #43: OWNS "webhook delivery and DLQ"
           EXCLUDES "retry logic (owned by #42)"

## A/B/C finding classification

Applied to every finding from the vendor's report:

- **(A) IN SCOPE** - the finding touches a target ticket's owned scope. Raise as a normal review finding against the PR.
- **(B) OWNED BY ANOTHER TICKET** - the finding touches another open ticket's owned scope. Do not raise against the PR. Only valid comment: "this belongs to #N; revert/stub it here."
- **(C) GENUINE GAP** - no ticket owns the affected area. Draft a gap ticket per the template in [gap-ticket-template.md](gap-ticket-template.md).
- **Uncertain mapping** - default to (C) GENUINE GAP. Flag uncertainty in the Scope Routing section.

Stubs, interfaces, TODOs, and hardcoded placeholders standing in for other tickets' unimplemented work are correct by design. Verify the stub matches the agreed interface; do not raise as findings.

## Gap rule

Draft each (C) finding as a new ticket using the template in [gap-ticket-template.md](gap-ticket-template.md). Present all drafts under "Proposed new tickets" in the report. Request one batch approval to file them via `gh issue create -R <REPO> --label <LABEL> -t "<title>" -b "<body>"`. Do not file unless approved. Capture the real number/URL of each filed ticket and substitute it back into the Scope Routing section.

## Recommendation reconciliation

The vendor skill emits a verdict (APPROVE/REJECT/CONDITIONAL). Preserve it verbatim. Additionally emit a **scope-adjusted verdict**:

- **APPROVE** when no in-scope blocking findings (CRITICAL or HIGH) and no PR-scope violations requiring revert.
- **CONDITIONAL** when in-scope findings exist but none are CRITICAL, or the PR contains trivial unscoped work to revert.
- **REJECT** when any in-scope finding is CRITICAL, or the PR contains non-trivial unscoped work requiring revert.

When the two verdicts differ, state both explicitly, e.g.: "Vendor verdict: REJECT. Scope-adjusted verdict: APPROVE - all blocking findings deferred to #42, #43; no in-scope blocking findings remain."

## PR-scope violations

- PR implements work owned by another open ticket -> flag as scope violation. Recommend "revert/stub the work belonging to #N."
- PR implements work owned by no ticket -> flag as scope violation AND (C) gap. Propose a gap ticket and recommend reverting the unscoped work.
