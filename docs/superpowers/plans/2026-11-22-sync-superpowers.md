# sync-superpowers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `sync-superpowers` skill whose script installs or updates obra/superpowers to a release tag, and makes it available once each in Claude Code, Codex, and Cursor.

**Architecture:** One standard-library Python script keeps a git checkout pinned to a release tag. Claude Code loads the checkout as a local-path marketplace (`superpowers@superpowers-dev`). Codex and Cursor load `~/.agents/skills/<skill>` symlinks into the checkout. The script removes duplicate superpowers plugins from both CLIs.

**Tech Stack:** Python 3 standard library, `git`, `gh`, `claude` CLI, `codex` CLI, `unittest`.

**Spec:** `docs/superpowers/specs/2026-11-22-sync-superpowers-design.md`

**Work in:** worktree `.worktrees/sync-superpowers`, branch `feat/sync-superpowers`. Run every command from the worktree root.

---

## Verified CLI behavior

These facts were checked on 2026-11-22 with an isolated `CLAUDE_CONFIG_DIR` and `CODEX_HOME`. The code depends on them.

| Command | Output used |
|---|---|
| `claude plugin marketplace list --json` | JSON array. A local marketplace entry is `{"name": "superpowers-dev", "source": "directory", "path": "<abs path>", ...}`. |
| `claude plugin marketplace add <dir>` | Registers the marketplace by the `name` in `<dir>/.claude-plugin/marketplace.json` (`superpowers-dev`). |
| `claude plugin list --json` | JSON array of `{"id", "version", "scope", "enabled", "projectPath"?...}`. `version` follows the checkout tag after `marketplace update` and `plugin update`. |
| `claude plugin install\|update\|uninstall <id>` | Exit 0 on success. Default scope is `user`. |
| `codex plugin list --json` | `{"installed": [{"pluginId", "name", "installed", ...}], "available": [...]}`. |
| `codex plugin marketplace list --json` | `{"marketplaces": [{"name", "root", ...}]}`. |
| `codex plugin remove <pluginId>`, `codex plugin marketplace remove <name>` | Exit 0 on success. |
| `gh release view -R obra/superpowers --json tagName --jq .tagName` | Prints the latest release tag, for example `v7.0.2`. |

Not verified: whether `codex plugin remove superpowers@openai-curated-remote` works for a remote-directory plugin. Task 8 checks it on the real machine.

## File structure

| Path | Responsibility |
|---|---|
| `skills/sync-superpowers/scripts/sync_superpowers.py` | All git, plugin, and link actions. |
| `skills/sync-superpowers/SKILL.md` | When to use the skill, the command, how to read the report and verify. |
| `skills/sync-superpowers/agents/openai.yaml` | Codex display metadata. |
| `tests/test_sync_superpowers.py` | Subprocess tests with a local release repo and fake `claude`, `codex`, and `gh`. |

Run tests with:

```bash
python3 -m unittest discover -s tests -p 'test_sync_superpowers.py' -v
```

---

### Task 1: Checkout and link creation

**Files:**
- Create: `tests/test_sync_superpowers.py`
- Create: `skills/sync-superpowers/scripts/sync_superpowers.py`

- [ ] **Step 1: Write the test harness and the first two tests**

Create `tests/test_sync_superpowers.py`:

