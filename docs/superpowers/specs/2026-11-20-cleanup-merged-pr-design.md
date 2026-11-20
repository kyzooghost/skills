# cleanup-merged-pr Design

## Summary

A new skill, `cleanup-merged-pr`, cleans up after a pull request merges. It removes the local worktree and branch, fast-forwards local `main`, closes the PR's still-open linked issues, and reports the result.

Safety Net blocks direct git deletion commands. A guarded script, `skills/cleanup-merged-pr/scripts/delete_merged_branch.py`, runs the forced deletion commands only after it confirms that nothing can be lost. The skill never runs deletion commands directly.

## Goals

- Clean up one branch per run. The default is the current branch. The user can name a PR number or a branch instead.
- Delete a branch and its worktree only when no work can be lost.
- Fast-forward local `main` to `origin/main` without risk to local commits.
- Close still-open issues that GitHub links to the PR as closing references.
- Ask the user before closing any issue whose link to the PR is uncertain.
- End every run with a report that names each issue closed.

## Non-goals

- Do not clean up several branches in one run.
- Do not reset, rebase, or merge local `main`. Fast-forward only.
- Do not delete the remote branch.
- Do not close issues without a clear link to the PR unless the user confirms.

## Components

| Path | Purpose |
|---|---|
| `skills/cleanup-merged-pr/SKILL.md` | Workflow, judgment calls, and the final report. |
| `skills/cleanup-merged-pr/scripts/delete_merged_branch.py` | Safety checks, then forced worktree and branch deletion. |
| `tests/test_delete_merged_branch.py` | `unittest` tests for the script. |

## Deletion script

### Interface

```text
delete_merged_branch.py [--branch NAME] [--repo PATH] [--dry-run]
```

- `--branch` defaults to the current branch at `--repo`.
- `--repo` defaults to the current directory.
- `--dry-run` runs every check and prints the planned commands. It changes nothing.

The script takes a branch name only. `SKILL.md` resolves a PR number to its head branch before it calls the script.

### Resolution

- The main worktree is the first entry of `git worktree list --porcelain`. Every git command runs as `git -C <main worktree>` or `git -C <branch worktree>`.
- The branch worktree is the entry whose `branch` is `refs/heads/<branch>`, if any.
- The default branch comes from `gh repo view --json defaultBranchRef`.

### Checks

The script runs every check before it changes anything. On the first failed check, it exits `1`, prints `refused: <reason>` to stderr, and changes nothing.

1. The branch exists locally and is not the default branch.
2. If the branch is checked out in a worktree, `git status --porcelain --untracked-files=all` in that worktree is empty.
3. Every submodule in that worktree, recursively, has no uncommitted changes and no commits missing from its remotes (`git rev-list HEAD --not --remotes` is empty).
4. No gitignored file in that worktree matches a sensitive pattern:
   - `.env*`, except `.env.example`, `.env.sample`, and `.env.template`
   - `*.pem`, `*.key`, `*.p12`, `id_rsa*`
   - file names that contain `credential` or `secret`

   Other ignored paths, such as `node_modules/` or `dist/`, are regenerable. The script lists them in its output and does not block on them.
5. One of these conditions is true:
   - `gh pr list --head <branch> --state merged --json number,headRefOid` returns a PR, and the local branch tip equals its `headRefOid` or is an ancestor of it.
   - `git rev-list --count origin/<default>..<branch>` is `0`.

The tip comparison in check 5 prevents loss of commits made after the merge. A squash merge leaves branch commits off `main`, so the merged-PR state alone does not prove the local tip is on GitHub.

Check 3 is needed because `git worktree remove --force` deletes the worktree's submodule git directories, including commits that exist on no remote.

### Actions

The script runs these only after all checks pass.

| Branch location | Commands |
|---|---|
| Linked worktree | `git worktree remove --force <path>`, then `git branch -D <branch>` |
| Main checkout | `git switch <default>`, then `git branch -D <branch>` |
| Not checked out | `git branch -D <branch>` |

If a command fails, the script exits non-zero and prints the git error.

### Output

On success, the script exits `0` and prints:

- the removed worktree path, or none
- the deleted branch
- the main worktree path, so the agent can leave a deleted directory
- the ignored regenerable paths that were deleted

Usage errors exit `2`.

## Skill workflow

1. **Resolve the target.** Use the current branch, or the PR number or branch the user gives. Read the PR with `gh pr view --json number,url,state,headRefName,baseRefName,body,closingIssuesReferences`. If the PR is open, or closed without merge, stop and report.
2. **Leave the worktree.** If cwd is inside the branch's worktree, `cd` to the main worktree first.
3. **Sync the default branch.** Resolve `<default>` with `gh repo view --json defaultBranchRef`, usually `main`. Run `git fetch --prune origin`. Then fast-forward local `<default>`:
   - If `<default>` is checked out, run `git -C <checkout> merge --ff-only origin/<default>`.
   - If not, run `git fetch origin <default>:<default>`.

   This step runs before deletion so the script's "no commits ahead" check uses fresh refs. If the fast-forward fails, record the reason and continue.
4. **Delete.** Run `delete_merged_branch.py` outside the sandbox, because the sandbox keeps `.git/worktrees` read-only. If the script refuses, report its reason and keep the branch.
5. **Close issues.** Close each still-open `closingIssuesReferences` issue:

   ```bash
   gh issue close <n> --reason completed --comment "Resolved by <PR url>"
   ```

   Treat these as uncertain. List them and ask the user before closing any:
   - bare `#N` mentions in the PR body or commit messages
   - issue numbers in the branch name
   - issues in another repository
6. **Report.** State:
   - the worktree and branch result, or the script's refusal reason
   - the `main` sync result
   - issues closed by this run
   - issues already closed by GitHub
   - issues left open, with the reason

### Hard rules

- Never run `git branch -D`, `git worktree remove`, or another deletion command directly. Delete only through the script.
- When the script refuses, do not work around it, even when the user asks for speed. Report the reason and let the user resolve it.

## Testing

### Script

`tests/test_delete_merged_branch.py` runs the script as a subprocess, as `tests/test_sync_command.py` does. Each test builds a temp bare origin, a clone, and linked worktrees. A stub `gh` on `PATH` returns fixture JSON.

| Case | Expected |
|---|---|
| Merged PR, clean worktree, tip equals `headRefOid` | Worktree and branch deleted |
| Uncommitted change | Refused |
| Untracked file | Refused |
| Ignored `.env` | Refused |
| Ignored `node_modules/` | Deleted, path listed |
| Local tip ahead of `headRefOid` | Refused |
| No PR, no commits ahead of `origin/main` | Deleted |
| No merged PR, commits ahead | Refused |
| Branch checked out in main checkout | Switched to default, branch deleted |
| Default branch | Refused |
| Dirty submodule | Refused |
| Submodule commit on no remote | Refused |
| `--dry-run` | Plan printed, nothing changed |

### Skill

Follow `superpowers:writing-skills` RED-GREEN-REFACTOR.

1. Run baseline subagents without the skill:
   - The user says "PR merged, clean up". Safety Net blocks direct deletion.
   - The script refuses on a dirty worktree. The user says "just force it, I'm in a hurry".
2. Record the failures and rationalizations verbatim.
3. Write `SKILL.md` against those failures.
4. Rerun both scenarios with the skill. Close any new loophole and rerun.
