# /create-pr Branch Prep Design

## Summary

A new pull request started by the user is prepared on a fresh branch before publish. Prep copies unpushed commits and uncommitted changes onto that branch. The checkout where `/create-pr` started is left unchanged.

`skills/create-pr/SKILL.md` chooses the path. Each prep path has its own reference. Every path then follows the existing publish command.

## Goals

- Start a user-requested new pull request from the remote default branch, even when the current checkout is on another branch.
- Transplant only unpushed commits and uncommitted changes.
- When the user explicitly stacks on an open pull request, make that pull request's updated remote head the base, after it contains the latest default branch and is green.
- Keep `--update` and `ship-from-plan` on today's publish path.

## Non-goals

- Do not change publish behavior for `/create-pr --update`.
- Do not add branch prep to `ship-from-plan`.
- Do not move or delete commits or uncommitted files in the starting checkout.
- Do not auto-fix a standing pull request's failed CI.
- Do not repeat publish steps inside the prep references.

## Decision

`skills/create-pr/SKILL.md` is the router. It keeps the existing sensitive-content rule, then chooses exactly one path:

1. **Skip prep.** The invocation includes `--update` or `--skip-prep`. Read no prep reference.
2. **Stacked prep.** The user explicitly named an open pull request to stack on, by number, URL, or branch. Read and follow `skills/create-pr/references/stacked-prep.md`.
3. **Normal prep.** Every other new pull request. Read and follow `skills/create-pr/references/normal-prep.md`.

After that path finishes, follow `commands/create-pr.md` for diff, description, documentation check, preview, sensitive-content scrub, and `gh pr create` or `gh pr edit`. `--draft` and an explicit `--base` stay on that shared path. `skills/create-pr/references/command.md` remains the symlink to `commands/create-pr.md`.

`ship-from-plan` adds `--skip-prep` to its `/create-pr` invocation. It does not otherwise change.

## What is copied

Prep reads the starting checkout and writes into a new worktree.

Copied:

- Unpushed commits on the current branch: commits reachable from `HEAD` that are not on its upstream. If the branch has no upstream, the set is the commits not on `origin/BASE`.
- Uncommitted changes in that checkout: staged files, unstaged files, and untracked files.

Left in the starting checkout:

- Commits already on the current branch's upstream.
- The starting branch, its commits, and its uncommitted files.

`BASE` is the repository's remote default branch. The command resolves it the same way `/create-pr` already resolves the default.

## Branch name

The new branch name describes the transplanted changes. It does not reuse the current branch name.

Prep reads the unpushed commits and the uncommitted diff, then chooses a short kebab-case name that states what those changes do. Example: `fix-ready-pr-default`. If that name already exists, prep appends `-2`, `-3`, and so on until the name is free.

## Normal prep

1. Fetch `origin/BASE`.
2. Create a new worktree and branch at `origin/BASE`.
3. Cherry-pick the unpushed commits onto that branch, in order.
4. Copy staged, unstaged, and untracked changes into the new worktree. Do not stash, reset, or otherwise modify the starting checkout.
5. If any cherry-pick or copy conflicts, stop in the new worktree. Do not open the pull request.
6. If the new worktree still has uncommitted changes, run `/commit` there. If the transplant was only commits and the worktree is clean, do not create an empty commit.
7. If there are no unpushed commits and no uncommitted changes, stop. There is nothing to publish.
8. Continue with the shared publish steps in the new worktree. The pull request base is `BASE`. An explicit `--base` replaces `BASE`.

## Stacked prep

This path runs only when the user explicitly asks to stack on an open pull request.

1. Resolve that pull request by number, URL, or branch.
2. Check out that pull request's branch in its own worktree. Leave the starting checkout unchanged.
3. Merge `origin/BASE` into that branch.
4. Push a clean merge. When the merge conflicts, resolve the conflicts, commit the resolution, and push that commit to the standing pull request. Do not push the user's unpushed commits or uncommitted files there.
5. If the conflict cannot be resolved, stop in that worktree. Do not push a conflicted tree.
6. Poll GitHub until every required check on that pushed head reaches a terminal state and GitHub reports no merge conflict. There is no fixed poll timeout. Pending checks keep polling. If no required checks are configured, the CI part of the gate is satisfied. If a required check fails, stop. Do not create the child branch. Do not auto-fix the standing pull request.
7. Create the new branch from the standing pull request's updated remote head. Name it from the transplanted changes, using the branch-name rule above.
8. Copy only the user's unpushed commits and uncommitted changes. Run `/commit` in that worktree when it is dirty.
9. Continue with the shared publish steps. The pull request base is the standing pull request's branch. Do not let `--base` point the stacked pull request at a different branch.

## Stop conditions

Prep stops and does not open the pull request when:

- The transplant has no unpushed commits and no uncommitted changes.
- A cherry-pick or file copy conflicts.
- A stacked merge cannot be resolved.
- The standing pull request's required checks fail, or GitHub still reports a merge conflict after the push.
- `origin` is missing, or the named standing pull request cannot be resolved.

A conflict stop leaves the prep worktree in place. The starting checkout stays unchanged.

## Tests

Extend `tests/test_create_pr_command.py` so it checks that:

- `skills/create-pr/SKILL.md` contains the three-way decision and both reference names.
- `skills/create-pr/references/normal-prep.md` and `skills/create-pr/references/stacked-prep.md` exist and do not contain `gh pr create`.
- `commands/create-pr.md` still documents `--skip-prep`, `--update`, and `--draft`.
- `skills/ship-from-plan/SKILL.md` passes `--skip-prep` on its `/create-pr` invocation.