```python
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "skills" / "sync-superpowers" / "scripts" / "sync_superpowers.py"
PLUGIN_ID = "superpowers@superpowers-dev"
MARKETPLACE = "superpowers-dev"
RELEASES = {"v1.0.0": ("alpha", "beta"), "v1.1.0": ("alpha", "gamma")}
GIT_TEST_CONFIG = (
    "-c", "user.name=Test",
    "-c", "user.email=test@example.com",
    "-c", "commit.gpgsign=false",
    "-c", "tag.gpgsign=false",
    "-c", "init.defaultBranch=main",
)
FAKE_TOOLS = ("claude", "codex", "gh")
GIT_REPO_VARS = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR")

# Fake claude, codex, and gh. Each call is logged to FAKE_LOG. State lives in
# FAKE_STATE so install, uninstall, and remove calls persist between runs.
FAKE_CLI = r'''
import json
import os
import sys

tool, args = sys.argv[1], sys.argv[2:]
state_path = os.environ["FAKE_STATE"]
with open(state_path, encoding="utf-8") as handle:
    state = json.load(handle)
with open(os.environ["FAKE_LOG"], "a", encoding="utf-8") as handle:
    handle.write(json.dumps([tool, *args]) + "\n")

command = " ".join([tool, *args])
if state.get("fail") and command.startswith(state["fail"]):
    sys.stderr.write("simulated failure\n")
    sys.exit(1)
if "list" in args and "--json" not in args:
    sys.stderr.write("fake: list commands need --json\n")
    sys.exit(2)


def save():
    with open(state_path, "w", encoding="utf-8") as handle:
        json.dump(state, handle)


def emit(value):
    print(json.dumps(value))


sub = args[1:]  # drop "release" for gh, "plugin" for claude and codex
if tool == "gh":
    print(state["latest_tag"])
elif tool == "claude":
    if sub[:2] == ["marketplace", "list"]:
        emit(state["claude_marketplaces"])
    elif sub[:2] == ["marketplace", "add"]:
        state["claude_marketplaces"].append(
            {"name": "superpowers-dev", "source": "directory", "path": sub[2]}
        )
        save()
    elif sub[:2] == ["marketplace", "remove"]:
        name = sub[2]
        state["claude_marketplaces"] = [
            m for m in state["claude_marketplaces"] if m["name"] != name
        ]
        state["claude_plugins"] = [
            p for p in state["claude_plugins"] if not p["id"].endswith("@" + name)
        ]
        save()
    elif sub[:2] == ["marketplace", "update"]:
        pass
    elif sub[:1] == ["list"]:
        emit(state["claude_plugins"])
    elif sub[:1] == ["install"]:
        state["claude_plugins"].append(
            {"id": sub[1], "version": state["plugin_version"], "scope": "user", "enabled": True}
        )
        save()
    elif sub[:1] == ["update"]:
        for plugin in state["claude_plugins"]:
            if plugin["id"] == sub[1] and plugin["scope"] == "user":
                plugin["version"] = state["plugin_version"]
        save()
    elif sub[:1] == ["uninstall"]:
        state["claude_plugins"] = [
            p for p in state["claude_plugins"]
            if not (p["id"] == sub[1] and p["scope"] == "user")
        ]
        save()
    else:
        sys.exit("fake claude: unexpected command: " + command)
elif tool == "codex":
    if sub[:2] == ["marketplace", "list"]:
        emit({"marketplaces": state["codex_marketplaces"]})
    elif sub[:2] == ["marketplace", "remove"]:
        state["codex_marketplaces"] = [
            m for m in state["codex_marketplaces"] if m["name"] != sub[2]
        ]
        save()
    elif sub[:1] == ["list"]:
        emit({"installed": state["codex_plugins"], "available": []})
    elif sub[:1] == ["remove"]:
        state["codex_plugins"] = [
            p for p in state["codex_plugins"] if p["pluginId"] != sub[1]
        ]
        save()
    else:
        sys.exit("fake codex: unexpected command: " + command)
'''


def isolated_env(**extra: str) -> dict[str, str]:
    """Environment without the developer's git config or inherited repository variables."""
    env = {key: value for key, value in os.environ.items() if key not in GIT_REPO_VARS}
    env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1", **extra)
    return env


def git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *GIT_TEST_CONFIG, *args],
        cwd=cwd,
        env=isolated_env(),
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def make_release_repo(repo: Path) -> Path:
    repo.mkdir(parents=True)
    git(repo, "init", "-q")
    skills_dir = repo / "skills"
    for tag, skills in RELEASES.items():
        if skills_dir.exists():
            shutil.rmtree(skills_dir)
        for name in skills:
            skill_dir = skills_dir / name
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                f"---\nname: {name}\ndescription: Test skill {name}.\n---\n",
                encoding="utf-8",
            )
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", tag)
        git(repo, "tag", tag)
    return repo


def install_fake_cli(bin_dir: Path) -> None:
    bin_dir.mkdir()
    fake = bin_dir / "fake_cli.py"
    fake.write_text(FAKE_CLI, encoding="utf-8")
    for tool in FAKE_TOOLS:
        wrapper = bin_dir / tool
        wrapper.write_text(
            f'#!/bin/sh\nexec "{sys.executable}" "{fake}" {tool} "$@"\n',
            encoding="utf-8",
        )
        wrapper.chmod(0o755)


def default_state() -> dict:
    return {
        "latest_tag": "v1.1.0",
        "plugin_version": "1.0.0",
        "fail": None,
        "claude_marketplaces": [],
        "claude_plugins": [],
        "codex_marketplaces": [],
        "codex_plugins": [],
    }


class SyncSuperpowersTest(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self._temp_dir.name).resolve()
        self.home = self.root / "home"
        self.home.mkdir()
        self.checkout = self.root / "checkout"
        self.agents = self.home / ".agents" / "skills"
        self.upstream = make_release_repo(self.root / "upstream")
        self.bin = self.root / "bin"
        install_fake_cli(self.bin)
        self.state_path = self.root / "state.json"
        self.log_path = self.root / "log.jsonl"
        self.write_state(default_state())

    def tearDown(self) -> None:
        self._temp_dir.cleanup()

    def write_state(self, state: dict) -> None:
        self.state_path.write_text(json.dumps(state), encoding="utf-8")

    def read_state(self) -> dict:
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def update_state(self, **changes: object) -> None:
        state = self.read_state()
        state.update(changes)
        self.write_state(state)

    def read_log(self) -> list[list[str]]:
        if not self.log_path.exists():
            return []
        return [
            json.loads(line)
            for line in self.log_path.read_text(encoding="utf-8").splitlines()
        ]

    def clear_log(self) -> None:
        self.log_path.unlink(missing_ok=True)

    def tool_calls(self, *tools: str) -> list[list[str]]:
        return [call for call in self.read_log() if call[0] in tools]

    def run_sync(self, *extra: str) -> subprocess.CompletedProcess[str]:
        env = isolated_env(
            HOME=str(self.home),
            PATH=f"{self.bin}{os.pathsep}{os.environ['PATH']}",
            FAKE_STATE=str(self.state_path),
            FAKE_LOG=str(self.log_path),
        )
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--checkout-dir", str(self.checkout),
                "--agents-skills-dir", str(self.agents),
                "--repo-url", str(self.upstream),
                *extra,
            ],
            env=env,
            capture_output=True,
            text=True,
        )

    def assert_ok(self, result: subprocess.CompletedProcess[str]) -> None:
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def link_targets(self) -> dict[str, Path]:
        return {
            entry.name: Path(os.readlink(entry))
            for entry in self.agents.iterdir()
            if entry.is_symlink()
        }

    def checkout_tag(self) -> str:
        return git(self.checkout, "describe", "--tags", "--exact-match")

    def test_first_run_checks_out_tag_and_links_skills(self) -> None:
        result = self.run_sync("--version", "v1.0.0")

        self.assert_ok(result)
        self.assertEqual(self.checkout_tag(), "v1.0.0")
        self.assertEqual(
            self.link_targets(),
            {
                "alpha": self.checkout / "skills" / "alpha",
                "beta": self.checkout / "skills" / "beta",
            },
        )
        self.assertTrue((self.agents / "alpha" / "SKILL.md").is_file())

    def test_latest_release_used_without_version(self) -> None:
        result = self.run_sync()

        self.assert_ok(result)
        self.assertEqual(self.checkout_tag(), "v1.1.0")
        self.assertIn(["gh", "release", "view", "-R", "obra/superpowers",
                       "--json", "tagName", "--jq", ".tagName"], self.read_log())
        self.assertEqual(set(self.link_targets()), {"alpha", "gamma"})


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m unittest discover -s tests -p 'test_sync_superpowers.py' -v`
Expected: both tests FAIL with a non-zero exit code. The stderr names a missing `sync_superpowers.py`.

- [ ] **Step 3: Write the script**

Create `skills/sync-superpowers/scripts/sync_superpowers.py`:

