---
name: sync-skill
description: Sync a skill from this repo into the local machine's skill directories. Use when the user asks to make a repo skill available locally, sync a local skill for Claude, Agents, or Codex, update local skill symlinks, or follow the .claude/skills source link pattern with .agents/skills and .codex/skills symlinks.
---

# Sync Skill

## Overview

Sync a skill from this repository by making `~/.claude/skills/<skill>` the source-facing symlink to the repo skill, then making `~/.agents/skills/<skill>` and `~/.codex/skills/<skill>` point at the Claude skill path.

Use the bundled script for the filesystem changes so repeated syncs update links consistently.

## Workflow

1. Identify the repo skill name or path. Prefer a skill name when the source is `skills/<name>`.
2. Inspect the source skill and confirm it contains `SKILL.md`.
3. Run the installer:

```bash
python3 <this-skill-dir>/scripts/install_local_skill.py <skill-name-or-path>
```

Example from this repo:

```bash
python3 skills/sync-skill/scripts/install_local_skill.py handover
```

4. Verify the output shows all three managed links:
   - `~/.claude/skills/<skill>` -> repo skill directory
   - `~/.agents/skills/<skill>` -> `~/.claude/skills/<skill>`
   - `~/.codex/skills/<skill>` -> `~/.claude/skills/<skill>`
5. Tell the user to restart the relevant agent app so it reloads skill metadata.

## Existing Installs

The installer replaces whatever is already at the destination:

- Missing links are created.
- Existing symlinks are replaced when they point somewhere else.
- Existing real files or directories are removed and replaced with the symlink.

## Options

Use `--dry-run` to preview changes without writing symlinks:

```bash
python3 skills/sync-skill/scripts/install_local_skill.py handover --dry-run
```

Use `--repo-root <path>` when running from outside this repository and passing a skill name.

Only override the destination directories when the user explicitly asks for non-default install roots.
