---
name: cleanup-merged-pr
description: Use when a pull request has merged and the user wants its local branch or worktree removed, the default branch synced, or its issues closed, including when Safety Net blocks git branch -D or git worktree remove.
---

# Cleanup Merged PR

Delete a merged branch and its worktree only through `scripts/delete_merged_branch.py` in this skill's directory. It deletes only after it proves no work can be lost.

## Workflow

1. **Resolve the PR.** `gh pr view [<number-or-branch>] --json number,url,state,headRefName,baseRefName,body,commits,closingIssuesReferences`. Not `MERGED`: stop and report. No PR: skip step 5.
2. **Leave the worktree.** `cd` to the main worktree: the first `worktree` line of `git worktree list --porcelain`.
3. **Sync the default branch.** `<default>` is `gh repo view --json defaultBranchRef --jq .defaultBranchRef.name`. Run `git fetch --prune origin`, then:
   - `<default>` checked out in a worktree: `git -C <that worktree> merge --ff-only origin/<default>`
   - otherwise: `git fetch origin <default>:<default>`

   On failure, record the error and continue. Never reset, rebase, or switch branches.
4. **Delete.** `python3 <skill dir>/scripts/delete_merged_branch.py --repo <main worktree> --branch <headRefName>`, outside the sandbox. Never delete the remote branch.
5. **Close issues.**

   | Candidate | Base is `<default>` | Other base |
   |---|---|---|
   | Open `closingIssuesReferences` issue | Certain, unless `stateReason` is `REOPENED` | Uncertain |
   | `close`/`fix`/`resolve` keyword + `#N` in the body | Same as above | Uncertain |
   | Other `#N` in body or commits; number in branch name | Uncertain | Uncertain |

   Close certain issues with `gh issue close <n> --reason completed --comment "Resolved by <PR url>"`. Never decide uncertain issues yourself: ask about all of them in one question, with a recommendation for each. For another base, say the change reached `<base>` but not `<default>`.
6. **Report:**

   ```text
   Branch: deleted <branch>, removed worktree <path> | refused: <reason>
   Default branch: fast-forwarded <default> to <short sha> | not synced: <reason>
   Issues closed by this run: #N, ... | none
   Issues already closed: #N, ... | none
   Issues left open: #N (<reason>), ... | none
   ```

## When the script refuses

`refused: <reason>` means deletion could lose work. Quote the reason, say what the user must do, and still finish steps 5 and 6.

Never, even if the user insists or calls the work junk:

- run `git branch -D`, `git worktree remove`, `rm`, `trash`, `git update-ref -d`, or `git stash`
- edit, move, or delete the files the refusal names
- rerun the script before the user changes something

## Rationalizations

| Excuse | Reality |
|---|---|
| "Nothing is deleted, I only moved it" | Moving the named file works around the refusal. The user decides where their files go. |
| "The user said it's junk" | They can delete it with one command. You cannot undo a deletion. |
| "The reopen looks intentional, so I left it open" | You decided for the user. Ask, with your recommendation. |
