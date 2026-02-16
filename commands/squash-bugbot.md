# Claude Command: Squash Bugbot

This command triages unresolved bot review comments on a GitHub PR - assessing validity, proposing fixes, and optionally applying them or dismissing them.

## Usage

```
/squash-bugbot <PR_NUMBER>
```

`PR_NUMBER` is the GitHub pull request number to triage (required).

## What This Command Does

1. Resolves the GitHub `owner/repo` from the local git remote
2. Fetches all review comments and issue comments on the PR via `gh api`
3. Filters to unresolved bot comments only
4. For each bot comment, reads the referenced source code and assesses whether the concern is valid
5. Presents a consolidated report with verdicts and proposed fixes
6. Asks the user per-comment whether to apply fixes (valid), dismiss comments (invalid), or decide (uncertain)
7. Reports which files were modified at the end

## Step 1: Repo Resolution

Run `git remote get-url origin` to get the remote URL.

Parse `owner/repo` from the URL:
- HTTPS format: `https://github.com/owner/repo.git` - extract between `github.com/` and `.git`
- SSH format: `git@github.com:owner/repo.git` - extract between `:` and `.git`
- Handle URLs with or without the trailing `.git`

If no origin remote exists, stop with: "Error: no git origin remote found. This command requires a GitHub remote."

## Step 2: Comment Fetching

Fetch both comment types in parallel:
- Review comments: `gh api repos/{owner}/{repo}/pulls/{PR_NUMBER}/comments`
- Issue comments: `gh api repos/{owner}/{repo}/issues/{PR_NUMBER}/comments`

### Bot Detection

A comment is from a bot if either condition is true:
- `author.type == "Bot"` (the `user.type` field in the API response)
- Username matches a known bot: `github-actions[bot]`, `coderabbitai`, `cursor[bot]`, `copilot`, `sonarcloud[bot]`, `codecov[bot]`, `dependabot[bot]`

### Filtering to Unresolved

For review comments: include only comments where the thread is not resolved. A top-level review comment has `in_reply_to_id` as null - these start threads. Skip comments in threads that have been explicitly resolved.

For issue comments: include all bot comments (issue comments have no resolution mechanism).

If zero bot comments remain after filtering, report "No unresolved bot comments found on PR #{PR_NUMBER}" and exit.

## Step 3: Assessment

For each bot comment:
1. Read the comment body to understand the bot's concern
2. Identify the file and line the comment references (from `path` and `line`/`original_line` fields for review comments; for issue comments, parse file references from the comment body if present)
3. Use the Read tool to read the actual source code at that location
4. Assess whether the bot's concern is a real issue in the current code
5. Categorize as one of:
   - **Valid** - the bot identified a real problem
   - **Invalid** - the bot's concern does not apply (false positive, already handled, or outdated)
   - **Uncertain** - cannot determine without more context

## Step 4: Report

Present a consolidated summary. For each comment, show:

```
### [BotName] - {verdict}
**File:** `path/to/file.ts` L{line}
**Comment:** [link to GitHub comment]
**Concern:** {one-line summary of what the bot flagged}
**Verdict:** {Valid/Invalid/Uncertain} - {reasoning}
**Proposed fix:** {concrete code change if valid or uncertain, or "N/A" if invalid}
```

## Step 5: Actions

After presenting the report, go through each comment and ask the user what to do:

- **Valid comments**: Ask "Apply this fix?" If yes, edit the file with the proposed fix using the Edit tool. Do NOT commit - leave changes unstaged.
- **Invalid comments**: Ask "Dismiss this comment on the PR?" If yes:
  - For review comments: reply to the thread via `gh api` with a brief dismissal message explaining why the concern does not apply
  - For issue comments: reply via `gh api` with the same dismissal message
- **Uncertain comments**: Ask the user whether to treat as valid or invalid, then proceed accordingly

At the end, report:
- Which files were modified (if any)
- Which comments were dismissed (if any)
- Any comments the user skipped

## Error Handling

- `git remote get-url origin` fails: stop with "Error: no git origin remote found. This command requires a GitHub remote."
- `gh` CLI not installed or not authenticated: stop with "Error: `gh` CLI is not available or not authenticated. Run `gh auth login` first."
- PR not found (404): stop with "Error: PR #{PR_NUMBER} not found in {owner}/{repo}."
- File referenced by a comment does not exist locally: flag in the report as "File not found locally - skipping fix" and continue with the next comment

## Important Notes

- This command never auto-commits. All file edits are left for the user to review and commit.
- Only bot comments are processed. Human review comments are ignored.
- The assessment uses the current local source code, not the PR diff - ensure your branch is up to date.
