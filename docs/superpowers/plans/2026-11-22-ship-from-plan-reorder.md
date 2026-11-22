# ship-from-plan Reorder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run one differential review before CI convergence in `ship-from-plan`, with its own required model input, and stop CI convergence at manual approval gates.

**Architecture:** Two prose files change. `references/model-map.md` gains Claude Code mappings and a three-role dispatch contract. `SKILL.md` gains a third model input, swaps Stages 4 and 5, makes differential review a single pass, and makes CI convergence approval-aware.

**Tech Stack:** Markdown skill files, `gh` CLI 2.97.0, `jq`, `rg`.

**Spec:** `docs/superpowers/specs/2026-11-22-ship-from-plan-reorder-design.md`

**Sourced facts used in Task 4:**

- With `--json`, `gh pr checks` writes JSON and exits 0, even when checks fail or are pending (`cli/cli` v2.97.0 `pkg/cmd/pr/checks/checks.go:189-190`).
- It exits nonzero when the PR has no checks (`checks.go:302-303`).
- `state` is the check status, or the conclusion when the status is `COMPLETED` (`aggregate.go:43-49`).
- The `ACTION_REQUIRED` state is in the `fail` bucket. The `WAITING` state is in the `pending` bucket (`aggregate.go:73-88`). Classify approval gates by `state`, not by `bucket`.

**Validation approach:** These files are prose and have no test suite. Each task ends with `rg` checks that prove the old text is gone and the new text is present.

---

## File Structure

| Path | Responsibility | Change |
|---|---|---|
| `skills/ship-from-plan/references/model-map.md` | Friendly model name to dispatch configuration, and which role uses which model. | Add 2 Claude Code mappings. Rewrite the dispatch contract for 3 roles. |
| `skills/ship-from-plan/SKILL.md` | Orchestration workflow. | Frontmatter, Overview, Inputs, Preflight, Stages 4 and 5, Final Readiness, Stop Conditions. |

---

### Task 1: Update the model map

**Files:**
- Modify: `skills/ship-from-plan/references/model-map.md:14-34`

The working tree already has an uncommitted `## Claude Code mappings` section with `Sonnet 5.5 high` and `Opus 5.5 high`. Keep it. This task adds to it and commits it.

- [ ] **Step 1: Add the two new Claude Code mappings**

Replace:

```markdown
- `Sonnet 5.5 high` -> Agent `model` `sonnet`, `effort` `high`
- `Opus 5.5 high` -> Agent `model` `opus`, `effort` `high`
```

With:

```markdown
- `Sonnet 5.5 medium` -> Agent `model` `sonnet`, `effort` `medium`
- `Sonnet 5.5 high` -> Agent `model` `sonnet`, `effort` `high`
- `Opus 5.5 high` -> Agent `model` `opus`, `effort` `high`
- `Fable 5.2 high` -> Agent `model` `fable`, `effort` `high`
```

- [ ] **Step 2: Rewrite the dispatch contract**

Replace:

```markdown
- Every implementer dispatch uses the resolved `IMPLEMENTOR_MODEL` configuration.
- Every task reviewer, final reviewer, and differential-review subagent uses the resolved `REVIEWER_MODEL` configuration.
```

With:

```markdown
- Every implementer dispatch uses the resolved `IMPLEMENTOR_MODEL` configuration.
- Every task reviewer, final whole-branch reviewer, and post-`/create-pr` reviewer uses the resolved `REVIEWER_MODEL` configuration.
- The differential-review subagent uses the resolved `DIFF_REVIEWER_MODEL` configuration.
```

- [ ] **Step 3: Verify**

Run:

```bash
rg -n 'Fable 5.2 high|Sonnet 5.5 medium|DIFF_REVIEWER_MODEL' skills/ship-from-plan/references/model-map.md
rg -n 'differential-review subagent uses the resolved `REVIEWER_MODEL`' skills/ship-from-plan/references/model-map.md
```

Expected: the first command prints 3 lines. The second command prints nothing and exits 1.

Check that each friendly name maps once:

