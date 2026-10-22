# Claude Command: Fix CI

This command diagnoses and fixes CI failures on a GitHub PR by analyzing GitHub Actions logs, proposing fixes, applying them automatically, and pushing a commit to the PR branch.

## Usage

```
/fix-ci           # Auto-detect PR from current branch
/fix-ci 123       # Specify PR number explicitly
```

## What This Command Does

1. Resolves the GitHub `owner/repo` from the local git remote
2. Resolves the PR (from argument or current branch)
3. Fetches CI check runs for the PR's head commit
4. Filters to failed checks only
5. Downloads and analyzes failure logs
6. Presents a consolidated diagnosis report
7. Applies all proposed fixes automatically
8. Commits the applied fixes and pushes them to the PR branch

## Step 1: Repo Resolution

Run `git remote get-url origin` to get the remote URL.

Parse `owner/repo` from the URL:
- HTTPS format: `https://github.com/owner/repo.git` - extract between `github.com/` and `.git`
- SSH format: `git@github.com:owner/repo.git` - extract between `:` and `.git`
- Handle URLs with or without the trailing `.git`

If no origin remote exists, stop with: "Error: no git origin remote found. This command requires a GitHub remote."

## Step 2: PR Resolution

If a PR number was provided as an argument, use it directly.

Otherwise, detect from current branch:
```bash
gh pr list --head $(git branch --show-current) --json number,url --jq '.[0]'
```

Behavior:
- If PR number provided but PR doesn't exist: stop with "Error: PR #{PR_NUMBER} not found in {owner}/{repo}."
- If no argument and no PR for current branch: stop with "Error: no PR exists for current branch. Specify a PR number: `/fix-ci 123`"
- Resolve and record the PR head branch and head repository
- If the checked-out local branch does not match the PR head branch, stop before editing files and ask the user to check out the PR branch
- Otherwise: proceed with the resolved PR number

## Step 3: Fetch CI Status

Get the PR's head commit SHA:
```bash
gh pr view {PR_NUMBER} --json headRefOid --jq '.headRefOid'
```

Fetch check runs for that commit:
```bash
gh api repos/{owner}/{repo}/commits/{SHA}/check-runs --paginate
```

Filter to failures only:
- `status == "completed"` AND
- `conclusion == "failure"` OR `conclusion == "timed_out"`

Exit conditions:
- All checks passing: "All CI checks are passing on PR #{PR_NUMBER}. Nothing to fix."
- Checks still running (any with `status != "completed"`): "CI checks are still running on PR #{PR_NUMBER}. Wait for completion or re-run when ready."
- No check runs found: "No CI checks found for PR #{PR_NUMBER}."

## Step 4: Fetch and Analyze Logs

For each failed check run, fetch the logs.

**For GitHub Actions jobs:**
```bash
gh run view {run_id} --log-failed
```

If that fails, try fetching via API:
```bash
gh api repos/{owner}/{repo}/actions/jobs/{job_id}/logs
```

**Log analysis:**

Parse logs for common failure patterns:

| Pattern Type | Indicators |
|--------------|------------|
| Build errors | `error:`, `Error:`, `FAILED`, `BUILD FAILURE`, `Cannot find module` |
| Type errors | `TS\d+:`, `TypeError`, `Type .* is not assignable` |
| Test failures | `FAIL`, `AssertionError`, `Expected`, `✗`, `✘` |
| Lint errors | `warning:`, `error:`, ESLint/Prettier output patterns |
| Timeout | Check run conclusion is `timed_out` |

**Extract from errors:**
- File paths and line numbers (e.g., `src/file.ts:42:10`)
- Error messages
- Stack traces (for test failures)

**Read referenced files:**
For each file path extracted, use the Read tool to get the current local code for context.

If a referenced file doesn't exist locally: "Warning: {file} not found locally. Ensure branch is up to date."

## Step 5: Generate Diagnosis Report

For each failure, analyze the error and propose a fix. Present a consolidated report:

