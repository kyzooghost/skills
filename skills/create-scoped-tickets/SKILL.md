---
name: create-scoped-tickets
description: Use when the user asks to seed or extend a GitHub label-scoped ticket set from a spec.
---

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

## Inputs

- `SPEC` - the technical implementation spec. A file path (e.g. `docs/spec.md`), a URL, or pasted content. Required.
- `REPO` - GitHub repository hosting the ticket universe, e.g. `org/project`. Required.
- `LABELS` - one or more labels that define the target universe, comma-separated (e.g. `topic1` on first seed; `topic1,topic2` when appending on a second run). Required. Every drafted ticket is filed with all listed labels.
- `SCOPE_HINT` (optional) - one sentence narrowing the slice of the spec to decompose in this run. Omit to decompose the whole spec.

Bare ticket numbers in later cross-references require `REPO`; `REPO` cannot be inferred from a spec path.

## Built-in defaults (never restated by the user)

- Exclusive ownership: every drafted ticket's "The owner may" scope is disjoint from every other drafted ticket and from every existing open ticket in the union of `LABELS`.
- Overlap-resolves-to-amendment: when the spec's next chunk overlaps an existing open ticket, propose amending that ticket (concrete text diff) rather than filing a duplicate.
- Draft-first, batch approval: never call `gh issue create` before showing the full drafted set and receiving one approval.
- Stubs and dependencies over folding: when a drafted ticket needs work owned by another drafted or existing ticket, specify the stub or interface and record the dependency; never pull the other ticket's work into this one.
- No mutations besides filing: this skill never edits, closes, or relabels existing issues. Amendment proposals are text only.

## Workflow

### Phase 0 - Universe inventory

1. List all open issues carrying **any** of `LABELS` in `REPO`:

   ```bash
   for label in <LABELS>; do
     gh issue list -R <REPO> --label "$label" --state open --limit 200 --json number,title,body,labels
   done
   ```

   Deduplicate by issue number.

2. For each existing ticket, parse the recognized scope-section headings and extract:
   - Owned scope from "The owner may" or "Scope of Work".
   - Excluded scope from "The owner must not" or "Not In Scope".

   The authoritative set of recognized headings is: `The owner may`, `The owner must not`, `Not In Scope`, `Scope of Work`, `Definition of Done`. If a ticket uses none of these, see Error handling.

3. Build the scope map: `{ticketNumber -> {title, labels, owned, excluded}}`. This is the boundary set drafted tickets must not cross.

4. Classify the universe state:
   - **Empty**: zero open tickets under `LABELS`. Enter **Seed** mode.
   - **Non-empty**: one or more open tickets. Enter **Append** mode.

### Phase 1 - Spec decomposition

Read `SPEC` in full. Identify the atomic units of work it prescribes. Each unit becomes at most one ticket candidate. Group only where a single owner would reasonably deliver the whole group in one PR sequence.

Constraints on the candidate set:

- Every candidate's outcome traces to a concrete section of `SPEC`. Cite the section path (e.g. `docs/spec.md §3.7`).
- Candidates are mutually exclusive: no work item appears in two candidates.
- Candidates are collectively complete for the region of `SPEC` in scope (governed by `SCOPE_HINT` if given).
- Candidates are ordered so that dependencies land before dependents; note dependencies explicitly.

### Phase 2 - Overlap classification (Append mode only)

For each candidate, classify against the Phase 0 scope map:

- **NEW** - candidate's owned scope is disjoint from every existing ticket. Draft it as a new ticket in Phase 3.
- **AMEND** - candidate's owned scope overlaps an existing open ticket's "The owner may" or Definition of Done. Do not draft a new ticket. Draft an **amendment proposal** for the existing ticket: the concrete text to add or refine (Request/Outcome bullets, Scope of Work bullets, DoD items, Source Materials links), citing the spec section. The user decides whether and how to apply it; this skill does not edit issues.
- **PARTIAL** - candidate's owned scope partially overlaps an existing ticket. Split the candidate:
  - The overlapping slice becomes an AMEND proposal.
  - The non-overlapping slice becomes a NEW candidate whose "The owner must not" explicitly cites the existing ticket by number.

