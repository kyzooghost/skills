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