```python
#!/usr/bin/env python3
"""Install or update obra/superpowers for Claude Code, Codex, and Cursor.

All three tools read one git checkout pinned to a release tag. Claude Code
loads the checkout as a local-path plugin marketplace. Codex and Cursor load
~/.agents/skills symlinks into the checkout.
"""

from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


REPO_SLUG = "obra/superpowers"
REPO_URL = f"https://github.com/{REPO_SLUG}.git"
SKILLS_DIR = "skills"
SKILL_MD = "SKILL.md"
DEFAULT_CHECKOUT_DIR = Path.home() / ".local" / "share" / "superpowers"
DEFAULT_AGENTS_SKILLS_DIR = Path.home() / ".agents" / SKILLS_DIR
REQUIRED_TOOLS = ("git", "claude", "codex")


class SyncError(Exception):
    """A failure that stops the run with a message for the user."""


@dataclass
class Report:
    dry_run: bool
    warnings: list[str] = field(default_factory=list)

    def action(self, message: str) -> None:
        print(f"would {message}" if self.dry_run else message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)


@dataclass(frozen=True)
class Release:
    tag: str
    skills: tuple[str, ...]


@dataclass
class LinkChanges:
    created: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    pruned: list[str] = field(default_factory=list)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install or update obra/superpowers for Claude Code, Codex, and Cursor.",
    )
    parser.add_argument("--version", help="Release tag to install, for example v7.0.2. Default: latest release.")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without changing anything.")
    parser.add_argument("--checkout-dir", type=Path, default=DEFAULT_CHECKOUT_DIR, help="Managed checkout location.")
    parser.add_argument(
        "--agents-skills-dir",
        type=Path,
        default=DEFAULT_AGENTS_SKILLS_DIR,
        help="Skill links for Codex and Cursor.",
    )
    parser.add_argument("--repo-url", default=REPO_URL, help="Clone source.")
    return parser.parse_args()


def run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise SyncError(f"command failed: {shlex.join(cmd)}\n{result.stderr.strip()}")
    return result.stdout


def git(repo: Path, *args: str) -> str:
    return run(["git", "-C", str(repo), *args])


def require_tools(need_gh: bool) -> None:
    tools = REQUIRED_TOOLS + (("gh",) if need_gh else ())
    missing = [tool for tool in tools if shutil.which(tool) is None]
    if missing:
        raise SyncError(f"missing required tools on PATH: {', '.join(missing)}")


def resolve_tag(version: str | None) -> str:
    if version:
        return version
    tag = run(["gh", "release", "view", "-R", REPO_SLUG, "--json", "tagName", "--jq", ".tagName"]).strip()
    if not tag:
        raise SyncError(f"gh returned no latest release for {REPO_SLUG}")
    return tag


def prepare_repo(checkout_dir: Path, repo_url: str) -> Path:
    if not os.path.lexists(checkout_dir):
        checkout_dir.parent.mkdir(parents=True, exist_ok=True)
        run(["git", "clone", "--quiet", "--", repo_url, str(checkout_dir)])
    git(checkout_dir, "fetch", "--quiet", "--tags", "--force", "origin")
    return checkout_dir


def list_tag_skills(repo_dir: Path, tag: str) -> tuple[str, ...]:
    listing = git(repo_dir, "ls-tree", "-r", "-z", "--name-only", f"refs/tags/{tag}", "--", SKILLS_DIR)
    paths = listing.split("\0")
    names = sorted(
        parts[1]
        for parts in (path.split("/") for path in paths)
        if len(parts) == 3 and parts[2] == SKILL_MD
    )
    if not names:
        raise SyncError(f"tag {tag} has no {SKILLS_DIR}/<name>/{SKILL_MD}")
    return tuple(names)


def preflight(version: str | None, repo_url: str, checkout_dir: Path) -> Release:
    require_tools(need_gh=version is None)
    tag = resolve_tag(version)
    repo_dir = prepare_repo(checkout_dir, repo_url)
    try:
        git(repo_dir, "rev-parse", "--verify", "--quiet", f"refs/tags/{tag}")
    except SyncError:
        raise SyncError(f"tag {tag} not found in {repo_url}") from None
    return Release(tag=tag, skills=list_tag_skills(repo_dir, tag))


def checkout_tag(checkout_dir: Path, tag: str, report: Report) -> None:
    report.action(f"check out {tag} in {checkout_dir}")
    if not report.dry_run:
        git(checkout_dir, "checkout", "--quiet", "--detach", f"refs/tags/{tag}")


def sync_links(agents_dir: Path, checkout_dir: Path, skills: tuple[str, ...], report: Report) -> LinkChanges:
    skills_root = checkout_dir / SKILLS_DIR
    changes = LinkChanges()
    for name in skills:
        link = agents_dir / name
        target = skills_root / name
        if link.is_symlink():
            if Path(os.readlink(link)) == target:
                continue
            report.action(f"update link {link} -> {target}")
            changes.updated.append(name)
            if not report.dry_run:
                link.unlink()
                link.symlink_to(target, target_is_directory=True)
        else:
            report.action(f"create link {link} -> {target}")
            changes.created.append(name)
            if not report.dry_run:
                link.parent.mkdir(parents=True, exist_ok=True)
                link.symlink_to(target, target_is_directory=True)
    return changes


def print_summary(release: Release, links: LinkChanges, report: Report) -> None:
    print()
    suffix = " (dry run: nothing changed)" if report.dry_run else ""
    print(f"superpowers {release.tag}{suffix}")
    print(
        f"links: {len(links.created)} created, {len(links.updated)} updated, "
        f"{len(links.pruned)} removed, {len(release.skills)} total"
    )
    for warning in report.warnings:
        print(f"warning: {warning}")
    if not report.dry_run:
        print("Restart Claude Code, Codex, and Cursor to load the change.")


def main() -> int:
    args = parse_args()
    checkout_dir = args.checkout_dir.expanduser().resolve()
    agents_dir = args.agents_skills_dir.expanduser()
    report = Report(dry_run=args.dry_run)
    completed = None
    try:
        release = preflight(args.version, args.repo_url, checkout_dir)
        completed = "preflight"
        checkout_tag(checkout_dir, release.tag, report)
        completed = "checkout"
        links = sync_links(agents_dir, checkout_dir, release.skills, report)
        completed = "links"
    except (SyncError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        if completed:
            print(f"last completed phase: {completed}; run again to finish", file=sys.stderr)
        return 1
    print_summary(release, links, report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `chmod +x skills/sync-superpowers/scripts/sync_superpowers.py && python3 -m unittest discover -s tests -p 'test_sync_superpowers.py' -v`
Expected: 2 tests, `OK`.

- [ ] **Step 5: Commit**

```bash
git add tests/test_sync_superpowers.py skills/sync-superpowers/scripts/sync_superpowers.py
git commit -m "feat(sync-superpowers): check out release tag and link skills"
```

---

### Task 2: Idempotence, pruning, and duplicate warnings

**Files:**
- Modify: `skills/sync-superpowers/scripts/sync_superpowers.py`
- Modify: `tests/test_sync_superpowers.py`

- [ ] **Step 1: Write the failing tests**

Add these methods to `SyncSuperpowersTest`:

```python
    def test_second_run_changes_no_links(self) -> None:
        self.assert_ok(self.run_sync("--version", "v1.0.0"))
        before = self.link_targets()

        result = self.run_sync("--version", "v1.0.0")

        self.assert_ok(result)
        self.assertEqual(self.link_targets(), before)
        self.assertIn("links: 0 created, 0 updated, 0 removed, 2 total", result.stdout)

    def test_upgrade_adds_new_skills_and_prunes_removed_ones(self) -> None:
        self.assert_ok(self.run_sync("--version", "v1.0.0"))
        unrelated_target = self.root / "elsewhere"
        unrelated_target.mkdir()
        (self.agents / "mine").symlink_to(unrelated_target)

        result = self.run_sync("--version", "v1.1.0")

        self.assert_ok(result)
        self.assertEqual(
            self.link_targets(),
            {
                "alpha": self.checkout / "skills" / "alpha",
                "gamma": self.checkout / "skills" / "gamma",
                "mine": unrelated_target,
            },
        )
        self.assertIn("links: 1 created, 0 updated, 1 removed, 2 total", result.stdout)

    def test_stale_link_to_other_target_is_replaced(self) -> None:
        self.agents.mkdir(parents=True)
        (self.agents / "alpha").symlink_to(self.root / "old-plugin-cache" / "alpha")

        result = self.run_sync("--version", "v1.0.0")

        self.assert_ok(result)
        self.assertEqual(self.link_targets()["alpha"], self.checkout / "skills" / "alpha")
        self.assertIn("links: 1 created, 1 updated, 0 removed, 2 total", result.stdout)

    def test_pruning_only_removes_links_into_the_checkout(self) -> None:
        self.assert_ok(self.run_sync("--version", "v1.0.0"))
        other_skill = self.root / "other" / "skills" / "beta-other"
        other_skill.mkdir(parents=True)
        (self.agents / "beta-other").symlink_to(other_skill)
        (self.agents / "real-dir").mkdir()
        for name in ("alpha", "beta"):
            (self.agents / name).unlink()
            (self.agents / name).symlink_to(os.path.relpath(self.checkout / "skills" / name, self.agents))

        result = self.run_sync("--version", "v1.1.0")

        self.assert_ok(result)
        self.assertEqual(set(self.link_targets()), {"alpha", "gamma", "beta-other"})
        self.assertTrue((self.agents / "real-dir").is_dir())
        self.assertIn("links: 1 created, 0 updated, 1 removed, 2 total", result.stdout)

    def test_superpowers_skill_in_other_skill_roots_warns(self) -> None:
        roots = [self.home / root / "skills" for root in (".claude", ".codex", ".cursor")]
        for skills_dir in roots:
            (skills_dir / "alpha").mkdir(parents=True)

        result = self.run_sync("--version", "v1.0.0")

        self.assert_ok(result)
        for skills_dir in roots:
            self.assertIn(f"warning: {skills_dir / 'alpha'} duplicates superpowers skill alpha", result.stdout)
            self.assertTrue((skills_dir / "alpha").is_dir())
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m unittest discover -s tests -p 'test_sync_superpowers.py' -v`
Expected: `test_upgrade_adds_new_skills_and_prunes_removed_ones` FAILS (`beta` link still present). `test_superpowers_skill_in_other_skill_roots_warns` FAILS (no warning). `test_pruning_only_removes_links_into_the_checkout` FAILS (`beta` not pruned). The other two pass.

- [ ] **Step 3: Add pruning and duplicate warnings**

In `sync_superpowers.py`, add this constant after `REQUIRED_TOOLS`:

```python
# Cursor reads all of these roots, and Codex reads ~/.codex/skills, so a
# superpowers skill in one of them appears twice.
DUPLICATE_SKILL_ROOTS = (".claude", ".codex", ".cursor")
```

Replace `sync_links` with:

```python
def link_target(link: Path) -> Path:
    """Return the absolute target of a symlink, without following the final component."""
    target = Path(os.readlink(link))
    if not target.is_absolute():
        target = link.parent / target
    # The OS resolves ".." through the real parent directory, so resolve the
    # parent through the file system, not as text. The skill directory itself
    # may already be gone after a tag change, so do not resolve the last part.
    return Path(os.path.realpath(target.parent)) / target.name


