# scoped-planning Design

## Summary

A new skill `scoped-planning` that operates as a per-stage scope-check overlay across the planning lifecycle (`/brainstorming` -> `/grill-plan` -> `/writing-plans`). Each stage is invoked separately as `scoped-planning /<wrapped-skill>`, wrapping that stage's base skill as a black box and bolting a scope guard onto its artifact. The wrapped skill runs to its natural checkpoint (brainstorming's user-review gate, grill-plan's handoff, writing-plans' execution-handoff); scope-check guardrails are then applied post-hoc, before the artifact is handed off. The deliverable is the wrapped skill's normal output (spec / grilled plan / task plan), kept scope-clean - not a separate verdict report.

The skill has zero reference to `scoped-tickets`. All scope-routing logic - scope inventory, IN/OWNED/GAP classification, gap rule, gap-ticket template - is self-contained inside this skill. Deleting `scoped-tickets` is a separate follow-up task, performed after `scoped-planning` and `scoped-differential-review` are both in place and validated on real work - not part of this skill's implementation.

## Problem

Running `/brainstorming`, `/grill-plan`, or `/writing-plans` for a ticket in a GitHub issue-label universe produces an artifact with no boundary against the surrounding ticket universe. A plan can grow to touch work owned by other open tickets, duplicate scope, or introduce entirely new scope - none of the base skills check.

Today this is enforced manually with a verbose prompt restated at every stage. The goal is to compress this to a single short per-stage invocation with the no-duplication, gap-routing, and no-new-scope guarantees as built-in defaults, while keeping each stage's human review gate intact.

## Goals

- Wrap `brainstorming`, `grill-plan`, and `writing-plans` (vendor, unmodified) as the planning engines, one per stage.
- Provide a per-stage scope-check overlay invoked three times across the lifecycle, not a single end-to-end run.
- Build a scope map from a GitHub issue-label universe and classify every overscoped artifact point as IN SCOPE, OWNED BY ANOTHER TICKET, or GENUINE GAP.
- Apply scope-checks as post-hoc guardrails at the wrapped skill's natural checkpoint (brainstorming's user-review gate, grill-plan's handoff, writing-plans' execution-handoff), not by interrupting the wrapped skill's dialogue and not as a separate verdict report.
- Propose gap tickets using a self-contained Agent Work Ticket template; create them only after approval.
- Bootstrap a new project's ticket universe when it is empty.
- Zero reference to `scoped-tickets` anywhere in the skill.

## Non-goals

- Modify `brainstorming`, `grill-plan`, or `writing-plans` (vendor skills).
- Reference or depend on `scoped-tickets`.
- Run the whole lifecycle in one continuous invocation; each stage's human review gate stays intact.
- Emit a separate scope-verdict report; the deliverable is the wrapped skill's normal artifact, scope-cleaned in flight.
- Edit existing issues, change labels, or close issues. The only GitHub mutation is `gh issue create` for approved gap tickets.
- Author the wrapped skill's artifact; the skill guards scope, it does not replace the base skill's output.

## Architecture

`scoped-planning` is a per-stage scope-check overlay with three entry points, each wrapping one lifecycle skill as a black box and bolting a scope guard onto its output:

| Mode | Wraps | Scope-checks |
|------|-------|--------------|
| `scoped-planning /brainstorming` | `brainstorming` | The emerging spec/design - flag scope creep vs the ticket universe before the user-review gate. |
| `scoped-planning /grill-plan` | `grill-plan` | The grilled plan - flag unresolved decisions that drift outside ticket scope. |
| `scoped-planning /writing-plans` | `writing-plans` | The task plan - flag any task that touches work owned by another ticket or outside the universe. |

Each stage keeps its own human review gate intact. `scoped-planning` is invoked once per stage, not as a single end-to-end run.

### Bootstrap mode

When the ticket universe is empty (new project), `scoped-planning /brainstorming` enters **bootstrap mode**: it skips the scope-check guard and instead helps the user draft the first ticket(s) in the Agent Work Ticket format, then commits them as GitHub issues with the configured label. Subsequent stages assume a non-empty universe.

