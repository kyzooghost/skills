---
name: create-pr
description: Use when the user asks to create, update, draft, or generate a GitHub pull request, including /create-pr behavior or equivalent workflow.
---

# Create PR

Read and follow `references/command.md`.

Preserve the command behavior exactly, including the preview step before creating or updating a PR.

**Before publishing the PR**, review it (PR descriptions/titles, commit messages, issue/PR comments, code comments, changelog entries) for sensitive content picked up during the chat and strip it out. Never include:

- Internal metrics or impact numbers (error rates, % of users/transactions affected, revenue, analytics results from Mixpanel, Sentry, Grafana, etc.)
- PII or user-identifiable data (names, emails, addresses, transaction hashes, account IDs)
- Incident narratives or details of unfixed/current production issues (what's broken, how to trigger it, who reported it)
- Internal links or names of internal sources (Slack threads, Jira tickets beyond a plain ID, Notion, Zoom, dashboards) and coworker names

Instead, describe the change technically and neutrally - keep incident context out of the PR.
