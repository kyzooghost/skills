# sync-superpowers Design

## Summary

A new skill, `sync-superpowers`, installs or updates [obra/superpowers](https://github.com/obra/superpowers) to its latest GitHub release with one command. It makes superpowers available, once each, in Claude Code, Codex, and Cursor.

All three tools read from one git checkout pinned to a release tag:

- Claude Code loads the checkout as a local-path plugin marketplace.
- Codex and Cursor load `~/.agents/skills/<skill>` symlinks into the checkout.

## Background

The previous setup linked `~/.claude/skills/<skill>` into a versioned Claude plugin cache folder (`.../superpowers/6.3.0/skills/...`). `~/.codex/skills` and `~/.agents/skills` linked to the Claude links. Claude Code removed the `6.3.0` folder when the plugin updated, so all 45 links broke. The links were removed on 2026-11-22.

Facts that shape the design:

| Fact | Source |
|---|---|
| obra/superpowers publishes GitHub releases. The latest is `v7.0.2`. | `gh release list -R obra/superpowers` |
| The repo is a Claude marketplace named `superpowers-dev` with one plugin, `superpowers`, at `source: "./"`. | `.claude-plugin/marketplace.json` at `v7.0.2` |
| The Codex plugin declares `"hooks": {}`. It provides skills only. | `.codex-plugin/plugin.json` at `v7.0.2` |
| Codex scans `~/.codex/skills`, `~/.agents/skills`, and its plugin cache. Skills with the same name are not merged. | Codex 0.171 binary strings (`codex-home-skills`, `user-agent-skills`, `plugins/cache`); [Codex skills docs](https://developers.openai.com/codex/skills) |
| Cursor reads `~/.agents/skills`, `~/.cursor/skills`, `~/.claude/skills`, and `~/.codex/skills`. It does not read Claude plugins. | [Cursor skills docs](https://cursor.com/docs/skills) |
| A Claude marketplace added from a local directory, with a relative plugin `source`, is read from that directory. | [Claude marketplace docs](https://code.claude.com/docs/en/plugin-marketplaces), "Test an edit to a plugin" |
| `claude plugin list --json` and `codex plugin list --json` report installed plugins with their ids and versions. | Local CLI output |

State on 2026-11-22, before this skill runs:

- Claude has `superpowers@superpowers-marketplace` 5.1.0 (user scope, enabled), the same plugin at local scope for `~/Desktop/repos/yt`, and `superpowers@claude-plugins-official` 7.0.2 (user scope, disabled).
- Codex has `superpowers@superpowers-dev` 7.0.2 (git marketplace tracking `main`) and `superpowers@openai-curated-remote` 7.0.1.

## Goals

- One command installs or updates superpowers to the latest release, or to a named tag.
- Claude Code, Codex, and Cursor each see one copy of each superpowers skill.
- All three tools use the same version.
- A plugin update never breaks a link.
- A second run on the same tag changes nothing.

## Non-goals

- Do not change `sync-skill` or `sync-command`. Their duplicate links in Codex and Cursor are a separate follow-up.
- Do not track `main`. Only release tags.
- Do not change project-scope or local-scope Claude installs. Report them only.
- Do not remove Claude marketplaces other than our own. Other marketplaces may host other plugins.
- Do not support agents other than Claude Code, Codex, and Cursor.

## Components

| Path | Purpose |
|---|---|
| `skills/sync-superpowers/SKILL.md` | When to use the skill, the command, and how to verify the result. |
| `skills/sync-superpowers/scripts/sync_superpowers.py` | All git, plugin, and link actions. Python standard library only. |
| `skills/sync-superpowers/agents/openai.yaml` | Codex display metadata, as in sibling skills. |
| `tests/test_sync_superpowers.py` | `unittest` tests for the script. |

## Script

### Interface

```text
sync_superpowers.py [--version TAG] [--dry-run]
                    [--checkout-dir PATH] [--agents-skills-dir PATH]
                    [--repo-url URL]
```

| Option | Default | Purpose |
|---|---|---|
| `--version` | latest release | Pin or roll back to a tag, for example `v7.0.1`. |
| `--dry-run` | off | Print every action. Run only read-only commands. |
| `--checkout-dir` | `~/.local/share/superpowers` | Location of the managed checkout. |
| `--agents-skills-dir` | `~/.agents/skills` | Location of the links for Codex and Cursor. |
| `--repo-url` | `https://github.com/obra/superpowers.git` | Clone source. Tests use a local repo. |

Shared constants hold the repo slug, repo URL, marketplace name `superpowers-dev`, plugin name `superpowers`, and default paths.

### Phase 1: Preflight

The script runs every check before it changes the working tree, a plugin, or a link. On the first failed check, it exits `1`, prints `error: <reason>` to stderr, and changes nothing else. Cloning a missing checkout and fetching tags are allowed in preflight, because they do not change anything the tools read.

1. `git`, `claude`, and `codex` are on `PATH`. `gh` is on `PATH` unless `--version` is given.
2. Resolve the target tag:
   - `--version`, if given.
   - Otherwise `gh release view -R obra/superpowers --json tagName`.
3. Get the repository:
   - If the checkout exists, it is a git repository whose `origin` URL equals `--repo-url`, and `git status --porcelain --untracked-files=all` is empty.
   - If the checkout is missing: `git clone --no-checkout <repo-url> <checkout-dir>`.
   - Then: `git -C <checkout-dir> fetch --tags --force origin`.
4. The tag exists: `git -C <checkout-dir> rev-parse --verify refs/tags/<tag>` succeeds.
5. Read the skill names in the tag with `git -C <checkout-dir> ls-tree --name-only <tag> skills/`, keeping entries that contain `SKILL.md`. For each name, `<agents-skills-dir>/<name>` is missing or a symlink. A real file or directory at that path is an error.

### Phase 2: Checkout

- `git -C <checkout-dir> checkout --detach <tag>`.

### Phase 3: Claude Code

Read state with `claude plugin marketplace list --json` and `claude plugin list --json`.

1. Marketplace:
   - If no marketplace named `superpowers-dev` exists: `claude plugin marketplace add <checkout-dir>`.
   - If one exists with a source other than `<checkout-dir>`: `claude plugin marketplace remove superpowers-dev`, then add as above. Today's `--json` output shows only GitHub marketplaces (`source`, `repo`, `installLocation`). The field that holds a local path is not yet confirmed. The implementation must confirm it by adding a local marketplace and reading the output.
   - Otherwise: `claude plugin marketplace update superpowers-dev`.
2. Plugin:
   - If `superpowers@superpowers-dev` is not installed at user scope: `claude plugin install superpowers@superpowers-dev`.
   - Otherwise: `claude plugin update superpowers@superpowers-dev`.
3. Duplicates: for each other installed id `superpowers@<marketplace>`:
   - User scope: `claude plugin uninstall superpowers@<marketplace>`.
   - Project or local scope: print a warning with the `projectPath`. Do not change it.
4. Verify: `claude plugin list --json` shows `superpowers@superpowers-dev` at user scope, enabled, with `version` equal to the tag without its leading `v`.

### Phase 4: Codex

Read state with `codex plugin list --json` (`installed` array).

1. For each installed plugin whose `name` is `superpowers`: `codex plugin remove <pluginId>`.
2. If `codex plugin marketplace list --json` shows a marketplace named `superpowers-dev`: `codex plugin marketplace remove superpowers-dev`. The remote `openai-curated` marketplace stays. Only its plugin is removed.
3. Verify: `codex plugin list --json` shows no installed plugin named `superpowers`.

### Phase 5: Links

The skill set is every `<checkout-dir>/skills/<name>/SKILL.md`.

1. For each skill, make `<agents-skills-dir>/<name>` a symlink to `<checkout-dir>/skills/<name>`:
   - Missing: create.
   - Symlink to the correct target: leave.
   - Symlink to another target: replace.
2. Prune: remove each symlink in `<agents-skills-dir>` whose target is inside `<checkout-dir>/skills/` and whose name is not in the skill set.
3. Warn, but do not change, when a skill name exists in `~/.claude/skills`, `~/.codex/skills`, or `~/.cursor/skills`. Cursor reads all three, so that copy would appear twice.

### Phase 6: Report

Print:

- the tag
- the Claude plugin id, scope, and version
- the Claude and Codex plugins removed
- the links created, updated, and pruned
- every warning
- a reminder to restart Claude Code, Codex, and Cursor

### Dry run

`--dry-run` runs Phase 1 and the read-only `list` commands, so it can report the correct plan. It prints each later write action with a `would` prefix instead of running it. When the checkout is missing, Phase 1 clones into a temporary directory instead of `<checkout-dir>`, and deletes the temporary directory at exit.

### Errors

- Any failed subprocess stops the run. The script prints the command and its stderr, then exits `1`.
- A failure after Phase 1 can leave a partial update. The report names the last completed phase. Running the script again finishes the update, because every phase is idempotent.
- The script never deletes a real file or directory.

## SKILL.md

The skill body covers:

1. When to use it: install, update, pin, or roll back superpowers, or repair broken superpowers links.
2. The command, with `--dry-run` first when the user wants a preview.
3. How to read the report, and what each warning means.
4. Verification:
   - `claude plugin list --json` shows `superpowers@superpowers-dev` at the tag.
   - `ls -l ~/.agents/skills` shows one link for each superpowers skill.
   - `codex plugin list --json` shows no installed `superpowers` plugin.
5. Restart Claude Code, Codex, and Cursor.

Skill names differ by tool. Claude Code uses `superpowers:<skill>`. Codex and Cursor use `<skill>`.

## Testing

`tests/test_sync_superpowers.py` runs the script as a subprocess, as `tests/test_sync_command.py` does. No test touches real home directories or the network.

Fixtures:

- A local git repo that acts as `--repo-url`. It has tag `v1.0.0` with skills `alpha` and `beta`, and tag `v1.1.0` with skills `alpha` and `gamma`.
- Stub `claude`, `codex`, and `gh` executables in a temporary directory placed first on `PATH`. Each stub logs its arguments to a file and prints canned JSON from fixture state.
- Temporary `--checkout-dir` and `--agents-skills-dir`. `HOME` is set to a temporary directory so the warning checks read only test data.

Cases:

1. A first run at `v1.0.0` clones, checks out the tag, adds the marketplace, installs the plugin, and creates links for `alpha` and `beta`.
2. A second run at `v1.0.0` creates or changes no links, and runs `update` instead of `install`.
3. A run at `v1.1.0` keeps `alpha`, creates `gamma`, and prunes `beta`.
4. With no `--version`, the script uses the tag from the `gh` stub.
5. A dirty checkout makes the script exit `1`, and no plugin command runs.
6. A real directory at `<agents-skills-dir>/alpha` makes the script exit `1` before any change.
7. Other `superpowers@*` plugins are uninstalled at user scope. A local-scope install produces a warning and no command.
8. All installed Codex `superpowers` plugins are removed, and the `superpowers-dev` Codex marketplace is removed.
9. `--dry-run` with no checkout leaves `--checkout-dir` and `--agents-skills-dir` unchanged and runs no write command.
10. A failing stub command makes the script exit `1` and print the failed command.

Run with `python3 -m unittest tests.test_sync_superpowers`.

## Acceptance

After `sync_superpowers.py` runs on this machine:

- `claude plugin list --json` shows `superpowers@superpowers-dev`, user scope, enabled, version `7.0.2`. It shows no other user-scope `superpowers@*`.
- `codex plugin list --json` shows no installed plugin named `superpowers`.
- `~/.agents/skills` has one symlink for each skill in `~/.local/share/superpowers/skills`, and each link resolves.
- `~/.claude/skills`, `~/.codex/skills`, and `~/.cursor/skills` contain no superpowers skill names.
- A second run reports no changes.
