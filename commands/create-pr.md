# Claude Command: Create PR

This command auto-generates and creates GitHub PRs from git diff analysis with minimal user input.

## Usage

```text
/create-pr [--base <branch>] [--draft]
/create-pr --update [--base <branch>]
```

- `--base <branch>` uses the named PR base instead of resolving the repository default.
- `--draft` creates a new draft PR.
- `--update --draft` is unsupported because draft conversion and PR content updates are separate mutations. Stop with: "Error: `--update --draft` is unsupported. Use `gh pr ready --undo` explicitly if the existing PR must return to draft."
- Reject unknown flags and a missing value after `--base` before performing any GitHub mutation.

## What This Command Does

1. Resolves the GitHub `owner/repo` from the local git remote
2. Checks if a PR already exists for the current branch
3. Resolves an explicit base branch, the existing PR base for updates, or the repository default branch
4. Gets the diff against the resolved base branch
5. Gets commit messages since branching from the resolved base branch
6. Scans conversation context for related ticket references
7. Generates a complete PR description
8. Shows a preview to the user
9. Scrubs sensitive content from the PR before publishing
10. Creates a normal or draft PR, or updates an existing PR, against the resolved base

## Step 1: Repo Resolution

Run `git remote get-url origin` to get the remote URL.

Parse `owner/repo` from the URL:
- HTTPS format: `https://github.com/owner/repo.git` - extract between `github.com/` and `.git`
- SSH format: `git@github.com:owner/repo.git` - extract between `:` and `.git`
- Handle URLs with or without the trailing `.git`

Record the parsed value as `OWNER_REPO`.

If no origin remote exists, stop with: "Error: no git origin remote found. This command requires a GitHub remote."

## Step 2: Check for Existing PR

```bash
gh pr list \
  --head "$(git branch --show-current)" \
  --json number,url,baseRefName \
  --jq '.[0]'
```

Behavior:
- If `--update` flag provided and no PR exists: stop with "Error: no PR exists for this branch. Use `/create-pr` to create one."
- If no flag provided and PR exists: stop with "A PR already exists for this branch: {url}. Use `/create-pr --update` to update it."
- Otherwise: proceed to next step

Record the existing PR number as `PR_NUMBER` and its `baseRefName` when present.

Base precedence:

1. Use the value supplied through `--base <branch>`.
2. For `--update` without `--base`, use the existing PR's `baseRefName`.
3. For a new PR without `--base`, defer to Step 3's repository-default lookup.

The same `BASE_BRANCH` value must be used for diff collection, commit collection, changed-file collection, PR creation, and PR update.

## Step 3: Gather Context

If `BASE_BRANCH` was not supplied or obtained from an existing PR, resolve it from GitHub:

```bash
BASE_BRANCH="$(
  gh repo view "$OWNER_REPO" \
    --json defaultBranchRef \
    --jq '.defaultBranchRef.name'
)"
```

If the command fails or returns an empty value, stop with:

```text
Error: unable to resolve the PR base branch. Pass one explicitly with `--base <branch>`.
```

Fetch the selected base so local context reflects the remote branch:

```bash
git fetch origin "$BASE_BRANCH"
```

Get the diff against the resolved base branch:
```bash
git diff "origin/$BASE_BRANCH"...HEAD
```

Get commit messages since branching:
```bash
git log "origin/$BASE_BRANCH"..HEAD --pretty=format:"%s%n%b"
```

Get list of changed files:
```bash
git diff "origin/$BASE_BRANCH"...HEAD --name-only
```

If `git rev-list --count "origin/$BASE_BRANCH"..HEAD` returns `0`, stop with: "Error: no commits ahead of `$BASE_BRANCH`. Commit your changes first."

Check for PR template:
```bash
find .github -iname 'pull_request_template.md' -o -iname 'pull_request_template' 2>/dev/null | head -1
```

If found, read the template file. If a `.github/PULL_REQUEST_TEMPLATE/` directory exists with multiple templates, use `default.md` or the first file found.

## Step 4: Detect Related Ticket

