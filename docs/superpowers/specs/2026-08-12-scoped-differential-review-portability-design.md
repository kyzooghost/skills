# Scoped Differential Review - Portability Redesign

## Goal

Make `scoped-differential-review` usable by anyone on Claude Code, Cursor, or Codex without requiring pre-installed vendor skills, specific ticket formats, or knowledge of companion skills.

## Locked decisions

| Decision | Choice |
|----------|--------|
| Vendor dependency | Copy Trail of Bits `differential-review` folder into `vendor/differential-review/` |
| Scope parsing | Pure heuristic. Comprehend ticket body, extract OWNED/EXCLUDED, display scope map, continue without confirmation |
| Rigid headings | Removed. No "authoritative set of recognized scope-section headings" |
| Platform portability | Existing `skills/` folder structure works for all targets. `sync-skill` handles distribution |
| `create-scoped-tickets` reference | Soft recommendation in gap-ticket section, never a hard gate |
| Hardcoded examples | Replace Consensys/zkevm references with generic placeholders |

## File structure

```
skills/scoped-differential-review/
├── SKILL.md                          # Main instructions (<500 lines)
├── scope-routing.md                  # A/B/C classification + gap rule
├── gap-ticket-template.md            # Template for proposed gap tickets
├── vendor/
│   └── differential-review/          # Unmodified copy of Trail of Bits skill
│       ├── SKILL.md
│       ├── methodology.md
│       ├── adversarial.md
│       ├── patterns.md
│       ├── reporting.md
│       └── agents/
└── ATTRIBUTION.md                    # Source repo, commit SHA, license
```

Progressive disclosure: SKILL.md covers workflow and decision points. Reference files hold classification logic and templates. All one level deep from SKILL.md.

## SKILL.md content

### Frontmatter

```yaml
name: scoped-differential-review
description: Wraps a vendored differential-review skill and routes its findings against a GitHub issue-label universe. Classifies each finding as IN SCOPE, OWNED BY ANOTHER TICKET, or GENUINE GAP. Proposes gap tickets for unowned findings. Use when running a scope-bounded security review of a PR.
```

### Sections

1. **Prerequisites** - `gh` CLI authenticated with repo access.
2. **Inputs** - `PR`, `--tickets`, `--label`, `--repo` (inferred from ticket URLs when possible).
3. **Workflow** - Five phases:
   - Phase 1: Parse inputs, build scope map (heuristic extraction)
   - Phase 2: Validate target tickets exist and are open
   - Phase 3: Run vendored `differential-review` (read and follow `vendor/differential-review/SKILL.md`)
   - Phase 4: Route findings by scope (see `scope-routing.md`)
   - Phase 5: Emit report and handle gaps (see `gap-ticket-template.md`)
4. **Invocation examples** - Generic (`org/repo#123`, `my-feature-label`)
5. **Error handling** - Missing tickets, empty universe, unparseable tickets, vendor failures

### Degrees of freedom

| Area | Freedom | Rationale |
|------|---------|-----------|
| Scope parsing | High | Multiple ticket formats are valid; heuristic comprehension adapts |
| A/B/C classification | Low | Exact rules; consistency is critical |
| Vendor delegation | Low | Invoke exactly as documented; do not alter methodology |
| Gap-ticket drafting | Medium | Template provides structure; adapt to project context |

## Scope routing logic (`scope-routing.md`)

### Heuristic scope parsing

For every ticket in the label universe:
1. Read the full ticket body.
2. Extract two lists:
   - **OWNED**: work this ticket is responsible for delivering.
   - **EXCLUDED**: work explicitly out of scope.
3. Infer from any available signal: acceptance criteria, task lists, headings, "out of scope" language, description, title.
4. If a ticket is too vague to extract any ownership boundary, mark as "unparseable" in the scope map. Note in the report. Continue with remaining tickets.
5. If ALL target tickets are unparseable, stop and report the error. At least one target ticket must have a parseable ownership boundary to route findings against.

### Scope map display

After extraction, emit the scope map in the report without pausing:

```
## Scope Map
- #42: OWNS "payment retry logic for idempotent endpoints"
       EXCLUDES "webhook delivery (owned by #43)"
- #43: OWNS "webhook delivery and DLQ"
       EXCLUDES "retry logic (owned by #42)"
```

### A/B/C classification

Applied to every finding from the vendor's report:

- **(A) IN SCOPE** - finding touches a target ticket's owned scope. Raise as a normal review finding.
- **(B) OWNED BY ANOTHER TICKET** - finding touches another open ticket's owned scope. Do not raise against PR. Only valid comment: "this belongs to #N; revert/stub it here."
- **(C) GENUINE GAP** - no ticket owns the area. Draft a gap ticket.
- **Uncertain** - default to (C), flag uncertainty in the report.

Stubs, interfaces, TODOs standing in for other tickets' work are correct by design. Verify the stub matches the agreed interface; do not raise as findings.

### Recommendation reconciliation

Preserve vendor verdict verbatim. Emit a scope-adjusted verdict alongside:

- **APPROVE** when no in-scope blocking findings and no PR-scope violations.
- **CONDITIONAL** when in-scope findings exist but none are CRITICAL, or PR has trivial unscoped work to revert.
- **REJECT** when any in-scope finding is CRITICAL, or PR has non-trivial unscoped work.

State both verdicts explicitly when they differ.

## Gap-ticket template (`gap-ticket-template.md`)

```markdown
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
```

For richer ticket structure, see the `create-scoped-tickets` skill.

## Vendor attribution (`ATTRIBUTION.md`)

```markdown
# Attribution

Source: https://github.com/trailofbits/skills
Path: plugins/differential-review/skills/differential-review/
Commit: <SHA at time of vendoring>
License: <license from source repo>
Vendored: <date>

This is an unmodified copy. To update, replace the contents of this
directory with the corresponding folder from the source repository.
```

## Changes from current skill

| Current | New |
|---------|-----|
| Assumes `differential-review` installed externally | Vendors the skill in `vendor/` |
| Rigid heading requirements ("The owner may", etc.) | Heuristic comprehension of any ticket format |
| Hard error on unparseable tickets | Mark unparseable, continue, note in report |
| Project-specific examples (Consensys, zkevm) | Generic examples |
| References `create-scoped-tickets` as prerequisite | Soft recommendation only |
| Single 222-line SKILL.md | Split into SKILL.md + 2 reference files |
| No setup/prerequisites section | Explicit prerequisites |
| No scope map display | Scope map emitted in report for auditability |

## Out of scope

- Extracting into a standalone plugin/repo (revisit if adoption grows)
- Platform-specific install instructions (handled by `sync-skill`)
- Modifying the vendor skill's methodology
- Automated testing framework (static checks and scenario exercises remain manual)
