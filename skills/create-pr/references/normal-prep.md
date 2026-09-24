# Normal prep

Run this in the starting checkout. Do not publish from this file.

## Select the start ref

Resolve `BASE` with the repository default branch lookup already in `commands/create-pr.md` (`gh repo view` `defaultBranchRef.name`).

An explicit `--base <branch>` replaces `BASE` for both the new branch and the pull request. When `--base` is omitted, both use that default. Fetch it:

```bash
git fetch origin "$BASE"
```

Record `START_REF=origin/$BASE` and `PR_BASE="$BASE"`.

## Select the transplant

Record `SOURCE` as `git rev-parse --show-toplevel` and `SOURCE_HEAD` as `git rev-parse HEAD`.

Unpushed commits are `git rev-list --reverse @{upstream}..HEAD` when the current branch has an upstream. When it has no upstream, they are the commits not on `origin/BASE`: `git rev-list --reverse origin/$BASE..HEAD`.

Uncommitted changes are staged files, unstaged files, and untracked files that Git does not ignore. List ignored-excluded untracked files with:

```bash
git ls-files --others --exclude-standard
```

If that commit list is empty and `git status --porcelain=v1 -unormal` is empty, stop. There is nothing to publish. Do not create a worktree.

## Name and create the branch

Read the unpushed commits and the uncommitted diff. Choose a short kebab-case branch name that states what those changes do. Do not reuse the current branch name. Example: `fix-ready-pr-default`.

If `refs/heads/<name>` or `refs/remotes/origin/<name>` exists, append `-2`, then `-3`, and so on until the name is free.

Create a worktree at `<repo-parent>/create-pr-worktrees/<name>` from `START_REF`:

```bash
mkdir -p "$(dirname "$WORKTREE")"
git worktree add -b "$BRANCH_NAME" "$WORKTREE" "$START_REF"
```

Do not stash, reset, checkout, or commit in the starting checkout.

## Transplant

In the new worktree, cherry-pick the unpushed SHAs in order:

```bash
git cherry-pick $UNPUSHED_SHAS
```

Skip that command when the SHA list is empty. If cherry-pick conflicts, stop in the new worktree. Do not open the pull request. Do not modify the starting checkout.

Copy the uncommitted tracked diff with `git -C "$SOURCE" diff HEAD` and `git apply` inside the worktree. Copy non-ignored untracked files from `SOURCE` into the worktree with their relative paths. If the copy or apply conflicts, stop in the new worktree. Do not open the pull request.

If the worktree is dirty, run `/commit` there. If the transplant was only commits and the worktree is clean, do not create an empty commit.

## Hand off

Push the new branch, then continue with `commands/create-pr.md` in the new worktree. The pull request base is `PR_BASE`.

```bash
git push --set-upstream origin "$BRANCH_NAME"
```