## Inputs (per invocation)

- `--tickets <N,M,...>` (required, except bootstrap): one or more target ticket numbers in the label universe that this planning effort implements (e.g. `4343,4380`). Comma-separated. The scope-check is against the union of the target tickets' owned scope.
- `--label <label>` (optional): the GitHub label defining the ticket universe. Default: `agent-work-ticket`.
- `<wrapped-skill>` (required): the base skill to wrap - one of `/brainstorming`, `/grill-plan`, `/writing-plans`. This token selects the overlay mode; no separate `--mode` flag.
- The wrapped skill's own inputs (idea/spec, plan draft, etc.) are passed through unchanged.

Invocation shape: `/scoped-planning /brainstorming <idea>`, `/scoped-planning /grill-plan <plan>`, `/scoped-planning /writing-plans <spec>`.

Bootstrap: `/scoped-planning /brainstorming <idea>` with no `--tickets` and an empty universe triggers bootstrap mode.

## Built-in defaults (self-contained, never restated by the user)

`scoped-planning` embeds its own copies of - no reference to `scoped-tickets`:

- **Scope-section headings** recognized when parsing tickets: "The owner may", "The owner must not", "Not In Scope", "Scope of Work", "Definition of Done".
- **Gap-ticket template**: the Agent Work Ticket Markdown format (Request/Outcome, Background/Context, Source Materials, Scope of Work, Definition of Done, Stop Conditions, Blocking Questions), identical to the one `scoped-tickets` emits.
- **Scope map**: built from all open issues carrying `--label`, mapping each ticket to its owned scope and excluded scope.

## Workflow

Each mode follows the same 4-phase shape: build scope map -> run wrapped skill (black box) to its natural checkpoint -> apply scope-check guardrails post-hoc -> emit the artifact scope-cleaned.

### Shared Phase 0 - Scope inventory

Run once at the start of every invocation (except bootstrap):

1. List all open GitHub issues carrying `--label` via `gh issue list --label <label> --state open --json number,title,body`.
2. For each issue, parse the recognized scope-section headings to extract **owned scope** ("The owner may" / "Scope of Work") and **excluded scope** ("The owner must not" / "Not In Scope").
3. Build the scope map: `{ticketNumber -> {owned, excluded}}`.
4. Fetch each target ticket in `--tickets` via `gh issue view <N> -R <REPO>` and confirm it is OPEN and carries `--label`. If any target ticket is closed, missing, or not in the label universe: **Error - unknown target ticket**. Stop.
5. Mark the union of the target tickets' owned scope as the in-scope region.
6. If the map is empty and no `--tickets` given: enter **bootstrap mode**.

### Mode: `/scoped-planning /brainstorming <idea>`

- **Bootstrap mode** (empty universe): skip Phase 0 scope-check. Run `brainstorming` to its full terminal state - spec written, self-reviewed, and committed per `brainstorming`'s own flow. Then, from that committed spec, help the user draft the first ticket(s) in the Agent Work Ticket format and create them via `gh issue create --label <label>`. Then exit - the user re-invokes with `--tickets` once the universe exists. Drafting tickets from the committed spec (not a half-formed design) ensures the seeded universe is correctly scoped.
- **Normal mode**: run `brainstorming` to its user-review gate. Then apply scope-check guardrails post-hoc, before the gate is passed:
  - **IN SCOPE**: design stays within the union of target tickets' owned scope. Silent pass; emit the spec as `brainstorming` would.
  - **OWNED BY ANOTHER TICKET**: flag inline at the design point that collides. Name the owning ticket. Ask the user to narrow the design, reassign, or explicitly accept the cross-ticket work before the artifact is finalized.
  - **GENUINE GAP**: flag inline at the unowned design point. **Stop and ask**: (i) create a gap ticket now (embedded template) or (ii) narrow the design to drop the gap.

