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

    def test_pruning_resolves_links_through_a_symlinked_agents_dir(self) -> None:
        # ~/.agents is a symlink into a deeper directory, as in a dotfiles setup.
        real_agents = self.root / "dotfiles" / "deep" / "agents"
        (real_agents / "skills").mkdir(parents=True)
        (self.home / ".agents").symlink_to(real_agents)
        # As text, this link points into the checkout. The OS resolves ".." from
        # the real directory, so it points under dotfiles and is not ours.
        (self.agents / "beta").symlink_to(Path("..") / ".." / ".." / "checkout" / "skills" / "beta")

        result = self.run_sync("--version", "v1.1.0")

        self.assert_ok(result)
        self.assertTrue((self.agents / "beta").is_symlink())
        self.assertIn("links: 2 created, 0 updated, 0 removed, 2 total", result.stdout)

    def test_superpowers_skill_in_other_skill_roots_warns(self) -> None:
        roots = [self.home / root / "skills" for root in (".claude", ".codex", ".cursor")]
        for skills_dir in roots:
            (skills_dir / "alpha").mkdir(parents=True)

        result = self.run_sync("--version", "v1.0.0")

        self.assert_ok(result)
        for skills_dir in roots:
            self.assertIn(f"warning: {skills_dir / 'alpha'} duplicates superpowers skill alpha", result.stdout)
            self.assertTrue((skills_dir / "alpha").is_dir())


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
        self.assertEqual(self.checkout_tag(), "v1.0.0")

    def test_origin_check_ignores_url_rewrites(self) -> None:
        self.assert_ok(self.run_sync("--version", "v1.0.0"))
        alias = self.root / "upstream-alias"
        alias.symlink_to(self.upstream)
        git(self.checkout, "config", f"url.{alias}.insteadOf", str(self.upstream))

        result = self.run_sync("--version", "v1.1.0")

        self.assert_ok(result)
        self.assertEqual(self.checkout_tag(), "v1.1.0")

    def test_non_git_checkout_dir_is_refused(self) -> None:
        self.checkout.mkdir()

        result = self.run_sync("--version", "v1.0.0")

        self.assertEqual(result.returncode, 1)
        self.assertIn("exists but is not a git checkout", result.stderr)

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


if __name__ == "__main__":
    unittest.main()
