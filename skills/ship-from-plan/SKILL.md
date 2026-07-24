---
name: ship-from-plan
description: Use when the user provides a completed implementation plan and wants one continuous isolated execution through a reviewed, CI-green draft pull request with explicitly selected implementer and reviewer models.
---

# Ship From Plan

## Overview

Execute one completed implementation plan through isolation, implementation, draft PR creation, CI convergence, and differential-review convergence. Delegate each stage to its owning workflow while this skill owns authorization, transitions, stop conditions, private artifacts, and final readiness.

Invocation grants standing authorization for all AI-resolvable edits, commits, and pushes. Do not pause at nested routine approval gates. Human authority is still required for product, protocol, security-boundary, irreversible-data, and external-compatibility decisions.

Never auto-merge.

## Inputs

Required:

- `PLAN_PATH`: repository-relative path to a completed implementation plan.
- `IMPLEMENTOR_MODEL`: friendly name from `references/model-map.md`.
- `REVIEWER_MODEL`: friendly name from `references/model-map.md`.

Optional:

- `BRANCH_NAME`: derived from the plan filename stem when omitted.
- `WORKTREE_DIR`: passed to `superpowers:using-git-worktrees`.
- `BASE_BRANCH`: passed to `/create-pr --base`; otherwise `/create-pr` resolves the repository default.

If a required input is missing, ask for it before starting Stage 1. Model selection is a required user input, not an environment default.

## Preflight

1. Read `PLAN_PATH` once. Require a writing-plans header and checkbox tasks. Stop if the file is missing or is not an implementation plan.
2. Read `references/model-map.md`.
3. Detect the active environment from runtime agent capabilities.
4. Resolve both friendly model names and confirm they are dispatchable. If either is unavailable, list available identifiers and ask the user to choose; never substitute.
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

## Stage 3: Create a Draft PR

Require a named feature branch. Push it before PR creation:

```bash
set -euo pipefail
BRANCH="$(git branch --show-current)"
test -n "$BRANCH"
git push --set-upstream origin "$BRANCH"
```

Record `HEAD` before invoking create-PR.

Invoke `/create-pr --draft`. Add `--base "$BASE_BRANCH"` only when the user supplied `BASE_BRANCH`; otherwise allow `/create-pr` to resolve the configured repository default. Standing authorization covers its routine preview and any AI-resolvable `/doc-update` changes. Preserve create-PR sensitive-content scrubbing.

Require a PR number, URL, and draft state. Stop if creation fails or the platform cannot preserve draft state.

If `/create-pr` changed `HEAD`, run another whole-branch review with `REVIEWER_MODEL`, resolve every AI-owned finding, and push the reviewed head before Stage 4.

Never mark the PR ready in this stage.

## Stage 4: Converge CI

Wait for every check on the current PR head to reach a terminal state. Polling while checks run does not count as a fix round.

If all checks pass, continue to Stage 5.

If no checks exist, stop because readiness cannot be established.

For a terminal failing head:

1. Invoke `/fix-ci` for the PR.
2. Analyze all failures before editing.
3. Treat this invocation as standing authorization for every AI-resolvable fix and the resulting commit.
4. Skip nested per-fix and commit approval prompts.
5. Apply all AI-resolvable fixes, commit with `fix(ci): resolve CI failures`, and push.
6. Wait for checks on the new head to finish.

If a fix requires human product or design authority, leave the PR draft and stop with the decision required.

Track the number of failed checks after every completed fix round. Stop after 3 consecutive rounds that do not reduce that number. Report every attempted commit and the remaining failures.

Never count polling calls as rounds. Never claim green while checks are missing, pending, skipped without an accepted policy, failed, cancelled, or timed out.

## Stage 5: Differential Review and Triage

Apply the `differential-review` applicability gate first.

If the change is documentation-only, formatting-only, or otherwise explicitly excluded, record Stage 5 as `NOT_APPLICABLE` with the exact reason and retain the Stage 2 final-review result.

For applicable changes, dispatch a reviewer subagent using `REVIEWER_MODEL` and require it to read and follow `differential-review`.

Create private artifact storage:

```bash
set -euo pipefail
PLAN_STEM="$(basename "$PLAN_PATH" .md)"
ARTIFACT_DIR="$(git rev-parse --git-path ship-from-plan)/$PLAN_STEM"
mkdir -p "$ARTIFACT_DIR"
```

Move each full differential-review report into `ARTIFACT_DIR` before staging or pushing anything. Never stage, commit, publish, or paste the full report into the PR.

Triage every finding:

- `AI_RESOLVABLE`: the correct fix does not require product, protocol, security-boundary, irreversible-data, or external-compatibility authority. Include it in the round's fix batch. Size, file count, and complexity do not change this classification.
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
2. Run affected tests.
3. Commit with `fix(review): address differential findings`.
4. Push.
5. Return to Stage 4 until CI is green on the new head.
6. Run a fresh full differential review against the updated head.

Repeat until no AI-resolvable finding remains. Stop after 3 consecutive full review rounds that do not reduce the unresolved AI-resolvable finding count.

Human decisions do not stop triage of later findings, but any open decision keeps the PR draft.

## Final Readiness

Mark the PR ready with:

```bash
set -euo pipefail
gh pr ready "$PR_NUMBER"
```

Only run that mutation when all conditions hold:

- CI is green on the current head.
- Differential review is clean or `NOT_APPLICABLE`.
- No AI-resolvable finding remains.
- No private decision entry has `Status: OPEN`.

Otherwise leave the PR draft and report status `CONDITIONAL`.

Print:

- PR URL, base, head, and draft/readiness state.
- Implementation and CI commits.
- Differential-review fix commits.
- Differential-review status or `NOT_APPLICABLE` reason.
- Exact private report and decision-ledger paths.
- Every unresolved human decision.

Retain the worktree while any private decision remains open. Never invoke branch cleanup or merge.

## Stop Conditions

Stop and report actionable context for:

- Missing or invalid plan.
- Missing required model input.
- Unmapped or unavailable selected model.
- Missing Git `origin`.
- Ambiguous existing branch, worktree, or PR.
- Isolation or baseline-test failure.
- Blocker requiring another model or human authority.
- Draft PR creation or draft-state failure.
- Missing CI checks.
- CI 3-round no-progress limit.
- Differential-review 3-round no-progress limit.
- Failure to keep security artifacts private.

All other local, reversible, AI-resolvable implementation choices are covered by standing authorization.
