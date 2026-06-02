---
name: sync-command
description: Sync a command from this repo into the local machine's command directories. Use when the user asks to make a repo command available locally, sync a local command for Claude, Agents, or Codex, update local command symlinks, or follow the .claude/commands source link pattern with .agents/commands and .codex/commands symlinks.
---

# Sync Command

## Overview

Sync a command from this repository by making `~/.claude/commands/<command>.md` a symlink to the repo command file, then making `~/.agents/commands/<command>.md` and `~/.codex/commands/<command>.md` point at the Claude command path.

Use the bundled script for the filesystem changes so repeated syncs update links consistently.

## Workflow

1. Identify the repo command name or path. Prefer a command name when the source is `commands/<name>.md`.
2. Inspect the source command and confirm the file exists.
3. Run the syncer:

```bash
python3 <this-skill-dir>/scripts/sync_command.py <command-name>
```

Example from this repo:

```bash
python3 skills/sync-command/scripts/sync_command.py doc-update
```

4. Verify the output shows all three managed links:
   - `~/.claude/commands/<command>.md` -> repo command file
   - `~/.agents/commands/<command>.md` -> `~/.claude/commands/<command>.md`
   - `~/.codex/commands/<command>.md` -> `~/.claude/commands/<command>.md`
5. Tell the user the command is available as `/<command>` in their next session.

## Existing Commands

The syncer replaces whatever is already at the destination:

- Missing links are created.
- Existing symlinks are replaced when they point somewhere else.
- Existing real files are removed and replaced with the symlink.

## Options

Use `--dry-run` to preview changes without writing symlinks:

```bash
python3 skills/sync-command/scripts/sync_command.py doc-update --dry-run
```

Use `--repo-root <path>` when running from outside this repository and passing a command name.

Only override the destination directories when the user explicitly asks for non-default install roots.
