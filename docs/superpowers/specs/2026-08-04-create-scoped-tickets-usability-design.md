# Create Scoped Tickets Usability Design

## Context

`docs/todos/2026-07-29-create-scoped-tickets-usability.md` audits
`skills/create-scoped-tickets/SKILL.md` from the perspective of a first-time user.
The highest-impact findings are orientation, preflight requirements, invocation syntax,
a worked example, and the repository-local Agent Work Ticket schema.

The current skill is already behaviorally complete: it inventories a GitHub label universe,
decomposes a spec, resolves overlap, presents drafts for batch approval, and files approved
new issues. This design improves discoverability without changing those decisions or filing
rules.

## Goal

Make the skill usable by a reader with no prior context who needs to understand:

1. Where this skill fits in the repository's scoped-ticket workflow.
2. What must be available before it can run.
3. How to invoke the skill in the active Skill-tool surface.
4. What an Agent Work Ticket and a batch draft look like.
5. Why the ticket headings are structured and load-bearing.

## Chosen approach

Use surgical onboarding additions in `skills/create-scoped-tickets/SKILL.md`.
Keep the existing phase structure, scenario exercises, error handling, and GitHub commands
in place. Do not add a command wrapper or split the skill into multiple files.

## Design

### 1. Top-of-file orientation

Change the frontmatter description to describe only the triggering condition:

```text
Use when the user asks to seed or extend a GitHub label-scoped ticket set from a spec.
```

Expand the opening explanation with a short statement that Seed mode creates the first
exclusive ticket boundaries and Append mode extends an existing boundary set without
duplicating open ticket scope.

Add a `Fits into the workflow` section immediately after the introduction. It should explain:

1. `create-scoped-tickets` seeds or extends the labeled Agent Work Ticket universe.
2. `scoped-planning` consumes selected ticket numbers to scope brainstorming, plan grilling,
   and implementation-plan writing. Link to `../scoped-planning/SKILL.md`.
3. `scoped-differential-review` consumes selected ticket numbers to route PR findings. Link to
   `../scoped-differential-review/SKILL.md`.
4. `ship-from-plan` consumes the completed plan produced downstream and executes it through a
   reviewed draft PR. It does not require ticket numbers as a direct input. Link to
   `../ship-from-plan/SKILL.md`.

Add a note that the Agent Work Ticket headings are a repository-local schema. Downstream
skills parse headings such as `The owner may`, `The owner must not`, `Scope of Work`, and
`Definition of Done` to build scope boundaries, so users should preserve the template's
structure when creating or amending tickets.

### 2. Requirements and invocation

Add a `Requirements` section before `Inputs` with these prerequisites:

- A GitHub repository with Issues enabled.
- The `gh` CLI installed and authenticated.
- Permission to read issues and create new issues.
- At least one usable label, or permission to create a missing label after confirmation.
- A readable spec source.

Retain the existing behavior for missing labels: report the missing label and ask whether to
create it via `gh label create`; never create it without confirmation.

Replace the slash-command invocation examples with Skill-tool syntax:

```text
$create-scoped-tickets <SPEC> --repo <OWNER/REPO> --labels <label1>[,label2,...] [--scope-hint "<one-sentence hint>"]
```

Keep the existing input rules: `SPEC`, `REPO`, and `LABELS` are required, while `SCOPE_HINT`
is optional. The examples should use `$create-scoped-tickets` consistently and must not imply
that a `commands/create-scoped-tickets.md` wrapper exists.

### 3. Glossary and schema adoption

Add a concise `Glossary` section near the requirements and inputs:

- **Agent Work Ticket**: a GitHub issue with exclusive ownership, exclusions, dependencies,
  and verifiable completion criteria.
- **Label universe**: all open issues in the repository carrying any requested label.
- **Scope map**: the ownership and exclusion boundaries extracted from those issues.
- **Amendment proposal**: text-only suggested changes to an existing issue; this skill never
  applies them automatically.

State that Seed mode establishes this ticket format, while Append mode expects existing tickets
to expose the recognized scope headings. The existing ticket template remains the canonical
format. This makes the formalism explicit without changing the fallback or error behavior for
non-conforming tickets.

### 4. Worked example

Add a compact, neutral Seed-mode example after the Phase 4 output instructions. It should show
the complete shape of the interaction without introducing a second template.

Use this hypothetical input:

```text
SPEC: docs/report-export-spec.md
REPO: acme/reporting
LABELS: agent-work-ticket
Universe: zero open tickets with that label
```

The example spec contains two sections:

- `§1 Export endpoint`: add `POST /reports/exports`, validate the request, and return an export
  job identifier.
- `§2 Export audit event`: record an `ExportRequested` audit event after an export request is
  accepted. The event is consumed through the endpoint's accepted-request hook from `[draft #A]`.

The example's coverage map assigns `§1` to `[draft #A]` and `§2` to `[draft #B]`, in dependency
order. The two complete but concise drafts must demonstrate:

- Concrete Request / Outcome bullets.
- A Background / Context dependency from `[draft #B]` to the hook owned by `[draft #A]`.
- Repo-relative Source Materials.
- Disjoint `The owner may` and `The owner must not` sections.
- Verifiable Definition of Done items that can use the hook stub.
- The existing Stop Conditions and Blocking Questions shape.

End the example with the existing single approval gate and its three permitted responses:
`Approve all`, `Approve subset`, and `Revise`. The example is illustrative only; it must not
call `gh issue create` or suggest that the example issues have been filed.

### 5. Boundaries and verification

Only `skills/create-scoped-tickets/SKILL.md` changes. The edit must not:

- Add `commands/create-scoped-tickets.md`.
- Change Phase 0-5 classification, overlap, approval, or filing semantics.
- Change the recognized scope headings or ticket template requirements.
- Move the ten scenario exercises or create a new reference document.

Verification for the skill edit consists of:

1. `git diff --check`.
2. Static checks for the new `Fits into the workflow`, `Requirements`, and `Glossary` sections.
3. A check that `$create-scoped-tickets` is documented and the old `/create-scoped-tickets`
   form is absent from this skill.
4. The existing no-em-dash, stale-reference, core-section, and GitHub-command checks.
5. Manual review that all five selected TODO items are addressed and the Phase 0-5 behavior is
   unchanged.

## Acceptance criteria

- A first-time reader can identify the downstream workflow, prerequisites, invocation syntax,
  key vocabulary, and reason for the formal ticket headings without external context.
- The skill documents `$create-scoped-tickets` rather than an unavailable slash command.
- The worked example demonstrates a two-ticket Seed-mode coverage map, complete drafts, a
  dependency stub, and batch approval without implying that any issue was filed.
- Existing ticket-universe, overlap, approval, and filing rules remain intact.
- The target skill passes its documented verification checks and `git diff --check`.

## Non-goals

- Adding a command wrapper or changing Skill-tool registration.
- Moving scenario exercises to a reference file.
- Adding amendment automation.
- Changing the Agent Work Ticket template or recognized headings.
- Editing `scoped-planning`, `scoped-differential-review`, or `ship-from-plan`.