def sync_links(agents_dir: Path, checkout_dir: Path, skills: tuple[str, ...], report: Report) -> LinkChanges:
    skills_root = checkout_dir / SKILLS_DIR
    changes = LinkChanges()
    for name in skills:
        link = agents_dir / name
        target = skills_root / name
        if link.is_symlink():
            if link_target(link) == target:
                continue
            report.action(f"update link {link} -> {target}")
            changes.updated.append(name)
            if not report.dry_run:
                link.unlink()
                link.symlink_to(target, target_is_directory=True)
        else:
            report.action(f"create link {link} -> {target}")
            changes.created.append(name)
            if not report.dry_run:
                link.parent.mkdir(parents=True, exist_ok=True)
                link.symlink_to(target, target_is_directory=True)

    # Only links into our checkout are ours to prune. Leave every other entry alone.
    existing = sorted(agents_dir.iterdir()) if agents_dir.is_dir() else []
    for link in existing:
        if link.name in skills or not link.is_symlink():
            continue
        if link_target(link).parent == skills_root:
            report.action(f"remove link {link}")
            changes.pruned.append(link.name)
            if not report.dry_run:
                link.unlink()
    return changes


def warn_duplicates(skills: tuple[str, ...], report: Report) -> None:
    for root in DUPLICATE_SKILL_ROOTS:
        skills_dir = Path.home() / root / SKILLS_DIR
        for name in skills:
            path = skills_dir / name
            if os.path.lexists(path):
                report.warn(
                    f"{path} duplicates superpowers skill {name}; remove it so each tool lists the skill once"
                )
```

In `main`, replace the line `links = sync_links(agents_dir, checkout_dir, release.skills, report)` with:

```python
        links = sync_links(agents_dir, checkout_dir, release.skills, report)
        warn_duplicates(release.skills, report)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m unittest discover -s tests -p 'test_sync_superpowers.py' -v`
Expected: 7 tests, `OK`.

- [ ] **Step 5: Commit**

```bash
git add tests/test_sync_superpowers.py skills/sync-superpowers/scripts/sync_superpowers.py
git commit -m "feat(sync-superpowers): prune removed skills and warn on duplicates"
```

---

### Task 3: Preflight refusals

**Files:**
- Modify: `skills/sync-superpowers/scripts/sync_superpowers.py`
- Modify: `tests/test_sync_superpowers.py`

- [ ] **Step 1: Write the failing tests**

Add these methods to `SyncSuperpowersTest`:

```python
    def test_dirty_checkout_is_refused(self) -> None:
        self.assert_ok(self.run_sync("--version", "v1.0.0"))
        (self.checkout / "local-edit.txt").write_text("edit\n", encoding="utf-8")
        self.clear_log()

        result = self.run_sync("--version", "v1.1.0")

        self.assertEqual(result.returncode, 1)
        self.assertIn("has local changes", result.stderr)
        self.assertEqual(self.checkout_tag(), "v1.0.0")
        self.assertEqual(self.tool_calls("claude", "codex"), [])

    def test_wrong_origin_is_refused(self) -> None:
        self.assert_ok(self.run_sync("--version", "v1.0.0"))
        git(self.checkout, "remote", "set-url", "origin", "https://example.com/other.git")

        result = self.run_sync("--version", "v1.1.0")

        self.assertEqual(result.returncode, 1)
        self.assertIn("origin is https://example.com/other.git", result.stderr)

    def test_real_directory_in_agents_dir_is_refused(self) -> None:
        (self.agents / "alpha").mkdir(parents=True)

        result = self.run_sync("--version", "v1.0.0")

        self.assertEqual(result.returncode, 1)
        self.assertIn("is a real file or directory", result.stderr)
        self.assertFalse((self.agents / "alpha").is_symlink())
        self.assertFalse((self.agents / "beta").exists())
        self.assertEqual(self.tool_calls("claude", "codex"), [])

    def test_unknown_tag_is_refused(self) -> None:
        result = self.run_sync("--version", "v9.9.9")

        self.assertEqual(result.returncode, 1)
        self.assertIn("tag v9.9.9 not found", result.stderr)

    def test_failed_first_run_does_not_block_next_run(self) -> None:
        self.assertEqual(self.run_sync("--version", "v9.9.9").returncode, 1)

        result = self.run_sync("--version", "v1.0.0")

        self.assert_ok(result)
        self.assertEqual(self.checkout_tag(), "v1.0.0")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m unittest discover -s tests -p 'test_sync_superpowers.py' -v`
Expected: `test_dirty_checkout_is_refused`, `test_wrong_origin_is_refused`, and `test_real_directory_in_agents_dir_is_refused` FAIL. `test_unknown_tag_is_refused` and `test_failed_first_run_does_not_block_next_run` pass.

- [ ] **Step 3: Add the checks**

In `sync_superpowers.py`, add these functions after `resolve_tag`:

```python
def require_clean_checkout(checkout_dir: Path, repo_url: str) -> None:
    if not (checkout_dir / ".git").exists():
        raise SyncError(f"{checkout_dir} exists but is not a git checkout")
    origin = git(checkout_dir, "remote", "get-url", "origin").strip()
    if origin != repo_url:
        raise SyncError(f"{checkout_dir} origin is {origin}, expected {repo_url}")
    if git(checkout_dir, "status", "--porcelain", "--untracked-files=all").strip():
        raise SyncError(f"{checkout_dir} has local changes; commit, move, or discard them first")


