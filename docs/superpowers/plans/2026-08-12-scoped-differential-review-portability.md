# Scoped Differential Review Portability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite `scoped-differential-review` to be self-contained and portable across Claude Code, Cursor, and Codex - no pre-installed vendor skills, no rigid ticket formats, no companion skill requirements.

**Architecture:** Vendor the Trail of Bits `differential-review` plugin into the skill folder. Split the monolithic SKILL.md into a main file (<500 lines) plus two reference files for scope-routing logic and gap-ticket template. Replace rigid heading-based scope parsing with heuristic comprehension.

**Tech Stack:** Markdown skills, `gh` CLI, git

---

## File Structure

```
skills/scoped-differential-review/
├── SKILL.md                          # Main instructions (rewritten)
├── scope-routing.md                  # A/B/C classification + gap rule (new)
├── gap-ticket-template.md            # Template for proposed gap tickets (new)
├── ATTRIBUTION.md                    # Source, commit, license (new)
├── vendor/
│   └── differential-review/          # Full plugin tree minus .claude-plugin/
│       ├── LICENSE                   # CC BY-SA 4.0 text
│       ├── README.md
│       ├── agents/
│       │   └── adversarial-modeler.md
│       ├── commands/
│       │   └── diff-review.md
│       └── skills/
│           └── differential-review/
│               ├── SKILL.md
│               ├── methodology.md
│               ├── adversarial.md
│               ├── patterns.md
│               └── reporting.md
```

---

### Task 1: Vendor the differential-review plugin

**Files:**
- Create: `skills/scoped-differential-review/vendor/differential-review/` (entire tree)
- Create: `skills/scoped-differential-review/vendor/differential-review/LICENSE`
- Create: `skills/scoped-differential-review/ATTRIBUTION.md`

- [ ] **Step 1: Clone the vendor skill files**

```bash
cd /tmp
git clone --depth 1 https://github.com/trailofbits/skills.git trailofbits-skills
VENDOR_SHA=$(cd trailofbits-skills && git rev-parse HEAD)
echo "Vendor commit: $VENDOR_SHA"
```

- [ ] **Step 2: Copy the plugin tree (minus .claude-plugin/)**

```bash
DEST="skills/scoped-differential-review/vendor/differential-review"
mkdir -p "$DEST"
cp -r /tmp/trailofbits-skills/plugins/differential-review/agents "$DEST/"
cp -r /tmp/trailofbits-skills/plugins/differential-review/commands "$DEST/"
cp -r /tmp/trailofbits-skills/plugins/differential-review/skills "$DEST/"
cp /tmp/trailofbits-skills/plugins/differential-review/README.md "$DEST/"
```

- [ ] **Step 3: Add CC BY-SA 4.0 license file**

Copy the full CC BY-SA 4.0 license text from `https://creativecommons.org/licenses/by-sa/4.0/legalcode.txt` into `skills/scoped-differential-review/vendor/differential-review/LICENSE`.

- [ ] **Step 4: Write ATTRIBUTION.md**

Create `skills/scoped-differential-review/ATTRIBUTION.md`:

```markdown
# Attribution

Source: https://github.com/trailofbits/skills
Path: plugins/differential-review/ (full plugin tree, minus .claude-plugin/)
Commit: <VENDOR_SHA from step 1>
License: CC BY-SA 4.0 (see vendor/differential-review/LICENSE)
Vendored: 2026-08-12

This is an unmodified copy. To update, replace the contents of
vendor/differential-review/ with the corresponding folder from the source
repository at the same path.

This wrapper skill (scoped-differential-review) constitutes an adaptation
of the vendored material under CC BY-SA 4.0 terms.
```

Replace `<VENDOR_SHA from step 1>` with the actual SHA captured in step 1.

- [ ] **Step 5: Clean up temp clone**

```bash
rm -rf /tmp/trailofbits-skills
```

- [ ] **Step 6: Verify vendor structure**

```bash
find skills/scoped-differential-review/vendor -type f | sort
```

