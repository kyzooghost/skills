# scoped-planning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a new skill `skills/scoped-planning/SKILL.md` that operates as a per-stage scope-check overlay across the planning lifecycle (`/brainstorming`, `/grill-plan`, `/writing-plans`), wrapping each base skill as a black box and applying post-hoc scope guardrails at the stage's natural checkpoint, with zero reference to `scoped-tickets`.

**Architecture:** A single new SKILL.md file. The skill instructs the agent to run the wrapped lifecycle skill to its natural checkpoint (brainstorming's user-review gate, grill-plan's handoff, writing-plans' execution-handoff), then classify every overscoped artifact point against a scope map built from a GitHub issue-label universe (IN SCOPE, OWNED BY ANOTHER TICKET, GENUINE GAP), flag overscope inline, and propose gap tickets using a self-contained Agent Work Ticket template with approval before filing. Includes bootstrap mode for empty universes. All `gh` commands are inline; no scripts.

**Tech Stack:** Markdown, GitHub CLI (`gh`), `rg`, Git

**Design:** `docs/superpowers/specs/2026-07-28-scoped-planning-design.md`

Angle-bracketed metavariables inside replacement snippets are literal content for the skill's output templates, not unfinished plan steps.

## Global Constraints

- Zero reference to `scoped-tickets` anywhere in `skills/scoped-planning/SKILL.md`. Use the character-class pattern `scoped[-_]tickets` in any self-check `rg` command so the command does not self-match.
- Do not modify the vendor `brainstorming`, `grill-plan`, or `writing-plans` skills (they live outside this repo).
- No em-dash (`\u2014`) anywhere in the new SKILL.md - use regular dash (`-`) per workspace rule.
- Use `gh` CLI for all GitHub mutations; the only mutation is `gh issue create` for approved gap tickets.
- Never edit existing issues, change labels, or close issues.

---

### Task 1: Scaffold SKILL.md with frontmatter, summary, inputs, defaults, and self-contained scope-routing concepts

**Files:**
- Create: `skills/scoped-planning/SKILL.md`
- Reference: `docs/superpowers/specs/2026-07-28-scoped-planning-design.md`

**Interfaces:**
- Produces: `skills/scoped-planning/SKILL.md` containing frontmatter, Summary, Inputs, Built-in defaults, Scope inventory, IN/OWNED/GAP classification, Gap rule, and Self-contained gap-ticket template sections. Later tasks append Architecture, Workflow, Guardrail behavior, Error handling, Invocation, and Verification sections to this same file.

- [ ] **Step 1: Create the directory and write the frontmatter + Summary + Inputs + Built-in defaults**

Create `skills/scoped-planning/SKILL.md` with this exact content:

````markdown
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
````

- [ ] **Step 2: Append the Scope inventory, IN/OWNED/GAP classification, Gap rule, and gap-ticket template sections**

Append to `skills/scoped-planning/SKILL.md`:

````markdown
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
````

- [ ] **Step 3: Verify Task 1 content is present and constraint-compliant**

Run:

```bash
rg -n 'scoped[-_]tickets' skills/scoped-planning/SKILL.md
```

Expected: no output.

```bash
rg -n 'name: scoped-planning|## Inputs|## Built-in defaults|## Scope inventory|## IN/OWNED/GAP classification|## Gap rule|## Self-contained gap-ticket template' skills/scoped-planning/SKILL.md
```

Expected: one match per heading.

```bash
rg -n $'\u2014' skills/scoped-planning/SKILL.md
```

Expected: no output.

- [ ] **Step 4: Commit Task 1**

```bash
git add skills/scoped-planning/SKILL.md
git diff --cached --check
git commit -m "feat(scoped-planning): scaffold skill with scope-routing concepts"
```

Expected: one commit creating `skills/scoped-planning/SKILL.md`.

---

### Task 2: Add Architecture, Bootstrap mode, Workflow, and Guardrail behavior sections

**Files:**
- Modify: `skills/scoped-planning/SKILL.md` (append after the gap-ticket template section)

**Interfaces:**
- Consumes: the Scope inventory, IN/OWNED/GAP classification, and Gap rule defined in Task 1.
- Produces: the Architecture, Bootstrap mode, Workflow (Phase 0 + 3 modes), and Guardrail behavior sections that Task 3's Error handling and Verification sections reference.

- [ ] **Step 1: Append the Architecture and Bootstrap mode sections**

Append to `skills/scoped-planning/SKILL.md`:

````markdown
## Architecture

`scoped-planning` is a per-stage scope-check overlay with three entry points, each wrapping one lifecycle skill as a black box and bolting a scope guard onto its output:

| Mode | Wraps | Scope-checks |
|------|-------|--------------|
| `scoped-planning /brainstorming` | `brainstorming` | The emerging spec/design - flag scope creep vs the ticket universe before the user-review gate. |
| `scoped-planning /grill-plan` | `grill-plan` | The grilled plan - flag unresolved decisions that drift outside ticket scope. |
| `scoped-planning /writing-plans` | `writing-plans` | The task plan - flag any task that touches work owned by another ticket or outside the universe. |

Each stage keeps its own human review gate intact. `scoped-planning` is invoked once per stage, not as a single end-to-end run.

## Bootstrap mode

When the ticket universe is empty (new project), `scoped-planning /brainstorming` with no `--tickets` enters **bootstrap mode**: skip the Phase 0 scope-check. Run `brainstorming` to its full terminal state - spec written, self-reviewed, and committed per `brainstorming`'s own flow. Then, from that committed spec, help the user draft the first ticket(s) in the Agent Work Ticket format and create them via `gh issue create --label <label>`. Then exit - the user re-invokes with `--tickets` once the universe exists. Drafting tickets from the committed spec (not a half-formed design) ensures the seeded universe is correctly scoped.
````

- [ ] **Step 2: Append the Workflow section (Phase 0 + 3 modes)**

Append to `skills/scoped-planning/SKILL.md`:

````markdown
## Workflow

Each mode follows the same shape: build scope map -> run wrapped skill (black box) to its natural checkpoint -> apply scope-check guardrails post-hoc -> emit the artifact scope-cleaned.

### Phase 0 - Scope inventory

Run once at the start of every invocation (except bootstrap):

1. List all open GitHub issues carrying `--label` via `gh issue list --label <label> --state open --json number,title,body`.
2. For each issue, parse the recognized scope-section headings to extract owned scope ("The owner may" / "Scope of Work") and excluded scope ("The owner must not" / "Not In Scope").
3. Build the scope map: `{ticketNumber -> {owned, excluded}}`.
4. Fetch each target ticket in `--tickets` via `gh issue view <N> -R <REPO>` and confirm it is OPEN and carries `--label`. If any target ticket is closed, missing, or not in the label universe: **Error - unknown target ticket**. Stop.
5. Mark the union of the target tickets' owned scope as the in-scope region.
6. If the map is empty and no `--tickets` given: enter **bootstrap mode**.

### Mode: `/scoped-planning /brainstorming <idea>`

- **Bootstrap mode** (empty universe): see the Bootstrap mode section above.
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
````

- [ ] **Step 3: Append the Guardrail behavior section**

Append to `skills/scoped-planning/SKILL.md`:

````markdown
## Guardrail behavior (all modes)

The scope-check runs as a post-hoc guardrail at the wrapped skill's natural checkpoint, not alongside its dialogue and not as a separate report. The deliverable is the wrapped skill's normal artifact, scope-cleaned before handoff:

- **IN SCOPE** - silent pass. No annotation; the artifact is emitted as the base skill would emit it.
- **OWNED BY ANOTHER TICKET** - flag inline at the point of collision (a spec section, an unresolved decision, a task line). Name the owning ticket. Ask the user how to resolve before the artifact is handed off.
- **GENUINE GAP** - flag inline at the unowned work. **Stop and ask**: create a gap ticket (embedded template) or narrow the artifact to drop the gap.

The final output is indistinguishable from the base skill's own output, except overscoped content has been flagged and resolved before the artifact is handed off.
````

- [ ] **Step 4: Verify Task 2 content is present**

Run:

```bash
rg -n '## Architecture|## Bootstrap mode|## Workflow|### Phase 0|### Mode:|## Guardrail behavior' skills/scoped-planning/SKILL.md
```

Expected: matches for Architecture, Bootstrap mode, Workflow, Phase 0, three Mode headings, and Guardrail behavior.

```bash
rg -n 'scoped[-_]tickets' skills/scoped-planning/SKILL.md
```

Expected: no output.

```bash
rg -n $'\u2014' skills/scoped-planning/SKILL.md
```

Expected: no output.

- [ ] **Step 5: Commit Task 2**

```bash
git add skills/scoped-planning/SKILL.md
git diff --cached --check
git commit -m "feat(scoped-planning): add architecture, bootstrap, workflow, guardrails"
```

Expected: one commit appending the Architecture, Bootstrap mode, Workflow, and Guardrail behavior sections.

---

### Task 3: Add Error handling, Invocation, and Verification sections

**Files:**
- Modify: `skills/scoped-planning/SKILL.md` (append after Guardrail behavior)

**Interfaces:**
- Consumes: Workflow modes and Guardrail behavior from Task 2; scope-routing concepts from Task 1.
- Produces: the complete SKILL.md with Error handling, Invocation, and Verification sections.

- [ ] **Step 1: Append the Error handling and edge cases section**

Append to `skills/scoped-planning/SKILL.md`:

````markdown
## Error handling and edge cases

### Input errors

- A target ticket is not in the `--label` universe -> stop, report which ticket(s), ask the user to confirm the label or ticket numbers.
- `REPO` cannot be inferred and was not supplied -> stop, ask for `REPO`.
- `gh issue list` returns zero open tickets carrying `--label` AND no `--tickets` given -> enter bootstrap mode.
- `gh issue list` returns zero open tickets carrying `--label` AND `--tickets` given -> stop, ask the user to confirm the label; an empty universe means scope routing has no boundary to enforce.
- A target ticket has no recognizable scope section -> stop, ask the user for the scope statement. Never infer scope from a ticket title alone.
- `--tickets` omitted (and not bootstrap) -> stop, ask for `--tickets`. Target tickets are explicit; the skill does not infer them.
- The wrapped skill token is not one of `/brainstorming`, `/grill-plan`, `/writing-plans` -> stop, report the unrecognized token, list the three valid modes.

### Scope-map ambiguity

- An artifact point touches an area that two tickets both appear to own -> flag the overlap inline with both ticket numbers; ask the user to resolve the boundary. Do not silently pick one.
- The scope map cannot be built because tickets use non-standard headings -> stop, report which tickets are unparseable, ask the user to confirm the heading convention or supply scope statements.

### Gap-ticket creation

- User declines to create a gap ticket -> leave the gap flagged inline; do not file. Ask whether to narrow the artifact to drop the gap instead.
- `gh issue create` fails -> report the error, stop, do not file. Already-filed tickets in the same batch remain filed; report their numbers.
- A drafted gap ticket duplicates an existing open ticket the scope map missed -> do not file; note the possible duplicate URL and ask the user to confirm.

### No mutations beyond gap tickets

- The skill never edits existing issues, changes labels, closes issues, or mutates the wrapped skill's artifact beyond inline scope flags. The only GitHub mutation is `gh issue create` for approved gap tickets.
````

- [ ] **Step 2: Append the Invocation section**

Append to `skills/scoped-planning/SKILL.md`:

````markdown
## Invocation

```
/scoped-planning /brainstorming <idea> --tickets 4343,4380 --label synchronous-composability-demo
/scoped-planning /grill-plan <plan> --tickets 4343,4380
/scoped-planning /writing-plans <spec> --tickets 4343,4380
/scoped-planning /brainstorming <idea>           # bootstrap mode (empty universe)
```

`--repo` is optional when tickets are given as full URLs (inferred); required when `--tickets` are bare numbers. `--label` defaults to `agent-work-ticket`. All scope-routing guarantees become built-in defaults, never restated by the user.
````

- [ ] **Step 3: Append the Verification section**

Append to `skills/scoped-planning/SKILL.md`:

````markdown
## Verification

Since this is a Markdown skill wrapping vendor skills, verification is static checks plus scenario exercises against this SKILL.md.

### Static checks

```bash
# Self-check: this file must not reference the sibling scope-ticket skill
rg -n 'scoped[-_]tickets' skills/scoped-planning/SKILL.md
# Expected: no output

# All three wrapped skills are referenced
rg -n 'brainstorming|grill-plan|writing-plans' skills/scoped-planning/SKILL.md
# Expected: matches in mode descriptions and workflow

# Self-contained scope-routing concepts are all defined
rg -n 'Scope inventory|IN SCOPE|OWNED BY ANOTHER TICKET|GENUINE GAP|Gap rule|Gap-ticket template|bootstrap|Guardrail behavior' skills/scoped-planning/SKILL.md
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
12. **Target ticket not in label universe** - `--tickets 4343` but `#4343` lacks `--label`. Output: stop, report, ask to confirm.
````

- [ ] **Step 4: Verify Task 3 content is present**

Run:

```bash
rg -n '## Error handling and edge cases|## Invocation|## Verification|### Static checks|### Scenario exercises' skills/scoped-planning/SKILL.md
```

Expected: one match per item.

```bash
rg -n 'scoped[-_]tickets' skills/scoped-planning/SKILL.md
```

Expected: no output.

```bash
rg -n $'\u2014' skills/scoped-planning/SKILL.md
```

Expected: no output.

- [ ] **Step 5: Commit Task 3**

```bash
git add skills/scoped-planning/SKILL.md
git diff --cached --check
git commit -m "feat(scoped-planning): add error handling, invocation, verification"
```

Expected: one commit appending the Error handling, Invocation, and Verification sections.

---

### Task 4: Final spec-to-SKILL.md consistency verification

**Files:**
- Verify: `skills/scoped-planning/SKILL.md`
- Verify: `docs/superpowers/specs/2026-07-28-scoped-planning-design.md`
- Verify: `docs/superpowers/plans/2026-07-28-scoped-planning.md`

**Interfaces:**
- Consumes: the complete SKILL.md from Tasks 1-3 and the design spec.

- [ ] **Step 1: Verify the global constraints hold across the whole SKILL.md**

Run:

```bash
# Zero reference to scoped-tickets
rg -n 'scoped[-_]tickets' skills/scoped-planning/SKILL.md
# Expected: no output

# All three wrapped skills are referenced
rg -n 'brainstorming|grill-plan|writing-plans' skills/scoped-planning/SKILL.md
# Expected: matches in description, architecture, workflow, invocation

# No em-dash anywhere
rg -n $'\u2014' skills/scoped-planning/SKILL.md
# Expected: no output

# The only GitHub mutation is gh issue create for gap tickets
rg -n 'gh issue create|gh issue list|gh issue view|gh pr' skills/scoped-planning/SKILL.md
# Expected: gh issue create (gap tickets), gh issue list (scope inventory), gh issue view (target ticket validation); no gh pr mutations
```

- [ ] **Step 2: Verify every spec section has a corresponding SKILL.md section**

Run:

```bash
rg -n '## Summary|## Problem|## Goals|## Non-goals|## Architecture|## Bootstrap mode|## Inputs|## Built-in defaults|## Scope inventory|## IN/OWNED/GAP classification|## Gap rule|## Self-contained gap-ticket template|## Workflow|## Guardrail behavior|## Error handling and edge cases|## Invocation|## Verification|## Success criteria' docs/superpowers/specs/2026-07-28-scoped-planning-design.md
rg -n '## Inputs|## Built-in defaults|## Scope inventory|## IN/OWNED/GAP classification|## Gap rule|## Self-contained gap-ticket template|## Architecture|## Bootstrap mode|## Workflow|## Guardrail behavior|## Error handling and edge cases|## Invocation|## Verification' skills/scoped-planning/SKILL.md
```

Expected: every spec concept (inputs, defaults, scope inventory, IN/OWNED/GAP, gap rule, gap-ticket template, architecture, bootstrap, workflow modes, guardrail behavior, error handling, invocation, verification scenarios) has a corresponding section in SKILL.md.

- [ ] **Step 3: Verify the post-hoc guardrail principle is consistent**

Run:

```bash
rg -n 'natural checkpoint|post-hoc|before handoff|before the artifact is handed off' skills/scoped-planning/SKILL.md
```

Expected: the post-hoc-at-checkpoint principle appears in the Summary, Architecture, Workflow mode descriptions, and Guardrail behavior sections, with no contradicting "in-flight" or "during the run" wording.

- [ ] **Step 4: Verify all 12 scenarios from the spec are present in SKILL.md**

Run:

```bash
rg -n 'Bootstrap, empty universe|Brainstorm, all in scope|Brainstorm, owned by another ticket|Brainstorm, genuine gap|Grill, unresolved decision drifts|Writing-plans, task touches another ticket|Writing-plans, genuine gap task|Gap ticket created|Gap ticket declined|Two target tickets both appear to own|Unrecognized wrapped skill|Target ticket not in label universe' skills/scoped-planning/SKILL.md
```

Expected: 12 matches, one per scenario.

- [ ] **Step 5: Verify the SKILL.md reads as a coherent standalone skill**

Read `skills/scoped-planning/SKILL.md` in full and confirm:

1. The frontmatter `name` and `description` are present and accurate.
2. The sections flow in a logical order: frontmatter -> Summary -> Inputs -> Built-in defaults -> Scope inventory -> IN/OWNED/GAP classification -> Gap rule -> gap-ticket template -> Architecture -> Bootstrap mode -> Workflow (Phase 0 + 3 modes) -> Guardrail behavior -> Error handling -> Invocation -> Verification.
3. No section references `scoped-tickets` or any external scope-ticket skill.
4. The only GitHub mutations are `gh issue create` for approved gap tickets.
5. No em-dash characters.

- [ ] **Step 6: Run final repository checks**

Run:

```bash
git diff --check origin/main...HEAD
git diff --name-only origin/main...HEAD
git status --short --branch
```

Expected:

- `git diff --check` exits successfully with no output.
- The branch changes only `docs/superpowers/specs/2026-07-28-scoped-planning-design.md`, `docs/superpowers/plans/2026-07-28-scoped-planning.md`, and `skills/scoped-planning/SKILL.md`.
- The branch is clean.

- [ ] **Step 7: Commit the plan document**

```bash
git add docs/superpowers/plans/2026-07-28-scoped-planning.md
git diff --cached --check
git commit -m "docs(scoped-planning): implementation plan"
```

Expected: one commit adding the plan document.
