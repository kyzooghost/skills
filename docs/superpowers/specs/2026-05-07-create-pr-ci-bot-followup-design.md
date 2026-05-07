# /create-pr CI and Bot Follow-up Design

## Summary

Update `commands/create-pr.md` so `/create-pr` does not stop immediately after creating or updating a PR. The command should monitor CI to completion, use a self-contained CI failure flow when checks fail, and check for unresolved bot comments only after CI is green.

## Goals

- Add post-PR follow-up steps directly to `commands/create-pr.md`.
- Keep the instructions self-contained, without requiring the reader to jump to `/fix-ci` or `/squash-bugbot`.
- Use separate steps for CI monitoring and bot comment checks.
- Stop with a report if unresolved bot comments exist.

## Non-goals

- Do not change `commands/fix-ci.md`.
- Do not change `commands/squash-bugbot.md`.
- Do not make `/create-pr` triage, fix, dismiss, reply to, or resolve bot comments.
- Do not auto-push CI fixes.

## Command Flow

### Step 7: Monitor CI

After PR creation or update, the command should fetch the PR head commit SHA, poll check runs until every check completes, and classify the final result.

If all checks pass, proceed to Step 8.

If any check fails or times out, the command should run a compact CI-fix flow:

1. Fetch failed check runs for the PR head commit.
2. Download failed logs with `gh run view {run_id} --log-failed`, falling back to the jobs logs API when needed.
3. Analyze all failures before presenting a report.
4. Include job name, failure type, relevant error snippet, file and line when identifiable, diagnosis, proposed fix, and confidence.
5. Ask before applying each proposed fix.
6. After processing fixes, show a summary and ask whether to commit applied changes with `fix(ci): resolve CI failures`.
7. Never auto-push. If changes are committed, report that the user should push to update the PR.

If checks are still running, the command keeps monitoring rather than stopping early. If no check runs are found, it reports that no CI checks were found and stops because readiness cannot be verified.

### Step 8: Check Bot Comments

Only run this step when CI is green.

The command should fetch bot comments using three data sources:

1. Review comments from `gh api repos/{owner}/{repo}/pulls/{PR_NUMBER}/comments --paginate`.
2. Issue comments from `gh api repos/{owner}/{repo}/issues/{PR_NUMBER}/comments --paginate`.
3. Review threads from GraphQL, including `isResolved`, thread node `id`, and every thread comment `databaseId`.

Review comments are unresolved only when their REST `id` joins to a GraphQL thread comment `databaseId` whose thread has `isResolved == false`. Bot detection uses the REST `user.type == "Bot"` field or known bot logins such as `github-actions[bot]`, `coderabbitai`, `cursor[bot]`, `copilot`, `sonarcloud[bot]`, `codecov[bot]`, and `dependabot[bot]`.

Issue comments have no resolution mechanism, so all bot issue comments are included in the report.

If unresolved bot comments exist, stop and report:

- Bot name
- Review or issue comment type
- File and line when available
- GitHub comment link
- One-line concern summary when it can be safely summarized

The command must not assess validity, apply fixes, dismiss comments, reply to comments, or resolve review threads.

### Step 9: Final Status

If CI is green and no unresolved bot comments exist, report that the PR is ready for human review.

## Error Handling

- If `gh` is unavailable or unauthenticated, stop with the existing `gh auth login` guidance.
- If PR metadata cannot be fetched after creation or update, show the underlying `gh` error and stop.
- If check-run polling cannot determine a final status, stop with the last known check status.
- If bot comment fetching partially fails, report which source failed and stop rather than claiming there are no bot comments.

## Testing

This is a documentation-only command update. Verification should include:

- Confirm numbered steps stay coherent after adding Steps 7 through 9.
- Confirm the new steps do not rely on cross-links to other command files.
- Confirm the bot-comment path stops with a report only.
- Confirm no em dash characters were introduced.