### Mode: `/scoped-planning /grill-plan <plan>`

- Run `grill-plan` to its handoff. Then apply scope-check guardrails post-hoc to the unresolved-decision list and the plan's scope:
  - **IN SCOPE**: unresolved decisions stay within the union of target tickets' owned scope. Silent pass; emit the grilled plan as `grill-plan` would.
  - **OWNED BY ANOTHER TICKET**: flag inline which unresolved decisions would commit to another ticket's owned work. Ask the user to narrow or reassign.
  - **GENUINE GAP**: flag inline decisions that require unowned work. **Stop and ask**: create a gap ticket or narrow.

### Mode: `/scoped-planning /writing-plans <spec>`

- Run `writing-plans` to its execution-handoff. Then apply scope-check guardrails post-hoc to every task:
  - **IN SCOPE**: every task touches only the union of target tickets' owned scope. Silent pass; emit the plan as `writing-plans` would, through to its execution-handoff.
  - **OWNED BY ANOTHER TICKET**: flag inline at the offending tasks and which ticket owns the work they touch. Ask the user to drop/split/reassign the tasks.
  - **GENUINE GAP**: flag inline tasks needing unowned work. **Stop and ask**: create a gap ticket or drop the tasks.

### Guardrail behavior (all modes)

The scope-check runs as a post-hoc guardrail at the wrapped skill's natural checkpoint, not alongside its dialogue and not as a separate report. The deliverable is the wrapped skill's normal artifact, scope-cleaned before handoff:

- **IN SCOPE** - silent pass. No annotation; the artifact is emitted as the base skill would emit it.
- **OWNED BY ANOTHER TICKET** - flag inline at the point of collision (a spec section, an unresolved decision, a task line). Name the owning ticket. Ask the user how to resolve before the artifact is handed off.
- **GENUINE GAP** - flag inline at the unowned work. **Stop and ask**: create a gap ticket (embedded template) or narrow the artifact to drop the gap.

The final output is indistinguishable from the base skill's own output, except overscoped content has been flagged and resolved before the artifact is handed off.

## Gap-ticket template (Agent Work Ticket format, self-contained)

When a GENUINE GAP is found and the user chooses to create a gap ticket, draft it in the Agent Work Ticket format - the same format `scoped-tickets` emits. The template is embedded verbatim in this skill; no reference to `scoped-tickets`.

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

On user approval, file via `gh issue create -R <REPO> --label <LABEL> -t "<title>" -b "<body>"`, capture the real number, and surface it back. Do not file unless approved.

## Error handling and edge cases

### Input errors

- `--tickets` not in the `LABEL` universe -> stop, report which ticket(s), ask the user to confirm the label or ticket numbers.
- `REPO` cannot be inferred and was not supplied -> stop, ask for `REPO`.
- `gh issue list` returns zero open tickets carrying `LABEL` AND no `--tickets` given -> enter bootstrap mode.
- `gh issue list` returns zero open tickets carrying `LABEL` AND `--tickets` given -> stop, ask the user to confirm the label; an empty universe means scope routing has no boundary to enforce.
- A target ticket has no recognizable scope section -> stop, ask the user for the scope statement. Never infer scope from a title alone.
- `--tickets` omitted -> stop, ask for `--tickets`. Target tickets are explicit; the skill does not infer them.
- Wrapped skill token is not one of `/brainstorming`, `/grill-plan`, `/writing-plans` -> stop, report the unrecognized token, list the three valid modes.

### Scope-map ambiguity

- A design/decision/task touches an area that two tickets both appear to own -> flag the overlap inline with both ticket numbers; ask the user to resolve the boundary. Do not silently pick one.
- Scope map cannot be built because tickets use non-standard headings -> stop, report which tickets are unparseable, ask the user to confirm the heading convention or supply scope statements.

### Gap-ticket creation

