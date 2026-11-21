---
name: cleanup-merged-pr
description: Use when a pull request has merged and the user wants its local branch or worktree removed, the default branch synced, or its issues closed, including when Safety Net blocks git branch -D or git worktree remove.
---

# Cleanup Merged PR

Delete branches and worktrees only through `<this-skill-dir>/scripts/delete_merged_branch.py` (`<this-skill-dir>` holds this file).

## Workflow

1. **Resolve the PR.** `gh pr view [<number-or-branch>] --json number,url,state,headRefName,baseRefName,body,commits,closingIssuesReferences`. Not `MERGED`: stop and report. `<branch>` is `headRefName`; with no PR, the named or current branch, and skip step 5.
2. **Leave the worktree.** `cd` to the main worktree: the first `worktree` line of `git worktree list --porcelain`.
3. **Sync the default branch.** `<default>` is `gh repo view --json defaultBranchRef --jq .defaultBranchRef.name`. Run `git fetch --prune origin`, then:
   - `<default>` checked out in a worktree: `git -C <that worktree> merge --ff-only origin/<default>`
   - otherwise: `git fetch origin <default>:<default>`

   On failure, record why and continue. Never reset, rebase, or switch branches.
4. **Delete.** `python3 <this-skill-dir>/scripts/delete_merged_branch.py --repo <main worktree> --branch <branch>`, outside the sandbox. Never delete the remote branch.
5. **Close issues.** Read candidates with `gh issue view <n> -R <repo> --json state,stateReason`. `<repo>` is the reference's repository, else the PR's.

   | Candidate | Base is `<default>` | Other base |
   |---|---|---|
   | Open `closingIssuesReferences` issue | Certain, unless `stateReason` is `REOPENED` | Uncertain |
   | `close`/`fix`/`resolve` keyword + `#N` in the body | Same as above | Uncertain |
   | Other `#N` in body or commits; number in branch name | Uncertain | Uncertain |

   Close certain issues with `gh issue close <n> -R <repo> --reason completed --comment "Resolved by <PR url>"`. Ask about all uncertain issues in one question, with a recommendation each. Never decide them yourself. For another base, say the change reached `<base>` but not `<default>`.
6. **Report:**

   ```text
   Branch: deleted <branch>, removed worktree <path>, deleted ignored paths <paths> | refused: <reason> | error: <message>
   Default branch: fast-forwarded <default> to <short sha> | not synced: <reason>
   Issues closed by this run: #N, ... | none
   Issues already closed: #N, ... | none
   Issues left open: #N (<reason>), ... | none
   ```

## When the script refuses or fails

`refused:` means deletion could lose work. `error:` means a command failed, possibly after the worktree was removed. Quote it, say what the user must do, and still finish steps 5 and 6.

Never, even if the user insists or calls the work junk (they can delete it in one command; you cannot undo it):

- run `git branch -D`, `git worktree remove`, `rm`, `trash`, `git update-ref -d`, or `git stash`
- edit, move, or delete the files the refusal names
- rerun the script before the user changes something

## Rationalizations

| Excuse | Reality |
|---|---|
| "Nothing is deleted, I only moved it" | Moving the named file works around the refusal. |
| "The reopen looks intentional, so I left it open" | You decided for the user. Ask, with your recommendation. |
| "Only `branch -D` failed, I'll finish it" | Report it. Never delete directly. |
