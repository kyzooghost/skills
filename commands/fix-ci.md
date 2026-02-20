# Claude Command: Fix CI

This command diagnoses and fixes CI failures on a GitHub PR by analyzing GitHub Actions logs, proposing fixes, and applying them with user approval.

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
7. Walks through each proposed fix with user approval
8. Optionally commits the applied fixes

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

After presenting the report, walk through each proposed fix:

```
### Applying Fix 1 of {N}: {Job Name}

**Proposed change to `path/to/file.ts`:**
{show diff preview of the proposed edit}

Apply this fix? (y/n/s)
```

**User responses:**
- `y` or `yes`: Apply the fix using the Edit tool
- `n` or `no`: Skip this fix
- `s` or `skip`: Same as no

**For each applied fix:**
1. Use the Edit tool to make the change
2. Track the file as modified

**For skipped fixes:**
1. Note as skipped in the summary
2. Continue to next fix

If diagnosis confidence was "Low", remind the user: "Note: This fix has low confidence. Review carefully before applying."

## Step 7: Summary and Commit

After processing all fixes, show a summary:

```
## Summary

Applied: {N} fix(es)
Skipped: {M} fix(es)

Modified files:
- path/to/file1.ts
- path/to/file2.ts
- .github/workflows/ci.yml

Commit these changes? (y/n)
```

**If user says yes:**
1. Stage all modified files: `git add {files}`
2. Create commit with message: `fix(ci): resolve CI failures`
3. Report: "Changes committed. Run `git push` to update the PR."
4. Do NOT auto-push

**If user says no:**
1. Leave files modified but unstaged
2. Report: "Changes left unstaged for your review."

**If no fixes were applied:**
1. Skip the commit prompt
2. Report: "No fixes were applied."

## Error Handling

| Condition | Message |
|-----------|---------|
| No git origin remote | "Error: no git origin remote found. This command requires a GitHub remote." |
| `gh` CLI not available | "Error: `gh` CLI is not available or not authenticated. Run `gh auth login` first." |
| PR not found (404) | "Error: PR #{PR_NUMBER} not found in {owner}/{repo}." |
| No PR for current branch | "Error: no PR exists for current branch. Specify a PR number: `/fix-ci 123`" |
| All checks passing | "All CI checks are passing on PR #{PR_NUMBER}. Nothing to fix." |
| Checks still running | "CI checks are still running on PR #{PR_NUMBER}. Wait for completion or re-run when ready." |
| No check runs found | "No CI checks found for PR #{PR_NUMBER}." |
| Log fetch fails | "Warning: could not fetch logs for {job_name}. Skipping." (continue with others) |
| File not found locally | "Warning: {file} not found locally. Ensure branch is up to date." (skip that fix) |
| Cannot diagnose failure | Include in report: "Diagnosis: Unable to determine root cause from logs. Manual investigation needed." |

## Ground Rules

- Always analyze ALL failed checks before presenting the report
- Never auto-apply fixes without user confirmation
- Never auto-push to remote
- If a fix cannot be determined, include it in the report with "Manual investigation needed"
- Match existing code style when proposing fixes
- For test failures, prefer fixing the code under test over modifying tests (unless the test itself is wrong)
- For workflow errors, be conservative - prefer minimal changes to CI configuration
