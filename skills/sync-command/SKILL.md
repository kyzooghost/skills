---
name: sync-command
description: Sync a command from this repo into the local machine's command directory (~/.claude/commands/). Use when the user asks to make a repo command available locally, install a local command for Claude, or update a local command file.
---

# Sync Command

## Overview

Sync a command from this repository by copying it to `~/.claude/commands/<command>.md`.

Unlike skills (which use symlinks), commands are plain markdown files copied to the destination.

## Workflow

1. Identify the repo command name or path. Prefer a command name when the source is `commands/<name>.md`.
2. Inspect the source command and confirm the file exists.
3. Copy the command file:

```bash
cp <repo-root>/commands/<command>.md ~/.claude/commands/<command>.md
```

Example from this repo:

```bash
cp commands/doc-update.md ~/.claude/commands/doc-update.md
```

4. Confirm the file exists at `~/.claude/commands/<command>.md`.
5. Tell the user the command is available as `/<command>` in their next Claude session.

## Sync All

To sync all commands from this repo at once:

```bash
cp commands/*.md ~/.claude/commands/
```

## Existing Commands

Existing files at the destination are overwritten without prompting. The source repo is the authority.
