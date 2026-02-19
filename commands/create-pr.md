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