Scan the conversation context for ticket references:
- Jira pattern: `[A-Z]+-\d+` (e.g., ABC-1234, PROJ-567)
- GitHub issue pattern: `#\d+` (e.g., #123)

Priority:
1. If found in conversation, use it
2. If not found, set Related to "None"

Do NOT prompt the user for a ticket. Only offer to create one if the user explicitly asks.

## Step 5: Generate PR Description

Analyze the diff and commits to generate the PR content.

### Title
Generate a concise title from the diff analysis. Use conventional commit format:
- `feat: ...` for new features
- `fix: ...` for bug fixes
- `chore: ...` for maintenance
- `docs: ...` for documentation
- `refactor: ...` for refactoring

### Description

**If a PR template was found:** Fill in each section of the template based on the diff/commit analysis. Preserve the template's structure and headings. Leave optional sections empty or mark as "N/A" if not applicable.

**If no template exists:** Generate each section based on the diff:

**Summary** - Bullet points of key changes (3-5 items max)

**Problem** - Infer from diff/commits what issue this solves. If unclear, describe what the changes do.

**Solution** - How the changes address the problem. Include code snippets if relevant (e.g., YAML config examples).

**Related** - The detected ticket, or "None" if not found.

**Scope** - Infer from file paths:
- Infrastructure paths (e.g., `cluster-core/dev/`) → environment name
- Source code paths → "Feature: [inferred feature name]"
- Mixed → list all affected areas

**Test Plan** - Auto-generate checklist based on change types:

| File Pattern | Test Plan Item |
|-------------|----------------|
| `*.yaml`, `*.yml` | YAML syntax validation passes |
| `*.ts`, `*.js`, `*.py`, `*.go` | Unit tests pass |
| `*.ts`, `*.js`, `*.py`, `*.go` | Build succeeds |
| `**/helm/**`, `**/argocd/**` | ArgoCD syncs successfully |
| `**/migrations/**` | Migration runs without errors |
| `**/api/**`, `**/*api*` | API contract tests pass |
| Any config/env file | Verify deployment in target environment |

## Step 6: Documentation Drift Check

Run the `/doc-update` command to detect and fix documentation drift caused by the changes on this branch.

- If drift is found and fixed, the doc-update command will present changes and optionally commit them.
- If doc fixes are committed, re-run Step 3 (Gather Context) to include the doc changes in the PR description.
- If no drift is found, proceed to the next step.

## Step 7: Preview

Display the generated PR to the user in this format:

```
## PR Preview

**Title:** {generated title}

---

{generated description}

---

Ready to create this PR? (Proceeding unless you say otherwise)
```

## Step 8: Sensitive Content Review

**Before publishing the PR**, review it (PR descriptions/titles, commit messages, issue/PR comments, code comments, changelog entries) for sensitive content picked up during the chat and strip it out. Never include:

- Internal metrics or impact numbers (error rates, % of users/transactions affected, revenue, analytics results from Mixpanel, Sentry, Grafana, etc.)
- PII or user-identifiable data (names, emails, addresses, transaction hashes, account IDs)
- Incident narratives or details of unfixed/current production issues (what's broken, how to trigger it, who reported it)
- Internal links or names of internal sources (Slack threads, Jira tickets beyond a plain ID, Notion, Zoom, dashboards) and coworker names

Instead, describe the change technically and neutrally - keep incident context out of the PR.

If the preview still contains any of the above, rewrite the title and/or body, show the updated preview, then proceed.

## Step 9: Create or Update

Use exactly one mutation.

For a new normal PR:

```bash
gh pr create --base "$BASE_BRANCH" --title "{title}" --body "{description}"
```

For a new draft PR:

```bash
gh pr create --base "$BASE_BRANCH" --draft --title "{title}" --body "{description}"
```

For an update:

```bash
gh pr edit "$PR_NUMBER" --base "$BASE_BRANCH" --title "{title}" --body "{description}"
```

After creation or update, show the PR URL and resolved base branch.

## Error Handling

- `gh` CLI not installed or not authenticated: "Error: `gh` CLI is not available or not authenticated. Run `gh auth login` first."
- PR creation fails: show the error from `gh` and stop
- Missing value after `--base`: "Error: `--base` requires a branch name."
- Unsupported flag combination: "Error: `--update --draft` is unsupported. Use `gh pr ready --undo` explicitly if the existing PR must return to draft."
- Base resolution failure: "Error: unable to resolve the PR base branch. Pass one explicitly with `--base <branch>`."
- Base fetch failure: show the `git fetch origin "$BASE_BRANCH"` error and stop.

## Ground Rules

- Do NOT prompt for user input unless explicitly requested (e.g., ticket creation)
- Auto-generate everything from diff/context
- Show preview before creating
- Scrub sensitive content before publishing (see Step 8)
- Never auto-commit - PR creation only