def require_link_slots(agents_dir: Path, skills: tuple[str, ...]) -> None:
    for name in skills:
        path = agents_dir / name
        if os.path.lexists(path) and not path.is_symlink():
            raise SyncError(f"{path} is a real file or directory; move it, then run again")
```

Replace `prepare_repo` with:

```python
def prepare_repo(checkout_dir: Path, repo_url: str) -> Path:
    if os.path.lexists(checkout_dir):
        require_clean_checkout(checkout_dir, repo_url)
    else:
        checkout_dir.parent.mkdir(parents=True, exist_ok=True)
        run(["git", "clone", "--quiet", "--", repo_url, str(checkout_dir)])
    git(checkout_dir, "fetch", "--quiet", "--tags", "--force", "origin")
    return checkout_dir
```

Replace `preflight` with:

```python
def preflight(version: str | None, repo_url: str, checkout_dir: Path, agents_dir: Path) -> Release:
    require_tools(need_gh=version is None)
    tag = resolve_tag(version)
    repo_dir = prepare_repo(checkout_dir, repo_url)
    try:
        git(repo_dir, "rev-parse", "--verify", "--quiet", f"refs/tags/{tag}")
    except SyncError:
        raise SyncError(f"tag {tag} not found in {repo_url}") from None
    skills = list_tag_skills(repo_dir, tag)
    require_link_slots(agents_dir, skills)
    return Release(tag=tag, skills=skills)
```

In `main`, replace `release = preflight(args.version, args.repo_url, checkout_dir)` with:

```python
        release = preflight(args.version, args.repo_url, checkout_dir, agents_dir)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m unittest discover -s tests -p 'test_sync_superpowers.py' -v`
Expected: 12 tests, `OK`.

- [ ] **Step 5: Commit**

```bash
git add tests/test_sync_superpowers.py skills/sync-superpowers/scripts/sync_superpowers.py
git commit -m "feat(sync-superpowers): refuse dirty checkouts and real skill directories"
```

---

### Task 4: Claude Code plugin

**Files:**
- Modify: `skills/sync-superpowers/scripts/sync_superpowers.py`
- Modify: `tests/test_sync_superpowers.py`

- [ ] **Step 1: Write the failing tests**

Add these methods to `SyncSuperpowersTest`:

```python
    def test_first_run_adds_marketplace_and_installs_plugin(self) -> None:
        result = self.run_sync("--version", "v1.0.0")

        self.assert_ok(result)
        claude_writes = [c for c in self.tool_calls("claude") if "list" not in c]
        self.assertEqual(
            claude_writes,
            [
                ["claude", "plugin", "marketplace", "add", str(self.checkout)],
                ["claude", "plugin", "install", PLUGIN_ID],
            ],
        )
        self.assertIn(f"claude: {PLUGIN_ID} scope=user version=1.0.0", result.stdout)

    def test_second_run_updates_marketplace_and_plugin(self) -> None:
        self.assert_ok(self.run_sync("--version", "v1.0.0"))
        self.clear_log()
        self.update_state(plugin_version="1.1.0")

        result = self.run_sync("--version", "v1.1.0")

        self.assert_ok(result)
        claude_writes = [c for c in self.tool_calls("claude") if "list" not in c]
        self.assertEqual(
            claude_writes,
            [
                ["claude", "plugin", "marketplace", "update", MARKETPLACE],
                ["claude", "plugin", "update", PLUGIN_ID],
            ],
        )

    def test_marketplace_pointing_elsewhere_is_replaced(self) -> None:
        self.update_state(
            claude_marketplaces=[{"name": MARKETPLACE, "source": "github", "repo": "obra/superpowers"}],
            claude_plugins=[{"id": PLUGIN_ID, "version": "0.9.0", "scope": "user", "enabled": True}],
        )

        result = self.run_sync("--version", "v1.0.0")

        self.assert_ok(result)
        claude_writes = [c for c in self.tool_calls("claude") if "list" not in c]
        self.assertEqual(
            claude_writes,
            [
                ["claude", "plugin", "marketplace", "remove", MARKETPLACE],
                ["claude", "plugin", "marketplace", "add", str(self.checkout)],
                ["claude", "plugin", "install", PLUGIN_ID],
            ],
        )

    def test_other_superpowers_plugins_uninstalled_at_user_scope_only(self) -> None:
        self.update_state(
            claude_plugins=[
                {"id": "superpowers@superpowers-marketplace", "version": "5.1.0", "scope": "user", "enabled": True},
                {"id": "superpowers@superpowers-marketplace", "version": "5.1.0", "scope": "local",
                 "enabled": True, "projectPath": "/work/yt"},
                {"id": "superpowers@claude-plugins-official", "version": "7.0.2", "scope": "user", "enabled": False},
                {"id": "safety-net@cc-marketplace", "version": "1.0.0", "scope": "user", "enabled": True},
            ],
        )

        result = self.run_sync("--version", "v1.0.0")

        self.assert_ok(result)
        uninstalls = [c for c in self.tool_calls("claude") if c[2] == "uninstall"]
        self.assertEqual(
            uninstalls,
            [
                ["claude", "plugin", "uninstall", "superpowers@superpowers-marketplace"],
                ["claude", "plugin", "uninstall", "superpowers@claude-plugins-official"],
            ],
        )
        self.assertIn("superpowers@superpowers-marketplace is installed at local scope for /work/yt", result.stdout)
        remaining = {(p["id"], p["scope"]) for p in self.read_state()["claude_plugins"]}
        self.assertEqual(
            remaining,
            {
                ("superpowers@superpowers-marketplace", "local"),
                ("safety-net@cc-marketplace", "user"),
                (PLUGIN_ID, "user"),
            },
        )

    def test_claude_version_mismatch_fails(self) -> None:
        self.update_state(plugin_version="0.0.1")

        result = self.run_sync("--version", "v1.0.0")

        self.assertEqual(result.returncode, 1)
        self.assertIn("expected 1.0.0", result.stderr)
        self.assertIn("last completed phase: checkout", result.stderr)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m unittest discover -s tests -p 'test_sync_superpowers.py' -v`
Expected: the five new tests FAIL, because the script makes no `claude` calls.

- [ ] **Step 3: Add the Claude phase**

In `sync_superpowers.py`, add `import json` to the imports, keeping alphabetical order:

```python
import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
```

Add these constants after `REPO_URL`:

```python
MARKETPLACE = "superpowers-dev"
PLUGIN = "superpowers"
PLUGIN_ID = f"{PLUGIN}@{MARKETPLACE}"
USER_SCOPE = "user"
DIRECTORY_SOURCE = "directory"
```

Add these functions after `checkout_tag`:

```python
def run_write(cmd: list[str], report: Report) -> None:
    report.action(f"run: {shlex.join(cmd)}")
    if not report.dry_run:
        run(cmd)