- User declines to create a gap ticket -> leave the gap flagged inline; do not file. Ask whether to narrow the artifact to drop the gap instead.
- `gh issue create` fails -> report the error, stop, do not file. Already-filed tickets in the same batch remain filed; report their numbers.
- A drafted gap ticket duplicates an existing open ticket the scope map missed -> do not file; note the possible duplicate URL and ask the user to confirm.

### No mutations beyond gap tickets

- The skill never edits existing issues, changes labels, closes issues, or mutates the wrapped skill's artifact beyond inline scope flags. The only GitHub mutation is `gh issue create` for approved gap tickets.

## Invocation

```
/scoped-planning /brainstorming <idea> --tickets 4343,4380 --label synchronous-composability-demo
/scoped-planning /grill-plan <plan> --tickets 4343,4380
/scoped-planning /writing-plans <spec> --tickets 4343,4380
/scoped-planning /brainstorming <idea>           # bootstrap mode (empty universe)
```

`--repo` is optional when tickets are given as full URLs (inferred). `--label` defaults to `agent-work-ticket`.

## Verification

Static checks against the written `skills/scoped-planning/SKILL.md`:

```bash
# Self-check: this file must not reference the sibling scope-ticket skill
rg -n 'scoped[-_]tickets' skills/scoped-planning/SKILL.md
# Expected: no output

# All three wrapped skills are referenced
rg -n 'brainstorming|grill-plan|writing-plans' skills/scoped-planning/SKILL.md
# Expected: matches in mode descriptions

# Self-contained scope-routing concepts are all defined
rg -n 'Scope inventory|IN SCOPE|OWNED BY ANOTHER TICKET|GENUINE GAP|Gap-ticket template|bootstrap' skills/scoped-planning/SKILL.md
# Expected: matches in workflow and classification sections

# No em-dash (per workspace rule)
rg -n $'\u2014' skills/scoped-planning/SKILL.md
# Expected: no output
```

### Scenario exercises

1. **Bootstrap, empty universe** - No `--tickets`, `gh issue list` returns zero. Output: run `brainstorming` to its terminal state (spec written + committed); then draft first ticket(s) in Agent Work Ticket format from that spec; create via `gh issue create`; exit.
2. **Brainstorm, all in scope** - Design stays within `#4343` and `#4380`'s owned scope. Output: `brainstorming`'s normal spec, no inline flags.
3. **Brainstorm, owned by another ticket** - A spec section touches `#4350`'s owned scope. Output: inline flag at the section, name `#4350`, ask user to narrow/reassign/accept.
4. **Brainstorm, genuine gap** - A design point needs unowned work. Output: inline flag, stop and ask - create gap ticket or narrow.
5. **Grill, unresolved decision drifts out of scope** - A grilled unresolved decision would commit to `#4350`'s work. Output: inline flag at the decision, ask user to narrow/reassign.
6. **Writing-plans, task touches another ticket's scope** - A task line implements `#4350`'s scope. Output: inline flag at the task, ask user to drop/split/reassign.
7. **Writing-plans, genuine gap task** - A task needs unowned work. Output: inline flag, stop and ask - create gap ticket or drop the task.
8. **Gap ticket created** - User approves gap creation. Output: `gh issue create`, capture real number, surface it back.
9. **Gap ticket declined** - User declines. Output: gap stays flagged inline, no filing; ask whether to narrow.
10. **Two target tickets both appear to own the same area** - Overlap flagged inline with both numbers; ask user to resolve boundary.
11. **Unrecognized wrapped skill** - User invokes `/scoped-planning /foo`. Output: stop, report unrecognized token, list three valid modes.
12. **Target ticket not in label universe** - `--tickets 4343` but `#4343` lacks `LABEL`. Output: stop, report, ask to confirm.

## Success criteria

The skill is successful when a scoped planning run produces the wrapped skill's normal artifact (spec / grilled plan / task plan) with overscoped content flagged inline and resolved before the user sees it, gap tickets drafted in the Agent Work Ticket format and filed only after approval, and zero reference to `scoped-tickets` anywhere in the SKILL.md.
