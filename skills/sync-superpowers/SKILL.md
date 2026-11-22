---
name: sync-superpowers
description: Use when the user wants to install, update, pin, or roll back obra/superpowers for Claude Code, Codex, and Cursor, or when superpowers skills are missing, duplicated, or have broken links.
---

# Sync Superpowers

## Overview

Install or update [obra/superpowers](https://github.com/obra/superpowers) to a GitHub release with one command. Each of Claude Code, Codex, and Cursor gets one copy of each skill, all from the same version.

The script keeps a git checkout pinned to a release tag at `~/.local/share/superpowers`:

| Tool | How it loads superpowers | Skill names |
|---|---|---|
| Claude Code | Plugin `superpowers@superpowers-dev` from a local marketplace at the checkout | `superpowers:<skill>` |
| Codex | Symlinks `~/.agents/skills/<skill>` into the checkout | `<skill>` |
| Cursor | The same `~/.agents/skills` symlinks | `<skill>` |

The script also removes duplicates: other user-scope `superpowers@*` plugins in Claude Code, and every superpowers plugin in Codex.

## Workflow

1. If the user wants a preview, run a dry run first:

```bash
python3 <this-skill-dir>/scripts/sync_superpowers.py --dry-run
```

2. Run the sync. With no `--version`, it installs the latest release:

```bash
python3 <this-skill-dir>/scripts/sync_superpowers.py
```

Use `--version <tag>` to pin or roll back, for example `--version v7.0.1`.

3. Read the report:
   - Each action line names a git, plugin, or link change.
   - `claude: superpowers@superpowers-dev scope=user version=<x>` confirms the Claude plugin.
   - `links: ...` counts the links created, updated, and removed.
   - Report each `warning:` line to the user. See Warnings.
4. Verify:
   - `claude plugin list --json` shows `superpowers@superpowers-dev`, user scope, enabled, at the tag version.
   - `ls -l ~/.agents/skills` shows one link for each skill in `~/.local/share/superpowers/skills`.
   - `codex plugin list --json` shows no installed plugin named `superpowers`.
5. Tell the user to restart Claude Code, Codex, and Cursor.

## Errors

The script checks everything before it changes anything:

| Error | Fix |
|---|---|
| `missing required tools on PATH` | Install the named tool. `gh` is needed only without `--version`. |
| `has local changes` | The checkout was edited. Ask the user before you discard anything there. |
| `origin is ..., expected ...` | The checkout was cloned from another URL. Pass the same `--repo-url` as the first run, or pass another `--checkout-dir`. |
| `is a real file or directory` | A real skill folder in `~/.agents/skills` has a superpowers name. Ask the user before you move it. |
| `tag ... not found` | Check the tag with `gh release list -R obra/superpowers`. |
| `command failed: ...` | Read the stderr shown below the command. Fix the cause and run the script again. Every phase is safe to repeat. |

## Warnings

- `Claude plugin ... is installed at local scope for <project>`: a project-level install the script does not change. Ask the user whether to uninstall it from that project with `claude plugin uninstall <id> --scope local`, run in that project.
- `... duplicates superpowers skill <name>`: a copy in `~/.claude/skills`, `~/.codex/skills`, or `~/.cursor/skills`. Cursor reads all three, so the skill appears twice. Ask the user before you remove it.

## Options

| Option | Default |
|---|---|
| `--version TAG` | latest release |
| `--dry-run` | off |
| `--checkout-dir PATH` | `~/.local/share/superpowers` |
| `--agents-skills-dir PATH` | `~/.agents/skills` |
| `--repo-url URL` | `https://github.com/obra/superpowers.git` |

Only override the paths or the repo URL when the user asks.
