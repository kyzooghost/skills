# Stacked prep

Run this only when the user explicitly asks to stack on an open pull request and names it by number, URL, or branch. Do not publish from this file. Ignore `--base`.

## Update the standing pull request

Resolve the pull request:

```bash
gh pr view "$PR_REF" --json number,headRefName,url
```

Record `PR_NUMBER` and `PR_BRANCH` (`headRefName`). Fetch that branch. Leave the starting checkout unchanged.

```bash
git fetch origin "$PR_BRANCH"
```

Create a detached worktree at `<repo-parent>/create-pr-worktrees/stack-update-$PR_NUMBER` from `origin/$PR_BRANCH`. Do not check out the dirty local branch.

```bash
git worktree add --detach "$STACK_WORKTREE" "origin/$PR_BRANCH"
```

In that worktree, merge the remote default branch. Resolve `BASE` the same way `commands/create-pr.md` resolves the repository default, then:

```bash
git fetch origin "$BASE"
git merge "origin/$BASE" -m "merge: update with latest $BASE"
```

If Git reports already up to date, do not create an empty merge commit. If the merge conflicts, resolve the conflicts and commit that resolution. If the conflict cannot be resolved, stop in this worktree. Do not push a conflicted tree.

Push only that merge or conflict-resolution commit to the standing pull request. Do not push the user's unpushed commits or uncommitted files. Do not force-push.

```bash
git push origin "HEAD:refs/heads/$PR_BRANCH"
```

## Wait for the quality gate

Poll with:

```bash
gh pr view "$PR_NUMBER" --json statusCheckRollup,mergeStateStatus
```

There is no fixed poll timeout.

- `mergeStateStatus` of `DIRTY` is a merge conflict. Stop. Do not create the child branch. The user cannot override this stop.
- `mergeStateStatus` of `UNKNOWN` means GitHub is still calculating. Poll again.
- An empty `statusCheckRollup` on the first poll is not success. Poll again. If that later poll is still empty, the CI part of the gate is satisfied because no checks are configured.
- Read both check-run `conclusion` and commit-status `state`.
- A pass is `SUCCESS`, `SKIPPED`, or `NEUTRAL` on either field.
- A failure stop is `FAILURE`, `CANCELLED`, `TIMED_OUT`, `ACTION_REQUIRED`, or `ERROR` on either field.
- A `PENDING` `state` keeps polling.
- A missing `conclusion` is not automatically pending when `state` is already terminal.
- When the user explicitly asks to continue despite failing or pending checks, skip the CI wait. Still stop on `mergeStateStatus` `DIRTY`.

Do not auto-fix the standing pull request's CI.

## Create the child branch

Decide there is something to transplant before creating the child worktree. Use the same unpushed and uncommitted rules as `normal-prep.md`. If there is nothing to transplant, stop and do not create that worktree. There is nothing to publish.

Fetch `origin/$PR_BRANCH` again. Create the child branch from that updated remote head, in a new worktree at `<repo-parent>/create-pr-worktrees/<child-name>`.

Name the child from the transplanted changes, using the same kebab-case rule as `normal-prep.md`. Do not reuse the current branch name. Append `-2`, `-3`, and so on when the name exists.

Copy only the user's unpushed commits and uncommitted changes from the starting checkout. Use the same unpushed, untracked, cherry-pick, and copy rules as `normal-prep.md`. Do not stash or otherwise modify the starting checkout. If cherry-pick or copy conflicts, stop in the child worktree and do not open the pull request.

If the child worktree is dirty, run `/commit` there. Do not create an empty commit.

Push, then follow `commands/create-pr.md` in the child worktree as `/create-pr --skip-prep --base "$PR_BRANCH"`. Do not run normal prep again. Ignore any user-supplied `--base`.

```bash
git push --set-upstream origin "$BRANCH_NAME"
```