def read_json(cmd: list[str]) -> object:
    output = run(cmd)
    try:
        return json.loads(output)
    except json.JSONDecodeError as error:
        raise SyncError(f"invalid JSON from {shlex.join(cmd)}: {error}") from None


def points_at(marketplace: dict, checkout_dir: Path) -> bool:
    path = marketplace.get("path")
    return (
        marketplace.get("source") == DIRECTORY_SOURCE
        and path is not None
        and Path(path).resolve() == checkout_dir
    )


def verify_claude(tag: str) -> dict:
    expected = tag.removeprefix("v")
    for plugin in read_json(["claude", "plugin", "list", "--json"]):
        if plugin.get("id") == PLUGIN_ID and plugin.get("scope") == USER_SCOPE:
            if plugin.get("version") != expected or not plugin.get("enabled"):
                raise SyncError(
                    f"Claude reports {PLUGIN_ID} version {plugin.get('version')} "
                    f"enabled={plugin.get('enabled')}; expected {expected} enabled"
                )
            return plugin
    raise SyncError(f"Claude does not list {PLUGIN_ID} at user scope after install")


def sync_claude(checkout_dir: Path, tag: str, report: Report) -> dict | None:
    marketplaces = read_json(["claude", "plugin", "marketplace", "list", "--json"])
    current = next((m for m in marketplaces if m.get("name") == MARKETPLACE), None)
    add = ["claude", "plugin", "marketplace", "add", str(checkout_dir)]
    if current is None:
        run_write(add, report)
    elif not points_at(current, checkout_dir):
        # Removing the marketplace also uninstalls its plugins, so the
        # plugin list read below sees ours as missing and reinstalls it.
        run_write(["claude", "plugin", "marketplace", "remove", MARKETPLACE], report)
        run_write(add, report)
    else:
        run_write(["claude", "plugin", "marketplace", "update", MARKETPLACE], report)

    plugins = read_json(["claude", "plugin", "list", "--json"])
    installed = any(p.get("id") == PLUGIN_ID and p.get("scope") == USER_SCOPE for p in plugins)
    run_write(["claude", "plugin", "update" if installed else "install", PLUGIN_ID], report)

    uninstalled: set[str] = set()
    for plugin in plugins:
        plugin_id = plugin.get("id", "")
        if plugin_id == PLUGIN_ID or plugin_id.split("@")[0] != PLUGIN:
            continue
        scope = plugin.get("scope")
        if scope == USER_SCOPE:
            if plugin_id not in uninstalled:
                run_write(["claude", "plugin", "uninstall", plugin_id], report)
                uninstalled.add(plugin_id)
        else:
            project = plugin.get("projectPath", "an unknown project")
            report.warn(f"Claude plugin {plugin_id} is installed at {scope} scope for {project}; left unchanged")

    if report.dry_run:
        return None
    return verify_claude(tag)
```

Replace `print_summary` with:

```python
def print_summary(release: Release, claude_plugin: dict | None, links: LinkChanges, report: Report) -> None:
    print()
    suffix = " (dry run: nothing changed)" if report.dry_run else ""
    print(f"superpowers {release.tag}{suffix}")
    if claude_plugin:
        print(
            f"claude: {claude_plugin['id']} scope={claude_plugin['scope']} "
            f"version={claude_plugin['version']}"
        )
    print(
        f"links: {len(links.created)} created, {len(links.updated)} updated, "
        f"{len(links.pruned)} removed, {len(release.skills)} total"
    )
    for warning in report.warnings:
        print(f"warning: {warning}")
    if not report.dry_run:
        print("Restart Claude Code, Codex, and Cursor to load the change.")
