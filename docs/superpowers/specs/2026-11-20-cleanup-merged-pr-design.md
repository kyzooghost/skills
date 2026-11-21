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
delete_merged_branch.py [--branch NAME] [--repo PATH]
```

- `--branch` defaults to the current branch at `--repo`.
- `--repo` defaults to the current directory.

The script takes a branch name only. `SKILL.md` resolves a PR number to its head branch before it calls the script.

### Resolution

- The main worktree is the first entry of `git worktree list --porcelain`. Every git command runs as `git -C <main worktree>` or `git -C <branch worktree>`.
- The branch worktree is the entry whose `branch` is `refs/heads/<branch>`, if any.
- The default branch comes from `gh repo view --json defaultBranchRef`.

### Checks

The script runs every check before it changes anything. On the first failed check, it exits `1`, prints `refused: <reason>` to stderr, and changes nothing.

1. The branch exists locally and is not the default branch.
2. If the branch is checked out in a worktree, `git status --porcelain --untracked-files=all` in that worktree is empty.
3. If the branch is in a linked worktree, every submodule git directory it owns is safe. This check is skipped for the main checkout, because `git switch` keeps submodule git directories. Git directories come from two sources:
   - a walk of `git rev-parse --git-path modules`, which includes nested and deinitialized submodules
   - `git rev-parse --absolute-git-dir` in each checked-out submodule, recursively, which includes embedded `.git` directories

   In each git directory, `refs/stash` must not exist and `git rev-list --exclude=refs/tags/* --all --not --remotes --tags` must be empty. This covers branches, the stash, and the HEAD of every worktree of that submodule. Tags count as safe because fetched release tags often point at commits that no remote branch contains, and a dependency is often checked out at such a tag. For example, a plain clone of `OpenZeppelin/openzeppelin-contracts` would otherwise refuse with 236 commits. Dirty submodule content is already caught by check 2, because `git status --ignore-submodules=none` reports it.
4. If the branch is in a linked worktree, no gitignored file in it matches a sensitive pattern. This check is skipped for the main checkout, because `git switch` keeps ignored files. Sensitive patterns:
   - `.env*`, except `.env.example`, `.env.sample`, and `.env.template`
   - `*.pem`, `*.key`, `*.p12`, `id_rsa*`
   - file names that contain `credential` or `secret`

   Matching ignores case. Paths with a `node_modules` or `site-packages` component are not matched, because they are package-manager output. Without this exemption, files such as viem's `createWebAuthnCredential.js` or certifi's `cacert.pem` refuse almost every JS or Python worktree.

   The script lists every ignored file with `git ls-files --others --ignored --exclude-standard`, without `--directory`, so a sensitive file inside an ignored directory is still found. It runs the same listing in each checked-out submodule, because `ls-files` does not descend into submodules and removal deletes their files too.

   `ls-files` prints an ignored nested git repository, such as a Foundry `lib/forge-std/` clone or an agent's `.worktrees/<name>`, as one entry with a trailing `/`. The script inspects each one with the same rules as the worktree itself: a clean status, no stash, no commits that are on no remote, safe submodules, and no sensitive ignored files, recursively. A clean clone of a remote does not block cleanup. A nested linked worktree of the same repository is refused with a request to remove it first with `git worktree remove`, because deleting it would leave stale worktree metadata.

   A deinitialized submodule path that still contains files is refused, because `git status` and `submodule foreach` cannot see those files.

   Other ignored paths, such as `node_modules/` or `dist/`, are regenerable. The script lists them in its output and does not block on them.
5. One of these conditions is true:
   - `gh pr list --head <branch> --state merged --json number,headRefOid` returns a PR, and the local branch tip equals its `headRefOid` or is an ancestor of it.
   - `git rev-list --count origin/<default>..<branch>` is `0`.

The tip comparison in check 5 prevents loss of commits made after the merge. A squash merge leaves branch commits off `main`, so the merged-PR state alone does not prove the local tip is on GitHub.

Check 3 is needed because a linked worktree keeps its submodule git directories under `.git/worktrees/<wt>/modules/`, and `git worktree remove --force` deletes them. That includes branches, stashes, and deinitialized submodules, not only the checked-out `HEAD`.

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

1. **Resolve the target.** Use the current branch, or the PR number or branch the user gives. Read the PR with `gh pr view --json number,url,state,headRefName,baseRefName,body,closingIssuesReferences`. If the PR is open, or closed without merge, stop and report. If the branch has no PR, use the branch the user named or the current branch, and skip step 5. The script's "no commits ahead" check then decides whether the branch can be deleted.
2. **Leave the worktree.** If cwd is inside the branch's worktree, `cd` to the main worktree first.
3. **Sync the default branch.** Resolve `<default>` with `gh repo view --json defaultBranchRef`, usually `main`. Run `git fetch --prune origin`. Then fast-forward local `<default>`:
   - If `<default>` is checked out, run `git -C <checkout> merge --ff-only origin/<default>`.
   - If not, run `git fetch origin <default>:<default>`.

   This step runs before deletion so the script's "no commits ahead" check uses fresh refs. If the fast-forward fails, record the reason and continue.
4. **Delete.** Run `delete_merged_branch.py` outside the sandbox, because the sandbox keeps `.git/worktrees` read-only. If the script refuses or prints `error:`, report its output and keep going with steps 5 and 6. An `error:` can follow a partial deletion, such as a removed worktree whose branch deletion failed; the agent still never deletes directly.
5. **Close issues.** GitHub links and closes issues from closing keywords only when the PR targets the default branch. For any other base, it ignores the keywords and creates no links. Classify each candidate issue by the PR's base:

   - **Base is `<default>`.** GitHub closes `closingIssuesReferences` issues on merge. An issue that is still open is certain only if `gh issue view <n> --json state,stateReason` does not show `REOPENED`. Close certain issues without asking. A reopened issue is uncertain, because someone chose to reopen it.
   - **Base is not `<default>`.** Collect issues from closing-keyword lines in the PR body (`Closes #N`, `Fixes #N`, `Resolves #N`, and their variants) and from `closingIssuesReferences`, which then holds only manual links. All are uncertain. When you ask, state that the change reached `<base>` but not `<default>`.
   - **Always uncertain:** bare `#N` mentions in the PR body or commit messages, and issue numbers in the branch name.

   Read each candidate's state with `gh issue view <n> -R <repo> --json state,stateReason`, because `closingIssuesReferences` holds no state. `<repo>` is the reference's repository, else the PR's, so a cross-repository reference such as `Closes acme/infra#7` is not confused with a local issue number. List all uncertain issues in one question and close only those the user confirms. Close each issue with:

   ```bash
   gh issue close <n> -R <repo> --reason completed --comment "Resolved by <PR url>"
   ```

6. **Report.** State:
   - the worktree and branch result, including deleted ignored paths, or the script's refusal or error
   - the default-branch sync result
   - issues closed by this run
   - issues already closed by GitHub
   - issues left open, with the reason. For a non-default base, the reason is "merged into `<base>`, not `<default>`". GitHub will not close these from this PR, so a later PR into `<default>` must reference them again.

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

### Skill

Follow `superpowers:writing-skills` RED-GREEN-REFACTOR.

1. Run baseline subagents without the skill:
   - The user says "PR merged, clean up". Safety Net blocks direct deletion.
   - The script refuses on a dirty worktree. The user says "just force it, I'm in a hurry".
2. Record the failures and rationalizations verbatim.
3. Write `SKILL.md` against those failures.
4. Rerun both scenarios with the skill. Close any new loophole and rerun.

## Decision ledger

### Human-owned decisions

- **Uncertain issues need the user.** Close an issue without asking only when its link to the merged change is certain. Ask in every other case. Report every closed issue at the end of the run.
- **Non-default base means ask.** For a PR merged into a branch other than the default branch, treat every candidate issue as uncertain, including `Closes #N` lines. The change has not reached the default branch, so closing can be premature.
- **One branch per run**, defaulting to the current branch.
- **Fast-forward only** for the default-branch sync. On failure, skip the sync, continue, and report.
- **Script owns only deletion** (approach A). The skill owns the PR lookup, sync, issues, and report.
- **Extra safety checks:** local tip must equal or precede the merged PR's `headRefOid`; submodules must have no unpushed commits; sensitive ignored files block deletion.

### Agent-owned decisions

- **Reopened issues are uncertain.** A still-open closing reference on a default-base PR with `stateReason` `REOPENED` was reopened by a person. Ask before closing it. This applies the uncertain-issue principle.
- **No PR means no issue step.** The script's "no commits ahead" check alone decides deletion.
- **No `--dry-run` flag.** No workflow step uses it, so it adds code and tests without value.
- **Full ignored-file listing.** List ignored files without `--directory`, so a sensitive file inside an ignored directory is still found.
- **Ignored-file check applies to linked worktrees only.** `git switch` in the main checkout keeps ignored files, so an `.env` there must not block cleanup.

### Deferred implementation decisions

- Exact closing-keyword regex and the commit-message scan: `writing-plans`.
- Fixture format for the stub `gh`: `writing-plans`.
- Wording of the baseline pressure scenarios: skill RED phase.

### Residual risks

- `stateReason` `REOPENED` is a valid `IssueStateReason` value (verified with GraphQL introspection on 2026-11-21).
- Check 3 trusts every remote-tracking ref in a submodule. A stale ref, left after a force-push or a remote branch deletion, can mark a commit as safe when no remote holds it. The skill fetches only the superproject. Accepted as a known limit.
- Check 3 ignores tags. A local-only tag on a submodule commit that no branch, stash, or worktree HEAD holds is lost on removal. Git does not create that state in normal work. Accepted by the user to avoid false refusals from fetched release tags.
- The `credential` and `secret` name rule can match build artifacts outside package directories, such as Foundry's `out/SecretStore.sol/SecretStore.json`. Cleanup is then refused until the user deletes the build output. Accepted, because users do keep real files in such directories.
- Listing every ignored file can be slow in a worktree with a very large `node_modules/`. Listing took 0.3 to 4 seconds on real repos with up to 207,674 ignored files. The 33-test suite takes about 50 seconds because each test builds real git repos.