```
## CI Failure Report for PR #123

Found {N} failing check(s).

### 1. {Job Name} - {failure type}
**Error:**
{error message snippet - max 10 lines}

**File:** `path/to/file.ts` L{line} (if identifiable)
**Diagnosis:** {root cause analysis - what went wrong and why}
**Proposed Fix:** {concrete description of the code change}
**Confidence:** {High|Medium|Low}

---

### 2. {Job Name} - {failure type}
...
```

**Failure types and fix strategies:**

| Type | Fix Strategy |
|------|--------------|
| Lint error | Edit source file to fix the specific violation |
| Type error | Fix type mismatch, add type annotation, or fix logic |
| Test failure | Fix the test assertion or fix the code under test |
| Build error | Fix syntax errors, missing imports, or dependency issues |
| Workflow error | Edit `.github/workflows/*.yml` to fix configuration |
| Timeout | Suggest optimization; may require manual investigation |

**Confidence levels:**
- **High**: Clear error message pointing to specific fix
- **Medium**: Error is clear but fix requires some inference
- **Low**: Error is ambiguous or fix is uncertain

## Step 6: Apply Fixes

After presenting the report, apply every proposed fix automatically. Do not ask the user to approve each fix.

**For each applied fix:**
1. Use the Edit tool to make the change
2. Track the file as modified

If a fix cannot be applied cleanly, leave it unapplied, record why, and continue with the other fixes. Apply low-confidence fixes automatically, but flag them in the report and summary.

If diagnosis confidence was "Low", include: "Note: This fix has low confidence. Review it carefully."

## Step 7: Commit and Push to the PR Branch

After processing all fixes, show a summary:

```
## Summary

Applied: {N} fix(es)
Not applied: {M} fix(es)

Modified files:
- path/to/file1.ts
- path/to/file2.ts
- .github/workflows/ci.yml
```

If at least one fix was applied:
1. Confirm the checked-out branch is the resolved PR head branch and the configured push remote targets the PR head repository. If either check fails, stop before committing and report the issue.
2. Stage only the files modified by this command: `git add {files}`
3. Create a commit with message: `fix(ci): resolve CI failures`
4. Push the commit to the PR head repository and branch without asking for confirmation.
5. Report whether the commit and push succeeded. If pushing fails, report that the commit remains local and include the push error.

**If no fixes were applied:**
1. Skip the commit and push
2. Report: "No fixes were applied."

## Error Handling

| Condition | Message |
|-----------|---------|
| No git origin remote | "Error: no git origin remote found. This command requires a GitHub remote." |
| `gh` CLI not available | "Error: `gh` CLI is not available or not authenticated. Run `gh auth login` first." |
| PR not found (404) | "Error: PR #{PR_NUMBER} not found in {owner}/{repo}." |
| No PR for current branch | "Error: no PR exists for current branch. Specify a PR number: `/fix-ci 123`" |
| Local branch does not match the PR head branch | Stop before editing and report the expected PR branch. |
| No push remote targets the PR head repository | Stop before committing and report that the PR head remote is unavailable. |
| All checks passing | "All CI checks are passing on PR #{PR_NUMBER}. Nothing to fix." |
| Checks still running | "CI checks are still running on PR #{PR_NUMBER}. Wait for completion or re-run when ready." |
| No check runs found | "No CI checks found for PR #{PR_NUMBER}." |
| Log fetch fails | "Warning: could not fetch logs for {job_name}. Skipping." (continue with others) |
| File not found locally | "Warning: {file} not found locally. Ensure branch is up to date." (skip that fix) |
| Cannot diagnose failure | Include in report: "Diagnosis: Unable to determine root cause from logs. Manual investigation needed." |

## Ground Rules

- Always analyze ALL failed checks before presenting the report
- Automatically apply all proposed fixes without asking for confirmation
- Automatically commit applied fixes and push them to the resolved PR head branch
- Verify the local branch and push remote match the PR head before pushing
- If a fix cannot be determined, include it in the report with "Manual investigation needed"
- Match existing code style when proposing fixes
- For test failures, prefer fixing the code under test over modifying tests (unless the test itself is wrong)
- For workflow errors, be conservative - prefer minimal changes to CI configuration
