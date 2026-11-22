# ship-from-plan Reorder Design

## Summary

Change `ship-from-plan` in three ways:

1. Run differential review before CI convergence. Today CI runs first, and a CI job that needs manual approval blocks the differential review.
2. Run differential review once. Apply its AI-resolvable findings, then go to CI. Do not review again.
3. Add a third required model input, `DIFF_REVIEWER_MODEL`, for the differential-review subagent.

CI convergence becomes the last stage. It fixes automatic check failures without help and stops when only approval-gated checks remain.

## Goals

- Reach the differential review without waiting for a manual CI approval.
- Let the user select a separate model and effort for differential review.
- Fix automatic CI failures autonomously, as today.
- Stop cleanly when CI reaches a manual approval gate, and report what needs approval.

## Non-goals

- Do not change Stages 1, 2, or 3.
- Do not re-review the differential-review fix batch with any model.
- Do not approve CI runs or deployments on the user's behalf.
- Do not add a default for any model input.

## Components

| Path | Change |
|---|---|
| `skills/ship-from-plan/SKILL.md` | New input, stage reorder, single-pass Stage 4, approval-aware Stage 5, updated readiness and stop conditions. |
| `skills/ship-from-plan/references/model-map.md` | New Claude Code mappings and an updated dispatch contract. |

## Inputs and preflight

- Add `DIFF_REVIEWER_MODEL` as a third required input. It is a friendly name from `references/model-map.md`.
- Preflight resolves all three model inputs. If any one is unmapped or unavailable, list the available identifiers and ask. Never substitute.
- Update the frontmatter `description` to say "explicitly selected implementer, reviewer, and differential-reviewer models".

## Stage order

1. Isolate - no change.
2. Implement - no change. Uses `IMPLEMENTOR_MODEL` and `REVIEWER_MODEL`.
3. Create a Ready PR - no change. The post-`/create-pr` whole-branch review keeps `REVIEWER_MODEL`.
4. Differential Review and Triage - moved from Stage 5. Single pass.
5. Converge CI - moved from Stage 4. Last stage.

## Stage 4: Differential Review and Triage

1. Apply the `differential-review` applicability gate. For an excluded change, record `NOT_APPLICABLE` with the exact reason and go to Stage 5.
2. Dispatch one reviewer subagent with `DIFF_REVIEWER_MODEL`. Require it to read and follow `differential-review` against the current PR head.
3. Keep private artifact storage, the `AI_RESOLVABLE` and `HUMAN_DECISION` triage classes, and the `decisions.md` entry format unchanged.
4. Apply all `AI_RESOLVABLE` findings as one batch.
5. Run affected tests. If a fix cannot pass affected tests, remove that fix from the batch and record the finding as an unapplied AI-resolvable finding.
6. If the batch is not empty, commit with `fix(review): address differential findings` and push. If it is empty, make no commit.
7. Go to Stage 5.

Do not run a second differential review. Affected tests and CI are the only checks on the fix batch. The final report states this.

Record the Stage 4 status:

- `CLEAN`: the review found no findings.
- `ADDRESSED`: every AI-resolvable finding was applied. Human decisions may still be open.
- `NOT_APPLICABLE`: the applicability gate excluded the change.

Remove the loop back to CI and the 3-round no-progress limit for differential review.

## Stage 5: Converge CI

Classify each check on the current PR head:

- **Approval-gated**: the check waits for a human approval, such as an environment or deployment review, or a run with an `action_required` conclusion.
- **Automatic**: every other check.

Confirm the exact `gh` field values that identify approval-gated checks during implementation. Do not guess them in the skill text.

Wait until every automatic check reaches a terminal state. Polling does not count as a fix round. Then:

| Automatic checks | Approval-gated checks | Action |
|---|---|---|
| One or more failed | Any | Run a fix round with `/fix-ci`, as today. |
| All passed | None pending | CI is green. Go to Final Readiness. |
| All passed | One or more pending | Stop. Report each gated check and its run URL. |

Keep these rules unchanged:

- If no checks exist, stop because readiness cannot be established.
- `/fix-ci` rounds use standing authorization, commit with `fix(ci): resolve CI failures`, and push.
- A fix that needs human product or design authority stops the run with the decision required.
- Stop after 3 consecutive fix rounds that do not reduce the failed-check count.
- Never claim green while a check is missing, pending, skipped without an accepted policy, failed, cancelled, or timed out.

Jobs that a pending approval blocks may not exist yet. Do not wait for them.

## Final Readiness

Keep the draft check and `gh pr ready` step.

Report status `CONDITIONAL` when any of these are true:

- CI is not green on the current head. When the run stopped at an approval gate, report it as "awaiting CI approval".
- An AI-resolvable finding was not applied.
- A private decision entry has `Status: OPEN`.

Remove the condition "differential review is neither clean nor `NOT_APPLICABLE`".

The printed report adds:

- The Stage 4 status: `CLEAN`, `ADDRESSED`, or the `NOT_APPLICABLE` reason.
- A note that the differential-review fix batch was not re-reviewed.
- Any pending approval-gated checks and their run URLs.

## Stop conditions

- Remove "Differential-review 3-round no-progress limit".
- Add "CI awaiting manual approval after all automatic checks pass". The PR stays ready and the report is `CONDITIONAL`.
- Change "Missing required model input" and "Unmapped or unavailable selected model" to cover all three model inputs.

## model-map.md

Keep the uncommitted Claude Code section and its `Sonnet 5.5 high` and `Opus 5.5 high` entries. Add:

- `Sonnet 5.5 medium` -> Agent `model` `sonnet`, `effort` `medium`
- `Fable 5.2 high` -> Agent `model` `fable`, `effort` `high`

Update the dispatch contract:

- Every implementer dispatch uses `IMPLEMENTOR_MODEL`.
- Every task reviewer, final whole-branch reviewer, and post-`/create-pr` reviewer uses `REVIEWER_MODEL`.
- The differential-review subagent uses `DIFF_REVIEWER_MODEL`.

## Validation

The skill is prose and has no automated tests. Before completion:

- Confirm every stage cross-reference uses the new numbers. Stage 3 hands off to Stage 4, Stage 4 hands off to Stage 5, and Stage 5 hands off to Final Readiness.
- Confirm no text still describes a differential-review loop or its round limit.
- Confirm the stop-condition list, the readiness conditions, and the report fields match the stage text.
- Confirm each friendly model name in `model-map.md` maps to exactly one dispatch configuration.
