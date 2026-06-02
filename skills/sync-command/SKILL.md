---
name: sync-command
description: Sync a command from this repo into local agent surfaces. Use when the user asks to make a repo command available locally, sync a local command for Claude, Agents, or Codex, update command symlinks, or expose a command to Codex as a skill.
---

# Sync Command

## Overview

Sync a command from this repository by making `~/.claude/commands/<command>.md` a symlink to the repo command file, then making `~/.agents/commands/<command>.md` point at the Claude command path.

Codex does not discover slash commands from `~/.codex/commands` in this setup. For Codex, the syncer ensures there is a repo-backed skill at `skills/<command>/` and makes `~/.codex/skills/<command>` point at that skill. If `skills/<command>/SKILL.md` already exists, preserve it and only refresh the command reference/link.

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
   - `~/.codex/skills/<command>` -> repo skill directory
5. Verify the repo skill state:
   - If `skills/<command>/SKILL.md` was missing, it was created as a command-backed wrapper.
   - `skills/<command>/references/command.md` points at the source command file.
6. Tell the user the command is available as `/<command>` for command-aware agents and as `$<command>` in Codex after restarting the relevant agent app.

## Existing Commands

The syncer replaces whatever is already at the destination:

- Missing links are created.
- Existing symlinks are replaced when they point somewhere else.
- Existing real files are removed and replaced with the symlink.

For Codex skill wrappers:

- Missing `skills/<command>/SKILL.md` files are created.
- Existing `skills/<command>/SKILL.md` files are preserved.
- `skills/<command>/references/command.md` is refreshed to point at the source command file.

## Options

Use `--dry-run` to preview changes without writing symlinks:

```bash
python3 skills/sync-command/scripts/sync_command.py doc-update --dry-run
```

Use `--repo-root <path>` when running from outside this repository and passing a command name.

Use `--codex-skills-dir <path>` only when explicitly asked to install Codex skills outside `~/.codex/skills`.

Only override the destination directories when the user explicitly asks for non-default install roots.