```

Replace `main` with:

```python
def main() -> int:
    args = parse_args()
    checkout_dir = args.checkout_dir.expanduser().resolve()
    agents_dir = args.agents_skills_dir.expanduser()
    report = Report(dry_run=args.dry_run)
    completed = None
    try:
        release = preflight(args.version, args.repo_url, checkout_dir, agents_dir)
        completed = "preflight"
        checkout_tag(checkout_dir, release.tag, report)
        completed = "checkout"
        claude_plugin = sync_claude(checkout_dir, release.tag, report)
        completed = "claude"
        links = sync_links(agents_dir, checkout_dir, release.skills, report)
        warn_duplicates(release.skills, report)
        completed = "links"
    except (SyncError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        if completed:
            print(f"last completed phase: {completed}; run again to finish", file=sys.stderr)
        return 1
    print_summary(release, claude_plugin, links, report)
    return 0
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m unittest discover -s tests -p 'test_sync_superpowers.py' -v`
Expected: 17 tests, `OK`.

- [ ] **Step 5: Commit**

```bash
git add tests/test_sync_superpowers.py skills/sync-superpowers/scripts/sync_superpowers.py
git commit -m "feat(sync-superpowers): install plugin in Claude Code from the checkout"
```

---

### Task 5: Codex plugin removal

**Files:**
- Modify: `skills/sync-superpowers/scripts/sync_superpowers.py`
- Modify: `tests/test_sync_superpowers.py`

- [ ] **Step 1: Write the failing test**

Add this method to `SyncSuperpowersTest`:

```python
    def test_codex_superpowers_plugins_and_marketplace_removed(self) -> None:
        self.update_state(
            codex_plugins=[
                {"pluginId": "superpowers@superpowers-dev", "name": "superpowers", "installed": True},
                {"pluginId": "superpowers@openai-curated-remote", "name": "superpowers", "installed": True},
                {"pluginId": "github@openai-curated-remote", "name": "github", "installed": True},
            ],
            codex_marketplaces=[
                {"name": MARKETPLACE, "root": "/tmp/x"},
                {"name": "openai-curated", "root": "/tmp/y"},
            ],
        )

        result = self.run_sync("--version", "v1.0.0")

        self.assert_ok(result)
        codex_writes = [c for c in self.tool_calls("codex") if "list" not in c]
        self.assertEqual(
            codex_writes,
            [
                ["codex", "plugin", "remove", "superpowers@superpowers-dev"],
                ["codex", "plugin", "remove", "superpowers@openai-curated-remote"],
                ["codex", "plugin", "marketplace", "remove", MARKETPLACE],
            ],
        )
        state = self.read_state()
        self.assertEqual([p["pluginId"] for p in state["codex_plugins"]], ["github@openai-curated-remote"])
        self.assertEqual([m["name"] for m in state["codex_marketplaces"]], ["openai-curated"])
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m unittest discover -s tests -p 'test_sync_superpowers.py' -v`
Expected: `test_codex_superpowers_plugins_and_marketplace_removed` FAILS with an empty `codex_writes` list.

- [ ] **Step 3: Add the Codex phase**

In `sync_superpowers.py`, add these functions after `sync_claude`:

```python
def installed_codex_superpowers() -> list[str]:
    listing = read_json(["codex", "plugin", "list", "--json"])
    return [
        plugin["pluginId"]
        for plugin in listing.get("installed", [])
        if plugin.get("name") == PLUGIN and plugin.get("installed")
    ]


def sync_codex(report: Report) -> None:
    # Codex reads ~/.agents/skills, so any superpowers plugin would duplicate the links.
    for plugin_id in installed_codex_superpowers():
        run_write(["codex", "plugin", "remove", plugin_id], report)

    listing = read_json(["codex", "plugin", "marketplace", "list", "--json"])
    if any(m.get("name") == MARKETPLACE for m in listing.get("marketplaces", [])):
        run_write(["codex", "plugin", "marketplace", "remove", MARKETPLACE], report)

    if not report.dry_run:
        remaining = installed_codex_superpowers()
        if remaining:
            raise SyncError(f"Codex still lists installed superpowers plugins: {', '.join(remaining)}")
```

In `main`, replace these two lines:

```python
        claude_plugin = sync_claude(checkout_dir, release.tag, report)
        completed = "claude"
```

with:

```python
        claude_plugin = sync_claude(checkout_dir, release.tag, report)
        completed = "claude"
        sync_codex(report)
        completed = "codex"
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m unittest discover -s tests -p 'test_sync_superpowers.py' -v`
Expected: 18 tests, `OK`.

- [ ] **Step 5: Commit**

```bash
git add tests/test_sync_superpowers.py skills/sync-superpowers/scripts/sync_superpowers.py
git commit -m "feat(sync-superpowers): remove superpowers plugins from Codex"
```

---

### Task 6: Dry run and failure reporting

**Files:**
- Modify: `skills/sync-superpowers/scripts/sync_superpowers.py`
- Modify: `tests/test_sync_superpowers.py`

- [ ] **Step 1: Write the tests**

Add these methods to `SyncSuperpowersTest`:

```python
    def test_dry_run_without_checkout_changes_nothing(self) -> None:
        self.update_state(
            codex_plugins=[{"pluginId": "superpowers@superpowers-dev", "name": "superpowers", "installed": True}],
        )
        before = self.read_state()

        result = self.run_sync("--version", "v1.0.0", "--dry-run")

        self.assert_ok(result)
        self.assertFalse(self.checkout.exists())
        self.assertFalse(self.agents.exists())
        self.assertEqual(self.read_state(), before)
        for call in self.tool_calls("claude", "codex"):
            self.assertIn("list", call)
        self.assertIn("would run: claude plugin install superpowers@superpowers-dev", result.stdout)
        self.assertIn("would run: codex plugin remove superpowers@superpowers-dev", result.stdout)
        self.assertIn(f"would create link {self.agents / 'alpha'}", result.stdout)
        self.assertIn("(dry run: nothing changed)", result.stdout)

    def test_failed_command_stops_run(self) -> None:
        self.update_state(fail="claude plugin install")

        result = self.run_sync("--version", "v1.0.0")

        self.assertEqual(result.returncode, 1)
        self.assertIn("command failed: claude plugin install superpowers@superpowers-dev", result.stderr)
        self.assertIn("simulated failure", result.stderr)
        self.assertIn("last completed phase: checkout", result.stderr)
        self.assertFalse(self.agents.exists())
```

- [ ] **Step 2: Run the tests**

Run: `python3 -m unittest discover -s tests -p 'test_sync_superpowers.py' -v`
Expected: `test_dry_run_without_checkout_changes_nothing` FAILS, because `prepare_repo` clones into `--checkout-dir`. `test_failed_command_stops_run` passes, because the error path exists since Task 1. Keep it as a regression test.

- [ ] **Step 3: Clone into a temporary directory during a dry run**

In `sync_superpowers.py`, add `import tempfile` to the imports:

```python
import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
```

Replace `prepare_repo` with:

```python
def prepare_repo(checkout_dir: Path, repo_url: str, dry_run: bool, temp_dirs: list[Path]) -> Path:
    """Return a repository with fresh tags: the checkout, or a temporary clone in a dry run."""
    if os.path.lexists(checkout_dir):
        require_clean_checkout(checkout_dir, repo_url)
        repo_dir = checkout_dir
    else:
        if dry_run:
            temp_dir = Path(tempfile.mkdtemp(prefix="sync-superpowers-"))
            temp_dirs.append(temp_dir)
            repo_dir = temp_dir / "checkout"
        else:
            checkout_dir.parent.mkdir(parents=True, exist_ok=True)
            repo_dir = checkout_dir
        # The temporary clone is read only with ls-tree, so it skips the working tree.
        # The real checkout gets one, so a failed run leaves it clean for the next run.
        clone_mode = ["--no-checkout"] if dry_run else []
        run(["git", "clone", "--quiet", *clone_mode, "--", repo_url, str(repo_dir)])
    git(repo_dir, "fetch", "--quiet", "--tags", "--force", "origin")
    return repo_dir
```

Replace `preflight` with:

```python
def preflight(
    version: str | None,
    repo_url: str,
    checkout_dir: Path,
    agents_dir: Path,
    dry_run: bool,
    temp_dirs: list[Path],
) -> Release:
    require_tools(need_gh=version is None)
    tag = resolve_tag(version)
    repo_dir = prepare_repo(checkout_dir, repo_url, dry_run, temp_dirs)
    try:
        git(repo_dir, "rev-parse", "--verify", "--quiet", f"refs/tags/{tag}")
    except SyncError:
        raise SyncError(f"tag {tag} not found in {repo_url}") from None
    skills = list_tag_skills(repo_dir, tag)
    require_link_slots(agents_dir, skills)
    return Release(tag=tag, skills=skills)
```

Replace `main` with:

```python
def main() -> int:
    args = parse_args()
    checkout_dir = args.checkout_dir.expanduser().resolve()
    agents_dir = args.agents_skills_dir.expanduser()
    report = Report(dry_run=args.dry_run)
    temp_dirs: list[Path] = []
    completed = None
    try:
        release = preflight(args.version, args.repo_url, checkout_dir, agents_dir, args.dry_run, temp_dirs)
        completed = "preflight"
        checkout_tag(checkout_dir, release.tag, report)
        completed = "checkout"
        claude_plugin = sync_claude(checkout_dir, release.tag, report)
        completed = "claude"
        sync_codex(report)
        completed = "codex"
        links = sync_links(agents_dir, checkout_dir, release.skills, report)
        warn_duplicates(release.skills, report)
        completed = "links"
    except (SyncError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        if completed:
            print(f"last completed phase: {completed}; run again to finish", file=sys.stderr)
        return 1
    finally:
        for temp_dir in temp_dirs:
            shutil.rmtree(temp_dir)
    print_summary(release, claude_plugin, links, report)
    return 0
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m unittest discover -s tests -p 'test_sync_superpowers.py' -v`
Expected: 20 tests, `OK`.

Also run the full suite to check nothing else broke:
Run: `python3 -m unittest discover -s tests -v`
Expected: `OK`.

- [ ] **Step 5: Commit**

```bash
git add tests/test_sync_superpowers.py skills/sync-superpowers/scripts/sync_superpowers.py
git commit -m "feat(sync-superpowers): support dry run without a checkout"
```

---

### Task 7: Skill documentation

**Files:**
- Create: `skills/sync-superpowers/SKILL.md`
- Create: `skills/sync-superpowers/agents/openai.yaml`

- [ ] **Step 1: Write `SKILL.md`**

Create `skills/sync-superpowers/SKILL.md`:

````markdown
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
| `origin is ..., expected ...` | The checkout belongs to another repo. Move it, or pass `--checkout-dir`. |
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
````

- [ ] **Step 2: Write `agents/openai.yaml`**

Create `skills/sync-superpowers/agents/openai.yaml`:

```yaml
interface:
  display_name: "Sync Superpowers"
  short_description: "Install or update superpowers for Claude, Codex, and Cursor"
  default_prompt: "Use $sync-superpowers to update superpowers to the latest release."
```

- [ ] **Step 3: Check the skill frontmatter parses**

Run:

```bash
python3 - <<'EOF'
from pathlib import Path
text = Path("skills/sync-superpowers/SKILL.md").read_text(encoding="utf-8")
front = text.split("---")[1]
fields = dict(line.split(": ", 1) for line in front.strip().splitlines())
assert fields["name"] == "sync-superpowers", fields
assert fields["description"].startswith("Use when"), fields
print("ok")
EOF
```

Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add skills/sync-superpowers/SKILL.md skills/sync-superpowers/agents/openai.yaml
git commit -m "docs(sync-superpowers): add skill instructions"
```

---

### Task 8: Real-machine acceptance

This task changes the user's real Claude Code and Codex setup. The user approved these changes in the design. Run each step in order and stop on any failure.

**Files:** none. If a step reveals a bug, fix it with a failing test first, as in Tasks 1-6.

- [ ] **Step 1: Record the starting state**

Run:

```bash
claude plugin list --json | python3 -c "import json,sys;[print(p['id'],p['scope'],p['version'],p['enabled']) for p in json.load(sys.stdin) if p['id'].startswith('superpowers@')]"
codex plugin list --json | python3 -c "import json,sys;[print(p['pluginId'],p['version']) for p in json.load(sys.stdin)['installed'] if p['name']=='superpowers']"
```

Expected on 2026-11-22: Claude lists `superpowers@superpowers-marketplace` (user and local) and `superpowers@claude-plugins-official`. Codex lists `superpowers@superpowers-dev` and `superpowers@openai-curated-remote`.

- [ ] **Step 2: Dry run**

Run: `python3 skills/sync-superpowers/scripts/sync_superpowers.py --dry-run`
Expected:
- exit 0
- `would run: claude plugin marketplace add /Users/<user>/.local/share/superpowers`
- `would run: claude plugin install superpowers@superpowers-dev`
- two `would run: claude plugin uninstall ...` lines
- a warning for the local-scope install in `~/Desktop/repos/yt`
- two `would run: codex plugin remove ...` lines and one `would run: codex plugin marketplace remove superpowers-dev`
- 15 `would create link` lines (v7.0.2 has 15 skills, including `diagnosing-superpowers`)

`~/.local/share/superpowers` must not exist afterward.

- [ ] **Step 3: Real run**

Run: `python3 skills/sync-superpowers/scripts/sync_superpowers.py`
Expected: exit 0, `claude: superpowers@superpowers-dev scope=user version=7.0.2`, `links: 15 created, 0 updated, 0 removed, 15 total`.

If `codex plugin remove superpowers@openai-curated-remote` fails, stop. Report the stderr to the user, because this remote-plugin case was not verified in isolation.

- [ ] **Step 4: Check acceptance criteria from the spec**

Run:

```bash
claude plugin list --json | python3 -c "import json,sys;[print(p['id'],p['scope'],p['version'],p['enabled'],p.get('readFromFolder')) for p in json.load(sys.stdin) if p['id'].startswith('superpowers@')]"
codex plugin list --json | python3 -c "import json,sys;print([p['pluginId'] for p in json.load(sys.stdin)['installed'] if p['name']=='superpowers'])"
find ~/.agents/skills -maxdepth 1 -type l -lname "$HOME/.local/share/superpowers/skills/*" | wc -l
find ~/.agents/skills -maxdepth 1 -type l ! -exec test -e {} \; -print
for d in ~/.claude/skills ~/.codex/skills ~/.cursor/skills; do for s in ~/.local/share/superpowers/skills/*/; do n=$(basename "$s"); [ -e "$d/$n" ] && echo "DUP $d/$n"; done; done
```

Expected:
- Claude: `superpowers@superpowers-dev user 7.0.2 True /Users/<user>/.local/share/superpowers`, plus only the local-scope `superpowers@superpowers-marketplace` for `yt`.
- Codex: `[]`
- link count: `15`
- no broken links printed
- no `DUP` lines

- [ ] **Step 5: Second run is a no-op**

Run: `python3 skills/sync-superpowers/scripts/sync_superpowers.py`
Expected: exit 0, `links: 0 created, 0 updated, 0 removed, 15 total`, and no `codex plugin remove` or `claude plugin uninstall` lines.

- [ ] **Step 6: Sync the skill itself**

Make the new skill available locally with the existing installer:

Run: `python3 skills/sync-skill/scripts/install_local_skill.py sync-superpowers --repo-root "$(pwd)"`
Expected: three lines, `claude`, `agents`, and `codex`, each `created`.

Note: this links the skill from this worktree. After merge, run the command again from the main checkout so the links point at `main`.

- [ ] **Step 7: Ask the user to restart and spot-check**

Ask the user to restart Claude Code, Codex, and Cursor, then confirm:
- Claude Code: `/superpowers:brainstorming` exists, and the SessionStart hook still loads `using-superpowers`.
- Codex: `$brainstorming` appears once in `/skills`.
- Cursor: `brainstorming` appears once in `/` skill search.
