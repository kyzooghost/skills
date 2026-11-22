---
name: ship-from-plan
description: Use when the user provides a completed implementation plan and wants one continuous isolated execution through a reviewed, CI-green pull request marked ready for review, with explicitly selected implementer, reviewer, and differential-reviewer models.
---

# Ship From Plan

## Overview

Execute one completed implementation plan through isolation, implementation, ready PR creation, a single differential review, and CI convergence. Delegate each stage to its owning workflow while this skill owns authorization, transitions, stop conditions, private artifacts, and final readiness.

Invocation grants standing authorization for all AI-resolvable edits, commits, and pushes. Do not pause at nested routine approval gates. Human authority is still required for product, protocol, security-boundary, irreversible-data, and external-compatibility decisions.

Never auto-merge.

## Inputs

Required:

- `PLAN_PATH`: repository-relative path to a completed implementation plan.
- `IMPLEMENTOR_MODEL`: friendly name from `references/model-map.md`.
- `REVIEWER_MODEL`: friendly name from `references/model-map.md`.
- `DIFF_REVIEWER_MODEL`: friendly name from `references/model-map.md`. Used only by the Stage 4 differential-review subagent.

Optional:

- `BRANCH_NAME`: derived from the plan filename stem when omitted.
- `WORKTREE_DIR`: passed to `superpowers:using-git-worktrees`.
- `BASE_BRANCH`: passed to `/create-pr --base`; otherwise `/create-pr` resolves the repository default.

If a required input is missing, ask for it before starting Stage 1. Model selection is a required user input, not an environment default.

## Preflight

1. Read `PLAN_PATH` once. Require a writing-plans header and checkbox tasks. Stop if the file is missing or is not an implementation plan.
2. Read `references/model-map.md`.
3. Detect the active environment from runtime agent capabilities.
4. Resolve all three friendly model names and confirm they are dispatchable. If any is unavailable, list available identifiers and ask the user to choose; never substitute.
5. Require a Git repository with an `origin` remote.
6. Derive `BRANCH_NAME` from the plan stem when omitted.
7. Detect an existing branch, worktree, or PR using the intended branch name. V1 does not resume across sessions. If ownership cannot be proven for this invocation, stop and report the existing worktree, branch, PR URL, and observable head commit. Do not adopt or duplicate them.

Announce every stage and continue automatically unless a stop condition applies.

## Stage 1: Isolate

Read and follow `superpowers:using-git-worktrees`.

The invocation explicitly requests isolation, so it supplies worktree consent. Detect existing isolation first. Use `BRANCH_NAME` and `WORKTREE_DIR` when supplied.

Run project setup and baseline tests in the isolated worktree.

Overrides:

- If native and Git worktree creation both fail, stop. Never accept an in-place fallback.
- If baseline tests fail, stop with the exact command and failures. Do not implement on an unclean baseline.
- Never implement on `main`, `master`, or the primary checkout.

## Stage 2: Implement

Read and follow the active environment's native `superpowers:subagent-driven-development` workflow against `PLAN_PATH`.

Enforce these portable outcomes:

- Use a fresh implementer for every plan task.
- Every implementer dispatch uses `IMPLEMENTOR_MODEL`.
- Every task receives explicit spec-compliance and code-quality judgment. One combined reviewer or two sequential reviewers are both valid.
- Every task reviewer uses `REVIEWER_MODEL`.
- Resolve review findings through the native review loop.
- Run a final whole-branch review with `REVIEWER_MODEL`.
- Return control to this skill after the final review and before `superpowers:finishing-a-development-branch`.

Never downgrade, upgrade, or substitute the selected role models.

Handle implementer status:

- `DONE`: enter the native review loop.
- `DONE_WITH_CONCERNS`: resolve correctness and scope concerns before review; record non-blocking observations.
- `NEEDS_CONTEXT`: supply focused context and redispatch with the same model.
- `BLOCKED`: supply context, decompose the task, and redispatch with the same model. Stop only when resolution requires a different model or a human-owned change to the plan contract.

Do not impose a fixed retry count on context enrichment or task decomposition. Do not invoke `finishing-a-development-branch`.

## Stage 3: Create a Ready PR

Require a named feature branch. Push it before PR creation:

```bash
set -euo pipefail
BRANCH="$(git branch --show-current)"
test -n "$BRANCH"
git push --set-upstream origin "$BRANCH"
```

Record `HEAD` before invoking create-PR.

Invoke `/create-pr`. Add `--base "$BASE_BRANCH"` only when the user supplied `BASE_BRANCH`; otherwise allow `/create-pr` to resolve the configured repository default. Standing authorization covers its routine preview and any AI-resolvable `/doc-update` changes. Preserve create-PR sensitive-content scrubbing.

Require a PR number and URL. The PR is ready for review by default. If it is draft, mark it ready:

