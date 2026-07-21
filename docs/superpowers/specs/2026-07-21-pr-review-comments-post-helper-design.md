# Deterministic PR Review Comment Posting Helper

## Context

The `pr-review-comments` workflow posts Markdown bodies through `gh api`. Shell-built bodies can
execute Markdown backticks as command substitutions or leave placeholder URLs in companion comments.
The workflow needs a deterministic posting boundary that preserves the approved rendered bodies and
verifies GitHub's responses.

## Design

Add `skills/pr-review-comments/scripts/post_review_comments.py`, a Python standard-library CLI driven
by a JSON spec file:

```json
{
  "repo": "owner/repository",
  "pr": 29,
  "commit": "sha",
  "primary": {
    "path": "src/Primary.kt",
    "line": 43,
    "body": "..."
  },
  "companions": [
    {
      "path": "src/Companion.kt",
      "line": 27,
      "body": "...\\n\\nSee primary comment: {primary_url}"
    }
  ]
}
```

The CLI performs these steps:

1. Parse and validate the JSON spec before any GitHub mutation.
2. Reject unsafe or unresolved companion placeholders, including `$primary_url` and angle-bracket
   primary-link placeholders; require exactly one `{primary_url}` token in each companion body.
3. With `--dry-run`, print the validated targets and stop before invoking `gh`.
4. Post the primary through `subprocess.run` with an argument list, never a shell command string.
5. Require the primary response to contain a real `html_url`, and verify the returned body, path, and
   line match the submitted comment.
6. Substitute the captured URL into each companion, post companions in spec order, and verify each
   response body, path, line, and primary footer before posting the next companion.
7. Stop on the first failure. The helper does not attempt destructive rollback because GitHub review
   comments cannot be safely rolled back by this workflow.

The `gh` boundary is injectable as a runner in unit tests. Tests use deterministic fake responses and
assert observable request arguments and failures, while production uses the real `gh api` command.

## Skill integration

Update `skills/pr-review-comments/SKILL.md` so the procedure builds the JSON spec from the approved
draft, invokes the helper, and requires its response validation. Keep comment classification, the
review approval gate, and the separate issue-creation gate in the skill. The helper owns only safe
body transport and response verification.

## Error handling

- Invalid JSON, missing fields, invalid line numbers, duplicate `{primary_url}` tokens, unresolved
  placeholders, and mismatched companion titles fail before the first API call.
- A non-zero `gh` exit, invalid JSON response, missing `html_url`, or response mismatch stops the
  workflow with the target and reason.
- A primary comment may exist if a later companion fails; the error reports the posted primary URL so
  the operator can recover manually.

## Test scope

Unit tests cover:

1. Safe primary and companion posting preserves backticks and substitutes the real primary URL.
2. `--dry-run` validates without invoking the runner.
3. Unresolved or duplicate placeholders fail before mutation.
4. A mismatched primary response stops before posting companions.
5. A mismatched companion response stops without posting later companions.
