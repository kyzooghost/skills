from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "skills" / "cleanup-merged-pr" / "scripts" / "delete_merged_branch.py"
DEFAULT_BRANCH = "main"
FEATURE_BRANCH = "feature"

# Isolates tests from the user's git config, such as commit signing.
GIT_CONFIG = """\
[user]
\tname = Test
\temail = test@example.com
[init]
\tdefaultBranch = main
[commit]
\tgpgsign = false
[protocol "file"]
\tallow = always
"""

# Answers only the two gh calls the script makes.
GH_STUB = """\
#!/usr/bin/env python3
import os
import sys

args = sys.argv[1:]
if args[:2] == ["repo", "view"]:
    print('{"defaultBranchRef": {"name": "main"}}')
elif args[:2] == ["pr", "list"] and "merged" in args:
    print(os.environ["GH_STUB_MERGED_PRS"])
else:
    sys.exit(f"unexpected gh call: {args}")
"""


class Fixture:
    """A bare origin, a clone at `main_checkout`, and a stub `gh` on PATH."""

    def __init__(self, root: Path) -> None:
        self.root = root
        bin_dir = root / "bin"
        bin_dir.mkdir()
        gh = bin_dir / "gh"
        gh.write_text(GH_STUB, encoding="utf-8")
        gh.chmod(0o755)
        git_config = root / "gitconfig"
        git_config.write_text(GIT_CONFIG, encoding="utf-8")
        self.env = {
            **os.environ,
            "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
            "GIT_CONFIG_GLOBAL": str(git_config),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GH_STUB_MERGED_PRS": "[]",
        }
        self.origin = root / "origin.git"
        self.git(root, "init", "--bare", str(self.origin))
        self.main_checkout = root / "repo"
        self.git(root, "clone", str(self.origin), str(self.main_checkout))
        (self.main_checkout / ".gitignore").write_text(".env\nnode_modules/\n", encoding="utf-8")
        self.commit(self.main_checkout, "README.md")
        self.git(self.main_checkout, "push", "origin", DEFAULT_BRANCH)

    def git(self, cwd: Path, *args: str) -> str:
        result = subprocess.run(
            ["git", *args], cwd=cwd, env=self.env, check=True, capture_output=True, text=True
        )
        return result.stdout.strip()

    def commit(self, cwd: Path, file_name: str) -> str:
        (cwd / file_name).write_text(f"{file_name}\n", encoding="utf-8")
        self.git(cwd, "add", "-A")
        self.git(cwd, "commit", "-m", f"add {file_name}")
        return self.git(cwd, "rev-parse", "HEAD")

    def add_worktree(self, branch: str = FEATURE_BRANCH) -> Path:
        path = self.root / f"wt-{branch}"
        self.git(self.main_checkout, "worktree", "add", "-b", branch, str(path))
        return path

    def set_merged_prs(self, *head_oids: str) -> None:
        prs = [{"number": 7 + index, "headRefOid": oid} for index, oid in enumerate(head_oids)]
        self.env["GH_STUB_MERGED_PRS"] = json.dumps(prs)

    def run_script(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=self.root,
            env=self.env,
            capture_output=True,
            text=True,
        )

    def branch_exists(self, branch: str) -> bool:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"],
            cwd=self.main_checkout,
            env=self.env,
            capture_output=True,
        )
        return result.returncode == 0


class DeleteMergedBranchTest(unittest.TestCase):
    def setUp(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.fixture = Fixture(Path(temp_dir.name).resolve())

    def assert_refused(self, result: subprocess.CompletedProcess[str], reason: str) -> None:
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("refused:", result.stderr)
        self.assertIn(reason, result.stderr)
        self.assertTrue(self.fixture.branch_exists(FEATURE_BRANCH))

    def test_merged_pr_matching_tip_deletes_current_worktree_and_branch(self) -> None:
        worktree = self.fixture.add_worktree()
        tip = self.fixture.commit(worktree, "feature.txt")
        self.fixture.set_merged_prs(tip)

        result = self.fixture.run_script("--repo", str(worktree))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(worktree.exists())
        self.assertFalse(self.fixture.branch_exists(FEATURE_BRANCH))
        self.assertIn(f"removed worktree: {worktree}", result.stdout)
        self.assertIn(f"main worktree: {self.fixture.main_checkout}", result.stdout)

    def test_local_tip_ahead_of_merged_head_is_refused(self) -> None:
        worktree = self.fixture.add_worktree()
        self.fixture.set_merged_prs(self.fixture.commit(worktree, "feature.txt"))
        self.fixture.commit(worktree, "after-merge.txt")

        result = self.fixture.run_script("--repo", str(worktree))

        self.assert_refused(result, "not on origin/main")

    def test_branch_without_pr_or_new_commits_is_deleted(self) -> None:
        worktree = self.fixture.add_worktree()

        result = self.fixture.run_script("--repo", str(worktree))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.fixture.branch_exists(FEATURE_BRANCH))

    def test_unmerged_commits_are_refused(self) -> None:
        worktree = self.fixture.add_worktree()
        self.fixture.commit(worktree, "feature.txt")

        result = self.fixture.run_script("--repo", str(worktree))

        self.assert_refused(result, "not on origin/main")

    def test_branch_in_main_checkout_switches_to_default_then_deletes(self) -> None:
        main_checkout = self.fixture.main_checkout
        self.fixture.git(main_checkout, "switch", "-c", FEATURE_BRANCH)
        self.fixture.set_merged_prs(self.fixture.commit(main_checkout, "feature.txt"))

        result = self.fixture.run_script("--repo", str(main_checkout))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.fixture.git(main_checkout, "branch", "--show-current"), DEFAULT_BRANCH)
        self.assertFalse(self.fixture.branch_exists(FEATURE_BRANCH))

    def test_default_branch_is_refused(self) -> None:
        result = self.fixture.run_script("--repo", str(self.fixture.main_checkout), "--branch", DEFAULT_BRANCH)

        self.assertEqual(result.returncode, 1)
        self.assertIn("refused: main is the default branch", result.stderr)


if __name__ == "__main__":
    unittest.main()
