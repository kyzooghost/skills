---
name: create-pr
description: Use when the user asks to create, update, draft, or generate a GitHub pull request, including /create-pr behavior or equivalent workflow.
---

# Create PR

Choose exactly one path, then follow `references/command.md` for publish.

1. **Skip prep.** The invocation includes `--update` or `--skip-prep`. Read no prep reference.
2. **Stacked prep.** The user explicitly named an open pull request to stack on, by number, URL, or branch. Read and follow `references/stacked-prep.md`.
3. **Normal prep.** Every other new pull request. Read and follow `references/normal-prep.md`.

A prep stop does not follow `references/command.md`.

On normal prep, resolve `--base` before the branch is created. Stacked prep ignores `--base`. `--draft` stays on the publish path.

Preserve the command behavior exactly, including the preview step before creating or updating a PR.

**Before publishing the PR**, review it (PR descriptions/titles, commit messages, issue/PR comments, code comments, changelog entries) for sensitive content picked up during the chat and strip it out. Never include:

- Internal metrics or impact numbers (error rates, % of users/transactions affected, revenue, analytics results from Mixpanel, Sentry, Grafana, etc.)
- PII or user-identifiable data (names, emails, addresses, transaction hashes, account IDs)
- Incident narratives or details of unfixed/current production issues (what's broken, how to trigger it, who reported it)
- Internal links or names of internal sources (Slack threads, Jira tickets beyond a plain ID, Notion, Zoom, dashboards) and coworker names

Instead, describe the change technically and neutrally - keep incident context out of the PR.