Expected output (file list matches the spec's tree diagram):
```
skills/scoped-differential-review/vendor/differential-review/LICENSE
skills/scoped-differential-review/vendor/differential-review/README.md
skills/scoped-differential-review/vendor/differential-review/agents/adversarial-modeler.md
skills/scoped-differential-review/vendor/differential-review/commands/diff-review.md
skills/scoped-differential-review/vendor/differential-review/skills/differential-review/SKILL.md
skills/scoped-differential-review/vendor/differential-review/skills/differential-review/adversarial.md
skills/scoped-differential-review/vendor/differential-review/skills/differential-review/methodology.md
skills/scoped-differential-review/vendor/differential-review/skills/differential-review/patterns.md
skills/scoped-differential-review/vendor/differential-review/skills/differential-review/reporting.md
```

- [ ] **Step 7: Commit**

```bash
git add skills/scoped-differential-review/vendor/ skills/scoped-differential-review/ATTRIBUTION.md
git commit -m "feat(scoped-differential-review): vendor Trail of Bits differential-review plugin

Source: https://github.com/trailofbits/skills
Commit: <VENDOR_SHA>
License: CC BY-SA 4.0"
```

---

### Task 2: Write scope-routing.md

**Files:**
- Create: `skills/scoped-differential-review/scope-routing.md`

- [ ] **Step 1: Write the scope-routing reference file**

Create `skills/scoped-differential-review/scope-routing.md` with this content:

```markdown
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
```

- [ ] **Step 2: Verify line count**

```bash
wc -l skills/scoped-differential-review/scope-routing.md
```

Expected: under 80 lines.

- [ ] **Step 3: Commit**

```bash
git add skills/scoped-differential-review/scope-routing.md
git commit -m "feat(scoped-differential-review): add scope-routing reference file"
```

---

### Task 3: Write gap-ticket-template.md

**Files:**
- Create: `skills/scoped-differential-review/gap-ticket-template.md`

- [ ] **Step 1: Write the gap-ticket template file**

Create `skills/scoped-differential-review/gap-ticket-template.md` with this content:

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add skills/scoped-differential-review/gap-ticket-template.md
git commit -m "feat(scoped-differential-review): add gap-ticket template reference"
```

---

### Task 4: Rewrite SKILL.md

**Files:**
- Modify: `skills/scoped-differential-review/SKILL.md` (full rewrite)

- [ ] **Step 1: Replace SKILL.md with the portable version**

Overwrite `skills/scoped-differential-review/SKILL.md` with:

```markdown
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
```

- [ ] **Step 2: Verify line count is under 500**

```bash
wc -l skills/scoped-differential-review/SKILL.md
```

Expected: under 100 lines (the above is ~95 lines of content).

- [ ] **Step 3: Verify no project-specific examples remain**

```bash
rg -in 'consensys|zkevm|synchronous-composability' skills/scoped-differential-review/SKILL.md
```

Expected: no output.

- [ ] **Step 4: Verify no rigid heading requirements remain**

```bash
rg -in 'authoritative set of recognized' skills/scoped-differential-review/SKILL.md
```

Expected: no output.

- [ ] **Step 5: Verify vendor skill is referenced by path**

```bash
rg -n 'vendor/differential-review' skills/scoped-differential-review/SKILL.md
```

Expected: matches in Phase 3 pointing to `vendor/differential-review/skills/differential-review/SKILL.md` and `vendor/differential-review/agents/adversarial-modeler.md`.

- [ ] **Step 6: Verify reference files are one level deep**

```bash
rg -n 'scope-routing\.md|gap-ticket-template\.md' skills/scoped-differential-review/SKILL.md
```

Expected: matches in Phases 4, 5, and the workflow description.

- [ ] **Step 7: Verify no em-dash**

```bash
rg -n $'—' skills/scoped-differential-review/SKILL.md
```

Expected: no output.

- [ ] **Step 8: Commit**

```bash
git add skills/scoped-differential-review/SKILL.md
git commit -m "feat(scoped-differential-review): rewrite SKILL.md for portability

- Vendor skill referenced by explicit path
- Heuristic scope parsing (no rigid headings)
- Generic examples (no project-specific references)
- Progressive disclosure via scope-routing.md and gap-ticket-template.md
- create-scoped-tickets as soft recommendation only"
```

---

### Task 5: Final integration verification

**Files:** None (read-only checks)

- [ ] **Step 1: Verify complete file structure matches spec**

```bash
find skills/scoped-differential-review -type f | sort
```

Expected output includes:
```
skills/scoped-differential-review/ATTRIBUTION.md
skills/scoped-differential-review/SKILL.md
skills/scoped-differential-review/gap-ticket-template.md
skills/scoped-differential-review/scope-routing.md
skills/scoped-differential-review/vendor/differential-review/LICENSE
skills/scoped-differential-review/vendor/differential-review/README.md
skills/scoped-differential-review/vendor/differential-review/agents/adversarial-modeler.md
skills/scoped-differential-review/vendor/differential-review/commands/diff-review.md
skills/scoped-differential-review/vendor/differential-review/skills/differential-review/SKILL.md
skills/scoped-differential-review/vendor/differential-review/skills/differential-review/adversarial.md
skills/scoped-differential-review/vendor/differential-review/skills/differential-review/methodology.md
skills/scoped-differential-review/vendor/differential-review/skills/differential-review/patterns.md
skills/scoped-differential-review/vendor/differential-review/skills/differential-review/reporting.md
```

- [ ] **Step 2: Verify no references to sibling scope-ticket skill as a hard dependency**

```bash
rg -n 'create-scoped-tickets' skills/scoped-differential-review/
```

Expected: only appears in `gap-ticket-template.md` as a soft recommendation ("For richer ticket structure...").

- [ ] **Step 3: Verify all cross-references resolve**

```bash
# Check scope-routing.md references gap-ticket-template.md
rg -n 'gap-ticket-template\.md' skills/scoped-differential-review/scope-routing.md

# Check SKILL.md references scope-routing.md
rg -n 'scope-routing\.md' skills/scoped-differential-review/SKILL.md

# Check SKILL.md references gap-ticket-template.md
rg -n 'gap-ticket-template\.md' skills/scoped-differential-review/SKILL.md

# Check SKILL.md references vendor skill path
rg -n 'vendor/differential-review/skills/differential-review/SKILL.md' skills/scoped-differential-review/SKILL.md
```

All four should produce at least one match.

- [ ] **Step 4: Verify total SKILL.md line count is reasonable**

```bash
wc -l skills/scoped-differential-review/SKILL.md skills/scoped-differential-review/scope-routing.md skills/scoped-differential-review/gap-ticket-template.md
```

Expected: SKILL.md < 100, scope-routing.md < 80, gap-ticket-template.md < 40. Total < 220.

- [ ] **Step 5: Verify description length is under 1024 chars**

```bash
head -4 skills/scoped-differential-review/SKILL.md | grep 'description:' | wc -c
```

Expected: under 1024 characters.