Any two NEW candidates must also be mutually exclusive. If they overlap, merge them or resplit their boundaries before Phase 3.

### Phase 3 - Draft tickets

For each NEW candidate, write an Agent Work Ticket using the template below.

Scoping rules per ticket:

- Every bullet under "The owner may" must trace to the candidate's slice of `SPEC`. If a bullet cannot be traced, delete it.
- **"The owner must not" is the most important section.** Build it from the union of the Phase 0 scope map and the sibling NEW candidates in this run: name each ticket (existing by number, sibling by draft label like `[draft #A]`) whose scope borders this one.
- Where the ticket depends on work owned by another ticket (existing or sibling draft) that is not yet implemented, do NOT pull that work in. Specify the stub or interface to code against (name the interface and the owning ticket) and record the dependency in Background / Context.
- Definition of Done must be verifiable without any other ticket's unimplemented work; tests may use stubs.

#### Ticket template

Title: `<Area> - <Concrete outcome>` (e.g. `Besu Sidecar - Builder 2PC: collapse lock-gap-lock pattern`).

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
* <Out-of-scope work item> (ticket #M or [draft #A])
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

### Phase 4 - Present drafts for batch approval

Emit the full drafted set as text in this order:

1. **Universe snapshot**: label(s), REPO, mode (Seed / Append), existing-ticket count.
2. **Coverage map**: which spec section maps to which drafted ticket letter (`[draft #A]`, `[draft #B]`, ...) or to which existing ticket (`AMEND #N`).
3. **New ticket drafts** in dependency order, each shown in full.
4. **Amendment proposals** grouped by target existing ticket number, each showing the concrete text to add.
5. **Uncovered spec sections** if any (spec content that mapped to neither a NEW candidate nor an AMEND proposal). Ask the user to confirm they are intentionally out of scope.

Ask one approval question with three permitted answers:

- **Approve all** - proceed to Phase 5 and file every NEW draft.
- **Approve subset** - the user names the drafts to file; the rest are held.
- **Revise** - the user gives feedback; return to Phase 3.

Amendment proposals are never filed by this skill; they are handed to the user as text regardless of approval choice.

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

### Phase 5 - File approved NEW drafts

For each approved NEW draft, run:

```bash
gh issue create \
  -R <REPO> \
  --title "<Title>" \
  --body "<full Agent Work Ticket body>" \
  --label "<label1>" --label "<label2>" ...
```

Include every entry in `LABELS`. Capture the returned issue number and URL.

After all filings, print a receipt: for each draft letter, the assigned issue number and URL, or "held" if not filed. If any filing fails, stop and report; already-filed tickets remain filed.

## Author checklist (per drafted ticket, before Phase 4)

- [ ] Outcome is specific enough to implement without guessing product intent
- [ ] Sources cite concrete spec sections
- [ ] "The owner may" bullets each trace to `SPEC`
- [ ] "The owner must not" cites every adjacent ticket in the universe (existing by number, sibling by draft letter)
- [ ] DoD is testable without other tickets' unimplemented work
- [ ] Stop conditions cover the real judgment calls
- [ ] Dependencies on stubs/interfaces are recorded in Background / Context

## Error handling and edge cases

### Input errors

- `SPEC` cannot be read (path missing, URL fetch fails) -> stop, report the error, ask for a working source.
- `REPO` not supplied -> stop, ask for `REPO`. Do not infer from spec path.
- `LABELS` not supplied -> stop, ask for at least one label.
- A label in `LABELS` does not exist on `REPO` -> report which; ask whether to create it via `gh label create` (do not create without confirmation).

### Universe-inventory errors

- An existing ticket carrying a label in `LABELS` has none of the recognized scope-section headings -> report which ticket(s); ask the user for its owned/excluded scope in one line each. Never infer scope from a ticket title alone.
- Two existing tickets appear to own the same area -> report the pair with numbers; ask the user which owns it before decomposing. Do not silently pick one.

### Decomposition errors

- `SPEC` yields zero decomposable units -> stop, ask whether `SCOPE_HINT` should be widened or the spec is genuinely out of scope for this label.
- After Phase 2, every candidate is AMEND -> emit only amendment proposals; skip Phase 5 (nothing to file); tell the user the spec is fully covered by existing tickets and the amendments are optional refinements.
- A candidate cannot be split cleanly around an existing ticket boundary -> flag the pair; ask the user to redraw the boundary before proceeding.

### Filing errors

- `gh issue create` fails on a draft -> report the error; stop before the next filing; already-filed tickets remain filed and their numbers are printed.
- Network / auth failure before any filing -> stop; nothing is filed.

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

## Verification

Static checks against this SKILL.md:

```bash
set -euo pipefail

# No em-dash (per workspace rule)
rg -n $'\u2014' skills/create-scoped-tickets/SKILL.md || true
# Expected: no output

# No lingering references to the removed workflows
if awk '/^## Verification$/{exit} {print}' skills/create-scoped-tickets/SKILL.md | rg -n 'Workflow B|Workflow C|sync_pr_status_comments|PR review scoped|status comments'; then
  exit 1
fi
# Expected: no output

# gh commands used
rg -n 'gh issue list|gh issue create' skills/create-scoped-tickets/SKILL.md
# Expected: matches in Phase 0 and Phase 5

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

# Every core heading appears exactly once before Verification
core_text="$(awk '/^## Verification$/{print; exit} {print}' skills/create-scoped-tickets/SKILL.md)"
required_headings=(
  '## Inputs'
  '## Built-in defaults (never restated by the user)'
  '## Workflow'
  '### Phase 0 - Universe inventory'
  '### Phase 1 - Spec decomposition'
  '### Phase 2 - Overlap classification (Append mode only)'
  '### Phase 3 - Draft tickets'
  '### Phase 4 - Present drafts for batch approval'
  '### Phase 5 - File approved NEW drafts'
  '## Author checklist (per drafted ticket, before Phase 4)'
  '## Error handling and edge cases'
  '## Invocation'
  '## Verification'
)
for heading in "${required_headings[@]}"; do
  match_count="$(printf '%s\n' "$core_text" | rg -F -x "$heading" | wc -l | tr -d ' ' || true)"
  if [ "$match_count" -ne 1 ]; then
    printf 'Expected exactly one heading: %s (found %s)\n' "$heading" "$match_count"
    exit 1
  fi
done
echo 'All core sections appear exactly once.'
```

Scenario exercises:

1. **Seed, empty universe** - `LABELS=topic1`, zero open tickets. Spec has 4 atomic units. Output: 4 NEW drafts in dependency order, batch approval, 4 `gh issue create` calls, receipt with 4 issue numbers.
2. **Append, all NEW** - `LABELS=topic1,topic2`, existing tickets under `topic1` cover an adjacent area not in the spec. All 3 spec candidates are NEW. Output: 3 NEW drafts with "The owner must not" citing existing ticket numbers.
3. **Append, all AMEND** - The spec's units all overlap existing tickets. Output: amendment proposals only; nothing to file in Phase 5; explicit "fully covered" message.
4. **Append, PARTIAL split** - One candidate overlaps existing ticket #N. Output: one AMEND proposal for #N plus one NEW draft whose "The owner must not" cites #N.
5. **Overlap between two NEW candidates** - Phase 3 detects two drafts touching the same area. Output: merged or resplit before Phase 4; no overlap survives to approval.
6. **Existing ticket with non-standard scope headings** - Ticket #M uses only "Description". Output: stop, ask user for #M's owned/excluded scope.
7. **User approves subset** - User approves drafts A, C; holds B. Output: file A and C; B held in receipt.
8. **Filing failure mid-batch** - `gh issue create` errors on draft B after A filed. Output: stop; report A filed, B failed, C not attempted.
9. **SCOPE_HINT narrows the run** - Hint restricts decomposition to §4. Output: only §4 units become candidates; §3 spec content appears under "Uncovered spec sections" for user confirmation.
10. **Two existing tickets appear to own the same area** - Phase 0 detects the conflict. Output: stop, ask user to resolve before decomposition.