```bash
set -euo pipefail
if [ "$(gh pr view "$PR_NUMBER" --json isDraft --jq .isDraft)" = "true" ]; then
  gh pr ready "$PR_NUMBER"
fi
```

Stop if creation fails or the PR cannot be marked ready. Do not run `gh pr ready --undo`.

If `/create-pr` changed `HEAD`, run another whole-branch review with `REVIEWER_MODEL`, resolve every AI-owned finding, and push the reviewed head before Stage 4.

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

## Stage 5: Converge CI

Read the checks on the current PR head:

```bash
set -euo pipefail
gh pr checks "$PR_NUMBER" --json name,state,bucket,link,workflow
```

With `--json`, `gh pr checks` exits 0 even when checks fail or are pending. A nonzero exit means the PR has no checks or the command failed. Checks can take a short time to appear after a push. On the error `no checks reported on the '<branch>' branch`, retry for up to 5 minutes. If no checks appear, stop because readiness cannot be established. For any other error, stop and report it.

Classify each check by its `state`, not its `bucket`. `gh` puts `ACTION_REQUIRED` in the `fail` bucket, so a bucket-only reading treats an approval gate as a failure.

- Approval-gated: `state` is `WAITING` or `ACTION_REQUIRED`. The check waits for a human, such as an environment review or a workflow-run approval.
- Automatic: every other check.

Wait until every automatic check is terminal, which means its `bucket` is not `pending`. An automatic check passed when its `bucket` is `pass` or `skipping`. Polling does not count as a fix round. Jobs that a pending approval blocks may not exist yet. Do not wait for them.

Then act on the result:

| Automatic checks | Approval-gated checks | Action |
|---|---|---|
| One or more failed, cancelled, or timed out | Any | Run a fix round. |
| All passed | None | CI is green. Continue to Final Readiness. |
| All passed | One or more | Stop CI convergence. Record each gated check `name`, `workflow`, and `link`, and continue to Final Readiness, which reports `CONDITIONAL`. |

A fix round:

1. Invoke `/fix-ci` for the PR.
2. Analyze all failures before editing.
3. Treat this invocation as standing authorization for every AI-resolvable fix and the resulting commit.
4. Skip nested per-fix and commit approval prompts.
5. Apply all AI-resolvable fixes, commit with `fix(ci): resolve CI failures`, and push.
6. Read and classify the checks on the new head again.

If a fix requires human product or design authority, leave the PR ready and stop with the decision required.

Count automatic checks whose `bucket` is `fail` or `cancel` before the first fix round and after every completed round. Stop after 3 consecutive rounds that do not reduce that number. Report every attempted commit and the remaining failures.

Never count polling calls as rounds. Never claim green while an automatic check is missing, pending, failed, cancelled, or timed out, or while an approval-gated check exists.

## Final Readiness

Confirm the PR is ready for review before reporting. Run this by default, including when the report status is `CONDITIONAL`:

```bash
set -euo pipefail
if [ "$(gh pr view "$PR_NUMBER" --json isDraft --jq .isDraft)" = "true" ]; then
  gh pr ready "$PR_NUMBER"
fi
```

Report status `CONDITIONAL` when any of these are true:

- CI is not green on the current head. If Stage 5 stopped at an approval gate, report it as "awaiting CI approval".
- An AI-resolvable finding was not applied.
- A private decision entry has `Status: OPEN`.

`CONDITIONAL` changes the report. It does not return the PR to draft.

Print:

- PR URL, base, head, and readiness state.
- Implementation and CI commits.
- Differential-review fix commits.
- Stage 4 status: `CLEAN`, `ADDRESSED`, or the `NOT_APPLICABLE` reason. State that the differential-review fix batch was not re-reviewed.
- Every unapplied AI-resolvable finding.
- Every pending approval-gated check, with its `name`, `workflow`, and `link`.
- Exact private report and decision-ledger paths.
- Every unresolved human decision.

Retain the worktree while any private decision remains open. Never invoke branch cleanup or merge.

## Stop Conditions

Stop and report actionable context for:

- Missing or invalid plan.
- Missing `IMPLEMENTOR_MODEL`, `REVIEWER_MODEL`, or `DIFF_REVIEWER_MODEL`.
- Unmapped or unavailable selected model, for any of the three inputs.
- Missing Git `origin`.
- Ambiguous existing branch, worktree, or PR.
- Isolation or baseline-test failure.
- Blocker requiring another model or human authority.
- PR creation failure, or failure to mark the PR ready.
- Missing CI checks.
- Any other `gh pr checks` error.
- CI 3-round no-progress limit.
- CI awaiting manual approval after all automatic checks pass. Continue to Final Readiness. The PR stays ready and the report is `CONDITIONAL`.
- Failure to keep security artifacts private.

All other local, reversible, AI-resolvable implementation choices are covered by standing authorization.
