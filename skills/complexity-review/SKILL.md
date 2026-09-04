---
name: complexity-review
description: Review a PR for unnecessary complexity, brittle test strategies, and overengineering. Produces a local markdown report with findings and actionable recommendations. Use when the user says "/complexity-review", "review this PR for complexity", or asks to check a PR for overengineering.
---

# Complexity Review

Read and follow `references/command.md`. Use `references/lenses.md` for the detection criteria.

Review the PR diff through three lenses: unnecessary complexity, brittle tests, and overengineering. For each finding, explain the concrete cost and recommend a specific action.

Write the report to a local markdown file. Print a summary to the terminal.