```bash
rg -o '^- `[^`]+` ->' skills/ship-from-plan/references/model-map.md | sort | uniq -d
```

Expected: no output.

- [ ] **Step 4: Commit**

```bash
git add skills/ship-from-plan/references/model-map.md
git commit -m "feat(ship-from-plan): map Claude models and add differential-review role

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Add the third model input

**Files:**
- Modify: `skills/ship-from-plan/SKILL.md:3,10,20-22,37`

- [ ] **Step 1: Update the frontmatter description (line 3)**

Replace:

```markdown
with explicitly selected implementer and reviewer models.
```

With:

```markdown
with explicitly selected implementer, reviewer, and differential-reviewer models.
```

- [ ] **Step 2: Update the Overview stage list (line 10)**

Replace:

```markdown
Execute one completed implementation plan through isolation, implementation, ready PR creation, CI convergence, and differential-review convergence.
```

With:

```markdown
Execute one completed implementation plan through isolation, implementation, ready PR creation, a single differential review, and CI convergence.
```

- [ ] **Step 3: Add the required input (after line 22)**

Replace:

```markdown
- `REVIEWER_MODEL`: friendly name from `references/model-map.md`.
```

With:

```markdown
- `REVIEWER_MODEL`: friendly name from `references/model-map.md`.
- `DIFF_REVIEWER_MODEL`: friendly name from `references/model-map.md`. Used only by the Stage 4 differential-review subagent.
```

- [ ] **Step 4: Update Preflight step 4 (line 37)**

Replace:

```markdown
4. Resolve both friendly model names and confirm they are dispatchable. If either is unavailable, list available identifiers and ask the user to choose; never substitute.
```

With:

```markdown
4. Resolve all three friendly model names and confirm they are dispatchable. If any is unavailable, list available identifiers and ask the user to choose; never substitute.
```

- [ ] **Step 5: Verify**

Run:

```bash
rg -n 'DIFF_REVIEWER_MODEL|all three friendly|differential-reviewer models|single differential review' skills/ship-from-plan/SKILL.md
rg -n 'Resolve both|implementer and reviewer models|differential-review convergence' skills/ship-from-plan/SKILL.md
```

Expected: the first command prints 4 lines. The second command prints nothing and exits 1.

- [ ] **Step 6: Commit**

```bash
git add skills/ship-from-plan/SKILL.md
git commit -m "feat(ship-from-plan): require a differential-review model input

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Make differential review Stage 4, single pass

**Files:**
- Modify: `skills/ship-from-plan/SKILL.md:111-183` (the current `## Stage 4: Converge CI` and `## Stage 5: Differential Review and Triage` sections)

This task replaces both current Stage 4 and Stage 5 sections with the new Stage 4 only. Task 4 adds the new Stage 5. Between the two tasks the file has no CI stage. Do not stop between Task 3 and Task 4.

- [ ] **Step 1: Replace both sections**

Delete everything from the line `## Stage 4: Converge CI` up to, but not including, the line `## Final Readiness`. Put this text in its place:

````markdown
## Stage 4: Differential Review and Triage

Run one differential review. Do not repeat it after fixes.

Apply the `differential-review` applicability gate first.

If the change is documentation-only, formatting-only, or otherwise explicitly excluded, record Stage 4 as `NOT_APPLICABLE` with the exact reason, retain the Stage 2 final-review result, and continue to Stage 5.

For applicable changes, dispatch one reviewer subagent using `DIFF_REVIEWER_MODEL` and require it to read and follow `differential-review` against the current PR head.

Create private artifact storage:

```bash
set -euo pipefail
PLAN_STEM="$(basename "$PLAN_PATH" .md)"
ARTIFACT_DIR="$(git rev-parse --git-path ship-from-plan)/$PLAN_STEM"
mkdir -p "$ARTIFACT_DIR"
```

Move the full differential-review report into `ARTIFACT_DIR` before staging or pushing anything. Never stage, commit, publish, or paste the full report into the PR.

Triage every finding:

- `AI_RESOLVABLE`: the correct fix does not require product, protocol, security-boundary, irreversible-data, or external-compatibility authority. Include it in the fix batch. Size, file count, and complexity do not change this classification.
- `HUMAN_DECISION`: the fix requires one of those authorities. Append it to `$ARTIFACT_DIR/decisions.md` and continue triaging the remaining findings.

Use this exact decision entry:

```markdown
## [SEVERITY] <finding title>
- Source: differential-review report, <private report path> section <heading>
- File/line: <path>:<line>
- Finding: <bounded technical description>
- Why deferred: <human-owned tradeoff>
- Options considered: <options and material consequences>
- Recommendation: <recommended option when evidence supports one>
- Status: OPEN
```

After triage:

1. Apply all `AI_RESOLVABLE` findings as one batch.
2. Run affected tests. If a fix cannot pass affected tests, remove that fix from the batch and record its finding as unapplied.
3. If the batch is not empty, commit with `fix(review): address differential findings` and push.
4. Continue to Stage 5.

Do not run a second differential review. Affected tests and Stage 5 CI are the only checks on the fix batch.

Record the Stage 4 status:

- `CLEAN`: the review reported no findings.
- `ADDRESSED`: the review reported findings and the fix batch is complete. Report every unapplied AI-resolvable finding separately.
- `NOT_APPLICABLE`: the applicability gate excluded the change.

Human decisions do not stop triage of later findings. An open decision does not return the PR to draft. The PR stays ready.

````

- [ ] **Step 2: Verify**

Run:

```bash
rg -n '^## ' skills/ship-from-plan/SKILL.md
rg -n 'Return to Stage 4|fresh full differential review|full review rounds|## Stage 4: Converge CI' skills/ship-from-plan/SKILL.md
rg -n 'DIFF_REVIEWER_MODEL` and require|Run one differential review|`ADDRESSED`' skills/ship-from-plan/SKILL.md
```

Expected:

- The first command lists `Stage 3: Create a Ready PR`, then `Stage 4: Differential Review and Triage`, then the `## [SEVERITY]` template line, then `Final Readiness`. No `Stage 5` heading exists yet.
- The second command prints nothing and exits 1.
- The third command prints 3 lines.

Do not commit yet. Continue to Task 4 so the commit always has a CI stage.

---

### Task 4: Make CI convergence Stage 5, approval-aware

**Files:**
- Modify: `skills/ship-from-plan/SKILL.md` (insert before `## Final Readiness`)

- [ ] **Step 1: Insert the new Stage 5**

Insert this text immediately before the line `## Final Readiness`:

````markdown
## Stage 5: Converge CI

Read the checks on the current PR head:

```bash
set -euo pipefail
gh pr checks "$PR_NUMBER" --json name,state,bucket,link,workflow
```

With `--json`, `gh pr checks` exits 0 even when checks fail or are pending. A nonzero exit means the PR has no checks or the command failed. If no checks exist, stop because readiness cannot be established. For any other error, stop and report it.

Classify each check by its `state`, not its `bucket`. `gh` puts `ACTION_REQUIRED` in the `fail` bucket, so a bucket-only reading treats an approval gate as a failure.

- Approval-gated: `state` is `WAITING` or `ACTION_REQUIRED`. The check waits for a human, such as an environment review or a workflow-run approval.
- Automatic: every other check.

Wait until every automatic check is terminal, which means its `bucket` is not `pending`. Polling does not count as a fix round. Jobs that a pending approval blocks may not exist yet. Do not wait for them.

Then act on the result:

| Automatic checks | Approval-gated checks | Action |
|---|---|---|
| One or more failed, cancelled, or timed out | Any | Run a fix round. |
| All passed | None pending | CI is green. Continue to Final Readiness. |
| All passed | One or more pending | Stop. Report each gated check `name`, `workflow`, and `link`. |

A fix round:

1. Invoke `/fix-ci` for the PR.
2. Analyze all failures before editing.
3. Treat this invocation as standing authorization for every AI-resolvable fix and the resulting commit.
4. Skip nested per-fix and commit approval prompts.
5. Apply all AI-resolvable fixes, commit with `fix(ci): resolve CI failures`, and push.
6. Read and classify the checks on the new head again.

If a fix requires human product or design authority, leave the PR ready and stop with the decision required.

Track the number of failed automatic checks after every completed fix round. Stop after 3 consecutive rounds that do not reduce that number. Report every attempted commit and the remaining failures.

Never count polling calls as rounds. Never claim green while an automatic check is missing, pending, skipped without an accepted policy, failed, cancelled, or timed out, or while an approval-gated check is pending.

````

- [ ] **Step 2: Verify**

Run:

```bash
rg -n '^## ' skills/ship-from-plan/SKILL.md
rg -n 'WAITING|ACTION_REQUIRED|state`, not its `bucket' skills/ship-from-plan/SKILL.md
rg -n 'continue to Stage 5|Continue to Stage 5|before Stage 4' skills/ship-from-plan/SKILL.md
```

Expected:

- The first command lists the stages in this order: `Stage 1: Isolate`, `Stage 2: Implement`, `Stage 3: Create a Ready PR`, `Stage 4: Differential Review and Triage`, `Stage 5: Converge CI`, then `Final Readiness` and `Stop Conditions`. The `## [SEVERITY]` template line appears inside Stage 4.
- The second command prints 2 lines, both inside Stage 5.
- The third command prints the Stage 3 line that pushes the reviewed head `before Stage 4`, and the two Stage 4 lines that continue to Stage 5.

- [ ] **Step 3: Commit Tasks 3 and 4 together**

```bash
git add skills/ship-from-plan/SKILL.md
git commit -m "feat(ship-from-plan): run one differential review before CI

Differential review now runs once, right after PR creation, using
DIFF_REVIEWER_MODEL. CI convergence runs last, fixes automatic check
failures, and stops when only approval-gated checks remain.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Update Final Readiness and Stop Conditions

**Files:**
- Modify: `skills/ship-from-plan/SKILL.md` (`## Final Readiness` and `## Stop Conditions` sections)

- [ ] **Step 1: Replace the CONDITIONAL criteria**

Replace:

```markdown
- CI is not green on the current head.
- Differential review is neither clean nor `NOT_APPLICABLE`.
- An AI-resolvable finding remains.
- A private decision entry has `Status: OPEN`.
```

With:

```markdown
- CI is not green on the current head. If Stage 5 stopped at an approval gate, report it as "awaiting CI approval".
- An AI-resolvable finding was not applied.
- A private decision entry has `Status: OPEN`.
```

- [ ] **Step 2: Replace the printed report list**

Replace:

```markdown
- PR URL, base, head, and readiness state.
- Implementation and CI commits.
- Differential-review fix commits.
- Differential-review status or `NOT_APPLICABLE` reason.
- Exact private report and decision-ledger paths.
- Every unresolved human decision.
```

With:

```markdown
- PR URL, base, head, and readiness state.
- Implementation and CI commits.
- Differential-review fix commits.
- Stage 4 status: `CLEAN`, `ADDRESSED`, or the `NOT_APPLICABLE` reason. State that the differential-review fix batch was not re-reviewed.
- Every unapplied AI-resolvable finding.
- Every pending approval-gated check, with its `name`, `workflow`, and `link`.
- Exact private report and decision-ledger paths.
- Every unresolved human decision.
```

- [ ] **Step 3: Update the stop-condition list**

Replace:

```markdown
- Missing required model input.
- Unmapped or unavailable selected model.
```

With:

```markdown
- Missing `IMPLEMENTOR_MODEL`, `REVIEWER_MODEL`, or `DIFF_REVIEWER_MODEL`.
- Unmapped or unavailable selected model, for any of the three inputs.
```

Replace:

```markdown
- CI 3-round no-progress limit.
- Differential-review 3-round no-progress limit.
```

With:

```markdown
- CI 3-round no-progress limit.
- CI awaiting manual approval after all automatic checks pass. The PR stays ready and the report is `CONDITIONAL`.
```

- [ ] **Step 4: Verify the whole file**

Run:

```bash
rg -n 'Differential-review 3-round|neither clean nor|An AI-resolvable finding remains|Missing required model input' skills/ship-from-plan/SKILL.md
rg -n 'awaiting CI approval|awaiting manual approval|not re-reviewed|for any of the three inputs' skills/ship-from-plan/SKILL.md
rg -n 'REVIEWER_MODEL' skills/ship-from-plan/SKILL.md
```

Expected:

- The first command prints nothing and exits 1.
- The second command prints 4 lines.
- In the third command, every `DIFF_REVIEWER_MODEL` line is in Inputs, Stage 4, or Stop Conditions. No Stage 2 or Stage 3 line uses `DIFF_REVIEWER_MODEL`. No Stage 4 line uses bare `REVIEWER_MODEL`.

Read the full file once, top to bottom. Confirm:

- Stage 3 hands off to Stage 4, Stage 4 hands off to Stage 5, and Stage 5 hands off to Final Readiness.
- No text describes a differential-review loop or a differential-review round limit.
- Every Stage 5 stop appears in the stop-condition list.
- Every `CONDITIONAL` criterion has a matching report field.

- [ ] **Step 5: Commit**

```bash
git add skills/ship-from-plan/SKILL.md
git commit -m "feat(ship-from-plan): report approval gates and single-pass review status

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
