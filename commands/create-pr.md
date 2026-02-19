# Claude Command: Create PR

This command auto-generates and creates GitHub PRs from git diff analysis with minimal user input.

## Usage

```
/create-pr           # Create new PR
/create-pr --update  # Update existing PR for current branch
```

## What This Command Does

1. Resolves the GitHub `owner/repo` from the local git remote
2. Checks if a PR already exists for the current branch
3. Gets the diff against main branch
4. Gets commit messages since branching from main
5. Scans conversation context for related ticket references
6. Generates a complete PR description
7. Shows a preview to the user
8. Creates or updates the PR via `gh` CLI

## Step 1: Repo Resolution

Run `git remote get-url origin` to get the remote URL.

Parse `owner/repo` from the URL:
- HTTPS format: `https://github.com/owner/repo.git` - extract between `github.com/` and `.git`
- SSH format: `git@github.com:owner/repo.git` - extract between `:` and `.git`
- Handle URLs with or without the trailing `.git`

If no origin remote exists, stop with: "Error: no git origin remote found. This command requires a GitHub remote."

## Step 2: Check for Existing PR

Run: `gh pr list --head $(git branch --show-current) --json number,url --jq '.[0]'`

Behavior:
- If `--update` flag provided and no PR exists: stop with "Error: no PR exists for this branch. Use `/create-pr` to create one."
- If no flag provided and PR exists: stop with "A PR already exists for this branch: {url}. Use `/create-pr --update` to update it."
- Otherwise: proceed to next step

## Step 3: Gather Context

Get the diff against main:
```bash
git diff main...HEAD
```

Get commit messages since branching:
```bash
git log main..HEAD --pretty=format:"%s%n%b"
```

Get list of changed files:
```bash
git diff main...HEAD --name-only
```

If no commits ahead of main, stop with: "Error: no changes to create PR for. Commit your changes first."

## Step 4: Detect Related Ticket

Scan the conversation context for ticket references:
- Jira pattern: `[A-Z]+-\d+` (e.g., ABC-1234, PROJ-567)
- GitHub issue pattern: `#\d+` (e.g., #123)

Priority:
1. If found in conversation, use it
2. If not found, set Related to "None"

Do NOT prompt the user for a ticket. Only offer to create one if the user explicitly asks.

## Step 5: Generate PR Description

Analyze the diff and commits to generate:

### Title
Generate a concise title from the diff analysis. Use conventional commit format:
- `feat: ...` for new features
- `fix: ...` for bug fixes
- `chore: ...` for maintenance
- `docs: ...` for documentation
- `refactor: ...` for refactoring

### Description Sections

Generate each section based on the diff:

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

## Step 6: Preview and Create

Display the generated PR to the user in this format:

```
## PR Preview

**Title:** {generated title}

---

{generated description}

---

Ready to create this PR? (Proceeding unless you say otherwise)
```

Then create or update the PR:

**For new PR:**
```bash
gh pr create --title "{title}" --body "{description}"
```

**For update (`--update` flag):**
```bash
gh pr edit --title "{title}" --body "{description}"
```

After creation/update, show the PR URL.

## Error Handling

- `gh` CLI not installed or not authenticated: "Error: `gh` CLI is not available or not authenticated. Run `gh auth login` first."
- PR creation fails: show the error from `gh` and stop

## Ground Rules

- Do NOT prompt for user input unless explicitly requested (e.g., ticket creation)
- Auto-generate everything from diff/context
- Show preview before creating
- Never auto-commit - PR creation only
